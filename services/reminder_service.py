"""
Driver Reminder Service
Handles automated reminders for drivers regarding active duties and missing photos
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import and_, or_, func

from app import db
from models import (
    Driver, Duty, DutyStatus, DriverReminder, ReminderType, ReminderStatus,
    DriverStatus, User
)
from timezone_utils import get_ist_time_naive
from services.notification_service import NotificationService
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

class ReminderService:
    """Service for managing driver reminders"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.audit_service = AuditService()
        
        # Reminder thresholds (in hours)
        self.ACTIVE_DUTY_OVERDUE_HOURS = 8  # Remind if duty active > 8 hours
        self.MISSING_PHOTO_HOURS = 2  # Remind if missing photo > 2 hours
        self.LONG_DUTY_HOURS = 12  # Urgent reminder for duties > 12 hours
        
        # Reminder intervals
        self.REMINDER_INTERVAL_HOURS = 2  # Send reminders every 2 hours
        self.MAX_REMINDERS_PER_ISSUE = 3  # Maximum reminders per issue
    
    def identify_drivers_needing_reminders(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify all drivers who need reminders for various issues.
        
        Returns:
            Dict with reminder types as keys and lists of driver data as values
        """
        current_time = get_ist_time_naive()
        reminders_needed = {
            ReminderType.LONG_ACTIVE_DUTY.value: [],
            ReminderType.MISSING_END_PHOTO.value: [],
            ReminderType.MISSING_START_PHOTO.value: [],
            ReminderType.DUTY_NOT_ENDED.value: []
        }
        
        try:
            # Get active duties that need attention  
            from models import UserStatus
            active_duties = db.session.query(Duty).join(Driver).join(User).filter(
                Duty.status == DutyStatus.ACTIVE,
                Driver.status == DriverStatus.ACTIVE,
                User.status == UserStatus.ACTIVE
            ).all()
            
            for duty in active_duties:
                if not duty.actual_start:
                    continue
                    
                duty_duration = current_time - duty.actual_start
                duty_hours = duty_duration.total_seconds() / 3600
                
                # Check for long active duties
                if duty_hours >= self.LONG_DUTY_HOURS:
                    if not self._has_recent_reminder(duty.driver_id, ReminderType.LONG_ACTIVE_DUTY.value, duty.id):
                        reminders_needed[ReminderType.LONG_ACTIVE_DUTY.value].append({
                            'driver': duty.driver,
                            'duty': duty,
                            'hours_active': duty_hours,
                            'priority': 'urgent' if duty_hours > 16 else 'high'
                        })
                
                # Check for missing start photos
                if not duty.start_photo and duty_hours >= self.MISSING_PHOTO_HOURS:
                    if not self._has_recent_reminder(duty.driver_id, ReminderType.MISSING_START_PHOTO.value, duty.id):
                        reminders_needed[ReminderType.MISSING_START_PHOTO.value].append({
                            'driver': duty.driver,
                            'duty': duty,
                            'hours_active': duty_hours,
                            'priority': 'normal'
                        })
                
                # Check for overdue duties that should be ended
                if duty_hours >= self.ACTIVE_DUTY_OVERDUE_HOURS:
                    if not self._has_recent_reminder(duty.driver_id, ReminderType.DUTY_NOT_ENDED.value, duty.id):
                        reminders_needed[ReminderType.DUTY_NOT_ENDED.value].append({
                            'driver': duty.driver,
                            'duty': duty,
                            'hours_active': duty_hours,
                            'priority': 'high' if duty_hours > 10 else 'normal'
                        })
            
            # Check for completed duties missing end photos
            completed_duties_missing_photos = db.session.query(Duty).join(Driver).join(User).filter(
                Duty.status.in_([DutyStatus.COMPLETED, DutyStatus.PENDING_APPROVAL]),
                Duty.end_photo.is_(None),
                Duty.actual_end.is_(None),  # Not properly ended
                Duty.actual_start >= current_time - timedelta(days=1),  # Within last 24 hours
                Driver.status == DriverStatus.ACTIVE,
                User.status == UserStatus.ACTIVE
            ).all()
            
            for duty in completed_duties_missing_photos:
                if not self._has_recent_reminder(duty.driver_id, ReminderType.MISSING_END_PHOTO.value, duty.id):
                    reminders_needed[ReminderType.MISSING_END_PHOTO.value].append({
                        'driver': duty.driver,
                        'duty': duty,
                        'priority': 'normal'
                    })
            
            logger.info(f"Identified reminders needed: {sum(len(v) for v in reminders_needed.values())} total")
            return reminders_needed
            
        except Exception as e:
            logger.error(f"Error identifying drivers needing reminders: {str(e)}")
            return reminders_needed
    
    def _has_recent_reminder(self, driver_id: int, reminder_type: str, duty_id: int = None) -> bool:
        """Check if driver has received a recent reminder for this issue"""
        cutoff_time = get_ist_time_naive() - timedelta(hours=self.REMINDER_INTERVAL_HOURS)
        
        query = db.session.query(DriverReminder).filter(
            DriverReminder.driver_id == driver_id,
            DriverReminder.reminder_type == reminder_type,
            DriverReminder.created_at >= cutoff_time,
            DriverReminder.status.in_([ReminderStatus.SENT, ReminderStatus.PENDING])
        )
        
        if duty_id:
            query = query.filter(DriverReminder.duty_id == duty_id)
        
        return query.first() is not None
    
    def create_reminder(self, driver_id: int, reminder_type: str, message: str, 
                       channel: str = 'whatsapp', duty_id: int = None,
                       priority: str = 'normal', context_data: Dict = None,
                       schedule_delay_minutes: int = 0) -> DriverReminder:
        """
        Create a new reminder for a driver.
        
        Args:
            driver_id: ID of the driver
            reminder_type: Type of reminder from ReminderType class
            message: Message content to send
            channel: Communication channel (whatsapp, sms, push, email)
            duty_id: Related duty ID if applicable
            priority: Priority level (low, normal, high, urgent)
            context_data: Additional context data
            schedule_delay_minutes: Delay before sending (for scheduling)
            
        Returns:
            Created DriverReminder instance
        """
        scheduled_at = get_ist_time_naive()
        if schedule_delay_minutes > 0:
            scheduled_at += timedelta(minutes=schedule_delay_minutes)
        
        reminder = DriverReminder(
            driver_id=driver_id,
            duty_id=duty_id,
            reminder_type=reminder_type,
            message=message,
            channel=channel,
            priority=priority,
            scheduled_at=scheduled_at,
            context_data=context_data or {},
            auto_generated=True
        )
        
        db.session.add(reminder)
        db.session.flush()  # Get the ID
        
        logger.info(f"Created reminder {reminder.id} for driver {driver_id}: {reminder_type}")
        return reminder
    
    def send_reminder(self, reminder: DriverReminder) -> Tuple[bool, Optional[str]]:
        """
        Send a specific reminder via the configured channel.
        
        Args:
            reminder: DriverReminder instance to send
            
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            if reminder.status != ReminderStatus.PENDING:
                return False, f"Reminder {reminder.id} is not in pending status"
            
            driver = reminder.driver
            if not driver or not driver.phone:
                reminder.mark_failed("Driver phone number not available")
                return False, "Driver phone number not available"
            
            success = False
            error_message = None
            
            if reminder.channel == 'whatsapp':
                success, error_message = self.notification_service.send_whatsapp_message(
                    to_number=driver.phone,
                    message=reminder.message,
                    entity_type='driver_reminder',
                    entity_id=reminder.id
                )
            elif reminder.channel == 'sms':
                # Use existing SMS functionality with graceful fallback
                try:
                    from utils.twilio_otp import send_otp_sms
                    # Adapt SMS function for reminder messages
                    result = send_otp_sms(driver.phone, f"PLS Travels reminder: {reminder.message}")
                    success = result.get('success', False)
                    error_message = result.get('message') if not success else None
                    
                    # Handle Twilio not configured gracefully
                    if not success and 'not configured' in (error_message or '').lower():
                        logger.warning(f"SMS not configured, marking reminder {reminder.id} as failed")
                        success = False
                        error_message = "SMS service not configured"
                except ImportError:
                    success = False
                    error_message = "SMS service not available"
            else:
                error_message = f"Unsupported channel: {reminder.channel}"
            
            if success:
                reminder.mark_sent()
                
                # Log the reminder action
                self.audit_service.log_action(
                    action='reminder_sent',
                    entity_type='driver_reminder',
                    entity_id=reminder.id,
                    details={
                        'driver_id': reminder.driver_id,
                        'reminder_type': reminder.reminder_type,
                        'channel': reminder.channel,
                        'duty_id': reminder.duty_id
                    },
                    user_id=None  # System-generated
                )
                
                logger.info(f"Successfully sent reminder {reminder.id} to driver {reminder.driver_id}")
                return True, None
            else:
                reminder.mark_failed(error_message or "Unknown error")
                logger.error(f"Failed to send reminder {reminder.id}: {error_message}")
                return False, error_message
                
        except Exception as e:
            error_msg = f"Error sending reminder {reminder.id}: {str(e)}"
            logger.error(error_msg)
            reminder.mark_failed(error_msg)
            return False, error_msg
    
    def process_pending_reminders(self) -> Dict[str, int]:
        """
        Process all pending reminders that are due to be sent.
        
        Returns:
            Dict with processing statistics
        """
        current_time = get_ist_time_naive()
        stats = {
            'processed': 0,
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Get all pending reminders that are due
            pending_reminders = db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.PENDING,
                DriverReminder.scheduled_at <= current_time,
                DriverReminder.attempts < DriverReminder.max_attempts
            ).order_by(DriverReminder.priority.desc(), DriverReminder.scheduled_at).all()
            
            for reminder in pending_reminders:
                stats['processed'] += 1
                
                try:
                    success, error_msg = self.send_reminder(reminder)
                    if success:
                        stats['sent'] += 1
                    else:
                        stats['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing reminder {reminder.id}: {str(e)}")
                    stats['failed'] += 1
                    
                # Commit after each reminder to avoid losing progress
                try:
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Error committing reminder {reminder.id}: {str(e)}")
                    db.session.rollback()
            
            logger.info(f"Processed {stats['processed']} reminders: {stats['sent']} sent, {stats['failed']} failed")
            return stats
            
        except Exception as e:
            logger.error(f"Error processing pending reminders: {str(e)}")
            db.session.rollback()
            return stats
    
    def generate_reminder_message(self, reminder_type: str, driver_name: str, 
                                 context_data: Dict = None) -> str:
        """
        Generate appropriate reminder message based on type and context.
        
        Args:
            reminder_type: Type of reminder
            driver_name: Driver's name
            context_data: Additional context information
            
        Returns:
            Formatted reminder message
        """
        context = context_data or {}
        
        messages = {
            ReminderType.LONG_ACTIVE_DUTY: (
                f"Hello {driver_name}, you have been on duty for {context.get('hours_active', 0):.1f} hours. "
                f"Please remember to end your duty when finished and upload required photos. "
                f"Contact support if you need assistance."
            ),
            ReminderType.MISSING_START_PHOTO: (
                f"Hello {driver_name}, please upload your duty start photo to complete your duty record. "
                f"This is required for compliance and payment processing."
            ),
            ReminderType.MISSING_END_PHOTO: (
                f"Hello {driver_name}, please upload your duty end photo to complete your duty record. "
                f"This is required for final approval and payment processing."
            ),
            ReminderType.DUTY_NOT_ENDED: (
                f"Hello {driver_name}, you have been on duty for {context.get('hours_active', 0):.1f} hours. "
                f"Please end your duty if you have finished work and upload all required photos."
            )
        }
        
        return messages.get(reminder_type, f"Hello {driver_name}, please check your duty status and complete any pending actions.")
    
    def create_reminders_for_identified_issues(self) -> Dict[str, int]:
        """
        Create reminders for all identified driver issues.
        
        Returns:
            Dict with creation statistics by reminder type
        """
        stats = {}
        
        try:
            issues = self.identify_drivers_needing_reminders()
            
            for reminder_type, driver_issues in issues.items():
                created_count = 0
                
                for issue in driver_issues:
                    driver = issue['driver']
                    duty = issue.get('duty')
                    
                    # Generate contextual message
                    message = self.generate_reminder_message(
                        reminder_type=reminder_type,
                        driver_name=driver.full_name,
                        context_data=issue
                    )
                    
                    # Create reminder
                    reminder = self.create_reminder(
                        driver_id=driver.id,
                        reminder_type=reminder_type,
                        message=message,
                        channel='whatsapp',  # Default to WhatsApp
                        duty_id=duty.id if duty else None,
                        priority=issue.get('priority', 'normal'),
                        context_data=issue
                    )
                    
                    created_count += 1
                
                stats[reminder_type] = created_count
                
            # Commit all created reminders
            db.session.commit()
            
            total_created = sum(stats.values())
            logger.info(f"Created {total_created} new reminders: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error creating reminders for identified issues: {str(e)}")
            db.session.rollback()
            return {}
    
    def mark_reminders_resolved(self, driver_id: int, reminder_types: List[str], 
                               duty_id: int = None) -> int:
        """
        Mark reminders as resolved when the underlying issue is fixed.
        
        Args:
            driver_id: ID of the driver
            reminder_types: List of reminder types to resolve
            duty_id: Optional duty ID to filter by
            
        Returns:
            Number of reminders marked as resolved
        """
        try:
            query = db.session.query(DriverReminder).filter(
                DriverReminder.driver_id == driver_id,
                DriverReminder.reminder_type.in_(reminder_types),
                DriverReminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT])
            )
            
            if duty_id:
                query = query.filter(DriverReminder.duty_id == duty_id)
            
            reminders = query.all()
            resolved_count = 0
            
            for reminder in reminders:
                reminder.mark_resolved()
                resolved_count += 1
            
            if resolved_count > 0:
                db.session.commit()
                logger.info(f"Marked {resolved_count} reminders as resolved for driver {driver_id}")
            
            return resolved_count
            
        except Exception as e:
            logger.error(f"Error marking reminders resolved: {str(e)}")
            db.session.rollback()
            return 0