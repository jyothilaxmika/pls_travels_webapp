"""
Vehicle Service

Handles vehicle management, availability tracking, maintenance scheduling,
and allocation logic.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime, timedelta
from models import db, Vehicle, VehicleStatus, VehicleAssignment, Driver
from .transaction_helper import TransactionHelper
from .audit_service import AuditService

logger = logging.getLogger(__name__)

class VehicleService:
    """Service class for vehicle management operations"""
    
    def __init__(self):
        self.audit_service = AuditService()
    
    def get_available_vehicles(self, branch_id: Optional[int] = None) -> List[Vehicle]:
        """
        Get list of available vehicles for duty assignment.
        
        Args:
            branch_id: Filter by branch if specified
            
        Returns:
            List of available vehicles
        """
        try:
            query = Vehicle.query.filter(
                Vehicle.status == VehicleStatus.ACTIVE,
                Vehicle.is_available == True
            )
            
            if branch_id:
                query = query.filter(Vehicle.branch_id == branch_id)
            
            return query.order_by(Vehicle.registration_number).all()
            
        except Exception as e:
            logger.error(f"Error getting available vehicles: {str(e)}")
            return []
    
    @TransactionHelper.with_transaction
    def assign_vehicle(self, vehicle_id: int, driver_id: int, 
                      assigned_by: int) -> Tuple[bool, Optional[str]]:
        """
        Assign a vehicle to a driver.
        
        Args:
            vehicle_id: ID of vehicle to assign
            driver_id: ID of driver
            assigned_by: ID of user making the assignment
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return False, "Vehicle not found"
                
            if vehicle.status != VehicleStatus.ACTIVE:
                return False, "Vehicle is not active"
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            # Check if vehicle is already assigned
            existing_assignment = VehicleAssignment.query.filter(
                VehicleAssignment.vehicle_id == vehicle_id,
                VehicleAssignment.end_date.is_(None)
            ).first()
            
            if existing_assignment:
                return False, "Vehicle is already assigned to another driver"
            
            # Create new assignment
            assignment = VehicleAssignment()
            assignment.vehicle_id = vehicle_id
            assignment.driver_id = driver_id
            assignment.start_date = datetime.now()
            assignment.assigned_by = assigned_by
            
            db.session.add(assignment)
            
            # Update driver's current vehicle
            driver.current_vehicle_id = vehicle_id
            
            # Log the assignment
            self.audit_service.log_action(
                action='assign_vehicle',
                entity_type='vehicle_assignment',
                entity_id=assignment.id,
                details={
                    'vehicle_reg': vehicle.registration_number,
                    'driver_name': driver.full_name
                },
                user_id=assigned_by
            )
            
            logger.info(f"Vehicle {vehicle.registration_number} assigned to driver {driver.full_name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error assigning vehicle {vehicle_id} to driver {driver_id}: {str(e)}")
            return False, f"Assignment failed: {str(e)}"
    
    def get_vehicle_utilization(self, vehicle_id: int, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get vehicle utilization statistics.
        
        Args:
            vehicle_id: ID of vehicle
            days: Number of days to analyze
            
        Returns:
            dict: Utilization statistics
        """
        try:
            from models import Duty, DutyStatus
            from sqlalchemy import func
            
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return None
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get duties for this vehicle in the period
            duties = Duty.query.filter(
                Duty.vehicle_id == vehicle_id,
                Duty.created_at >= cutoff_date
            ).all()
            
            total_duties = len(duties)
            total_distance = sum(duty.total_distance or 0 for duty in duties)
            total_revenue = sum(duty.revenue or 0 for duty in duties)
            
            # Calculate active hours (simplified)
            total_hours = 0
            for duty in duties:
                if duty.actual_start and duty.actual_end:
                    duration = duty.actual_end - duty.actual_start
                    total_hours += duration.total_seconds() / 3600
            
            return {
                'vehicle': vehicle,
                'period_days': days,
                'total_duties': total_duties,
                'total_distance': total_distance,
                'total_revenue': total_revenue,
                'total_hours': total_hours,
                'avg_distance_per_duty': total_distance / total_duties if total_duties > 0 else 0,
                'avg_revenue_per_duty': total_revenue / total_duties if total_duties > 0 else 0,
                'utilization_rate': total_duties / days if days > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting vehicle utilization for {vehicle_id}: {str(e)}")
            return None