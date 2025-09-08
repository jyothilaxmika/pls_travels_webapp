"""
Playwright configuration for PLS TRAVELS application testing
"""

import os
from playwright.sync_api import BrowserType

# Test configuration
PLAYWRIGHT_CONFIG = {
    'base_url': 'http://localhost:5000',
    'timeout': 60000,  # 60 seconds
    'headless': True,
    'browser': 'chromium',
    'screenshot_mode': 'only-on-failure',
    'video_mode': 'retain-on-failure',
    'trace_mode': 'retain-on-failure'
}

# Test data paths
TEST_DATA_DIR = 'tests/test_data'
SCREENSHOT_DIR = 'tests/screenshots'
VIDEO_DIR = 'tests/videos'

# Test users
TEST_USERS = {
    'admin': {
        'username': 'admin',
        'password': 'admin123',
        'role': 'ADMIN'
    },
    'manager': {
        'username': 'manager',
        'password': 'manager123', 
        'role': 'MANAGER'
    },
    'driver': {
        'username': 'driver1',
        'password': 'driver123',
        'role': 'DRIVER'
    }
}

# Test routes
TEST_ROUTES = {
    'login': '/auth/login',
    'dashboard': '/',
    'admin_dashboard': '/admin',
    'admin_drivers': '/admin/drivers',
    'admin_storage': '/admin/storage',
    'admin_documents': '/admin/documents',
    'admin_duty_photos': '/admin/duty-photos',
    'driver_dashboard': '/driver',
    'driver_profile': '/driver/profile',
    'driver_duty': '/driver/duty',
    'driver_earnings': '/driver/earnings'
}