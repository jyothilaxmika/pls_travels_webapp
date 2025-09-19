"""
Logging service for consistent structured logging across services
Provides standardized logging patterns for business operations
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import g, has_request_context
from utils.logging_config import get_logger


class LoggingService:
    """
    Service for consistent business operation logging
    Provides standardized logging patterns for audit, security, and operations
    """
    
    def __init__(self):
        self.logger = get_logger('services')
        self.audit_logger = get_logger('audit')
        self.security_logger = get_logger('security')
        self.performance_logger = get_logger('performance')
    
    def log_business_operation(self, operation: str, entity_type: str, entity_id: Optional[str] = None,
                             user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
                             level: int = logging.INFO):
        """
        Log a business operation with structured data
        
        Args:
            operation: The operation performed (e.g., 'create', 'update', 'delete', 'approve')
            entity_type: Type of entity (e.g., 'driver', 'vehicle', 'duty')
            entity_id: ID of the entity (if applicable)
            user_id: ID of the user performing the operation
            details: Additional operation details
            level: Logging level
        """
        log_data = {
            'operation': operation,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        # Add correlation ID if available
        if has_request_context() and hasattr(g, 'correlation_id'):
            log_data['correlation_id'] = g.correlation_id
        
        message = f"Business operation: {operation} {entity_type}"
        if entity_id:
            message += f" (ID: {entity_id})"
        
        self.logger.log(level, message, extra=log_data)
    
    def log_audit_event(self, action: str, resource: str, user_id: Optional[int] = None,
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                       success: bool = True, details: Optional[Dict[str, Any]] = None):
        """
        Log an audit event for compliance and security monitoring
        
        Args:
            action: The action performed
            resource: The resource accessed or modified
            user_id: ID of the user performing the action
            ip_address: IP address of the client
            user_agent: User agent string
            success: Whether the action was successful
            details: Additional audit details
        """
        audit_data = {
            'audit_event': action,
            'resource': resource,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            audit_data['correlation_id'] = g.correlation_id
        
        level = logging.INFO if success else logging.WARNING
        message = f"Audit: {action} on {resource} - {'SUCCESS' if success else 'FAILED'}"
        
        self.audit_logger.log(level, message, extra=audit_data)
    
    def log_security_event(self, event_type: str, severity: str = 'medium',
                          user_id: Optional[int] = None, ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None):
        """
        Log a security-related event
        
        Args:
            event_type: Type of security event (e.g., 'login_attempt', 'unauthorized_access')
            severity: Severity level ('low', 'medium', 'high', 'critical')
            user_id: ID of the user involved
            ip_address: IP address involved
            details: Additional security event details
        """
        severity_levels = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }
        
        security_data = {
            'security_event': event_type,
            'severity': severity,
            'user_id': user_id,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            security_data['correlation_id'] = g.correlation_id
        
        level = severity_levels.get(severity, logging.WARNING)
        message = f"Security Event [{severity.upper()}]: {event_type}"
        
        self.security_logger.log(level, message, extra=security_data)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str,
                             operation: Optional[str] = None, 
                             details: Optional[Dict[str, Any]] = None):
        """
        Log a performance metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            operation: Related operation (if applicable)
            details: Additional metric details
        """
        metric_data = {
            'metric': metric_name,
            'value': value,
            'unit': unit,
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            metric_data['correlation_id'] = g.correlation_id
        
        message = f"Performance metric: {metric_name} = {value} {unit}"
        if operation:
            message += f" (operation: {operation})"
        
        self.performance_logger.info(message, extra=metric_data)
    
    def log_error(self, error: Exception, context: Optional[str] = None,
                  user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        Log an error with full context and structured data
        
        Args:
            error: The exception that occurred
            context: Additional context about when/where the error occurred
            user_id: ID of the user (if applicable)
            details: Additional error details
        """
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            error_data['correlation_id'] = g.correlation_id
        
        message = f"Error occurred: {type(error).__name__}"
        if context:
            message += f" in {context}"
        
        self.logger.error(message, extra=error_data, exc_info=True)
    
    def log_external_service_call(self, service: str, operation: str, duration: float,
                                success: bool = True, response_code: Optional[int] = None,
                                details: Optional[Dict[str, Any]] = None):
        """
        Log external service API calls for monitoring and troubleshooting
        
        Args:
            service: Name of the external service (e.g., 'twilio', 'google_storage')
            operation: The operation performed
            duration: Duration of the call in seconds
            success: Whether the call was successful
            response_code: HTTP response code (if applicable)
            details: Additional call details
        """
        external_logger = get_logger('external')
        
        call_data = {
            'external_service': service,
            'operation': operation,
            'duration_seconds': duration,
            'success': success,
            'response_code': response_code,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            call_data['correlation_id'] = g.correlation_id
        
        level = logging.INFO if success else logging.ERROR
        message = f"External service call: {service}.{operation} - {'SUCCESS' if success else 'FAILED'}"
        if duration > 5.0:  # Log slow calls
            level = logging.WARNING
            message += f" (SLOW: {duration:.2f}s)"
        
        external_logger.log(level, message, extra=call_data)
    
    def log_database_operation(self, operation: str, table: str, duration: float,
                             affected_rows: Optional[int] = None, success: bool = True,
                             details: Optional[Dict[str, Any]] = None):
        """
        Log database operations for performance monitoring
        
        Args:
            operation: The database operation (e.g., 'SELECT', 'INSERT', 'UPDATE', 'DELETE')
            table: The table involved
            duration: Duration of the operation in seconds
            affected_rows: Number of rows affected (if applicable)
            success: Whether the operation was successful
            details: Additional operation details
        """
        db_logger = get_logger('database')
        
        db_data = {
            'db_operation': operation,
            'table': table,
            'duration_seconds': duration,
            'affected_rows': affected_rows,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if has_request_context() and hasattr(g, 'correlation_id'):
            db_data['correlation_id'] = g.correlation_id
        
        level = logging.INFO if success else logging.ERROR
        message = f"Database operation: {operation} on {table}"
        if affected_rows is not None:
            message += f" ({affected_rows} rows)"
        if duration > 1.0:  # Log slow queries
            level = logging.WARNING
            message += f" (SLOW: {duration:.2f}s)"
        
        db_logger.log(level, message, extra=db_data)


# Global logging service instance
logging_service = LoggingService()