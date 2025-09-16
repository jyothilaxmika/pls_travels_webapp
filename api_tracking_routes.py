"""
Mobile API routes for driver location tracking
JWT-protected endpoints for batch GPS data ingestion and tracking configuration
"""

from flask import Blueprint, request, jsonify, current_app, session
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
import json
import logging
import time
import hashlib
from functools import wraps
from collections import defaultdict
from threading import Lock

from app import db
from models import Driver, Duty, TrackingSession, DriverLocation, DutyStatus
from timezone_utils import get_ist_time_naive
from utils.privacy_controls import LocationPrivacyValidator, PrivacySettings

api_tracking_bp = Blueprint('api_tracking', __name__, url_prefix='/api/v1/tracking')

logger = logging.getLogger(__name__)

# Rate limiting and deduplication system
class TrackingRateLimiter:
    """Production-grade rate limiter for location tracking API"""
    
    def __init__(self):
        self._lock = Lock()
        
        # Rate limiting per driver (driver_id -> {last_request: timestamp, request_count: int})
        self._driver_requests = defaultdict(dict)
        self._max_requests_per_minute = 10  # Max 10 batch requests per minute per driver
        self._max_locations_per_hour = 3600  # Max 3600 locations per hour per driver (1 per second)
        
        # Deduplication cache (scoped key -> timestamp) with size limits
        self._processed_events = {}
        self._dedup_cache_duration = 86400  # Keep cache for 24 hours
        self._max_dedup_cache_size = 100000  # Prevent memory DoS
        
        # IP-based rate limiting for additional security
        self._ip_requests = defaultdict(dict)
        self._max_ip_requests_per_minute = 50  # Max requests per IP per minute
        
        # Last cleanup time
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        
    def can_submit_batch(self, driver_id, client_ip, batch_size):
        """Check if driver can submit a location batch"""
        with self._lock:
            self._cleanup_expired_entries()
            
            current_time = time.time()
            
            # Check driver rate limits
            driver_data = self._driver_requests[driver_id]
            
            # Reset counters if it's a new minute
            if 'last_minute' not in driver_data or current_time - driver_data['last_minute'] >= 60:
                driver_data['requests_this_minute'] = 0
                driver_data['last_minute'] = current_time
            
            # Reset hourly counters if it's a new hour (separate from minute reset)
            if 'last_hour' not in driver_data or current_time - driver_data['last_hour'] >= 3600:
                driver_data['locations_this_hour'] = 0
                driver_data['last_hour'] = current_time
            
            # Check per-minute request limit
            if driver_data.get('requests_this_minute', 0) >= self._max_requests_per_minute:
                return False, "Too many requests per minute", 60
                
            # Check hourly location limit
            if driver_data.get('locations_this_hour', 0) + batch_size > self._max_locations_per_hour:
                return False, "Location submission rate exceeded", 3600
            
            # Check IP rate limits
            ip_data = self._ip_requests[client_ip]
            if 'last_minute' not in ip_data or current_time - ip_data['last_minute'] >= 60:
                ip_data['requests_this_minute'] = 0
                ip_data['last_minute'] = current_time
                
            if ip_data.get('requests_this_minute', 0) >= self._max_ip_requests_per_minute:
                return False, "IP rate limit exceeded", 60
            
            # Update counters
            driver_data['requests_this_minute'] = driver_data.get('requests_this_minute', 0) + 1
            driver_data['locations_this_hour'] = driver_data.get('locations_this_hour', 0) + batch_size
            ip_data['requests_this_minute'] = ip_data.get('requests_this_minute', 0) + 1
            
            return True, "OK", 0
    
    def is_duplicate_event(self, driver_id, client_event_id):
        """Check if event ID has already been processed (scoped by driver)"""
        with self._lock:
            self._cleanup_expired_entries()
            
            # Scope dedup key by driver to prevent cross-driver collisions
            scoped_key = f"{driver_id}:{client_event_id}"
            
            if scoped_key in self._processed_events:
                return True
                
            # Check cache size limit to prevent memory DoS
            if len(self._processed_events) >= self._max_dedup_cache_size:
                # Emergency cleanup - remove oldest 10%
                sorted_items = sorted(self._processed_events.items(), key=lambda x: x[1])
                for key, _ in sorted_items[:len(sorted_items) // 10]:
                    del self._processed_events[key]
                
            # Mark as processed
            self._processed_events[scoped_key] = time.time()
            return False
    
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
            
        # Clean deduplication cache
        expired_events = []
        for event_id, timestamp in self._processed_events.items():
            if current_time - timestamp > self._dedup_cache_duration:
                expired_events.append(event_id)
                
        for event_id in expired_events:
            del self._processed_events[event_id]
        
        self._last_cleanup = current_time

# Global rate limiter instance
tracking_rate_limiter = TrackingRateLimiter()

def mobile_auth_required(f):
    """Custom authentication decorator for mobile API endpoints"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        
        # Get driver profile from user ID  
        from models import DriverStatus, User
        driver = Driver.query.join(User, Driver.user_id == User.id).filter(
            User.id == current_user_id,
            Driver.status.in_([DriverStatus.ACTIVE, DriverStatus.PENDING])
        ).first()
        
        if not driver:
            return jsonify({
                'success': False,
                'error': 'Driver profile not found or inactive',
                'code': 'DRIVER_NOT_FOUND'
            }), 404
            
        # Store driver in request context using g
        from flask import g
        g.current_driver = driver
        return f(*args, **kwargs)
    
    return decorated_function

@api_tracking_bp.route('/auth/driver-login', methods=['POST'])
def driver_mobile_login():
    """
    Authenticate driver for mobile tracking
    Expected payload: {"phone": "1234567890", "otp": "123456"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON payload',
                'code': 'INVALID_PAYLOAD'
            }), 400
            
        phone = data.get('phone')
        otp = data.get('otp')
        
        if not phone or not otp:
            return jsonify({
                'success': False,
                'error': 'Phone number and OTP are required',
                'code': 'MISSING_CREDENTIALS'
            }), 400
        
        # Implement OTP verification using existing system
        from utils.twilio_otp import OTPSession, format_phone_number
        from utils.rate_limiter import otp_rate_limiter
        from models import DriverStatus, User, UserStatus
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Get client IP for OTP rate limiting  
        client_ip = request.remote_addr or '127.0.0.1'
        
        # Import session at the top if not already imported
        from flask import session as flask_session
        
        # Apply OTP verification rate limiting
        can_verify, reason, retry_after = otp_rate_limiter.can_verify_otp(
            formatted_phone, client_ip, flask_session.get('temp_session_id', 'unknown')
        )
        
        if not can_verify:
            logger.warning(f"OTP verification rate limited for {formatted_phone[-4:].rjust(4, '*')}: {reason}")
            return jsonify({
                'success': False,
                'error': 'RATE_LIMITED',
                'code': 'TOO_MANY_ATTEMPTS',
                'message': reason,
                'retry_after': retry_after
            }), 429
        
        # Verify OTP using the existing session-based system
        otp_result = OTPSession.verify_otp(flask_session, otp)
        
        if not otp_result['success']:
            return jsonify({
                'success': False,
                'error': 'OTP_VERIFICATION_FAILED',
                'code': 'INVALID_OTP',
                'message': otp_result['message']
            }), 400
        
        # Ensure the phone from OTP matches the requested phone
        if otp_result['phone'] != formatted_phone:
            return jsonify({
                'success': False,
                'error': 'PHONE_MISMATCH',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # Find driver by phone
        driver = Driver.query.join(User, Driver.user_id == User.id).filter(
            User.phone == formatted_phone,
            User.status == UserStatus.ACTIVE,
            Driver.status.in_([DriverStatus.ACTIVE, DriverStatus.PENDING])
        ).first()
        
        if not driver:
            return jsonify({
                'success': False,
                'error': 'Driver not found or inactive',
                'code': 'DRIVER_NOT_FOUND'
            }), 404
        
        # Create JWT token
        access_token = create_access_token(
            identity=driver.user.id,
            expires_delta=timedelta(days=30)  # Long-lived for mobile
        )
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'driver': {
                'id': driver.id,
                'name': driver.full_name,
                'phone': driver.phone,
                'branch': driver.branch.name if driver.branch else None
            },
            'expires_in': 30 * 24 * 3600  # 30 days in seconds
        })
        
    except Exception as e:
        logger.error(f"Driver mobile login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed',
            'code': 'AUTH_ERROR'
        }), 500

@api_tracking_bp.route('/locations/batch', methods=['POST'])
@mobile_auth_required
def submit_location_batch():
    """
    Submit batch of GPS location points
    Expected payload: {
        "duty_id": 123,
        "session_id": "uuid",
        "locations": [
            {
                "client_event_id": "unique_id",
                "latitude": 12.34567,
                "longitude": 98.76543,
                "accuracy": 5.0,
                "altitude": 100.0,
                "speed": 15.5,
                "bearing": 180.0,
                "captured_at": "2024-01-01T12:00:00Z",
                "battery_level": 85,
                "network_type": "cellular",
                "signal_strength": -70
            }
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON payload',
                'code': 'INVALID_PAYLOAD'
            }), 400
        
        from flask import g
        driver = g.current_driver
        duty_id = data.get('duty_id')
        locations = data.get('locations', [])
        
        # Get client IP for rate limiting (secure with ProxyFix)
        # ProxyFix ensures request.remote_addr is the real client IP
        client_ip = request.remote_addr or '127.0.0.1'
        
        # Apply rate limiting
        can_submit, reason, retry_after = tracking_rate_limiter.can_submit_batch(
            driver.id, client_ip, len(locations)
        )
        
        if not can_submit:
            logger.warning(f"Rate limit exceeded for driver {driver.id}: {reason}")
            return jsonify({
                'success': False,
                'error': 'RATE_LIMITED',
                'code': 'RATE_LIMITED',
                'message': reason,
                'retry_after': retry_after
            }), 429
        
        if not duty_id or not locations:
            return jsonify({
                'success': False,
                'error': 'duty_id and locations are required',
                'code': 'MISSING_DATA'
            }), 400
        
        # Enforce maximum batch size for security and performance
        MAX_BATCH_SIZE = 500
        if len(locations) > MAX_BATCH_SIZE:
            return jsonify({
                'success': False,
                'error': f'Batch size too large. Maximum {MAX_BATCH_SIZE} locations allowed',
                'code': 'BATCH_TOO_LARGE'
            }), 400
        
        # Verify duty belongs to this driver and is active
        duty = Duty.query.filter_by(
            id=duty_id,
            driver_id=driver.id,
            status=DutyStatus.ACTIVE
        ).first()
        
        if not duty:
            return jsonify({
                'success': False,
                'error': 'Active duty not found for this driver',
                'code': 'DUTY_NOT_FOUND'
            }), 404
        
        # Check privacy settings - ensure tracking is allowed
        if not PrivacySettings.should_track_location(driver.id, duty.status.value):
            logger.info(f"Location tracking blocked by privacy settings for driver {driver.id}")
            return jsonify({
                'success': False,
                'error': 'Location tracking not permitted by privacy settings',
                'code': 'PRIVACY_RESTRICTED'
            }), 403
        
        # Get or create tracking session
        session = TrackingSession.query.filter_by(
            duty_id=duty_id,
            driver_id=driver.id,
            is_active=True
        ).first()
        
        if not session:
            session = TrackingSession(
                duty_id=duty_id,
                driver_id=driver.id,
                device_info=json.dumps(data.get('device_info', {})),
                app_version=data.get('app_version', 'unknown')
            )
            db.session.add(session)
            db.session.flush()  # Get the session ID
        
        processed_count = 0
        duplicate_count = 0
        error_count = 0
        errors = []
        
        for location_data in locations:
            try:
                # Validate required fields
                if not all(key in location_data for key in ['latitude', 'longitude', 'captured_at']):
                    error_count += 1
                    errors.append(f"Missing required fields in location data")
                    continue
                
                # Privacy and accuracy validation
                is_valid, validation_reason = LocationPrivacyValidator.validate_location_accuracy(location_data)
                if not is_valid:
                    error_count += 1
                    errors.append(f"Location validation failed: {validation_reason}")
                    continue
                
                # Check for duplicates using client_event_id with fast cache lookup
                client_event_id = location_data.get('client_event_id')
                if client_event_id:
                    # First check our fast in-memory cache (scoped by driver)
                    if tracking_rate_limiter.is_duplicate_event(driver.id, client_event_id):
                        duplicate_count += 1
                        continue
                    
                    # Double-check database for safety (in case cache was cleared)
                    existing = DriverLocation.query.filter_by(
                        driver_id=driver.id,
                        client_event_id=client_event_id
                    ).first()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                
                # Parse captured_at timestamp
                try:
                    captured_at = datetime.fromisoformat(
                        location_data['captured_at'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    error_count += 1
                    errors.append(f"Invalid captured_at timestamp")
                    continue
                
                # Check location frequency to prevent spam
                if not LocationPrivacyValidator.validate_location_frequency(driver.id, captured_at):
                    duplicate_count += 1  # Count as duplicate since it's too frequent
                    continue
                
                # Validate coordinate ranges (will be caught by DB constraints too)
                lat = float(location_data['latitude'])
                lon = float(location_data['longitude'])
                
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    error_count += 1
                    errors.append(f"Invalid coordinates: {lat}, {lon}")
                    continue
                
                # Create location record
                location = DriverLocation(
                    driver_id=driver.id,
                    duty_id=duty_id,
                    tracking_session_id=session.id,
                    latitude=lat,
                    longitude=lon,
                    altitude=location_data.get('altitude'),
                    accuracy=location_data.get('accuracy'),
                    speed=location_data.get('speed'),
                    bearing=location_data.get('bearing'),
                    captured_at=captured_at,
                    source='mobile',
                    client_event_id=client_event_id,
                    battery_level=location_data.get('battery_level'),
                    network_type=location_data.get('network_type'),
                    signal_strength=location_data.get('signal_strength'),
                    is_mocked=location_data.get('is_mocked', False)
                )
                
                db.session.add(location)
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing location: {str(e)}")
                logger.error(f"Location processing error: {str(e)}")
        
        # Update session metadata
        session.total_points += processed_count
        session.updated_at = get_ist_time_naive()
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session.uuid,
            'processed': processed_count,
            'duplicates': duplicate_count,
            'errors': error_count,
            'error_details': errors[:5] if errors else None,  # Limit error details
            'next_upload_interval': session.sampling_interval
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Batch location submission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process location batch',
            'code': 'PROCESSING_ERROR'
        }), 500

@api_tracking_bp.route('/config/<int:duty_id>', methods=['GET'])
@mobile_auth_required
def get_tracking_config(duty_id):
    """
    Get tracking configuration for a specific duty
    Returns sampling intervals, accuracy thresholds, etc.
    """
    try:
        from flask import g
        driver = g.current_driver
        
        # Verify duty belongs to driver
        duty = Duty.query.filter_by(
            id=duty_id,
            driver_id=driver.id
        ).first()
        
        if not duty:
            return jsonify({
                'success': False,
                'error': 'Duty not found',
                'code': 'DUTY_NOT_FOUND'
            }), 404
        
        # Get active tracking session if exists
        session = TrackingSession.query.filter_by(
            duty_id=duty_id,
            driver_id=driver.id,
            is_active=True
        ).first()
        
        config = {
            'duty_id': duty_id,
            'sampling_interval': 30,  # Default 30 seconds
            'min_distance': 10.0,     # Default 10 meters
            'accuracy_threshold': 50.0,  # Default 50 meters
            'batch_size': 20,         # Send locations in batches of 20
            'upload_interval': 60,    # Upload every 60 seconds
            'low_battery_mode': {
                'enabled_below': 20,  # Enable when battery < 20%
                'sampling_interval': 120,  # 2 minutes in low battery
                'min_distance': 50.0
            }
        }
        
        if session:
            config.update({
                'session_id': session.uuid,
                'sampling_interval': session.sampling_interval,
                'min_distance': session.min_distance,
                'accuracy_threshold': session.accuracy_threshold
            })
        
        return jsonify({
            'success': True,
            'config': config,
            'duty_status': duty.status.value,
            'tracking_enabled': duty.status == DutyStatus.ACTIVE
        })
        
    except Exception as e:
        logger.error(f"Get tracking config error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get tracking configuration',
            'code': 'CONFIG_ERROR'
        }), 500

@api_tracking_bp.route('/session/<int:duty_id>/start', methods=['POST'])
@mobile_auth_required
def start_tracking_session(duty_id):
    """
    Start a new tracking session for a duty
    Called when duty starts or app reconnects
    """
    try:
        from flask import g
        driver = g.current_driver
        data = request.get_json() or {}
        
        # Verify duty belongs to driver and is active
        duty = Duty.query.filter_by(
            id=duty_id,
            driver_id=driver.id,
            status=DutyStatus.ACTIVE
        ).first()
        
        if not duty:
            return jsonify({
                'success': False,
                'error': 'Active duty not found',
                'code': 'DUTY_NOT_FOUND'
            }), 404
        
        # End any existing active sessions for this duty
        existing_sessions = TrackingSession.query.filter_by(
            duty_id=duty_id,
            driver_id=driver.id,
            is_active=True
        ).all()
        
        for session in existing_sessions:
            session.is_active = False
            session.session_end = get_ist_time_naive()
        
        # Create new tracking session
        new_session = TrackingSession(
            duty_id=duty_id,
            driver_id=driver.id,
            device_info=json.dumps(data.get('device_info', {})),
            app_version=data.get('app_version', 'unknown')
        )
        
        db.session.add(new_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': new_session.uuid,
            'session_start': new_session.session_start.isoformat(),
            'config': {
                'sampling_interval': new_session.sampling_interval,
                'min_distance': new_session.min_distance,
                'accuracy_threshold': new_session.accuracy_threshold
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Start tracking session error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to start tracking session',
            'code': 'SESSION_ERROR'
        }), 500

@api_tracking_bp.route('/session/<int:duty_id>/stop', methods=['POST'])
@mobile_auth_required  
def stop_tracking_session(duty_id):
    """
    Stop tracking session for a duty
    Called when duty ends or tracking is manually stopped
    """
    try:
        from flask import g
        driver = g.current_driver
        
        # Find active session for this duty
        session = TrackingSession.query.filter_by(
            duty_id=duty_id,
            driver_id=driver.id,
            is_active=True
        ).first()
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'No active tracking session found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        # End the session
        session.is_active = False
        session.session_end = get_ist_time_naive()
        session.duration = int((session.session_end - session.session_start).total_seconds())
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session.uuid,
            'duration': session.duration,
            'total_points': session.total_points,
            'session_end': session.session_end.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Stop tracking session error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to stop tracking session',
            'code': 'SESSION_ERROR'
        }), 500

@api_tracking_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check for mobile apps"""
    return jsonify({
        'success': True,
        'service': 'location_tracking_api',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers
@api_tracking_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'code': 'BAD_REQUEST'
    }), 400

@api_tracking_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'error': 'Unauthorized - valid JWT token required',
        'code': 'UNAUTHORIZED'
    }), 401

@api_tracking_bp.errorhandler(422)
def unprocessable_entity(error):
    return jsonify({
        'success': False,
        'error': 'JWT token is invalid or expired',
        'code': 'INVALID_TOKEN'
    }), 422

@api_tracking_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500