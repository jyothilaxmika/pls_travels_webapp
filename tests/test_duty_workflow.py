"""
Duty Start/End Workflow Tests
"""

import pytest
from playwright.sync_api import Page, expect
from playwright_config import TEST_ROUTES


class TestDutyWorkflow:
    """Test complete duty start/end workflow"""
    
    @pytest.mark.workflow
    @pytest.mark.integration
    def test_complete_duty_cycle(self, driver_page: Page, test_files):
        """Test complete duty cycle from start to end"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        page.wait_for_load_state('networkidle')
        
        # Check if we can start a duty
        if driver_page.locator('button:has-text("Start Duty")').count() > 0:
            # Fill duty start form
            if driver_page.locator('select[name="vehicle_id"]').count() > 0:
                # Select first available vehicle
                driver_page.select_option('select[name="vehicle_id"]', index=1)
            
            if driver_page.locator('select[name="duty_scheme_id"]').count() > 0:
                # Select first available duty scheme
                driver_page.select_option('select[name="duty_scheme_id"]', index=1)
            
            if driver_page.locator('input[name="start_odometer"]').count() > 0:
                driver_page.fill('input[name="start_odometer"]', '12000')
            
            # Upload start photo
            if driver_page.locator('input[name*="start_photo"]').count() > 0:
                driver_page.set_input_files('input[name*="start_photo"]', test_files['duty_start_photo'])
            
            # Start the duty
            driver_page.click('button:has-text("Start Duty")')
            
            # Verify duty started
            expect(driver_page.locator('.alert-success')).to_be_visible()
            expect(driver_page.locator('body')).to_contain_text(['Active', 'Started', 'duty'])
            
            # Now test ending the duty
            if driver_page.locator('button:has-text("End Duty")').count() > 0:
                # Fill duty end form
                if driver_page.locator('input[name="end_odometer"]').count() > 0:
                    driver_page.fill('input[name="end_odometer"]', '12050')
                
                if driver_page.locator('input[name="trip_count"]').count() > 0:
                    driver_page.fill('input[name="trip_count"]', '5')
                
                if driver_page.locator('input[name="cash_collected"]').count() > 0:
                    driver_page.fill('input[name="cash_collected"]', '500.00')
                
                # Upload end photo
                if driver_page.locator('input[name*="end_photo"]').count() > 0:
                    driver_page.set_input_files('input[name*="end_photo"]', test_files['duty_end_photo'])
                
                # End the duty
                driver_page.click('button:has-text("End Duty")')
                
                # Verify duty ended
                expect(driver_page.locator('.alert-success')).to_be_visible()
                expect(driver_page.locator('body')).to_contain_text(['Completed', 'Ended', 'Pending'])
    
    @pytest.mark.workflow
    def test_duty_start_validation(self, driver_page: Page):
        """Test validation during duty start"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        if driver_page.locator('button:has-text("Start Duty")').count() > 0:
            # Try to start duty without required fields
            driver_page.click('button:has-text("Start Duty")')
            
            # Should see validation errors
            expect(driver_page.locator('.alert-danger, .error-message')).to_be_visible()
            expect(driver_page.locator('body')).to_contain_text(['required', 'select', 'enter'])
    
    @pytest.mark.workflow 
    def test_duty_end_validation(self, driver_page: Page):
        """Test validation during duty end"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        # Only test if we have an active duty to end
        if driver_page.locator('button:has-text("End Duty")').count() > 0:
            # Try to end duty without required fields
            driver_page.click('button:has-text("End Duty")')
            
            # Should see validation errors
            expect(driver_page.locator('.alert-danger, .error-message')).to_be_visible()
            expect(driver_page.locator('body')).to_contain_text(['required', 'enter'])
    
    @pytest.mark.workflow
    def test_odometer_reading_validation(self, driver_page: Page):
        """Test odometer reading validation"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        # Test with invalid odometer readings
        if driver_page.locator('input[name="start_odometer"]').count() > 0:
            # Test negative reading
            driver_page.fill('input[name="start_odometer"]', '-100')
            driver_page.click('button:has-text("Start Duty")')
            expect(driver_page.locator('.alert-danger')).to_be_visible()
            
            # Test invalid format
            driver_page.fill('input[name="start_odometer"]', 'abc')
            driver_page.click('button:has-text("Start Duty")')
            expect(driver_page.locator('.alert-danger')).to_be_visible()


class TestDutyPhotoCapture:
    """Test duty photo capture functionality"""
    
    @pytest.mark.workflow
    def test_duty_start_photo_upload(self, driver_page: Page, test_files):
        """Test duty start photo upload"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        if driver_page.locator('input[name*="start_photo"]').count() > 0:
            driver_page.set_input_files('input[name*="start_photo"]', test_files['duty_start_photo'])
            
            # Check if preview is shown
            if driver_page.locator('.photo-preview, .image-preview').count() > 0:
                expect(driver_page.locator('.photo-preview, .image-preview')).to_be_visible()
    
    @pytest.mark.workflow
    def test_duty_end_photo_upload(self, driver_page: Page, test_files):
        """Test duty end photo upload"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        if driver_page.locator('input[name*="end_photo"]').count() > 0:
            driver_page.set_input_files('input[name*="end_photo"]', test_files['duty_end_photo'])
            
            # Check if preview is shown
            if driver_page.locator('.photo-preview, .image-preview').count() > 0:
                expect(driver_page.locator('.photo-preview, .image-preview')).to_be_visible()
    
    @pytest.mark.workflow
    def test_camera_capture_interface(self, driver_page: Page):
        """Test camera capture interface"""
        driver_page.goto(TEST_ROUTES['driver_duty'])
        
        # Look for camera capture buttons
        if driver_page.locator('button:has-text("Camera"), .camera-btn').count() > 0:
            camera_btn = driver_page.locator('button:has-text("Camera"), .camera-btn').first
            camera_btn.click()
            
            # Check if camera interface opens
            expect(driver_page.locator('.camera-modal, #cameraModal')).to_be_visible()


class TestDutyAdminApproval:
    """Test duty approval workflow from admin side"""
    
    @pytest.mark.workflow
    @pytest.mark.integration
    def test_admin_duty_approval(self, admin_page: Page):
        """Test admin approving pending duties"""
        admin_page.goto('/admin/duties')
        page.wait_for_load_state('networkidle')
        
        # Look for pending duties
        if admin_page.locator('tr:has(.status:has-text("PENDING"))').count() > 0:
            pending_duty_row = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            
            # Click approve button
            if pending_duty_row.locator('button:has-text("Approve")').count() > 0:
                pending_duty_row.locator('button:has-text("Approve")').click()
                
                # Confirm approval if modal appears
                if admin_page.locator('button:has-text("Confirm")').count() > 0:
                    admin_page.click('button:has-text("Confirm")')
                
                # Verify approval
                expect(admin_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow
    def test_admin_duty_rejection(self, admin_page: Page):
        """Test admin rejecting duties"""
        admin_page.goto('/admin/duties')
        
        if admin_page.locator('tr:has(.status:has-text("PENDING"))').count() > 0:
            pending_duty_row = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            
            # Click reject button
            if pending_duty_row.locator('button:has-text("Reject")').count() > 0:
                pending_duty_row.locator('button:has-text("Reject")').click()
                
                # Add rejection reason if required
                if admin_page.locator('textarea[name="rejection_reason"]').count() > 0:
                    admin_page.fill('textarea[name="rejection_reason"]', 'Test rejection reason')
                
                # Confirm rejection
                if admin_page.locator('button:has-text("Confirm")').count() > 0:
                    admin_page.click('button:has-text("Confirm")')
                
                expect(admin_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow 
    def test_admin_view_duty_details(self, admin_page: Page):
        """Test admin viewing duty details"""
        admin_page.goto('/admin/duties')
        
        if admin_page.locator('tbody tr').count() > 0:
            # Click view button or duty row
            if admin_page.locator('button:has-text("View"), .btn-view').count() > 0:
                admin_page.locator('button:has-text("View"), .btn-view').first.click()
                
                # Should open duty details modal or page
                expect(admin_page.locator('.modal, .duty-details')).to_be_visible()
                
                # Check for duty information
                expect(admin_page.locator('body')).to_contain_text(['Duty Details', 'Distance', 'Revenue'])


class TestDutyEarningsCalculation:
    """Test duty earnings calculation"""
    
    @pytest.mark.workflow
    @pytest.mark.integration  
    def test_earnings_calculation_display(self, driver_page: Page):
        """Test that earnings are calculated and displayed correctly"""
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Check for earnings information
        expect(driver_page.locator('h1, h2')).to_contain_text('Earnings')
        
        # Look for earnings breakdown
        if driver_page.locator('.earnings-card, .earning-item').count() > 0:
            expect(driver_page.locator('body')).to_contain_text(['Total', 'Revenue', 'Deductions'])
    
    @pytest.mark.workflow
    def test_duty_financial_summary(self, driver_page: Page):
        """Test duty financial summary in earnings page"""
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Check for financial summary elements
        if driver_page.locator('.duty-list, .earning-list').count() > 0:
            expect(driver_page.locator('body')).to_contain_text(['Date', 'Amount', 'Distance'])
    
    @pytest.mark.workflow
    def test_earnings_filtering(self, driver_page: Page):
        """Test earnings filtering by date/period"""  
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Test date filters if available
        if driver_page.locator('input[type="date"]').count() > 0:
            driver_page.fill('input[type="date"]', '2024-01-01')
            
            if driver_page.locator('button:has-text("Filter")').count() > 0:
                driver_page.click('button:has-text("Filter")')
                # Page should reload with filtered results
                driver_page.wait_for_load_state('networkidle')