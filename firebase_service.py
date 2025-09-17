"""
Firebase Cloud Messaging Service
Handles push notifications for PLS Travels Android app
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from firebase_admin import credentials, messaging, initialize_app
import firebase_admin
from models import User, db

logger = logging.getLogger(__name__)

class FirebaseService:
    """Firebase Cloud Messaging service for sending push notifications"""
    
    def __init__(self):
        self._app = None
        self._initialized = False
        
    def initialize(self):
        """Initialize Firebase Admin SDK"""
        if self._initialized:
            return True
            
        try:
            # Check if Firebase service account key exists
            if not os.path.exists('firebase-service-account.json'):
                logger.warning("Firebase service account key not found. Push notifications disabled.")
                return False
                
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                cred = credentials.Certificate('firebase-service-account.json')
                self._app = initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                self._app = firebase_admin.get_app()
                
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            return False
    
    def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        notification_type: str = "general",
        priority: str = "normal"
    ) -> bool:
        """
        Send push notification to a specific user
        
        Args:
            user_id: ID of the user to send notification to
            title: Notification title
            body: Notification body text
            data: Additional data payload
            notification_type: Type of notification (duty_assignment, emergency_alert, etc.)
            priority: Notification priority (high, normal, low)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._initialized and not self.initialize():
            logger.error("Firebase not initialized. Cannot send notification.")
            return False
            
        try:
            # Get user's FCM token
            user = User.query.get(user_id)
            if not user or not user.fcm_token:
                logger.warning(f"User {user_id} not found or no FCM token available")
                return False
            
            # Prepare data payload
            if data is None:
                data = {}
            
            data.update({
                'type': notification_type,
                'priority': priority,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': str(user_id)
            })
            
            # Create notification message
            android_config = messaging.AndroidConfig(
                priority='high' if priority == 'high' else 'normal',
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon='ic_notification',
                    color='#FFC107',  # PLS Travels yellow theme
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK'
                ),
                data=data
            )
            
            message = messaging.Message(
                token=user.fcm_token,
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data,
                android=android_config
            )
            
            # Send the message
            response = messaging.send(message)
            logger.info(f"Notification sent successfully to user {user_id}: {response}")
            
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token for user {user_id} is invalid/unregistered. Clearing token.")
            # Clear invalid token from database
            if user:
                old_token = user.fcm_token
                user.fcm_token = None
                user.fcm_token_updated = None
                db.session.commit()
                logger.info(f"Cleared invalid FCM token for user {user_id}: {old_token[:20] + '...' if old_token else 'None'}")
            return False
            
        except messaging.SenderIdMismatchError:
            logger.error(f"FCM sender ID mismatch for user {user_id}. Token belongs to different project.")
            # Clear token as it's for a different project
            if user:
                user.fcm_token = None
                user.fcm_token_updated = None
                db.session.commit()
            return False
            
        except messaging.QuotaExceededError:
            logger.error(f"FCM quota exceeded for user {user_id}. Retrying later.")
            # Don't clear token, just fail gracefully - quota issue is temporary
            return False
            
        except messaging.InvalidArgumentError as e:
            logger.error(f"Invalid FCM message arguments for user {user_id}: {str(e)}")
            # Check if it's token-related and clear if necessary
            if "registration-token" in str(e).lower() or "invalid token" in str(e).lower():
                if user:
                    user.fcm_token = None
                    user.fcm_token_updated = None
                    db.session.commit()
                    logger.info(f"Cleared invalid FCM token for user {user_id} due to argument error")
            return False
            
        except messaging.ThirdPartyAuthError:
            logger.error(f"FCM authentication error for user {user_id}. Check Firebase credentials.")
            # Don't clear user token - this is a server-side auth issue
            return False
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {str(e)}")
            # For unknown errors, check if it might be token-related
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['token', 'invalid', 'unregistered', 'registration']):
                logger.warning(f"Possible token-related error for user {user_id}, clearing FCM token")
                if user:
                    user.fcm_token = None
                    user.fcm_token_updated = None
                    db.session.commit()
            return False
    
    def send_notification_to_multiple_users(
        self,
        user_ids: List[int],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        notification_type: str = "general",
        priority: str = "normal"
    ) -> Dict[int, bool]:
        """
        Send notification to multiple users
        
        Returns:
            Dict[int, bool]: Dictionary mapping user_id to success status
        """
        results = {}
        
        for user_id in user_ids:
            results[user_id] = self.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                data=data,
                notification_type=notification_type,
                priority=priority
            )
            
        return results
    
    def send_duty_assignment_notification(
        self,
        driver_id: int,
        duty_id: int,
        vehicle_registration: str,
        start_time: str
    ) -> bool:
        """Send duty assignment notification to driver"""
        return self.send_notification(
            user_id=driver_id,
            title="🚗 New Duty Assignment",
            body=f"Vehicle {vehicle_registration} assigned. Start time: {start_time}",
            data={
                'duty_id': str(duty_id),
                'vehicle_registration': vehicle_registration,
                'start_time': start_time,
                'action': 'view_duty'
            },
            notification_type='duty_assignment',
            priority='high'
        )
    
    def send_duty_status_update(
        self,
        driver_id: int,
        duty_id: int,
        status: str,
        message: str
    ) -> bool:
        """Send duty status update notification"""
        return self.send_notification(
            user_id=driver_id,
            title="📋 Duty Status Update",
            body=message,
            data={
                'duty_id': str(duty_id),
                'status': status,
                'action': 'view_duty'
            },
            notification_type='duty_update',
            priority='normal'
        )
    
    def send_emergency_alert(
        self,
        user_ids: List[int],
        alert_id: str,
        message: str
    ) -> Dict[int, bool]:
        """Send emergency alert to multiple users"""
        return self.send_notification_to_multiple_users(
            user_ids=user_ids,
            title="🚨 Emergency Alert",
            body=message,
            data={
                'alert_id': alert_id,
                'action': 'acknowledge_emergency'
            },
            notification_type='emergency_alert',
            priority='high'
        )
    
    def send_system_message(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[int, bool]:
        """Send system message to multiple users"""
        return self.send_notification_to_multiple_users(
            user_ids=user_ids,
            title=title,
            body=message,
            data=data or {},
            notification_type='system_message',
            priority='normal'
        )
    
    def send_silent_sync_request(
        self,
        user_id: int
    ) -> bool:
        """Send silent background sync request"""
        return self.send_notification(
            user_id=user_id,
            title="",  # Silent notification
            body="",
            data={
                'action': 'background_sync'
            },
            notification_type='silent_sync',
            priority='normal'
        )
    
    def get_user_notification_settings(self, user_id: int) -> Dict[str, bool]:
        """Get user's notification preferences (placeholder for future feature)"""
        return {
            'duty_assignments': True,
            'duty_updates': True,
            'emergency_alerts': True,
            'system_messages': True,
            'location_reminders': True
        }
    
    def cleanup_invalid_tokens(self) -> Dict[str, int]:
        """
        Cleanup invalid FCM tokens by testing them
        This method can be called periodically to maintain token hygiene
        
        Returns:
            Dict with cleanup statistics
        """
        if not self._initialized and not self.initialize():
            logger.error("Firebase not initialized. Cannot cleanup tokens.")
            return {'error': 'Firebase not initialized'}
        
        try:
            # Get all users with FCM tokens
            users_with_tokens = User.query.filter(User.fcm_token.isnot(None)).all()
            
            total_tokens = len(users_with_tokens)
            invalid_tokens = 0
            valid_tokens = 0
            
            logger.info(f"Starting FCM token cleanup for {total_tokens} users")
            
            for user in users_with_tokens:
                try:
                    # Create a minimal test message
                    test_message = messaging.Message(
                        token=user.fcm_token,
                        data={'test': 'token_validation', 'timestamp': datetime.utcnow().isoformat()}
                    )
                    
                    # Validate token without sending (dry_run=True)
                    messaging.send(test_message, dry_run=True)
                    valid_tokens += 1
                    
                except messaging.UnregisteredError:
                    logger.info(f"Cleaning up unregistered token for user {user.id}")
                    user.fcm_token = None
                    user.fcm_token_updated = None
                    invalid_tokens += 1
                    
                except messaging.SenderIdMismatchError:
                    logger.info(f"Cleaning up mismatched token for user {user.id}")
                    user.fcm_token = None
                    user.fcm_token_updated = None
                    invalid_tokens += 1
                    
                except messaging.InvalidArgumentError:
                    logger.info(f"Cleaning up invalid token for user {user.id}")
                    user.fcm_token = None
                    user.fcm_token_updated = None
                    invalid_tokens += 1
                    
                except Exception as e:
                    logger.warning(f"Error validating token for user {user.id}: {str(e)}")
                    # For unknown errors, be conservative and don't clear the token
            
            # Commit all changes
            db.session.commit()
            
            result = {
                'total_tokens_checked': total_tokens,
                'valid_tokens': valid_tokens,
                'invalid_tokens_removed': invalid_tokens
            }
            
            logger.info(f"FCM token cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error during FCM token cleanup: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

# Global Firebase service instance
firebase_service = FirebaseService()

def send_push_notification(
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    notification_type: str = "general",
    priority: str = "normal"
) -> bool:
    """
    Convenience function to send push notification
    
    Usage:
        from firebase_service import send_push_notification
        
        send_push_notification(
            user_id=123,
            title="New Duty",
            body="You have been assigned a new duty",
            data={'duty_id': '456'},
            notification_type='duty_assignment'
        )
    """
    return firebase_service.send_notification(
        user_id=user_id,
        title=title,
        body=body,
        data=data,
        notification_type=notification_type,
        priority=priority
    )

def send_duty_notification(driver_id: int, duty_id: int, vehicle_registration: str, start_time: str) -> bool:
    """Convenience function for duty assignment notifications"""
    return firebase_service.send_duty_assignment_notification(
        driver_id=driver_id,
        duty_id=duty_id,
        vehicle_registration=vehicle_registration,
        start_time=start_time
    )

def send_emergency_notification(user_ids: List[int], alert_id: str, message: str) -> Dict[int, bool]:
    """Convenience function for emergency alerts"""
    return firebase_service.send_emergency_alert(
        user_ids=user_ids,
        alert_id=alert_id,
        message=message
    )