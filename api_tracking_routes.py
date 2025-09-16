"""
Mobile API routes for driver location tracking
JWT-protected endpoints for batch GPS data ingestion and tracking configuration
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
import json
import logging
from functools import wraps

from app import db
from models import Driver, Duty, TrackingSession, DriverLocation, DutyStatus
from timezone_utils import get_ist_time_naive

api_tracking_bp = Blueprint('api_tracking', __name__, url_prefix='/api/v1/tracking')

logger = logging.getLogger(__name__)

def mobile_auth_required(f):
    """Custom authentication decorator for mobile API endpoints"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        
        # Get driver profile from user ID  
        from models import DriverStatus
        driver = Driver.query.join(Driver.user).filter(
            Driver.user.has(id=current_user_id),
            Driver.status.in_([DriverStatus.ACTIVE, DriverStatus.PENDING])
        ).first()
        
        if not driver:
            return jsonify({
                'success': False,
                'error': 'Driver profile not found or inactive',
                'code': 'DRIVER_NOT_FOUND'
            }), 404
            
        # Attach driver to request context
        request.current_driver = driver
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
        
        # TODO: Implement OTP verification logic here
        # For now, create a basic JWT token for development
        
        # Find driver by phone
        from models import DriverStatus
        driver = Driver.query.filter_by(phone=phone).first()
        if not driver or driver.status not in [DriverStatus.ACTIVE, DriverStatus.PENDING]:
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
        
        driver = request.current_driver
        duty_id = data.get('duty_id')
        locations = data.get('locations', [])
        
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
                
                # Check for duplicates using client_event_id
                client_event_id = location_data.get('client_event_id')
                if client_event_id:
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
        driver = request.current_driver
        
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
        driver = request.current_driver
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
        driver = request.current_driver
        
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