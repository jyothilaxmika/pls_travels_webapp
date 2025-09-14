"""
Production configuration validation for OTP system
Ensures all required environment variables are properly configured
"""
import os
import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Raised when critical configuration is missing or invalid"""
    pass

def validate_twilio_config() -> Tuple[bool, List[str]]:
    """
    Validate Twilio configuration for OTP functionality.
    
    Returns:
        tuple: (is_valid: bool, issues: List[str])
    """
    issues = []
    
    # Required Twilio environment variables
    required_vars = {
        'TWILIO_ACCOUNT_SID': 'Twilio Account SID',
        'TWILIO_AUTH_TOKEN': 'Twilio Auth Token', 
        'TWILIO_PHONE_NUMBER': 'Twilio Phone Number'
    }
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            issues.append(f"Missing {description} ({var_name})")
        elif len(value.strip()) == 0:
            issues.append(f"Empty {description} ({var_name})")
    
    # Validate Twilio phone number format if present
    phone_number = os.getenv('TWILIO_PHONE_NUMBER', '').strip()
    if phone_number and not phone_number.startswith('+'):
        issues.append("TWILIO_PHONE_NUMBER must start with '+' (e.g., +1234567890)")
    
    return len(issues) == 0, issues

def validate_flask_config() -> Tuple[bool, List[str]]:
    """
    Validate Flask configuration for production.
    
    Returns:
        tuple: (is_valid: bool, issues: List[str])
    """
    issues = []
    
    # Check session secret
    session_secret = os.getenv('SESSION_SECRET')
    if not session_secret:
        issues.append("Missing SESSION_SECRET environment variable")
    elif len(session_secret) < 32:
        issues.append("SESSION_SECRET should be at least 32 characters for security")
    
    # Check DEBUG mode in production
    debug_mode = os.getenv('DEBUG', 'False').lower()
    if debug_mode in ('true', '1', 'yes'):
        issues.append("DEBUG mode is enabled - should be disabled in production")
    
    return len(issues) == 0, issues

def check_production_readiness() -> Dict[str, Any]:
    """
    Comprehensive check of production readiness for OTP system.
    
    Returns:
        dict: Status information including issues and recommendations
    """
    debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    # Validate configurations
    twilio_valid, twilio_issues = validate_twilio_config()
    flask_valid, flask_issues = validate_flask_config()
    
    all_issues = twilio_issues + flask_issues
    is_production_ready = bool(len(all_issues) == 0 and not debug_mode)
    
    # Check if OTP should be enabled
    otp_enabled = True
    if not twilio_valid and not debug_mode:
        otp_enabled = False
        all_issues.append("OTP login disabled: Twilio not configured and DEBUG mode off")
    
    result = {
        'production_ready': is_production_ready,
        'otp_enabled': otp_enabled,
        'debug_mode': debug_mode,
        'twilio_configured': twilio_valid,
        'issues': all_issues,
        'recommendations': []
    }
    
    # Add recommendations
    if debug_mode:
        result['recommendations'].append("Disable DEBUG mode for production deployment")
    
    if not twilio_valid:
        result['recommendations'].append("Configure Twilio credentials for SMS functionality")
    
    if not is_production_ready:
        result['recommendations'].append("Address configuration issues before deploying to production")
    
    # Log the status
    if is_production_ready:
        logger.info("OTP_CONFIG: Production readiness check PASSED")
    else:
        logger.warning(f"OTP_CONFIG: Production readiness check FAILED - Issues: {len(all_issues)}")
        for issue in all_issues:
            logger.warning(f"OTP_CONFIG: Issue - {issue}")
    
    return result

def get_otp_config_status() -> str:
    """
    Get a human-readable status of OTP configuration.
    
    Returns:
        str: Configuration status message
    """
    status = check_production_readiness()
    
    if status['production_ready']:
        return "✅ OTP system is production-ready with Twilio SMS"
    elif status['otp_enabled'] and status['debug_mode']:
        return "⚠️ OTP system enabled in DEBUG mode (development only)"
    elif not status['otp_enabled']:
        return "❌ OTP system disabled due to missing Twilio configuration"
    else:
        return f"❌ OTP system has {len(status['issues'])} configuration issues"