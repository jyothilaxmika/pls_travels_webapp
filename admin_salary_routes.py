"""
Admin routes for the new 5-method salary calculation system
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
import json
import logging

from models import db, NewSalaryMethod, Driver, Duty, Branch
from services.new_salary_service import NewSalaryCalculationService
from services.audit_service import AuditService
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserRole
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

logger = logging.getLogger(__name__)

# Create blueprint
admin_salary_bp = Blueprint('admin_salary', __name__, url_prefix='/admin/salary-methods')

@admin_salary_bp.route('/')
@login_required
@admin_required
def salary_methods_dashboard():
    """Display the salary methods configuration dashboard"""
    try:
        # Get all configured salary methods
        methods = NewSalaryMethod.query.filter_by(is_active=True).all()
        
        # Get branches for filtering
        branches = Branch.query.filter_by(is_active=True).all()
        
        return render_template('admin/new_salary_methods.html', 
                             methods=methods, 
                             branches=branches)
    except Exception as e:
        logger.error(f"Error loading salary methods dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", 'error')
        return redirect(url_for('admin.dashboard'))

@admin_salary_bp.route('/<method_name>/save', methods=['POST'])
@login_required
@admin_required
def save_method_configuration(method_name):
    """Save configuration for a salary method"""
    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({'success': False, 'message': 'No configuration data provided'})
        
        # Validate method name
        valid_methods = ['d2d', 'revenue_share', 'fixed_daily', 'slab_incentive', 'hybrid_commission', 'final_settlement']
        if method_name not in valid_methods:
            return jsonify({'success': False, 'message': 'Invalid method name'})
        
        # Find or create method record
        method = NewSalaryMethod.query.filter_by(method_name=method_name).first()
        if not method:
            method = NewSalaryMethod()
            method.method_name = method_name
            method.display_name = method_name.replace('_', ' ').title()
            method.description = f"Configuration for {method.display_name} salary calculation"
            method.effective_from = date.today()
            method.created_by = current_user.id
            db.session.add(method)
        
        # Update configuration
        method.set_configuration(config_data)
        method.updated_by = current_user.id
        method.updated_at = datetime.now()
        
        db.session.commit()
        
        # Audit log
        AuditService.log_action(
            f'update_salary_method_{method_name}', 'salary_method', method.id,
            {'config_updated': config_data, 'updated_by': current_user.username}
        )
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving {method_name} configuration: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving configuration: {str(e)}'})

@admin_salary_bp.route('/<method_name>/config', methods=['GET'])
@login_required
@admin_required
def get_method_configuration(method_name):
    """Get current configuration for a salary method"""
    try:
        method = NewSalaryMethod.query.filter_by(method_name=method_name, is_active=True).first()
        if method:
            return jsonify({'success': True, 'config': method.get_configuration()})
        else:
            # Return default configuration
            salary_service = NewSalaryCalculationService()
            default_config = salary_service.get_method_configuration_template(method_name)
            return jsonify({'success': True, 'config': default_config})
            
    except Exception as e:
        logger.error(f"Error getting {method_name} configuration: {str(e)}")
        return jsonify({'success': False, 'message': f'Error loading configuration: {str(e)}'})

@admin_salary_bp.route('/<method_name>/test', methods=['POST'])
@login_required
@admin_required
def test_method_calculation(method_name):
    """Test salary calculation with sample data"""
    try:
        test_data = request.get_json()
        if not test_data:
            return jsonify({'error': 'No test data provided'})
        
        # Get method configuration
        method = NewSalaryMethod.query.filter_by(method_name=method_name, is_active=True).first()
        custom_config = method.get_configuration() if method else None
        
        # Create salary service and calculate
        salary_service = NewSalaryCalculationService()
        
        # Mock duty data for testing
        mock_duty_data = {
            'duty_id': 999999,  # Test duty ID
            'driver_id': 1,
            'vehicle_id': 1,
            'revenue': test_data.get('revenue', 0),
            'total_trips': test_data.get('total_trips', 0),
            'duration_hours': test_data.get('duration_hours', 8),
            'fuel_consumed': test_data.get('fuel_consumed', 0),
            'distance_traveled': 100,  # Mock distance
            'is_weekend': test_data.get('is_weekend', False),
            'duty_date': date.today(),
            'status': 'completed',
            # Manual input fields
            'cash_collected': test_data.get('revenue', 0),  # Use revenue as cash for test
            'advance_taken': test_data.get('advance_taken', 0),
            'fuel_expense': test_data.get('fuel_consumed', 0) * 90,  # Mock fuel cost
            'toll_expense': test_data.get('toll_expense', 0),
            'maintenance_expense': test_data.get('maintenance_expense', 0),
            'other_expenses': test_data.get('other_expenses', 0)
        }
        
        # Use direct calculation instead of duty_id lookup for testing
        salary_service._auto_fetch_duty_data = lambda duty_id: mock_duty_data
        
        result = salary_service.calculate_salary(
            duty_id=999999,  # Mock duty ID
            method=method_name,
            custom_config=custom_config,
            manual_data=test_data
        )
        
        return jsonify({
            'method_name': result.method_name,
            'total_salary': result.total_salary,
            'base_amount': result.base_amount,
            'incentive_amount': result.incentive_amount,
            'deductions': result.deductions,
            'net_salary': result.net_salary,
            'breakdown': result.breakdown,
            'calculation_notes': result.calculation_notes
        })
        
    except Exception as e:
        logger.error(f"Error testing {method_name} calculation: {str(e)}")
        return jsonify({'error': f'Calculation error: {str(e)}'})

@admin_salary_bp.route('/initialize', methods=['POST'])
@login_required
@admin_required
def initialize_default_methods():
    """Initialize all 5 salary methods with default configurations"""
    try:
        salary_service = NewSalaryCalculationService()
        
        method_definitions = [
            {
                'method_name': 'd2d',
                'display_name': 'D2D Final Settlement',
                'description': 'Tamil-style day-to-day settlement with operator and CNG calculations'
            },
            {
                'method_name': 'revenue_share',
                'display_name': 'Revenue Share',
                'description': 'Driver gets percentage of total revenue collected'
            },
            {
                'method_name': 'fixed_daily',
                'display_name': 'Fixed Daily Rate',
                'description': 'Driver gets fixed amount per day regardless of revenue'
            },
            {
                'method_name': 'slab_incentive',
                'display_name': 'Slab-based Incentive',
                'description': 'Tiered rates based on revenue ranges'
            },
            {
                'method_name': 'hybrid_commission',
                'display_name': 'Hybrid Base + Commission',
                'description': 'Fixed base salary plus percentage of revenue above threshold'
            },
            {
                'method_name': 'final_settlement',
                'display_name': 'Final Settlement (Tamil Style)',
                'description': 'Traditional settlement with detailed deductions and CNG adjustments'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for method_def in method_definitions:
            method = NewSalaryMethod.query.filter_by(method_name=method_def['method_name']).first()
            
            if not method:
                # Create new method
                method = NewSalaryMethod()
                method.method_name = method_def['method_name']
                method.display_name = method_def['display_name']
                method.description = method_def['description']
                method.effective_from = date.today()
                method.created_by = current_user.id
                method.is_active = True
                method.is_default = True
                
                # Set default configuration
                default_config = salary_service.get_method_configuration_template(method_def['method_name'])
                method.set_configuration(default_config)
                
                db.session.add(method)
                created_count += 1
            else:
                # Update existing method
                method.display_name = method_def['display_name']
                method.description = method_def['description']
                method.updated_by = current_user.id
                method.updated_at = datetime.now()
                method.is_active = True
                
                # Update configuration if empty
                if not method.configuration:
                    default_config = salary_service.get_method_configuration_template(method_def['method_name'])
                    method.set_configuration(default_config)
                
                updated_count += 1
        
        db.session.commit()
        
        # Audit log
        AuditService.log_action(
            'initialize_salary_methods', 'system', None,
            {
                'created_methods': created_count,
                'updated_methods': updated_count,
                'initialized_by': current_user.username
            }
        )
        
        return jsonify({
            'success': True, 
            'message': f'Initialized {created_count} new methods, updated {updated_count} existing methods'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing salary methods: {str(e)}")
        return jsonify({'success': False, 'message': f'Error initializing methods: {str(e)}'})

@admin_salary_bp.route('/duty/<int:duty_id>/audit', methods=['GET', 'POST'])
@login_required  
@admin_required
def audit_duty_salary(duty_id):
    """Manual duty salary audit interface for admin/manager"""
    duty = Duty.query.get_or_404(duty_id)
    
    if request.method == 'GET':
        # Get all available salary methods
        methods = NewSalaryMethod.query.filter_by(is_active=True).all()
        
        # Auto-fetch duty data
        salary_service = NewSalaryCalculationService()
        auto_data = salary_service._auto_fetch_duty_data(duty_id)
        
        return render_template('admin/duty_salary_audit.html', 
                             duty=duty, 
                             methods=methods,
                             auto_data=auto_data)
    
    elif request.method == 'POST':
        # Process manual salary calculation
        try:
            form_data = request.get_json() or request.form.to_dict()
            
            method_name = form_data.get('salary_method') or 'd2d'
            manual_data = {
                'revenue': float(form_data.get('revenue', 0)),
                'total_trips': int(form_data.get('total_trips', 0)),
                'duration_hours': float(form_data.get('duration_hours', 0)),
                'fuel_consumed': float(form_data.get('fuel_consumed', 0)),
                'advance_taken': float(form_data.get('advance_taken', 0)),
                'toll_expense': float(form_data.get('toll_expense', 0)),
                'maintenance_expense': float(form_data.get('maintenance_expense', 0)),
                'other_expenses': float(form_data.get('other_expenses', 0)),
                'is_weekend': form_data.get('is_weekend') == 'true'
            }
            
            # Calculate salary
            salary_service = NewSalaryCalculationService()
            result = salary_service.calculate_salary(
                duty_id=duty_id,
                method=method_name,
                manual_data=manual_data
            )
            
            # Update duty with calculated earnings
            duty.driver_earnings = result.net_salary
            duty.earnings_breakdown = json.dumps({
                'method': result.method_name,
                'total_salary': result.total_salary,
                'deductions': result.deductions,
                'net_salary': result.net_salary,
                'breakdown': result.breakdown,
                'calculation_notes': result.calculation_notes,
                'calculated_by': current_user.username,
                'calculated_at': datetime.now().isoformat()
            })
            
            db.session.commit()
            
            # Audit log
            AuditService.log_action(
                'manual_salary_audit', 'duty', duty_id,
                {
                    'method_used': method_name,
                    'manual_data': manual_data,
                    'calculated_salary': result.net_salary,
                    'audited_by': current_user.username
                }
            )
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'result': {
                        'method_name': result.method_name,
                        'total_salary': result.total_salary,
                        'net_salary': result.net_salary,
                        'deductions': result.deductions,
                        'breakdown': result.breakdown,
                        'calculation_notes': result.calculation_notes
                    }
                })
            else:
                flash(f'Duty salary calculated: ₹{result.net_salary:.2f} using {result.method_name}', 'success')
                return redirect(url_for('admin.view_duty', duty_id=duty_id))
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in duty salary audit: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)})
            else:
                flash(f'Error calculating salary: {str(e)}', 'error')
                return redirect(url_for('admin.view_duty', duty_id=duty_id))

@admin_salary_bp.route('/bulk-calculate', methods=['POST'])
@login_required
@admin_required  
def bulk_calculate_salaries():
    """Bulk calculate salaries for multiple duties"""
    try:
        data = request.get_json()
        duty_ids = data.get('duty_ids', [])
        method_name = data.get('method_name')
        
        if not duty_ids or not method_name:
            return jsonify({'success': False, 'message': 'Missing duty IDs or method name'})
        
        salary_service = NewSalaryCalculationService()
        results = []
        success_count = 0
        error_count = 0
        
        for duty_id in duty_ids:
            try:
                result = salary_service.calculate_salary(duty_id=duty_id, method=method_name)
                
                # Update duty
                duty = Duty.query.get(duty_id)
                if duty:
                    duty.driver_earnings = result.net_salary
                    duty.earnings_breakdown = json.dumps({
                        'method': result.method_name,
                        'total_salary': result.total_salary,
                        'net_salary': result.net_salary,
                        'bulk_calculated_by': current_user.username,
                        'calculated_at': datetime.now().isoformat()
                    })
                    success_count += 1
                
                results.append({
                    'duty_id': duty_id,
                    'success': True,
                    'net_salary': result.net_salary
                })
                
            except Exception as e:
                error_count += 1
                results.append({
                    'duty_id': duty_id,
                    'success': False,
                    'error': str(e)
                })
        
        db.session.commit()
        
        # Audit log
        AuditService.log_action(
            'bulk_salary_calculation', 'system', None,
            {
                'method_used': method_name,
                'total_duties': len(duty_ids),
                'success_count': success_count,
                'error_count': error_count,
                'calculated_by': current_user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(duty_ids)} duties: {success_count} success, {error_count} errors',
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk salary calculation: {str(e)}")
        return jsonify({'success': False, 'message': f'Bulk calculation error: {str(e)}'})

@admin_salary_bp.route('/d2d/calculator')
@login_required
@admin_required  
def d2d_calculator():
    """Display the D2D calculator interface"""
    return render_template('admin/d2d_calculator.html')

@admin_salary_bp.route('/d2d/save-calculation', methods=['POST'])
@login_required
@admin_required
def save_d2d_calculation():
    """Save a D2D calculation result"""
    try:
        calculation_data = request.get_json()
        if not calculation_data:
            return jsonify({'success': False, 'message': 'No calculation data provided'})
        
        # Save calculation to audit log
        AuditService.log_action(
            'save_d2d_calculation', 'system', None,
            {
                'inputs': calculation_data.get('inputs', {}),
                'results': calculation_data.get('results', {}),
                'saved_by': current_user.username,
                'calculation_type': 'D2D Final Settlement'
            }
        )
        
        return jsonify({'success': True, 'message': 'D2D calculation saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving D2D calculation: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving calculation: {str(e)}'})

@admin_salary_bp.route('/reports')
@login_required
@admin_required
def salary_calculation_reports():
    """Display salary calculation reports and analytics"""
    try:
        # Get summary statistics
        from sqlalchemy import func
        
        # Total duties calculated by method
        method_stats = db.session.query(
            NewSalaryMethod.method_name,
            NewSalaryMethod.display_name,
            func.count(Duty.id).label('duty_count'),
            func.avg(Duty.driver_earnings).label('avg_earnings'),
            func.sum(Duty.driver_earnings).label('total_paid')
        ).join(
            Duty, Duty.earnings_breakdown.like(f'%{NewSalaryMethod.method_name}%')
        ).filter(
            NewSalaryMethod.is_active == True,
            Duty.driver_earnings.isnot(None)
        ).group_by(
            NewSalaryMethod.method_name, NewSalaryMethod.display_name
        ).all()
        
        return render_template('admin/salary_reports.html', method_stats=method_stats)
        
    except Exception as e:
        logger.error(f"Error loading salary reports: {str(e)}")
        flash(f'Error loading reports: {str(e)}', 'error')
        return redirect(url_for('admin_salary.salary_methods_dashboard'))

# Error handlers
@admin_salary_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Resource not found'}), 404

@admin_salary_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'message': 'Internal server error'}), 500