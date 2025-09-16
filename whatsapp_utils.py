"""
WhatsApp integration utilities for PLS Travels
Handles advance payment requests and driver-admin communication
"""
import os
import logging
from datetime import datetime
from typing import Optional
from models import AdvancePaymentRequest, Driver, User, Duty, Branch, UserRole
from app import db
from sqlalchemy import or_
from auth import log_audit
# From twilio_send_message integration
import os
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_twilio_message(to_phone_number: str, message: str) -> dict:
    """Send WhatsApp/SMS message via Twilio"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Try WhatsApp first, fall back to SMS
        try:
            # WhatsApp format
            message_obj = client.messages.create(
                body=message,
                from_=f'whatsapp:{TWILIO_PHONE_NUMBER}',
                to=f'whatsapp:{to_phone_number}'
            )
            return {'success': True, 'message_sid': message_obj.sid, 'type': 'whatsapp'}
        except Exception as whatsapp_error:
            # Fall back to SMS
            message_obj = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_phone_number
            )
            return {'success': True, 'message_sid': message_obj.sid, 'type': 'sms'}
    
    except Exception as e:
        logging.error(f"Failed to send message: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_branch_admins_phones(branch_id: int) -> list:
    """Get WhatsApp numbers of all admins/managers for a branch"""
    try:
        # Get branch managers - prioritize WhatsApp number, fallback to regular phone  
        from models import manager_branches
        branch_managers = db.session.query(
            User.whatsapp_number, User.phone
        ).join(manager_branches).join(Branch).filter(
            User.role == UserRole.MANAGER,
            or_(User.whatsapp_number.isnot(None), User.phone.isnot(None)),
            Branch.id == branch_id
        ).all()
        
        # Get system admins - prioritize WhatsApp number, fallback to regular phone
        system_admins = db.session.query(
            User.whatsapp_number, User.phone
        ).filter(
            User.role == UserRole.ADMIN,
            or_(User.whatsapp_number.isnot(None), User.phone.isnot(None))
        ).all()
        
        # Combine and extract phone numbers (prefer WhatsApp numbers)
        phone_numbers = []
        
        # Process branch managers (manager is a tuple: (whatsapp_number, phone))
        for manager in branch_managers:
            preferred_number = manager[0] or manager[1]  # whatsapp_number or phone
            if preferred_number:
                phone_numbers.append(preferred_number)
        
        # Process system admins (admin is a tuple: (whatsapp_number, phone))
        for admin in system_admins:
            preferred_number = admin[0] or admin[1]  # whatsapp_number or phone
            if preferred_number:
                phone_numbers.append(preferred_number)
        
        return phone_numbers
    except Exception as e:
        logging.error(f"Error getting admin phones: {str(e)}")
        return []

def send_advance_payment_request(duty_id: int, driver_id: int, amount: float, 
                                purpose: str = 'fuel', notes: str = '', 
                                location_lat: Optional[float] = None, location_lng: Optional[float] = None) -> dict:
    """
    Send advance payment request to admins via WhatsApp
    
    Args:
        duty_id: Current active duty ID
        driver_id: Driver requesting advance
        amount: Amount requested
        purpose: Purpose of advance (fuel, maintenance, emergency)
        notes: Additional notes from driver
        location_lat: Driver's current latitude
        location_lng: Driver's current longitude
    
    Returns:
        dict: Success status and details
    """
    try:
        # Get driver and duty information
        driver = Driver.query.get(driver_id)
        duty = Duty.query.get(duty_id)
        
        if not driver or not duty:
            return {'success': False, 'error': 'Driver or duty not found'}
        
        # Create advance payment request record with proper defaults
        advance_request = AdvancePaymentRequest()
        advance_request.duty_id = duty_id
        advance_request.driver_id = driver_id
        advance_request.amount_requested = amount
        advance_request.purpose = purpose
        advance_request.notes = notes
        advance_request.request_lat = location_lat
        advance_request.request_lng = location_lng
        advance_request.status = 'pending'
        advance_request.created_at = datetime.now()
        advance_request.whatsapp_message_sent = False
        
        db.session.add(advance_request)
        db.session.flush()  # Get the ID
        
        # Get admin phone numbers for the branch
        admin_phones = get_branch_admins_phones(duty.branch_id)
        
        # Always commit the request first to ensure it's saved, even if messaging fails
        db.session.commit()
        
        # Log the advance payment request
        log_audit('create_advance_payment_request', 'advance_payment_request', advance_request.id, {
            'driver_id': driver_id,
            'duty_id': duty_id,
            'amount_requested': amount,
            'purpose': purpose
        })
        
        if not admin_phones:
            return {'success': True, 'error': 'No admin contacts found for branch', 'request_id': advance_request.id, 'message_sent_to': []}
        
        # Create WhatsApp message
        driver_name = driver.full_name
        vehicle_number = duty.vehicle.registration_number if duty.vehicle else 'N/A'
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        message = f"""
🚗 *PLS TRAVELS - ADVANCE PAYMENT REQUEST*

👤 **Driver:** {driver_name}
🚙 **Vehicle:** {vehicle_number}
💰 **Amount:** ₹{amount:,.2f}
🎯 **Purpose:** {purpose.title()}
📅 **Time:** {current_time}

📝 **Notes:** {notes if notes else 'No additional notes'}

🆔 **Request ID:** #{advance_request.id}
📍 **Duty ID:** #{duty_id}

*Please respond with approval/rejection*

---
PLS Travels Fleet Management System
        """.strip()
        
        # Send to all admins
        successful_sends = 0
        for phone in admin_phones:
            result = send_twilio_message(phone, message)
            if result['success']:
                successful_sends += 1
                # Update the advance request with successful send
                if not advance_request.whatsapp_message_sent:
                    advance_request.whatsapp_message_sent = True
                    advance_request.whatsapp_sent_at = datetime.now()
                    advance_request.admin_phone = phone
        
        # Commit metadata updates
        db.session.commit()
        
        # Return success regardless of messaging status since request is already saved
        if successful_sends > 0:
            return {
                'success': True, 
                'request_id': advance_request.id,
                'message_sent_to': successful_sends,
                'total_admins': len(admin_phones)
            }
        else:
            return {
                'success': True, 
                'request_id': advance_request.id,
                'message_sent_to': 0,
                'total_admins': len(admin_phones),
                'warning': 'Request saved but failed to send messages to any admin'
            }
            
    except Exception as e:
        # Handle error gracefully
        db.session.rollback()
        logging.error(f"Error creating advance payment request: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_pending_advance_requests(driver_id: int) -> list:
    """Get pending advance payment requests for a driver"""
    try:
        requests = AdvancePaymentRequest.query.filter(
            AdvancePaymentRequest.driver_id == driver_id,
            AdvancePaymentRequest.status == 'pending'
        ).order_by(AdvancePaymentRequest.created_at.desc()).all()
        
        return [{
            'id': req.id,
            'amount_requested': req.amount_requested,
            'purpose': req.purpose,
            'notes': req.notes,
            'created_at': req.created_at.strftime('%Y-%m-%d %H:%M'),
            'status': req.status
        } for req in requests]
        
    except Exception as e:
        logging.error(f"Error getting pending requests: {str(e)}")
        return []

def respond_to_advance_request(request_id: int, admin_user_id: int, 
                              status: str, approved_amount: float = 0.0, 
                              response_notes: str = '') -> dict:
    """
    Admin response to advance payment request
    
    Args:
        request_id: Advance payment request ID
        admin_user_id: Admin user ID responding
        status: 'approved' or 'rejected'
        approved_amount: Amount approved (if different from requested)
        response_notes: Admin's response notes
    
    Returns:
        dict: Success status and details
    """
    try:
        advance_request = AdvancePaymentRequest.query.get(request_id)
        if not advance_request:
            return {'success': False, 'error': 'Advance request not found'}
        
        # Update the request
        advance_request.status = status
        advance_request.approved_amount = approved_amount if status == 'approved' else 0.0
        advance_request.response_notes = response_notes
        advance_request.responded_by = admin_user_id
        advance_request.responded_at = datetime.now()
        
        # If approved, update the duty's company pay (advance is company expense)
        if status == 'approved' and approved_amount > 0:
            duty = advance_request.duty
            if duty:
                duty.company_pay = (duty.company_pay or 0) + approved_amount
        
        db.session.commit()
        
        # Log the admin response
        log_audit('respond_advance_payment_request', 'advance_payment_request', request_id, {
            'status': status,
            'approved_amount': approved_amount,
            'admin_user_id': admin_user_id
        })
        
        # Send confirmation message to driver
        driver = advance_request.driver
        driver_phones = driver.get_all_phones()
        
        if driver_phones:
            admin = User.query.get(admin_user_id)
            admin_name = admin.full_name if admin else 'Admin'
            
            status_emoji = '✅' if status == 'approved' else '❌'
            status_text = status.upper()
            
            confirmation_message = f"""
{status_emoji} *ADVANCE PAYMENT {status_text}*

Request ID: #{request_id}
Amount Requested: ₹{advance_request.amount_requested:,.2f}
{f'Amount Approved: ₹{approved_amount:,.2f}' if status == 'approved' else ''}

Response by: {admin_name}
{f'Notes: {response_notes}' if response_notes else ''}

---
PLS Travels Fleet Management
            """.strip()
            
            # Send to driver's primary phone
            send_twilio_message(driver_phones[0], confirmation_message)
        
        return {'success': True, 'message': f'Request {status} successfully'}
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error responding to advance request: {str(e)}")
        return {'success': False, 'error': str(e)}