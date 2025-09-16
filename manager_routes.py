from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from timezone_utils import get_ist_time_naive
from sqlalchemy import func, desc, and_
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, db,
                   DriverStatus, VehicleStatus, DutyStatus, TrackingSession, DriverLocation)
from auth import log_audit

manager_bp = Blueprint('manager', __name__)

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserRole
        if not current_user.is_authenticated or current_user.role != UserRole.MANAGER:
            flash('Manager access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_manager_branches():
    """Get branches accessible to current manager"""
    return [branch.id for branch in current_user.managed_branches]

@manager_bp.route('/dashboard')
@login_required
@manager_required
def dashboard():
    branch_ids = get_manager_branches()
    
    if not branch_ids:
        flash('No branches assigned. Please contact admin.', 'warning')
        return render_template('manager/dashboard.html')
    
    # Branch statistics
    today = datetime.now().date()
    
    # Active drivers in managed branches
    active_drivers = Driver.query.filter(
        Driver.branch_id.in_(branch_ids),
        Driver.status == DriverStatus.ACTIVE
    ).count()
    
    # Active vehicles in managed branches
    active_vehicles = Vehicle.query.filter(
        Vehicle.branch_id.in_(branch_ids),
        Vehicle.status == VehicleStatus.ACTIVE
    ).count()
    
    # Today's duties
    todays_duties = Duty.query.filter(
        Duty.branch_id.in_(branch_ids),
        func.date(Duty.start_time) == today
    ).count()
    
    # Today's revenue vs target
    revenue_stats = db.session.query(
        Branch.name,
        Branch.target_revenue,
        func.coalesce(func.sum(Duty.revenue), 0).label('actual_revenue')
    ).outerjoin(Duty, and_(
        Duty.branch_id == Branch.id,
        func.date(Duty.start_time) == today
    )).filter(
        Branch.id.in_(branch_ids),
        Branch.is_active == True
    ).group_by(Branch.id, Branch.name, Branch.target_revenue).all()
    
    # Pending driver approvals
    pending_drivers = Driver.query.filter(
        Driver.branch_id.in_(branch_ids),
        Driver.status == 'pending'
    ).count()
    
    # Recent activities in managed branches
    recent_duties = Duty.query.filter(
        Duty.branch_id.in_(branch_ids)
    ).order_by(desc(Duty.start_time)).limit(5).all()
    
    return render_template('manager/dashboard.html',
                         active_drivers=active_drivers,
                         active_vehicles=active_vehicles,
                         todays_duties=todays_duties,
                         revenue_stats=revenue_stats,
                         pending_drivers=pending_drivers,
                         recent_duties=recent_duties)

@manager_bp.route('/drivers')
@login_required
@manager_required
def drivers():
    branch_ids = get_manager_branches()
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Driver.query.filter(Driver.branch_id.in_(branch_ids))
    
    if status_filter:
        query = query.filter(Driver.status == status_filter)
    
    drivers = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('manager/drivers.html', 
                         drivers=drivers,
                         status_filter=status_filter)

@manager_bp.route('/drivers/<int:driver_id>/approve', methods=['POST'])
@login_required
@manager_required
def approve_driver(driver_id):
    branch_ids = get_manager_branches()
    
    driver = Driver.query.filter(
        Driver.id == driver_id,
        Driver.branch_id.in_(branch_ids)
    ).first_or_404()
    
    if driver.status != 'pending':
        flash('Driver is not in pending status.', 'error')
        return redirect(url_for('manager.drivers'))
    
    driver.status = DriverStatus.ACTIVE
    driver.approved_by = current_user.id
    driver.approved_at = get_ist_time_naive()
    
    # Activate user account
    driver.user.active = True
    
    db.session.commit()
    
    log_audit('approve_driver', 'driver', driver_id,
             {'driver_name': driver.full_name, 'branch': driver.branch.name})
    
    flash(f'Driver {driver.full_name} has been approved.', 'success')
    return redirect(url_for('manager.drivers'))

@manager_bp.route('/drivers/<int:driver_id>/reject', methods=['POST'])
@login_required
@manager_required
def reject_driver(driver_id):
    branch_ids = get_manager_branches()
    
    driver = Driver.query.filter(
        Driver.id == driver_id,
        Driver.branch_id.in_(branch_ids)
    ).first_or_404()
    
    if driver.status != 'pending':
        flash('Driver is not in pending status.', 'error')
        return redirect(url_for('manager.drivers'))
    
    driver.status = 'rejected'
    driver.approved_by = current_user.id
    driver.approved_at = get_ist_time_naive()
    
    db.session.commit()
    
    log_audit('reject_driver', 'driver', driver_id,
             {'driver_name': driver.full_name, 'branch': driver.branch.name})
    
    flash(f'Driver {driver.full_name} has been rejected.', 'warning')
    return redirect(url_for('manager.drivers'))

@manager_bp.route('/reports')
@login_required
@manager_required
def reports():
    branch_ids = get_manager_branches()
    
    # Date range filter
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = (datetime.now() - timedelta(days=30)).date()
        end_date_obj = datetime.now().date()
    
    # Revenue trends
    revenue_trend = db.session.query(
        func.date(Duty.start_time).label('date'),
        func.sum(Duty.revenue).label('revenue')
    ).filter(
        Duty.branch_id.in_(branch_ids),
        func.date(Duty.start_time) >= start_date_obj,
        func.date(Duty.start_time) <= end_date_obj
    ).group_by(func.date(Duty.start_time)) \
     .order_by(func.date(Duty.start_time)).all()
    
    # Top drivers
    top_drivers = db.session.query(
        Driver.full_name,
        Branch.name.label('branch_name'),
        func.sum(Duty.driver_earnings).label('total_earnings'),
        func.count(Duty.id).label('duty_count')
    ).join(Branch).join(Duty).filter(
        Duty.branch_id.in_(branch_ids),
        func.date(Duty.start_time) >= start_date_obj,
        func.date(Duty.start_time) <= end_date_obj
    ).group_by(Driver.id, Driver.full_name, Branch.name) \
     .order_by(desc(func.sum(Duty.driver_earnings))).limit(10).all()
    
    # Branch performance
    branch_performance = db.session.query(
        Branch.name,
        Branch.target_revenue,
        func.sum(Duty.revenue).label('actual_revenue'),
        func.count(Duty.id).label('duty_count')
    ).join(Duty).filter(
        Branch.id.in_(branch_ids),
        func.date(Duty.start_time) >= start_date_obj,
        func.date(Duty.start_time) <= end_date_obj
    ).group_by(Branch.id, Branch.name, Branch.target_revenue).all()
    
    return render_template('manager/reports.html',
                         revenue_trend=revenue_trend,
                         top_drivers=top_drivers,
                         branch_performance=branch_performance,
                         start_date=start_date,
                         end_date=end_date)

@manager_bp.route('/api/branch-revenue-chart')
@login_required
@manager_required
def branch_revenue_chart():
    branch_ids = get_manager_branches()
    
    # Get last 7 days revenue data
    days = []
    revenues = []
    
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        revenue = db.session.query(func.sum(Duty.revenue)).filter(
            Duty.branch_id.in_(branch_ids),
            func.date(Duty.start_time) == date
        ).scalar() or 0
        
        days.append(date.strftime('%m/%d'))
        revenues.append(float(revenue))
    
    return jsonify({
        'labels': days,
        'data': revenues
    })

@manager_bp.route('/api/driver-performance')
@login_required
@manager_required
def driver_performance():
    branch_ids = get_manager_branches()
    
    # Get top 5 drivers by earnings this month
    start_of_month = datetime.now().replace(day=1).date()
    
    driver_data = db.session.query(
        Driver.full_name,
        func.sum(Duty.driver_earnings).label('earnings')
    ).join(Duty).filter(
        Duty.branch_id.in_(branch_ids),
        func.date(Duty.start_time) >= start_of_month
    ).group_by(Driver.id, Driver.full_name) \
     .order_by(desc(func.sum(Duty.driver_earnings))).limit(5).all()
    
    return jsonify([{
        'name': row.full_name,
        'earnings': float(row.earnings or 0)
    } for row in driver_data])

@manager_bp.route('/drivers/tracking')
@login_required
@manager_required
def driver_tracking():
    """Driver location tracking and heatmap page"""
    branch_ids = get_manager_branches()
    
    # Get branches for filter dropdown
    branches = Branch.query.filter(
        Branch.id.in_(branch_ids),
        Branch.is_active == True
    ).all()
    
    return render_template('manager/driver_tracking.html', branches=branches)

@manager_bp.route('/api/drivers')
@login_required
@manager_required
def api_drivers():
    """API endpoint to get drivers for filtering"""
    branch_ids = get_manager_branches()
    
    drivers = Driver.query.filter(
        Driver.branch_id.in_(branch_ids),
        Driver.status.in_([DriverStatus.ACTIVE, DriverStatus.PENDING])
    ).all()
    
    driver_data = []
    for driver in drivers:
        # Check if driver has active duty
        active_duty = Duty.query.filter_by(
            driver_id=driver.id,
            status=DutyStatus.ACTIVE
        ).first()
        
        driver_data.append({
            'id': driver.id,
            'full_name': driver.full_name,
            'phone': driver.phone,
            'branch_id': driver.branch_id,
            'branch_name': driver.branch.name if driver.branch else None,
            'status': driver.status.value,
            'has_active_duty': bool(active_duty)
        })
    
    return jsonify({
        'success': True,
        'drivers': driver_data
    })

@manager_bp.route('/api/driver-locations', methods=['POST'])
@login_required
@manager_required
def api_driver_locations():
    """API endpoint to get driver location data with filters"""
    try:
        data = request.get_json()
        branch_ids = get_manager_branches()
        
        # Parse filters
        time_range = data.get('time_range', 'live')
        branch_id = data.get('branch_id')
        driver_ids = data.get('driver_ids', [])
        
        # Calculate time range with timezone handling
        from datetime import timezone
        now = datetime.now(timezone.utc)  # Use UTC for consistency
        
        # Limit time ranges for performance
        if time_range == 'live':
            start_time = now - timedelta(minutes=30)
            end_time = now
        elif time_range == '1h':
            start_time = now - timedelta(hours=1)
            end_time = now
        elif time_range == '6h':
            start_time = now - timedelta(hours=6)
            end_time = now
        elif time_range == '1d':
            start_time = now - timedelta(days=1)
            end_time = now
        elif time_range == '3d':
            start_time = now - timedelta(days=2)  # Limit to 2 days for performance
            end_time = now
        elif time_range == '1w':
            start_time = now - timedelta(days=3)  # Limit to 3 days for performance
            end_time = now
        elif time_range == 'custom':
            # Parse custom times and convert to UTC
            start_str = data.get('start_time', '')
            end_str = data.get('end_time', '')
            if start_str and end_str:
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                # Limit custom range to 7 days for performance
                if (end_time - start_time).days > 7:
                    start_time = end_time - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=1)
                end_time = now
        else:
            start_time = now - timedelta(hours=1)
            end_time = now
        
        # Convert to naive UTC for database query (assuming DB stores UTC)
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
        
        # Build location query
        location_query = DriverLocation.query.join(Driver).filter(
            Driver.branch_id.in_(branch_ids),
            DriverLocation.captured_at.between(start_time, end_time)
        )
        
        # Apply filters
        if branch_id:
            location_query = location_query.filter(Driver.branch_id == int(branch_id))
        
        if driver_ids:
            location_query = location_query.filter(DriverLocation.driver_id.in_(driver_ids))
        
        # Get locations with performance limits
        MAX_LOCATIONS = 2000  # Performance limit
        locations = location_query.order_by(DriverLocation.captured_at.desc()).limit(MAX_LOCATIONS).all()
        
        # Format location data
        location_data = []
        for loc in locations:
            location_data.append({
                'driver_id': loc.driver_id,
                'driver_name': loc.driver.full_name,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'accuracy': loc.accuracy,
                'speed': loc.speed,
                'captured_at': loc.captured_at.isoformat(),
                'battery_level': loc.battery_level,
                'is_mocked': loc.is_mocked
            })
        
        # Get current positions (latest location for each driver)
        current_positions = []
        seen_drivers = set()
        
        for loc in locations:
            if loc.driver_id not in seen_drivers:
                seen_drivers.add(loc.driver_id)
                # Handle timezone for time difference calculation
                loc_time = loc.captured_at.replace(tzinfo=timezone.utc) if loc.captured_at.tzinfo is None else loc.captured_at
                time_diff = (now - loc_time).total_seconds() / 60  # minutes
                
                current_positions.append({
                    'driver_id': loc.driver_id,
                    'driver_name': loc.driver.full_name,
                    'latitude': float(loc.latitude),
                    'longitude': float(loc.longitude),
                    'accuracy': float(loc.accuracy) if loc.accuracy else None,
                    'speed': float(loc.speed) if loc.speed else None,
                    'battery_level': int(loc.battery_level) if loc.battery_level else None,
                    'last_update_minutes': int(time_diff),
                    'is_active': time_diff < 5  # Active if updated within 5 minutes
                })
        
        # Get recent location history for table
        recent_locations = []
        for loc in locations[:20]:  # Last 20 locations
            time_diff = (now - loc.captured_at).total_seconds() / 60
            recent_locations.append({
                'driver_name': loc.driver.full_name,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'accuracy': loc.accuracy,
                'speed': loc.speed,
                'battery_level': loc.battery_level,
                'captured_at': loc.captured_at.isoformat(),
                'time_ago': f"{int(time_diff)} min ago" if time_diff < 60 else f"{int(time_diff/60)} hr ago",
                'is_recent': time_diff < 30
            })
        
        # Calculate routes for selected drivers (simplified)
        routes = []
        for driver_id in set(driver_ids[:5]) if driver_ids else []:  # Limit to 5 drivers
            driver_locations = [loc for loc in locations if loc.driver_id == driver_id]
            if len(driver_locations) > 1:
                coordinates = [[loc.latitude, loc.longitude] for loc in driver_locations]
                driver = Driver.query.get(driver_id)
                routes.append({
                    'driver_id': driver_id,
                    'driver_name': driver.full_name if driver else 'Unknown',
                    'coordinates': coordinates,
                    'color': f'hsl({(driver_id * 137) % 360}, 70%, 50%)',  # Generate unique color
                    'date': start_time.strftime('%Y-%m-%d'),
                    'distance': f"{len(coordinates) * 0.5:.1f}"  # Rough estimate
                })
        
        # Calculate statistics
        active_drivers = len([pos for pos in current_positions if pos['is_active']])
        
        return jsonify({
            'success': True,
            'locations': location_data,
            'current_positions': current_positions,
            'recent_locations': recent_locations,
            'routes': routes,
            'stats': {
                'active_drivers': active_drivers,
                'total_locations': len(location_data),
                'time_range': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }
        })
        
    except Exception as e:
        print(f"Error in driver locations API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch location data',
            'details': str(e)
        }), 500
