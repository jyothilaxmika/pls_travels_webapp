from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models import (User, Driver, Vehicle, Branch, Duty, DutyScheme, 
                   Penalty, Asset, AuditLog, db)
from forms import DriverForm, VehicleForm, DutySchemeForm
from utils import allowed_file, calculate_earnings
from auth import log_audit

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get overall statistics
    total_drivers = Driver.query.filter_by(status='active').count()
    total_vehicles = Vehicle.query.filter_by(status='active').count()
    total_branches = Branch.query.filter_by(is_active=True).count()
    
    # Active duties today
    today = datetime.now().date()
    active_duties = Duty.query.filter(
        func.date(Duty.start_time) == today,
        Duty.status == 'active'
    ).count()
    
    # Revenue statistics
    revenue_stats = db.session.query(
        Branch.name,
        Branch.target_revenue,
        func.coalesce(func.sum(Duty.revenue), 0).label('actual_revenue')
    ).outerjoin(Duty, func.date(Duty.start_time) == today) \
     .filter(Branch.is_active == True) \
     .group_by(Branch.id, Branch.name, Branch.target_revenue).all()
    
    # Recent activities
    recent_activities = AuditLog.query.order_by(desc(AuditLog.created_at)).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_drivers=total_drivers,
                         total_vehicles=total_vehicles,
                         total_branches=total_branches,
                         active_duties=active_duties,
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
        query = query.filter(Driver.status == status_filter)
    
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
    driver.status = 'active'
    driver.approved_by = current_user.id
    driver.approved_at = datetime.utcnow()
    
    # Activate user account
    driver.user.is_active = True
    
    db.session.commit()
    
    log_audit('approve_driver', 'driver', driver_id, 
             {'driver_name': driver.full_name, 'branch': driver.branch.name})
    
    flash(f'Driver {driver.full_name} has been approved.', 'success')
    return redirect(url_for('admin.drivers'))

@admin_bp.route('/drivers/<int:driver_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.status = 'rejected'
    driver.approved_by = current_user.id
    driver.approved_at = datetime.utcnow()
    
    db.session.commit()
    
    log_audit('reject_driver', 'driver', driver_id,
             {'driver_name': driver.full_name, 'branch': driver.branch.name})
    
    flash(f'Driver {driver.full_name} has been rejected.', 'warning')
    return redirect(url_for('admin.drivers'))

@admin_bp.route('/drivers/<int:driver_id>/view')
@login_required
@admin_required
def view_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    
    # Get driver's recent duties
    recent_duties = Duty.query.filter_by(driver_id=driver_id).order_by(desc(Duty.created_at)).limit(10).all()
    
    # Get driver's penalties
    penalties = Penalty.query.filter_by(driver_id=driver_id).order_by(desc(Penalty.applied_at)).all()
    
    # Get driver's assets
    assets = Asset.query.filter_by(driver_id=driver_id).all()
    
    return render_template('admin/driver_details.html', 
                         driver=driver, 
                         recent_duties=recent_duties,
                         penalties=penalties,
                         assets=assets)

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
    
    return render_template('admin/vehicles.html', 
                         vehicles=vehicles, 
                         branches=branches,
                         branch_filter=branch_filter)

@admin_bp.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_vehicle():
    form = VehicleForm()
    form.branch_id.choices = [(b.id, b.name) for b in Branch.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        vehicle = Vehicle()
        vehicle.registration_number = form.registration_number.data
        vehicle.vehicle_type = form.vehicle_type.data
        vehicle.model = form.model.data
        vehicle.year = form.year.data
        vehicle.color = form.color.data
        vehicle.branch_id = form.branch_id.data
        vehicle.insurance_number = form.insurance_number.data
        vehicle.insurance_expiry = form.insurance_expiry.data
        vehicle.fitness_expiry = form.fitness_expiry.data
        vehicle.permit_expiry = form.permit_expiry.data
        vehicle.fastag_number = form.fastag_number.data
        vehicle.device_imei = form.device_imei.data
        
        db.session.add(vehicle)
        db.session.commit()
        
        log_audit('add_vehicle', 'vehicle', vehicle.id,
                 {'registration': vehicle.registration_number, 'type': vehicle.vehicle_type})
        
        flash('Vehicle added successfully.', 'success')
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

@admin_bp.route('/duty-schemes')
@login_required
@admin_required
def duty_schemes():
    schemes = DutyScheme.query.filter_by(is_active=True).all()
    return render_template('admin/duty_schemes.html', schemes=schemes)

@admin_bp.route('/duty-schemes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_duty_scheme():
    form = DutySchemeForm()
    form.branch_id.choices = [('0', 'Global')] + [(str(b.id), b.name) for b in Branch.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        config = {}
        
        if form.scheme_type.data == 'fixed':
            config = {'daily_amount': float(form.fixed_amount.data or 0)}
        elif form.scheme_type.data == 'per_trip':
            config = {'per_trip_amount': float(form.per_trip_amount.data or 0)}
        elif form.scheme_type.data == 'slab':
            config = {
                'slabs': [
                    {'min': 0, 'max': float(form.slab1_max.data or 0), 'percentage': float(form.slab1_percent.data or 0)},
                    {'min': float(form.slab1_max.data or 0), 'max': float(form.slab2_max.data or 0), 'percentage': float(form.slab2_percent.data or 0)},
                    {'min': float(form.slab2_max.data or 0), 'max': 999999, 'percentage': float(form.slab3_percent.data or 0)}
                ]
            }
        elif form.scheme_type.data == 'mixed':
            config = {
                'base_amount': float(form.base_amount.data or 0),
                'percentage': float(form.incentive_percent.data or 0)
            }
        
        scheme = DutyScheme()
        scheme.name = form.name.data
        scheme.scheme_type = form.scheme_type.data
        scheme.branch_id = form.branch_id.data if form.branch_id.data else None
        scheme.bmg_amount = form.bmg_amount.data or 0.0
        scheme.set_config(config)
        
        db.session.add(scheme)
        db.session.commit()
        
        log_audit('add_duty_scheme', 'duty_scheme', scheme.id,
                 {'name': scheme.name, 'type': scheme.scheme_type})
        
        flash('Duty scheme added successfully.', 'success')
        return redirect(url_for('admin.duty_schemes'))
    
    return render_template('admin/duty_scheme_form.html', form=form, title='Add Duty Scheme')

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
    ).join(Branch).join(Duty).filter(
        Duty.start_time >= thirty_days_ago
    ).group_by(Driver.id, Driver.full_name, Branch.name) \
     .order_by(desc(func.sum(Duty.driver_earnings))).limit(10).all()
    
    # Vehicle utilization
    vehicle_stats = db.session.query(
        Vehicle.registration_number,
        Branch.name.label('branch_name'),
        func.count(Duty.id).label('duty_count'),
        func.sum(Duty.distance_km).label('total_distance')
    ).join(Branch).outerjoin(Duty).filter(
        Vehicle.status == 'active'
    ).group_by(Vehicle.id, Vehicle.registration_number, Branch.name).all()
    
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
