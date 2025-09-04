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
        audit.details = json.dumps(details) if details else None
        audit.ip_address = request.remote_addr
        audit.user_agent = request.headers.get('User-Agent', '')[:255]
        db.session.add(audit)
        db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'manager':
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('driver.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.active and user.password_hash and form.password.data and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            
            # Log successful login
            log_audit('login_success')
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('manager.dashboard'))
            else:
                return redirect(url_for('driver.dashboard'))
        else:
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
        user.role = form.role.data if form.role.data else 'driver'
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # If registering as manager, assign branch
        if form.role.data == 'manager' and form.branch.data:
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
