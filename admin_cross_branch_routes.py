from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, or_
from models import (db, VehicleAssignment, Vehicle, Driver, Branch, User, 
                   VehicleStatus, DriverStatus, UserStatus, AssignmentStatus, UserRole)
from services.vehicle_service import VehicleService
from services.audit_service import AuditService

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_audit(action, entity_type, entity_id, details=None):
    """Simple audit logging for cross-branch operations"""
    audit_service = AuditService()
    audit_service.log_action(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        user_id=current_user.id if current_user.is_authenticated else None
    )

admin_cross_branch_bp = Blueprint('admin_cross_branch', __name__, url_prefix='/admin/cross-branch')

@admin_cross_branch_bp.route('/dashboard')
@login_required
@admin_required
def cross_branch_dashboard():
    """Cross-branch vehicle assignment dashboard"""
    # Get pending cross-branch assignments
    pending_assignments = VehicleAssignment.query.filter(
        VehicleAssignment.is_cross_branch == True,
        VehicleAssignment.status == AssignmentStatus.PENDING_APPROVAL
    ).join(Driver).join(Vehicle).order_by(desc(VehicleAssignment.created_at)).limit(10).all()
    
    # Get active cross-branch assignments
    active_assignments = VehicleAssignment.query.filter(
        VehicleAssignment.is_cross_branch == True,
        VehicleAssignment.status == AssignmentStatus.ACTIVE,
        VehicleAssignment.end_date.is_(None)
    ).join(Driver).join(Vehicle).order_by(desc(VehicleAssignment.created_at)).limit(10).all()
    
    # Get expiring assignments (within 7 days)
    one_week_from_now = datetime.utcnow() + timedelta(days=7)
    expiring_assignments = VehicleAssignment.query.filter(
        VehicleAssignment.is_cross_branch == True,
        VehicleAssignment.cross_branch_expires_at <= one_week_from_now,
        VehicleAssignment.cross_branch_expires_at > datetime.utcnow(),
        VehicleAssignment.status == AssignmentStatus.ACTIVE
    ).join(Driver).join(Vehicle).order_by(VehicleAssignment.cross_branch_expires_at).all()
    
    # Statistics
    stats = {
        'total_cross_branch': VehicleAssignment.query.filter(VehicleAssignment.is_cross_branch == True).count(),
        'pending_approval': len(pending_assignments),
        'active_assignments': len(active_assignments),
        'expiring_soon': len(expiring_assignments),
        'branches_count': Branch.query.filter(Branch.is_active == True).count()
    }
    
    return render_template('admin/cross_branch/dashboard.html',
                         pending_assignments=pending_assignments,
                         active_assignments=active_assignments,
                         expiring_assignments=expiring_assignments,
                         stats=stats)

@admin_cross_branch_bp.route('/assignments')
@login_required
@admin_required
def list_assignments():
    """List all cross-branch assignments with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    status_filter = request.args.get('status', '')
    branch_filter = request.args.get('branch', '')
    
    # Build query
    query = VehicleAssignment.query.filter(
        VehicleAssignment.is_cross_branch == True
    ).join(Driver).join(Vehicle)
    
    if status_filter:
        try:
            status_enum = AssignmentStatus(status_filter)
            query = query.filter(VehicleAssignment.status == status_enum)
        except ValueError:
            # Invalid status filter, ignore it
            pass
    
    if branch_filter:
        try:
            branch_id = int(branch_filter)
            query = query.filter(
                or_(Driver.branch_id == branch_id, Vehicle.branch_id == branch_id)
            )
        except (ValueError, TypeError):
            # Invalid branch filter, ignore it
            pass
    
    # Order by priority and recency
    assignments = query.order_by(
        desc(VehicleAssignment.created_at)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get filter options
    branches = Branch.query.filter(Branch.is_active == True).order_by(Branch.name).all()
    statuses = [status.value for status in AssignmentStatus]
    
    return render_template('admin/cross_branch/list.html',
                         assignments=assignments,
                         branches=branches,
                         statuses=statuses,
                         current_filters={
                             'status': status_filter,
                             'branch': branch_filter
                         })

@admin_cross_branch_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assignment():
    """Create a new cross-branch vehicle assignment"""
    if request.method == 'GET':
        # Get all active drivers and vehicles for selection
        drivers = Driver.query.filter(
            Driver.status == DriverStatus.ACTIVE
        ).join(User).filter(User.status == UserStatus.ACTIVE).order_by(Driver.full_name).all()
        
        vehicles = Vehicle.query.filter(
            Vehicle.status == VehicleStatus.ACTIVE,
            Vehicle.is_available == True
        ).order_by(Vehicle.registration_number).all()
        
        branches = Branch.query.filter(Branch.is_active == True).order_by(Branch.name).all()
        
        return render_template('admin/cross_branch/create.html',
                             drivers=drivers,
                             vehicles=vehicles,
                             branches=branches)
    
    # Handle POST request
    try:
        driver_id = int(request.form['driver_id'])
        vehicle_id = int(request.form['vehicle_id'])
        reason = request.form['reason']
        assignment_type = request.form.get('assignment_type', 'cross_branch')
        expires_at_str = request.form.get('expires_at')
        
        expires_at = None
        if expires_at_str:
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        
        # Use VehicleService to create the assignment (pending approval)
        vehicle_service = VehicleService()
        success, error_message = vehicle_service.assign_vehicle(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            assigned_by=current_user.id,
            allow_cross_branch=True,
            cross_branch_reason=reason,
            assignment_type=assignment_type,
            cross_branch_expires_at=expires_at,
            create_pending=True  # Create as pending approval
        )
        
        if success:
            flash('Cross-branch vehicle assignment created and is pending approval!', 'success')
            return redirect(url_for('admin_cross_branch.cross_branch_dashboard'))
        else:
            flash(f'Failed to create assignment: {error_message}', 'error')
            
    except ValueError as e:
        flash(f'Invalid form data: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error creating assignment: {str(e)}', 'error')
    
    # Redirect back to form on error
    return redirect(url_for('admin_cross_branch.create_assignment'))

@admin_cross_branch_bp.route('/approve/<int:assignment_id>', methods=['POST'])
@login_required
@admin_required
def approve_assignment(assignment_id):
    """Approve a pending cross-branch assignment"""
    assignment = VehicleAssignment.query.get_or_404(assignment_id)
    
    if not assignment.is_cross_branch:
        return jsonify({'success': False, 'message': 'Not a cross-branch assignment'})
    
    if assignment.status != AssignmentStatus.PENDING_APPROVAL:
        return jsonify({'success': False, 'message': 'Assignment is not pending approval'})
    
    try:
        assignment.status = AssignmentStatus.ACTIVE
        assignment.approved_by = current_user.id
        assignment.approved_at = datetime.utcnow()
        assignment.cross_branch_approved_by = current_user.id
        assignment.cross_branch_approved_at = datetime.utcnow()
        
        # Now actually assign the vehicle to the driver
        assignment.driver.current_vehicle_id = assignment.vehicle_id
        assignment.vehicle.is_available = False
        
        db.session.commit()
        
        # Log approval
        log_audit('approve_cross_branch_assignment', 'vehicle_assignment', assignment_id, {
            'driver_name': assignment.driver.full_name,
            'vehicle_registration': assignment.vehicle.registration_number,
            'driver_branch': assignment.driver.branch.name,
            'vehicle_branch': assignment.vehicle.branch.name,
            'approved_by': current_user.username,
            'reason': assignment.cross_branch_reason
        })
        
        return jsonify({
            'success': True, 
            'message': f'Cross-branch assignment approved for {assignment.driver.full_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_cross_branch_bp.route('/reject/<int:assignment_id>', methods=['POST'])
@login_required
@admin_required
def reject_assignment(assignment_id):
    """Reject a pending cross-branch assignment"""
    assignment = VehicleAssignment.query.get_or_404(assignment_id)
    rejection_reason = request.form.get('rejection_reason', 'No reason provided')
    
    if not assignment.is_cross_branch:
        return jsonify({'success': False, 'message': 'Not a cross-branch assignment'})
    
    if assignment.status != AssignmentStatus.PENDING_APPROVAL:
        return jsonify({'success': False, 'message': 'Assignment is not pending approval'})
    
    try:
        assignment.status = AssignmentStatus.CANCELLED
        assignment.end_date = date.today()
        assignment.notes = f"Rejected: {rejection_reason}"
        
        # Make vehicle available again
        assignment.vehicle.is_available = True
        
        # Clear driver's current vehicle assignment
        assignment.driver.current_vehicle_id = None
        
        db.session.commit()
        
        # Log rejection
        log_audit('reject_cross_branch_assignment', 'vehicle_assignment', assignment_id, {
            'driver_name': assignment.driver.full_name,
            'vehicle_registration': assignment.vehicle.registration_number,
            'rejected_by': current_user.username,
            'rejection_reason': rejection_reason
        })
        
        return jsonify({
            'success': True, 
            'message': f'Cross-branch assignment rejected for {assignment.driver.full_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_cross_branch_bp.route('/extend/<int:assignment_id>', methods=['POST'])
@login_required
@admin_required
def extend_assignment(assignment_id):
    """Extend expiry date of a cross-branch assignment"""
    assignment = VehicleAssignment.query.get_or_404(assignment_id)
    
    if not assignment.is_cross_branch:
        return jsonify({'success': False, 'message': 'Not a cross-branch assignment'})
    
    new_expiry_str = request.form.get('new_expiry')
    extension_reason = request.form.get('extension_reason', 'Admin extension')
    
    if not new_expiry_str:
        return jsonify({'success': False, 'message': 'New expiry date required'})
    
    try:
        new_expiry = datetime.strptime(new_expiry_str, '%Y-%m-%d')
        
        if new_expiry <= datetime.utcnow():
            return jsonify({'success': False, 'message': 'New expiry must be in the future'})
        
        old_expiry = assignment.cross_branch_expires_at
        assignment.cross_branch_expires_at = new_expiry
        assignment.notes = f"{assignment.notes or ''}\nExtended until {new_expiry.strftime('%Y-%m-%d')}: {extension_reason}"
        
        db.session.commit()
        
        # Log extension
        log_audit('extend_cross_branch_assignment', 'vehicle_assignment', assignment_id, {
            'driver_name': assignment.driver.full_name,
            'vehicle_registration': assignment.vehicle.registration_number,
            'old_expiry': old_expiry.isoformat() if old_expiry else None,
            'new_expiry': new_expiry.isoformat(),
            'extended_by': current_user.username,
            'extension_reason': extension_reason
        })
        
        return jsonify({
            'success': True, 
            'message': f'Assignment extended until {new_expiry.strftime("%Y-%m-%d")}'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': 'Invalid date format'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_cross_branch_bp.route('/end/<int:assignment_id>', methods=['POST'])
@login_required
@admin_required
def end_assignment(assignment_id):
    """End a cross-branch assignment"""
    assignment = VehicleAssignment.query.get_or_404(assignment_id)
    end_reason = request.form.get('end_reason', 'Admin ended assignment')
    
    if not assignment.is_cross_branch:
        return jsonify({'success': False, 'message': 'Not a cross-branch assignment'})
    
    if assignment.status != AssignmentStatus.ACTIVE:
        return jsonify({'success': False, 'message': 'Assignment is not active'})
    
    try:
        assignment.status = AssignmentStatus.COMPLETED
        assignment.end_date = date.today()
        assignment.notes = f"{assignment.notes or ''}\nEnded: {end_reason}"
        
        # Make vehicle available again
        assignment.vehicle.is_available = True
        
        # Clear driver's current vehicle assignment
        assignment.driver.current_vehicle_id = None
        
        db.session.commit()
        
        # Log assignment end
        log_audit('end_cross_branch_assignment', 'vehicle_assignment', assignment_id, {
            'driver_name': assignment.driver.full_name,
            'vehicle_registration': assignment.vehicle.registration_number,
            'ended_by': current_user.username,
            'end_reason': end_reason
        })
        
        return jsonify({
            'success': True, 
            'message': f'Cross-branch assignment ended for {assignment.driver.full_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@admin_cross_branch_bp.route('/api/drivers/<int:branch_id>')
@login_required
@admin_required
def get_drivers_by_branch(branch_id):
    """API endpoint to get drivers by branch for assignment creation"""
    try:
        drivers = Driver.query.filter(
            Driver.branch_id == branch_id,
            Driver.status == DriverStatus.ACTIVE
        ).join(User).filter(User.status == UserStatus.ACTIVE).order_by(Driver.full_name).all()
        
        return jsonify({
            'success': True,
            'drivers': [{
                'id': driver.id,
                'name': driver.full_name,
                'phone': driver.user.phone,
                'current_vehicle': driver.current_vehicle.registration_number if driver.current_vehicle else None
            } for driver in drivers]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_cross_branch_bp.route('/api/vehicles/<int:branch_id>')
@login_required
@admin_required
def get_vehicles_by_branch(branch_id):
    """API endpoint to get available vehicles by branch for assignment creation"""
    try:
        vehicles = Vehicle.query.filter(
            Vehicle.branch_id == branch_id,
            Vehicle.status == VehicleStatus.ACTIVE,
            Vehicle.is_available == True
        ).order_by(Vehicle.registration_number).all()
        
        return jsonify({
            'success': True,
            'vehicles': [{
                'id': vehicle.id,
                'registration': vehicle.registration_number,
                'make_model': f"{vehicle.make} {vehicle.model}",
                'seating_capacity': vehicle.seating_capacity
            } for vehicle in vehicles]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})