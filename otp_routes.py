from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from models import db, User, OTPVerification, UserRole, UserStatus, Driver
from utils.twilio_otp import generate_otp, send_twilio_otp, format_phone_number
from auth import log_audit
import logging
from datetime import datetime

otp_bp = Blueprint('otp', __name__)

# Import CSRF protection
from app import csrf

@otp_bp.route('/login/otp')
def otp_login():
    """OTP login page"""
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == UserRole.MANAGER:
            return redirect(url_for('manager.dashboard'))
        elif current_user.role == UserRole.DRIVER:
            return redirect(url_for('driver.dashboard'))
        else:
            return redirect(url_for('auth.login'))
    return render_template('auth/otp_login.html')

@otp_bp.route('/register/otp')
def otp_register():
    """OTP registration page"""
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == UserRole.MANAGER:
            return redirect(url_for('manager.dashboard'))
        elif current_user.role == UserRole.DRIVER:
            return redirect(url_for('driver.dashboard'))
        else:
            return redirect(url_for('auth.login'))
    return render_template('auth/otp_register.html')

@otp_bp.route('/send-otp', methods=['POST'])
@csrf.exempt
def send_otp():
    """Send OTP to phone number"""
    try:
        phone_number = request.form.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({'success': False, 'message': 'Phone number is required'})
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Check if user exists with this phone number
        user = User.query.filter_by(phone=phone_number).first()
        
        if not user:
            return jsonify({'success': False, 'message': 'No account found with this phone number'})
        
        # Generate OTP
        otp_code = generate_otp()
        
        # Create OTP verification entry
        otp_verification = OTPVerification.create_otp(formatted_phone, otp_code)
        otp_verification.ip_address = request.remote_addr
        otp_verification.user_agent = request.headers.get('User-Agent', '')[:500]
        
        db.session.add(otp_verification)
        db.session.commit()
        
        # Send OTP via Twilio
        sms_sent = send_twilio_otp(formatted_phone, otp_code)
        
        if sms_sent:
            # Store phone number in session for verification
            session['otp_phone_number'] = formatted_phone
            session['otp_user_id'] = user.id
            
            log_audit('otp_requested', 'user', user.id, {
                'phone_number': phone_number,
                'formatted_phone': formatted_phone
            })
            
            return jsonify({
                'success': True, 
                'message': f'OTP sent to {phone_number}',
                'masked_phone': f"****{phone_number[-4:]}"
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'})
            
    except Exception as e:
        logging.error(f"Error sending OTP: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})

@otp_bp.route('/verify-otp', methods=['POST'])
@csrf.exempt
def verify_otp():
    """Verify OTP and login user"""
    try:
        otp_code = request.form.get('otp_code', '').strip()
        phone_number = session.get('otp_phone_number')
        user_id = session.get('otp_user_id')
        
        if not otp_code:
            return jsonify({'success': False, 'message': 'OTP code is required'})
            
        if not phone_number or not user_id:
            return jsonify({'success': False, 'message': 'Session expired. Please request a new OTP.'})
        
        # Verify OTP
        is_valid, message = OTPVerification.verify_otp(phone_number, otp_code)
        
        if is_valid:
            # Get user and login
            user = User.query.get(user_id)
            if user:
                login_user(user)
                
                # Clear OTP session data
                session.pop('otp_phone_number', None)
                session.pop('otp_user_id', None)
                
                log_audit('otp_login_success', 'user', user.id, {
                    'phone_number': phone_number,
                    'login_method': 'otp'
                })
                
                # Redirect based on user role
                if user.role == UserRole.ADMIN:
                    redirect_url = url_for('admin.dashboard')
                elif user.role == UserRole.MANAGER:
                    redirect_url = url_for('manager.dashboard')
                elif user.role == UserRole.DRIVER:
                    redirect_url = url_for('driver.dashboard')
                else:
                    redirect_url = url_for('auth.login')
                
                return jsonify({
                    'success': True, 
                    'message': 'Login successful',
                    'redirect': redirect_url
                })
            else:
                return jsonify({'success': False, 'message': 'User account not found'})
        else:
            log_audit('otp_verification_failed', 'user', user_id, {
                'phone_number': phone_number,
                'reason': message
            })
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        logging.error(f"Error verifying OTP: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during verification.'})

@otp_bp.route('/send-register-otp', methods=['POST'])
@csrf.exempt
def send_register_otp():
    """Send OTP for registration (allows new phone numbers)"""
    try:
        phone_number = request.form.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({'success': False, 'message': 'Phone number is required'})
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Check if phone number is already registered
        existing_user = User.query.filter_by(phone=phone_number).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Phone number already registered. Please use login instead.'})
        
        # Generate OTP
        otp_code = generate_otp()
        
        # Create OTP verification entry
        otp_verification = OTPVerification.create_otp(formatted_phone, otp_code)
        otp_verification.ip_address = request.remote_addr
        otp_verification.user_agent = request.headers.get('User-Agent', '')[:500]
        
        db.session.add(otp_verification)
        db.session.commit()
        
        # Send OTP via Twilio
        sms_sent = send_twilio_otp(formatted_phone, otp_code)
        
        if sms_sent:
            # Store phone number in session for verification
            session['otp_phone_number'] = formatted_phone
            session['registration_pending'] = True
            session.permanent = True
            
            # Debug logging
            logging.info(f"OTP sent - storing in session: phone={formatted_phone}, pending=True")
            
            log_audit('otp_registration_requested', 'registration', 0, {
                'phone_number': phone_number,
                'formatted_phone': formatted_phone
            })
            
            return jsonify({
                'success': True, 
                'message': f'OTP sent to {phone_number}',
                'masked_phone': f"****{phone_number[-4:]}"
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'})
            
    except Exception as e:
        logging.error(f"Error sending registration OTP: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})

@otp_bp.route('/complete-registration', methods=['POST'])
@csrf.exempt
def complete_registration():
    """Complete user registration after OTP verification"""
    try:
        otp_code = request.form.get('otp_code', '').strip()
        phone_number = session.get('otp_phone_number')
        
        # Debug logging
        logging.info(f"Complete registration attempt - OTP: {otp_code}, Session phone: {phone_number}, Pending: {session.get('registration_pending')}")
        
        if not otp_code:
            return jsonify({'success': False, 'message': 'OTP code is required'})
            
        if not phone_number or not session.get('registration_pending'):
            return jsonify({'success': False, 'message': 'Session expired. Please start registration again.'})
        
        # If session is lost, try to find phone number from recent OTP verification
        if not phone_number:
            # Look for recent OTP verification with this code
            recent_otp = OTPVerification.query.filter_by(
                otp_code=otp_code,
                is_verified=False
            ).filter(
                OTPVerification.expires_at > datetime.utcnow()
            ).first()
            
            if recent_otp:
                phone_number = recent_otp.phone_number
                logging.info(f"Found phone number from OTP verification: {phone_number}")
            
        if not phone_number:
            return jsonify({'success': False, 'message': 'Session expired. Please start registration again.'})
        
        # Verify OTP
        is_valid, message = OTPVerification.verify_otp(phone_number, otp_code)
        
        if not is_valid:
            return jsonify({'success': False, 'message': message})
        
        # Create user account
        from werkzeug.security import generate_password_hash
        
        user = User()
        user.username = request.form.get('phone_number')  # Use phone as username
        user.phone = request.form.get('phone_number')
        user.email = request.form.get('email', '')
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '')
        role = request.form.get('role', 'driver')
        
        if not password:
            return jsonify({'success': False, 'message': 'Password is required'})
        
        user.password_hash = generate_password_hash(password)
        name_parts = full_name.split(' ') if full_name else ['']
        user.first_name = name_parts[0]
        user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Set role
        role_mapping = {
            'driver': UserRole.DRIVER,
            'manager': UserRole.MANAGER,
            'admin': UserRole.ADMIN
        }
        user.role = role_mapping.get(role, UserRole.DRIVER)
        user.status = UserStatus.PENDING  # Needs admin approval
        
        db.session.add(user)
        db.session.commit()
        
        # Clear session data
        session.pop('otp_phone_number', None)
        session.pop('registration_pending', None)
        
        # Login the user
        login_user(user)
        
        log_audit('otp_registration_completed', 'user', user.id, {
            'phone_number': phone_number,
            'role': user.role.value,
            'registration_method': 'otp'
        })
        
        # Redirect based on role
        if user.role == UserRole.ADMIN:
            redirect_url = url_for('admin.dashboard')
        elif user.role == UserRole.MANAGER:
            redirect_url = url_for('manager.dashboard')
        elif user.role == UserRole.DRIVER:
            redirect_url = url_for('driver.dashboard')
        else:
            redirect_url = url_for('auth.login')
        
        return jsonify({
            'success': True, 
            'message': 'Registration successful! Welcome to PLS TRAVELS.',
            'redirect': redirect_url
        })
            
    except Exception as e:
        logging.error(f"Error completing registration: {str(e)}")
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'})

@otp_bp.route('/resend-otp', methods=['POST'])
@csrf.exempt
def resend_otp():
    """Resend OTP to the same phone number"""
    try:
        phone_number = session.get('otp_phone_number')
        user_id = session.get('otp_user_id')
        
        if not phone_number or not user_id:
            return jsonify({'success': False, 'message': 'Session expired. Please start over.'})
        
        # Generate new OTP
        otp_code = generate_otp()
        
        # Create new OTP verification entry
        otp_verification = OTPVerification.create_otp(phone_number, otp_code)
        otp_verification.ip_address = request.remote_addr
        otp_verification.user_agent = request.headers.get('User-Agent', '')[:500]
        
        db.session.add(otp_verification)
        db.session.commit()
        
        # Send OTP via Twilio
        sms_sent = send_twilio_otp(phone_number, otp_code)
        
        if sms_sent:
            log_audit('otp_resent', 'user', user_id, {
                'phone_number': phone_number
            })
            
            return jsonify({
                'success': True, 
                'message': 'New OTP sent successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to resend OTP. Please try again.'})
            
    except Exception as e:
        logging.error(f"Error resending OTP: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})

# Cleanup endpoint for expired OTPs (can be called via cron job)
@otp_bp.route('/cleanup-expired-otps', methods=['POST'])
@login_required
def cleanup_expired_otps():
    """Clean up expired OTP entries - admin only"""
    if not current_user.role == UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        expired_count = OTPVerification.cleanup_expired()
        log_audit('otp_cleanup', 'system', 0, {
            'expired_entries_removed': expired_count
        })
        
        return jsonify({
            'success': True, 
            'message': f'Cleaned up {expired_count} expired OTP entries'
        })
    except Exception as e:
        logging.error(f"Error cleaning up expired OTPs: {str(e)}")
        return jsonify({'success': False, 'message': 'Cleanup failed'})