from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from models import db, User, OTPVerification, UserRole, Driver
from utils.twilio_otp import generate_otp, send_twilio_otp, format_phone_number
from auth import log_audit
import logging
from datetime import datetime

otp_bp = Blueprint('otp', __name__)

@otp_bp.route('/login/otp')
def otp_login():
    """OTP login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth/otp_login.html')

@otp_bp.route('/send-otp', methods=['POST'])
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
            # Check in Driver table as well
            driver = Driver.query.filter_by(phone_number=phone_number).first()
            if driver and driver.user:
                user = driver.user
        
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
                    redirect_url = url_for('dashboard')
                
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

@otp_bp.route('/resend-otp', methods=['POST'])
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