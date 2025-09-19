"""
Audit Service

Centralized audit logging service for tracking all user actions,
security events, and system changes. Provides consistent audit
trail across all business operations.
"""

from typing import Optional, Dict, Any, List
import logging
import json
from datetime import datetime
from flask import request, g
from flask_login import current_user
from models import db, AuditLog
from .transaction_helper import TransactionHelper

logger = logging.getLogger(__name__)

class AuditService:
    """Service class for centralized audit logging"""
    
    @staticmethod
    def log_action(action: str, 
                  entity_type: Optional[str] = None,
                  entity_id: Optional[int] = None,
                  details: Optional[Dict[str, Any]] = None,
                  user_id: Optional[int] = None) -> bool:
        """
        Log an audit event with comprehensive context.
        
        Args:
            action: Action performed (e.g., 'approve_driver', 'start_duty')
            entity_type: Type of entity affected (e.g., 'driver', 'duty', 'vehicle')
            entity_id: ID of the affected entity
            details: Additional details about the action
            user_id: ID of user performing the action (defaults to current_user)
            
        Returns:
            bool: True if logging successful, False otherwise
        """
        try:
            # Use provided user_id or current authenticated user
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            
            # Only log if we have a valid user (skip for system operations)
            if user_id is None:
                logger.debug(f"Skipping audit log for system action: {action}")
                return True
            
            audit = AuditLog()
            audit.user_id = user_id
            audit.action = action
            audit.entity_type = entity_type
            audit.entity_id = entity_id
            audit.new_values = json.dumps(details) if details else None
            
            # Capture request context if available
            if request:
                audit.ip_address = request.remote_addr
                audit.user_agent = request.headers.get('User-Agent', '')[:255]
            
            db.session.add(audit)
            
            # Let outer transaction handle the commit
            # DO NOT commit here - this breaks atomicity of service operations
            logger.debug(f"Audit logged: {action} by user {user_id}")
            return True
                        
        except Exception as e:
            logger.error(f"Error logging audit action '{action}': {str(e)}")
            return False
        
        return False
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any]) -> bool:
        """
        Log security-related events with high priority.
        
        Args:
            event_type: Type of security event (e.g., 'login_failed', 'otp_abuse')
            details: Event details including IP, user agent, etc.
            
        Returns:
            bool: True if logging successful
        """
        try:
            # Add correlation ID if available
            correlation_id = getattr(g, 'correlation_id', None)
            if correlation_id:
                details['correlation_id'] = correlation_id
            
            return AuditService.log_action(
                action=f'SECURITY_{event_type.upper()}',
                entity_type='security',
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error logging security event '{event_type}': {str(e)}")
            return False
    
    @staticmethod
    def get_user_activity(user_id: int, limit: int = 50) -> List[AuditLog]:
        """
        Get recent activity for a specific user.
        
        Args:
            user_id: ID of user
            limit: Maximum number of records to return
            
        Returns:
            List of AuditLog records
        """
        try:
            return AuditLog.query.filter_by(user_id=user_id) \
                               .order_by(AuditLog.created_at.desc()) \
                               .limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting user activity for {user_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_entity_history(entity_type: str, entity_id: int, limit: int = 50) -> List[AuditLog]:
        """
        Get audit history for a specific entity.
        
        Args:
            entity_type: Type of entity (e.g., 'driver', 'duty')
            entity_id: ID of entity
            limit: Maximum number of records to return
            
        Returns:
            List of AuditLog records
        """
        try:
            return AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id) \
                               .order_by(AuditLog.created_at.desc()) \
                               .limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting entity history for {entity_type}:{entity_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_activities(limit: int = 20) -> List[AuditLog]:
        """
        Get recent system-wide activities for dashboard display.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of AuditLog records with user information
        """
        try:
            return AuditLog.query.options(
                db.joinedload(AuditLog.user)
            ).order_by(AuditLog.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
            return []
    
    @staticmethod 
    def cleanup_old_logs(days_to_keep: int = 90) -> int:
        """
        Clean up old audit logs to maintain database performance.
        
        Args:
            days_to_keep: Number of days of logs to retain
            
        Returns:
            int: Number of records deleted
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Count records to be deleted
            count = AuditLog.query.filter(AuditLog.created_at < cutoff_date).count()
            
            if count > 0:
                # Delete old records
                AuditLog.query.filter(AuditLog.created_at < cutoff_date).delete()
                db.session.commit()
                
                logger.info(f"Cleaned up {count} audit log records older than {days_to_keep} days")
            
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up audit logs: {str(e)}")
            return 0