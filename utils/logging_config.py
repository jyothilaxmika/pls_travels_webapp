"""
Centralized logging configuration for PLS Travels
Provides structured JSON logging, request/response tracking, and monitoring setup
"""

import os
import sys
import json
import logging
import logging.config
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import has_request_context, request, g
import traceback


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    Includes correlation ID, request context, and application metadata
    """
    
    def __init__(self):
        super().__init__()
        self.application_name = "pls_travels"
        self.environment = os.environ.get('FLASK_ENV', 'development')
        self.deployment_id = os.environ.get('REPL_DEPLOYMENT_ID', 'unknown')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log data
        log_data: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'application': self.application_name,
            'environment': self.environment,
            'deployment_id': self.deployment_id
        }
        
        # Add correlation ID if available
        if has_request_context() and hasattr(g, 'correlation_id'):
            log_data['correlation_id'] = g.correlation_id
        
        # Add request context if available
        if has_request_context() and request:
            try:
                log_data['request'] = {
                    'method': request.method,
                    'url': request.url,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'content_type': request.headers.get('Content-Type', ''),
                    'content_length': request.headers.get('Content-Length'),
                    'referrer': request.headers.get('Referer')
                }
                
                # Add user context if available
                if hasattr(g, 'current_user_id'):
                    log_data['user'] = {
                        'user_id': g.current_user_id,
                        'username': getattr(g, 'current_username', 'unknown')
                    }
            except Exception:
                # Avoid logging errors in the logger itself
                pass
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message']:
                extra_fields[key] = value
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        # Add code location for debug/error levels
        if record.levelno in (logging.DEBUG, logging.ERROR):
            log_data['location'] = {
                'file': record.pathname,
                'function': record.funcName,
                'line': record.lineno
            }
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class RequestContextFilter(logging.Filter):
    """
    Filter to inject request context into log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record"""
        if has_request_context():
            # Add correlation ID
            if hasattr(g, 'correlation_id'):
                record.correlation_id = g.correlation_id
            
            # Add request timing if available
            if hasattr(g, 'request_start_time'):
                record.request_duration = datetime.now().timestamp() - g.request_start_time
        
        return True


def setup_logging(app=None) -> Dict[str, logging.Logger]:
    """
    Configure centralized logging for the application
    Returns dict of configured loggers for different components
    """
    
    # Determine log level from environment
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        log_level = 'INFO'
    
    # Configure JSON formatting for production, simple for development
    use_json_logging = (
        os.environ.get('USE_JSON_LOGGING', 'false').lower() == 'true' or
        os.environ.get('FLASK_ENV') == 'production' or
        os.environ.get('REPL_DEPLOYMENT') == 'true'
    )
    
    # Configure logging
    if use_json_logging:
        formatter = JSONFormatter()
    else:
        # Development-friendly format
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())
    
    # File handler for errors (always enabled)
    os.makedirs('logs', exist_ok=True)
    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(RequestContextFilter())
    
    # File handler for all logs (optional)
    file_handler = None
    if os.environ.get('ENABLE_FILE_LOGGING', 'false').lower() == 'true':
        file_handler = logging.FileHandler('logs/application.log')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestContextFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    if file_handler:
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers for application components
    loggers = {}
    
    # Application logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    loggers['app'] = app_logger
    
    # Service layer loggers
    loggers['services'] = logging.getLogger('services')
    loggers['services'].setLevel(log_level)
    
    loggers['models'] = logging.getLogger('models')
    loggers['models'].setLevel(log_level)
    
    loggers['utils'] = logging.getLogger('utils')
    loggers['utils'].setLevel(log_level)
    
    # Request logging
    loggers['requests'] = logging.getLogger('requests')
    loggers['requests'].setLevel(log_level)
    
    # Security logging
    loggers['security'] = logging.getLogger('security')
    loggers['security'].setLevel(log_level)
    
    # Performance monitoring
    loggers['performance'] = logging.getLogger('performance')
    loggers['performance'].setLevel(log_level)
    
    # Audit logging
    loggers['audit'] = logging.getLogger('audit')
    loggers['audit'].setLevel(log_level)
    
    # Database logging
    loggers['database'] = logging.getLogger('database')
    loggers['database'].setLevel(log_level)
    
    # Third-party service logging
    loggers['external'] = logging.getLogger('external')
    loggers['external'].setLevel(log_level)
    
    # Silence noisy third-party loggers in production
    if os.environ.get('FLASK_ENV') == 'production':
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    if app:
        app.logger.info(f"Logging configured: level={log_level}, json_format={use_json_logging}")
        app.logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    return loggers


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    Ensures consistent configuration across the application
    """
    return logging.getLogger(name)


def log_request_start():
    """Mark the start of request processing for timing"""
    if has_request_context():
        g.request_start_time = datetime.now().timestamp()


def log_request_end(response):
    """Log request completion with timing and response info"""
    if has_request_context() and hasattr(g, 'request_start_time'):
        duration = datetime.now().timestamp() - g.request_start_time
        
        logger = get_logger('requests')
        
        # Log request completion with structured data
        extra_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'response_size': response.content_length or 0,
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
        
        # Add user context if available
        if hasattr(g, 'current_user_id'):
            extra_data['user_id'] = g.current_user_id
        
        # Determine log level based on response status
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        elif duration > 5.0:  # Slow requests
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        logger.log(log_level, f"Request completed: {request.method} {request.path}", extra=extra_data)
    
    return response


# Pre-configured logger instances for common use cases
LOGGERS = {
    'app': get_logger('app'),
    'services': get_logger('services'),
    'models': get_logger('models'),
    'utils': get_logger('utils'),
    'requests': get_logger('requests'),
    'security': get_logger('security'),
    'performance': get_logger('performance'),
    'audit': get_logger('audit'),
    'database': get_logger('database'),
    'external': get_logger('external')
}