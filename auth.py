from flask import Blueprint, request, jsonify
from models import User, OTPVerification, db, UserRole, AuditLog
from utils.security import create_access_token, extract_request_info
from utils.twilio_otp import send_twilio_otp, generate_otp
import re
import json
import logging

auth_bp = Blueprint('auth', __name__)

def log_audit(action, entity_type=None, entity_id=None, details=None, user_id=None):
    """Helper function to log audit events"""
    audit = AuditLog()
    audit.user_id = user_id  # For OTP-based auth, we'll pass user_id explicitly
    audit.action = action
    audit.entity_type = entity_type
    audit.entity_id = entity_id
    audit.new_values = json.dumps(details) if details else None
    audit.ip_address = request.remote_addr
    audit.user_agent = request.headers.get('User-Agent', '')[:255]
    db.session.add(audit)
    
    # Commit with retry logic for connection issues
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

def validate_phone_number(phone):
    """Validate and format phone number"""
    if not phone:
        return None, "Phone number is required"
    
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid 10-digit number
    if len(digits_only) == 10:
        return f"+91{digits_only}", None
    elif len(digits_only) == 12 and digits_only.startswith('91'):
        return f"+{digits_only}", None
    elif len(digits_only) == 13 and digits_only.startswith('91'):
        return f"+{digits_only}", None
    else:
        return None, "Please enter a valid 10-digit phone number"

def validate_email(email):
    """Basic email validation"""
    if not email:
        return None, "Email is required"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return email.lower(), None
    else:
        return None, "Please enter a valid email address"

@auth_bp.route('/login', methods=['POST'])
def login():
    """Request OTP for existing user login"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'JSON data required'}), 400
        
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        
        if not phone and not email:
            return jsonify({'success': False, 'message': 'Either phone number or email is required'}), 400
        
        # Process phone or email
        target = None
        channel = None
        
        if phone:
            formatted_phone, error = validate_phone_number(phone)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_phone
            channel = 'sms'
        else:
            formatted_email, error = validate_email(email)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_email
            channel = 'email'
        
        # Check if user exists
        user = None
        if channel == 'sms':
            user = User.query.filter_by(phone=target).first()
        else:
            user = User.query.filter_by(email=target).first()
        
        if not user:
            # SECURITY: Generic message to prevent account enumeration
            return jsonify({'success': False, 'message': 'Authentication failed. Please check your credentials.'}), 400
        
        # Generate and send OTP
        otp_code = generate_otp()
        request_info = extract_request_info()
        
        otp_entry = OTPVerification.create_otp(
            target=target,
            otp_code=otp_code,
            purpose='login',
            user_id=user.id,
            channel=channel
        )
        otp_entry.ip_address = request_info['ip_address']
        otp_entry.user_agent = request_info['user_agent']
        
        db.session.add(otp_entry)
        
        # Send OTP
        if channel == 'sms':
            success = send_twilio_otp(target, otp_code)
            if not success:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'}), 500
        else:
            # TODO: Implement email OTP sending
            logging.warning(f"Email OTP not implemented yet for {target}")
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Email OTP not supported yet. Please use phone number.'}), 400
        
        db.session.commit()
        
        # Mask target for response
        if channel == 'sms':
            masked_target = f"****{target[-4:]}"
        else:
            parts = target.split('@')
            masked_target = f"{parts[0][:2]}***@{parts[1]}"
        
        logging.info(f"Login OTP sent to {target[:5]}***")
        
        return jsonify({
            'success': True,
            'message': f'OTP sent to {masked_target}',
            'target': masked_target,
            'channel': channel
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register new user with phone/email + name"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'JSON data required'}), 400
        
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        # SECURITY: Ignore client-provided role, always default to driver
        role = 'driver'  # Only admin can elevate roles through admin interface
        
        # Validation
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
        
        if not phone and not email:
            return jsonify({'success': False, 'message': 'Either phone number or email is required'}), 400
        
        # Process phone or email
        target = None
        channel = None
        
        if phone:
            formatted_phone, error = validate_phone_number(phone)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_phone
            channel = 'sms'
        else:
            formatted_email, error = validate_email(email)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_email
            channel = 'email'
        
        # Check if user already exists (prevent account enumeration)
        existing_user = None
        if channel == 'sms':
            existing_user = User.query.filter_by(phone=target).first()
        else:
            existing_user = User.query.filter_by(email=target).first()
        
        if existing_user:
            # SECURITY: Generic message to prevent account enumeration
            return jsonify({'success': False, 'message': 'Registration failed. Please try again or contact support.'}), 400
        
        # Create new user (without password)
        user = User()
        user.username = target  # Use phone/email as username
        user.first_name = name.split()[0] if name else ""
        user.last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
        user.role = UserRole(role)
        
        if channel == 'sms':
            user.phone = target
            user.email = email if email else None  # Use None instead of empty string
        else:
            user.email = target
            user.phone = phone if phone else None  # Use None instead of empty string
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Generate and send OTP
        otp_code = generate_otp()
        request_info = extract_request_info()
        
        otp_entry = OTPVerification.create_otp(
            target=target,
            otp_code=otp_code,
            purpose='signup',
            user_id=user.id,
            channel=channel
        )
        otp_entry.ip_address = request_info['ip_address']
        otp_entry.user_agent = request_info['user_agent']
        
        db.session.add(otp_entry)
        
        # Send OTP
        if channel == 'sms':
            success = send_twilio_otp(target, otp_code)
            if not success:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'}), 500
        else:
            # TODO: Implement email OTP sending
            logging.warning(f"Email OTP not implemented yet for {target}")
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Email OTP not supported yet. Please use phone number.'}), 400
        
        db.session.commit()
        
        # Mask target for response
        if channel == 'sms':
            masked_target = f"****{target[-4:]}"
        else:
            parts = target.split('@')
            masked_target = f"{parts[0][:2]}***@{parts[1]}"
        
        logging.info(f"Signup OTP sent to {target[:5]}***")
        
        return jsonify({
            'success': True,
            'message': f'OTP sent to {masked_target}',
            'user_id': user.id,
            'target': masked_target,
            'channel': channel
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Signup error: {str(e)}")
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Validate OTP and issue JWT token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'JSON data required'}), 400
        
        otp_code = data.get('otp', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        purpose = data.get('purpose', '').strip().lower()
        
        if not otp_code:
            return jsonify({'success': False, 'message': 'OTP code is required'}), 400
        
        if not phone and not email:
            return jsonify({'success': False, 'message': 'Either phone number or email is required'}), 400
        
        if purpose not in ['login', 'signup']:
            return jsonify({'success': False, 'message': 'Invalid purpose. Must be login or signup'}), 400
        
        # Process phone or email
        target = None
        
        if phone:
            formatted_phone, error = validate_phone_number(phone)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_phone
        else:
            formatted_email, error = validate_email(email)
            if error:
                return jsonify({'success': False, 'message': error}), 400
            target = formatted_email
        
        # Verify OTP
        is_valid, user_id, message = OTPVerification.verify_otp(target, otp_code, purpose)
        
        if not is_valid:
            return jsonify({'success': False, 'message': message}), 400
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Update login tracking
        user.last_login = db.func.now()
        user.login_count = (user.login_count or 0) + 1
        db.session.commit()
        
        # Create JWT token
        token_data = create_access_token(user.id, user.role.value)
        
        # Log successful authentication
        log_audit('otp_authentication_success', user_id=user.id)
        
        logging.info(f"Successful OTP verification for user {user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user': {
                'id': user.id,
                'name': user.full_name,
                'role': user.role.value,
                'phone': user.phone,
                'email': user.email
            },
            **token_data
        }), 200
        
    except Exception as e:
        logging.error(f"OTP verification error: {str(e)}")
        return jsonify({'success': False, 'message': 'Verification failed. Please try again.'}), 500

# Add rate limiting placeholder for future implementation
# TODO: Implement rate limiting for OTP requests per IP/phone/email
