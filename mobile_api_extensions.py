"""
Additional Mobile API Endpoints for Production Android App
These endpoints extend mobile_api.py with production-ready features
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime
import uuid
import os
from werkzeug.utils import secure_filename

from models import User, Duty, Vehicle, DutyStatus, db, AdvancePaymentRequest
from app import csrf
from whatsapp_utils import send_advance_payment_request

logger = logging.getLogger(__name__)

# Create mobile extensions blueprint
mobile_extensions_bp = Blueprint('mobile_extensions', __name__)

def get_current_mobile_user():
    """Get current user from JWT token"""
    current_user_identity = get_jwt_identity()
    user = User.query.filter_by(username=current_user_identity).first()
    return user

# === PHOTO UPLOAD ENDPOINTS ===

@mobile_extensions_bp.route('/api/v1/driver/upload-photo', methods=['POST'])
@jwt_required()
@csrf.exempt
def upload_duty_photo():
    """Upload photo for duty (start/end duty photos)"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        # Check if photo file is present
        if 'photo' not in request.files:
            return jsonify({
                'success': False,
                'error': 'NO_PHOTO',
                'message': 'No photo file provided'
            }), 400
        
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({
                'success': False,
                'error': 'NO_PHOTO',
                'message': 'No photo file selected'
            }), 400
        
        # Validate file type and size
        allowed_extensions = {'jpg', 'jpeg', 'png'}
        file_ext = photo.filename.rsplit('.', 1)[1].lower() if '.' in photo.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': 'INVALID_FILE_TYPE',
                'message': 'Only JPG, JPEG, PNG files allowed'
            }), 400
        
        # Generate secure filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"duty_{user.id}_{timestamp}_{str(uuid.uuid4())[:8]}.{file_ext}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads', 'duty_photos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, filename)
        photo.save(file_path)
        
        # Return the file URL
        file_url = f"/static/uploads/duty_photos/{filename}"
        
        return jsonify({
            'success': True,
            'file_url': file_url,
            'filename': filename,
            'message': 'Photo uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in upload_duty_photo: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'UPLOAD_ERROR',
            'message': 'Failed to upload photo'
        }), 500

# === LOCATION TRACKING ENDPOINTS ===

@mobile_extensions_bp.route('/api/v1/driver/location/update', methods=['POST'])
@jwt_required()
@csrf.exempt
def update_driver_location():
    """Update driver's current location for real-time tracking"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'NO_DATA',
                'message': 'No location data provided'
            }), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        speed = data.get('speed', 0)
        heading = data.get('heading', 0)
        
        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'error': 'INVALID_COORDINATES',
                'message': 'Valid latitude and longitude required'
            }), 400
        
        # For now, update user's last known location (you may want to create a separate location_tracking table)
        user.last_latitude = float(latitude)
        user.last_longitude = float(longitude)
        user.last_location_update = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Location updated successfully',
            'timestamp': user.last_location_update.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in update_driver_location: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'LOCATION_ERROR',
            'message': 'Failed to update location'
        }), 500

# === FCM PUSH NOTIFICATIONS ===

@mobile_extensions_bp.route('/api/v1/driver/fcm-token', methods=['POST'])
@jwt_required()
@csrf.exempt
def register_fcm_token():
    """Register FCM token for push notifications"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        data = request.get_json()
        if not data or not data.get('fcm_token'):
            return jsonify({
                'success': False,
                'error': 'NO_TOKEN',
                'message': 'FCM token required'
            }), 400
        
        # Update user's FCM token
        user.fcm_token = data['fcm_token']
        user.fcm_token_updated = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'FCM token registered successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in register_fcm_token: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'TOKEN_ERROR',
            'message': 'Failed to register FCM token'
        }), 500

# === ADVANCE PAYMENT REQUESTS ===

@mobile_extensions_bp.route('/api/v1/driver/advance-payment', methods=['POST'])
@jwt_required()
@csrf.exempt
def request_advance_payment():
    """Request advance payment via WhatsApp to admins"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        # Check if driver has an active duty
        active_duty = Duty.query.filter_by(
            driver_id=user.id,
            status=DutyStatus.ACTIVE
        ).first()
        
        if not active_duty:
            return jsonify({
                'success': False,
                'error': 'NO_ACTIVE_DUTY',
                'message': 'No active duty found. Start duty first.'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'NO_DATA',
                'message': 'Request data required'
            }), 400
        
        amount = data.get('amount')
        purpose = data.get('purpose', 'fuel')
        notes = data.get('notes', '')
        location_lat = data.get('latitude')
        location_lng = data.get('longitude')
        
        if not amount or amount <= 0:
            return jsonify({
                'success': False,
                'error': 'INVALID_AMOUNT',
                'message': 'Valid amount required'
            }), 400
        
        # Send advance payment request via WhatsApp
        result = send_advance_payment_request(
            duty_id=active_duty.id,
            driver_id=user.id,
            amount=float(amount),
            purpose=purpose,
            notes=notes,
            location_lat=location_lat,
            location_lng=location_lng
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'request_id': result['request_id'],
                'message': 'Advance payment request sent successfully',
                'sent_to_admins': result.get('message_sent_to', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'REQUEST_FAILED',
                'message': result.get('error', 'Failed to send advance payment request')
            }), 500
        
    except Exception as e:
        logger.error(f"Error in request_advance_payment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'REQUEST_ERROR',
            'message': 'Failed to process advance payment request'
        }), 500

@mobile_extensions_bp.route('/api/v1/driver/advance-payments', methods=['GET'])
@jwt_required()
@csrf.exempt
def get_advance_payments():
    """Get driver's advance payment requests history"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')  # pending, approved, rejected
        
        # Build query
        query = AdvancePaymentRequest.query.filter_by(driver_id=user.id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Paginate results
        paginated = query.order_by(AdvancePaymentRequest.created_at.desc()).paginate(
            page=page, per_page=per_page
        )
        
        requests_data = []
        for req in paginated.items:
            request_data = {
                'id': req.id,
                'amount_requested': req.amount_requested,
                'amount_approved': req.approved_amount,
                'purpose': req.purpose,
                'notes': req.notes,
                'status': req.status,
                'created_at': req.created_at.isoformat(),
                'responded_at': req.responded_at.isoformat() if req.responded_at else None,
                'response_notes': req.response_notes,
                'duty_id': req.duty_id
            }
            requests_data.append(request_data)
        
        return jsonify({
            'success': True,
            'requests': requests_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_advance_payments: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'FETCH_ERROR',
            'message': 'Failed to fetch advance payment requests'
        }), 500

# === HEALTH CHECK ENDPOINT ===

@mobile_extensions_bp.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint for Android app"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'version': 'v1.0',
        'timestamp': datetime.now().isoformat()
    })