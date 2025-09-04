from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, db)
from forms import DriverProfileForm, DutyForm
from utils import allowed_file, calculate_earnings
from auth import log_audit

driver_bp = Blueprint('driver', __name__)

def driver_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'driver':
            flash('Driver access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_driver_profile():
    """Get current driver's profile"""
    if hasattr(current_user, 'driver_profile') and current_user.driver_profile:
        return current_user.driver_profile
    return None

@driver_bp.route('/dashboard')
@login_required
@driver_required
def dashboard():
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found. Please complete your profile.', 'warning')
        return redirect(url_for('driver.profile'))
    
    # Today's statistics
    today = datetime.now().date()
    
    # Today's duty
    todays_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        func.date(Duty.start_time) == today,
        Duty.status == 'active'
    ).first()
    
    # Today's earnings
    todays_earnings = db.session.query(func.sum(Duty.driver_earnings)).filter(
        Duty.driver_id == driver.id,
        func.date(Duty.start_time) == today
    ).scalar() or 0
    
    # This month's earnings
    start_of_month = datetime.now().replace(day=1).date()
    monthly_earnings = db.session.query(func.sum(Duty.driver_earnings)).filter(
        Duty.driver_id == driver.id,
        func.date(Duty.start_time) >= start_of_month
    ).scalar() or 0
    
    # Recent duties
    recent_duties = Duty.query.filter(
        Duty.driver_id == driver.id
    ).order_by(desc(Duty.start_time)).limit(5).all()
    
    # Pending penalties
    pending_penalties = Penalty.query.filter_by(driver_id=driver.id).all()
    
    return render_template('driver/dashboard.html',
                         driver=driver,
                         todays_duty=todays_duty,
                         todays_earnings=todays_earnings,
                         monthly_earnings=monthly_earnings,
                         recent_duties=recent_duties,
                         pending_penalties=pending_penalties)

@driver_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@driver_required
def profile():
    driver = get_driver_profile()
    
    # Create driver profile if doesn't exist
    if not driver:
        branches = Branch.query.filter_by(is_active=True).all()
        if request.method == 'POST':
            # Create new driver profile
            driver = Driver()
            driver.user_id = current_user.id
            driver.full_name = request.form.get('full_name') or ''
            driver.phone = request.form.get('phone') or ''
            driver.address = request.form.get('address')
            branch_id_str = request.form.get('branch_id')
            driver.branch_id = int(branch_id_str) if branch_id_str and branch_id_str.isdigit() else None
            driver.aadhar_number = request.form.get('aadhar_number')
            driver.license_number = request.form.get('license_number')
            driver.bank_name = request.form.get('bank_name')
            driver.account_number = request.form.get('account_number')
            driver.ifsc_code = request.form.get('ifsc_code')
            driver.account_holder_name = request.form.get('account_holder_name')
            
            # Handle file uploads
            if 'aadhar_photo' in request.files:
                file = request.files['aadhar_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"aadhar_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.aadhar_photo = filename
            
            if 'license_photo' in request.files:
                file = request.files['license_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"license_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.license_photo = filename
            
            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"profile_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.profile_photo = filename
            
            db.session.add(driver)
            db.session.commit()
            
            log_audit('create_driver_profile', 'driver', driver.id)
            
            flash('Profile created successfully! Waiting for approval.', 'success')
            return redirect(url_for('driver.dashboard'))
        
        return render_template('driver/profile.html', driver=None, branches=branches)
    
    # Update existing profile
    if request.method == 'POST':
        driver.full_name = request.form.get('full_name', driver.full_name)
        driver.phone = request.form.get('phone', driver.phone)
        driver.address = request.form.get('address', driver.address)
        driver.bank_name = request.form.get('bank_name', driver.bank_name)
        driver.account_number = request.form.get('account_number', driver.account_number)
        driver.ifsc_code = request.form.get('ifsc_code', driver.ifsc_code)
        driver.account_holder_name = request.form.get('account_holder_name', driver.account_holder_name)
        
        # Handle file uploads if driver is not yet approved
        if driver.status in ['pending', 'rejected']:
            if 'aadhar_photo' in request.files:
                file = request.files['aadhar_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"aadhar_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.aadhar_photo = filename
            
            if 'license_photo' in request.files:
                file = request.files['license_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"license_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.license_photo = filename
            
            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"profile_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.profile_photo = filename
        
        db.session.commit()
        
        log_audit('update_driver_profile', 'driver', driver.id)
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('driver.profile'))
    
    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('driver/profile.html', driver=driver, branches=branches)

@driver_bp.route('/duty')
@login_required
@driver_required
def duty():
    driver = get_driver_profile()
    
    if not driver or driver.status != 'active':
        flash('Your driver profile is not active. Please contact admin.', 'error')
        return redirect(url_for('driver.dashboard'))
    
    # Check for active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == 'active'
    ).first()
    
    # Available vehicles in driver's branch
    available_vehicles = Vehicle.query.filter(
        Vehicle.branch_id == driver.branch_id,
        Vehicle.status == 'active',
        Vehicle.is_available == True
    ).all()
    
    return render_template('driver/duty.html',
                         driver=driver,
                         active_duty=active_duty,
                         available_vehicles=available_vehicles)

@driver_bp.route('/duty/start', methods=['POST'])
@login_required
@driver_required
def start_duty():
    driver = get_driver_profile()
    
    if not driver or driver.status != 'active':
        flash('Your driver profile is not active.', 'error')
        return redirect(url_for('driver.duty'))
    
    # Check if already has active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == 'active'
    ).first()
    
    if active_duty:
        flash('You already have an active duty.', 'error')
        return redirect(url_for('driver.duty'))
    
    vehicle_id = request.form.get('vehicle_id')
    start_odometer = request.form.get('start_odometer', type=float)
    
    if not vehicle_id:
        flash('Please select a vehicle.', 'error')
        return redirect(url_for('driver.duty'))
    
    vehicle = Vehicle.query.filter(
        Vehicle.id == vehicle_id,
        Vehicle.branch_id == driver.branch_id,
        Vehicle.is_available == True
    ).first()
    
    if not vehicle:
        flash('Selected vehicle is not available.', 'error')
        return redirect(url_for('driver.duty'))
    
    # Get default duty scheme for branch
    duty_scheme = DutyScheme.query.filter(
        DutyScheme.branch_id == driver.branch_id,
        DutyScheme.is_active == True
    ).first()
    
    if not duty_scheme:
        # Get global scheme
        duty_scheme = DutyScheme.query.filter(
            DutyScheme.branch_id.is_(None),
            DutyScheme.is_active == True
        ).first()
    
    # Create new duty
    duty = Duty()
    duty.driver_id = driver.id
    duty.vehicle_id = vehicle.id
    duty.branch_id = driver.branch_id
    duty.duty_scheme_id = duty_scheme.id if duty_scheme else None
    duty.start_time = datetime.utcnow()
    duty.start_odometer = start_odometer or 0.0
    duty.status = 'active'
    
    # Handle start photo
    if 'start_photo' in request.files:
        file = request.files['start_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"duty_start_{duty.driver_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            duty.start_photo = filename
    
    # Mark vehicle as not available
    vehicle.is_available = False
    driver.current_vehicle_id = vehicle.id
    
    db.session.add(duty)
    db.session.commit()
    
    log_audit('start_duty', 'duty', duty.id,
             {'vehicle': vehicle.registration_number, 'odometer': start_odometer})
    
    flash('Duty started successfully!', 'success')
    return redirect(url_for('driver.duty'))

@driver_bp.route('/duty/end', methods=['POST'])
@login_required
@driver_required
def end_duty():
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.duty'))
    
    # Get active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == 'active'
    ).first()
    
    if not active_duty:
        flash('No active duty found.', 'error')
        return redirect(url_for('driver.duty'))
    
    # Get financial data from form
    end_odometer = request.form.get('end_odometer', type=float)
    trip_count = request.form.get('trip_count', type=int, default=0)
    fuel_amount = request.form.get('fuel_amount', type=float, default=0.0)
    
    # Comprehensive financial data
    active_duty.cash_collected = request.form.get('cash_collected', type=float, default=0.0)
    active_duty.qr_payment = request.form.get('qr_payment', type=float, default=0.0)
    active_duty.outside_cash = request.form.get('outside_cash', type=float, default=0.0)
    active_duty.operator_bill = request.form.get('operator_bill', type=float, default=0.0)
    active_duty.toll = request.form.get('toll', type=float, default=0.0)
    active_duty.petrol_expenses = request.form.get('petrol_expenses', type=float, default=0.0)
    active_duty.gas_expenses = request.form.get('gas_expenses', type=float, default=0.0)
    active_duty.other_expenses = request.form.get('other_expenses', type=float, default=0.0)
    active_duty.company_pay = request.form.get('company_pay', type=float, default=0.0)
    active_duty.advance = request.form.get('advance', type=float, default=0.0)
    active_duty.driver_expenses = request.form.get('driver_expenses', type=float, default=0.0)
    active_duty.pass_deduction = request.form.get('pass_deduction', type=float, default=0.0)
    
    # Update basic duty info
    active_duty.end_time = datetime.utcnow()
    active_duty.end_odometer = end_odometer
    active_duty.trip_count = trip_count
    active_duty.fuel_amount = fuel_amount
    active_duty.status = 'completed'
    
    if end_odometer and active_duty.start_odometer:
        active_duty.distance_km = end_odometer - active_duty.start_odometer
    
    # Handle end photo
    if 'end_photo' in request.files:
        file = request.files['end_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"duty_end_{driver.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            active_duty.end_photo = filename
    
    # Calculate comprehensive tripsheet
    from utils import calculate_tripsheet
    tripsheet_result = calculate_tripsheet(active_duty)
    
    # Update all calculated fields
    active_duty.revenue = tripsheet_result['company_earnings']
    active_duty.driver_earnings = tripsheet_result['driver_salary']
    active_duty.company_expenses = tripsheet_result['company_expenses']
    active_duty.company_profit = tripsheet_result['company_profit']
    active_duty.incentive = tripsheet_result['incentive']
    
    # Update driver total earnings
    driver.total_earnings += active_duty.driver_earnings
    
    # Make vehicle available
    if active_duty.vehicle:
        active_duty.vehicle.is_available = True
    
    driver.current_vehicle_id = None
    
    db.session.commit()
    
    log_audit('end_duty', 'duty', active_duty.id,
             {'revenue': active_duty.revenue, 'earnings': active_duty.driver_earnings})
    
    flash(f'Duty completed! You earned ₹{active_duty.driver_earnings:.2f}', 'success')
    return redirect(url_for('driver.earnings'))

@driver_bp.route('/earnings')
@login_required
@driver_required
def earnings():
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    # Date range filter
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = (datetime.now() - timedelta(days=30)).date()
        end_date_obj = datetime.now().date()
    
    # Get duties in date range
    duties = Duty.query.filter(
        Duty.driver_id == driver.id,
        func.date(Duty.start_time) >= start_date_obj,
        func.date(Duty.start_time) <= end_date_obj,
        Duty.status == 'completed'
    ).order_by(desc(Duty.start_time)).all()
    
    # Calculate totals
    total_earnings = sum(duty.driver_earnings for duty in duties)
    total_revenue = sum(duty.revenue for duty in duties)
    total_bmg = sum(duty.bmg_applied for duty in duties)
    total_incentive = sum(duty.incentive for duty in duties)
    
    # Get penalties in date range
    penalties = Penalty.query.filter(
        Penalty.driver_id == driver.id,
        func.date(Penalty.applied_at) >= start_date_obj,
        func.date(Penalty.applied_at) <= end_date_obj
    ).all()
    
    total_penalties = sum(penalty.amount for penalty in penalties)
    
    return render_template('driver/earnings.html',
                         driver=driver,
                         duties=duties,
                         penalties=penalties,
                         total_earnings=total_earnings,
                         total_revenue=total_revenue,
                         total_bmg=total_bmg,
                         total_incentive=total_incentive,
                         total_penalties=total_penalties,
                         start_date=start_date,
                         end_date=end_date)

@driver_bp.route('/api/earnings-chart')
@login_required
@driver_required
def earnings_chart():
    driver = get_driver_profile()
    
    if not driver:
        return jsonify({'error': 'Driver not found'}), 404
    
    # Get last 7 days earnings
    days = []
    earnings = []
    
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        daily_earning = db.session.query(func.sum(Duty.driver_earnings)).filter(
            Duty.driver_id == driver.id,
            func.date(Duty.start_time) == date,
            Duty.status == 'completed'
        ).scalar() or 0
        
        days.append(date.strftime('%m/%d'))
        earnings.append(float(daily_earning))
    
    return jsonify({
        'labels': days,
        'data': earnings
    })
