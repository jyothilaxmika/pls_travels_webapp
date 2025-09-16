"""
Privacy controls and data retention policies for GPS tracking system
Handles data anonymization, retention limits, and privacy preferences
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_
from app import db
from models import DriverLocation, TrackingSession, Driver, Duty
from timezone_utils import get_ist_time_naive

logger = logging.getLogger(__name__)

class LocationPrivacyValidator:
    """Validates location data for privacy and accuracy"""
    
    # Accuracy thresholds (meters)
    MAX_ACCURACY_METERS = 100  # Reject locations with accuracy > 100m
    SUSPICIOUS_ACCURACY_METERS = 50  # Flag locations with accuracy > 50m
    
    # Speed validation (km/h)
    MAX_REASONABLE_SPEED = 150  # Maximum reasonable speed for vehicles
    SUSPICIOUS_SPEED = 100  # Flag speeds above this
    
    # Geographic bounds for India (approximate)
    INDIA_LAT_BOUNDS = (6.0, 37.6)  # Southern tip to northern border
    INDIA_LON_BOUNDS = (68.0, 97.25)  # Western to eastern border
    
    # Minimum time between location points (seconds)
    MIN_LOCATION_INTERVAL = 10  # Don't accept locations more frequent than every 10s
    
    @classmethod
    def validate_location_accuracy(cls, location_data: Dict) -> Tuple[bool, str]:
        """
        Validate location data for accuracy and privacy compliance
        Returns: (is_valid, reason)
        """
        try:
            lat = float(location_data.get('latitude', 0))
            lon = float(location_data.get('longitude', 0))
            accuracy = location_data.get('accuracy')
            speed = location_data.get('speed')
            
            # Basic coordinate validation
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False, "Invalid coordinate ranges"
            
            # Geographic bounds check (India region)
            if not (cls.INDIA_LAT_BOUNDS[0] <= lat <= cls.INDIA_LAT_BOUNDS[1] and
                    cls.INDIA_LON_BOUNDS[0] <= lon <= cls.INDIA_LON_BOUNDS[1]):
                # Log without exposing precise coordinates for privacy
                lat_rounded = round(lat, 1)
                lon_rounded = round(lon, 1) 
                logger.warning(f"Location outside expected region: ~{lat_rounded}, ~{lon_rounded}")
                # Don't reject, just log for monitoring
            
            # Accuracy validation
            if accuracy is not None:
                if float(accuracy) > cls.MAX_ACCURACY_METERS:
                    return False, f"Location accuracy too low: {accuracy}m (max: {cls.MAX_ACCURACY_METERS}m)"
                
                if float(accuracy) > cls.SUSPICIOUS_ACCURACY_METERS:
                    logger.warning(f"Suspicious location accuracy: {accuracy}m")
            
            # Speed validation
            if speed is not None:
                speed_kmh = float(speed)
                if speed_kmh > cls.MAX_REASONABLE_SPEED:
                    return False, f"Unreasonable speed: {speed_kmh} km/h (max: {cls.MAX_REASONABLE_SPEED})"
                
                if speed_kmh > cls.SUSPICIOUS_SPEED:
                    logger.warning(f"High speed detected: {speed_kmh} km/h")
            
            # Check for obvious mocked locations
            if cls._is_likely_mocked_location(lat, lon, accuracy, speed):
                # Log without exposing precise coordinates for privacy
                logger.warning(f"Potentially mocked location detected (coordinates redacted)")
                location_data['is_mocked'] = True
            
            return True, "Valid"
            
        except (ValueError, TypeError) as e:
            return False, f"Invalid location data format: {str(e)}"
    
    @classmethod
    def _is_likely_mocked_location(cls, lat: float, lon: float, 
                                 accuracy: Optional[float], speed: Optional[float]) -> bool:
        """Detect potentially mocked GPS locations"""
        
        # Check for exact coordinates (often a sign of mocked data)
        if lat == int(lat) and lon == int(lon):
            return True
        
        # Check for suspiciously perfect accuracy
        if accuracy is not None and accuracy <= 1.0:
            return True
        
        # Check for common mock locations (0,0), (1,1), etc.
        mock_locations = [(0.0, 0.0), (1.0, 1.0), (37.4219999, -122.0839999)]  # Including default Android emulator
        for mock_lat, mock_lon in mock_locations:
            if abs(lat - mock_lat) < 0.001 and abs(lon - mock_lon) < 0.001:
                return True
        
        return False
    
    @classmethod
    def validate_location_frequency(cls, driver_id: int, captured_at: datetime) -> bool:
        """Check if location is not too frequent from same driver"""
        
        # Get last location from this driver
        last_location = DriverLocation.query.filter_by(
            driver_id=driver_id
        ).order_by(DriverLocation.captured_at.desc()).first()
        
        if last_location:
            time_diff = (captured_at - last_location.captured_at).total_seconds()
            if time_diff < cls.MIN_LOCATION_INTERVAL:
                return False
        
        return True

class DataRetentionManager:
    """Manages data retention policies for location data"""
    
    # Retention periods
    ACTIVE_DUTY_RETENTION_DAYS = 90      # Keep active duty data for 90 days
    INACTIVE_DATA_RETENTION_DAYS = 30    # Keep inactive data for 30 days  
    AUDIT_RETENTION_DAYS = 365          # Keep audit logs for 1 year
    
    # Cleanup batch sizes
    CLEANUP_BATCH_SIZE = 1000
    
    @classmethod
    def cleanup_expired_data(cls) -> Dict[str, int]:
        """
        Clean up expired location data based on retention policies
        Returns statistics about cleaned data
        """
        logger.info("Starting scheduled data retention cleanup")
        
        stats = {
            'locations_deleted': 0,
            'sessions_deleted': 0,
            'errors': 0
        }
        
        try:
            # Clean up old location data
            stats['locations_deleted'] = cls._cleanup_old_locations()
            
            # Clean up orphaned tracking sessions
            stats['sessions_deleted'] = cls._cleanup_orphaned_sessions()
            
            # Update location data anonymization
            cls._anonymize_old_data()
            
            logger.info(f"Data retention cleanup completed: {stats}")
            
        except Exception as e:
            logger.error(f"Error during data retention cleanup: {str(e)}")
            stats['errors'] += 1
        
        return stats
    
    @classmethod
    def _cleanup_old_locations(cls) -> int:
        """Clean up location data older than retention period"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=cls.ACTIVE_DUTY_RETENTION_DAYS)
        deleted_count = 0
        
        while True:
            # Delete in batches to avoid long-running transactions
            batch = DriverLocation.query.filter(
                DriverLocation.captured_at < cutoff_date
            ).limit(cls.CLEANUP_BATCH_SIZE).all()
            
            if not batch:
                break
            
            for location in batch:
                db.session.delete(location)
            
            db.session.commit()
            deleted_count += len(batch)
            
            logger.info(f"Deleted {len(batch)} location records (total: {deleted_count})")
        
        return deleted_count
    
    @classmethod  
    def _cleanup_orphaned_sessions(cls) -> int:
        """Clean up tracking sessions with no location data"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=cls.INACTIVE_DATA_RETENTION_DAYS)
        
        # Find sessions with no recent locations
        orphaned_sessions = db.session.query(TrackingSession).filter(
            and_(
                TrackingSession.created_at < cutoff_date,
                ~TrackingSession.id.in_(
                    db.session.query(DriverLocation.tracking_session_id).distinct()
                )
            )
        ).limit(cls.CLEANUP_BATCH_SIZE).all()
        
        deleted_count = len(orphaned_sessions)
        
        for session in orphaned_sessions:
            db.session.delete(session)
        
        db.session.commit()
        
        return deleted_count
    
    @classmethod
    def _anonymize_old_data(cls):
        """Anonymize old location data for privacy compliance"""
        
        # Anonymization cutoff (older than 1 year)
        anonymize_cutoff = datetime.utcnow() - timedelta(days=365)
        
        # Update old locations to remove precise coordinates
        # Keep only district-level accuracy for statistical purposes
        old_locations = DriverLocation.query.filter(
            and_(
                DriverLocation.captured_at < anonymize_cutoff,
                DriverLocation.is_anonymized != True
            )
        ).limit(cls.CLEANUP_BATCH_SIZE).all()
        
        for location in old_locations:
            # Round coordinates to district level (~1km accuracy)
            location.latitude = round(location.latitude, 2)  
            location.longitude = round(location.longitude, 2)
            location.is_anonymized = True
            location.accuracy = None  # Remove precise accuracy data
            location.speed = None     # Remove precise speed data
            location.bearing = None   # Remove bearing data
        
        if old_locations:
            db.session.commit()
            logger.info(f"Anonymized {len(old_locations)} old location records")

class PrivacySettings:
    """Manage driver privacy preferences"""
    
    @classmethod
    def get_driver_privacy_level(cls, driver_id: int) -> str:
        """
        Get privacy level for driver
        Returns: 'full', 'limited', 'minimal'
        """
        # For now, return default privacy level
        # In future, this would check driver preferences from database
        return 'full'
    
    @classmethod
    def should_track_location(cls, driver_id: int, duty_status: str = None) -> bool:
        """Check if location tracking is allowed for driver"""
        
        privacy_level = cls.get_driver_privacy_level(driver_id)
        
        # Always track during active duties for safety/operational reasons
        if duty_status == 'ACTIVE':
            return True
        
        # For other statuses, respect privacy settings
        if privacy_level == 'minimal':
            return False
        elif privacy_level == 'limited':
            return duty_status in ['ACTIVE', 'PENDING']
        else:  # 'full' tracking
            return True
    
    @classmethod
    def get_data_sharing_permissions(cls, driver_id: int) -> Dict[str, bool]:
        """Get data sharing permissions for driver"""
        
        privacy_level = cls.get_driver_privacy_level(driver_id)
        
        permissions = {
            'share_with_managers': True,        # Always allowed for operational needs
            'share_for_analytics': privacy_level in ['full', 'limited'],
            'share_with_third_parties': privacy_level == 'full',
            'keep_historical_data': privacy_level in ['full', 'limited']
        }
        
        return permissions

def schedule_data_retention_cleanup():
    """Background task to run data retention cleanup"""
    try:
        stats = DataRetentionManager.cleanup_expired_data()
        logger.info(f"Scheduled data retention cleanup completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Scheduled data retention cleanup failed: {str(e)}")
        return {'error': str(e)}