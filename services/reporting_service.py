"""
Reporting Service

Handles dashboard statistics, revenue calculations, analytics,
and comprehensive reporting across all business domains.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
from models import (db, Driver, Vehicle, Duty, Branch, AuditLog, 
                   DriverStatus, VehicleStatus, DutyStatus)

logger = logging.getLogger(__name__)

class ReportingService:
    """Service class for reporting and analytics operations"""
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics for admin overview.
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            today = date.today()
            
            # Basic entity counts
            total_drivers = Driver.query.filter_by(status=DriverStatus.ACTIVE).count()
            total_vehicles = Vehicle.query.filter_by(status=VehicleStatus.ACTIVE).count()
            total_branches = Branch.query.filter_by(is_active=True).count()
            
            # Active duties today
            active_duties = Duty.query.filter(
                and_(func.date(Duty.start_time) == today, Duty.status == DutyStatus.ACTIVE)
            ).count()
            
            pending_duties = Duty.query.filter_by(status=DutyStatus.PENDING_APPROVAL).count()
            
            # Revenue statistics with branch breakdown
            revenue_stats = self._get_branch_revenue_stats(today)
            
            # Recent activities
            recent_activities = AuditLog.query.options(
                db.joinedload(AuditLog.user)
            ).order_by(AuditLog.created_at.desc()).limit(10).all()
            
            return {
                'total_drivers': total_drivers,
                'total_vehicles': total_vehicles,
                'total_branches': total_branches,
                'active_duties': active_duties,
                'pending_duties': pending_duties,
                'revenue_stats': revenue_stats,
                'recent_activities': recent_activities,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard statistics: {str(e)}")
            return {
                'total_drivers': 0,
                'total_vehicles': 0,
                'total_branches': 0,
                'active_duties': 0,
                'pending_duties': 0,
                'revenue_stats': [],
                'recent_activities': [],
                'error': str(e)
            }
    
    def _get_branch_revenue_stats(self, target_date: date) -> List[Dict[str, Any]]:
        """Get revenue statistics by branch for a specific date."""
        try:
            # Explicit join condition via branch_id foreign key relationship
            revenue_stats = db.session.query(
                Branch.name,
                Branch.target_revenue,
                func.coalesce(func.sum(Duty.revenue), 0).label('actual_revenue')
            ).outerjoin(Duty, and_(
                Duty.branch_id == Branch.id,
                func.date(Duty.start_time) == target_date
            )) \
             .filter(Branch.is_active == True) \
             .group_by(Branch.id, Branch.name, Branch.target_revenue) \
             .limit(20).all()
            
            return [
                {
                    'branch_name': stat.name,
                    'target_revenue': float(stat.target_revenue or 0),
                    'actual_revenue': float(stat.actual_revenue),
                    'achievement_rate': (stat.actual_revenue / stat.target_revenue * 100) 
                                      if stat.target_revenue else 0
                }
                for stat in revenue_stats
            ]
            
        except Exception as e:
            logger.error(f"Error getting branch revenue stats: {str(e)}")
            return []
    
    def get_driver_performance_report(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Generate driver performance report.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of driver performance data
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query driver performance data
            performance_data = db.session.query(
                Driver.id,
                Driver.full_name,
                Driver.employee_id,
                Branch.name.label('branch_name'),
                func.count(Duty.id).label('total_duties'),
                func.coalesce(func.sum(Duty.revenue), 0).label('total_revenue'),
                func.coalesce(func.sum(Duty.driver_earnings), 0).label('total_earnings'),
                func.coalesce(func.sum(Duty.total_distance), 0).label('total_distance'),
                func.avg(Duty.driver_earnings).label('avg_earnings_per_duty')
            ).join(Branch, Driver.branch_id == Branch.id) \
             .outerjoin(Duty, and_(
                 Duty.driver_id == Driver.id,
                 Duty.created_at >= cutoff_date
             )) \
             .filter(Driver.status == DriverStatus.ACTIVE) \
             .group_by(Driver.id, Driver.full_name, Driver.employee_id, Branch.name) \
             .order_by(func.sum(Duty.revenue).desc()) \
             .all()
            
            return [
                {
                    'driver_id': data.id,
                    'driver_name': data.full_name,
                    'employee_id': data.employee_id,
                    'branch_name': data.branch_name,
                    'total_duties': data.total_duties or 0,
                    'total_revenue': float(data.total_revenue),
                    'total_earnings': float(data.total_earnings),
                    'total_distance': float(data.total_distance),
                    'avg_earnings_per_duty': float(data.avg_earnings_per_duty or 0),
                    'revenue_per_km': float(data.total_revenue / data.total_distance) 
                                    if data.total_distance else 0
                }
                for data in performance_data
            ]
            
        except Exception as e:
            logger.error(f"Error generating driver performance report: {str(e)}")
            return []
    
    def get_revenue_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Get revenue trend data for charts.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            dict: Revenue trend data
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Daily revenue data
            daily_revenue = db.session.query(
                func.date(Duty.actual_start).label('duty_date'),
                func.coalesce(func.sum(Duty.revenue), 0).label('daily_revenue'),
                func.count(Duty.id).label('duty_count')
            ).filter(
                func.date(Duty.actual_start).between(start_date, end_date),
                Duty.status.in_([DutyStatus.COMPLETED, DutyStatus.PENDING_APPROVAL])
            ).group_by(func.date(Duty.actual_start)) \
             .order_by(func.date(Duty.actual_start)) \
             .all()
            
            # Format for chart consumption
            dates = []
            revenues = []
            duty_counts = []
            
            for data in daily_revenue:
                dates.append(data.duty_date.isoformat())
                revenues.append(float(data.daily_revenue))
                duty_counts.append(data.duty_count)
            
            # Calculate summary statistics
            total_revenue = sum(revenues)
            avg_daily_revenue = total_revenue / len(revenues) if revenues else 0
            total_duties = sum(duty_counts)
            avg_duties_per_day = total_duties / len(duty_counts) if duty_counts else 0
            
            return {
                'dates': dates,
                'revenues': revenues,
                'duty_counts': duty_counts,
                'summary': {
                    'total_revenue': total_revenue,
                    'avg_daily_revenue': avg_daily_revenue,
                    'total_duties': total_duties,
                    'avg_duties_per_day': avg_duties_per_day,
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue trend: {str(e)}")
            return {'dates': [], 'revenues': [], 'duty_counts': [], 'summary': {}, 'error': str(e)}
    
    def get_fleet_utilization_report(self) -> List[Dict[str, Any]]:
        """
        Generate fleet utilization report.
        
        Returns:
            List of vehicle utilization data
        """
        try:
            from datetime import datetime, timedelta
            
            # Last 7 days utilization
            cutoff_date = datetime.now() - timedelta(days=7)
            
            utilization_data = db.session.query(
                Vehicle.id,
                Vehicle.registration_number,
                Vehicle.model,
                Branch.name.label('branch_name'),
                func.count(Duty.id).label('duty_count'),
                func.coalesce(func.sum(Duty.total_distance), 0).label('total_distance'),
                func.coalesce(func.sum(Duty.revenue), 0).label('total_revenue')
            ).join(Branch, Vehicle.branch_id == Branch.id) \
             .outerjoin(Duty, and_(
                 Duty.vehicle_id == Vehicle.id,
                 Duty.created_at >= cutoff_date
             )) \
             .filter(Vehicle.status == VehicleStatus.ACTIVE) \
             .group_by(Vehicle.id, Vehicle.registration_number, Vehicle.model, Branch.name) \
             .order_by(func.count(Duty.id).desc()) \
             .all()
            
            return [
                {
                    'vehicle_id': data.id,
                    'registration_number': data.registration_number,
                    'model': data.model,
                    'branch_name': data.branch_name,
                    'duty_count': data.duty_count or 0,
                    'total_distance': float(data.total_distance),
                    'total_revenue': float(data.total_revenue),
                    'avg_revenue_per_duty': float(data.total_revenue / data.duty_count) 
                                          if data.duty_count else 0,
                    'utilization_rate': (data.duty_count / 7) * 100 if data.duty_count else 0
                }
                for data in utilization_data
            ]
            
        except Exception as e:
            logger.error(f"Error generating fleet utilization report: {str(e)}")
            return []