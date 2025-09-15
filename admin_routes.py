from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from functools import wraps
import os
import math
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_, and_
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, VehicleAssignment, VehicleType, VehicleTracking, 
                   UberSyncJob, UberSyncLog, UberIntegrationSettings, db, AssignmentTemplate, Photo, PhotoType,
                   DriverStatus, VehicleStatus, DutyStatus, AssignmentStatus, ResignationRequest, ResignationStatus, UserRole, UserStatus)
from forms import DriverForm, VehicleForm, DutySchemeForm, VehicleAssignmentForm, ScheduledAssignmentForm, QuickAssignmentForm, AssignmentTemplateForm
from utils_main import allowed_file, calculate_earnings, process_file_upload, process_camera_capture
import json
from timezone_utils import get_ist_time_naive

# Import scheduling functions after initial imports
try:
    from utils.scheduling import (check_assignment_conflicts, generate_assignment_suggestions,
                                build_assignment_calendar, create_bulk_assignments, create_recurring_assignments)
except ImportError:
    # Fallback functions if module not available
    def check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, shift_type):
        return {'driver_conflict': None, 'vehicle_conflict': None}
    
    def generate_assignment_suggestions(driver_id, vehicle_id, start_date, end_date, shift_type):
        return []
        
    def build_assignment_calendar(assignments, start_date_str, end_date_str):
        return {}
        
    def create_bulk_assignments(assignments_data, assigned_by_user_id):
        return {'success': False, 'created_count': 0, 'errors': ['Function not available']}
        
    def create_recurring_assignments(base_assignment_data, pattern, until_date, assigned_by_user_id):
        return {'success': False, 'created_count': 0, 'errors': ['Function not available']}
from auth import log_audit
from recommendation_engine import recommendation_engine

admin_bp = Blueprint('admin', __name__)

def safe_float_conversion(value, default=0.0):
    """Safely convert a value to float, preventing NaN injection"""
    if value is None:
        return default
    try:
        result = float(value)
        if not math.isfinite(result):
            return default
        return result
    except (ValueError, TypeError):
        return default

def create_default_vehicle_types():
    """Create default vehicle types if they don't exist"""
    default_types = [
        {'name': 'CAB', 'category': 'Commercial', 'capacity_passengers': 4, 'fuel_type': 'CNG'},
        {'name': 'Taxi', 'category': 'Commercial', 'capacity_passengers': 4, 'fuel_type': 'CNG'},
        {'name': 'Auto Rickshaw', 'category': 'Commercial', 'capacity_passengers': 3, 'fuel_type': 'CNG'},
        {'name': 'Bus', 'category': 'Public', 'capacity_passengers': 40, 'fuel_type': 'Diesel'},
        {'name': 'Mini Bus', 'category': 'Commercial', 'capacity_passengers': 20, 'fuel_type': 'Diesel'},
        {'name': 'Truck', 'category': 'Commercial', 'capacity_passengers': 2, 'fuel_type': 'Diesel'}
    ]
    
    for vtype_data in default_types:
        existing = VehicleType.query.filter_by(name=vtype_data['name']).first()
        if not existing:
            vtype = VehicleType()
            vtype.name = vtype_data['name']
            vtype.category = vtype_data['category']
            vtype.capacity_passengers = vtype_data['capacity_passengers']
            vtype.fuel_type = vtype_data['fuel_type']
            vtype.is_active = True
            db.session.add(vtype)
    
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

def create_default_branch():
    """Create a default branch if none exist"""
    if Branch.query.filter_by(is_active=True).count() == 0:
        default_branch = Branch()
        default_branch.name = "Main Branch"
        default_branch.code = "MAIN"
        default_branch.address = "Main Office"
        default_branch.city = "City"
        default_branch.contact_phone = "0000000000"
        default_branch.is_active = True
        # Note: is_head_office attribute not available in Branch model
        
        try:
            db.session.add(default_branch)
            db.session.commit()
        except Exception:
            db.session.rollback()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserRole
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get overall statistics with optimized queries
    from models import DriverStatus, VehicleStatus, DutyStatus
    
    # Separate simpler queries for counts
    total_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).count()
    total_vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE).count()
    total_branches = Branch.query.filter_by(is_active=True).count()
    
    # Active duties today with simple queries
    today = datetime.now().date()
    active_duties = Duty.query.filter(
        and_(func.date(Duty.start_time) == today, Duty.status == DutyStatus.ACTIVE)
    ).count()
    pending_duties = Duty.query.filter_by(status=DutyStatus.PENDING_APPROVAL).count()
    
    # Revenue statistics with limited results
    revenue_stats = db.session.query(
        Branch.name,
        Branch.target_revenue,
        func.coalesce(func.sum(Duty.revenue), 0).label('actual_revenue')
    ).outerjoin(Duty, func.date(Duty.start_time) == today) \
     .filter(Branch.is_active == True) \
     .group_by(Branch.id, Branch.name, Branch.target_revenue) \
     .limit(20).all()
    
    # Recent activities - limit and optimize
    recent_activities = AuditLog.query.options(
        db.joinedload(AuditLog.user)
    ).order_by(desc(AuditLog.created_at)).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_drivers=total_drivers,
                         total_vehicles=total_vehicles,
                         total_branches=total_branches,
                         active_duties=active_duties,
                         pending_duties=pending_duties,
                         revenue_stats=revenue_stats,
                         recent_activities=recent_activities)

@admin_bp.route('/drivers')
@login_required
@admin_required
def drivers():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    branch_filter = request.args.get('branch', '', type=int)
    
    query = Driver.query
    
    if status_filter:
        try:
            status_enum = DriverStatus(status_filter)
            query = query.filter(Driver.status == status_enum)
        except ValueError:
            # Invalid status filter, ignore it
            pass
    
    if branch_filter:
        query = query.filter(Driver.branch_id == branch_filter)
    
    drivers = query.paginate(page=page, per_page=20, error_out=False)
    branches = Branch.query.filter_by(is_active=True).all()
    
    return render_template('admin/drivers.html', 
                         drivers=drivers, 
                         branches=branches,
                         status_filter=status_filter,
                         branch_filter=branch_filter)

@admin_bp.route('/drivers/<int:driver_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.status = DriverStatus.ACTIVE
    driver.approved_by = current_user.id
    driver.approved_at = get_ist_time_naive()
    
    # Activate user account
    driver.user.active = True
    
    db.session.commit()
    
    log_audit('approve_driver', 'driver', driver_id, 
             {'driver_name': driver.full_name, 'branch': driver.branch.name if driver.branch else 'Unknown'})
    
    flash(f'Driver {driver.full_name} has been approved.', 'success')
    return redirect(url_for('admin.drivers'))

@admin_bp.route('/drivers/<int:driver_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.status = DriverStatus.REJECTED
    driver.approved_by = current_user.id
    driver.approved_at = get_ist_time_naive()
    
    db.session.commit()
    
    log_audit('reject_driver', 'driver', driver_id,
             {'driver_name': driver.full_name, 'branch': driver.branch.name if driver.branch else 'Unknown'})
    
    flash(f'Driver {driver.full_name} has been rejected.', 'warning')
    return redirect(url_for('admin.drivers'))

@admin_bp.route('/drivers/<int:driver_id>/view')
@login_required
@admin_required
def view_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    
    # Get driver's recent duties (all duties)
    all_duties = Duty.query.filter_by(driver_id=driver_id).order_by(desc(Duty.created_at)).all()
    recent_duties = all_duties[:10]  # Show top 10 for recent section
    
    # Get driver's penalties
    penalties = Penalty.query.filter_by(driver_id=driver_id).order_by(desc(Penalty.applied_at)).all()
    
    # Get driver's assets
    assets = Asset.query.filter_by(driver_id=driver_id).all()
    
    # Get vehicle assignments
    assignments = VehicleAssignment.query.filter_by(driver_id=driver_id).order_by(desc(VehicleAssignment.start_date)).all()
    
    # Calculate comprehensive statistics
    total_duties = len(all_duties)
    total_earnings = sum(duty.driver_earnings or 0 for duty in all_duties)
    total_penalties = sum(penalty.amount or 0 for penalty in penalties)
    net_earnings = total_earnings - total_penalties
    
    # Active duty statistics
    active_duties = [d for d in all_duties if d.status == DutyStatus.ACTIVE]
    completed_duties = [d for d in all_duties if d.status == DutyStatus.COMPLETED]
    
    # Monthly breakdown (last 6 months)
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    six_months_ago = datetime.now() - timedelta(days=180)
    recent_duties_for_stats = [d for d in all_duties if d.created_at and d.created_at >= six_months_ago]
    
    monthly_stats = defaultdict(lambda: {'duties': 0, 'earnings': 0, 'trips': 0})
    for duty in recent_duties_for_stats:
        month_key = duty.created_at.strftime('%Y-%m')
        monthly_stats[month_key]['duties'] += 1
        monthly_stats[month_key]['earnings'] += duty.driver_earnings or 0
        monthly_stats[month_key]['trips'] += duty.total_trips or 0
    
    return render_template('admin/driver_details.html', 
                         driver=driver, 
                         recent_duties=recent_duties,
                         all_duties=all_duties,
                         penalties=penalties,
                         assets=assets,
                         assignments=assignments,
                         total_duties=total_duties,
                         total_earnings=total_earnings,
                         total_penalties=total_penalties,
                         net_earnings=net_earnings,
                         active_duties=len(active_duties),
                         completed_duties=len(completed_duties),
                         monthly_stats=dict(monthly_stats))

# Document Management Routes
@admin_bp.route('/drivers/documents/add', methods=['POST'])
@login_required
@admin_required
def add_driver_document():
    """Add a new document for a driver"""
    driver_id = request.form.get('driver_id')
    document_type = request.form.get('document_type')
    document_number = request.form.get('document_number')
    notes = request.form.get('notes')
    
    if not driver_id or not document_type:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    driver = Driver.query.get_or_404(driver_id)
    
    # Handle file upload
    if 'document_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    
    file = request.files['document_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{driver_id}_{document_type}_{timestamp}_{filename}"
        
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Update driver document fields
        if document_type == 'aadhar':
            # Handle legacy uploads - map to front document for now
            driver.aadhar_document_front = filename
            if document_number:
                driver.aadhar_number = document_number
        elif document_type == 'license':
            # Handle legacy uploads - map to front document for now
            driver.license_document_front = filename
            if document_number:
                driver.license_number = document_number
        elif document_type == 'profile':
            driver.profile_photo = filename
        
        try:
            db.session.commit()
            log_audit('add_driver_document', 'driver', driver_id,
                     {'document_type': document_type, 'filename': filename})
            return jsonify({'success': True, 'message': 'Document added successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@admin_bp.route('/drivers/<int:driver_id>/documents/<document_type>', methods=['DELETE'])
@login_required
@admin_required
def delete_driver_document(driver_id, document_type):
    """Delete a driver's document"""
    driver = Driver.query.get_or_404(driver_id)
    
    # Collect all filenames to delete
    files_to_delete = []
    
    if document_type == 'aadhar':
        # Handle deletion of both front and back documents
        if driver.aadhar_document_front:
            files_to_delete.append(driver.aadhar_document_front)
        if driver.aadhar_document_back:
            files_to_delete.append(driver.aadhar_document_back)
        driver.aadhar_document_front = None
        driver.aadhar_document_back = None
        driver.aadhar_verified = False
        driver.aadhar_verified_at = None
    elif document_type == 'license':
        # Handle deletion of both front and back documents
        if driver.license_document_front:
            files_to_delete.append(driver.license_document_front)
        if driver.license_document_back:
            files_to_delete.append(driver.license_document_back)
        driver.license_document_front = None
        driver.license_document_back = None
        driver.license_verified = False
        driver.license_verified_at = None
    elif document_type == 'profile':
        if driver.profile_photo:
            files_to_delete.append(driver.profile_photo)
        driver.profile_photo = None
    
    # Delete all physical files
    deleted_files = []
    for filename in files_to_delete:
        if filename:
            file_path = os.path.join(os.getcwd(), 'uploads', filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                except OSError as e:
                    # Log but don't fail the entire operation
                    flash(f'Warning: Could not delete file {filename}: {str(e)}', 'warning')
    
    try:
        db.session.commit()
        log_audit('delete_driver_document', 'driver', driver_id,
                 {'document_type': document_type, 'deleted_files': deleted_files})
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_bp.route('/drivers/<int:driver_id>/documents/<document_type>/verify', methods=['POST'])
@login_required
@admin_required
def verify_driver_document(driver_id, document_type):
    """Mark a driver's document as verified"""
    driver = Driver.query.get_or_404(driver_id)
    
    if document_type == 'aadhar':
        driver.aadhar_verified = True
        driver.aadhar_verified_at = datetime.utcnow()
    elif document_type == 'license':
        driver.license_verified = True
        driver.license_verified_at = datetime.utcnow()
    
    try:
        db.session.commit()
        log_audit('verify_driver_document', 'driver', driver_id,
                 {'document_type': document_type, 'verified_by': current_user.username})
        return jsonify({'success': True, 'message': 'Document verified successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_bp.route('/drivers/<int:driver_id>/documents/<document_type>/unverify', methods=['POST'])
@login_required
@admin_required
def unverify_driver_document(driver_id, document_type):
    """Mark a driver's document as unverified"""
    driver = Driver.query.get_or_404(driver_id)
    
    if document_type == 'aadhar':
        driver.aadhar_verified = False
        driver.aadhar_verified_at = None
    elif document_type == 'license':
        driver.license_verified = False
        driver.license_verified_at = None
    
    try:
        db.session.commit()
        log_audit('unverify_driver_document', 'driver', driver_id,
                 {'document_type': document_type, 'unverified_by': current_user.username})
        return jsonify({'success': True, 'message': 'Document marked as unverified'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

# Financial Transaction Management Routes
@admin_bp.route('/transactions/add', methods=['POST'])
@login_required
@admin_required
def add_manual_transaction():
    """Add a manual financial transaction for a driver"""
    driver_id = request.form.get('driver_id')
    transaction_type = request.form.get('transaction_type')
    amount = request.form.get('amount')
    description = request.form.get('description')
    reference = request.form.get('reference')
    transaction_date = request.form.get('transaction_date')
    
    if not all([driver_id, transaction_type, amount, description]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    try:
        # Use safe conversion to prevent NaN/infinity injection
        amount = safe_float_conversion(amount)
        if amount == 0.0 and request.form.get('amount') not in ['0', '0.0', '0.00']:
            return jsonify({'success': False, 'message': 'Invalid amount value'})
        # Additional check: ensure amount is not zero for financial transactions
        if amount == 0:
            return jsonify({'success': False, 'message': 'Transaction amount cannot be zero'})
        if transaction_date:
            trans_date = datetime.strptime(transaction_date, '%Y-%m-%d').date()
        else:
            trans_date = datetime.now().date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid amount or date format'})
    
    driver = Driver.query.get_or_404(driver_id)
    
    # Create manual transaction record based on type
    if transaction_type == 'penalty':
        penalty = Penalty()
        penalty.driver_id = driver_id
        penalty.amount = amount
        penalty.reason = description
        penalty.applied_by = current_user.id
        penalty.applied_at = datetime.combine(trans_date, datetime.min.time())
        # Note: reference stored in reason field as reference_number not available
        if reference:
            penalty.reason = f"{description} (Ref: {reference})"
        db.session.add(penalty)
        
        # Update driver totals
        driver.total_penalties = (driver.total_penalties or 0) + amount
        
    else:
        # For other transaction types, we'll need a generic Transaction model
        # For now, create penalty-like records with different types
        penalty = Penalty()
        penalty.driver_id = driver_id
        if transaction_type in ['advance', 'deduction']:
            penalty.amount = amount  # Debit
        else:
            penalty.amount = -amount  # Credit (bonus, reimbursement)
        penalty.reason = f"{(transaction_type or 'UNKNOWN').upper()}: {description}"
        penalty.applied_by = current_user.id
        penalty.applied_at = datetime.combine(trans_date, datetime.min.time())
        # Note: reference stored in reason field as reference_number not available
        if reference:
            penalty.reason = f"{penalty.reason} (Ref: {reference})"
        db.session.add(penalty)
        
        # Update driver totals
        if transaction_type in ['advance', 'deduction']:
            driver.total_penalties = (driver.total_penalties or 0) + amount
        else:
            driver.total_earnings = (driver.total_earnings or 0) + amount
    
    try:
        db.session.commit()
        log_audit('add_manual_transaction', 'driver', driver_id,
                 {'type': transaction_type, 'amount': amount, 'description': description})
        return jsonify({'success': True, 'message': 'Transaction added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_bp.route('/transactions/<transaction_type>/<int:transaction_id>', methods=['DELETE'])
@login_required
@admin_required
def remove_transaction(transaction_type, transaction_id):
    """Remove a financial transaction"""
    if transaction_type == 'penalty':
        transaction = Penalty.query.get_or_404(transaction_id)
        driver = Driver.query.get(transaction.driver_id)
        
        # Update driver totals
        if driver:
            driver.total_penalties = max(0, (driver.total_penalties or 0) - transaction.amount)
        
        db.session.delete(transaction)
    elif transaction_type == 'duty':
        # Don't allow deletion of duty earnings - return error
        return jsonify({'success': False, 'message': 'Cannot delete duty earnings. Edit the duty instead.'})
    
    try:
        db.session.commit()
        log_audit('remove_transaction', transaction_type, transaction_id,
                 {'removed_by': current_user.username})
        return jsonify({'success': True, 'message': 'Transaction removed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

# Driver Block/Unblock Routes
@admin_bp.route('/drivers/<int:driver_id>/block', methods=['POST'])
@login_required
@admin_required
def block_driver(driver_id):
    """Block (suspend) a driver"""
    driver = Driver.query.get_or_404(driver_id)
    reason = request.form.get('reason', 'Administrative action')
    
    if driver.status == DriverStatus.SUSPENDED:
        return jsonify({'success': False, 'message': 'Driver is already blocked'})
    
    # Store the previous status for audit purposes
    previous_status = driver.status.value
    
    # Block the driver
    driver.status = DriverStatus.SUSPENDED
    driver.suspended_at = datetime.utcnow()
    driver.suspended_by = current_user.id
    driver.suspension_reason = reason
    
    # End any active vehicle assignments
    active_assignments = VehicleAssignment.query.filter_by(
        driver_id=driver_id,
        status=AssignmentStatus.ACTIVE
    ).all()
    
    for assignment in active_assignments:
        assignment.status = AssignmentStatus.COMPLETED
        assignment.end_date = datetime.now().date()
        assignment.notes = f"Assignment ended due to driver suspension: {reason}"
    
    # End any active duties
    active_duties = Duty.query.filter_by(
        driver_id=driver_id,
        status=DutyStatus.ACTIVE
    ).all()
    
    for duty in active_duties:
        duty.status = DutyStatus.COMPLETED
        duty.end_time = datetime.utcnow()
        duty.notes = f"Duty ended due to driver suspension: {reason}"
    
    try:
        db.session.commit()
        log_audit('block_driver', 'driver', driver_id,
                 {'driver_name': driver.full_name, 'reason': reason, 'previous_status': previous_status})
        return jsonify({'success': True, 'message': 'Driver has been blocked successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_bp.route('/drivers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_driver():
    """Add a new driver by admin"""
    from forms import DriverForm
    form = DriverForm()
    
    # Populate branch choices
    branches = Branch.query.filter_by(is_active=True).all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    
    if form.validate_on_submit():
        try:
            # Create user account first
            user = User()
            user.username = (form.full_name.data or '').lower().replace(' ', '_')
            user.email = f"{user.username}@plstravels.com"  # Generate email if not provided
            user.password_hash = generate_password_hash('driver123')  # Default password
            user.role = UserRole.DRIVER
            user.status = UserStatus.ACTIVE
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create driver profile
            driver = Driver()
            driver.user_id = user.id
            driver.branch_id = form.branch_id.data
            from utils import generate_employee_id
            driver.employee_id = generate_employee_id()
            driver.full_name = form.full_name.data
            # Note: Driver model uses current_address instead of address
            # Phone stored in additional_phones as JSON or consider adding phone field to model
            if form.phone.data:
                import json
                driver.additional_phones = json.dumps([form.phone.data])
            driver.current_address = form.address.data
            driver.date_of_birth = form.date_of_birth.data
            driver.aadhar_number = form.aadhar_number.data
            driver.license_number = form.license_number.data
            driver.bank_name = form.bank_name.data
            driver.account_number = form.account_number.data
            driver.ifsc_code = form.ifsc_code.data
            driver.account_holder_name = form.account_holder_name.data
            driver.status = DriverStatus.ACTIVE  # Admin created drivers are active by default
            driver.approved_by = current_user.id
            driver.approved_at = get_ist_time_naive()
            
            db.session.add(driver)
            db.session.commit()
            
            log_audit('add_driver', 'driver', driver.id, {
                'driver_name': driver.full_name, 
                'branch': (lambda br: br.name if br else 'Unknown')(getattr(driver, 'branch', None)),
                'created_by_admin': True
            })
            
            flash(f'Driver {driver.full_name} has been successfully added.', 'success')
            return redirect(url_for('admin.drivers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding driver: {str(e)}', 'error')
    
    return render_template('admin/driver_form.html', form=form, title='Add Driver', action='add')

@admin_bp.route('/drivers/<int:driver_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_driver(driver_id):
    """Edit an existing driver"""
    from forms import DriverForm
    driver = Driver.query.get_or_404(driver_id)
    form = DriverForm(obj=driver)
    
    # Populate branch choices
    branches = Branch.query.filter_by(is_active=True).all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    
    if form.validate_on_submit():
        try:
            # Update driver details
            driver.full_name = form.full_name.data
            # Note: Driver model uses current_address instead of address
            # Phone stored in additional_phones as JSON or consider adding phone field to model
            if form.phone.data:
                import json
                driver.additional_phones = json.dumps([form.phone.data])
            driver.current_address = form.address.data
            driver.date_of_birth = form.date_of_birth.data
            driver.aadhar_number = form.aadhar_number.data
            driver.license_number = form.license_number.data
            driver.bank_name = form.bank_name.data
            driver.account_number = form.account_number.data
            driver.ifsc_code = form.ifsc_code.data
            driver.account_holder_name = form.account_holder_name.data
            driver.branch_id = form.branch_id.data
            
            db.session.commit()
            
            log_audit('edit_driver', 'driver', driver.id, {
                'driver_name': driver.full_name,
                'updated_by_admin': True
            })
            
            flash(f'Driver {driver.full_name} has been successfully updated.', 'success')
            return redirect(url_for('admin.drivers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating driver: {str(e)}', 'error')
    
    return render_template('admin/driver_form.html', form=form, title='Edit Driver', action='edit', driver=driver)

@admin_bp.route('/drivers/<int:driver_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_driver(driver_id):
    """Soft delete a driver (set status to terminated)"""
    driver = Driver.query.get_or_404(driver_id)
    
    if driver.status == DriverStatus.TERMINATED:
        return jsonify({'success': False, 'message': 'Driver is already deleted'})
    
    try:
        # Soft delete - set status to terminated
        previous_status = driver.status.value
        driver.status = DriverStatus.TERMINATED
        driver.terminated_at = datetime.utcnow()
        driver.terminated_by = current_user.id
        
        # End any active assignments and duties
        active_assignments = VehicleAssignment.query.filter_by(
            driver_id=driver_id,
            status=AssignmentStatus.ACTIVE
        ).all()
        
        for assignment in active_assignments:
            assignment.status = AssignmentStatus.COMPLETED
            assignment.end_date = datetime.now().date()
            assignment.notes = "Assignment ended due to driver termination"
        
        active_duties = Duty.query.filter_by(
            driver_id=driver_id,
            status=DutyStatus.ACTIVE
        ).all()
        
        for duty in active_duties:
            duty.status = DutyStatus.COMPLETED
            duty.end_time = datetime.utcnow()
            duty.notes = "Duty ended due to driver termination"
        
        db.session.commit()
        
        log_audit('delete_driver', 'driver', driver_id, {
            'driver_name': driver.full_name,
            'previous_status': previous_status
        })
        
        return jsonify({'success': True, 'message': 'Driver has been successfully deleted'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting driver: {str(e)}'})

@admin_bp.route('/drivers/<int:driver_id>/unblock', methods=['POST'])
@login_required
@admin_required
def unblock_driver(driver_id):
    """Unblock (reactivate) a driver"""
    driver = Driver.query.get_or_404(driver_id)
    
    if driver.status != DriverStatus.SUSPENDED:
        return jsonify({'success': False, 'message': 'Driver is not currently blocked'})
    
    # Reactivate the driver
    driver.status = DriverStatus.ACTIVE
    driver.reactivated_at = datetime.utcnow()
    driver.reactivated_by = current_user.id
    driver.suspension_reason = None
    
    try:
        db.session.commit()
        log_audit('unblock_driver', 'driver', driver_id,
                 {'driver_name': driver.full_name, 'reactivated_by': current_user.username})
        return jsonify({'success': True, 'message': 'Driver has been unblocked successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

# Resignation Management Routes
@admin_bp.route('/resignations')
@login_required
@admin_required
def resignations():
    """View all resignation requests"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    branch_filter = request.args.get('branch', '', type=int)
    
    query = ResignationRequest.query.join(Driver).join(Branch)
    
    if status_filter:
        query = query.filter(ResignationRequest.status == status_filter)
    
    if branch_filter:
        query = query.filter(Driver.branch_id == branch_filter)
    
    resignations = query.order_by(desc(ResignationRequest.submitted_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    branches = Branch.query.filter_by(is_active=True).all()
    
    # Get summary statistics
    stats = {
        'pending': ResignationRequest.query.filter_by(status=ResignationStatus.PENDING).count(),
        'approved': ResignationRequest.query.filter_by(status=ResignationStatus.APPROVED).count(),
        'in_notice': ResignationRequest.query.filter(
            ResignationRequest.status == ResignationStatus.APPROVED,
            ResignationRequest.notice_period_start <= datetime.now().date(),
            ResignationRequest.notice_period_end >= datetime.now().date()
        ).count(),
        'completed': ResignationRequest.query.filter_by(status=ResignationStatus.COMPLETED).count()
    }
    
    return render_template('admin/resignations.html',
                         resignations=resignations,
                         branches=branches,
                         status_filter=status_filter,
                         branch_filter=branch_filter,
                         stats=stats)

@admin_bp.route('/resignations/<int:resignation_id>')
@login_required
@admin_required
def view_resignation(resignation_id):
    """View resignation request details"""
    resignation = ResignationRequest.query.get_or_404(resignation_id)
    
    # Get driver's current assignments and assets
    active_assignments = VehicleAssignment.query.filter_by(
        driver_id=resignation.driver_id,
        status=AssignmentStatus.ACTIVE
    ).all()
    
    assigned_assets = Asset.query.filter_by(
        driver_id=resignation.driver_id,
        status='assigned'
    ).all()
    
    # Get financial summary
    total_earnings = sum(duty.driver_earnings or 0 for duty in resignation.driver.duties)
    total_penalties = sum(penalty.amount or 0 for penalty in resignation.driver.penalties)
    net_amount = total_earnings - total_penalties
    
    return render_template('admin/resignation_details.html',
                         resignation=resignation,
                         active_assignments=active_assignments,
                         assigned_assets=assigned_assets,
                         financial_summary={
                             'total_earnings': total_earnings,
                             'total_penalties': total_penalties,
                             'net_amount': net_amount
                         })

@admin_bp.route('/resignations/<int:resignation_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_resignation(resignation_id):
    """Approve resignation request and start 30-day notice period"""
    resignation = ResignationRequest.query.get_or_404(resignation_id)
    
    if resignation.status != ResignationStatus.PENDING:
        flash('This resignation request has already been processed.', 'error')
        return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))
    
    admin_comments = request.form.get('admin_comments', '')
    waive_notice = request.form.get('waive_notice') == 'on'
    waiver_reason = request.form.get('waiver_reason', '')
    
    # Calculate notice period dates
    notice_start = datetime.now().date()
    if waive_notice:
        notice_end = notice_start  # Immediate termination
        resignation.is_notice_period_waived = True
        resignation.waiver_reason = waiver_reason
    else:
        notice_end = notice_start + timedelta(days=30)
    
    # Update resignation request
    resignation.status = ResignationStatus.APPROVED
    resignation.reviewed_by = current_user.id
    resignation.reviewed_at = datetime.utcnow()
    resignation.approved_at = datetime.utcnow()
    resignation.admin_comments = admin_comments
    resignation.notice_period_start = notice_start
    resignation.notice_period_end = notice_end
    resignation.actual_last_working_date = resignation.preferred_last_working_date
    
    try:
        db.session.commit()
        log_audit('approve_resignation', 'resignation', resignation_id,
                 {'driver_name': resignation.driver.full_name, 'notice_waived': waive_notice})
        
        flash(f'Resignation approved. Driver must complete {"notice period waived" if waive_notice else "30-day notice period"}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error approving resignation. Please try again.', 'error')
    
    return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))

@admin_bp.route('/resignations/<int:resignation_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_resignation(resignation_id):
    """Reject resignation request"""
    resignation = ResignationRequest.query.get_or_404(resignation_id)
    
    if resignation.status != ResignationStatus.PENDING:
        flash('This resignation request has already been processed.', 'error')
        return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))
    
    rejection_reason = request.form.get('rejection_reason', '')
    admin_comments = request.form.get('admin_comments', '')
    
    if not rejection_reason:
        flash('Please provide a reason for rejection.', 'error')
        return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))
    
    # Update resignation request
    resignation.status = ResignationStatus.REJECTED
    resignation.reviewed_by = current_user.id
    resignation.reviewed_at = datetime.utcnow()
    resignation.rejection_reason = rejection_reason
    resignation.admin_comments = admin_comments
    
    try:
        db.session.commit()
        log_audit('reject_resignation', 'resignation', resignation_id,
                 {'driver_name': resignation.driver.full_name, 'reason': rejection_reason})
        
        flash('Resignation request has been rejected.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting resignation. Please try again.', 'error')
    
    return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))

@admin_bp.route('/resignations/<int:resignation_id>/complete', methods=['POST'])
@login_required
@admin_required
def complete_resignation(resignation_id):
    """Complete resignation process after notice period"""
    resignation = ResignationRequest.query.get_or_404(resignation_id)
    
    if resignation.status != ResignationStatus.APPROVED:
        flash('This resignation is not in approved status.', 'error')
        return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))
    
    if not resignation.can_be_completed:
        flash('Notice period is still active. Cannot complete resignation yet.', 'error')
        return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))
    
    # Update resignation to completed
    resignation.status = ResignationStatus.COMPLETED
    resignation.completed_at = datetime.utcnow()
    
    # Update driver status to terminated
    driver = resignation.driver
    driver.status = DriverStatus.TERMINATED
    
    # Complete active assignments
    VehicleAssignment.query.filter_by(
        driver_id=driver.id,
        status=AssignmentStatus.ACTIVE
    ).update({
        'status': AssignmentStatus.COMPLETED,
        'end_date': datetime.now().date()
    })
    
    # Complete active duties
    Duty.query.filter_by(
        driver_id=driver.id,
        status=DutyStatus.ACTIVE
    ).update({
        'status': DutyStatus.COMPLETED,
        'end_time': datetime.utcnow()
    })
    
    try:
        db.session.commit()
        log_audit('complete_resignation', 'resignation', resignation_id,
                 {'driver_name': driver.full_name})
        
        flash('Resignation completed successfully. Driver status updated to terminated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error completing resignation. Please try again.', 'error')
    
    return redirect(url_for('admin.view_resignation', resignation_id=resignation_id))

@admin_bp.route('/schedule-duty-assignments', methods=['GET', 'POST'])
@login_required
@admin_required
def schedule_duty_assignments():
    """Enhanced duty assignment scheduling interface"""
    if request.method == 'POST':
        # Handle assignment creation
        driver_id = request.form.get('driver_id', type=int)
        vehicle_id = request.form.get('vehicle_id', type=int)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        shift_type = request.form.get('shift_type', 'full_day')
        assignment_type = request.form.get('assignment_type', 'regular')
        
        if not all([driver_id, vehicle_id, start_date]):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        try:
            # start_date is already checked for non-None in all() above, add extra safety
            if start_date and start_date.strip():
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                return jsonify({'success': False, 'message': 'Invalid start date format'})
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date and end_date.strip() else None
            
            # Check for conflicts
            conflicts = check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, shift_type)
            
            if conflicts['driver_conflict'] or conflicts['vehicle_conflict']:
                return jsonify({
                    'success': False, 
                    'message': 'Assignment conflicts detected',
                    'conflicts': {
                        'driver': conflicts['driver_conflict'].id if conflicts['driver_conflict'] else None,
                        'vehicle': conflicts['vehicle_conflict'].id if conflicts['vehicle_conflict'] else None
                    }
                })
            
            # Create assignment
            assignment = VehicleAssignment()
            assignment.driver_id = driver_id
            assignment.vehicle_id = vehicle_id
            assignment.start_date = start_date
            assignment.end_date = end_date
            assignment.shift_type = shift_type
            assignment.assignment_type = assignment_type
            assignment.priority = 2  # Medium priority by default
            assignment.assigned_by = current_user.id
            
            # Set status based on start date
            if start_date <= datetime.now().date():
                assignment.status = AssignmentStatus.ACTIVE
                # Update driver's current vehicle
                driver = Driver.query.get(driver_id)
                if driver:
                    driver.current_vehicle_id = vehicle_id
            else:
                assignment.status = AssignmentStatus.SCHEDULED
            
            db.session.add(assignment)
            db.session.commit()
            
            log_audit('create_duty_assignment', 'assignment', assignment.id,
                     {'driver': assignment.assignment_driver.full_name,
                      'vehicle': assignment.assignment_vehicle.registration_number,
                      'start_date': str(start_date),
                      'shift_type': shift_type})
            
            return jsonify({
                'success': True, 
                'message': 'Duty assignment created successfully',
                'assignment_id': assignment.id
            })
            
        except ValueError as e:
            return jsonify({'success': False, 'message': 'Invalid date format'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
    
    # Get data for the interface
    branches = Branch.query.filter_by(is_active=True).all()
    active_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).join(Branch).all()
    available_vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE, is_available=True).join(Branch).all()
    
    # Get recent assignments for display
    recent_assignments = VehicleAssignment.query.filter(
        VehicleAssignment.start_date >= datetime.now().date() - timedelta(days=7)
    ).order_by(desc(VehicleAssignment.start_date)).limit(20).all()
    
    # Get assignment statistics
    stats = {
        'active_assignments': VehicleAssignment.query.filter_by(status=AssignmentStatus.ACTIVE).count(),
        'scheduled_assignments': VehicleAssignment.query.filter_by(status=AssignmentStatus.SCHEDULED).count(),
        'available_drivers': len([d for d in active_drivers if not d.current_vehicle_id]),
        'available_vehicles': len(available_vehicles)
    }
    
    return render_template('admin/schedule_duty_assignments.html',
                         branches=branches,
                         drivers=active_drivers,
                         vehicles=available_vehicles,
                         recent_assignments=recent_assignments,
                         stats=stats,
                         today=datetime.now().strftime('%Y-%m-%d'))

# Smart Recommendation Engine API Endpoints
@admin_bp.route('/api/recommendations/driver-vehicle', methods=['GET'])
@login_required
@admin_required
def get_driver_vehicle_recommendations():
    """Get smart recommendations for driver-vehicle assignments"""
    branch_id = request.args.get('branch_id', type=int)
    shift_type = request.args.get('shift_type', 'full_day')
    strategy = request.args.get('strategy', 'balanced')
    limit = request.args.get('limit', 10, type=int)
    
    try:
        recommendations = recommendation_engine.get_recommendations(
            branch_id=branch_id,
            shift_type=shift_type,
            strategy=strategy,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        result = []
        for rec in recommendations:
            driver = Driver.query.get(rec.driver_id)
            vehicle = Vehicle.query.get(rec.vehicle_id)
            
            result.append({
                'driver_id': rec.driver_id,
                'driver_name': driver.full_name if driver else 'Unknown',
                'driver_employee_id': driver.employee_id if driver else None,
                'vehicle_id': rec.vehicle_id,
                'vehicle_registration': vehicle.registration_number if vehicle else 'Unknown',
                'vehicle_type': vehicle.vehicle_type.name if vehicle and vehicle.vehicle_type else 'Unknown',
                'total_score': rec.total_score,
                'performance_score': rec.performance_score,
                'compatibility_score': rec.compatibility_score,
                'availability_score': rec.availability_score,
                'experience_score': rec.experience_score,
                'location_score': rec.location_score,
                'reasoning': rec.reasoning
            })
        
        return jsonify({
            'success': True,
            'recommendations': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating recommendations: {str(e)}'
        })

@admin_bp.route('/api/recommendations/driver/<int:vehicle_id>', methods=['GET'])
@login_required 
@admin_required
def get_driver_recommendations_for_vehicle(vehicle_id):
    """Get best driver recommendations for a specific vehicle"""
    limit = request.args.get('limit', 5, type=int)
    
    try:
        recommendations = recommendation_engine.get_driver_recommendations(vehicle_id, limit)
        
        result = []
        for rec in recommendations:
            driver = Driver.query.get(rec.driver_id)
            
            result.append({
                'driver_id': rec.driver_id,
                'driver_name': driver.full_name if driver else 'Unknown',
                'driver_employee_id': driver.employee_id if driver else None,
                'total_score': rec.total_score,
                'performance_score': rec.performance_score,
                'compatibility_score': rec.compatibility_score,
                'reasoning': rec.reasoning[:3]  # Top 3 reasons
            })
        
        return jsonify({
            'success': True,
            'vehicle_id': vehicle_id,
            'recommendations': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting driver recommendations: {str(e)}'
        })

@admin_bp.route('/api/recommendations/vehicle/<int:driver_id>', methods=['GET'])
@login_required
@admin_required 
def get_vehicle_recommendations_for_driver(driver_id):
    """Get best vehicle recommendations for a specific driver"""
    limit = request.args.get('limit', 5, type=int)
    
    try:
        recommendations = recommendation_engine.get_vehicle_recommendations(driver_id, limit)
        
        result = []
        for rec in recommendations:
            vehicle = Vehicle.query.get(rec.vehicle_id)
            
            result.append({
                'vehicle_id': rec.vehicle_id,
                'vehicle_registration': vehicle.registration_number if vehicle else 'Unknown',
                'vehicle_type': vehicle.vehicle_type.name if vehicle and vehicle.vehicle_type else 'Unknown',
                'fuel_type': vehicle.fuel_type if vehicle else 'Unknown',
                'total_score': rec.total_score,
                'performance_score': rec.performance_score,
                'compatibility_score': rec.compatibility_score,
                'reasoning': rec.reasoning[:3]  # Top 3 reasons
            })
        
        return jsonify({
            'success': True,
            'driver_id': driver_id,
            'recommendations': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting vehicle recommendations: {str(e)}'
        })

@admin_bp.route('/api/recommendations/analytics', methods=['GET'])
@login_required
@admin_required
def get_recommendation_analytics():
    """Get analytics summary for recommendation engine"""
    branch_id = request.args.get('branch_id', type=int)
    
    try:
        analytics = recommendation_engine.get_analytics_summary(branch_id)
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting analytics: {str(e)}'
        })

@admin_bp.route('/recommendations-dashboard')
@login_required
@admin_required
def recommendations_dashboard():
    """Smart Recommendations Dashboard"""
    branches = Branch.query.filter_by(is_active=True).all()
    
    # Get some quick stats
    total_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).count()
    total_vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE, is_available=True).count()
    
    # Get top performing drivers
    top_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).order_by(desc(Driver.rating_average)).limit(10).all()
    
    return render_template('admin/recommendations_dashboard.html',
                         branches=branches,
                         total_drivers=total_drivers,
                         total_vehicles=total_vehicles,
                         top_drivers=top_drivers)

@admin_bp.route('/assignments')
@login_required
@admin_required
def assignments():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    branch_filter = request.args.get('branch', '', type=int)
    
    query = VehicleAssignment.query.join(Driver).join(Vehicle)
    
    if status_filter:
        query = query.filter(VehicleAssignment.status == status_filter)
    
    if branch_filter:
        query = query.filter(Driver.branch_id == branch_filter)
    
    assignments = query.order_by(desc(VehicleAssignment.start_date)).paginate(page=page, per_page=20, error_out=False)
    branches = Branch.query.filter_by(is_active=True).all()
    
    return render_template('admin/assignments.html',
                         assignments=assignments,
                         branches=branches,
                         status_filter=status_filter,
                         branch_filter=branch_filter)

@admin_bp.route('/assignments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_assignment():
    form = VehicleAssignmentForm()
    
    # Populate form choices
    active_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).join(Branch).all()
    form.driver_id.choices = [(d.id, f"{d.full_name} ({d.branch.name if d.branch else 'Unknown'})") for d in active_drivers]
    
    available_vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE, is_available=True).join(Branch).all()
    form.vehicle_id.choices = [(v.id, f"{v.registration_number} - {v.model or v.vehicle_type.name} ({v.branch.name if v.branch else 'Unknown'})") for v in available_vehicles]
    
    if form.validate_on_submit():
        conflicts = check_assignment_conflicts(form.driver_id.data, form.vehicle_id.data, 
                                             form.start_date.data, form.end_date.data, form.shift_type.data)
        
        if conflicts['driver_conflict']:
            flash(f"Driver already has an assignment for this period: {conflicts['driver_conflict'].start_date} to {conflicts['driver_conflict'].end_date or 'ongoing'}", 'error')
        elif conflicts['vehicle_conflict']:
            flash(f"Vehicle is already assigned for this period: {conflicts['vehicle_conflict'].start_date} to {conflicts['vehicle_conflict'].end_date or 'ongoing'}", 'error')
        else:
            assignment = VehicleAssignment()
            assignment.driver_id = form.driver_id.data
            assignment.vehicle_id = form.vehicle_id.data
            assignment.start_date = form.start_date.data
            assignment.end_date = form.end_date.data
            assignment.shift_type = form.shift_type.data
            assignment.assignment_type = form.assignment_type.data
            assignment.priority = form.priority.data
            assignment.notes = form.assignment_notes.data
            assignment.assigned_by = current_user.id
            
            # Set status based on start date
            if form.start_date.data and form.start_date.data <= datetime.now().date():
                assignment.status = AssignmentStatus.ACTIVE
                # Update driver's current vehicle
                driver = Driver.query.get(form.driver_id.data)
                if driver:
                    driver.current_vehicle_id = form.vehicle_id.data
            else:
                assignment.status = AssignmentStatus.SCHEDULED
            
            db.session.add(assignment)
            db.session.commit()
            
            log_audit('create_vehicle_assignment', 'assignment', assignment.id,
                     {'driver': assignment.assignment_driver.full_name, 
                      'vehicle': assignment.assignment_vehicle.registration_number,
                      'start_date': str(assignment.start_date),
                      'shift_type': assignment.shift_type})
            
            flash('Vehicle assignment created successfully!', 'success')
            return redirect(url_for('admin.assignments'))
    
    return render_template('admin/add_assignment.html', form=form)

def handle_bulk_assignment():
    """Handle bulk assignment form submission"""
    try:
        data = request.json if request.is_json else request.form
        assignments_data = json.loads((data or {}).get('assignments_data', '[]'))
        result = create_bulk_assignments(assignments_data, current_user.id)
        
        if result['success']:
            flash(f"Successfully created {result['created_count']} assignments.", 'success')
        else:
            flash("Failed to create bulk assignments.", 'error')
            for error in result['errors']:
                flash(error, 'error')
                
        return redirect(url_for('admin.assignments'))
    except Exception as e:
        flash(f"Error processing bulk assignments: {str(e)}", 'error')
        return redirect(url_for('admin.assignments'))

def handle_quick_assignment():
    """Handle quick assignment form submission"""
    try:
        form_data = request.form
        date_range = form_data.get('date_range', '').split(' to ')
        driver_ids = [int(id) for id in form_data.get('drivers', '').split(',') if id.strip()]
        vehicle_ids = [int(id) for id in form_data.get('vehicles', '').split(',') if id.strip()]
        shift_type = form_data.get('shift_type', 'full_day')
        
        assignments_data = []
        start_date = datetime.strptime(date_range[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(date_range[1], '%Y-%m-%d').date() if len(date_range) > 1 else start_date
        
        # Create assignments for each driver-vehicle pair
        for i, driver_id in enumerate(driver_ids):
            vehicle_id = vehicle_ids[i] if i < len(vehicle_ids) else vehicle_ids[0]
            assignments_data.append({
                'driver_id': driver_id,
                'vehicle_id': vehicle_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'shift_type': shift_type,
                'assignment_type': 'regular',
                'priority': 2
            })
        
        result = create_bulk_assignments(assignments_data, current_user.id)
        
        if result['success']:
            flash(f"Successfully created {result['created_count']} quick assignments.", 'success')
        else:
            flash("Failed to create quick assignments.", 'error')
            
        return redirect(url_for('admin.assignments'))
    except Exception as e:
        flash(f"Error processing quick assignments: {str(e)}", 'error')
        return redirect(url_for('admin.assignments'))

@admin_bp.route('/assignments/schedule', methods=['GET', 'POST'])
@login_required 
@admin_required
def schedule_assignments():
    """Enhanced scheduling interface with calendar view and bulk operations"""
    form = ScheduledAssignmentForm()
    
    if request.method == 'POST':
        if 'bulk_assign' in request.form:
            return handle_bulk_assignment()
        elif 'quick_assign' in request.form:
            return handle_quick_assignment()
    
    # Get data for calendar view
    today = datetime.now().date()
    start_date = request.args.get('start', today.strftime('%Y-%m-%d'))
    end_date = request.args.get('end', (today + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    # Get assignments for the date range
    assignments = VehicleAssignment.query.filter(
        VehicleAssignment.start_date <= datetime.strptime(end_date, '%Y-%m-%d').date(),
        VehicleAssignment.end_date.is_(None) | (VehicleAssignment.end_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    ).all()
    
    # Get available drivers and vehicles
    drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).all()
    vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE, is_available=True).all()
    
    # Build calendar data
    calendar_data = build_assignment_calendar(assignments, start_date, end_date)
    
    return render_template('admin/schedule_assignments.html',
                         form=form,
                         assignments=assignments,
                         drivers=drivers,
                         vehicles=vehicles,
                         calendar_data=calendar_data,
                         start_date=start_date,
                         end_date=end_date)

@admin_bp.route('/assignment-templates')
@login_required
@admin_required
def assignment_templates():
    """Manage assignment templates"""
    templates = AssignmentTemplate.query.filter_by(is_active=True).order_by(AssignmentTemplate.name).all()
    return render_template('admin/assignment_templates.html', templates=templates)

@admin_bp.route('/assignment-templates/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_assignment_template():
    """Add new assignment template"""
    form = AssignmentTemplateForm()
    branches = Branch.query.filter_by(is_active=True).all()
    # Simple approach for SelectField choices to avoid typing issues
    form.branch_id.choices = []
    form.branch_id.choices.append(('0', 'All Branches'))
    for b in branches:
        form.branch_id.choices.append((str(b.id), b.name))
    
    if form.validate_on_submit():
        template = AssignmentTemplate()
        template.name = form.name.data
        template.description = form.description.data
        template.branch_id = int(form.branch_id.data) if form.branch_id.data else None
        template.shift_pattern = form.shift_pattern.data
        template.days_of_week = form.days_of_week.data
        template.default_shift_type = form.default_shift_type.data
        template.is_default = form.is_default.data
        template.created_by = current_user.id
        
        # Process template assignments if provided
        if form.template_assignments.data:
            try:
                template_data = json.loads(form.template_assignments.data)
                template.set_template_data(template_data)
            except json.JSONDecodeError:
                flash('Invalid JSON format in template assignments.', 'error')
                return render_template('admin/assignment_template_form.html', form=form, title='Add Assignment Template')
        
        # If set as default, unset other defaults in same branch
        if template.is_default:
            AssignmentTemplate.query.filter_by(
                branch_id=template.branch_id,
                is_default=True
            ).update({'is_default': False})
        
        db.session.add(template)
        db.session.commit()
        
        log_audit('add_assignment_template', 'assignment_template', template.id,
                 {'name': template.name, 'pattern': template.shift_pattern})
        
        flash('Assignment template created successfully.', 'success')
        return redirect(url_for('admin.assignment_templates'))
    
    return render_template('admin/assignment_template_form.html', form=form, title='Add Assignment Template')

def apply_template_to_dates(template, start_date, end_date):
    """Apply assignment template to create assignments for date range"""
    assignments_created = 0
    template_data = template.get_template_data()
    
    if not template_data:
        # Create basic pattern if no specific data
        current_date = start_date
        while current_date <= (end_date or start_date):
            # Apply basic template logic based on shift pattern
            if template.shift_pattern == 'daily' or should_apply_on_date(template, current_date):
                assignments_created += 1
            
            current_date += timedelta(days=1)
            if template.shift_pattern == 'weekly':
                current_date += timedelta(days=6)  # Skip to next week
    
    return assignments_created

def should_apply_on_date(template, date):
    """Check if template should be applied on given date"""
    if not template.days_of_week:
        return True
    
    day_numbers = [int(d.strip()) for d in template.days_of_week.split(',') if d.strip().isdigit()]
    weekday = date.weekday() + 1  # Python uses 0-6, we want 1-7
    
    return weekday in day_numbers

@admin_bp.route('/assignments/conflicts', methods=['POST'])
@login_required
@admin_required  
def check_conflicts():
    """API endpoint to check for assignment conflicts"""
    data = request.json or {}
    driver_id = data.get('driver_id')
    vehicle_id = data.get('vehicle_id')
    start_date_str = data.get('start_date')
    if not start_date_str:
        return jsonify({'error': 'start_date is required'}), 400
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date_str = data.get('end_date')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str and end_date_str.strip() else None
    shift_type = data.get('shift_type', 'full_day')
    
    conflicts = check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, shift_type)
    
    return jsonify({
        'has_conflicts': bool(conflicts['driver_conflict'] or conflicts['vehicle_conflict']),
        'driver_conflict': conflicts['driver_conflict'].id if conflicts['driver_conflict'] else None,
        'vehicle_conflict': conflicts['vehicle_conflict'].id if conflicts['vehicle_conflict'] else None,
        'suggestions': generate_assignment_suggestions(driver_id, vehicle_id, start_date, end_date, shift_type)
    })

@admin_bp.route('/assignments/<int:assignment_id>/end', methods=['POST'])
@login_required
@admin_required
def end_assignment(assignment_id):
    assignment = VehicleAssignment.query.get_or_404(assignment_id)
    
    assignment.status = AssignmentStatus.COMPLETED
    assignment.end_date = datetime.now().date()
    assignment.updated_at = datetime.utcnow()
    
    # Clear driver's current vehicle
    if assignment.assignment_driver.current_vehicle_id == assignment.vehicle_id:
        assignment.assignment_driver.current_vehicle_id = None
    
    db.session.commit()
    
    log_audit('end_vehicle_assignment', 'assignment', assignment_id,
             {'driver': assignment.assignment_driver.full_name,
              'vehicle': assignment.assignment_vehicle.registration_number})
    
    flash('Assignment ended successfully.', 'success')
    return redirect(url_for('admin.assignments'))

@admin_bp.route('/vehicles')
@login_required
@admin_required
def vehicles():
    page = request.args.get('page', 1, type=int)
    branch_filter = request.args.get('branch', '', type=int)
    
    query = Vehicle.query
    
    if branch_filter:
        query = query.filter(Vehicle.branch_id == branch_filter)
    
    vehicles = query.paginate(page=page, per_page=20, error_out=False)
    branches = Branch.query.filter_by(is_active=True).all()
    
    from datetime import datetime
    return render_template('admin/vehicles.html', 
                         vehicles=vehicles, 
                         branches=branches,
                         branch_filter=branch_filter,
                         today=datetime.now().date())

@admin_bp.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_vehicle():
    # Ensure default data exists
    create_default_branch()
    create_default_vehicle_types()
    
    form = VehicleForm()
    
    # Get branches and vehicle types
    branches = Branch.query.filter_by(is_active=True).all()
    vehicle_types = VehicleType.query.filter_by(is_active=True).all()
    
    if not branches:
        flash('No active branches found. Please create a branch first.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    if not vehicle_types:
        flash('No vehicle types found. Please create vehicle types first.', 'error')
        return redirect(url_for('admin.dashboard'))
        
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.vehicle_type_id.choices = [(vt.id, vt.name) for vt in vehicle_types]
    
    if form.validate_on_submit():
        # Check if registration number already exists
        reg_number = (form.registration_number.data or '').upper()
        existing_vehicle = Vehicle.query.filter_by(registration_number=reg_number).first()
        if existing_vehicle:
            flash('Vehicle with this registration number already exists.', 'error')
            return render_template('admin/vehicle_form.html', form=form, title='Add Vehicle')
        
        vehicle = Vehicle()
        vehicle.registration_number = (form.registration_number.data or '').upper()  # Store in uppercase
        vehicle.vehicle_type_id = form.vehicle_type_id.data
        vehicle.model = form.model.data
        vehicle.manufacturing_year = form.manufacturing_year.data
        vehicle.color = form.color.data
        vehicle.branch_id = form.branch_id.data
        vehicle.insurance_policy_number = form.insurance_number.data
        vehicle.insurance_expiry_date = form.insurance_expiry.data
        vehicle.fitness_expiry_date = form.fitness_expiry.data
        vehicle.permit_expiry_date = form.permit_expiry.data
        vehicle.fastag_id = form.fastag_number.data
        vehicle.gps_device_id = form.device_imei.data
        
        # Set defaults for required fields
        vehicle.status = VehicleStatus.ACTIVE
        vehicle.is_available = True
        vehicle.current_odometer = 0.0
        
        try:
            # Add vehicle to session first to get the ID after flush
            db.session.add(vehicle)
            db.session.flush()  # This assigns the ID without committing
            
            # Process vehicle document uploads
            document_fields = [
                ('registration_document', 'vehicle_registration'),
                ('insurance_document', 'vehicle_insurance'), 
                ('fitness_document', 'vehicle_fitness'),
                ('permit_document', 'vehicle_permit'),
                ('pollution_document', 'vehicle_pollution'),
                ('other_document', 'vehicle_other')
            ]
            
            for field_name, document_type in document_fields:
                file_field = getattr(form, field_name)
                if file_field.data and allowed_file(file_field.data.filename):
                    # Process traditional file upload
                    filename = process_file_upload(file_field.data, vehicle.id, document_type)
                    if filename:
                        setattr(vehicle, field_name, filename)
                else:
                    # Check for camera capture (base64 data)
                    filename, metadata = process_camera_capture(request.form, field_name, vehicle.id, document_type)
                    if filename:
                        setattr(vehicle, field_name, filename)
            
            db.session.commit()
            
            log_audit('add_vehicle', 'vehicle', vehicle.id,
                     {'registration': vehicle.registration_number})
            
            flash('Vehicle added successfully.', 'success')
            return redirect(url_for('admin.vehicles'))
        except Exception as e:
            db.session.rollback()
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('admin.vehicles'))
    
    return render_template('admin/vehicle_form.html', form=form, title='Add Vehicle')

@admin_bp.route('/duties')
@login_required
@admin_required
def duties():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    branch_filter = request.args.get('branch', '', type=int)
    date_filter = request.args.get('date', '')
    
    query = Duty.query
    
    if status_filter:
        query = query.filter(Duty.status == status_filter)
    
    if branch_filter:
        query = query.filter(Duty.branch_id == branch_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Duty.start_time) == filter_date)
        except ValueError:
            pass
    
    duties = query.order_by(desc(Duty.start_time)).paginate(page=page, per_page=20, error_out=False)
    branches = Branch.query.filter_by(is_active=True).all()
    
    return render_template('admin/duties.html', 
                         duties=duties, 
                         branches=branches,
                         status_filter=status_filter,
                         branch_filter=branch_filter,
                         date_filter=date_filter)

def _validate_salary_method_config(scheme_type, config):
    """Validate salary method configuration based on scheme type"""
    if scheme_type == 'daily_payout':
        return config.get('daily_base_amount', 0) > 0 or config.get('daily_incentive_percent', 0) > 0
    elif scheme_type == 'monthly_payout':
        return config.get('monthly_base_salary', 0) > 0 or config.get('monthly_incentive_percent', 0) > 0
    elif scheme_type == 'performance_based':
        return config.get('target_trips_daily', 0) > 0 and config.get('target_revenue_daily', 0) > 0
    elif scheme_type == 'hybrid_commission':
        return config.get('base_amount', 0) > 0 and config.get('incentive_percent', 0) > 0
    elif scheme_type == 'revenue_sharing':
        return config.get('revenue_share_percent', 0) > 0
    elif scheme_type == 'fixed_salary':
        return config.get('fixed_monthly_salary', 0) > 0
    elif scheme_type == 'piece_rate':
        return config.get('per_trip_amount', 0) > 0
    elif scheme_type == 'slab_incentive':
        return config.get('slab1_max', 0) > 0 and config.get('slab1_percent', 0) > 0
    elif scheme_type == 'custom_formula':
        return bool(config.get('calculation_formula', '').strip())
    return True

@admin_bp.route('/duty-schemes')
@login_required
@admin_required
def duty_schemes():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    filter_type = request.args.get('type', '')
    filter_branch = request.args.get('branch', '')
    
    query = DutyScheme.query.filter_by(is_active=True)
    
    # Apply search filter
    if search:
        query = query.filter(or_(
            DutyScheme.name.ilike(f'%{search}%'),
            DutyScheme.scheme_type.ilike(f'%{search}%')
        ))
    
    # Apply type filter
    if filter_type:
        query = query.filter(DutyScheme.scheme_type == filter_type)
    
    # Apply branch filter
    if filter_branch:
        if filter_branch == 'global':
            query = query.filter(DutyScheme.branch_id.is_(None))
        else:
            query = query.filter(DutyScheme.branch_id == int(filter_branch))
    
    schemes = query.order_by(desc(DutyScheme.created_at)).paginate(
        page=page, per_page=12, error_out=False)
    
    branches = Branch.query.filter_by(is_active=True).all()
    scheme_types = [
        ('daily_payout', 'Daily Salary'),
        ('monthly_payout', 'Monthly Salary'),
        ('performance_based', 'Performance Based'),
        ('hybrid_commission', 'Hybrid Commission'),
        ('revenue_sharing', 'Revenue Sharing'),
        ('fixed_salary', 'Fixed Salary'),
        ('piece_rate', 'Piece Rate'),
        ('slab_incentive', 'Slab Incentive'),
        ('custom_formula', 'Custom Formula')
    ]
    
    return render_template('admin/duty_schemes.html', 
                         schemes=schemes, 
                         branches=branches,
                         scheme_types=scheme_types,
                         search=search,
                         filter_type=filter_type,
                         filter_branch=filter_branch)

@admin_bp.route('/duty-schemes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_duty_scheme():
    form = DutySchemeForm()
    branches = Branch.query.filter_by(is_active=True).all()
    # Simple approach for SelectField choices to avoid typing issues
    form.branch_id.choices = []
    form.branch_id.choices.append(('0', 'Global'))
    for b in branches:
        form.branch_id.choices.append((str(b.id), b.name))
    
    if form.validate_on_submit():
        # Enhanced configuration for all salary methods
        config = {
            'scheme_type': form.scheme_type.data,
            'bmg_amount': safe_float_conversion(form.bmg_amount.data, 0),
            'payout_frequency': form.payout_frequency.data or 'immediate',
            
            # Basic payout configurations
            'daily_base_amount': safe_float_conversion(form.daily_base_amount.data, 0),
            'daily_incentive_percent': safe_float_conversion(form.daily_incentive_percent.data, 0),
            'monthly_base_salary': safe_float_conversion(form.monthly_base_salary.data, 0),
            'monthly_incentive_percent': safe_float_conversion(form.monthly_incentive_percent.data, 0),
            
            # Performance-based salary components
            'target_trips_daily': safe_float_conversion(form.target_trips_daily.data, 0),
            'target_revenue_daily': safe_float_conversion(form.target_revenue_daily.data, 0),
            'bonus_per_extra_trip': safe_float_conversion(form.bonus_per_extra_trip.data, 0),
            'bonus_target_achievement': safe_float_conversion(form.bonus_target_achievement.data, 0),
            
            # Deduction management
            'fuel_deduction_percent': safe_float_conversion(form.fuel_deduction_percent.data, 0),
            'maintenance_deduction': safe_float_conversion(form.maintenance_deduction.data, 0),
            'insurance_deduction': safe_float_conversion(form.insurance_deduction.data, 0),
            'other_deductions': safe_float_conversion(form.other_deductions.data, 0),
            
            # Advanced salary components
            'overtime_rate_multiplier': safe_float_conversion(form.overtime_rate_multiplier.data, 1.5),
            'weekend_bonus_percent': safe_float_conversion(form.weekend_bonus_percent.data, 0),
            'holiday_bonus_percent': safe_float_conversion(form.holiday_bonus_percent.data, 0),
            
            # Revenue sharing configurations
            'revenue_share_percent': safe_float_conversion(form.revenue_share_percent.data, 0),
            'company_expense_deduction': safe_float_conversion(form.company_expense_deduction.data, 0),
            
            # Fixed salary components
            'fixed_monthly_salary': safe_float_conversion(form.fixed_monthly_salary.data, 0),
            'allowances': safe_float_conversion(form.allowances.data, 0),
            
            # Legacy scheme configurations (maintained for compatibility)
            'fixed_amount': safe_float_conversion(form.fixed_amount.data, 0),
            'per_trip_amount': safe_float_conversion(form.per_trip_amount.data, 0),
            'base_amount': safe_float_conversion(form.base_amount.data, 0),
            'incentive_percent': safe_float_conversion(form.incentive_percent.data, 0),
            'slab1_max': safe_float_conversion(form.slab1_max.data, 0),
            'slab1_percent': safe_float_conversion(form.slab1_percent.data, 0),
            'slab2_max': safe_float_conversion(form.slab2_max.data, 0),
            'slab2_percent': safe_float_conversion(form.slab2_percent.data, 0),
            'slab3_percent': safe_float_conversion(form.slab3_percent.data, 0)
        }
        
        scheme = DutyScheme()
        scheme.name = form.name.data
        scheme.scheme_type = form.scheme_type.data
        scheme.branch_id = int(form.branch_id.data) if form.branch_id.data and form.branch_id.data != 0 else None
        scheme.minimum_guarantee = form.bmg_amount.data or 0.0
        scheme.calculation_formula = form.calculation_formula.data or ''
        scheme.effective_from = form.effective_from.data or datetime.now().date()
        scheme.effective_until = form.effective_until.data
        scheme.set_config(config)
        scheme.created_by = current_user.id
        
        # Validation for salary method configurations
        if not _validate_salary_method_config(form.scheme_type.data, config):
            flash('Please fill in required fields for the selected salary method.', 'error')
            return render_template('admin/duty_scheme_form.html', form=form, title='Add Duty Scheme')
        
        db.session.add(scheme)
        db.session.commit()
        
        log_audit('add_duty_scheme', 'duty_scheme', scheme.id,
                 {'name': scheme.name, 'type': scheme.scheme_type, 'branch_id': scheme.branch_id})
        
        flash(f'Salary method "{scheme.name}" added successfully!', 'success')
        return redirect(url_for('admin.duty_schemes'))
    
    return render_template('admin/duty_scheme_form.html', form=form, title='Add Salary Method')

@admin_bp.route('/duty-schemes/<int:scheme_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_duty_scheme(scheme_id):
    scheme = DutyScheme.query.get_or_404(scheme_id)
    form = DutySchemeForm(obj=scheme)
    branches = Branch.query.filter_by(is_active=True).all()
    # Simple approach for SelectField choices to avoid typing issues
    form.branch_id.choices = []
    form.branch_id.choices.append(('0', 'Global'))
    for b in branches:
        form.branch_id.choices.append((str(b.id), b.name))
    
    if request.method == 'GET':
        # Pre-populate form with existing scheme data
        config = scheme.get_configuration()
        form.scheme_type.data = scheme.scheme_type
        form.branch_id.data = str(scheme.branch_id) if scheme.branch_id else ''
        form.bmg_amount.data = scheme.minimum_guarantee
        form.calculation_formula.data = scheme.calculation_formula
        
        # Populate configuration fields
        form.daily_base_amount.data = config.get('daily_base_amount', 0)
        form.daily_incentive_percent.data = config.get('daily_incentive_percent', 0)
        form.monthly_base_salary.data = config.get('monthly_base_salary', 0)
        form.monthly_incentive_percent.data = config.get('monthly_incentive_percent', 0)
        form.target_trips_daily.data = config.get('target_trips_daily', 0)
        form.target_revenue_daily.data = config.get('target_revenue_daily', 0)
        form.bonus_per_extra_trip.data = config.get('bonus_per_extra_trip', 0)
        form.bonus_target_achievement.data = config.get('bonus_target_achievement', 0)
        form.fuel_deduction_percent.data = config.get('fuel_deduction_percent', 0)
        form.maintenance_deduction.data = config.get('maintenance_deduction', 0)
        form.insurance_deduction.data = config.get('insurance_deduction', 0)
        form.other_deductions.data = config.get('other_deductions', 0)
        form.overtime_rate_multiplier.data = config.get('overtime_rate_multiplier', 1.5)
        form.weekend_bonus_percent.data = config.get('weekend_bonus_percent', 0)
        form.holiday_bonus_percent.data = config.get('holiday_bonus_percent', 0)
        form.revenue_share_percent.data = config.get('revenue_share_percent', 0)
        form.company_expense_deduction.data = config.get('company_expense_deduction', 0)
        form.fixed_monthly_salary.data = config.get('fixed_monthly_salary', 0)
        form.allowances.data = config.get('allowances', 0)
        form.fixed_amount.data = config.get('fixed_amount', 0)
        form.per_trip_amount.data = config.get('per_trip_amount', 0)
        form.base_amount.data = config.get('base_amount', 0)
        form.incentive_percent.data = config.get('incentive_percent', 0)
        form.slab1_max.data = config.get('slab1_max', 0)
        form.slab1_percent.data = config.get('slab1_percent', 0)
        form.slab2_max.data = config.get('slab2_max', 0)
        form.slab2_percent.data = config.get('slab2_percent', 0)
        form.slab3_percent.data = config.get('slab3_percent', 0)
    
    if form.validate_on_submit():
        # Enhanced configuration for all salary methods
        config = {
            'scheme_type': form.scheme_type.data,
            'bmg_amount': safe_float_conversion(form.bmg_amount.data, 0),
            'payout_frequency': form.payout_frequency.data or 'immediate',
            
            # Basic payout configurations
            'daily_base_amount': safe_float_conversion(form.daily_base_amount.data, 0),
            'daily_incentive_percent': safe_float_conversion(form.daily_incentive_percent.data, 0),
            'monthly_base_salary': safe_float_conversion(form.monthly_base_salary.data, 0),
            'monthly_incentive_percent': safe_float_conversion(form.monthly_incentive_percent.data, 0),
            
            # Performance-based salary components
            'target_trips_daily': safe_float_conversion(form.target_trips_daily.data, 0),
            'target_revenue_daily': safe_float_conversion(form.target_revenue_daily.data, 0),
            'bonus_per_extra_trip': safe_float_conversion(form.bonus_per_extra_trip.data, 0),
            'bonus_target_achievement': safe_float_conversion(form.bonus_target_achievement.data, 0),
            
            # Deduction management
            'fuel_deduction_percent': safe_float_conversion(form.fuel_deduction_percent.data, 0),
            'maintenance_deduction': safe_float_conversion(form.maintenance_deduction.data, 0),
            'insurance_deduction': safe_float_conversion(form.insurance_deduction.data, 0),
            'other_deductions': safe_float_conversion(form.other_deductions.data, 0),
            
            # Advanced salary components
            'overtime_rate_multiplier': safe_float_conversion(form.overtime_rate_multiplier.data, 1.5),
            'weekend_bonus_percent': safe_float_conversion(form.weekend_bonus_percent.data, 0),
            'holiday_bonus_percent': safe_float_conversion(form.holiday_bonus_percent.data, 0),
            
            # Revenue sharing configurations
            'revenue_share_percent': safe_float_conversion(form.revenue_share_percent.data, 0),
            'company_expense_deduction': safe_float_conversion(form.company_expense_deduction.data, 0),
            
            # Fixed salary components
            'fixed_monthly_salary': safe_float_conversion(form.fixed_monthly_salary.data, 0),
            'allowances': safe_float_conversion(form.allowances.data, 0),
            
            # Legacy scheme configurations (maintained for compatibility)
            'fixed_amount': safe_float_conversion(form.fixed_amount.data, 0),
            'per_trip_amount': safe_float_conversion(form.per_trip_amount.data, 0),
            'base_amount': safe_float_conversion(form.base_amount.data, 0),
            'incentive_percent': safe_float_conversion(form.incentive_percent.data, 0),
            'slab1_max': safe_float_conversion(form.slab1_max.data, 0),
            'slab1_percent': safe_float_conversion(form.slab1_percent.data, 0),
            'slab2_max': safe_float_conversion(form.slab2_max.data, 0),
            'slab2_percent': safe_float_conversion(form.slab2_percent.data, 0),
            'slab3_percent': safe_float_conversion(form.slab3_percent.data, 0)
        }
        
        # Validation for salary method configurations
        if not _validate_salary_method_config(form.scheme_type.data, config):
            flash('Please fill in required fields for the selected salary method.', 'error')
            return render_template('admin/duty_scheme_form.html', form=form, title=f'Edit {scheme.name}')
        
        # Update scheme
        scheme.name = form.name.data
        scheme.scheme_type = form.scheme_type.data
        scheme.branch_id = int(form.branch_id.data) if form.branch_id.data and form.branch_id.data != 0 else None
        scheme.minimum_guarantee = form.bmg_amount.data or 0.0
        scheme.calculation_formula = form.calculation_formula.data or ''
        scheme.effective_from = form.effective_from.data or datetime.now().date()
        scheme.effective_until = form.effective_until.data
        scheme.set_config(config)
        scheme.updated_at = datetime.now()
        
        db.session.commit()
        
        log_audit('edit_duty_scheme', 'duty_scheme', scheme.id,
                 {'name': scheme.name, 'type': scheme.scheme_type, 'branch_id': scheme.branch_id})
        
        flash(f'Salary method "{scheme.name}" updated successfully!', 'success')
        return redirect(url_for('admin.duty_schemes'))
    
    return render_template('admin/duty_scheme_form.html', form=form, title=f'Edit {scheme.name}', scheme=scheme)

@admin_bp.route('/duty-schemes/<int:scheme_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_duty_scheme(scheme_id):
    scheme = DutyScheme.query.get_or_404(scheme_id)
    
    # Check if scheme is being used by active duties
    active_duties = Duty.query.filter_by(duty_scheme_id=scheme.id).filter(
        Duty.status.in_(['pending', 'in_progress'])
    ).count()
    
    if active_duties > 0:
        flash(f'Cannot delete "{scheme.name}" - it is currently being used by {active_duties} active duties.', 'error')
        return redirect(url_for('admin.duty_schemes'))
    
    # Soft delete by marking as inactive
    scheme.is_active = False
    scheme.updated_at = datetime.now()
    
    db.session.commit()
    
    log_audit('delete_duty_scheme', 'duty_scheme', scheme.id,
             {'name': scheme.name, 'type': scheme.scheme_type})
    
    flash(f'Salary method "{scheme.name}" has been deleted.', 'success')
    return redirect(url_for('admin.duty_schemes'))

@admin_bp.route('/duty-schemes/<int:scheme_id>/duplicate', methods=['POST'])
@login_required
@admin_required
def duplicate_duty_scheme(scheme_id):
    original = DutyScheme.query.get_or_404(scheme_id)
    
    # Create duplicate
    duplicate = DutyScheme()
    duplicate.name = f"{original.name} (Copy)"
    duplicate.scheme_type = original.scheme_type
    duplicate.branch_id = original.branch_id
    duplicate.minimum_guarantee = original.minimum_guarantee
    duplicate.calculation_formula = original.calculation_formula
    duplicate.effective_from = datetime.now().date()
    duplicate.effective_until = original.effective_until
    duplicate.configuration = original.configuration
    duplicate.created_by = current_user.id
    
    db.session.add(duplicate)
    db.session.commit()
    
    log_audit('duplicate_duty_scheme', 'duty_scheme', duplicate.id,
             {'original_id': original.id, 'name': duplicate.name})
    
    flash(f'Salary method duplicated as "{duplicate.name}".', 'success')
    return redirect(url_for('admin.edit_duty_scheme', scheme_id=duplicate.id))

@admin_bp.route('/duty-schemes/bulk-action', methods=['POST'])
@login_required
@admin_required
def bulk_duty_schemes_action():
    """Handle bulk operations on duty schemes"""
    try:
        action = request.form.get('action')
        scheme_ids = request.form.getlist('scheme_ids')
        
        if not scheme_ids:
            flash('No duty schemes selected', 'warning')
            return redirect(url_for('admin.duty_schemes'))
        
        scheme_ids = [int(id) for id in scheme_ids]
        schemes = DutyScheme.query.filter(DutyScheme.id.in_(scheme_ids)).all()
        
        if action == 'activate':
            for scheme in schemes:
                scheme.is_active = True
            db.session.commit()
            flash(f'{len(schemes)} duty schemes activated successfully')
            
        elif action == 'deactivate':
            for scheme in schemes:
                scheme.is_active = False
            db.session.commit()
            flash(f'{len(schemes)} duty schemes deactivated successfully')
            
        elif action == 'delete':
            # Check if any scheme is currently in use
            in_use_schemes = []
            for scheme in schemes:
                # Check if scheme is referenced by any drivers or duties
                from models import Driver, Duty
                if Driver.query.filter_by(duty_scheme_id=scheme.id).first() or \
                   Duty.query.filter_by(duty_scheme_id=scheme.id).first():
                    in_use_schemes.append(scheme.name)
                    
            if in_use_schemes:
                flash(f'Cannot delete schemes in use: {", ".join(in_use_schemes)}', 'error')
            else:
                for scheme in schemes:
                    scheme.is_active = False  # Soft delete
                db.session.commit()
                flash(f'{len(schemes)} duty schemes deleted successfully')
                
        else:
            flash('Invalid bulk action', 'error')
            
        # Log the bulk action
        log_audit('bulk_duty_schemes_action', 'duty_scheme', 0,
                 {'action': action, 'scheme_count': len(schemes), 'scheme_ids': scheme_ids})
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error performing bulk action: {str(e)}', 'error')
    
    return redirect(url_for('admin.duty_schemes'))

@admin_bp.route('/duty-schemes/compare')
@login_required
@admin_required
def compare_duty_schemes():
    """Compare multiple duty schemes"""
    scheme_ids = request.args.getlist('ids')
    
    if not scheme_ids or len(scheme_ids) < 2:
        flash('Please select at least 2 duty schemes to compare', 'warning')
        return redirect(url_for('admin.duty_schemes'))
    
    try:
        scheme_ids = [int(id) for id in scheme_ids]
        schemes = DutyScheme.query.filter(DutyScheme.id.in_(scheme_ids)).all()
        
        if len(schemes) != len(scheme_ids):
            flash('One or more selected schemes not found', 'error')
            return redirect(url_for('admin.duty_schemes'))
        
        # Sample calculation scenarios for comparison
        test_scenarios = [
            {'revenue': 1000, 'trips': 5, 'name': 'Low Revenue Day'},
            {'revenue': 2500, 'trips': 10, 'name': 'Average Day'},
            {'revenue': 5000, 'trips': 15, 'name': 'High Revenue Day'},
            {'revenue': 8000, 'trips': 20, 'name': 'Exceptional Day'}
        ]
        
        comparison_data = []
        for scenario in test_scenarios:
            scenario_data = {'scenario': scenario}
            for scheme in schemes:
                try:
                    from utils_main import calculate_earnings
                    earnings_data = calculate_earnings(scheme, scenario['revenue'], scenario['trips'])
                    scenario_data[f'scheme_{scheme.id}'] = earnings_data
                except Exception as e:
                    scenario_data[f'scheme_{scheme.id}'] = {'earnings': 0, 'error': str(e)}
            comparison_data.append(scenario_data)
        
        # Log the comparison action
        log_audit('compare_duty_schemes', 'duty_scheme', 0,
                 {'scheme_count': len(schemes), 'scheme_ids': scheme_ids})
        
        return render_template('admin/duty_schemes_comparison.html', 
                             schemes=schemes, 
                             comparison_data=comparison_data)
        
    except Exception as e:
        flash(f'Error comparing schemes: {str(e)}', 'error')
        return redirect(url_for('admin.duty_schemes'))

@admin_bp.route('/vehicle-tracking')
@login_required
@admin_required
def vehicle_tracking():
    """Vehicle tracking dashboard with odometer and CNG continuity"""
    page = request.args.get('page', 1, type=int)
    vehicle_filter = request.args.get('vehicle_id', type=int)
    date_filter = request.args.get('date_filter')
    
    # Base query
    query = VehicleTracking.query
    
    # Apply filters
    if vehicle_filter:
        query = query.filter_by(vehicle_id=vehicle_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(VehicleTracking.recorded_at) == filter_date)
        except ValueError:
            pass
    
    # Get tracking records
    tracking_records = query.order_by(desc(VehicleTracking.recorded_at)).paginate(
        page=page, per_page=50, error_out=False)
    
    # Get vehicles for filter dropdown
    vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE).all()
    
    return render_template('admin/vehicle_tracking.html',
                         tracking_records=tracking_records,
                         vehicles=vehicles,
                         vehicle_filter=vehicle_filter,
                         date_filter=date_filter)

@admin_bp.route('/vehicle-tracking/<int:vehicle_id>')
@login_required
@admin_required
def vehicle_tracking_detail(vehicle_id):
    """Detailed vehicle tracking with continuity analysis"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to last 30 days
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Get vehicle tracking records
    tracking_records = VehicleTracking.get_vehicle_continuity(
        vehicle_id, 
        datetime.strptime(start_date, '%Y-%m-%d'),
        datetime.strptime(end_date, '%Y-%m-%d')
    )
    
    # Validate continuity
    continuity_errors = VehicleTracking.validate_continuity(vehicle_id)
    
    # Calculate summary statistics
    total_distance = sum(record.distance_traveled or 0 for record in tracking_records)
    total_cng_used = sum(record.cng_quantity or 0 for record in tracking_records if record.cng_quantity)
    avg_efficiency = round(total_distance / total_cng_used, 2) if total_cng_used > 0 else 0
    
    # Group CNG points by usage frequency
    cng_points = {}
    for record in tracking_records:
        if record.cng_point:
            cng_points[record.cng_point] = cng_points.get(record.cng_point, 0) + 1
    
    return render_template('admin/vehicle_tracking_detail.html',
                         vehicle=vehicle,
                         tracking_records=tracking_records,
                         continuity_errors=continuity_errors,
                         total_distance=total_distance,
                         total_cng_used=total_cng_used,
                         avg_efficiency=avg_efficiency,
                         cng_points=cng_points,
                         start_date=start_date,
                         end_date=end_date)

@admin_bp.route('/vehicle-tracking/validate/<int:vehicle_id>')
@login_required
@admin_required
def validate_vehicle_continuity(vehicle_id):
    """Run continuity validation for a specific vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    errors = VehicleTracking.validate_continuity(vehicle_id)
    
    if errors:
        flash(f'Found {len(errors)} continuity issues for {vehicle.registration_number}', 'warning')
        for error in errors[:5]:  # Show first 5 errors
            flash(error, 'error')
    else:
        flash(f'No continuity issues found for {vehicle.registration_number}', 'success')
    
    return redirect(url_for('admin.vehicle_tracking_detail', vehicle_id=vehicle_id))

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    # Revenue by branch (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    branch_revenue = db.session.query(
        Branch.name,
        func.sum(Duty.revenue).label('total_revenue')
    ).join(Duty).filter(
        Duty.start_time >= thirty_days_ago
    ).group_by(Branch.id, Branch.name).all()
    
    # Top drivers by earnings
    top_drivers = db.session.query(
        Driver.full_name,
        Branch.name.label('branch_name'),
        func.sum(Duty.driver_earnings).label('total_earnings')
    ).join(Branch, Driver.branch_id == Branch.id) \
     .join(Duty, Driver.id == Duty.driver_id) \
     .filter(Duty.start_time >= thirty_days_ago) \
     .group_by(Driver.id, Driver.full_name, Branch.name) \
     .order_by(desc(func.sum(Duty.driver_earnings))).limit(10).all()
    
    # Vehicle utilization
    vehicle_stats = db.session.query(
        Vehicle.registration_number,
        Branch.name.label('branch_name'),
        func.count(Duty.id).label('duty_count'),
        func.sum(Duty.distance_km).label('total_distance')
    ).join(Branch, Vehicle.branch_id == Branch.id) \
     .outerjoin(Duty, Vehicle.id == Duty.vehicle_id) \
     .filter(Vehicle.status == VehicleStatus.ACTIVE) \
     .group_by(Vehicle.id, Vehicle.registration_number, Branch.name).all()
    
    return render_template('admin/reports.html',
                         branch_revenue=branch_revenue,
                         top_drivers=top_drivers,
                         vehicle_stats=vehicle_stats)

@admin_bp.route('/api/revenue-chart')
@login_required
@admin_required
def revenue_chart():
    # Get last 7 days revenue data
    days = []
    revenues = []
    
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        revenue = db.session.query(func.sum(Duty.revenue)).filter(
            func.date(Duty.start_time) == date
        ).scalar() or 0
        
        days.append(date.strftime('%m/%d'))
        revenues.append(float(revenue))
    
    return jsonify({
        'labels': days,
        'data': revenues
    })

@admin_bp.route('/api/branch-performance')
@login_required
@admin_required
def branch_performance():
    today = datetime.now().date()
    
    branch_data = db.session.query(
        Branch.name,
        Branch.target_revenue,
        func.sum(Duty.revenue).label('actual_revenue')
    ).outerjoin(Duty, func.date(Duty.start_time) == today) \
     .filter(Branch.is_active == True) \
     .group_by(Branch.id, Branch.name, Branch.target_revenue).all()
    
    return jsonify([{
        'branch': row.name,
        'target': float(row.target_revenue),
        'actual': float(row.actual_revenue or 0)
    } for row in branch_data])

# Uber Integration Management Routes

@admin_bp.route('/uber')
@login_required
@admin_required
def uber_integration():
    """Main Uber integration management page"""
    try:
        from uber_sync import uber_sync
        
        # Get current settings
        settings = uber_sync.get_sync_settings()
        if not settings:
            settings = uber_sync.create_default_settings(current_user.id)
    except Exception as e:
        flash(f'Uber integration not available: {str(e)}', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    # Get recent sync jobs
    recent_jobs = UberSyncJob.query.order_by(desc(UberSyncJob.created_at)).limit(10).all()
    
    # Get sync statistics
    total_jobs = UberSyncJob.query.count()
    successful_jobs = UberSyncJob.query.filter_by(status='completed').count()
    failed_jobs = UberSyncJob.query.filter_by(status='failed').count()
    pending_jobs = UberSyncJob.query.filter_by(status='pending').count()
    
    # Get sync counts by type
    vehicle_synced = Vehicle.query.filter_by(uber_sync_status='synced').count()
    driver_synced = Driver.query.filter_by(uber_sync_status='synced').count()
    vehicle_failed = Vehicle.query.filter_by(uber_sync_status='failed').count()
    driver_failed = Driver.query.filter_by(uber_sync_status='failed').count()
    
    return render_template('admin/uber_integration.html',
                         settings=settings,
                         recent_jobs=recent_jobs,
                         stats={
                             'total_jobs': total_jobs,
                             'successful_jobs': successful_jobs,
                             'failed_jobs': failed_jobs,
                             'pending_jobs': pending_jobs,
                             'vehicle_synced': vehicle_synced,
                             'driver_synced': driver_synced,
                             'vehicle_failed': vehicle_failed,
                             'driver_failed': driver_failed
                         })

@admin_bp.route('/uber/test-connection')
@login_required
@admin_required
def uber_test_connection():
    """Test connection to Uber APIs"""
    try:
        from uber_sync import uber_sync
        
        result = uber_sync.test_connection()
    except Exception as e:
        flash(f'Uber integration not available: {str(e)}', 'error')
        return redirect(url_for('admin.uber_integration'))
    
    if result['status'] == 'success':
        flash(f"Connection successful! {result['message']}", 'success')
    else:
        flash(f"Connection failed: {result['message']}", 'error')
    
    return redirect(url_for('admin.uber_integration'))

@admin_bp.route('/uber/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def uber_settings():
    """Manage Uber integration settings"""
    from uber_sync import uber_sync
    
    settings = uber_sync.get_sync_settings()
    if not settings:
        settings = uber_sync.create_default_settings(current_user.id)
    
    if request.method == 'POST':
        try:
            # Update settings
            settings.is_enabled = request.form.get('is_enabled') == 'on'
            settings.auto_sync_vehicles = request.form.get('auto_sync_vehicles') == 'on'
            settings.auto_sync_drivers = request.form.get('auto_sync_drivers') == 'on'
            settings.auto_sync_trips = request.form.get('auto_sync_trips') == 'on'
            settings.sync_frequency_hours = int(request.form.get('sync_frequency_hours', 24))
            settings.sync_direction_vehicles = request.form.get('sync_direction_vehicles', 'bidirectional')
            settings.sync_direction_drivers = request.form.get('sync_direction_drivers', 'to_uber')
            settings.max_retry_attempts = int(request.form.get('max_retry_attempts', 3))
            settings.error_notification_email = request.form.get('error_notification_email', '')
            settings.api_calls_per_minute = int(request.form.get('api_calls_per_minute', 60))
            settings.batch_size = int(request.form.get('batch_size', 50))
            settings.updated_by = current_user.id
            settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            log_audit('update_uber_settings', 'uber_settings', settings.id,
                     {'action': 'Updated Uber integration settings'})
            
            flash('Uber integration settings updated successfully!', 'success')
            return redirect(url_for('admin.uber_integration'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')
    
    return render_template('admin/uber_settings.html', settings=settings)

@admin_bp.route('/uber/sync/<job_type>')
@login_required
@admin_required
def uber_start_sync(job_type):
    """Start a sync job"""
    from uber_sync import uber_sync
    
    # Validate job type
    if job_type not in ['vehicles', 'drivers', 'trips']:
        flash('Invalid sync job type', 'error')
        return redirect(url_for('admin.uber_integration'))
    
    # Get sync direction from settings
    settings = uber_sync.get_sync_settings()
    if not settings:
        flash('Please configure Uber integration settings first', 'error')
        return redirect(url_for('admin.uber_settings'))
    
    if not settings.is_enabled:
        flash('Uber integration is not enabled', 'error')
        return redirect(url_for('admin.uber_integration'))
    
    try:
        # Determine sync direction
        if job_type == 'vehicles':
            sync_direction = settings.sync_direction_vehicles
        elif job_type == 'drivers':
            sync_direction = settings.sync_direction_drivers
        else:  # trips
            sync_direction = 'from_uber'  # trips are always from Uber
        
        # Create and run sync job
        config = {}
        if job_type == 'trips':
            # For trips, sync last 7 days by default
            config = {
                'start_date': (datetime.utcnow() - timedelta(days=7)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            }
        
        job = uber_sync.create_sync_job(job_type, sync_direction, current_user.id, config)
        result = uber_sync.run_sync_job(job.id)
        
        if result['status'] == 'completed':
            flash(f"Sync completed! {result['message']}", 'success')
        else:
            flash(f"Sync failed: {result['message']}", 'error')
        
        log_audit('start_uber_sync', 'uber_sync_job', job.id,
                 {'job_type': job_type, 'action': f'Started {job_type} sync job'})
        
    except Exception as e:
        flash(f'Error starting sync job: {str(e)}', 'error')
    
    return redirect(url_for('admin.uber_integration'))

@admin_bp.route('/uber/sync-jobs')
@login_required
@admin_required
def uber_sync_jobs():
    """View all sync jobs"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    jobs = UberSyncJob.query.order_by(desc(UberSyncJob.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/uber_sync_jobs.html', jobs=jobs)

@admin_bp.route('/uber/sync-job/<int:job_id>')
@login_required
@admin_required
def uber_sync_job_details(job_id):
    """View detailed sync job information"""
    job = UberSyncJob.query.get_or_404(job_id)
    
    # Get sync logs for this job
    logs = UberSyncLog.query.filter_by(sync_job_id=job_id).order_by(
        desc(UberSyncLog.timestamp)
    ).all()
    
    return render_template('admin/uber_sync_job_details.html', job=job, logs=logs)

@admin_bp.route('/uber/sync-status')
@login_required
@admin_required
def uber_sync_status():
    """View sync status for all vehicles and drivers"""
    # Get vehicles with sync status
    vehicles = Vehicle.query.filter(Vehicle.uber_sync_status.isnot(None)).all()
    
    # Get drivers with sync status  
    drivers = Driver.query.filter(Driver.uber_sync_status.isnot(None)).all()
    
    return render_template('admin/uber_sync_status.html', vehicles=vehicles, drivers=drivers)

@admin_bp.route('/uber/reset-sync/<record_type>/<int:record_id>')
@login_required
@admin_required
def uber_reset_sync(record_type, record_id):
    """Reset sync status for a record"""
    try:
        if record_type == 'vehicle':
            record = Vehicle.query.get_or_404(record_id)
            record.uber_sync_status = 'none'
            record.uber_sync_error = None
            record.uber_last_sync = None
            
        elif record_type == 'driver':
            record = Driver.query.get_or_404(record_id)
            record.uber_sync_status = 'none' 
            record.uber_sync_error = None
            record.uber_last_sync = None
            
        else:
            flash('Invalid record type', 'error')
            return redirect(url_for('admin.uber_sync_status'))
        
        db.session.commit()
        
        log_audit('reset_uber_sync', f'uber_{record_type}', record_id,
                 {'action': f'Reset Uber sync status for {record_type}'})
        
        flash(f'Sync status reset for {record_type}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting sync status: {str(e)}', 'error')
    
    return redirect(url_for('admin.uber_sync_status'))


# Duty Approval Routes
@admin_bp.route('/duties/pending')
@login_required
@admin_required
def pending_duties():
    """View duties pending approval"""
    page = request.args.get('page', 1, type=int)
    branch_filter = request.args.get('branch', '', type=int)
    date_filter = request.args.get('date', '')
    
    query = Duty.query.filter_by(status=DutyStatus.PENDING_APPROVAL)
    
    if branch_filter:
        query = query.filter(Duty.branch_id == branch_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Duty.actual_end) == filter_date)
        except ValueError:
            pass
    
    duties = query.order_by(desc(Duty.submitted_at)).paginate(page=page, per_page=20, error_out=False)
    branches = Branch.query.filter_by(is_active=True).all()
    
    # Load photos for each duty
    for duty in duties.items:
        duty.all_photos = Photo.query.filter_by(duty_id=duty.id).order_by(Photo.timestamp.desc()).all()
    
    return render_template('admin/pending_duties.html', 
                         duties=duties, 
                         branches=branches,
                         branch_filter=branch_filter,
                         date_filter=date_filter)

@admin_bp.route('/duties/<int:duty_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_duty(duty_id):
    """Approve a duty submission"""
    duty = Duty.query.get_or_404(duty_id)
    
    if duty.status != DutyStatus.PENDING_APPROVAL:
        flash('Duty is not pending approval.', 'error')
        return redirect(url_for('admin.pending_duties'))
    
    # Approve the duty
    duty.status = DutyStatus.COMPLETED
    duty.reviewed_by = current_user.id
    duty.reviewed_at = datetime.utcnow()
    duty.approved_at = datetime.utcnow()
    
    # Update driver earnings only after approval
    if duty.driver and duty.driver_earnings:
        duty.driver.total_earnings += duty.driver_earnings
    
    db.session.commit()
    
    log_audit('approve_duty', 'duty', duty_id,
             {'duty_id': duty_id, 'driver': duty.driver.full_name if duty.driver else 'Unknown',
              'earnings': duty.driver_earnings})
    
    flash(f'Duty approved for {duty.driver.full_name if duty.driver else "Unknown"}. Earnings: ₹{duty.driver_earnings:.2f}', 'success')
    return redirect(url_for('admin.pending_duties'))

@admin_bp.route('/duties/<int:duty_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_duty(duty_id):
    """Reject a duty submission"""
    duty = Duty.query.get_or_404(duty_id)
    
    if duty.status != DutyStatus.PENDING_APPROVAL:
        flash('Duty is not pending approval.', 'error')
        return redirect(url_for('admin.pending_duties'))
    
    rejection_reason = request.form.get('rejection_reason', '').strip()
    if not rejection_reason:
        flash('Please provide a reason for rejection.', 'error')
        return redirect(url_for('admin.pending_duties'))
    
    # Reject the duty
    duty.status = DutyStatus.REJECTED
    duty.reviewed_by = current_user.id
    duty.reviewed_at = datetime.utcnow()
    duty.rejection_reason = rejection_reason
    
    # Make vehicle available again since duty is rejected
    if duty.vehicle:
        duty.vehicle.is_available = True
    
    # Reset driver's current vehicle
    if duty.driver:
        duty.driver.current_vehicle_id = None
    
    db.session.commit()
    
    log_audit('reject_duty', 'duty', duty_id,
             {'duty_id': duty_id, 'driver': duty.driver.full_name if duty.driver else 'Unknown',
              'reason': rejection_reason})
    
    flash(f'Duty rejected for {duty.driver.full_name if duty.driver else "Unknown"}. Reason: {rejection_reason}', 'warning')
    return redirect(url_for('admin.pending_duties'))


# Audit Log Management Routes
@admin_bp.route('/audit-logs')
@login_required  
@admin_required
def audit_logs():
    """View audit logs with filtering and search"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Filters
    user_filter = request.args.get('user', '', type=int)
    action_filter = request.args.get('action', '')
    entity_type_filter = request.args.get('entity_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search_term = request.args.get('search', '')
    success_filter = request.args.get('success', '')
    
    # Build query
    query = AuditLog.query.join(User)
    
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
        
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
        
    if entity_type_filter:
        query = query.filter(AuditLog.entity_type == entity_type_filter)
        
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= from_date)
        except ValueError:
            pass
            
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire day
            to_date = to_date + timedelta(days=1)
            query = query.filter(AuditLog.created_at < to_date)
        except ValueError:
            pass
            
    if search_term:
        query = query.filter(
            db.or_(
                AuditLog.action.ilike(f'%{search_term}%'),
                AuditLog.new_values.ilike(f'%{search_term}%'),
                AuditLog.old_values.ilike(f'%{search_term}%'),
                User.username.ilike(f'%{search_term}%'),
                AuditLog.ip_address.ilike(f'%{search_term}%')
            )
        )
        
    if success_filter:
        success_bool = success_filter.lower() == 'true'
        query = query.filter(AuditLog.success == success_bool)
    
    # Order by most recent first
    audit_logs = query.order_by(desc(AuditLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options
    users = User.query.filter(User.role.in_([UserRole.ADMIN, UserRole.MANAGER])).all()
    actions = db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    entity_types = db.session.query(AuditLog.entity_type).distinct().filter(
        AuditLog.entity_type.isnot(None)
    ).order_by(AuditLog.entity_type).all()
    
    # Statistics
    stats = {
        'total_logs': AuditLog.query.count(),
        'today_logs': AuditLog.query.filter(
            AuditLog.created_at >= datetime.now().date()
        ).count(),
        'failed_actions': AuditLog.query.filter(AuditLog.success == False).count(),
        'unique_users': db.session.query(AuditLog.user_id).distinct().count()
    }
    
    return render_template('admin/audit_logs.html',
                         audit_logs=audit_logs,
                         users=users,
                         actions=[a[0] for a in actions],
                         entity_types=[e[0] for e in entity_types],
                         user_filter=user_filter,
                         action_filter=action_filter,
                         entity_type_filter=entity_type_filter,
                         date_from=date_from,
                         date_to=date_to,
                         search_term=search_term,
                         success_filter=success_filter,
                         per_page=per_page,
                         stats=stats)

@admin_bp.route('/audit-logs/<int:log_id>')
@login_required
@admin_required  
def view_audit_log(log_id):
    """View detailed audit log entry"""
    audit_log = AuditLog.query.get_or_404(log_id)
    
    # Import security utilities
    from utils.security import get_sanitized_audit_data
    
    # Get sanitized data for display
    sanitized_data = get_sanitized_audit_data(audit_log)
    
    # Parse changed fields
    changed_fields = []
    try:
        if audit_log.changed_fields:
            changed_fields = json.loads(audit_log.changed_fields)
    except (json.JSONDecodeError, TypeError):
        pass
    
    return render_template('admin/audit_log_detail.html',
                         audit_log=audit_log,
                         old_values=sanitized_data['old_values'],
                         new_values=sanitized_data['new_values'],
                         changed_fields=changed_fields,
                         sanitized_error=sanitized_data['error_message'],
                         masked_ip=sanitized_data['masked_ip'],
                         masked_session=sanitized_data['masked_session'])

@admin_bp.route('/audit-logs/export')
@login_required
@admin_required
def export_audit_logs():
    """Export audit logs to CSV with security protections"""
    # Import security utilities
    from utils.security import CSVSanitizer, AuditDataSanitizer
    
    # Apply same filters as main view
    user_filter = request.args.get('user', '', type=int)
    action_filter = request.args.get('action', '')
    entity_type_filter = request.args.get('entity_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search_term = request.args.get('search', '')
    success_filter = request.args.get('success', '')
    
    query = AuditLog.query.join(User)
    
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
        
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
        
    if entity_type_filter:
        query = query.filter(AuditLog.entity_type == entity_type_filter)
        
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= from_date)
        except ValueError:
            pass
            
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < to_date)
        except ValueError:
            pass
            
    if search_term:
        query = query.filter(
            db.or_(
                AuditLog.action.ilike(f'%{search_term}%'),
                AuditLog.new_values.ilike(f'%{search_term}%'),
                User.username.ilike(f'%{search_term}%')
            )
        )
        
    if success_filter:
        success_bool = success_filter.lower() == 'true'
        query = query.filter(AuditLog.success == success_bool)
    
    # Limit to prevent memory issues (max 10,000 rows for security)
    audit_logs = query.order_by(desc(AuditLog.created_at)).limit(10000).all()
    
    # Generate CSV with security protections
    import defusedcsv as csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Security header with metadata
    metadata_row = [
        f'# PLS TRAVELS AUDIT LOG EXPORT',
        f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'# Records: {len(audit_logs)}/10000 max',
        f'# Note: Sensitive data has been sanitized for security'
    ]
    writer.writerow(CSVSanitizer.sanitize_csv_row(metadata_row))
    
    # Column headers
    header_row = [
        'Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID', 
        'Success', 'IP Address (Masked)', 'Details (Sanitized)', 'Error Message (Sanitized)'
    ]
    writer.writerow(CSVSanitizer.sanitize_csv_row(header_row))
    
    # Data with sanitization and CSV injection protection
    sanitizer = AuditDataSanitizer()
    for log in audit_logs:
        # Sanitize sensitive data
        sanitized_details = sanitizer.sanitize_json_data(log.new_values)
        sanitized_error = sanitizer.sanitize_error_message(log.error_message or '')
        masked_ip = sanitizer.mask_ip_address(log.ip_address or '')
        
        # Prepare row data
        row_data = [
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'Unknown',
            log.action,
            log.entity_type or '',
            log.entity_id or '',
            'Yes' if log.success else 'No',
            masked_ip,
            json.dumps(sanitized_details) if sanitized_details else '',
            sanitized_error
        ]
        
        # Apply CSV injection protection
        writer.writerow(CSVSanitizer.sanitize_csv_row(row_data))
    
    output.seek(0)
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=audit_logs_secure_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@admin_bp.route('/vehicles/<int:vehicle_id>/documents/<document_type>')
@login_required
def serve_vehicle_document(vehicle_id, document_type):
    """Serve vehicle document files with permission checks"""
    # Check if user has permission to access vehicle documents
    if current_user.role.name not in ['ADMIN', 'MANAGER', 'DRIVER']:
        return "Access denied", 403
    
    # Get the vehicle
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # For drivers, only allow access if they are assigned to this vehicle or have an active duty
    if current_user.role.name == 'DRIVER':
        driver = Driver.query.filter_by(user_id=current_user.id).first()
        if not driver:
            return "Access denied", 403
        
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
            return "Access denied", 403
    
    # Get document filename based on type
    document_field_map = {
        'registration': vehicle.registration_document,
        'insurance': vehicle.insurance_document,
        'fitness': vehicle.fitness_document,
        'permit': vehicle.permit_document,
        'pollution': vehicle.pollution_document,
        'other': vehicle.other_document
    }
    
    if document_type not in document_field_map:
        return "Invalid document type", 400
        
    filename = document_field_map[document_type]
    if not filename:
        return "Document not found", 404
    
    # Serve the file
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    file_path = os.path.join(upload_dir, filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404
        
    return send_from_directory(upload_dir, filename)
