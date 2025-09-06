from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, VehicleTracking, db,
                   DriverStatus, VehicleStatus, DutyStatus)
from forms import DriverProfileForm, DutyForm
from utils import allowed_file, calculate_earnings
from auth import log_audit

driver_bp = Blueprint('driver', __name__)

def driver_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserRole
        if not current_user.is_authenticated or current_user.role != UserRole.DRIVER:
            flash('Driver access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_driver_profile():
    """Get current driver's profile"""
    if hasattr(current_user, 'driver_profile') and current_user.driver_profile:
        return current_user.driver_profile
    return None

def generate_employee_id():
    """Generate unique employee ID for driver"""
    import random
    import string
    
    while True:
        # Generate format: EMP + 6 digit number
        employee_id = f"EMP{random.randint(100000, 999999)}"
        
        # Check if it already exists
        existing = Driver.query.filter_by(employee_id=employee_id).first()
        if not existing:
            return employee_id

def get_last_duty_values(driver_id, vehicle_id=None):
    """Get odometer values and CNG point from the last completed duty"""
    query = Duty.query.filter_by(driver_id=driver_id, status=DutyStatus.COMPLETED)
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)

    last_duty = query.order_by(desc(Duty.created_at)).first()
    
    # Get most commonly used CNG point for this vehicle
    most_common_cng_point = None
    if vehicle_id:
        cng_usage = db.session.query(VehicleTracking.cng_point, func.count(VehicleTracking.cng_point).label('usage_count')).filter(
            VehicleTracking.vehicle_id == vehicle_id,
            VehicleTracking.cng_point.isnot(None)
        ).group_by(VehicleTracking.cng_point).order_by(desc('usage_count')).first()
        
        if cng_usage:
            most_common_cng_point = cng_usage[0]

    if last_duty:
        return {
            'last_odometer': last_duty.end_odometer,
            'last_duty_date': last_duty.actual_end.strftime('%Y-%m-%d %H:%M') if last_duty.actual_end else None,
            'last_end_cng': last_duty.end_cng,
            'most_common_cng_point': most_common_cng_point,
            'vehicle_current_odometer': Vehicle.query.get(vehicle_id).current_odometer if vehicle_id else None
        }
    return {
        'last_odometer': Vehicle.query.get(vehicle_id).current_odometer if vehicle_id else None,
        'last_duty_date': None,
        'last_end_cng': None,
        'most_common_cng_point': most_common_cng_point,
        'vehicle_current_odometer': Vehicle.query.get(vehicle_id).current_odometer if vehicle_id else None
    }

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
        Duty.status == DutyStatus.ACTIVE
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
            driver.employee_id = generate_employee_id()  # Generate unique employee ID
            driver.full_name = request.form.get('full_name') or ''
            # Phone is stored in User model
            if request.form.get('phone'):
                current_user.phone = request.form.get('phone')
            driver.current_address = request.form.get('address')
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
                    driver.aadhar_document = filename

            if 'license_photo' in request.files:
                file = request.files['license_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"license_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.license_document = filename

            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"profile_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.profile_photo = filename

            try:
                db.session.add(driver)
                db.session.commit()

                log_audit('create_driver_profile', 'driver', driver.id)

                flash('Profile created successfully! Waiting for approval.', 'success')
                return redirect(url_for('driver.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('Error creating profile. Please try again.', 'error')
                return render_template('driver/profile.html', driver=None, branches=branches)

        return render_template('driver/profile.html', driver=None, branches=branches)

    # Update existing profile
    if request.method == 'POST':
        driver.full_name = request.form.get('full_name', driver.full_name)
        # Phone is stored in User model
        if request.form.get('phone'):
            current_user.phone = request.form.get('phone')
        driver.current_address = request.form.get('address', driver.current_address)
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
                    driver.aadhar_document = filename

            if 'license_photo' in request.files:
                file = request.files['license_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"license_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.license_document = filename

            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"profile_{driver.user_id}_{file.filename}")
                    file.save(os.path.join('uploads', filename))
                    driver.profile_photo = filename

        try:
            db.session.commit()

            log_audit('update_driver_profile', 'driver', driver.id)

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('driver.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')

    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('driver/profile.html', driver=driver, branches=branches)

@driver_bp.route('/duty')
@login_required
@driver_required
def duty():
    driver = get_driver_profile()

    if not driver or driver.status != DriverStatus.ACTIVE:
        flash('Your driver profile is not active. Please contact admin.', 'error')
        return redirect(url_for('driver.dashboard'))

    # Check for active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == DutyStatus.ACTIVE
    ).first()

    # Available vehicles in driver's branch
    available_vehicles = Vehicle.query.filter(
        Vehicle.branch_id == driver.branch_id,
        Vehicle.status == VehicleStatus.ACTIVE,
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

    if not driver or driver.status != DriverStatus.ACTIVE:
        flash('Your driver profile is not active.', 'error')
        return redirect(url_for('driver.duty'))

    # Check if already has active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == DutyStatus.ACTIVE
    ).first()

    if active_duty:
        flash('You already have an active duty.', 'error')
        return redirect(url_for('driver.duty'))

    vehicle_id = request.form.get('vehicle_id')
    start_odometer = request.form.get('start_odometer', type=float)

    # Auto-fill from last duty if not provided
    if not start_odometer:
        last_duty_data = get_last_duty_values(driver.id, int(vehicle_id) if vehicle_id else None)
        if last_duty_data['last_odometer']:
            start_odometer = last_duty_data['last_odometer']

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
    duty.status = DutyStatus.ACTIVE

    # Handle start photo
    if 'start_photo' in request.files:
        file = request.files['start_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"duty_start_{duty.driver_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            duty.start_photo = filename

    # Handle start location and timestamp data
    duty.start_latitude = request.form.get('start_latitude', type=float)
    duty.start_longitude = request.form.get('start_longitude', type=float)
    duty.start_location_accuracy = request.form.get('start_location_accuracy', type=float)

    # Parse timestamp if provided
    timestamp_str = request.form.get('start_photo_timestamp')
    if timestamp_str:
        try:
            duty.start_photo_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            duty.start_photo_timestamp = datetime.utcnow()

    # Mark vehicle as not available
    vehicle.is_available = False
    vehicle.current_odometer = start_odometer or 0.0
    driver.current_vehicle_id = vehicle.id

    db.session.add(duty)
    db.session.commit()
    
    # Create vehicle tracking record for duty start
    tracking_record = VehicleTracking()
    tracking_record.vehicle_id = vehicle.id
    tracking_record.duty_id = duty.id
    tracking_record.driver_id = driver.id
    tracking_record.recorded_at = duty.actual_start or datetime.utcnow()
    tracking_record.odometer_reading = start_odometer or 0.0
    tracking_record.odometer_type = 'start'
    tracking_record.source = 'duty'
    tracking_record.latitude = duty.start_location_lat
    tracking_record.longitude = duty.start_location_lng
    tracking_record.location_accuracy = duty.start_location_accuracy
    
    # Calculate distance from previous record
    last_tracking = VehicleTracking.query.filter_by(vehicle_id=vehicle.id).order_by(VehicleTracking.recorded_at.desc()).first()
    if last_tracking and start_odometer:
        tracking_record.distance_traveled = max(0, start_odometer - last_tracking.odometer_reading)
    
    db.session.add(tracking_record)
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
        Duty.status == DutyStatus.ACTIVE
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
    active_duty.status = DutyStatus.COMPLETED

    if end_odometer and active_duty.start_odometer:
        active_duty.distance_km = end_odometer - active_duty.start_odometer

    # Handle end photo
    if 'end_photo' in request.files:
        file = request.files['end_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"duty_end_{driver.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            active_duty.end_photo = filename

    # Handle end location and timestamp data
    active_duty.end_latitude = request.form.get('end_latitude', type=float)
    active_duty.end_longitude = request.form.get('end_longitude', type=float)
    active_duty.end_location_accuracy = request.form.get('end_location_accuracy', type=float)

    # Parse timestamp if provided
    timestamp_str = request.form.get('end_photo_timestamp')
    if timestamp_str:
        try:
            active_duty.end_photo_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            active_duty.end_photo_timestamp = datetime.utcnow()

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

    # Make vehicle available and update current odometer
    if active_duty.vehicle:
        active_duty.vehicle.is_available = True
        active_duty.vehicle.current_odometer = end_odometer or active_duty.vehicle.current_odometer

    driver.current_vehicle_id = None
    
    # Create vehicle tracking record for duty end
    end_tracking_record = VehicleTracking()
    end_tracking_record.vehicle_id = active_duty.vehicle_id
    end_tracking_record.duty_id = active_duty.id
    end_tracking_record.driver_id = driver.id
    end_tracking_record.recorded_at = active_duty.actual_end or datetime.utcnow()
    end_tracking_record.odometer_reading = end_odometer or 0.0
    end_tracking_record.odometer_type = 'end'
    end_tracking_record.source = 'duty'
    end_tracking_record.latitude = active_duty.end_location_lat
    end_tracking_record.longitude = active_duty.end_location_lng
    end_tracking_record.location_accuracy = active_duty.end_location_accuracy
    
    # CNG/fuel tracking data
    end_tracking_record.cng_point = request.form.get('cng_point')
    end_tracking_record.cng_level = request.form.get('end_cng', type=float)
    end_tracking_record.cng_cost = request.form.get('cng_cost', type=float)
    end_tracking_record.cng_quantity = request.form.get('cng_quantity', type=float)
    
    # Calculate distance traveled during this duty
    if end_odometer and active_duty.start_odometer:
        end_tracking_record.distance_traveled = max(0, end_odometer - active_duty.start_odometer)
    
    db.session.add(end_tracking_record)
    db.session.commit()

    log_audit('end_duty', 'duty', active_duty.id,
             {'revenue': active_duty.revenue, 'earnings': active_duty.driver_earnings})

    flash(f'Duty completed! You earned ₹{active_duty.driver_earnings:.2f}', 'success')
    return redirect(url_for('driver.earnings'))


@driver_bp.route('/duty/last-values/<int:vehicle_id>')
@login_required
@driver_required
def get_last_values(vehicle_id):
    """API endpoint to get last duty values for auto-fill"""
    driver = get_driver_profile()

    if not driver:
        return jsonify({'error': 'Driver not found'}), 404

    last_duty_data = get_last_duty_values(driver.id, vehicle_id)
    return jsonify(last_duty_data)

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
        Duty.status == DutyStatus.COMPLETED
    ).order_by(desc(Duty.start_time)).all()

    # Calculate totals
    total_earnings = sum(duty.driver_earnings or 0 for duty in duties)
    total_revenue = sum(duty.revenue or 0 for duty in duties)
    total_bmg = sum(duty.bmg_applied or 0 for duty in duties)
    total_incentive = sum(duty.incentive or 0 for duty in duties)

    # Get penalties in date range
    penalties = Penalty.query.filter(
        Penalty.driver_id == driver.id,
        func.date(Penalty.applied_at) >= start_date_obj,
        func.date(Penalty.applied_at) <= end_date_obj
    ).all()

    total_penalties = sum(penalty.amount or 0 for penalty in penalties)

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
        daily_earning = db.session.query(func.sum(func.coalesce(Duty.driver_earnings, 0))).filter(
            Duty.driver_id == driver.id,
            func.date(Duty.start_time) == date,
            Duty.status == DutyStatus.COMPLETED
        ).scalar() or 0

        days.append(date.strftime('%m/%d'))
        earnings.append(float(daily_earning))

    return jsonify({
        'labels': days,
        'data': earnings
    })