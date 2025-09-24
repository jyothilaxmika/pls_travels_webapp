"""
Scheduled Task System for Driver Reminders
Handles automated reminder generation and processing
"""

import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app import create_app, db
from services.reminder_service import ReminderService
from services.audit_service import AuditService
from timezone_utils import get_ist_time_naive

logger = logging.getLogger(__name__)

class ReminderScheduler:
    """Handles scheduled tasks for the reminder system"""
    
    def __init__(self):
        self.reminder_service = ReminderService()
        self.audit_service = AuditService()
        self.running = False
        self.scheduler_thread = None
        
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Reminder scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("Reminder scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        # Schedule reminder tasks
        self._setup_schedule()
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(60)  # Continue after error
    
    def _setup_schedule(self):
        """Setup all scheduled tasks"""
        # Generate new reminders every 30 minutes
        schedule.every(30).minutes.do(self._job_wrapper, self.generate_reminders_job)
        
        # Process pending reminders every 5 minutes
        schedule.every(5).minutes.do(self._job_wrapper, self.process_pending_reminders_job)
        
        # Cleanup old resolved reminders daily at 2 AM
        schedule.every().day.at("02:00").do(self._job_wrapper, self.cleanup_old_reminders_job)
        
        # Auto-resolve reminders for completed duties every hour
        schedule.every().hour.do(self._job_wrapper, self.auto_resolve_completed_duties_job)
        
        logger.info("Scheduled tasks configured")
    
    def _job_wrapper(self, job_func):
        """Wrapper for scheduled jobs with error handling and app context"""
        try:
            app = create_app()
            with app.app_context():
                return job_func()
        except Exception as e:
            logger.error(f"Job error in {job_func.__name__}: {str(e)}")
    
    def generate_reminders_job(self):
        """Scheduled job to generate new reminders for identified issues"""
        try:
            start_time = get_ist_time_naive()
            logger.info("Starting reminder generation job")
            
            stats = self.reminder_service.create_reminders_for_identified_issues()
            
            total_created = sum(stats.values())
            execution_time = (get_ist_time_naive() - start_time).total_seconds()
            
            # Log the job execution
            self.audit_service.log_action(
                action='scheduled_reminder_generation',
                entity_type='system',
                entity_id=None,
                details={
                    'stats': stats,
                    'total_created': total_created,
                    'execution_time_seconds': execution_time
                },
                user_id=None  # System job
            )
            
            logger.info(f"Reminder generation completed: {total_created} reminders created in {execution_time:.2f}s")
            return stats
            
        except Exception as e:
            logger.error(f"Error in reminder generation job: {str(e)}")
            return {}
    
    def process_pending_reminders_job(self):
        """Scheduled job to process and send pending reminders"""
        try:
            start_time = get_ist_time_naive()
            logger.info("Starting pending reminders processing job")
            
            stats = self.reminder_service.process_pending_reminders()
            
            execution_time = (get_ist_time_naive() - start_time).total_seconds()
            
            # Log the job execution
            self.audit_service.log_action(
                action='scheduled_reminder_processing',
                entity_type='system',
                entity_id=None,
                details={
                    'stats': stats,
                    'execution_time_seconds': execution_time
                },
                user_id=None  # System job
            )
            
            logger.info(f"Reminder processing completed: {stats['sent']} sent, {stats['failed']} failed in {execution_time:.2f}s")
            return stats
            
        except Exception as e:
            logger.error(f"Error in reminder processing job: {str(e)}")
            return {}
    
    def cleanup_old_reminders_job(self):
        """Scheduled job to cleanup old resolved/failed reminders"""
        try:
            start_time = get_ist_time_naive()
            logger.info("Starting reminder cleanup job")
            
            # Delete resolved reminders older than 30 days
            resolved_cutoff = start_time - timedelta(days=30)
            
            # Delete failed reminders older than 7 days (keep for troubleshooting)
            failed_cutoff = start_time - timedelta(days=7)
            
            from models import DriverReminder, ReminderStatus
            
            # Count before deletion
            resolved_count = db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.RESOLVED,
                DriverReminder.resolved_at < resolved_cutoff
            ).count()
            
            failed_count = db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.FAILED,
                DriverReminder.updated_at < failed_cutoff
            ).count()
            
            # Perform deletion
            db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.RESOLVED,
                DriverReminder.resolved_at < resolved_cutoff
            ).delete()
            
            db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.FAILED,
                DriverReminder.updated_at < failed_cutoff
            ).delete()
            
            db.session.commit()
            
            execution_time = (get_ist_time_naive() - start_time).total_seconds()
            total_cleaned = resolved_count + failed_count
            
            # Log the cleanup
            self.audit_service.log_action(
                action='scheduled_reminder_cleanup',
                entity_type='system',
                entity_id=None,
                details={
                    'resolved_cleaned': resolved_count,
                    'failed_cleaned': failed_count,
                    'total_cleaned': total_cleaned,
                    'execution_time_seconds': execution_time
                },
                user_id=None
            )
            
            logger.info(f"Reminder cleanup completed: {total_cleaned} reminders cleaned in {execution_time:.2f}s")
            return {'cleaned': total_cleaned}
            
        except Exception as e:
            logger.error(f"Error in reminder cleanup job: {str(e)}")
            db.session.rollback()
            return {}
    
    def auto_resolve_completed_duties_job(self):
        """Scheduled job to auto-resolve reminders for completed duties"""
        try:
            start_time = get_ist_time_naive()
            logger.info("Starting auto-resolve completed duties job")
            
            from models import (
                DriverReminder, ReminderStatus, ReminderType, 
                Duty, DutyStatus
            )
            
            resolved_count = 0
            
            # Find reminders for duties that are now completed with photos
            completed_duties_reminders = db.session.query(DriverReminder).join(Duty).filter(
                DriverReminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT]),
                DriverReminder.reminder_type.in_([
                    ReminderType.MISSING_START_PHOTO,
                    ReminderType.MISSING_END_PHOTO,
                    ReminderType.DUTY_NOT_ENDED,
                    ReminderType.LONG_ACTIVE_DUTY
                ]),
                Duty.status.in_([DutyStatus.COMPLETED, DutyStatus.PENDING_APPROVAL])
            ).all()
            
            for reminder in completed_duties_reminders:
                duty = reminder.duty
                should_resolve = False
                
                # Check if the specific issue is resolved
                if reminder.reminder_type == ReminderType.MISSING_START_PHOTO and duty.start_photo:
                    should_resolve = True
                elif reminder.reminder_type == ReminderType.MISSING_END_PHOTO and duty.end_photo:
                    should_resolve = True
                elif reminder.reminder_type in [ReminderType.DUTY_NOT_ENDED, ReminderType.LONG_ACTIVE_DUTY]:
                    should_resolve = True  # Duty is completed
                
                if should_resolve:
                    reminder.mark_resolved()
                    resolved_count += 1
            
            if resolved_count > 0:
                db.session.commit()
            
            execution_time = (get_ist_time_naive() - start_time).total_seconds()
            
            # Log the auto-resolution
            self.audit_service.log_action(
                action='scheduled_auto_resolve_reminders',
                entity_type='system',
                entity_id=None,
                details={
                    'resolved_count': resolved_count,
                    'execution_time_seconds': execution_time
                },
                user_id=None
            )
            
            logger.info(f"Auto-resolve completed: {resolved_count} reminders resolved in {execution_time:.2f}s")
            return {'resolved': resolved_count}
            
        except Exception as e:
            logger.error(f"Error in auto-resolve job: {str(e)}")
            db.session.rollback()
            return {}

# Global scheduler instance
reminder_scheduler = ReminderScheduler()

def start_reminder_scheduler():
    """Start the global reminder scheduler"""
    reminder_scheduler.start()

def stop_reminder_scheduler():
    """Stop the global reminder scheduler"""
    reminder_scheduler.stop()

def run_manual_reminder_generation():
    """Manually trigger reminder generation (for testing/admin use)"""
    app = create_app()
    with app.app_context():
        return reminder_scheduler.generate_reminders_job()

def run_manual_reminder_processing():
    """Manually trigger reminder processing (for testing/admin use)"""
    app = create_app()
    with app.app_context():
        return reminder_scheduler.process_pending_reminders_job()