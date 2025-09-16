from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf.csrf import validate_csrf
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, timedelta
from timezone_utils import get_ist_time_naive
from sqlalchemy import func, desc
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, VehicleTracking, VehicleAssignment, db,
                   DriverStatus, VehicleStatus, DutyStatus, AssignmentStatus, ResignationRequest, ResignationStatus,
                   TrackingSession, AdvancePaymentRequest)
from forms import DriverProfileForm, DutyForm
from utils import (allowed_file, calculate_earnings, calculate_advanced_salary, 
                   process_file_upload, process_camera_capture, calculate_tripsheet)
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
        vehicle = Vehicle.query.get(vehicle_id) if vehicle_id else None
        return {
            'last_odometer': last_duty.end_odometer,
            'last_duty_date': last_duty.actual_end.strftime('%Y-%m-%d %H:%M') if last_duty.actual_end else None,
            'last_end_cng': last_duty.end_cng,
            'most_common_cng_point': most_common_cng_point,
            'vehicle_current_odometer': vehicle.current_odometer if vehicle else None
        }
    vehicle = Vehicle.query.get(vehicle_id) if vehicle_id else None
    return {
        'last_odometer': vehicle.current_odometer if vehicle else None,
        'last_duty_date': None,
        'last_end_cng': None,
        'most_common_cng_point': most_common_cng_point,
        'vehicle_current_odometer': vehicle.current_odometer if vehicle else None
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
            
            # Generate unique employee ID - ensure it's not None
            from utils import generate_employee_id
            employee_id = generate_employee_id()
            if not employee_id:
                flash('Error generating employee ID. Please try again.', 'error')
                return render_template('driver/profile.html', driver=None, branches=branches)
            
            driver.employee_id = employee_id
            driver.full_name = request.form.get('full_name') or current_user.email
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

            # Handle additional phone numbers
            additional_phones = []
            for i in range(1, 4):  # additional_phone_1, additional_phone_2, additional_phone_3
                phone_field = f'additional_phone_{i}'
                phone = request.form.get(phone_field, '').strip()
                if phone:
                    additional_phones.append(phone)
            
            driver.set_additional_phones(additional_phones)

            # Enhanced file upload handling with cloud storage
            # Process Aadhar photo
            aadhar_filename, aadhar_metadata = process_camera_capture(
                request.form, 'aadhar_photo', driver.user_id, 'aadhar', use_cloud=True
            )
            if aadhar_filename:
                driver.aadhar_document = aadhar_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'aadhar_photo' in request.files:
                file = request.files['aadhar_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'aadhar', use_cloud=True)
                    if cloud_url:
                        driver.aadhar_document = cloud_url

            # Process License photo
            license_filename, license_metadata = process_camera_capture(
                request.form, 'license_photo', driver.user_id, 'license', use_cloud=True
            )
            if license_filename:
                driver.license_document = license_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'license_photo' in request.files:
                file = request.files['license_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'license', use_cloud=True)
                    if cloud_url:
                        driver.license_document = cloud_url

            # Process Profile photo
            profile_filename, profile_metadata = process_camera_capture(
                request.form, 'profile_photo', driver.user_id, 'profile', use_cloud=True
            )
            if profile_filename:
                driver.profile_photo = profile_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'profile', use_cloud=True)
                    if cloud_url:
                        driver.profile_photo = cloud_url

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

    # Fetch additional data for profile display
    # Get all duties with details
    all_duties = Duty.query.filter_by(driver_id=driver.id).order_by(desc(Duty.start_time)).all()
    
    # Calculate financial summary
    total_earnings = db.session.query(func.sum(Duty.driver_earnings)).filter_by(driver_id=driver.id).scalar() or 0
    total_advances = db.session.query(func.sum(Duty.advance_deduction)).filter_by(driver_id=driver.id).scalar() or 0
    total_deductions = db.session.query(
        func.sum(Duty.advance_deduction + Duty.fuel_deduction + Duty.penalty_deduction)
    ).filter_by(driver_id=driver.id).scalar() or 0
    
    # Recent financial transactions (from duties)
    recent_transactions = Duty.query.filter(
        Duty.driver_id == driver.id,
        (Duty.advance_deduction > 0) | (Duty.fuel_deduction > 0) | (Duty.penalty_deduction > 0)
    ).order_by(desc(Duty.start_time)).limit(10).all()

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

        # Handle additional phone numbers
        additional_phones = []
        for i in range(1, 4):  # additional_phone_1, additional_phone_2, additional_phone_3
            phone_field = f'additional_phone_{i}'
            phone = request.form.get(phone_field, '').strip()
            if phone:
                additional_phones.append(phone)
        
        driver.set_additional_phones(additional_phones)

        # Enhanced file upload handling with cloud storage (only if driver is not yet approved)
        if driver.status in ['pending', 'rejected']:
            # Process Aadhar photo
            aadhar_filename, aadhar_metadata = process_camera_capture(
                request.form, 'aadhar_photo', driver.user_id, 'aadhar', use_cloud=True
            )
            if aadhar_filename:
                driver.aadhar_document = aadhar_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'aadhar_photo' in request.files:
                file = request.files['aadhar_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'aadhar', use_cloud=True)
                    if cloud_url:
                        driver.aadhar_document = cloud_url

            # Process License photo
            license_filename, license_metadata = process_camera_capture(
                request.form, 'license_photo', driver.user_id, 'license', use_cloud=True
            )
            if license_filename:
                driver.license_document = license_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'license_photo' in request.files:
                file = request.files['license_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'license', use_cloud=True)
                    if cloud_url:
                        driver.license_document = cloud_url

            # Process Profile photo
            profile_filename, profile_metadata = process_camera_capture(
                request.form, 'profile_photo', driver.user_id, 'profile', use_cloud=True
            )
            if profile_filename:
                driver.profile_photo = profile_filename
            
            # Fallback to traditional file upload if no camera capture
            elif 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file:
                    cloud_url = process_file_upload(file, driver.user_id, 'profile', use_cloud=True)
                    if cloud_url:
                        driver.profile_photo = cloud_url

        try:
            db.session.commit()

            log_audit('update_driver_profile', 'driver', driver.id)

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('driver.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')

    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('driver/profile.html', 
                         driver=driver, 
                         branches=branches,
                         all_duties=all_duties,
                         total_earnings=total_earnings,
                         total_advances=total_advances,
                         total_deductions=total_deductions,
                         recent_transactions=recent_transactions)

@driver_bp.route('/api/vehicle-last-duty/<int:vehicle_id>')
@login_required
@driver_required
def get_vehicle_last_duty(vehicle_id):
    """API endpoint to get last duty values for a vehicle"""
    driver = get_driver_profile()
    if not driver:
        return jsonify({'error': 'Driver profile not found'}), 404
    
    # Verify vehicle belongs to driver's branch
    vehicle = Vehicle.query.filter_by(
        id=vehicle_id, 
        branch_id=driver.branch_id,
        is_available=True
    ).first()
    
    if not vehicle:
        return jsonify({'error': 'Vehicle not found or not available'}), 404
    
    # Get last duty values
    last_duty_data = get_last_duty_values(driver.id, vehicle_id)
    
    return jsonify({
        'success': True,
        'vehicle_registration': vehicle.registration_number,
        'last_odometer': last_duty_data['last_odometer'],
        'vehicle_current_odometer': last_duty_data['vehicle_current_odometer'],
        'suggested_start_odometer': last_duty_data['vehicle_current_odometer'] or last_duty_data['last_odometer'],
        'last_duty_date': last_duty_data['last_duty_date'],
        'last_end_cng': last_duty_data['last_end_cng'],
        'most_common_cng_point': last_duty_data['most_common_cng_point'],
        'continuity_check': {
            'status': 'ok' if last_duty_data['vehicle_current_odometer'] else 'warning',
            'message': 'Auto-filled from vehicle\'s last duty' if last_duty_data['vehicle_current_odometer'] else 'No previous duty found'
        }
    })

@driver_bp.route('/duty')
@login_required
@driver_required
def duty():
    driver = get_driver_profile()

    if not driver or driver.status not in [DriverStatus.ACTIVE, DriverStatus.PENDING]:
        flash('Your driver profile has been rejected or suspended. Please contact admin.', 'error')
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

    # Available duty schemes (global and branch-specific)
    available_schemes = DutyScheme.query.filter(
        DutyScheme.is_active == True,
        (DutyScheme.branch_id == driver.branch_id) | (DutyScheme.branch_id.is_(None))
    ).order_by(DutyScheme.is_default.desc(), DutyScheme.name).all()

    return render_template('driver/duty.html',
                         driver=driver,
                         active_duty=active_duty,
                         available_vehicles=available_vehicles,
                         available_schemes=available_schemes)

@driver_bp.route('/duty/start', methods=['POST'])
@login_required
@driver_required
def start_duty():
    driver = get_driver_profile()

    if not driver or driver.status not in [DriverStatus.ACTIVE, DriverStatus.PENDING]:
        flash('Your driver profile has been rejected or suspended. Please contact admin.', 'error')
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
    start_cng_level = request.form.get('start_cng_level', type=float)

    if not vehicle_id:
        flash('Please select a vehicle.', 'error')
        return redirect(url_for('driver.duty'))

    # Get last duty data for validation and auto-fill
    last_duty_data = get_last_duty_values(driver.id, int(vehicle_id))
    
    # Validate odometer reading continuity
    if start_odometer and last_duty_data['vehicle_current_odometer']:
        # Check if start reading is less than vehicle's current odometer
        if start_odometer < last_duty_data['vehicle_current_odometer']:
            flash(f'Invalid odometer reading. Vehicle last reading was {last_duty_data["vehicle_current_odometer"]} km. New reading cannot be less than this.', 'error')
            return redirect(url_for('driver.duty'))
        
        # Warning if reading differs significantly from expected
        expected_reading = last_duty_data['vehicle_current_odometer']
        if abs(start_odometer - expected_reading) > 50:  # More than 50 km difference
            flash(f'Warning: Odometer reading differs significantly from expected value ({expected_reading} km). Please verify the reading is correct.', 'warning')
    
    # Auto-fill from last duty if not provided
    if not start_odometer:
        if last_duty_data['vehicle_current_odometer']:
            start_odometer = last_duty_data['vehicle_current_odometer']
        elif last_duty_data['last_odometer']:
            start_odometer = last_duty_data['last_odometer']
    
    if not start_odometer:
        flash('Please enter a valid starting odometer reading.', 'error')
        return redirect(url_for('driver.duty'))
    
    # Validate CNG level if provided
    if start_cng_level is not None:
        if not (0.0 <= start_cng_level <= 10.0):
            flash('Please select a valid CNG level between 0 and 10 bars.', 'error')
            return redirect(url_for('driver.duty'))
    else:
        # Default to last end CNG level if available, otherwise 10 bars (full tank assumption)
        if last_duty_data and 'last_end_cng' in last_duty_data and last_duty_data['last_end_cng']:
            start_cng_level = last_duty_data['last_end_cng']
        else:
            start_cng_level = 10.0  # Assume full tank for new drivers

    vehicle = Vehicle.query.filter(
        Vehicle.id == vehicle_id,
        Vehicle.branch_id == driver.branch_id,
        Vehicle.is_available == True
    ).first()

    if not vehicle:
        flash('Selected vehicle is not available.', 'error')
        return redirect(url_for('driver.duty'))

    # Automatically select the default duty scheme for the driver's branch
    # Priority 1: Branch-specific default scheme
    duty_scheme = DutyScheme.query.filter_by(
        branch_id=driver.branch_id, 
        is_active=True, 
        is_default=True
    ).first()
    
    # Priority 2: Global default scheme
    if not duty_scheme:
        duty_scheme = DutyScheme.query.filter_by(
            branch_id=None,  # Global schemes
            is_active=True, 
            is_default=True
        ).first()
    
    # Priority 3: Any branch-specific active scheme
    if not duty_scheme:
        duty_scheme = DutyScheme.query.filter_by(
            branch_id=driver.branch_id, 
            is_active=True
        ).first()
    
    # Priority 4: Any global active scheme
    if not duty_scheme:
        duty_scheme = DutyScheme.query.filter_by(
            branch_id=None,  # Global schemes
            is_active=True
        ).first()
    
    if not duty_scheme:
        flash('No duty scheme available. Please contact your manager.', 'error')
        return redirect(url_for('driver.duty'))

    # Create new duty
    duty = Duty()
    duty.driver_id = driver.id
    duty.vehicle_id = vehicle.id
    duty.branch_id = driver.branch_id
    duty.duty_scheme_id = duty_scheme.id
    duty.actual_start = get_ist_time_naive()
    duty.start_odometer = start_odometer or 0.0
    duty.start_cng = start_cng_level or 0.0  # Store the starting CNG level
    duty.status = DutyStatus.ACTIVE

    # Handle start photo camera capture
    start_photo_filename, start_photo_metadata = process_camera_capture(
        request.form, 'start_photo', driver.id, 'duty_start'
    )
    if start_photo_filename:
        duty.start_photo = start_photo_filename
    
    # Fallback to traditional file upload if no camera capture
    elif 'start_photo' in request.files:
        file = request.files['start_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"duty_start_{duty.driver_id}_{get_ist_time_naive().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join('uploads', filename))
            duty.start_photo = filename

    # Location data removed per user request
    duty.start_location_lat = None
    duty.start_location_lng = None
    duty.start_location_accuracy = None

    # Note: Photo timestamp metadata is handled in process_camera_capture function
    # No need to set separate timestamp fields as they don't exist in the model

    # Mark vehicle as not available
    vehicle.is_available = False
    vehicle.current_odometer = start_odometer or 0.0
    driver.current_vehicle_id = vehicle.id

    db.session.add(duty)
    db.session.commit()
    
    # Create GPS tracking session for the duty
    tracking_session = TrackingSession(
        duty_id=duty.id,
        driver_id=driver.id,
        device_info='{"source": "web", "platform": "desktop"}',
        app_version='web-1.0'
    )
    db.session.add(tracking_session)
    db.session.commit()
    
    # Create vehicle tracking record for duty start
    tracking_record = VehicleTracking()
    tracking_record.vehicle_id = vehicle.id
    tracking_record.duty_id = duty.id
    tracking_record.driver_id = driver.id
    tracking_record.recorded_at = duty.actual_start or get_ist_time_naive()
    tracking_record.odometer_reading = start_odometer or 0.0
    tracking_record.odometer_type = 'start'
    tracking_record.source = 'duty'
    tracking_record.latitude = None
    tracking_record.longitude = None
    tracking_record.location_accuracy = None
    
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
    try:
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
        active_duty.cash_collection = request.form.get('cash_collected', type=float, default=0.0)
        active_duty.qr_payment = request.form.get('qr_payment', type=float, default=0.0)
        active_duty.digital_payments = request.form.get('outside_cash', type=float, default=0.0)
        active_duty.operator_out = request.form.get('operator_bill', type=float, default=0.0)
        active_duty.toll_expense = request.form.get('toll', type=float, default=0.0)
        active_duty.fuel_expense = request.form.get('petrol_expenses', type=float, default=0.0)
        active_duty.other_expenses = request.form.get('gas_expenses', type=float, default=0.0)
        active_duty.maintenance_expense = request.form.get('other_expenses', type=float, default=0.0)
        active_duty.company_pay = request.form.get('company_pay', type=float, default=0.0)
        active_duty.advance_deduction = request.form.get('advance', type=float, default=0.0)
        active_duty.fuel_deduction = request.form.get('driver_expenses', type=float, default=0.0)
        active_duty.penalty_deduction = request.form.get('pass_deduction', type=float, default=0.0)

        # Update basic duty info
        active_duty.actual_end = get_ist_time_naive()
        active_duty.end_odometer = end_odometer
        active_duty.total_trips = trip_count
        active_duty.fuel_consumed = fuel_amount
        active_duty.status = DutyStatus.PENDING_APPROVAL
        active_duty.submitted_at = get_ist_time_naive()

        if end_odometer and active_duty.start_odometer:
            active_duty.total_distance = end_odometer - active_duty.start_odometer

        # Handle end photo camera capture
        end_photo_filename, end_photo_metadata = process_camera_capture(
            request.form, 'end_photo', driver.id, 'duty_end'
        )
        if end_photo_filename:
            active_duty.end_photo = end_photo_filename
        
        # Fallback to traditional file upload if no camera capture
        elif 'end_photo' in request.files:
            file = request.files['end_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"duty_end_{driver.id}_{get_ist_time_naive().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join('uploads', filename))
                active_duty.end_photo = filename

        # Location data removed per user request
        active_duty.end_location_lat = None
        active_duty.end_location_lng = None
        active_duty.end_location_accuracy = None

        # Calculate comprehensive tripsheet
        tripsheet_result = calculate_tripsheet(active_duty)

        # Update all calculated fields
        active_duty.gross_revenue = tripsheet_result['company_earnings']
        active_duty.driver_earnings = tripsheet_result['driver_salary']
        active_duty.company_profit = tripsheet_result['company_profit']
        active_duty.incentive_payment = tripsheet_result['incentive']

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
        end_tracking_record.recorded_at = active_duty.actual_end or get_ist_time_naive()
        end_tracking_record.odometer_reading = end_odometer or 0.0
        end_tracking_record.odometer_type = 'end'
        end_tracking_record.source = 'duty'
        end_tracking_record.latitude = None
        end_tracking_record.longitude = None
        end_tracking_record.location_accuracy = None
        
        # CNG/fuel tracking data with bar calculation
        start_cng_bars = request.form.get('start_cng', type=float)
        end_cng_bars = request.form.get('end_cng', type=float)
        cng_point = request.form.get('cng_point')
        
        # Store CNG data in duty record
        active_duty.start_cng = start_cng_bars
        active_duty.end_cng = end_cng_bars  
        active_duty.cng_point = cng_point
        
        # Calculate CNG charges/payments (₹90 per bar)
        cng_adjustment = 0.0
        if start_cng_bars and end_cng_bars:
            bar_difference = end_cng_bars - start_cng_bars
            cng_adjustment = bar_difference * 90  # ₹90 per bar
            
            # Apply CNG adjustment to duty record
            if cng_adjustment < 0:
                # Driver consumed CNG - deduct from driver
                active_duty.fuel_deduction = (active_duty.fuel_deduction or 0) + abs(cng_adjustment)
            elif cng_adjustment > 0:
                # Driver filled CNG - company pays driver
                active_duty.bonus_payment = (active_duty.bonus_payment or 0) + cng_adjustment
        
        end_tracking_record.cng_point = cng_point
        end_tracking_record.cng_level = end_cng_bars
        end_tracking_record.cng_cost = cng_adjustment
        end_tracking_record.cng_quantity = abs(bar_difference) if start_cng_bars and end_cng_bars else 0.0
        
        # Calculate distance traveled during this duty
        if end_odometer and active_duty.start_odometer:
            end_tracking_record.distance_traveled = max(0, end_odometer - active_duty.start_odometer)
        
        db.session.add(end_tracking_record)
        
        # End GPS tracking session when duty ends
        active_tracking_session = TrackingSession.query.filter_by(
            duty_id=active_duty.id,
            driver_id=driver.id,
            is_active=True
        ).first()
        
        if active_tracking_session:
            active_tracking_session.is_active = False
            active_tracking_session.session_end = get_ist_time_naive()
            active_tracking_session.duration = int((active_tracking_session.session_end - active_tracking_session.session_start).total_seconds())
        
        db.session.commit()

        log_audit('end_duty', 'duty', active_duty.id,
                 {'revenue': active_duty.gross_revenue, 'earnings': active_duty.driver_earnings})

        flash(f'Duty submitted for approval! Expected earnings: ₹{active_duty.driver_earnings:.2f}. Please wait for admin approval.', 'info')
        return redirect(url_for('driver.earnings'))
    
    except Exception as e:
        import traceback
        error_message = str(e)
        print(f"ERROR in end_duty: {error_message}")
        print("Full traceback:")
        traceback.print_exc()
        db.session.rollback()
        flash(f'Debug Error: {error_message}', 'error')
        return redirect(url_for('driver.duty'))


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
    total_bmg = 0  # BMG applied data not stored in Duty model
    total_incentive = sum(duty.incentive_payment or 0 for duty in duties)

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

# === ADVANCE PAYMENT REQUEST ENDPOINTS ===

@driver_bp.route('/advance-payment/request', methods=['POST'])
@login_required
@driver_required
def request_advance_payment():
    """Request advance payment during active duty"""
    from whatsapp_utils import send_advance_payment_request
    
    driver = get_driver_profile()
    if not driver:
        return jsonify({'error': 'Driver profile not found'}), 404
    
    # Get current active duty
    active_duty = Duty.query.filter_by(
        driver_id=driver.id,
        status=DutyStatus.ACTIVE
    ).first()
    
    if not active_duty:
        return jsonify({'error': 'No active duty found'}), 400
    
    try:
        # CSRF protection for JSON endpoint
        csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({'error': 'CSRF token missing'}), 400
        
        try:
            validate_csrf(csrf_token)
        except Exception:
            return jsonify({'error': 'Invalid CSRF token'}), 400
        
        data = request.get_json()
        amount = float(data.get('amount', 0))
        purpose = data.get('purpose', 'fuel')
        notes = data.get('notes', '')
        location_lat = data.get('latitude')
        location_lng = data.get('longitude')
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        if amount > 5000:  # Set reasonable limit
            return jsonify({'error': 'Amount exceeds maximum limit of ₹5,000'}), 400
        
        # Send WhatsApp request to admins
        result = send_advance_payment_request(
            duty_id=active_duty.id,
            driver_id=driver.id,
            amount=amount,
            purpose=purpose,
            notes=notes,
            location_lat=location_lat,
            location_lng=location_lng
        )
        
        if result['success']:
            log_audit('request_advance_payment', 'advance_payment_request', result['request_id'],
                     {'amount': amount, 'purpose': purpose})
            
            return jsonify({
                'success': True,
                'message': 'Advance payment request sent to admin',
                'request_id': result['request_id'],
                'sent_to_admins': result['message_sent_to']
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(f"Error requesting advance payment: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500

@driver_bp.route('/advance-payment/pending')
@login_required
@driver_required
def get_pending_advance_requests():
    """Get pending advance payment requests for current driver"""
    from whatsapp_utils import get_pending_advance_requests
    
    driver = get_driver_profile()
    if not driver:
        return jsonify({'error': 'Driver profile not found'}), 404
    
    try:
        pending_requests = get_pending_advance_requests(driver.id)
        return jsonify({
            'success': True,
            'requests': pending_requests
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch requests'}), 500

@driver_bp.route('/advance-payment/<int:request_id>/status')
@login_required
@driver_required
def get_advance_request_status(request_id):
    """Get status of specific advance payment request"""
    driver = get_driver_profile()
    if not driver:
        return jsonify({'error': 'Driver profile not found'}), 404
    
    try:
        advance_request = AdvancePaymentRequest.query.filter_by(
            id=request_id,
            driver_id=driver.id
        ).first()
        
        if not advance_request:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify({
            'success': True,
            'request': {
                'id': advance_request.id,
                'amount_requested': advance_request.amount_requested,
                'approved_amount': advance_request.approved_amount,
                'purpose': advance_request.purpose,
                'status': advance_request.status,
                'notes': advance_request.notes,
                'response_notes': advance_request.response_notes,
                'created_at': advance_request.created_at.strftime('%Y-%m-%d %H:%M'),
                'responded_at': advance_request.responded_at.strftime('%Y-%m-%d %H:%M') if advance_request.responded_at else None
            }
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch request status'}), 500


@driver_bp.route('/ledger')
@login_required
@driver_required
def financial_ledger():
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    # Date range filter with default to last 3 months
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    transaction_type = request.args.get('type', 'all')  # all, earnings, deductions, advances
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = (datetime.now() - timedelta(days=90)).date()
        end_date_obj = datetime.now().date()
    
    # Get all duties in date range
    duties = Duty.query.filter(
        Duty.driver_id == driver.id,
        func.date(Duty.start_time) >= start_date_obj,
        func.date(Duty.start_time) <= end_date_obj
    ).order_by(Duty.start_time).all()
    
    # Get penalties in date range
    penalties = Penalty.query.filter(
        Penalty.driver_id == driver.id,
        func.date(Penalty.applied_at) >= start_date_obj,
        func.date(Penalty.applied_at) <= end_date_obj
    ).order_by(Penalty.applied_at).all()
    
    # Create comprehensive transaction ledger
    transactions = []
    running_balance = 0.0
    
    # Process all duties to create detailed transactions
    for duty in duties:
        duty_date = duty.start_time.date() if duty.start_time else datetime.now().date()
        
        # Earnings transactions
        if duty.driver_earnings and duty.driver_earnings > 0:
            running_balance += duty.driver_earnings
            transactions.append({
                'date': duty_date,
                'time': duty.start_time.strftime('%H:%M') if duty.start_time else '',
                'type': 'EARNINGS',
                'description': f'Duty Earnings - {duty.vehicle.registration_number if duty.vehicle else "N/A"}',
                'reference': f'DUTY-{duty.id}',
                'debit': 0,
                'credit': duty.driver_earnings,
                'balance': running_balance,
                'details': {
                    'company_pay': duty.company_pay or 0,
                    'incentive': (duty.cash_collection or 0) - (duty.operator_out or 0) if (duty.cash_collection or 0) > (duty.operator_out or 0) else 0,
                    'total_revenue': duty.total_revenue or 0,
                    'duty_id': duty.id
                }
            })
        
        # Advance deductions
        if duty.advance_deduction and duty.advance_deduction > 0:
            running_balance -= duty.advance_deduction
            transactions.append({
                'date': duty_date,
                'time': duty.start_time.strftime('%H:%M') if duty.start_time else '',
                'type': 'ADVANCE',
                'description': f'Advance Deduction - {duty.vehicle.registration_number if duty.vehicle else "N/A"}',
                'reference': f'ADV-{duty.id}',
                'debit': duty.advance_deduction,
                'credit': 0,
                'balance': running_balance,
                'details': {
                    'duty_id': duty.id,
                    'amount': duty.advance_deduction
                }
            })
        
        # Fuel deductions
        if duty.fuel_deduction and duty.fuel_deduction > 0:
            running_balance -= duty.fuel_deduction
            transactions.append({
                'date': duty_date,
                'time': duty.start_time.strftime('%H:%M') if duty.start_time else '',
                'type': 'FUEL_DEDUCTION',
                'description': f'Fuel Deduction - {duty.vehicle.registration_number if duty.vehicle else "N/A"}',
                'reference': f'FUEL-{duty.id}',
                'debit': duty.fuel_deduction,
                'credit': 0,
                'balance': running_balance,
                'details': {
                    'duty_id': duty.id,
                    'amount': duty.fuel_deduction
                }
            })
        
        # Penalty deductions
        if duty.penalty_deduction and duty.penalty_deduction > 0:
            running_balance -= duty.penalty_deduction
            transactions.append({
                'date': duty_date,
                'time': duty.start_time.strftime('%H:%M') if duty.start_time else '',
                'type': 'PENALTY',
                'description': f'Penalty Deduction - {duty.vehicle.registration_number if duty.vehicle else "N/A"}',
                'reference': f'PEN-{duty.id}',
                'debit': duty.penalty_deduction,
                'credit': 0,
                'balance': running_balance,
                'details': {
                    'duty_id': duty.id,
                    'amount': duty.penalty_deduction
                }
            })
    
    # Add penalty transactions
    for penalty in penalties:
        penalty_date = penalty.applied_at.date() if penalty.applied_at else datetime.now().date()
        running_balance -= penalty.amount
        transactions.append({
            'date': penalty_date,
            'time': penalty.applied_at.strftime('%H:%M') if penalty.applied_at else '',
            'type': 'PENALTY',
            'description': f'Penalty - {penalty.reason}',
            'reference': f'PENALTY-{penalty.id}',
            'debit': penalty.amount,
            'credit': 0,
            'balance': running_balance,
            'details': {
                'penalty_id': penalty.id,
                'reason': penalty.reason,
                'amount': penalty.amount
            }
        })
    
    # Sort transactions by date and time
    transactions.sort(key=lambda x: (x['date'], x['time']))
    
    # Recalculate running balance in chronological order
    balance = 0.0
    for transaction in transactions:
        balance += transaction['credit'] - transaction['debit']
        transaction['balance'] = balance
    
    # Apply transaction type filter
    if transaction_type != 'all':
        if transaction_type == 'earnings':
            transactions = [t for t in transactions if t['type'] == 'EARNINGS']
        elif transaction_type == 'deductions':
            transactions = [t for t in transactions if t['type'] in ['FUEL_DEDUCTION', 'PENALTY']]
        elif transaction_type == 'advances':
            transactions = [t for t in transactions if t['type'] == 'ADVANCE']
    
    # Calculate summary statistics
    total_credits = sum(t['credit'] for t in transactions)
    total_debits = sum(t['debit'] for t in transactions)
    net_amount = total_credits - total_debits
    
    # Transaction type counts
    transaction_counts = {
        'earnings': len([t for t in transactions if t['type'] == 'EARNINGS']),
        'advances': len([t for t in transactions if t['type'] == 'ADVANCE']),
        'deductions': len([t for t in transactions if t['type'] in ['FUEL_DEDUCTION', 'PENALTY']]),
        'penalties': len([t for t in transactions if t['type'] == 'PENALTY'])
    }
    
    return render_template('driver/ledger.html',
                         driver=driver,
                         transactions=transactions,
                         total_credits=total_credits,
                         total_debits=total_debits,
                         net_amount=net_amount,
                         transaction_counts=transaction_counts,
                         start_date=start_date,
                         end_date=end_date,
                         transaction_type=transaction_type)

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

# Resignation Management Routes
@driver_bp.route('/resign', methods=['GET', 'POST'])
@login_required
@driver_required
def resign():
    """Submit resignation request"""
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    # Check if driver already has a pending or approved resignation
    existing_resignation = ResignationRequest.query.filter_by(
        driver_id=driver.id
    ).filter(
        ResignationRequest.status.in_([ResignationStatus.PENDING, ResignationStatus.APPROVED])
    ).first()
    
    if existing_resignation:
        flash('You already have a pending resignation request.', 'warning')
        return redirect(url_for('driver.resignation_status'))
    
    if request.method == 'POST':
        reason = request.form.get('reason')
        detailed_reason = request.form.get('detailed_reason')
        preferred_last_working_date = request.form.get('preferred_last_working_date')
        
        if not all([reason, preferred_last_working_date]):
            flash('Please provide all required information.', 'error')
            return render_template('driver/resign.html', driver=driver)
        
        try:
            preferred_date = datetime.strptime(preferred_last_working_date, '%Y-%m-%d').date()
            
            # Ensure preferred date is at least 30 days from today
            min_date = datetime.now().date() + timedelta(days=30)
            if preferred_date < min_date:
                flash('Preferred last working date must be at least 30 days from today.', 'error')
                return render_template('driver/resign.html', driver=driver)
            
            # Create resignation request
            resignation_request = ResignationRequest()
            resignation_request.driver_id = driver.id
            resignation_request.reason = reason
            resignation_request.detailed_reason = detailed_reason
            resignation_request.preferred_last_working_date = preferred_date
            resignation_request.status = ResignationStatus.PENDING
            
            db.session.add(resignation_request)
            db.session.commit()
            
            log_audit('submit_resignation', 'resignation', resignation_request.id,
                     {'driver_name': driver.full_name, 'reason': reason})
            
            flash('Your resignation request has been submitted successfully. HR will review and respond within 3-5 business days.', 'success')
            return redirect(url_for('driver.resignation_status'))
            
        except ValueError:
            flash('Invalid date format.', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Error submitting resignation request. Please try again.', 'error')
    
    return render_template('driver/resign.html', driver=driver)

@driver_bp.route('/resignation-status')
@login_required
@driver_required
def resignation_status():
    """View resignation request status"""
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    # Get all resignation requests for this driver
    resignation_requests = ResignationRequest.query.filter_by(
        driver_id=driver.id
    ).order_by(desc(ResignationRequest.submitted_at)).all()
    
    return render_template('driver/resignation_status.html', 
                         driver=driver, 
                         resignation_requests=resignation_requests)

@driver_bp.route('/cancel-resignation/<int:request_id>', methods=['POST'])
@login_required
@driver_required
def cancel_resignation(request_id):
    """Cancel a pending resignation request"""
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    resignation_request = ResignationRequest.query.filter_by(
        id=request_id,
        driver_id=driver.id,
        status=ResignationStatus.PENDING
    ).first()
    
    if not resignation_request:
        flash('Resignation request not found or cannot be cancelled.', 'error')
        return redirect(url_for('driver.resignation_status'))
    
    resignation_request.status = ResignationStatus.CANCELLED
    db.session.commit()
    
    log_audit('cancel_resignation', 'resignation', resignation_request.id,
             {'driver_name': driver.full_name})
    
    flash('Your resignation request has been cancelled.', 'info')
    return redirect(url_for('driver.resignation_status'))

@driver_bp.route('/vehicles/<int:vehicle_id>/documents/<document_type>')
@login_required
@driver_required
def serve_vehicle_document(vehicle_id, document_type):
    """Serve vehicle document files with proper driver authorization"""
    driver = get_driver_profile()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('driver.profile'))
    
    # Validate document type against whitelist
    allowed_document_types = {'registration', 'insurance', 'fitness', 'permit', 'pollution', 'other'}
    if document_type not in allowed_document_types:
        return "Invalid document type", 400
    
    # Get the vehicle
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Check if driver is currently assigned to this vehicle or has active duty with it
    from datetime import datetime
    active_assignment = VehicleAssignment.query.filter_by(
        driver_id=driver.id,
        vehicle_id=vehicle_id,
        status=AssignmentStatus.ACTIVE
    ).first()
    
    active_duty = Duty.query.filter_by(
        driver_id=driver.id,
        vehicle_id=vehicle_id,
        status=DutyStatus.ACTIVE
    ).first()
    
    if not active_assignment and not active_duty:
        return "Access denied - You are not assigned to this vehicle", 403
    
    # Get document filename based on type
    document_field_map = {
        'registration': vehicle.registration_document,
        'insurance': vehicle.insurance_document,
        'fitness': vehicle.fitness_document,
        'permit': vehicle.permit_document,
        'pollution': vehicle.pollution_document,
        'other': vehicle.other_document
    }
    
    filename = document_field_map[document_type]
    if not filename:
        return "Document not found", 404
    
    # Serve the file securely
    import os
    from flask import send_from_directory
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    file_path = os.path.join(upload_dir, filename)
    
    # Security check - ensure file is within upload directory and exists
    if not file_path.startswith(upload_dir + os.sep) and file_path != upload_dir:
        return "Access denied", 403
        
    if not os.path.exists(file_path):
        return "File not found", 404
        
    return send_from_directory(upload_dir, filename)