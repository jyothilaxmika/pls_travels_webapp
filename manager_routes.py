from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from timezone_utils import get_ist_time_naive
from sqlalchemy import func, desc, and_
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, db,
                   DriverStatus, VehicleStatus, DutyStatus)
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
