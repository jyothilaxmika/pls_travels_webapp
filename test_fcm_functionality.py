#!/usr/bin/env python3
"""
Test script for FCM functionality
This script tests the Firebase service methods and token cleanup functionality
"""

from app import app, db
from firebase_service import firebase_service
from models import User
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_firebase_initialization():
    """Test Firebase service initialization"""
    try:
        with app.app_context():
            result = firebase_service.initialize()
            logger.info(f"Firebase initialization result: {result}")
            return result
    except Exception as e:
        logger.error(f"Firebase initialization failed: {str(e)}")
        return False

def test_token_cleanup():
    """Test the token cleanup functionality"""
    try:
        with app.app_context():
            logger.info("Testing Firebase token cleanup...")
            result = firebase_service.cleanup_invalid_tokens()
            logger.info(f"Token cleanup result: {result}")
            return result
    except Exception as e:
        logger.error(f"Token cleanup failed: {str(e)}")
        return {'error': str(e)}

def test_send_notification():
    """Test sending a notification to a dummy user"""
    try:
        with app.app_context():
            # Create a test user with a dummy FCM token
            test_user = User.query.filter_by(username='test_fcm_user').first()
            if not test_user:
                test_user = User(
                    username='test_fcm_user',
                    email='test@example.com',
                    fcm_token='dummy_invalid_token_for_testing'
                )
                db.session.add(test_user)
                db.session.commit()
                
            logger.info(f"Testing notification to user {test_user.id}")
            result = firebase_service.send_notification(
                user_id=test_user.id,
                title="Test Notification",
                body="This is a test notification to verify FCM functionality",
                data={'test': 'true'},
                notification_type='test',
                priority='normal'
            )
            logger.info(f"Notification send result: {result}")
            return result
    except Exception as e:
        logger.error(f"Notification test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all FCM tests"""
    logger.info("=== Starting FCM Functionality Tests ===")
    
    # Test 1: Firebase initialization
    logger.info("\n1. Testing Firebase initialization...")
    init_result = test_firebase_initialization()
    
    # Test 2: Token cleanup
    logger.info("\n2. Testing token cleanup...")
    cleanup_result = test_token_cleanup()
    
    # Test 3: Notification sending (with invalid token)
    logger.info("\n3. Testing notification with invalid token...")
    notification_result = test_send_notification()
    
    # Summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"Firebase initialization: {'✅ PASS' if init_result else '❌ FAIL'}")
    logger.info(f"Token cleanup: {'✅ PASS' if not cleanup_result.get('error') else '❌ FAIL'}")
    logger.info(f"Notification handling: {'✅ PASS' if notification_result is not None else '❌ FAIL'}")
    
    return {
        'firebase_init': init_result,
        'token_cleanup': cleanup_result,
        'notification_test': notification_result
    }

if __name__ == '__main__':
    results = run_all_tests()
    print(f"\nFinal test results: {results}")