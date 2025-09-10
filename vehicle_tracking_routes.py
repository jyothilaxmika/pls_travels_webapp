from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_
from models import (User, Driver, Vehicle, Branch, Duty, VehicleTracking, db,
                   DriverStatus, VehicleStatus, DutyStatus, UserRole)
from auth import log_audit
from timezone_utils import get_ist_time_naive

tracking_bp = Blueprint('tracking', __name__)

def admin_or_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            flash('Access denied. Admin or Manager role required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_accessible_branches():
    """Get branches accessible to current user"""
    if current_user.role == UserRole.ADMIN:
        return [branch.id for branch in Branch.query.all()]
    elif current_user.role == UserRole.MANAGER:
        return [branch.id for branch in current_user.managed_branches]
    return []

@tracking_bp.route('/vehicle-map')
@login_required
@admin_or_manager_required
def vehicle_map():
    """Main vehicle tracking map page"""
    branch_ids = get_accessible_branches()
    if not branch_ids:
        flash('No branches accessible. Contact admin.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Get active vehicles for dropdown filter
    vehicles = Vehicle.query.filter(
        Vehicle.branch_id.in_(branch_ids),
        Vehicle.status == VehicleStatus.ACTIVE
    ).all()
    
    # Get branches for filter
    branches = Branch.query.filter(Branch.id.in_(branch_ids)).all()
    
    log_audit('vehicle_tracking_map_accessed', f'User accessed vehicle tracking map')
    
    return render_template('tracking/vehicle_map.html', 
                         vehicles=vehicles, 
                         branches=branches,
                         title='Vehicle Tracking & Heatmap')

@tracking_bp.route('/api/vehicle-locations')
@login_required
@admin_or_manager_required
def api_vehicle_locations():
    """API endpoint to get current vehicle locations"""
    branch_ids = get_accessible_branches()
    if not branch_ids:
        return jsonify({'error': 'No accessible branches'}), 403
    
    # Get filter parameters
    vehicle_ids = request.args.getlist('vehicle_ids')
    branch_id = request.args.get('branch_id', type=int)
    hours_back = request.args.get('hours_back', default=24, type=int)
    
    # Build query
    time_threshold = get_ist_time_naive() - timedelta(hours=hours_back)
    
    query = VehicleTracking.query.join(Vehicle).filter(
        Vehicle.branch_id.in_(branch_ids),
        VehicleTracking.recorded_at >= time_threshold,
        VehicleTracking.latitude.isnot(None),
        VehicleTracking.longitude.isnot(None)
    )
    
    # Apply filters
    if vehicle_ids:
        query = query.filter(VehicleTracking.vehicle_id.in_(vehicle_ids))
    
    if branch_id and branch_id in branch_ids:
        query = query.filter(Vehicle.branch_id == branch_id)
    
    # Get latest location for each vehicle
    subquery = query.with_entities(
        VehicleTracking.vehicle_id,
        func.max(VehicleTracking.recorded_at).label('latest_time')
    ).group_by(VehicleTracking.vehicle_id).subquery()
    
    latest_locations = query.join(
        subquery,
        and_(
            VehicleTracking.vehicle_id == subquery.c.vehicle_id,
            VehicleTracking.recorded_at == subquery.c.latest_time
        )
    ).all()
    
    # Format response
    locations = []
    for tracking in latest_locations:
        locations.append({
            'vehicle_id': tracking.vehicle_id,
            'vehicle_number': tracking.vehicle.number,
            'vehicle_type': tracking.vehicle.vehicle_type.name if tracking.vehicle.vehicle_type else 'Unknown',
            'driver_id': tracking.driver_id,
            'driver_name': tracking.driver.user.full_name if tracking.driver and tracking.driver.user else 'Unknown',
            'latitude': float(tracking.latitude),
            'longitude': float(tracking.longitude),
            'location_name': tracking.location_name,
            'recorded_at': tracking.recorded_at.isoformat(),
            'accuracy': tracking.location_accuracy,
            'duty_id': tracking.duty_id,
            'duty_status': tracking.duty.status.value if tracking.duty else None,
            'odometer_reading': tracking.odometer_reading,
            'speed': 0  # Placeholder for speed calculation
        })
    
    return jsonify({
        'locations': locations,
        'total_vehicles': len(locations),
        'timestamp': get_ist_time_naive().isoformat()
    })

@tracking_bp.route('/api/vehicle-path/<int:vehicle_id>')
@login_required
@admin_or_manager_required
def api_vehicle_path(vehicle_id):
    """API endpoint to get vehicle path history"""
    branch_ids = get_accessible_branches()
    
    # Verify vehicle access
    vehicle = Vehicle.query.filter(
        Vehicle.id == vehicle_id,
        Vehicle.branch_id.in_(branch_ids)
    ).first_or_404()
    
    # Get time range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    hours_back = request.args.get('hours_back', default=24, type=int)
    
    if start_date and end_date:
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        end_time = get_ist_time_naive()
        start_time = end_time - timedelta(hours=hours_back)
    
    # Get path data
    path_data = VehicleTracking.query.filter(
        VehicleTracking.vehicle_id == vehicle_id,
        VehicleTracking.recorded_at >= start_time,
        VehicleTracking.recorded_at <= end_time,
        VehicleTracking.latitude.isnot(None),
        VehicleTracking.longitude.isnot(None)
    ).order_by(VehicleTracking.recorded_at.asc()).all()
    
    # Format path
    path = []
    for tracking in path_data:
        path.append({
            'latitude': float(tracking.latitude),
            'longitude': float(tracking.longitude),
            'timestamp': tracking.recorded_at.isoformat(),
            'location_name': tracking.location_name,
            'odometer_reading': tracking.odometer_reading,
            'driver_name': tracking.driver.user.full_name if tracking.driver and tracking.driver.user else 'Unknown'
        })
    
    return jsonify({
        'vehicle_id': vehicle_id,
        'vehicle_number': vehicle.number,
        'path': path,
        'total_points': len(path),
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    })

@tracking_bp.route('/api/heatmap-data')
@login_required
@admin_or_manager_required
def api_heatmap_data():
    """API endpoint to get heatmap data for vehicle activity"""
    branch_ids = get_accessible_branches()
    if not branch_ids:
        return jsonify({'error': 'No accessible branches'}), 403
    
    # Get parameters
    days_back = request.args.get('days_back', default=7, type=int)
    vehicle_ids = request.args.getlist('vehicle_ids')
    branch_id = request.args.get('branch_id', type=int)
    
    # Time range
    end_time = get_ist_time_naive()
    start_time = end_time - timedelta(days=days_back)
    
    # Build query
    query = VehicleTracking.query.join(Vehicle).filter(
        Vehicle.branch_id.in_(branch_ids),
        VehicleTracking.recorded_at >= start_time,
        VehicleTracking.recorded_at <= end_time,
        VehicleTracking.latitude.isnot(None),
        VehicleTracking.longitude.isnot(None)
    )
    
    # Apply filters
    if vehicle_ids:
        query = query.filter(VehicleTracking.vehicle_id.in_(vehicle_ids))
    
    if branch_id and branch_id in branch_ids:
        query = query.filter(Vehicle.branch_id == branch_id)
    
    # Get all location data
    tracking_data = query.all()
    
    # Format for heatmap (lat, lng, intensity)
    heatmap_points = []
    for tracking in tracking_data:
        # Use a simple intensity based on how recent the data is
        hours_ago = (get_ist_time_naive() - tracking.recorded_at).total_seconds() / 3600
        intensity = max(0.1, 1.0 - (hours_ago / (days_back * 24)))
        
        heatmap_points.append([
            float(tracking.latitude),
            float(tracking.longitude),
            intensity
        ])
    
    return jsonify({
        'heatmap_data': heatmap_points,
        'total_points': len(heatmap_points),
        'time_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'days': days_back
        }
    })

@tracking_bp.route('/api/add-test-location', methods=['POST'])
@login_required
@admin_or_manager_required
def api_add_test_location():
    """API endpoint to add test location data (for development/testing)"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if not data or 'vehicle_id' not in data or 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': 'Missing required data'}), 400
    
    branch_ids = get_accessible_branches()
    vehicle = Vehicle.query.filter(
        Vehicle.id == data['vehicle_id'],
        Vehicle.branch_id.in_(branch_ids)
    ).first()
    
    if not vehicle:
        return jsonify({'error': 'Vehicle not found or not accessible'}), 404
    
    # Get current active duty for the vehicle
    active_duty = Duty.query.filter(
        Duty.vehicle_id == vehicle.id,
        Duty.status == DutyStatus.ACTIVE
    ).first()
    
    if not active_duty:
        return jsonify({'error': 'No active duty found for vehicle'}), 404
    
    # Create tracking record
    tracking = VehicleTracking()
    tracking.vehicle_id = vehicle.id
    tracking.duty_id = active_duty.id
    tracking.driver_id = active_duty.driver_id
    tracking.recorded_at = get_ist_time_naive()
    tracking.odometer_reading = data.get('odometer_reading', 0)
    tracking.odometer_type = 'manual'
    tracking.latitude = data['latitude']
    tracking.longitude = data['longitude']
    tracking.location_accuracy = data.get('accuracy', 10.0)
    tracking.location_name = data.get('location_name', 'Test Location')
    tracking.source = 'manual'
    tracking.notes = 'Test location data'
    
    db.session.add(tracking)
    db.session.commit()
    
    log_audit('test_location_added', f'Added test location for vehicle {vehicle.number}')
    
    return jsonify({
        'success': True,
        'tracking_id': tracking.id,
        'message': 'Test location added successfully'
    })

@tracking_bp.route('/api/driver-location', methods=['POST'])
@login_required
def api_driver_location_update():
    """REST API fallback for driver location updates when WebSocket is unavailable"""
    from flask import request, jsonify
    from flask_login import current_user
    from models import Driver, VehicleTracking, Duty, DutyStatus, db
    from timezone_utils import get_ist_time_naive
    
    if current_user.role not in [UserRole.DRIVER, UserRole.ADMIN]:
        return jsonify({'error': 'Access denied. Driver access required.'}), 403
    
    data = request.get_json()
    if not data or 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': 'Missing required location data'}), 400
    
    # Get driver profile
    driver = Driver.query.filter_by(user_id=current_user.id).first()
    if not driver:
        return jsonify({'error': 'Driver profile not found'}), 404
    
    # Get active duty
    active_duty = Duty.query.filter(
        Duty.driver_id == driver.id,
        Duty.status == DutyStatus.ACTIVE
    ).first()
    
    if not active_duty:
        return jsonify({'error': 'No active duty found'}), 404
    
    # Create tracking record
    try:
        tracking = VehicleTracking()
        tracking.vehicle_id = active_duty.vehicle_id
        tracking.duty_id = active_duty.id
        tracking.driver_id = driver.id
        tracking.recorded_at = get_ist_time_naive()
        tracking.odometer_reading = 0  # Will be updated by driver later
        tracking.odometer_type = 'gps'
        tracking.latitude = data.get('latitude')
        tracking.longitude = data.get('longitude')
        tracking.location_accuracy = data.get('accuracy', 0)
        tracking.location_name = data.get('location_name', 'GPS Location')
        tracking.source = 'mobile_gps'
        tracking.notes = 'GPS update from mobile device (REST fallback)'
        
        db.session.add(tracking)
        db.session.commit()
        
        log_audit('driver_location_updated', f'Driver {driver.full_name} updated location via REST API')
        
        return jsonify({
            'success': True,
            'tracking_id': tracking.id,
            'message': 'Location updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update location: {str(e)}'}), 500