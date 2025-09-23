"""
Duty Service

Handles duty lifecycle management, validation, calculations, vehicle allocation,
GPS tracking, and complex business logic from driver_routes.py.
"""

from typing import Optional, Dict, Any, Tuple, List
import logging
from datetime import datetime, timedelta
from flask import current_app
from models import (db, Duty, Driver, Vehicle, DutyStatus, DriverStatus, 
                   VehicleStatus, DutyScheme)
from .transaction_helper import TransactionHelper
from .audit_service import AuditService
from .vehicle_service import VehicleService
from timezone_utils import get_ist_time_naive
from driver_routes import get_last_duty_values

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
        Calculate earnings for a completed duty based on the duty scheme.
        
        Args:
            duty_id: ID of duty to calculate earnings for
            
        Returns:
            tuple: (success: bool, earnings_breakdown: dict, error_message: str)
        """
        try:
            duty = Duty.query.get(duty_id)
            if not duty:
                return False, None, "Duty not found"
            
            if not duty.duty_scheme:
                return False, None, "No duty scheme assigned"
            
            scheme = duty.duty_scheme
            revenue = duty.revenue or 0.0
            trips = duty.total_trips or 0
            
            earnings = 0.0
            breakdown = {
                'base_amount': 0.0,
                'revenue_share': 0.0,
                'trip_bonus': 0.0,
                'bmg_guarantee': 0.0,
                'final_earnings': 0.0
            }
            
            if scheme.scheme_type == 'fixed':
                earnings = scheme.fixed_amount or 0.0
                breakdown['base_amount'] = earnings
                
            elif scheme.scheme_type == 'per_trip':
                earnings = trips * (scheme.per_trip_rate or 0.0)
                breakdown['trip_bonus'] = earnings
                
            elif scheme.scheme_type == 'slab':
                # Implement slab-based calculation
                # This would need the slab configuration from the scheme
                earnings = revenue * (scheme.revenue_percentage or 0.0) / 100
                breakdown['revenue_share'] = earnings
                
            elif scheme.scheme_type == 'mixed':
                # Combination of fixed + revenue share
                base_amount = scheme.fixed_amount or 0.0
                revenue_share = revenue * (scheme.revenue_percentage or 0.0) / 100
                earnings = base_amount + revenue_share
                breakdown['base_amount'] = base_amount
                breakdown['revenue_share'] = revenue_share
                
            elif scheme.scheme_type == 'custom_formula':
                # Final Settlement Calculator (Scheme 1) Logic
                earnings, breakdown = self._calculate_custom_formula_earnings(duty, scheme)
            
            else:
                logger.warning(f"Unknown scheme type: {scheme.scheme_type}")
                earnings = 0.0
            
            # Apply BMG (Business Minimum Guarantee) if applicable
            if scheme.bmg_amount and earnings < scheme.bmg_amount:
                breakdown['bmg_guarantee'] = scheme.bmg_amount - earnings
                earnings = scheme.bmg_amount
            
            breakdown['final_earnings'] = earnings
            
            # Update duty with calculated earnings
            duty.driver_earnings = earnings
            db.session.commit()
            
            return True, breakdown, None
            
        except Exception as e:
            logger.error(f"Error calculating earnings for duty {duty_id}: {str(e)}")
            return False, None, f"Calculation error: {str(e)}"
    
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
            # Cash collections are stored in cash_collection field (total of cash_collected_1 + cash_collected_2 + out_cash)
            total_cash = duty.cash_collection or 0.0
            
            # Operator amounts are stored in gross_revenue and net_revenue fields
            operator_amount_1 = duty.gross_revenue or 0.0
            operator_amount_2 = duty.net_revenue or 0.0
            out_operator = duty.operator_out or 0.0
            
            # Pass deduction is stored in fuel_deduction field
            pass_deduction = duty.fuel_deduction or 0.0
            
            # CNG data from driver form
            start_cng = duty.start_cng or 0.0
            end_cng = duty.end_cng or 0.0
            
            # For individual cash collection breakdown, we'll estimate from total
            # (Admin can adjust during approval if needed)
            cash_collected_1 = total_cash * 0.6  # Estimate 60% as cash_collected_1
            cash_collected_2 = total_cash * 0.4  # Estimate 40% as cash_collected_2
            out_cash = 0.0  # Usually minimal, already included in total_cash
            
            # Configuration defaults
            insurance_deduction = config.get('insurance_deduction', {}).get('default', 60)
            cng_rate = config.get('cng_rate', {}).get('default', 90)
            inhouse_slab_threshold = config.get('inhouse_slab_threshold', {}).get('default', 4500)
            inhouse_base_percentage = config.get('inhouse_base_percentage', {}).get('default', 30)
            inhouse_above_threshold_percentage = config.get('inhouse_above_threshold_percentage', {}).get('default', 70)
            out_operator_percentage = config.get('out_operator_percentage', {}).get('default', 30)
            base_cng_percentage = config.get('base_cng_percentage', {}).get('default', 30)
            
            # Calculate as per Final Settlement Calculator logic
            # 1. Total collections
            total_cash = cash_collected_1 + cash_collected_2 + out_cash
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
            
            # 3. CNG calculations
            base_cng = grand_total_operator * base_cng_percentage / 100
            cng_adjustment = (start_cng - end_cng) * cng_rate
            final_cng = base_cng - cng_adjustment
            
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
                'base_cng': base_cng,
                'cng_adjustment': cng_adjustment,
                'final_cng': final_cng,
                'company_settlement': company_settlement,
                'final_earnings': earnings,
                'pass_deduction': pass_deduction
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