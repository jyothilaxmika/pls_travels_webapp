"""
Vehicle Service

Handles vehicle management, availability tracking, maintenance scheduling,
and allocation logic.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime, timedelta
from models import db, Vehicle, VehicleStatus, VehicleAssignment, Driver, AssignmentStatus
from .transaction_helper import TransactionHelper
from .audit_service import AuditService

logger = logging.getLogger(__name__)

class VehicleService:
    """Service class for vehicle management operations"""
    
    def __init__(self):
        self.audit_service = AuditService()
    
    def get_available_vehicles(self, branch_id: Optional[int] = None, 
                              include_cross_branch: bool = False) -> List[Vehicle]:
        """
        Get list of available vehicles for duty assignment.
        
        Args:
            branch_id: Filter by branch if specified
            include_cross_branch: Whether to include vehicles from other branches
            
        Returns:
            List of available vehicles
        """
        try:
            query = Vehicle.query.filter(
                Vehicle.status == VehicleStatus.ACTIVE,
                Vehicle.is_available == True
            )
            
            # If cross-branch is not allowed, filter by branch
            if branch_id and not include_cross_branch:
                query = query.filter(Vehicle.branch_id == branch_id)
            
            return query.order_by(Vehicle.registration_number).all()
            
        except Exception as e:
            logger.error(f"Error getting available vehicles: {str(e)}")
            return []
    
    @TransactionHelper.with_transaction
    def assign_vehicle(self, vehicle_id: int, driver_id: int, 
                      assigned_by: int, allow_cross_branch: bool = False,
                      cross_branch_reason: str = None, 
                      cross_branch_approved_by: int = None,
                      assignment_type: str = 'regular',
                      cross_branch_expires_at = None, 
                      create_pending: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Assign a vehicle to a driver, supporting cross-branch assignments with admin override.
        
        Args:
            vehicle_id: ID of vehicle to assign
            driver_id: ID of driver
            assigned_by: ID of user making the assignment
            allow_cross_branch: Whether to allow cross-branch assignment
            cross_branch_reason: Reason for cross-branch assignment
            cross_branch_approved_by: ID of admin approving cross-branch assignment
            assignment_type: Type of assignment (regular, temporary, replacement, cross_branch)
            cross_branch_expires_at: Optional expiry for cross-branch assignment
            
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
            
            # Check for cross-branch assignment
            is_cross_branch = driver.branch_id != vehicle.branch_id
            
            if is_cross_branch and not allow_cross_branch and not create_pending:
                return False, f"Cross-branch assignment not allowed. Driver is from {driver.branch.name} but vehicle is from {vehicle.branch.name}. Admin override required."
            
            if is_cross_branch and not create_pending and not cross_branch_approved_by:
                return False, "Cross-branch assignment requires admin approval"
                
            if is_cross_branch and not cross_branch_reason:
                return False, "Cross-branch assignment requires a reason"
            
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
            assignment.start_date = datetime.now().date()
            assignment.assigned_by = assigned_by
            assignment.assignment_type = assignment_type
            
            # Cross-branch assignment fields
            if is_cross_branch:
                assignment.is_cross_branch = True
                assignment.cross_branch_reason = cross_branch_reason
                assignment.cross_branch_expires_at = cross_branch_expires_at
                assignment.assignment_type = 'cross_branch'
                
                # Handle approval workflow
                if create_pending:
                    # Create pending assignment for admin approval
                    assignment.status = AssignmentStatus.PENDING_APPROVAL
                else:
                    # Direct approval (admin override)
                    assignment.cross_branch_approved_by = cross_branch_approved_by
                    assignment.cross_branch_approved_at = datetime.now()
                    assignment.status = AssignmentStatus.ACTIVE
            
            db.session.add(assignment)
            
            # For pending assignments, don't assign the vehicle yet
            if not is_cross_branch or not create_pending:
                # Update driver's current vehicle
                driver.current_vehicle_id = vehicle_id
                
                # Mark vehicle as unavailable
                vehicle.is_available = False
            
            # Log the assignment with cross-branch details
            log_details = {
                'vehicle_registration': vehicle.registration_number,
                'driver_name': driver.full_name,
                'assignment_type': assignment.assignment_type,
                'driver_branch': driver.branch.name,
                'vehicle_branch': vehicle.branch.name
            }
            
            if is_cross_branch:
                log_details.update({
                    'is_cross_branch': True,
                    'cross_branch_reason': cross_branch_reason,
                    'cross_branch_approved_by': cross_branch_approved_by,
                    'cross_branch_expires_at': cross_branch_expires_at.isoformat() if cross_branch_expires_at else None
                })
            
            self.audit_service.log_action(
                action='assign_vehicle_cross_branch' if is_cross_branch else 'assign_vehicle',
                entity_type='vehicle_assignment',
                entity_id=assignment.id,
                details=log_details,
                user_id=assigned_by
            )
            
            logger.info(f"Vehicle {vehicle.registration_number} ({'cross-branch' if is_cross_branch else 'regular'}) assigned to driver {driver.full_name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error assigning vehicle {vehicle_id} to driver {driver_id}: {str(e)}")
            return False, f"Failed to assign vehicle: {str(e)}"
    
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