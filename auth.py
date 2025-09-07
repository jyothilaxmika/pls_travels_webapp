from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Branch, db, AuditLog
from forms import LoginForm, RegisterForm, OTPRequestForm, OTPVerifyForm
import json

auth_bp = Blueprint('auth', __name__)

def log_audit(action, entity_type=None, entity_id=None, details=None):
    """Helper function to log audit events"""
    if current_user.is_authenticated:
        audit = AuditLog()
        audit.user_id = current_user.id
        audit.action = action
        audit.entity_type = entity_type
        audit.entity_id = entity_id
        audit.new_values = json.dumps(details) if details else None
        audit.ip_address = request.remote_addr
        audit.user_agent = request.headers.get('User-Agent', '')[:255]
        db.session.add(audit)
        db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect authenticated users to their dashboard
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    # Show OTP login form by default
    return redirect(url_for('auth.otp_login'))

@auth_bp.route('/otp-login', methods=['GET', 'POST'])
def otp_login():
    """OTP-based login using phone number"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    form = OTPRequestForm()
    if form.validate_on_submit():
        phone_number = form.phone_number.data
        
        # Check if user exists with this phone number
        from models import Driver
        driver = Driver.query.filter_by(phone=phone_number).first()
        if not driver:
            # Check additional phone fields
            driver = Driver.query.filter(
                (Driver.additional_phone_1 == phone_number) |
                (Driver.additional_phone_2 == phone_number) |
                (Driver.additional_phone_3 == phone_number)
            ).first()
        
        if not driver or not driver.user:
            flash('No account found with this phone number.', 'error')
            return render_template('auth/otp_login.html', form=form)
        
        # Check if user is active
        if driver.user.status.name != 'ACTIVE':
            flash('Your account is not active. Please contact administrator.', 'error')
            return render_template('auth/otp_login.html', form=form)
        
        # Send OTP
        from otp_service import send_otp_sms
        result = send_otp_sms(phone_number)
        
        if result['success']:
            flash(f'OTP sent to {phone_number}. Please check your messages.', 'success')
            return redirect(url_for('auth.verify_otp', phone=phone_number))
        else:
            flash(result['message'], 'error')
    
    return render_template('auth/otp_login.html', form=form)

@auth_bp.route('/verify-otp/<phone>', methods=['GET', 'POST'])
def verify_otp(phone):
    """Verify OTP code and complete login"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    form = OTPVerifyForm()
    form.phone_number.data = phone
    
    if form.validate_on_submit():
        phone_number = form.phone_number.data
        otp_code = form.otp_code.data
        
        # Verify OTP
        from otp_service import verify_otp_code
        result = verify_otp_code(phone_number, otp_code)
        
        if result['success']:
            # Find user by phone number
            from models import Driver
            driver = Driver.query.filter_by(phone=phone_number).first()
            if not driver:
                # Check additional phone fields
                driver = Driver.query.filter(
                    (Driver.additional_phone_1 == phone_number) |
                    (Driver.additional_phone_2 == phone_number) |
                    (Driver.additional_phone_3 == phone_number)
                ).first()
            
            if driver and driver.user:
                # Login the user
                login_user(driver.user, remember=form.remember_me.data)
                
                # Update last login
                from datetime import datetime
                driver.user.last_login = datetime.utcnow()
                driver.user.login_count = (driver.user.login_count or 0) + 1
                driver.user.failed_login_attempts = 0
                db.session.commit()
                
                # Log successful login
                log_audit('otp_login_success')
                
                flash(f'Welcome back, {driver.user.full_name}!', 'success')
                return redirect_to_dashboard()
            else:
                flash('Account not found. Please contact administrator.', 'error')
        else:
            flash(result['message'], 'error')
    
    # Get OTP status for display
    from otp_service import get_otp_status
    otp_status = get_otp_status(phone)
    
    return render_template('auth/verify_otp.html', form=form, phone=phone, otp_status=otp_status)

@auth_bp.route('/resend-otp/<phone>', methods=['POST'])
def resend_otp(phone):
    """Resend OTP code"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    from otp_service import send_otp_sms
    result = send_otp_sms(phone)
    
    if result['success']:
        flash('New OTP sent successfully.', 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('auth.verify_otp', phone=phone))

def redirect_to_dashboard():
    """Helper function to redirect users to their role-specific dashboard"""
    from models import UserRole
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == UserRole.MANAGER:
        return redirect(url_for('manager.dashboard'))
    else:
        return redirect(url_for('driver.dashboard'))

@auth_bp.route('/legacy-login', methods=['GET', 'POST'])
def legacy_login():
    """Legacy password-based login (kept for admin access)"""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.status.name == 'ACTIVE' and user.password_hash and form.password.data and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            
            # Update last login
            from datetime import datetime
            user.last_login = datetime.utcnow()
            user.login_count = (user.login_count or 0) + 1
            user.failed_login_attempts = 0
            db.session.commit()
            
            # Log successful login
            log_audit('legacy_login_success')
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect_to_dashboard()
        else:
            # Increment failed attempts
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                db.session.commit()
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/legacy_login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    form.branch.choices = [(b.id, b.name) for b in Branch.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists.', 'error')
            return render_template('auth/register.html', form=form)
        
        # Create new user
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.password_hash = generate_password_hash(form.password.data) if form.password.data else ''
        # Convert string role to UserRole enum
        from models import UserRole
        role_str = form.role.data if form.role.data else 'driver'
        user.role = UserRole.ADMIN if role_str == 'admin' else UserRole.MANAGER if role_str == 'manager' else UserRole.DRIVER
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # If registering as manager, assign branch
        if user.role == UserRole.MANAGER and form.branch.data:
            branch = Branch.query.get(form.branch.data)
            if branch:
                user.managed_branches.append(branch)
        
        db.session.commit()
        
        flash('Registration successful! Please wait for admin approval.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit('logout')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
