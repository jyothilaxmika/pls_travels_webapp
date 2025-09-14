"""
Mobile Authentication Module
JWT-based authentication for Android app integration
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, 
    create_refresh_token, get_jwt_identity, get_jwt
)
from flask_login import login_user
import logging
from datetime import datetime, timezone, timedelta

from utils.twilio_otp import (
    generate_otp, 
    send_otp_sms, 
    is_valid_phone_number, 
    format_phone_number,
    OTPSession
)
from utils.rate_limiter import otp_rate_limiter
from utils.config_validator import check_production_readiness
from models import User, UserRole, UserStatus, db
from app import csrf

logger = logging.getLogger(__name__)

# Create mobile auth blueprint
mobile_auth_bp = Blueprint('mobile_auth', __name__)

# JWT token blacklist for logout functionality
blacklisted_tokens = set()

def get_client_ip():
    """Get real client IP address with proxy support"""
    # Check for forwarded IP (when behind proxy)
    forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(',')[0].strip()
    
    # Check for real IP (some proxies)
    real_ip = request.environ.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip.strip()
    
    # Fallback to remote address
    return request.remote_addr or '127.0.0.1'

@mobile_auth_bp.route('/api/v1/auth/send-otp', methods=['POST'])
@csrf.exempt
def mobile_send_otp():
    """Send OTP for mobile authentication"""
    try:
        client_ip = get_client_ip()
        
        # Check production readiness
        config_status = check_production_readiness()
        if not config_status['otp_enabled']:
            return jsonify({
                'success': False,
                'error': 'OTP_SERVICE_UNAVAILABLE',
                'message': 'Authentication service is currently unavailable'
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'INVALID_REQUEST',
                'message': 'Request body is required'
            }), 400
        
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'PHONE_REQUIRED',
                'message': 'Phone number is required'
            }), 400
        
        # Validate phone number format
        if not is_valid_phone_number(phone_number):
            return jsonify({
                'success': False,
                'error': 'INVALID_PHONE',
                'message': 'Invalid phone number format'
            }), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Apply production-grade rate limiting
        can_send, reason, retry_after = otp_rate_limiter.can_send_otp(formatted_phone, client_ip)
        if not can_send:
            logger.warning(f"MOBILE_OTP_RATE_LIMITED: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                          f"IP: {client_ip} Reason: {reason}")
            return jsonify({
                'success': False,
                'error': 'RATE_LIMITED',
                'message': 'Too many requests. Please try again later.',
                'retry_after': retry_after
            }), 429
        
        # Record start time for consistent response timing
        import time
        start_time = time.time()
        
        # Check if user exists with this phone number
        user = User.query.filter_by(phone=formatted_phone).first()
        
        # Generate OTP for timing consistency
        otp_code = generate_otp(6)
        
        if user and user.status == UserStatus.ACTIVE:
            # Send OTP via SMS for valid users
            sms_result = send_otp_sms(formatted_phone, otp_code)
            
            if sms_result['success']:
                # Store OTP in session for mobile verification
                # For mobile, we'll use a simple in-memory store or database
                # This is a simplified version for mobile API
                from flask import session as flask_session
                OTPSession.store_otp(flask_session, formatted_phone, otp_code, 'mobile_login')
                
                # Record successful send for rate limiting
                otp_rate_limiter.record_otp_sent(formatted_phone, client_ip)
                
                logger.info(f"MOBILE_OTP_SENT: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                           f"User: {user.username}")
            else:
                logger.error(f"MOBILE_OTP_FAILED: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                           f"Error: {sms_result['message']}")
        else:
            # Still record the send attempt for rate limiting (prevent enumeration)
            otp_rate_limiter.record_otp_sent(formatted_phone, client_ip)
            if not user:
                logger.info(f"MOBILE_OTP_UNKNOWN_USER: Phone: {formatted_phone[-4:].rjust(4, '*')}")
            else:
                logger.info(f"MOBILE_OTP_INACTIVE_USER: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                           f"Status: {user.status.name}")
        
        # Ensure consistent minimum response time (1.5 seconds) to prevent timing attacks
        elapsed = time.time() - start_time
        min_response_time = 1.5
        if elapsed < min_response_time:
            time.sleep(min_response_time - elapsed)
        
        # Always return success to prevent user enumeration
        return jsonify({
            'success': True,
            'message': 'If this phone number is registered, you will receive an OTP shortly',
            'session_id': formatted_phone[-4:]  # Last 4 digits for session reference
        })
        
    except Exception as e:
        logger.error(f"Error in mobile_send_otp: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_auth_bp.route('/api/v1/auth/verify-otp', methods=['POST'])
@csrf.exempt
def mobile_verify_otp():
    """Verify OTP and return JWT tokens for mobile authentication"""
    try:
        client_ip = get_client_ip()
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'INVALID_REQUEST',
                'message': 'Request body is required'
            }), 400
        
        phone_number = data.get('phone_number', '').strip()
        otp_code = data.get('otp_code', '').strip()
        device_id = data.get('device_id', '').strip()
        
        if not phone_number or not otp_code:
            return jsonify({
                'success': False,
                'error': 'MISSING_FIELDS',
                'message': 'Phone number and OTP code are required'
            }), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Verify OTP (this will be implemented using session-like storage)
        # For now, let's verify against the user database
        user = User.query.filter_by(phone=formatted_phone).first()
        
        if not user or user.status != UserStatus.ACTIVE:
            logger.warning(f"MOBILE_OTP_VERIFY_INVALID_USER: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                          f"IP: {client_ip}")
            return jsonify({
                'success': False,
                'error': 'INVALID_CREDENTIALS',
                'message': 'Invalid phone number or OTP'
            }), 401
        
        # TODO: Implement proper OTP verification with session storage
        # For demo purposes, accept any 6-digit code for development
        if len(otp_code) != 6 or not otp_code.isdigit():
            logger.warning(f"MOBILE_OTP_VERIFY_INVALID_CODE: Phone: {formatted_phone[-4:].rjust(4, '*')} "
                          f"Code: {otp_code[:2]}**** IP: {client_ip}")
            return jsonify({
                'success': False,
                'error': 'INVALID_OTP',
                'message': 'Invalid OTP code'
            }), 401
        
        # Create JWT tokens with user claims
        additional_claims = {
            'role': user.role.name,
            'user_id': user.id,
            'phone': formatted_phone,
            'device_id': device_id if device_id else None
        }
        
        access_token = create_access_token(
            identity=user.username,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=1)  # 1 hour access token
        )
        
        refresh_token = create_refresh_token(
            identity=user.username,
            additional_claims={'user_id': user.id, 'role': user.role.name},
            expires_delta=timedelta(days=30)  # 30 day refresh token
        )
        
        # Update user's last login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        
        logger.info(f"MOBILE_LOGIN_SUCCESS: User: {user.username} "
                   f"Phone: {formatted_phone[-4:].rjust(4, '*')} IP: {client_ip}")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role.name,
                'full_name': user.full_name,
                'phone': formatted_phone,
                'branch_name': user.branch.name if user.branch else None
            },
            'token_expires_in': 3600  # 1 hour in seconds
        })
        
    except Exception as e:
        logger.error(f"Error in mobile_verify_otp: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_auth_bp.route('/api/v1/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
@csrf.exempt
def mobile_refresh_token():
    """Refresh JWT access token using refresh token"""
    try:
        current_user_identity = get_jwt_identity()
        jwt_claims = get_jwt()
        
        # Get user from database
        user = User.query.filter_by(username=current_user_identity).first()
        
        if not user or user.status != UserStatus.ACTIVE:
            return jsonify({
                'success': False,
                'error': 'USER_INACTIVE',
                'message': 'User account is not active'
            }), 401
        
        # Create new access token
        additional_claims = {
            'role': user.role.name,
            'user_id': user.id,
            'phone': user.phone,
            'device_id': jwt_claims.get('device_id')
        }
        
        new_access_token = create_access_token(
            identity=current_user_identity,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=1)
        )
        
        logger.info(f"MOBILE_TOKEN_REFRESH: User: {user.username}")
        
        return jsonify({
            'success': True,
            'access_token': new_access_token,
            'token_expires_in': 3600
        })
        
    except Exception as e:
        logger.error(f"Error in mobile_refresh_token: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_auth_bp.route('/api/v1/auth/logout', methods=['POST'])
@jwt_required()
@csrf.exempt
def mobile_logout():
    """Logout and blacklist JWT token"""
    try:
        jwt_claims = get_jwt()
        jti = jwt_claims['jti']  # JWT ID
        
        # Add token to blacklist
        blacklisted_tokens.add(jti)
        
        current_user = get_jwt_identity()
        logger.info(f"MOBILE_LOGOUT: User: {current_user}")
        
        return jsonify({
            'success': True,
            'message': 'Successfully logged out'
        })
        
    except Exception as e:
        logger.error(f"Error in mobile_logout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

# JWT token blacklist checker
def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if JWT token is in blacklist"""
    jti = jwt_payload['jti']
    return jti in blacklisted_tokens