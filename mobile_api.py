"""
Mobile API Module
Driver-specific endpoints for Android app
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import logging
from datetime import datetime, timezone
import uuid
import os
from werkzeug.utils import secure_filename

from models import User, Duty, Vehicle, DutyStatus, db
from app import csrf

logger = logging.getLogger(__name__)

# Create mobile API blueprint
mobile_api_bp = Blueprint('mobile_api', __name__)

def get_current_mobile_user():
    """Get current user from JWT token"""
    current_user_identity = get_jwt_identity()
    jwt_claims = get_jwt()
    
    user = User.query.filter_by(username=current_user_identity).first()
    if not user:
        return None
    
    return user

@mobile_api_bp.route('/api/v1/driver/profile', methods=['GET'])
@jwt_required()
@csrf.exempt
def get_driver_profile():
    """Get driver profile information"""
    try:
        user = get_current_mobile_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'USER_NOT_FOUND',
                'message': 'User not found'
            }), 404
        
        # Check if user is a driver
        if user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        profile_data = {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'phone': user.phone,
            'email': user.email,
            'branch': {
                'id': user.branch.id if user.branch else None,
                'name': user.branch.name if user.branch else None
            },
            'status': user.status.name,
            'license_number': getattr(user, 'license_number', None),
            'aadhar_number': getattr(user, 'aadhar_number', None),
            'address': getattr(user, 'address', None),
            'profile_photo_url': getattr(user, 'profile_photo_url', None)
        }
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_driver_profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_api_bp.route('/api/v1/driver/duties', methods=['GET'])
@jwt_required()
@csrf.exempt
def get_driver_duties():
    """Get driver's recent duties"""
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
        status = request.args.get('status')  # active, completed, pending
        
        # Build query
        query = Duty.query.filter_by(driver_id=user.id)
        
        if status:
            if status == 'active':
                query = query.filter(Duty.status == DutyStatus.ACTIVE)
            elif status == 'completed':
                query = query.filter(Duty.status == DutyStatus.COMPLETED)
            elif status == 'pending':
                query = query.filter(Duty.status.in_([DutyStatus.ACTIVE, DutyStatus.COMPLETED]))
        
        # Order by most recent first
        duties = query.order_by(Duty.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        duties_data = []
        for duty in duties.items:
            duty_data = {
                'id': duty.id,
                'status': duty.status.name,
                'start_time': duty.actual_start.isoformat() if duty.actual_start else None,
                'end_time': duty.actual_end.isoformat() if duty.actual_end else None,
                'vehicle': {
                    'id': duty.vehicle_id,
                    'registration': duty.vehicle.registration_number if duty.vehicle else None,
                    'model': duty.vehicle.model if duty.vehicle else None
                } if duty.vehicle_id else None,
                'route': duty.notes,
                'total_earnings': float(duty.cash_collection or 0),
                'distance_km': float(duty.total_distance or 0),
                'created_at': duty.created_at.isoformat() if duty.created_at else None
            }
            duties_data.append(duty_data)
        
        return jsonify({
            'success': True,
            'duties': duties_data,
            'pagination': {
                'page': duties.page,
                'pages': duties.pages,
                'per_page': duties.per_page,
                'total': duties.total,
                'has_next': duties.has_next,
                'has_prev': duties.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_driver_duties: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_api_bp.route('/api/v1/driver/duty/start', methods=['POST'])
@jwt_required()
@csrf.exempt
def start_duty():
    """Start a new duty"""
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
                'error': 'INVALID_REQUEST',
                'message': 'Request body is required'
            }), 400
        
        vehicle_id = data.get('vehicle_id')
        duty_type = data.get('duty_type', 'REGULAR')
        route = data.get('route', '')
        start_odometer = data.get('start_odometer', 0)
        start_location = data.get('start_location', {})
        
        if not vehicle_id:
            return jsonify({
                'success': False,
                'error': 'VEHICLE_REQUIRED',
                'message': 'Vehicle ID is required'
            }), 400
        
        # Check if vehicle exists and is available
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({
                'success': False,
                'error': 'VEHICLE_NOT_FOUND',
                'message': 'Vehicle not found'
            }), 404
        
        # Check if driver already has an active duty
        active_duty = Duty.query.filter_by(
            driver_id=user.id,
            status=DutyStatus.ACTIVE
        ).first()
        
        if active_duty:
            return jsonify({
                'success': False,
                'error': 'DUTY_ALREADY_ACTIVE',
                'message': 'You already have an active duty. Please end it first.',
                'active_duty_id': active_duty.id
            }), 409
        
        # Create new duty
        duty = Duty()
        duty.driver_id = user.id
        duty.vehicle_id = vehicle_id
        duty.branch_id = user.branch_id
        duty.status = DutyStatus.ACTIVE
        duty.actual_start = datetime.now(timezone.utc)
        duty.start_odometer = start_odometer
        duty.notes = route
        
        # Store location data if provided
        if start_location:
            duty.start_location_lat = start_location.get('latitude')
            duty.start_location_lng = start_location.get('longitude')
            if start_location.get('address'):
                duty.notes += f" | Start: {start_location.get('address')}"
        
        db.session.add(duty)
        db.session.commit()
        
        logger.info(f"DUTY_STARTED: Driver: {user.username} Vehicle: {vehicle.registration_number} "
                   f"Duty ID: {duty.id}")
        
        return jsonify({
            'success': True,
            'message': 'Duty started successfully',
            'duty': {
                'id': duty.id,
                'status': duty.status.name,
                'start_time': duty.actual_start.isoformat(),
                'vehicle': {
                    'id': vehicle.id,
                    'registration': vehicle.registration_number,
                    'model': vehicle.model
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in start_duty: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_api_bp.route('/api/v1/driver/duty/end', methods=['POST'])
@jwt_required()
@csrf.exempt
def end_duty():
    """End current active duty"""
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
                'error': 'INVALID_REQUEST',
                'message': 'Request body is required'
            }), 400
        
        duty_id = data.get('duty_id')
        end_odometer = data.get('end_odometer', 0)
        end_location = data.get('end_location', {})
        total_revenue = data.get('total_revenue', 0)
        notes = data.get('notes', '')
        
        # Get active duty
        if duty_id:
            duty = Duty.query.filter_by(id=duty_id, driver_id=user.id).first()
        else:
            duty = Duty.query.filter_by(
                driver_id=user.id,
                status=DutyStatus.ACTIVE
            ).first()
        
        if not duty:
            return jsonify({
                'success': False,
                'error': 'DUTY_NOT_FOUND',
                'message': 'No active duty found'
            }), 404
        
        if duty.status != DutyStatus.ACTIVE:
            return jsonify({
                'success': False,
                'error': 'DUTY_NOT_ACTIVE',
                'message': 'Duty is not active'
            }), 409
        
        # End the duty
        duty.actual_end = datetime.now(timezone.utc)
        duty.end_odometer = end_odometer
        duty.cash_collection = total_revenue  # Store as cash collection
        if notes:
            duty.notes = f"{duty.notes} | End Notes: {notes}" if duty.notes else notes
        duty.status = DutyStatus.COMPLETED
        
        # Calculate distance
        if duty.start_odometer and end_odometer:
            duty.total_distance = end_odometer - duty.start_odometer
        
        # Store end location
        if end_location:
            duty.end_location_lat = end_location.get('latitude')
            duty.end_location_lng = end_location.get('longitude')
            if end_location.get('address'):
                duty.notes = f"{duty.notes} | End: {end_location.get('address')}" if duty.notes else f"End: {end_location.get('address')}"
        
        db.session.commit()
        
        logger.info(f"DUTY_ENDED: Driver: {user.username} Duty ID: {duty.id} "
                   f"Distance: {duty.distance_km}km Revenue: {total_revenue}")
        
        return jsonify({
            'success': True,
            'message': 'Duty ended successfully',
            'duty': {
                'id': duty.id,
                'status': duty.status.name,
                'start_time': duty.actual_start.isoformat() if duty.actual_start else None,
                'end_time': duty.actual_end.isoformat() if duty.actual_end else None,
                'distance_km': float(duty.total_distance or 0),
                'total_revenue': float(duty.cash_collection or 0),
                'duration_hours': (duty.actual_end - duty.actual_start).total_seconds() / 3600 
                                if duty.actual_start and duty.actual_end else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error in end_duty: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

@mobile_api_bp.route('/api/v1/driver/vehicles', methods=['GET'])
@jwt_required()
@csrf.exempt
def get_available_vehicles():
    """Get list of available vehicles for the driver"""
    try:
        user = get_current_mobile_user()
        if not user or user.role.name != 'DRIVER':
            return jsonify({
                'success': False,
                'error': 'ACCESS_DENIED',
                'message': 'Access denied - drivers only'
            }), 403
        
        # Get vehicles from the same branch or unassigned vehicles
        vehicles = Vehicle.query.filter(
            (Vehicle.branch_id == user.branch_id) |
            (Vehicle.branch_id.is_(None))
        ).filter_by(status='ACTIVE').all()
        
        vehicles_data = []
        for vehicle in vehicles:
            vehicle_data = {
                'id': vehicle.id,
                'registration_number': vehicle.registration_number,
                'model': vehicle.model,
                'manufacturer': vehicle.manufacturer,
                'year': vehicle.year,
                'fuel_type': vehicle.fuel_type,
                'current_odometer': getattr(vehicle, 'current_odometer', 0),
                'is_available': not hasattr(vehicle, 'active_duty')  # Check if vehicle is in use
            }
            vehicles_data.append(vehicle_data)
        
        return jsonify({
            'success': True,
            'vehicles': vehicles_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_available_vehicles: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500