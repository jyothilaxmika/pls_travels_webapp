"""
Notification Service

Handles WhatsApp, SMS, email notifications and message orchestration
across different communication channels.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from flask import current_app
from .audit_service import AuditService

logger = logging.getLogger(__name__)

class NotificationService:
    """Service class for notification and messaging operations"""
    
    def __init__(self):
        self.audit_service = AuditService()
    
    def send_whatsapp_message(self, to_number: str, message: str, 
                             entity_type: Optional[str] = None,
                             entity_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Send WhatsApp message via Twilio.
        
        Args:
            to_number: Recipient phone number
            message: Message content
            entity_type: Related entity type for logging
            entity_id: Related entity ID for logging
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            # Import Twilio client (assuming it's configured)
            from utils.whatsapp_utils import send_whatsapp_message as send_wa
            
            result = send_wa(to_number, message)
            
            # Log notification attempt
            self.audit_service.log_action(
                action='whatsapp_message_sent',
                entity_type=entity_type,
                entity_id=entity_id,
                details={
                    'to_number': to_number[-4:].rjust(10, '*'),  # Mask phone number
                    'message_length': len(message),
                    'success': result.get('success', False),
                    'message_id': result.get('message_id')
                }
            )
            
            if result.get('success'):
                logger.info(f"WhatsApp message sent successfully to {to_number[-4:]}")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"WhatsApp message failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False, f"Failed to send message: {str(e)}"
    
    def send_advance_payment_request(self, driver_id: int, amount: float,
                                   reason: str) -> Tuple[bool, Optional[str]]:
        """
        Send advance payment request via WhatsApp.
        
        Args:
            driver_id: ID of driver requesting advance
            amount: Amount requested
            reason: Reason for advance
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            from models import Driver, User
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
            
            if not driver.phone:
                return False, "Driver phone number not available"
            
            # Format message
            message = f"""
🏢 *PLS Travels - Advance Request*

Driver: {driver.full_name}
Employee ID: {driver.employee_id}
Amount: ₹{amount:,.2f}
Reason: {reason}

Request submitted on: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Your request has been forwarded to management for review.
You will be notified once it's processed.

*Note: Advance amounts will be deducted from future earnings.*
            """.strip()
            
            # Send WhatsApp message
            success, error = self.send_whatsapp_message(
                driver.phone, message, 'advance_request', driver_id
            )
            
            if success:
                logger.info(f"Advance payment request notification sent to driver {driver.full_name}")
            
            return success, error
            
        except Exception as e:
            logger.error(f"Error sending advance payment request notification: {str(e)}")
            return False, f"Notification failed: {str(e)}"
    
    def notify_duty_approval(self, duty_id: int, approved: bool,
                            comments: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Notify driver about duty approval/rejection.
        
        Args:
            duty_id: ID of duty
            approved: Whether duty was approved
            comments: Optional comments from approver
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            from models import Duty
            from datetime import datetime
            
            duty = Duty.query.get(duty_id)
            if not duty or not duty.driver:
                return False, "Duty or driver not found"
            
            driver = duty.driver
            if not driver.phone:
                return False, "Driver phone number not available"
            
            # Format message based on approval status
            if approved:
                status_text = "✅ *APPROVED*"
                status_emoji = "🎉"
            else:
                status_text = "❌ *REJECTED*"
                status_emoji = "⚠️"
            
            message = f"""
{status_emoji} *PLS Travels - Duty {status_text}*

Driver: {driver.full_name}
Duty Date: {duty.actual_start.strftime('%Y-%m-%d') if duty.actual_start else 'N/A'}
Vehicle: {duty.vehicle.registration_number if duty.vehicle else 'N/A'}
Distance: {duty.total_distance or 0} km
Revenue: ₹{duty.revenue or 0:,.2f}

{status_text}
            """
            
            if comments:
                message += f"\n\n*Comments:* {comments}"
            
            message += f"\n\nProcessed on: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Send notification
            success, error = self.send_whatsapp_message(
                driver.phone, message.strip(), 'duty_approval', duty_id
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"Error sending duty approval notification: {str(e)}")
            return False, f"Notification failed: {str(e)}"
    
    def send_driver_welcome_message(self, driver_id: int) -> Tuple[bool, Optional[str]]:
        """
        Send welcome message to newly approved driver.
        
        Args:
            driver_id: ID of driver
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            from models import Driver
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return False, "Driver not found"
                
            if not driver.phone:
                return False, "Driver phone number not available"
            
            message = f"""
🎉 *Welcome to PLS Travels!*

Dear {driver.full_name},

Your driver profile has been APPROVED! 

Employee ID: {driver.employee_id}
Branch: {driver.branch.name if driver.branch else 'Main Branch'}

You can now:
✅ Start duties using the mobile app
✅ Track your earnings
✅ View duty history
✅ Update your profile

Download our driver app and login with your credentials to get started.

For support, contact your branch manager or call our helpline.

Welcome to the PLS Travels family! 🚗💪
            """
            
            success, error = self.send_whatsapp_message(
                driver.phone, message.strip(), 'driver_welcome', driver_id
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
            return False, f"Welcome message failed: {str(e)}"
    
    def send_bulk_notification(self, recipients: List[Dict[str, Any]], 
                              message_template: str) -> Dict[str, Any]:
        """
        Send bulk notifications to multiple recipients.
        
        Args:
            recipients: List of recipient dicts with 'phone' and 'name' keys
            message_template: Message template with placeholders
            
        Returns:
            dict: Results summary
        """
        try:
            results = {
                'total': len(recipients),
                'sent': 0,
                'failed': 0,
                'errors': []
            }
            
            for recipient in recipients:
                try:
                    # Format message with recipient data
                    message = message_template.format(**recipient)
                    
                    success, error = self.send_whatsapp_message(
                        recipient['phone'], message
                    )
                    
                    if success:
                        results['sent'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'recipient': recipient.get('name', 'Unknown'),
                            'error': error
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'recipient': recipient.get('name', 'Unknown'),
                        'error': str(e)
                    })
            
            # Log bulk notification summary
            self.audit_service.log_action(
                action='bulk_notification_sent',
                entity_type='notification',
                details=results
            )
            
            logger.info(f"Bulk notification completed: {results['sent']}/{results['total']} sent")
            return results
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {str(e)}")
            return {
                'total': len(recipients) if recipients else 0,
                'sent': 0,
                'failed': len(recipients) if recipients else 0,
                'errors': [{'error': str(e)}]
            }