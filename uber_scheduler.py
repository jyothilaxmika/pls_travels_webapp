"""
Uber Fleet Data Synchronization Scheduler

This module provides background task scheduling for automated 
data synchronization with Uber Fleet Supplier APIs.
"""

import os
import time
import logging
import schedule
from datetime import datetime, timedelta
from contextlib import contextmanager
from app import create_app
from models import UberIntegrationSettings, UberSyncJob, db
from uber_sync import uber_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uber_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UberScheduler:
    """
    Background scheduler for Uber data synchronization
    """
    
    def __init__(self):
        self.app = create_app()
        self.running = False
    
    @contextmanager
    def app_context(self):
        """Provide Flask application context for database operations"""
        with self.app.app_context():
            yield
    
    def get_integration_settings(self):
        """Get current integration settings"""
        with self.app_context():
            return UberIntegrationSettings.query.first()
    
    def should_run_sync(self, last_sync, frequency_hours):
        """Check if sync should run based on frequency"""
        if not last_sync:
            return True
        
        next_sync_time = last_sync + timedelta(hours=frequency_hours)
        return datetime.utcnow() >= next_sync_time
    
    def run_vehicle_sync(self):
        """Run vehicle synchronization"""
        with self.app_context():
            try:
                settings = self.get_integration_settings()
                if not settings or not settings.is_enabled or not settings.auto_sync_vehicles:
                    logger.info("Vehicle sync disabled or not configured")
                    return
                
                # Check if we should run sync based on frequency
                if not self.should_run_sync(settings.last_full_sync, settings.sync_frequency_hours):
                    logger.info("Vehicle sync not due yet")
                    return
                
                logger.info("Starting scheduled vehicle sync")
                
                # Create sync job (use system user ID = 1 for scheduled jobs)
                job = uber_sync.create_sync_job(
                    'vehicles', 
                    settings.sync_direction_vehicles, 
                    1,  # System user
                    {'scheduled': True, 'scheduler_run': True}
                )
                
                # Run the sync
                result = uber_sync.run_sync_job(job.id)
                
                if result['status'] == 'completed':
                    logger.info(f"Vehicle sync completed: {result['message']}")
                    # Update last sync time
                    settings.last_full_sync = datetime.utcnow()
                    db.session.commit()
                else:
                    logger.error(f"Vehicle sync failed: {result['message']}")
                    
            except Exception as e:
                logger.error(f"Error in scheduled vehicle sync: {str(e)}")
                db.session.rollback()
    
    def run_driver_sync(self):
        """Run driver synchronization"""
        with self.app_context():
            try:
                settings = self.get_integration_settings()
                if not settings or not settings.is_enabled or not settings.auto_sync_drivers:
                    logger.info("Driver sync disabled or not configured")
                    return
                
                # Check if we should run sync based on frequency
                if not self.should_run_sync(settings.last_full_sync, settings.sync_frequency_hours):
                    logger.info("Driver sync not due yet")
                    return
                
                logger.info("Starting scheduled driver sync")
                
                # Create sync job
                job = uber_sync.create_sync_job(
                    'drivers', 
                    settings.sync_direction_drivers, 
                    1,  # System user
                    {'scheduled': True, 'scheduler_run': True}
                )
                
                # Run the sync
                result = uber_sync.run_sync_job(job.id)
                
                if result['status'] == 'completed':
                    logger.info(f"Driver sync completed: {result['message']}")
                else:
                    logger.error(f"Driver sync failed: {result['message']}")
                    
            except Exception as e:
                logger.error(f"Error in scheduled driver sync: {str(e)}")
                db.session.rollback()
    
    def run_trip_sync(self):
        """Run trip data synchronization"""
        with self.app_context():
            try:
                settings = self.get_integration_settings()
                if not settings or not settings.is_enabled or not settings.auto_sync_trips:
                    logger.info("Trip sync disabled or not configured")
                    return
                
                logger.info("Starting scheduled trip sync")
                
                # Sync trips from last 24 hours
                config = {
                    'start_date': (datetime.utcnow() - timedelta(hours=24)).isoformat(),
                    'end_date': datetime.utcnow().isoformat(),
                    'scheduled': True,
                    'scheduler_run': True
                }
                
                # Create sync job
                job = uber_sync.create_sync_job(
                    'trips', 
                    'from_uber',  # trips are always from Uber
                    1,  # System user
                    config
                )
                
                # Run the sync
                result = uber_sync.run_sync_job(job.id)
                
                if result['status'] == 'completed':
                    logger.info(f"Trip sync completed: {result['message']}")
                else:
                    logger.error(f"Trip sync failed: {result['message']}")
                    
            except Exception as e:
                logger.error(f"Error in scheduled trip sync: {str(e)}")
                db.session.rollback()
    
    def cleanup_old_jobs(self):
        """Clean up old sync jobs to prevent database bloat"""
        with self.app_context():
            try:
                # Delete sync jobs older than 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                old_jobs = UberSyncJob.query.filter(
                    UberSyncJob.created_at < cutoff_date
                ).all()
                
                for job in old_jobs:
                    db.session.delete(job)
                
                db.session.commit()
                
                if old_jobs:
                    logger.info(f"Cleaned up {len(old_jobs)} old sync jobs")
                
            except Exception as e:
                logger.error(f"Error cleaning up old jobs: {str(e)}")
                db.session.rollback()
    
    def setup_schedule(self):
        """Setup the synchronization schedule with optimized intervals"""
        # Schedule main sync jobs every 2 hours instead of every hour to reduce load
        schedule.every(2).hours.do(self.run_vehicle_sync)
        schedule.every(2).hours.do(self.run_driver_sync)
        
        # Schedule trip sync less frequently (every hour instead of 30 minutes)
        schedule.every().hour.do(self.run_trip_sync)
        
        # Schedule cleanup once daily at 2 AM
        schedule.every().day.at("02:00").do(self.cleanup_old_jobs)
        
        logger.info("Uber sync scheduler configured with optimized intervals")
        logger.info("- Vehicle/Driver sync: Every 2 hours (respects frequency settings)")
        logger.info("- Trip sync: Every hour")
        logger.info("- Cleanup: Daily at 2:00 AM")
    
    def run(self):
        """Run the scheduler"""
        logger.info("Starting Uber Fleet Sync Scheduler")
        
        # Setup the schedule
        self.setup_schedule()
        
        # Initial connection test
        with self.app_context():
            test_result = uber_sync.test_connection()
            if test_result['status'] == 'success':
                logger.info("Initial Uber API connection test successful")
            else:
                logger.warning(f"Initial Uber API connection test failed: {test_result['message']}")
        
        self.running = True
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(300)  # Check every 5 minutes instead of every minute to reduce CPU usage
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
        finally:
            self.running = False
            logger.info("Uber Fleet Sync Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False

def main():
    """Main entry point for the scheduler"""
    scheduler = UberScheduler()
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        scheduler.stop()

if __name__ == '__main__':
    main()