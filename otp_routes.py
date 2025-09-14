"""
OTP Authentication Routes
Handles phone number based OTP login and verification
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from flask_login import login_user, current_user
import logging
from datetime import datetime, timezone, timedelta
from app import csrf

from utils.twilio_otp import (
    generate_otp, 
    send_otp_sms, 
    is_valid_phone_number, 
    format_phone_number,
    OTPSession
)
from models import User, UserRole, UserStatus, db
from timezone_utils import get_ist_time_naive

logger = logging.getLogger(__name__)

# Create OTP blueprint
otp_bp = Blueprint('otp', __name__)

def log_audit(action, phone_number=None, details=None):
    """Log audit trail for OTP actions"""
    if phone_number:
        masked_phone = f"{phone_number[:3]}****{phone_number[-3:]}"
    else:
        masked_phone = 'N/A'
    logger.info(f"OTP_AUDIT: {action} - Phone: {masked_phone} - Details: {details}")

@otp_bp.route('/send-otp', methods=['POST'])
@csrf.exempt
def send_otp():
    """Send OTP to phone number for login"""
    try:
        # Basic rate limiting - check if OTP was sent recently
        last_otp_time = session.get('last_otp_time')
        if last_otp_time:
            last_time = datetime.fromisoformat(last_otp_time)
            if datetime.now(timezone.utc) - last_time < timedelta(seconds=60):
                return jsonify({
                    'success': False,
                    'message': 'Please wait before requesting another OTP'
                }), 429
        data = request.get_json()
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Phone number is required'
            }), 400
        
        # Validate phone number format
        if not is_valid_phone_number(phone_number):
            return jsonify({
                'success': False,
                'message': 'Invalid phone number format'
            }), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Record start time for consistent response timing
        import time
        start_time = time.time()
        
        # Check if user exists with this phone number
        user = User.query.filter_by(phone=formatted_phone).first()
        
        # Always return success to prevent user enumeration
        # Generate OTP for timing consistency even if user doesn't exist
        otp_code = generate_otp(6)
        
        if user and user.status == UserStatus.ACTIVE:
            # Send OTP via SMS for valid users
            sms_result = send_otp_sms(formatted_phone, otp_code)
            
            if sms_result['success']:
                # Store OTP in session only for valid users
                OTPSession.store_otp(session, formatted_phone, otp_code, 'login')
                log_audit('send_otp_success', formatted_phone, f'User: {user.username}')
            else:
                log_audit('send_otp_failed', formatted_phone, sms_result['message'])
        else:
            # Log but don't store OTP for invalid users
            if not user:
                log_audit('send_otp_unknown_user', formatted_phone)
            else:
                log_audit('send_otp_inactive_user', formatted_phone, f'Status: {user.status.name}')
        
        # Ensure consistent minimum response time (1.5 seconds) to prevent timing attacks
        elapsed = time.time() - start_time
        min_response_time = 1.5
        if elapsed < min_response_time:
            time.sleep(min_response_time - elapsed)
        
        # Record send time for rate limiting
        session['last_otp_time'] = datetime.now(timezone.utc).isoformat()
        
        # Always return the same message to prevent enumeration
        return jsonify({
            'success': True,
            'message': 'If the phone number is registered and active, an OTP has been sent.'
        })
        
    except Exception as e:
        logger.error(f"Error in send_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@otp_bp.route('/verify-otp', methods=['POST'])
@csrf.exempt
def verify_otp():
    """Verify OTP and log user in"""
    try:
        data = request.get_json()
        otp_code = data.get('otp_code', '').strip()
        
        if not otp_code:
            return jsonify({
                'success': False,
                'message': 'OTP code is required'
            }), 400
        
        # Verify OTP
        verification_result = OTPSession.verify_otp(session, otp_code)
        
        if not verification_result['success']:
            log_audit('verify_otp_failed', None, verification_result['message'])
            return jsonify(verification_result), 400
        
        # Get user by phone number
        phone_number = verification_result['phone']
        user = User.query.filter_by(phone=phone_number).first()
        
        if not user:
            log_audit('verify_otp_user_not_found', phone_number)
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Double-check user is still active
        if user.status != UserStatus.ACTIVE:
            log_audit('verify_otp_inactive_user', phone_number, f'Status: {user.status.name}')
            return jsonify({
                'success': False,
                'message': 'Account is not active'
            }), 403
        
        # Log the user in
        login_user(user, remember=True)
        
        # Update last login
        user.last_login = get_ist_time_naive()
        user.login_count = (user.login_count or 0) + 1
        user.failed_login_attempts = 0
        
        # Commit with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                db.session.commit()
                break
            except Exception:
                db.session.rollback()
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5)
        
        log_audit('verify_otp_success', phone_number, f'User: {user.username}')
        
        # Determine redirect URL based on user role
        if user.role == UserRole.ADMIN:
            redirect_url = url_for('admin.dashboard')
        elif user.role == UserRole.MANAGER:
            redirect_url = url_for('manager.dashboard')
        else:
            redirect_url = url_for('driver.dashboard')
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'redirect_url': redirect_url,
            'user': {
                'username': user.username,
                'role': user.role.name,
                'full_name': user.full_name
            }
        })
        
    except Exception as e:
        logger.error(f"Error in verify_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@otp_bp.route('/resend-otp', methods=['POST'])
@csrf.exempt
def resend_otp():
    """Resend OTP to the same phone number"""
    try:
        # Get current OTP data
        otp_data = OTPSession.get_otp_data(session)
        
        if not otp_data:
            return jsonify({
                'success': False,
                'message': 'No active OTP session found. Please start over.'
            }), 400
        
        phone_number = otp_data['phone']
        
        # Check if user still exists and is active
        user = User.query.filter_by(phone=phone_number).first()
        if not user or user.status != UserStatus.ACTIVE:
            OTPSession.clear_otp(session)
            return jsonify({
                'success': False,
                'message': 'Invalid session. Please start over.'
            }), 400
        
        # Generate new OTP
        otp_code = generate_otp(6)
        
        # Send OTP via SMS
        sms_result = send_otp_sms(phone_number, otp_code)
        
        if not sms_result['success']:
            log_audit('resend_otp_failed', phone_number, sms_result['message'])
            return jsonify({
                'success': False,
                'message': 'Failed to resend OTP. Please try again later.'
            }), 500
        
        # Store new OTP in session
        OTPSession.store_otp(session, phone_number, otp_code, 'login')
        
        log_audit('resend_otp_success', phone_number, f'User: {user.username}')
        
        return jsonify({
            'success': True,
            'message': 'OTP resent successfully',
            'debug_mode': sms_result.get('debug_mode', False)
        })
        
    except Exception as e:
        logger.error(f"Error in resend_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@otp_bp.route('/otp-login', methods=['GET'])
def otp_login_page():
    """Show OTP login page"""
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == UserRole.MANAGER:
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('driver.dashboard'))
    
    return render_template('auth/otp_login.html')

@otp_bp.route('/clear-otp-session', methods=['POST'])
@csrf.exempt
def clear_otp_session():
    """Clear OTP session data"""
    OTPSession.clear_otp(session)
    return jsonify({
        'success': True,
        'message': 'OTP session cleared'
    })

# Error handlers for OTP blueprint
@otp_bp.errorhandler(404)
def otp_not_found(error):
    return jsonify({
        'success': False,
        'message': 'OTP endpoint not found'
    }), 404

@otp_bp.errorhandler(500)
def otp_internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error in OTP service'
    }), 500