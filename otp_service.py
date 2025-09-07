import os
import random
import string
from datetime import datetime, timedelta
from flask import request
from twilio.rest import Client
from models import OTPCode, db
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# OTP configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS = 3
MAX_OTP_REQUESTS_PER_HOUR = 5

def generate_otp_code():
    """Generate a random 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))

def normalize_phone_number(phone_number):
    """Normalize phone number format for consistency"""
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # Add country code if not present (assuming India +91)
    if len(digits_only) == 10:
        return f"+91{digits_only}"
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        return f"+{digits_only}"
    elif digits_only.startswith("+"):
        return phone_number
    else:
        return f"+{digits_only}"

def check_rate_limit(phone_number):
    """Check if phone number has exceeded rate limit for OTP requests"""
    normalized_phone = normalize_phone_number(phone_number)
    
    # Check requests in last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_otps = OTPCode.query.filter(
        OTPCode.phone_number == normalized_phone,
        OTPCode.created_at >= one_hour_ago
    ).count()
    
    return recent_otps < MAX_OTP_REQUESTS_PER_HOUR

def cleanup_expired_otps():
    """Clean up expired OTP codes from database"""
    try:
        expired_otps = OTPCode.query.filter(
            OTPCode.expires_at < datetime.utcnow()
        ).all()
        
        for otp in expired_otps:
            db.session.delete(otp)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(expired_otps)} expired OTP codes")
    except Exception as e:
        logger.error(f"Error cleaning up expired OTPs: {str(e)}")
        db.session.rollback()

def invalidate_previous_otps(phone_number):
    """Invalidate all previous OTP codes for a phone number"""
    try:
        normalized_phone = normalize_phone_number(phone_number)
        previous_otps = OTPCode.query.filter(
            OTPCode.phone_number == normalized_phone,
            OTPCode.is_used == False
        ).all()
        
        for otp in previous_otps:
            otp.is_used = True
            otp.used_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Invalidated {len(previous_otps)} previous OTP codes for {normalized_phone}")
    except Exception as e:
        logger.error(f"Error invalidating previous OTPs: {str(e)}")
        db.session.rollback()

def send_otp_sms(phone_number):
    """Send OTP code via SMS using Twilio"""
    try:
        # Normalize phone number
        normalized_phone = normalize_phone_number(phone_number)
        
        # Check rate limit
        if not check_rate_limit(normalized_phone):
            return {
                'success': False,
                'message': 'Too many OTP requests. Please try again later.'
            }
        
        # Clean up expired OTPs
        cleanup_expired_otps()
        
        # Invalidate previous OTPs for this phone number
        invalidate_previous_otps(normalized_phone)
        
        # Generate new OTP
        otp_code = generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        # Save OTP to database
        otp_record = OTPCode(
            phone_number=normalized_phone,
            otp_code=otp_code,
            expires_at=expires_at,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        
        db.session.add(otp_record)
        db.session.commit()
        
        # Check if we're in development mode (for Twilio trial limitations)
        import os
        test_mode = os.environ.get('OTP_TEST_MODE', 'false').lower() == 'true'
        
        if test_mode:
            # Development mode - show OTP in response for testing
            logger.info(f"TEST MODE: OTP for {normalized_phone} is: {otp_code}")
            return {
                'success': True,
                'message': f'TEST MODE: Your OTP code is {otp_code}',
                'test_otp': otp_code,
                'expires_in_minutes': OTP_EXPIRY_MINUTES
            }
        
        # Send SMS using Twilio
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                
                message_body = f"Your PLS TRAVELS login code is: {otp_code}\n\nThis code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share this code with anyone."
                
                message = client.messages.create(
                    body=message_body,
                    from_=TWILIO_PHONE_NUMBER,
                    to=normalized_phone
                )
                
                logger.info(f"SMS sent successfully to {normalized_phone}, Message SID: {message.sid}")
                
                return {
                    'success': True,
                    'message': f'OTP sent to {normalized_phone}',
                    'expires_in_minutes': OTP_EXPIRY_MINUTES
                }
            except Exception as twilio_error:
                # If SMS fails, fall back to test mode for development
                logger.warning(f"SMS failed, falling back to test mode: {str(twilio_error)}")
                return {
                    'success': True,
                    'message': f'SMS failed - TEST MODE: Your OTP code is {otp_code}',
                    'test_otp': otp_code,
                    'expires_in_minutes': OTP_EXPIRY_MINUTES
                }
        else:
            logger.error("Twilio credentials not configured")
            return {
                'success': False,
                'message': 'SMS service not configured. Please contact administrator.'
            }
            
    except Exception as e:
        logger.error(f"Error sending OTP SMS: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'message': 'Failed to send OTP. Please try again.'
        }

def verify_otp_code(phone_number, otp_code):
    """Verify OTP code for a phone number"""
    try:
        normalized_phone = normalize_phone_number(phone_number)
        
        # Find the most recent valid OTP for this phone number
        otp_record = OTPCode.query.filter(
            OTPCode.phone_number == normalized_phone,
            OTPCode.otp_code == otp_code,
            OTPCode.is_used == False
        ).order_by(OTPCode.created_at.desc()).first()
        
        if not otp_record:
            return {
                'success': False,
                'message': 'Invalid OTP code.'
            }
        
        # Increment attempt count
        otp_record.increment_attempt()
        
        # Check if too many attempts
        if otp_record.attempt_count > MAX_ATTEMPTS:
            otp_record.mark_as_used()
            return {
                'success': False,
                'message': 'Too many invalid attempts. Please request a new OTP.'
            }
        
        # Check if expired
        if otp_record.is_expired():
            otp_record.mark_as_used()
            return {
                'success': False,
                'message': 'OTP code has expired. Please request a new one.'
            }
        
        # OTP is valid - mark as used
        otp_record.mark_as_used()
        
        logger.info(f"OTP verified successfully for {normalized_phone}")
        
        return {
            'success': True,
            'message': 'OTP verified successfully.'
        }
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return {
            'success': False,
            'message': 'Failed to verify OTP. Please try again.'
        }

def get_otp_status(phone_number):
    """Get status of latest OTP for a phone number"""
    try:
        normalized_phone = normalize_phone_number(phone_number)
        
        latest_otp = OTPCode.query.filter(
            OTPCode.phone_number == normalized_phone
        ).order_by(OTPCode.created_at.desc()).first()
        
        if not latest_otp:
            return {
                'has_otp': False,
                'message': 'No OTP found for this number.'
            }
        
        if latest_otp.is_used:
            return {
                'has_otp': False,
                'message': 'OTP has been used.'
            }
        
        if latest_otp.is_expired():
            return {
                'has_otp': False,
                'message': 'OTP has expired.'
            }
        
        # Calculate remaining time
        remaining_time = latest_otp.expires_at - datetime.utcnow()
        remaining_minutes = int(remaining_time.total_seconds() / 60)
        
        return {
            'has_otp': True,
            'expires_at': latest_otp.expires_at,
            'remaining_minutes': remaining_minutes,
            'attempt_count': latest_otp.attempt_count,
            'max_attempts': MAX_ATTEMPTS
        }
        
    except Exception as e:
        logger.error(f"Error getting OTP status: {str(e)}")
        return {
            'has_otp': False,
            'message': 'Error checking OTP status.'
        }