"""
Driver Service

Handles driver lifecycle management, approval workflows, status changes,
and profile management. Encapsulates business logic from admin_routes.py
and driver_routes.py for better testability and maintenance.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime, timedelta
from flask import current_app
from models import db, Driver, User, Branch, AuditLog, DriverStatus, UserStatus, UserRole
from .transaction_helper import TransactionHelper
from .audit_service import AuditService
from timezone_utils import get_ist_time_naive

logger = logging.getLogger(__name__)

class DriverService:
    """Service class for driver management operations"""
    
    def __init__(self):
        self.audit_service = AuditService()
    
    @TransactionHelper.with_transaction
    def approve_driver(self, driver_id: int, approved_by: int) -> Tuple[bool, Optional[str]]:
        """
        Approve a driver and activate their user account.
        
        Args:
            driver_id: ID of driver to approve
            approved_by: ID of user approving the driver
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            if driver.status == DriverStatus.ACTIVE:
                return False, "Driver is already active"
            
            # Update driver status
            driver.status = DriverStatus.ACTIVE
            driver.approved_by = approved_by
            driver.approved_at = get_ist_time_naive()
            
            # Activate user account
            if driver.user:
                driver.user.status = UserStatus.ACTIVE
            else:
                return False, "Driver has no associated user account"
            
            # Log the approval
            self.audit_service.log_action(
                action='approve_driver',
                entity_type='driver',
                entity_id=driver_id,
                details={
                    'driver_name': driver.full_name,
                    'branch': driver.branch.name if driver.branch else 'Unknown'
                },
                user_id=approved_by
            )
            
            logger.info(f"Driver {driver.full_name} (ID: {driver_id}) approved by user {approved_by}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error approving driver {driver_id}: {str(e)}")
            return False, f"Failed to approve driver: {str(e)}"
    
    @TransactionHelper.with_transaction
    def reject_driver(self, driver_id: int, rejected_by: int, reason: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Reject a driver application.
        
        Args:
            driver_id: ID of driver to reject
            rejected_by: ID of user rejecting the driver
            reason: Optional reason for rejection
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            # Update driver status
            driver.status = DriverStatus.REJECTED
            driver.approved_by = rejected_by
            driver.approved_at = get_ist_time_naive()
            
            # Log the rejection
            details = {
                'driver_name': driver.full_name,
                'branch': driver.branch.name if driver.branch else 'Unknown'
            }
            if reason:
                details['reason'] = reason
            
            self.audit_service.log_action(
                action='reject_driver',
                entity_type='driver',
                entity_id=driver_id,
                details=details,
                user_id=rejected_by
            )
            
            logger.info(f"Driver {driver.full_name} (ID: {driver_id}) rejected by user {rejected_by}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error rejecting driver {driver_id}: {str(e)}")
            return False, f"Failed to reject driver: {str(e)}"
    
    @TransactionHelper.with_transaction
    def block_driver(self, driver_id: int, blocked_by: int, reason: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Block a driver and handle their active assignments.
        
        Args:
            driver_id: ID of driver to block
            blocked_by: ID of user blocking the driver
            reason: Optional reason for blocking
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            from models import Duty, DutyStatus, VehicleAssignment
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            # End any active duties
            active_duties = Duty.query.filter(
                Duty.driver_id == driver_id,
                Duty.status == DutyStatus.ACTIVE
            ).all()
            
            for duty in active_duties:
                duty.status = DutyStatus.TERMINATED
                duty.actual_end = get_ist_time_naive()
                
                # Free up the vehicle
                if duty.vehicle:
                    duty.vehicle.is_available = True
            
            # End any active vehicle assignments
            active_assignments = VehicleAssignment.query.filter(
                VehicleAssignment.driver_id == driver_id,
                VehicleAssignment.end_date.is_(None)
            ).all()
            
            for assignment in active_assignments:
                assignment.end_date = get_ist_time_naive()
            
            # Update driver status
            driver.status = DriverStatus.SUSPENDED
            driver.current_vehicle_id = None
            
            # Deactivate user account
            if driver.user:
                driver.user.status = UserStatus.INACTIVE
            
            # Log the blocking
            details = {
                'driver_name': driver.full_name,
                'active_duties_ended': len(active_duties),
                'assignments_ended': len(active_assignments)
            }
            if reason:
                details['reason'] = reason
            
            self.audit_service.log_action(
                action='block_driver',
                entity_type='driver',
                entity_id=driver_id,
                details=details,
                user_id=blocked_by
            )
            
            logger.info(f"Driver {driver.full_name} (ID: {driver_id}) blocked by user {blocked_by}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error blocking driver {driver_id}: {str(e)}")
            return False, f"Failed to block driver: {str(e)}"
    
    @TransactionHelper.with_transaction
    def unblock_driver(self, driver_id: int, unblocked_by: int) -> Tuple[bool, Optional[str]]:
        """
        Unblock a driver and reactivate their account.
        
        Args:
            driver_id: ID of driver to unblock
            unblocked_by: ID of user unblocking the driver
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            if driver.status != DriverStatus.SUSPENDED:
                return False, "Driver is not currently blocked"
            
            # Reactivate driver
            driver.status = DriverStatus.ACTIVE
            
            # Reactivate user account
            if driver.user:
                driver.user.status = UserStatus.ACTIVE
            
            # Log the unblocking
            self.audit_service.log_action(
                action='unblock_driver',
                entity_type='driver',
                entity_id=driver_id,
                details={'driver_name': driver.full_name},
                user_id=unblocked_by
            )
            
            logger.info(f"Driver {driver.full_name} (ID: {driver_id}) unblocked by user {unblocked_by}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error unblocking driver {driver_id}: {str(e)}")
            return False, f"Failed to unblock driver: {str(e)}"
    
    def get_driver_statistics(self, driver_id: int, months: int = 6) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive statistics for a driver.
        
        Args:
            driver_id: ID of driver
            months: Number of months to analyze (default: 6)
            
        Returns:
            dict: Driver statistics or None if not found
        """
        try:
            from models import Duty, DutyStatus, Penalty
            from collections import defaultdict
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return None
            
            # Get duties for analysis
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            duties = Duty.query.filter(
                Duty.driver_id == driver_id,
                Duty.created_at >= cutoff_date
            ).all()
            
            # Basic statistics
            total_duties = len(duties)
            active_duties = [d for d in duties if d.status == DutyStatus.ACTIVE]
            completed_duties = [d for d in duties if d.status == DutyStatus.COMPLETED]
            
            # Financial statistics
            total_earnings = sum(duty.driver_earnings or 0 for duty in duties)
            total_revenue = sum(duty.revenue or 0 for duty in duties)
            
            # Penalties
            penalties = Penalty.query.filter(
                Penalty.driver_id == driver_id,
                Penalty.applied_at >= cutoff_date
            ).all()
            total_penalties = sum(penalty.amount or 0 for penalty in penalties)
            
            # Monthly breakdown
            monthly_stats = defaultdict(lambda: {'duties': 0, 'earnings': 0, 'trips': 0, 'revenue': 0})
            for duty in duties:
                if duty.created_at:
                    month_key = duty.created_at.strftime('%Y-%m')
                    monthly_stats[month_key]['duties'] += 1
                    monthly_stats[month_key]['earnings'] += duty.driver_earnings or 0
                    monthly_stats[month_key]['trips'] += duty.total_trips or 0
                    monthly_stats[month_key]['revenue'] += duty.revenue or 0
            
            return {
                'driver': driver,
                'total_duties': total_duties,
                'active_duties': len(active_duties),
                'completed_duties': len(completed_duties),
                'total_earnings': total_earnings,
                'total_revenue': total_revenue,
                'total_penalties': total_penalties,
                'net_earnings': total_earnings - total_penalties,
                'monthly_stats': dict(monthly_stats),
                'average_earnings_per_duty': total_earnings / total_duties if total_duties > 0 else 0,
                'completion_rate': len(completed_duties) / total_duties if total_duties > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting driver statistics for {driver_id}: {str(e)}")
            return None
    
    def get_drivers_with_filters(self, status_filter: Optional[str] = None, 
                               branch_filter: Optional[int] = None,
                               page: int = 1, per_page: int = 20) -> Optional[Any]:
        """
        Get paginated list of drivers with filters.
        
        Args:
            status_filter: Filter by driver status
            branch_filter: Filter by branch ID
            page: Page number
            per_page: Items per page
            
        Returns:
            Paginated driver query result
        """
        try:
            query = Driver.query
            
            if status_filter:
                try:
                    status_enum = DriverStatus(status_filter)
                    query = query.filter(Driver.status == status_enum)
                except ValueError:
                    # Invalid status filter, ignore it
                    pass
            
            if branch_filter:
                query = query.filter(Driver.branch_id == branch_filter)
            
            return query.paginate(page=page, per_page=per_page, error_out=False)
            
        except Exception as e:
            logger.error(f"Error getting drivers with filters: {str(e)}")
            return None