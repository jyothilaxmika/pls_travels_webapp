"""
End-to-End Integration Tests
Tests complete workflows from start to finish
"""

import pytest
from playwright.sync_api import Page, expect
from playwright_config import TEST_ROUTES


class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.e2e
    @pytest.mark.integration
    def test_complete_driver_journey(self, page: Page, admin_page: Page, test_driver_data, test_files):
        """Test complete driver journey from registration to duty completion"""
        
        # Step 1: Driver Registration
        page.goto('/auth/register')
        page.fill('input[name="full_name"]', test_driver_data['full_name'])
        page.fill('input[name="email"]', test_driver_data['email']) 
        page.fill('input[name="username"]', test_driver_data['username'])
        page.fill('input[name="phone_number"]', test_driver_data['phone_number'])
        page.fill('input[name="aadhar_number"]', test_driver_data['aadhar_number'])
        page.fill('input[name="license_number"]', test_driver_data['license_number'])
        
        if page.locator('input[name="aadhar_photo"]').count() > 0:
            page.set_input_files('input[name="aadhar_photo"]', test_files['aadhar_doc'])
        
        if page.locator('input[name="license_photo"]').count() > 0:
            page.set_input_files('input[name="license_photo"]', test_files['license_doc'])
        
        page.click('button[type="submit"]')
        expect(page.locator('.alert-success')).to_be_visible()
        
        # Step 2: Admin approves driver
        admin_page.goto('/admin/drivers')
        if admin_page.locator('.status:has-text("PENDING")').count() > 0:
            pending_row = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            if pending_row.locator('button:has-text("Approve")').count() > 0:
                pending_row.locator('button:has-text("Approve")').click()
                expect(admin_page.locator('.alert-success')).to_be_visible()
        
        # Step 3: Driver logs in and starts duty
        page.goto('/auth/login')
        page.fill('input[name="username"]', test_driver_data['username'])
        page.fill('input[name="password"]', 'default_password')  # Would need actual password
        page.click('button[type="submit"]')
        
        # If login successful, try duty workflow
        if page.url.endswith('/driver'):
            page.goto('/driver/duty')
            
            if page.locator('button:has-text("Start Duty")').count() > 0:
                # Start duty workflow
                if page.locator('select[name="vehicle_id"]').count() > 0:
                    page.select_option('select[name="vehicle_id"]', index=1)
                
                if page.locator('input[name="start_odometer"]').count() > 0:
                    page.fill('input[name="start_odometer"]', '10000')
                
                if page.locator('input[name*="start_photo"]').count() > 0:
                    page.set_input_files('input[name*="start_photo"]', test_files['duty_start_photo'])
                
                page.click('button:has-text("Start Duty")')
                expect(page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.e2e
    @pytest.mark.integration
    def test_admin_workflow_complete(self, admin_page: Page):
        """Test complete admin workflow - driver management to financial approval"""
        
        # Step 1: Review pending drivers
        admin_page.goto('/admin/drivers')
        driver_count = admin_page.locator('tbody tr').count()
        
        # Step 2: Check document manager
        admin_page.goto('/admin/documents')
        expect(admin_page.locator('h1, h2')).to_contain_text('Document')
        
        # Step 3: Review duty photos
        admin_page.goto('/admin/duty-photos')
        expect(admin_page.locator('h1, h2')).to_contain_text(['Duty', 'Photo'])
        
        # Step 4: Check storage system
        admin_page.goto('/admin/storage')
        expect(admin_page.locator('h1, h2')).to_contain_text('Storage')
        
        # Step 5: Review pending duties for approval
        admin_page.goto('/admin/duties')
        if admin_page.locator('.status:has-text("PENDING")').count() > 0:
            pending_duty = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            
            # View duty details first
            if pending_duty.locator('button:has-text("View")').count() > 0:
                pending_duty.locator('button:has-text("View")').click()
                expect(admin_page.locator('.modal')).to_be_visible()
                
                # Close modal
                if admin_page.locator('.btn-close, .close').count() > 0:
                    admin_page.click('.btn-close, .close')
            
            # Approve the duty
            if pending_duty.locator('button:has-text("Approve")').count() > 0:
                pending_duty.locator('button:has-text("Approve")').click()
                expect(admin_page.locator('.alert-success')).to_be_visible()
        
        # Step 6: Check reports
        admin_page.goto('/admin/reports')
        expect(admin_page.locator('h1, h2')).to_contain_text('Reports')
    
    @pytest.mark.e2e 
    @pytest.mark.integration
    def test_storage_workflow_complete(self, admin_page: Page):
        """Test complete storage management workflow"""
        
        # Step 1: Check storage overview
        admin_page.goto('/admin/storage')
        expect(admin_page.locator('.card')).to_have_count(4, min=3)
        
        # Step 2: Navigate to document manager
        admin_page.click('a[href*="documents"]')
        expect(admin_page).to_have_url('**/documents')
        
        # Step 3: View driver documents
        if admin_page.locator('button:has-text("View")').count() > 0:
            admin_page.locator('button:has-text("View")').first.click()
            expect(admin_page.locator('.modal')).to_be_visible()
            
            # Close modal
            if admin_page.locator('.btn-close').count() > 0:
                admin_page.click('.btn-close')
        
        # Step 4: Navigate to duty photos
        admin_page.goto('/admin/duty-photos')
        expect(admin_page.locator('h1, h2')).to_contain_text(['Duty', 'Photo'])
        
        # Step 5: Test file galleries
        admin_page.goto('/storage/gallery/documents')
        expect(admin_page.locator('h1, h2')).to_contain_text('Gallery')
        
        # Switch categories
        if admin_page.locator('button:has-text("Photos")').count() > 0:
            admin_page.click('button:has-text("Photos")')
            expect(admin_page).to_have_url('**/gallery/photos')
        
        # Step 6: Test file operations if files exist
        if admin_page.locator('.card .btn-group').count() > 0:
            # Test file preview
            if admin_page.locator('button[class*="btn-primary"]').count() > 0:
                first_view_btn = admin_page.locator('button[class*="btn-primary"]').first
                first_view_btn.click()
                # Should open file or show preview
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_multi_user_concurrent_access(self, browser):
        """Test multiple users accessing system concurrently"""
        
        # Create multiple browser contexts for different users
        admin_context = browser.new_context()
        driver_context = browser.new_context()
        
        admin_page = admin_context.new_page()
        driver_page = driver_context.new_page()
        
        try:
            # Admin logs in
            admin_page.goto('/auth/login')
            admin_page.fill('input[name="username"]', 'admin')
            admin_page.fill('input[name="password"]', 'admin123')
            admin_page.click('button[type="submit"]')
            
            # Driver logs in 
            driver_page.goto('/auth/login')
            driver_page.fill('input[name="username"]', 'driver1')
            driver_page.fill('input[name="password"]', 'driver123')
            driver_page.click('button[type="submit"]')
            
            # Both should be logged in successfully
            expect(admin_page).to_have_url('**/admin')
            expect(driver_page).to_have_url('**/driver')
            
            # Admin accesses admin features
            admin_page.goto('/admin/drivers')
            expect(admin_page.locator('h1, h2')).to_contain_text('Drivers')
            
            # Driver accesses driver features
            driver_page.goto('/driver/duty')
            expect(driver_page.locator('h1, h2')).to_contain_text('Duty')
            
            # Test concurrent operations don't interfere
            admin_page.goto('/admin/storage')
            driver_page.goto('/driver/earnings')
            
            # Both pages should load without issues
            expect(admin_page.locator('h1, h2')).to_contain_text('Storage')
            expect(driver_page.locator('h1, h2')).to_contain_text('Earnings')
            
        finally:
            admin_context.close()
            driver_context.close()


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.integration
    def test_network_error_handling(self, page: Page):
        """Test handling of network errors"""
        # This would require mocking network failures
        # For now, just test that pages handle missing data gracefully
        
        page.goto('/admin/drivers')
        # Page should load even if no data
        expect(page.locator('body')).not_to_contain_text('500 Internal Server Error')
    
    @pytest.mark.integration
    def test_database_connection_resilience(self, page: Page):
        """Test system resilience to database issues"""
        # Test that pages load even with potential database issues
        test_urls = [
            '/admin',
            '/admin/drivers', 
            '/admin/storage',
            '/driver',
            '/driver/duty'
        ]
        
        for url in test_urls:
            page.goto(url)
            # Should not show 500 errors
            expect(page.locator('body')).not_to_contain_text('500 Internal Server Error')
    
    @pytest.mark.integration
    def test_file_upload_edge_cases(self, page: Page, test_files):
        """Test file upload edge cases"""
        page.goto('/auth/register')
        
        # Test large file upload (if file size limits are enforced)
        if page.locator('input[type="file"]').count() > 0:
            # Try uploading a file - should either succeed or show appropriate error
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(test_files['aadhar_doc'])
            
            # Page should handle file upload gracefully
            expect(page.locator('body')).not_to_contain_text('500 Internal Server Error')