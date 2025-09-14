import secrets
import string
import re
import os
import logging
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure OTP code with specified length"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def format_phone_number(phone: str) -> str:
    """Format phone number for international use (E.164 format)"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Add country code if not present (assuming India +91 for 10-digit numbers)
    if len(phone) == 10:
        phone = '91' + phone
    
    # Add + prefix for E.164 format
    if not phone.startswith('+'):
        phone = '+' + phone
    
    return phone

def send_otp_sms(phone_number: str, otp_code: str) -> Dict[str, Any]:
    """
    Send OTP via SMS using Twilio integration
    Returns: {'success': bool, 'message': str, 'sid': str (optional)}
    """
    try:
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Check if Twilio credentials are available
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logger.warning("Twilio credentials not configured")
            # Only log OTP in debug mode, and mask it partially
            debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
            if debug_mode:
                masked_otp = otp_code[:2] + '*' * (len(otp_code) - 2)
                logger.info(f"DEBUG: OTP for {formatted_phone}: {masked_otp}")
                return {
                    'success': True,
                    'message': 'OTP would be sent in production (check logs for masked version)',
                    'debug_mode': True
                }
            else:
                return {
                    'success': False,
                    'message': 'SMS service not configured. Please contact administrator.'
                }
        
        # Import and use Twilio
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        
        message_body = f"Your PLS Travels verification code is: {otp_code}. Valid for 10 minutes. Do not share this code."
        
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=formatted_phone
        )
        
        logger.info(f"OTP sent successfully to {formatted_phone}, SID: {message.sid}")
        
        return {
            'success': True,
            'message': 'OTP sent successfully',
            'sid': message.sid
        }
        
    except Exception as e:
        logger.error(f"Failed to send OTP to {phone_number}: {str(e)}")
        return {
            'success': False,
            'message': f'Failed to send OTP: {str(e)}'
        }

def is_valid_phone_number(phone: str) -> bool:
    """Validate phone number format (E.164 compatible)"""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid E.164 format (1-15 digits)
    # For India: 10-digit local or 12-digit with +91
    # For global: accept 7-15 digits (excluding country code)
    if len(digits_only) >= 7 and len(digits_only) <= 15:
        return True
    
    # Also accept 10-digit numbers (will be formatted as +91 India)
    return len(digits_only) == 10

def _hash_otp(otp_code: str) -> str:
    """Hash OTP for secure storage using Flask's secret key"""
    try:
        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY')
    except RuntimeError:
        # Fallback if no app context (e.g., testing)
        secret_key = os.environ.get('SECRET_KEY')
    
    if not secret_key:
        raise RuntimeError("SECRET_KEY is required for OTP hashing")
    
    return hmac.new(
        secret_key.encode(),
        otp_code.encode(),
        hashlib.sha256
    ).hexdigest()

class OTPSession:
    """Manage OTP session data"""
    MAX_ATTEMPTS = 3
    
    @staticmethod
    def store_otp(session, phone_number: str, otp_code: str, purpose: str = 'login'):
        """Store OTP in session with expiry (stores hash for security)"""
        session['otp_data'] = {
            'phone': phone_number,
            'code_hash': _hash_otp(otp_code),
            'purpose': purpose,
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            'attempts': 0
        }
    
    @staticmethod
    def get_otp_data(session) -> Optional[Dict[str, Any]]:
        """Get OTP data from session if not expired"""
        otp_data = session.get('otp_data')
        if not otp_data:
            return None
        
        # Check if expired
        expires_at = datetime.fromisoformat(otp_data['expires_at'])
        if datetime.now(timezone.utc) > expires_at:
            session.pop('otp_data', None)
            return None
        
        return otp_data
    
    @staticmethod
    def verify_otp(session, entered_code: str) -> Dict[str, Any]:
        """Verify OTP code"""
        otp_data = OTPSession.get_otp_data(session)
        
        if not otp_data:
            return {'success': False, 'message': 'OTP expired or not found'}
        
        # Check if max attempts reached before verifying
        if otp_data['attempts'] >= OTPSession.MAX_ATTEMPTS:
            session.pop('otp_data', None)
            return {'success': False, 'message': 'Too many attempts. Please request a new OTP'}
        
        # Verify code using hash comparison
        entered_hash = _hash_otp(entered_code)
        if hmac.compare_digest(otp_data['code_hash'], entered_hash):
            # Success - clear OTP immediately to prevent reuse
            phone = otp_data['phone']
            purpose = otp_data['purpose']
            session.pop('otp_data', None)
            return {
                'success': True,
                'message': 'OTP verified successfully',
                'phone': phone,
                'purpose': purpose
            }
        else:
            # Increment attempts on failure
            otp_data['attempts'] += 1
            session['otp_data'] = otp_data
            
            remaining_attempts = OTPSession.MAX_ATTEMPTS - otp_data['attempts']
            if remaining_attempts <= 0:
                session.pop('otp_data', None)
                return {'success': False, 'message': 'Too many attempts. Please request a new OTP'}
            
            return {
                'success': False,
                'message': f'Invalid OTP. {remaining_attempts} attempts remaining'
            }
    
    @staticmethod
    def clear_otp(session):
        """Clear OTP data from session"""
        session.pop('otp_data', None)