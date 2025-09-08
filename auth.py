from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Branch, db, AuditLog
from forms import LoginForm, RegisterForm
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
    if current_user.is_authenticated:
        from models import UserRole
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == UserRole.MANAGER:
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('driver.dashboard'))
    
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
            log_audit('login_success')
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect based on role
            from models import UserRole
            if user.role == UserRole.ADMIN:
                return redirect(url_for('admin.dashboard'))
            elif user.role == UserRole.MANAGER:
                return redirect(url_for('manager.dashboard'))
            else:
                return redirect(url_for('driver.dashboard'))
        else:
            # Increment failed attempts
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                db.session.commit()
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html', form=form)

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
        from models import UserRole, Driver, DriverStatus
        role_str = form.role.data if form.role.data else 'driver'
        user.role = UserRole.ADMIN if role_str == 'admin' else UserRole.MANAGER if role_str == 'manager' else UserRole.DRIVER
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # If registering as driver, create driver profile
        if user.role == UserRole.DRIVER:
            driver = Driver()
            driver.user_id = user.id
            driver.full_name = form.full_name.data
            driver.phone = form.phone.data
            driver.additional_phone_1 = form.additional_phone_1.data
            driver.additional_phone_2 = form.additional_phone_2.data
            driver.additional_phone_3 = form.additional_phone_3.data
            driver.address = form.address.data
            driver.date_of_birth = form.date_of_birth.data
            driver.aadhar_number = form.aadhar_number.data
            driver.license_number = form.license_number.data
            driver.bank_name = form.bank_name.data
            driver.account_number = form.account_number.data
            driver.ifsc_code = form.ifsc_code.data
            driver.account_holder_name = form.account_holder_name.data
            driver.branch_id = form.branch.data
            driver.status = DriverStatus.PENDING  # Default to pending approval
            
            # Handle file uploads
            from utils import process_file_upload
            if form.aadhar_photo.data:
                aadhar_url = process_file_upload(form.aadhar_photo.data, user.id, 'aadhar', use_cloud=True)
                if aadhar_url:
                    driver.aadhar_document = aadhar_url
            
            if form.license_photo.data:
                license_url = process_file_upload(form.license_photo.data, user.id, 'license', use_cloud=True)
                if license_url:
                    driver.license_document = license_url
                    
            if form.profile_photo.data:
                profile_url = process_file_upload(form.profile_photo.data, user.id, 'profile', use_cloud=True)
                if profile_url:
                    driver.profile_photo = profile_url
            
            db.session.add(driver)
        
        # If registering as manager, assign branch
        elif user.role == UserRole.MANAGER and form.branch.data:
            branch = Branch.query.get(form.branch.data)
            if branch:
                user.managed_branches.append(branch)
        
        db.session.commit()
        
        flash('Registration successful! Your profile has been submitted for admin approval.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit('logout')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
