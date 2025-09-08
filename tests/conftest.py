"""
Pytest configuration and fixtures for PLS TRAVELS application testing
"""

import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import os

# Test configuration inline
PLAYWRIGHT_CONFIG = {
    'base_url': 'http://localhost:5000',
    'timeout': 60000,
    'headless': True,
    'browser': 'chromium'
}

TEST_USERS = {
    'admin': {'username': 'admin', 'password': 'admin123', 'role': 'ADMIN'},
    'manager': {'username': 'manager', 'password': 'manager123', 'role': 'MANAGER'},
    'driver': {'username': 'driver1', 'password': 'driver123', 'role': 'DRIVER'}
}

TEST_ROUTES = {
    'login': '/auth/login',
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


@pytest.fixture(scope="session")
def browser():
    """Create browser instance for the test session"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=PLAYWRIGHT_CONFIG['headless'],
            slow_mo=50 if not PLAYWRIGHT_CONFIG['headless'] else 0
        )
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser):
    """Create a new browser context for each test"""
    context = browser.new_context(
        base_url=PLAYWRIGHT_CONFIG['base_url'],
        viewport={'width': 1280, 'height': 720},
        record_video_dir="tests/videos" if PLAYWRIGHT_CONFIG['video_mode'] else None,
    )
    
    # Enable tracing for debugging
    if PLAYWRIGHT_CONFIG['trace_mode'] == 'retain-on-failure':
        context.tracing.start(screenshots=True, snapshots=True)
    
    yield context
    
    # Save trace on test failure
    if PLAYWRIGHT_CONFIG['trace_mode'] == 'retain-on-failure':
        context.tracing.stop(path="tests/trace.zip")
    
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """Create a new page for each test"""
    page = context.new_page()
    page.set_default_timeout(PLAYWRIGHT_CONFIG['timeout'])
    yield page
    page.close()


@pytest.fixture
def admin_page(page: Page):
    """Logged in admin page"""
    login_as_user(page, 'admin')
    return page


@pytest.fixture  
def manager_page(page: Page):
    """Logged in manager page"""
    login_as_user(page, 'manager')
    return page


@pytest.fixture
def driver_page(page: Page):
    """Logged in driver page"""
    login_as_user(page, 'driver')
    return page


def login_as_user(page: Page, user_type: str):
    """Helper function to login as different user types"""
    user = TEST_USERS[user_type]
    
    page.goto(TEST_ROUTES['login'])
    page.wait_for_load_state('networkidle')
    
    # Fill login form
    page.fill('input[name="username"]', user['username'])
    page.fill('input[name="password"]', user['password'])
    page.click('button[type="submit"]')
    
    # Wait for redirect after login
    page.wait_for_url('**/')
    

@pytest.fixture
def test_driver_data():
    """Test data for driver creation"""
    return {
        'full_name': 'Test Driver John',
        'email': 'testdriver@example.com', 
        'username': 'testdriver123',
        'phone_number': '9876543210',
        'aadhar_number': '123456789012',
        'license_number': 'DL1234567890',
        'bank_account_number': '98765432109876'
    }


@pytest.fixture
def test_files():
    """Test files for upload testing"""
    return {
        'aadhar_doc': 'tests/test_data/sample_aadhar.jpg',
        'license_doc': 'tests/test_data/sample_license.jpg', 
        'profile_photo': 'tests/test_data/sample_profile.jpg',
        'duty_start_photo': 'tests/test_data/sample_duty_start.jpg',
        'duty_end_photo': 'tests/test_data/sample_duty_end.jpg'
    }


def create_test_image(filepath: str, width: int = 400, height: int = 300):
    """Create a dummy test image file"""
    from PIL import Image
    import io
    
    # Create a simple test image
    img = Image.new('RGB', (width, height), color='blue')
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img.save(filepath, 'JPEG')


# Create test images if they don't exist
test_image_files = [
    'tests/test_data/sample_aadhar.jpg',
    'tests/test_data/sample_license.jpg',
    'tests/test_data/sample_profile.jpg', 
    'tests/test_data/sample_duty_start.jpg',
    'tests/test_data/sample_duty_end.jpg'
]

for img_path in test_image_files:
    if not os.path.exists(img_path):
        try:
            create_test_image(img_path)
        except ImportError:
            # If PIL is not available, create a simple text file as placeholder
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, 'w') as f:
                f.write('Test image placeholder')