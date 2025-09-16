"""
Background task scheduler for data retention and privacy compliance
Handles periodic cleanup of location data and privacy maintenance
"""

import logging
import schedule
import time
import threading
from datetime import datetime
from utils.privacy_controls import schedule_data_retention_cleanup

logger = logging.getLogger(__name__)

class BackgroundTaskScheduler:
    """Manages background tasks for data retention and privacy"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
    
    def start_scheduler(self):
        """Start the background task scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        logger.info("Starting background task scheduler")
        
        # Schedule data retention cleanup daily at 2 AM
        schedule.every().day.at("02:00").do(self._safe_run_cleanup)
        
        # Schedule weekly comprehensive cleanup on Sundays at 3 AM  
        schedule.every().sunday.at("03:00").do(self._comprehensive_cleanup)
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Background task scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the background task scheduler"""
        if not self.running:
            return
            
        logger.info("Stopping background task scheduler")
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=30)
        
        logger.info("Background task scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying on error
    
    def _safe_run_cleanup(self):
        """Safely run data retention cleanup with error handling"""
        try:
            logger.info("Starting scheduled data retention cleanup")
            stats = schedule_data_retention_cleanup()
            logger.info(f"Data retention cleanup completed: {stats}")
        except Exception as e:
            logger.error(f"Data retention cleanup failed: {str(e)}")
    
    def _comprehensive_cleanup(self):
        """Run comprehensive weekly cleanup"""
        try:
            logger.info("Starting comprehensive weekly cleanup")
            
            # Run regular data retention
            stats = schedule_data_retention_cleanup()
            
            # Additional cleanup tasks could be added here
            # - Database optimization
            # - Log cleanup  
            # - Cache clearing
            
            logger.info(f"Comprehensive cleanup completed: {stats}")
        except Exception as e:
            logger.error(f"Comprehensive cleanup failed: {str(e)}")

# Global scheduler instance
background_scheduler = BackgroundTaskScheduler()

def init_background_tasks():
    """Initialize background tasks - call this from app startup"""
    try:
        background_scheduler.start_scheduler()
        logger.info("Background tasks initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize background tasks: {str(e)}")

def cleanup_background_tasks():
    """Cleanup background tasks - call this on app shutdown"""
    try:
        background_scheduler.stop_scheduler()
        logger.info("Background tasks cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to cleanup background tasks: {str(e)}")