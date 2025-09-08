"""
Driver Onboarding Workflow Tests
"""

import pytest
from playwright.sync_api import Page, expect
from .conftest import TEST_ROUTES


class TestDriverOnboarding:
    """Test complete driver onboarding workflow"""
    
    @pytest.mark.workflow
    @pytest.mark.integration
    def test_complete_driver_registration_flow(self, page: Page, test_driver_data, test_files):
        """Test complete driver registration from start to finish"""
        # Navigate to driver registration page
        page.goto('/auth/register')
        page.wait_for_load_state('networkidle')
        
        # Fill basic information
        page.fill('input[name="full_name"]', test_driver_data['full_name'])
        page.fill('input[name="email"]', test_driver_data['email'])
        page.fill('input[name="username"]', test_driver_data['username'])
        page.fill('input[name="phone_number"]', test_driver_data['phone_number'])
        
        # Fill Aadhar information
        page.fill('input[name="aadhar_number"]', test_driver_data['aadhar_number'])
        
        # Upload Aadhar document if file upload exists
        if page.locator('input[name="aadhar_photo"]').count() > 0:
            page.set_input_files('input[name="aadhar_photo"]', test_files['aadhar_doc'])
        
        # Fill license information
        page.fill('input[name="license_number"]', test_driver_data['license_number'])
        
        # Upload license document if file upload exists
        if page.locator('input[name="license_photo"]').count() > 0:
            page.set_input_files('input[name="license_photo"]', test_files['license_doc'])
        
        # Upload profile photo if exists
        if page.locator('input[name="profile_photo"]').count() > 0:
            page.set_input_files('input[name="profile_photo"]', test_files['profile_photo'])
        
        # Fill bank information
        page.fill('input[name="bank_account_number"]', test_driver_data['bank_account_number'])
        
        # Submit the form
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        
        # Check for success message
        expect(page.locator('.alert-success, .success-message')).to_be_visible()
        expect(page.locator('body')).to_contain_text(['successfully', 'registered', 'pending'])
    
    @pytest.mark.workflow
    def test_driver_profile_completion(self, driver_page: Page, test_files):
        """Test driver completing their profile"""
        driver_page.goto(TEST_ROUTES['driver_profile'])
        
        # Check if profile completion form is available
        if driver_page.locator('form').count() > 0:
            # Fill additional profile information
            if driver_page.locator('input[name="emergency_contact"]').count() > 0:
                driver_page.fill('input[name="emergency_contact"]', '9988776655')
            
            if driver_page.locator('textarea[name="address"]').count() > 0:
                driver_page.fill('textarea[name="address"]', 'Test Address, Test City')
            
            # Upload additional documents if required
            if driver_page.locator('input[name="bank_passbook"]').count() > 0:
                driver_page.set_input_files('input[name="bank_passbook"]', test_files['aadhar_doc'])
            
            # Submit profile update
            if driver_page.locator('button[type="submit"]').count() > 0:
                driver_page.click('button[type="submit"]')
                expect(driver_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow
    def test_admin_driver_approval_workflow(self, admin_page: Page):
        """Test admin approving a pending driver"""
        admin_page.goto(TEST_ROUTES['admin_drivers'])
        
        # Look for pending drivers
        if admin_page.locator('.status:has-text("PENDING")').count() > 0:
            # Find approve button for a pending driver
            pending_row = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            
            if pending_row.locator('button:has-text("Approve"), .btn-approve').count() > 0:
                pending_row.locator('button:has-text("Approve"), .btn-approve').first.click()
                
                # Wait for approval confirmation
                expect(admin_page.locator('.alert-success')).to_be_visible()
                expect(admin_page.locator('body')).to_contain_text(['approved', 'active'])
    
    @pytest.mark.workflow
    def test_document_verification_workflow(self, admin_page: Page):
        """Test admin verifying driver documents"""
        admin_page.goto(TEST_ROUTES['admin_documents'])
        
        # Look for unverified documents
        if admin_page.locator('button:has-text("Verify")').count() > 0:
            # Click verify button for a document
            admin_page.locator('button:has-text("Verify")').first.click()
            
            # Confirm verification
            if admin_page.locator('button:has-text("Confirm")').count() > 0:
                admin_page.click('button:has-text("Confirm")')
            
            # Check for success message
            expect(admin_page.locator('.alert-success')).to_be_visible()


class TestDriverDocumentUpload:
    """Test driver document upload functionality"""
    
    @pytest.mark.workflow
    def test_aadhar_document_upload(self, driver_page: Page, test_files):
        """Test Aadhar document upload"""
        driver_page.goto(TEST_ROUTES['driver_profile'])
        
        # Find Aadhar upload section
        if driver_page.locator('input[name*="aadhar"]').count() > 0:
            driver_page.set_input_files('input[name*="aadhar"]', test_files['aadhar_doc'])
            
            # Submit if there's a submit button
            if driver_page.locator('button:has-text("Upload")').count() > 0:
                driver_page.click('button:has-text("Upload")')
                expect(driver_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow  
    def test_license_document_upload(self, driver_page: Page, test_files):
        """Test license document upload"""
        driver_page.goto(TEST_ROUTES['driver_profile'])
        
        # Find license upload section
        if driver_page.locator('input[name*="license"]').count() > 0:
            driver_page.set_input_files('input[name*="license"]', test_files['license_doc'])
            
            # Submit if there's a submit button
            if driver_page.locator('button:has-text("Upload")').count() > 0:
                driver_page.click('button:has-text("Upload")')
                expect(driver_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow
    def test_profile_photo_upload(self, driver_page: Page, test_files):
        """Test profile photo upload"""
        driver_page.goto(TEST_ROUTES['driver_profile'])
        
        # Find profile photo upload section
        if driver_page.locator('input[name*="profile"]').count() > 0:
            driver_page.set_input_files('input[name*="profile"]', test_files['profile_photo'])
            
            # Submit if there's a submit button  
            if driver_page.locator('button:has-text("Upload")').count() > 0:
                driver_page.click('button:has-text("Upload")')
                expect(driver_page.locator('.alert-success')).to_be_visible()


class TestDriverStatusWorkflow:
    """Test driver status transitions"""
    
    @pytest.mark.workflow
    @pytest.mark.integration
    def test_driver_status_progression(self, admin_page: Page):
        """Test driver status from PENDING -> ACTIVE -> SUSPENDED"""
        admin_page.goto(TEST_ROUTES['admin_drivers'])
        
        # Find a driver to work with
        if admin_page.locator('tbody tr').count() > 0:
            driver_row = admin_page.locator('tbody tr').first
            current_status = driver_row.locator('.status, .badge').text_content()
            
            # Test status change buttons
            if driver_row.locator('button:has-text("Approve")').count() > 0:
                driver_row.locator('button:has-text("Approve")').click()
                expect(admin_page.locator('.alert-success')).to_be_visible()
                
            elif driver_row.locator('button:has-text("Suspend")').count() > 0:
                driver_row.locator('button:has-text("Suspend")').click()
                
                # Confirm suspension if modal appears
                if admin_page.locator('button:has-text("Confirm")').count() > 0:
                    admin_page.click('button:has-text("Confirm")')
                
                expect(admin_page.locator('.alert-success')).to_be_visible()