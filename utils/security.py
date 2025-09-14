"""
Security utilities for data sanitization and protection
"""
import re
import json
from typing import Dict, Any, Union, List


class AuditDataSanitizer:
    """Handles sanitization of audit log data to protect sensitive information"""
    
    # Sensitive field patterns to redact
    SENSITIVE_PATTERNS = [
        r'password',
        r'secret',
        r'token',
        r'key',
        r'api_key',
        r'access_token',
        r'refresh_token',
        r'authorization',
        r'auth',
        r'credential',
        r'private',
        r'session',
        r'salt',
        r'hash'
    ]
    
    # Email and phone patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?1?[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
    
    @classmethod
    def sanitize_json_data(cls, data: Union[str, Dict, None]) -> Dict[str, Any]:
        """
        Sanitize JSON data by redacting sensitive fields
        """
        if not data:
            return {}
        
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            if not isinstance(data, dict):
                return {}
            
            sanitized = {}
            for key, value in data.items():
                if cls._is_sensitive_field(key):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, str):
                    sanitized[key] = cls._sanitize_string_value(value)
                elif isinstance(value, dict):
                    sanitized[key] = cls.sanitize_json_data(value)
                elif isinstance(value, list):
                    sanitized[key] = [cls.sanitize_json_data(item) if isinstance(item, dict) 
                                    else cls._sanitize_string_value(str(item)) if isinstance(item, str)
                                    else item for item in value]
                else:
                    sanitized[key] = value
            
            return sanitized
            
        except (json.JSONDecodeError, TypeError, AttributeError):
            return {"error": "Invalid JSON data"}
    
    @classmethod
    def _is_sensitive_field(cls, field_name: str) -> bool:
        """Check if a field name indicates sensitive data"""
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in cls.SENSITIVE_PATTERNS)
    
    @classmethod
    def _sanitize_string_value(cls, value: str) -> str:
        """Sanitize string values by masking emails and phone numbers"""
        if not isinstance(value, str):
            return str(value)
        
        # Replace emails with masked version
        value = cls.EMAIL_PATTERN.sub(lambda m: cls._mask_email(m.group()), value)
        
        # Replace phone numbers with masked version
        value = cls.PHONE_PATTERN.sub(lambda m: cls._mask_phone(m.group()), value)
        
        return value
    
    @classmethod
    def _mask_email(cls, email: str) -> str:
        """Mask email address for privacy"""
        try:
            local, domain = email.split('@')
            if len(local) <= 2:
                masked_local = '*' * len(local)
            else:
                masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
            return f"{masked_local}@{domain}"
        except ValueError:
            return email
    
    @classmethod
    def _mask_phone(cls, phone: str) -> str:
        """Mask phone number for privacy"""
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 4:
            return f"***-***-{digits[-4:]}"
        return "*" * len(phone)
    
    @classmethod
    def sanitize_error_message(cls, error_msg: str) -> str:
        """Sanitize error messages to remove sensitive information"""
        if not error_msg:
            return ""
        
        # Remove potential sensitive data from error messages
        sanitized = cls._sanitize_string_value(error_msg)
        
        # Remove common sensitive patterns from error messages
        sensitive_in_errors = [
            r'password=\S+',
            r'token=\S+',
            r'key=\S+',
            r'secret=\S+',
            r'auth=\S+',
            r'api_key=\S+',
        ]
        
        for pattern in sensitive_in_errors:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @classmethod
    def mask_ip_address(cls, ip_address: str) -> str:
        """Partially mask IP address for privacy"""
        if not ip_address or ip_address == 'Unknown':
            return ip_address
        
        # IPv4 masking
        if '.' in ip_address:
            parts = ip_address.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.xxx.xxx"
        
        # IPv6 masking  
        if ':' in ip_address:
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return f"{parts[0]}:{parts[1]}:xxxx:xxxx"
        
        return ip_address
    
    @classmethod 
    def mask_session_id(cls, session_id: str) -> str:
        """Partially mask session ID for privacy"""
        if not session_id or len(session_id) < 8:
            return session_id
        
        # Show first 4 and last 4 characters, mask the middle
        return f"{session_id[:4]}{'*' * (len(session_id) - 8)}{session_id[-4:]}"


class CSVSanitizer:
    """Handles CSV injection protection"""
    
    INJECTION_PREFIXES = ['=', '+', '-', '@', '\t', '\r']
    
    @classmethod
    def sanitize_csv_cell(cls, value: Any) -> str:
        """Sanitize a single CSV cell to prevent injection attacks"""
        if value is None:
            return ""
        
        str_value = str(value)
        
        # Check for injection patterns
        if str_value and str_value[0] in cls.INJECTION_PREFIXES:
            # Prefix with single quote to neutralize formula injection
            return f"'{str_value}"
        
        # Escape existing quotes
        if '"' in str_value:
            str_value = str_value.replace('"', '""')
        
        # Quote the cell if it contains commas, newlines, or quotes
        if ',' in str_value or '\n' in str_value or '"' in str_value:
            return f'"{str_value}"'
        
        return str_value
    
    @classmethod
    def sanitize_csv_row(cls, row: List[Any]) -> List[str]:
        """Sanitize an entire CSV row"""
        return [cls.sanitize_csv_cell(cell) for cell in row]


def get_sanitized_audit_data(audit_log):
    """
    Get sanitized audit data for display
    """
    sanitizer = AuditDataSanitizer()
    
    return {
        'old_values': sanitizer.sanitize_json_data(audit_log.old_values),
        'new_values': sanitizer.sanitize_json_data(audit_log.new_values),
        'error_message': sanitizer.sanitize_error_message(audit_log.error_message or ""),
        'masked_ip': sanitizer.mask_ip_address(audit_log.ip_address or ""),
        'masked_session': sanitizer.mask_session_id(audit_log.session_id or "")
    }


# JWT Authentication Utilities
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', os.environ.get('SESSION_SECRET', 'fallback-secret-key'))
JWT_ALGORITHM = 'HS256'
DEFAULT_EXPIRY_MINUTES = 15

def create_access_token(user_id, role, expires_in_minutes=DEFAULT_EXPIRY_MINUTES):
    """Create a JWT access token for user authentication"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(minutes=expires_in_minutes),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        'access_token': token,
        'expires_in': expires_in_minutes * 60,  # Convert to seconds
        'token_type': 'Bearer'
    }

def verify_jwt(token):
    """Verify and decode JWT token, return user or None"""
    try:
        from models import User  # Import here to avoid circular imports
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        
        if not user_id:
            return None
            
        user = User.query.get(user_id)
        return user
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def jwt_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'success': False, 'message': 'Authorization header required'}), 401
            
        try:
            # Expect format: "Bearer <token>"
            token_type, token = auth_header.split(' ', 1)
            if token_type.lower() != 'bearer':
                return jsonify({'success': False, 'message': 'Invalid token format'}), 401
                
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid Authorization header format'}), 401
        
        # Verify token and get user
        user = verify_jwt(token)
        if not user:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401
            
        # Store user in Flask's g object for access in route handlers
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def role_required(required_role):
    """Decorator to check user role (use after jwt_required)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
                
            if g.current_user.role.value != required_role:
                return jsonify({'success': False, 'message': 'Insufficient permissions'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def extract_request_info():
    """Extract IP address and user agent for security logging"""
    return {
        'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
        'user_agent': request.headers.get('User-Agent', '')[:500]  # Limit length
    }