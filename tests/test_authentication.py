"""
Authentication and Role-based Access Control Tests
"""

import pytest
from playwright.sync_api import Page, expect
from playwright_config import TEST_USERS, TEST_ROUTES


class TestAuthentication:
    """Test authentication functionality"""
    
    @pytest.mark.auth
    def test_login_page_loads(self, page: Page):
        """Test that login page loads correctly"""
        page.goto(TEST_ROUTES['login'])
        expect(page.locator('h1')).to_contain_text('Login')
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()
    
    @pytest.mark.auth
    def test_admin_login_success(self, page: Page):
        """Test successful admin login"""
        user = TEST_USERS['admin']
        
        page.goto(TEST_ROUTES['login'])
        page.fill('input[name="username"]', user['username'])
        page.fill('input[name="password"]', user['password'])
        page.click('button[type="submit"]')
        
        # Should redirect to dashboard
        expect(page).to_have_url('**/admin')
        expect(page.locator('h1, h2')).to_contain_text('Dashboard')
    
    @pytest.mark.auth
    def test_driver_login_success(self, page: Page):
        """Test successful driver login"""
        user = TEST_USERS['driver']
        
        page.goto(TEST_ROUTES['login'])
        page.fill('input[name="username"]', user['username'])
        page.fill('input[name="password"]', user['password'])
        page.click('button[type="submit"]')
        
        # Should redirect to driver dashboard
        expect(page).to_have_url('**/driver')
        expect(page.locator('h1, h2')).to_contain_text('Dashboard')
    
    @pytest.mark.auth
    def test_invalid_login(self, page: Page):
        """Test login with invalid credentials"""
        page.goto(TEST_ROUTES['login'])
        page.fill('input[name="username"]', 'invalid_user')
        page.fill('input[name="password"]', 'invalid_pass')
        page.click('button[type="submit"]')
        
        # Should stay on login page with error
        expect(page).to_have_url('**/login')
        expect(page.locator('.alert-danger, .error-message')).to_be_visible()


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    @pytest.mark.auth 
    @pytest.mark.integration
    def test_admin_can_access_admin_pages(self, admin_page: Page):
        """Test that admin can access admin-only pages"""
        # Test admin dashboard
        admin_page.goto(TEST_ROUTES['admin_dashboard'])
        expect(admin_page.locator('h1, h2')).to_contain_text('Dashboard')
        
        # Test admin drivers page
        admin_page.goto(TEST_ROUTES['admin_drivers'])
        expect(admin_page.locator('h1, h2')).to_contain_text('Drivers')
        
        # Test admin storage page
        admin_page.goto(TEST_ROUTES['admin_storage'])
        expect(admin_page.locator('h1, h2')).to_contain_text('Storage')
    
    @pytest.mark.auth
    @pytest.mark.integration
    def test_driver_cannot_access_admin_pages(self, driver_page: Page):
        """Test that driver cannot access admin pages"""
        # Try to access admin dashboard
        driver_page.goto(TEST_ROUTES['admin_dashboard'])
        
        # Should be redirected or see access denied
        expect(driver_page.locator('body')).to_contain_text(['Access Denied', 'Forbidden', '403'])
        
    @pytest.mark.auth
    def test_driver_can_access_driver_pages(self, driver_page: Page):
        """Test that driver can access driver pages"""
        # Test driver dashboard
        driver_page.goto(TEST_ROUTES['driver_dashboard'])
        expect(driver_page.locator('h1, h2')).to_contain_text('Dashboard')
        
        # Test driver profile
        driver_page.goto(TEST_ROUTES['driver_profile'])
        expect(driver_page.locator('h1, h2')).to_contain_text('Profile')
        
        # Test driver duty
        driver_page.goto(TEST_ROUTES['driver_duty'])
        expect(driver_page.locator('h1, h2')).to_contain_text('Duty')
    
    @pytest.mark.auth
    def test_logout_functionality(self, admin_page: Page):
        """Test logout functionality"""
        # Look for logout link/button and click it
        logout_selector = 'a[href*="logout"], button:has-text("Logout"), .logout-btn'
        
        if admin_page.locator(logout_selector).count() > 0:
            admin_page.click(logout_selector)
            expect(admin_page).to_have_url('**/login')
        else:
            pytest.skip("Logout functionality not found or implemented differently")


class TestNavigationMenus:
    """Test navigation menu visibility based on roles"""
    
    @pytest.mark.auth
    def test_admin_navigation_menu(self, admin_page: Page):
        """Test that admin sees admin navigation options"""
        admin_page.goto(TEST_ROUTES['admin_dashboard'])
        
        # Check for admin menu items
        expect(admin_page.locator('nav')).to_contain_text('Drivers')
        expect(admin_page.locator('nav')).to_contain_text('Vehicles') 
        expect(admin_page.locator('nav')).to_contain_text('Duties')
        expect(admin_page.locator('nav')).to_contain_text('Storage')
    
    @pytest.mark.auth
    def test_driver_navigation_menu(self, driver_page: Page):
        """Test that driver sees driver navigation options"""
        driver_page.goto(TEST_ROUTES['driver_dashboard'])
        
        # Check for driver menu items
        expect(driver_page.locator('nav')).to_contain_text('Dashboard')
        expect(driver_page.locator('nav')).to_contain_text('Profile')
        expect(driver_page.locator('nav')).to_contain_text('Duty')
        
        # Should not see admin options
        expect(driver_page.locator('nav')).not_to_contain_text('Admin')
        expect(driver_page.locator('nav')).not_to_contain_text('Vehicles')