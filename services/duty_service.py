"""
Duty Service

Handles duty lifecycle management, validation, calculations, vehicle allocation,
GPS tracking, and complex business logic from driver_routes.py.
"""

from typing import Optional, Dict, Any, Tuple, List
import logging
import json
from datetime import datetime, timedelta
from flask import current_app
from models import (db, Duty, Driver, Vehicle, DutyStatus, DriverStatus, 
                   VehicleStatus, DutyScheme)
from .transaction_helper import TransactionHelper
from .audit_service import AuditService
from .vehicle_service import VehicleService
from timezone_utils import get_ist_time_naive
from utils_main import get_last_duty_values


logger = logging.getLogger(__name__)

class DutyService:
    """Service class for duty management operations"""
    
    def __init__(self):
        self.audit_service = AuditService()
        self.vehicle_service = VehicleService()
    
    def validate_duty_start(self, driver_id: int, vehicle_id: int, 
                           start_odometer: Optional[float]) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate if a driver can start a new duty.
        
        Args:
            driver_id: ID of driver starting duty
            vehicle_id: ID of vehicle to use
            start_odometer: Starting odometer reading
            
        Returns:
            tuple: (is_valid: bool, error_message: str, validation_data: dict)
        """
        try:
            # Check driver eligibility
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found", None
                
            if driver.status not in [DriverStatus.ACTIVE, DriverStatus.PENDING]:
                return False, "Driver profile is not active. Please contact admin.", None
            
            # Document verification check with database-based admin override
            documents_verified = driver.aadhar_verified and driver.license_verified
            if not documents_verified:
                # Check for valid admin override (use UTC for consistency)
                from datetime import datetime
                current_time = datetime.utcnow()
                
                admin_override_active = (
                    driver.doc_verification_override and 
                    driver.doc_verification_override_until and 
                    driver.doc_verification_override_until > current_time
                )
                
                missing_docs = []
                if not driver.aadhar_verified:
                    missing_docs.append("Aadhar")
                if not driver.license_verified:
                    missing_docs.append("Driving License")
                
                if not admin_override_active:
                    return False, f"Document verification required. Missing verified documents: {', '.join(missing_docs)}. Please contact admin for verification or emergency override.", None
                else:
                    # Log that override is being used
                    self.audit_service.log_action(
                        action='duty_start_with_doc_override',
                        entity_type='driver',
                        entity_id=driver_id,
                        details={
                            'missing_documents': missing_docs,
                            'override_reason': driver.doc_verification_override_reason,
                            'override_valid_until': driver.doc_verification_override_until.isoformat(),
                            'override_authorized_by': driver.doc_verification_override_by
                        },
                        user_id=driver.user_id
                    )
            
            # Check for existing active duty
            active_duty = Duty.query.filter(
                Duty.driver_id == driver_id,
                Duty.status == DutyStatus.ACTIVE
            ).first()
            
            if active_duty:
                return False, "Driver already has an active duty", None
            
            # Check vehicle availability
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return False, "Vehicle not found", None
                
            if vehicle.status != VehicleStatus.ACTIVE:
                return False, "Vehicle is not available for duty", None
                
            if not vehicle.is_available:
                return False, "Vehicle is currently assigned to another duty", None
            
            # Get last duty data for validation
            last_duty_data = get_last_duty_values(driver_id, vehicle_id)
            
            # Validate odometer reading
            validation_warnings = []
            if start_odometer and last_duty_data.get('vehicle_current_odometer'):
                vehicle_last_reading = last_duty_data['vehicle_current_odometer']
                
                if start_odometer < vehicle_last_reading:
                    return False, f"Invalid odometer reading. Vehicle last reading was {vehicle_last_reading} km. New reading cannot be less than this.", None
                
                # Check for significant differences
                if abs(start_odometer - vehicle_last_reading) > 50:
                    validation_warnings.append(f"Odometer reading differs significantly from expected value ({vehicle_last_reading} km)")
            
            validation_data = {
                'driver': driver,
                'vehicle': vehicle,
                'last_duty_data': last_duty_data,
                'warnings': validation_warnings
            }
            
            return True, None, validation_data
            
        except Exception as e:
            logger.error(f"Error validating duty start for driver {driver_id}: {str(e)}")
            return False, f"Validation error: {str(e)}", None
    
    @TransactionHelper.with_transaction
    def start_duty(self, driver_id: int, vehicle_id: int, start_odometer: Optional[float],
                  start_cng_level: Optional[float], start_location: Optional[Dict[str, float]] = None,
                  anomaly_flags: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Start a new duty for a driver.
        
        Args:
            driver_id: ID of driver
            vehicle_id: ID of vehicle
            start_odometer: Starting odometer reading
            start_cng_level: Starting CNG level
            start_location: Starting GPS location {lat, lng}
            anomaly_flags: Anomaly detection flags
            
        Returns:
            tuple: (success: bool, error_message: str, duty_id: int)
        """
        try:
            # Validate duty start
            is_valid, error_msg, validation_data = self.validate_duty_start(driver_id, vehicle_id, start_odometer)
            if not is_valid:
                return False, error_msg, None
            
            if not validation_data:
                return False, "Validation data not available", None
                
            driver = validation_data['driver']
            vehicle = validation_data['vehicle']
            last_duty_data = validation_data['last_duty_data']
            
            # Auto-fill odometer if not provided
            if not start_odometer and last_duty_data.get('vehicle_current_odometer'):
                start_odometer = last_duty_data['vehicle_current_odometer']
            
            # Create new duty record
            duty = Duty()
            duty.driver_id = driver_id
            duty.vehicle_id = vehicle_id
            duty.scheduled_start = get_ist_time_naive()
            duty.actual_start = get_ist_time_naive()
            duty.start_odometer = start_odometer or 0.0
            duty.start_cng = start_cng_level or 0.0
            duty.status = DutyStatus.ACTIVE
            
            # Set location if provided
            if start_location:
                duty.start_location_lat = start_location.get('lat')
                duty.start_location_lng = start_location.get('lng')
            
            # Note: Anomaly tracking would need additional fields in the Duty model
            # For now, we'll log anomalies but not store them directly on the duty record
            anomaly_detected = False
            if anomaly_flags:
                if anomaly_flags.get('odometer_anomaly_detected') or anomaly_flags.get('cng_anomaly_detected'):
                    anomaly_detected = True
            
            # Mark vehicle as unavailable and update status
            vehicle.is_available = False
            vehicle.current_odometer = start_odometer or 0.0
            driver.current_vehicle_id = vehicle_id
            
            db.session.add(duty)
            db.session.flush()  # Get duty ID
            
            # Log anomalies for admin review
            if anomaly_flags:
                anomaly_details = {
                    'duty_id': duty.id,
                    'vehicle_reg': vehicle.registration_number
                }
                if anomaly_flags.get('odometer_anomaly_detected'):
                    anomaly_details['odometer_anomaly'] = {
                        'original': anomaly_flags.get('odometer_original_value'),
                        'corrected': start_odometer
                    }
                if anomaly_flags.get('cng_anomaly_detected'):
                    anomaly_details['cng_anomaly'] = {
                        'original': anomaly_flags.get('cng_original_value'),
                        'corrected': start_cng_level
                    }
                
                self.audit_service.log_action(
                    action='duty_start_anomaly_detected',
                    entity_type='duty',
                    entity_id=duty.id,
                    details=anomaly_details,
                    user_id=driver.user_id
                )
            
            # Log duty start
            self.audit_service.log_action(
                action='start_duty',
                entity_type='duty',
                entity_id=duty.id,
                details={
                    'vehicle': vehicle.registration_number,
                    'odometer': start_odometer
                },
                user_id=driver.user_id
            )
            
            logger.info(f"Duty started: Driver {driver.full_name}, Vehicle {vehicle.registration_number}, Duty ID {duty.id}")
            return True, None, duty.id
            
        except Exception as e:
            logger.error(f"Error starting duty for driver {driver_id}: {str(e)}")
            return False, f"Failed to start duty: {str(e)}", None
    
    @TransactionHelper.with_transaction
    def end_duty(self, duty_id: int, end_odometer: Optional[float],
                end_location: Optional[Dict[str, float]] = None) -> Tuple[bool, Optional[str]]:
        """
        End an active duty.
        
        Args:
            duty_id: ID of duty to end
            end_odometer: Ending odometer reading
            end_location: Ending GPS location {lat, lng}
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            duty = Duty.query.get(duty_id)
            if not duty:
                return False, "Duty not found"
            
            if duty.status != DutyStatus.ACTIVE:
                return False, "Duty is not active"
            
            # Update duty end details
            duty.actual_end = get_ist_time_naive()
            duty.end_odometer = end_odometer
            duty.status = DutyStatus.PENDING_APPROVAL
            duty.submitted_at = get_ist_time_naive()
            
            # Calculate distance if both readings available
            if end_odometer and duty.start_odometer:
                duty.total_distance = end_odometer - duty.start_odometer
            
            # Set end location if provided
            if end_location:
                duty.end_location_lat = end_location.get('lat')
                duty.end_location_lng = end_location.get('lng')
            
            # Free up vehicle
            if duty.vehicle:
                duty.vehicle.is_available = True
                duty.vehicle.current_odometer = end_odometer or duty.vehicle.current_odometer
            
            # Clear driver's current vehicle
            if duty.driver:
                duty.driver.current_vehicle_id = None
            
            # Log duty end
            self.audit_service.log_action(
                action='end_duty',
                entity_type='duty',
                entity_id=duty_id,
                details={
                    'vehicle': duty.vehicle.registration_number if duty.vehicle else 'Unknown',
                    'end_odometer': end_odometer,
                    'total_distance': duty.total_distance
                },
                user_id=duty.driver.user_id if duty.driver else None
            )
            
            logger.info(f"Duty ended: ID {duty_id}, Distance {duty.total_distance or 0} km")
            return True, None
            
        except Exception as e:
            logger.error(f"Error ending duty {duty_id}: {str(e)}")
            return False, f"Failed to end duty: {str(e)}"
    
    def calculate_duty_earnings(self, duty_id: int) -> Tuple[bool, Optional[Dict[str, float]], Optional[str]]:
        """
        Calculate earnings for a completed duty using the new 5-method salary calculation system.
        
        Args:
            duty_id: ID of duty to calculate earnings for
            
        Returns:
            tuple: (success: bool, earnings_breakdown: dict, error_message: str)
        """
        try:
            duty = Duty.query.get(duty_id)
            if not duty:
                return False, None, "Duty not found"
            
            # Use new salary calculation system
            from services.new_salary_service import NewSalaryCalculationService
            salary_service = NewSalaryCalculationService()
            
            # Determine method based on duty scheme or default to D2D
            method = 'd2d'  # Default to D2D method
            custom_config = None
            
            if duty.duty_scheme:
                # Map old scheme types to new methods - use consistent attributes
                scheme = duty.duty_scheme
                scheme_type = getattr(scheme, 'scheme_type', None) or getattr(scheme, 'type', 'revenue_share')
                
                if scheme_type == 'final_settlement' or scheme_type == 'mixed' or scheme_type == 'd2d':
                    method = 'd2d'
                    # Load scheme configuration JSON for D2D method
                    try:
                        import json
                        if hasattr(scheme, 'configuration') and scheme.configuration:
                            scheme_config = json.loads(scheme.configuration)
                            if isinstance(scheme_config, dict):
                                custom_config = scheme_config
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse D2D scheme configuration: {e}")
                        custom_config = None
                elif scheme_type == 'fixed':
                    method = 'fixed_daily'
                    custom_config = {'daily_rate': getattr(scheme, 'fixed_amount', 500.0) or 500.0}
                elif scheme_type == 'per_trip':
                    method = 'hybrid_commission'
                    # Proper conversion: per trip rate becomes base salary, not commission percentage
                    per_trip_rate = getattr(scheme, 'per_trip_rate', 50.0) or 50.0
                    custom_config = {
                        'base_salary': per_trip_rate,  # Fixed amount per trip as base
                        'commission_threshold': 1000.0,  # Start commission after reasonable threshold
                        'commission_percentage': 10.0  # Small percentage for additional revenue
                    }
                elif scheme_type == 'slab':
                    method = 'slab_incentive'
                    revenue_pct = getattr(scheme, 'revenue_percentage', 60.0) or 60.0
                    bmg_amount = getattr(scheme, 'bmg_amount', 400.0) or 400.0
                    custom_config = {
                        'slabs': [
                            {'min_revenue': 0, 'max_revenue': 2000, 'percentage': revenue_pct},
                            {'min_revenue': 2001, 'max_revenue': 99999, 'percentage': min(revenue_pct + 10, 80.0)}
                        ],
                        'minimum_guarantee': bmg_amount
                    }
                else:
                    method = 'revenue_share'
                    custom_config = {
                        'driver_percentage': getattr(scheme, 'revenue_percentage', 70.0) or 70.0,
                        'minimum_guarantee': getattr(scheme, 'bmg_amount', 0.0) or 0.0
                    }
            
            # Calculate using new system
            result = salary_service.calculate_salary(
                duty_id=duty_id,
                method=method,
                custom_config=custom_config
            )
            
            # Update duty record
            duty.driver_earnings = result.net_salary
            import json
            from datetime import datetime
            duty.earnings_breakdown = json.dumps({
                'method': result.method_name,
                'total_salary': result.total_salary,
                'deductions': result.deductions,
                'net_salary': result.net_salary,
                'breakdown': result.breakdown,
                'calculation_notes': result.calculation_notes,
                'calculated_at': datetime.now().isoformat(),
                'system_version': 'new_5_method_system'
            })
            
            # Convert new system result to old format for backward compatibility
            breakdown = {
                'base_amount': result.base_amount,
                'incentive_amount': result.incentive_amount,
                'revenue_share': result.base_amount if method == 'revenue_share' else 0.0,
                'trip_bonus': result.incentive_amount if method == 'hybrid_commission' else 0.0,
                'bmg_guarantee': max(0, result.total_salary - result.base_amount - result.incentive_amount),
                'total_deductions': result.deductions,
                'final_earnings': result.net_salary,
                'method_used': result.method_name,
                'calculation_notes': result.calculation_notes
            }
            
            # Commit the changes in a transaction
            try:
                db.session.commit()
                logger.info(f"Salary calculated for duty {duty_id}: ₹{result.net_salary:.2f} using {result.method_name}")
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f"Error committing salary calculation for duty {duty_id}: {str(commit_error)}")
                raise commit_error

            
            return True, breakdown, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error calculating earnings for duty {duty_id}: {str(e)}")
            return False, None, f"Calculation error: {str(e)}"
            
    def _calculate_final_settlement_earnings(self, duty, scheme) -> Tuple[float, Dict[str, float]]:
        """
        Calculate earnings using Final Settlement Calculator logic
        Based on the Tamil-style settlement with CNG adjustments
        """
        # Get configuration from scheme (JSON stored configuration)
        config = {}
        if scheme.configuration:
            import json
            try:
                config = json.loads(scheme.configuration)
            except:
                config = {}
        
        # Configuration parameters with defaults
        cng_rate = config.get('cng_rate', 90.0)
        insurance_deduction = config.get('insurance_deduction_amount', 60.0)
        operator_threshold = config.get('operator_threshold', 4500.0)
        operator_low_percent = config.get('operator_low_percentage', 30.0) / 100
        operator_high_percent = config.get('operator_high_percentage', 70.0) / 100
        
        # Extract data from duty with safe attribute access
        # Cash collection inputs (map to existing fields)
        cash1 = getattr(duty, 'cash_collection', 0.0) or 0.0  # Cash Collected 1
        cash2 = getattr(duty, 'digital_payments', 0.0) or 0.0  # Cash Collected 2  
        out_cash = getattr(duty, 'card_payments', 0.0) or 0.0  # Out Cash
        
        # Operator inputs
        op1 = getattr(duty, 'uber_collected', 0.0) or 0.0  # Operator 1
        op2 = getattr(duty, 'wallet_payments', 0.0) or 0.0  # Operator 2
        out_operator = getattr(duty, 'operator_out', 0.0) or 0.0  # Out Operator
        
        # Other inputs
        pass_deduction = getattr(duty, 'pass_amount', 0.0) or 0.0  # Pass Deduction
        start_cng = getattr(duty, 'start_cng', 0.0) or 0.0  # Start CNG
        end_cng = getattr(duty, 'end_cng', 0.0) or 0.0  # End CNG
        
        # 1. Calculate totals
        total_cash = cash1 + cash2 + out_cash
        in_house_operator_total = op1 + op2
        grand_total_operator = in_house_operator_total + out_operator
        
        # 2. Gross Salary Calculation
        in_house_salary = 0.0
        if in_house_operator_total > operator_threshold:
            in_house_salary = (operator_threshold * operator_low_percent) + \
                            ((in_house_operator_total - operator_threshold) * operator_high_percent)
        else:
            in_house_salary = in_house_operator_total * operator_low_percent
        
        out_operator_salary = out_operator * operator_low_percent
        gross_salary = in_house_salary + out_operator_salary
        
        # 3. Net Salary Calculation  
        net_salary = gross_salary - insurance_deduction
        
        # 4. CNG Calculation
        base_cng = grand_total_operator * operator_low_percent  # 30% of total operator
        cng_adjustment = (start_cng - end_cng) * cng_rate
        final_cng = base_cng - cng_adjustment
        
        # 5. Final Settlement Calculation
        company_settlement = (total_cash - final_cng) + pass_deduction - net_salary
        
        # Return net salary as earnings and detailed breakdown
        earnings = net_salary
        
        breakdown = {
            'total_cash': round(total_cash, 2),
            'grand_total_operator': round(grand_total_operator, 2), 
            'gross_salary': round(gross_salary, 2),
            'insurance_deduction': round(insurance_deduction, 2),
            'net_salary': round(net_salary, 2),
            'base_cng': round(base_cng, 2),
            'cng_adjustment': round(cng_adjustment, 2),
            'final_cng': round(final_cng, 2),
            'company_settlement': round(company_settlement, 2),
            'final_earnings': round(earnings, 2),
            
            # Additional breakdown details
            'in_house_operator_total': round(in_house_operator_total, 2),
            'in_house_salary': round(in_house_salary, 2),
            'out_operator_salary': round(out_operator_salary, 2),
            'pass_deduction': round(pass_deduction, 2),
            'start_cng': round(start_cng, 2),
            'end_cng': round(end_cng, 2),
            'cng_rate': round(cng_rate, 2)
        }
        
        return earnings, breakdown
    
    def _calculate_custom_formula_earnings(self, duty, scheme) -> Tuple[float, Dict[str, float]]:
        """
        Calculate earnings for custom formula schemes (Final Settlement Calculator).
        
        Args:
            duty: Duty object with revenue and other data
            scheme: DutyScheme object with configuration
            
        Returns:
            tuple: (earnings: float, breakdown: dict)
        """
        import json
        
        try:
            # Get scheme configuration
            config = json.loads(scheme.configuration) if scheme.configuration else {}
            
            # Extract duty data from financial settlement form submitted by driver
            # Get atomic financial fields and compute totals for robustness
            operator_amount_1 = duty.gross_revenue or 0.0  # Stored in gross_revenue
            operator_amount_2 = duty.net_revenue or 0.0    # Stored in net_revenue
            out_operator = duty.operator_out or 0.0
            
            # Get individual cash collections from duty record (stored in repurposed fields)
            # Cash collections are stored separately for accurate calculation
            cash_collected_1 = duty.digital_payments or 0.0   # Repurposed field
            cash_collected_2 = duty.card_payments or 0.0      # Repurposed field
            out_cash = duty.wallet_payments or 0.0            # Repurposed field
            
            # Compute total cash for Final Settlement Calculator
            total_cash = cash_collected_1 + cash_collected_2 + out_cash
            
            # Pass deduction from fuel_deduction field
            pass_deduction = duty.fuel_deduction or 0.0
            
            # CNG data from driver form
            start_cng = duty.start_cng or 0.0
            end_cng = duty.end_cng or 0.0
            
            # Validate essential fields are present
            if start_cng == 0 and end_cng == 0:
                logger.warning(f"Duty {duty.id}: Missing CNG data for Final Settlement Calculator")
            if total_cash == 0 and operator_amount_1 == 0 and operator_amount_2 == 0:
                logger.warning(f"Duty {duty.id}: Missing financial data for Final Settlement Calculator")
            
            # Configuration defaults
            insurance_deduction = config.get('insurance_deduction', {}).get('default', 60)
            cng_rate = config.get('cng_rate', {}).get('default', 90)
            inhouse_slab_threshold = config.get('inhouse_slab_threshold', {}).get('default', 4500)
            inhouse_base_percentage = config.get('inhouse_base_percentage', {}).get('default', 30)
            inhouse_above_threshold_percentage = config.get('inhouse_above_threshold_percentage', {}).get('default', 70)
            out_operator_percentage = config.get('out_operator_percentage', {}).get('default', 30)
            base_cng_percentage = config.get('base_cng_percentage', {}).get('default', 30)
            
            # Calculate as per Final Settlement Calculator logic
            # 1. Total collections (already calculated from driver input)
            # total_cash is already set from duty.cash_collection
            inhouse_operator_total = operator_amount_1 + operator_amount_2
            grand_total_operator = inhouse_operator_total + out_operator
            
            # 2. Salary calculations
            if inhouse_operator_total > inhouse_slab_threshold:
                inhouse_salary = (inhouse_slab_threshold * inhouse_base_percentage / 100) + \
                               ((inhouse_operator_total - inhouse_slab_threshold) * inhouse_above_threshold_percentage / 100)
            else:
                inhouse_salary = inhouse_operator_total * inhouse_base_percentage / 100
            
            out_operator_salary = out_operator * out_operator_percentage / 100
            gross_salary = inhouse_salary + out_operator_salary
            net_salary = gross_salary - insurance_deduction
            
            # 3. CNG calculations - SIMPLIFIED per user request
            # New simplified formula: Final CNG = (Starting CNG Level - End CNG) * 90
            final_cng = (start_cng - end_cng) * cng_rate
            
            # 4. Final settlement
            company_settlement = (total_cash - final_cng) + pass_deduction - net_salary
            
            # Driver earnings is the net salary they receive
            earnings = net_salary
            
            # Detailed breakdown for reporting
            breakdown = {
                'total_cash': total_cash,
                'grand_total_operator': grand_total_operator,
                'inhouse_salary': inhouse_salary,
                'out_operator_salary': out_operator_salary,
                'gross_salary': gross_salary,
                'insurance_deduction': insurance_deduction,
                'net_salary': net_salary,
                'final_cng': final_cng,
                'company_settlement': company_settlement,
                'final_earnings': earnings,
                'pass_deduction': pass_deduction,
                'operator_amount_1': operator_amount_1,
                'operator_amount_2': operator_amount_2,
                'out_operator': out_operator,
                'start_cng': start_cng,
                'end_cng': end_cng,
                # Add configurable parameters to breakdown for transparency
                'salary_threshold': inhouse_slab_threshold,
                'base_percentage': inhouse_base_percentage,
                'above_threshold_percentage': inhouse_above_threshold_percentage,
                'cng_rate': cng_rate
            }
            
            return earnings, breakdown
            
        except Exception as e:
            logger.error(f"Error in custom formula calculation: {str(e)}")
            return 0.0, {'final_earnings': 0.0}
    
    def get_active_duties_summary(self) -> Dict[str, Any]:
        """
        Get summary of all active duties for dashboard.
        
        Returns:
            dict: Summary statistics
        """
        try:
            from datetime import date
            from sqlalchemy import func
            
            today = date.today()
            
            # Basic counts
            active_duties = Duty.query.filter_by(status=DutyStatus.ACTIVE).count()
            pending_approval = Duty.query.filter_by(status=DutyStatus.PENDING_APPROVAL).count()
            
            # Today's completed duties
            today_completed = Duty.query.filter(
                func.date(Duty.actual_end) == today,
                Duty.status == DutyStatus.COMPLETED
            ).count()
            
            # Today's revenue
            today_revenue = db.session.query(func.sum(Duty.revenue)).filter(
                func.date(Duty.actual_start) == today,
                Duty.status.in_([DutyStatus.ACTIVE, DutyStatus.COMPLETED, DutyStatus.PENDING_APPROVAL])
            ).scalar() or 0.0
            
            return {
                'active_duties': active_duties,
                'pending_approval': pending_approval,
                'today_completed': today_completed,
                'today_revenue': float(today_revenue),
                'summary_generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting active duties summary: {str(e)}")
            return {
                'active_duties': 0,
                'pending_approval': 0,
                'today_completed': 0,
                'today_revenue': 0.0,
                'error': str(e)
            }