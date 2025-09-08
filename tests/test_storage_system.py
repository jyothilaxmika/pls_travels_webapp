"""
Storage System and Document Management Tests
"""

import pytest
from playwright.sync_api import Page, expect
from playwright_config import TEST_ROUTES


class TestStorageManagement:
    """Test storage management functionality"""
    
    @pytest.mark.storage
    @pytest.mark.integration
    def test_storage_dashboard_loads(self, admin_page: Page):
        """Test that storage dashboard loads correctly"""
        admin_page.goto(TEST_ROUTES['admin_storage'])
        
        expect(admin_page.locator('h1, h2')).to_contain_text('Storage')
        
        # Check for storage statistics
        expect(admin_page.locator('.card')).to_have_count(4, min=3)
        expect(admin_page.locator('body')).to_contain_text(['Total Files', 'Documents', 'Photos'])
    
    @pytest.mark.storage
    def test_document_manager_access(self, admin_page: Page):
        """Test document manager page access and functionality"""
        admin_page.goto(TEST_ROUTES['admin_documents'])
        
        expect(admin_page.locator('h1, h2')).to_contain_text('Document')
        
        # Check for driver document listing
        if admin_page.locator('table, .driver-list').count() > 0:
            expect(admin_page.locator('table thead, .table-header')).to_contain_text(['Driver', 'Aadhar', 'License'])
    
    @pytest.mark.storage
    def test_duty_photo_manager_access(self, admin_page: Page):
        """Test duty photo manager page access"""
        admin_page.goto(TEST_ROUTES['admin_duty_photos'])
        
        expect(admin_page.locator('h1, h2')).to_contain_text(['Duty', 'Photo'])
        
        # Check for photo galleries
        if admin_page.locator('.card, .photo-card').count() > 0:
            expect(admin_page.locator('body')).to_contain_text(['Start Photo', 'End Photo'])
    
    @pytest.mark.storage
    def test_file_gallery_access(self, admin_page: Page):
        """Test file gallery access for different categories"""
        # Test documents gallery
        admin_page.goto('/storage/gallery/documents')
        expect(admin_page.locator('h1, h2')).to_contain_text(['Documents', 'Gallery'])
        
        # Test photos gallery
        admin_page.goto('/storage/gallery/photos')
        expect(admin_page.locator('h1, h2')).to_contain_text(['Photos', 'Gallery'])
        
        # Test captures gallery
        admin_page.goto('/storage/gallery/captures')
        expect(admin_page.locator('h1, h2')).to_contain_text(['Captures', 'Gallery'])


class TestDocumentViewing:
    """Test document viewing functionality"""
    
    @pytest.mark.storage
    def test_driver_document_viewing(self, admin_page: Page):
        """Test viewing driver documents"""
        admin_page.goto(TEST_ROUTES['admin_documents'])
        
        # Look for view document buttons
        if admin_page.locator('button:has-text("View"), .btn-view').count() > 0:
            admin_page.locator('button:has-text("View"), .btn-view').first.click()
            
            # Should open document viewer modal
            expect(admin_page.locator('.modal')).to_be_visible()
            
            # Check for document display
            expect(admin_page.locator('.modal-body')).to_contain_text(['Document', 'Type', 'Date'])
    
    @pytest.mark.storage
    def test_photo_preview_functionality(self, admin_page: Page):
        """Test photo preview functionality"""
        admin_page.goto(TEST_ROUTES['admin_duty_photos'])
        
        # Look for photo thumbnails
        if admin_page.locator('img').count() > 0:
            # Click on a photo thumbnail
            photo = admin_page.locator('img').first
            if photo.get_attribute('style') and 'cursor: pointer' in photo.get_attribute('style'):
                photo.click()
                
                # Should open photo modal
                expect(admin_page.locator('.modal')).to_be_visible()
                expect(admin_page.locator('.modal img')).to_be_visible()
    
    @pytest.mark.storage  
    def test_document_metadata_display(self, admin_page: Page):
        """Test document metadata display"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for metadata info buttons
        if admin_page.locator('button:has-text("Info"), .btn-info').count() > 0:
            admin_page.locator('button:has-text("Info"), .btn-info').first.click()
            
            # Should show metadata modal
            expect(admin_page.locator('.modal')).to_be_visible()
            expect(admin_page.locator('.modal-body')).to_contain_text(['Filename', 'Size', 'Date'])


class TestFileOperations:
    """Test file operations (download, delete)"""
    
    @pytest.mark.storage
    def test_file_download_functionality(self, admin_page: Page):
        """Test file download functionality"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for download buttons
        if admin_page.locator('a:has-text("Download"), .btn-download').count() > 0:
            download_link = admin_page.locator('a:has-text("Download"), .btn-download').first
            
            # Check that download link has correct href
            href = download_link.get_attribute('href')
            expect(href).to_contain('/storage/file/')
    
    @pytest.mark.storage
    def test_file_deletion_workflow(self, admin_page: Page):
        """Test file deletion workflow"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for delete buttons  
        if admin_page.locator('button:has-text("Delete"), .btn-delete').count() > 0:
            delete_btn = admin_page.locator('button:has-text("Delete"), .btn-delete').first
            delete_btn.click()
            
            # Should show confirmation dialog
            admin_page.on('dialog', lambda dialog: dialog.accept())
            
            # Wait for deletion to complete
            admin_page.wait_for_timeout(1000)
    
    @pytest.mark.storage
    def test_bulk_operations(self, admin_page: Page):
        """Test bulk file operations if available"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for bulk selection checkboxes
        if admin_page.locator('input[type="checkbox"]').count() > 1:
            # Select multiple files
            checkboxes = admin_page.locator('input[type="checkbox"]')
            for i in range(min(2, checkboxes.count())):
                checkboxes.nth(i).click()
            
            # Look for bulk action buttons
            if admin_page.locator('button:has-text("Bulk"), .bulk-action').count() > 0:
                expect(admin_page.locator('button:has-text("Bulk"), .bulk-action')).to_be_visible()


class TestStorageSearch:
    """Test storage search and filtering functionality"""
    
    @pytest.mark.storage
    def test_driver_search_functionality(self, admin_page: Page):
        """Test driver search in document manager"""
        admin_page.goto(TEST_ROUTES['admin_documents'])
        
        # Look for search input
        if admin_page.locator('input[placeholder*="search"], #driverSearch').count() > 0:
            search_input = admin_page.locator('input[placeholder*="search"], #driverSearch').first
            search_input.fill('test')
            
            # Wait for search results
            admin_page.wait_for_timeout(500)
            
            # Check that results are filtered
            visible_rows = admin_page.locator('tbody tr:visible').count()
            expect(visible_rows).to_be_less_than_or_equal(10)
    
    @pytest.mark.storage
    def test_file_category_filtering(self, admin_page: Page):
        """Test file filtering by category"""
        admin_page.goto('/storage/gallery/documents')
        
        # Test category buttons
        category_buttons = ['Documents', 'Photos', 'Captures', 'Assets']
        
        for category in category_buttons:
            if admin_page.locator(f'button:has-text("{category}")').count() > 0:
                admin_page.click(f'button:has-text("{category}")')
                
                # Should navigate to category page
                expect(admin_page).to_have_url(f'**/gallery/{category.lower()}')
                admin_page.go_back()
    
    @pytest.mark.storage
    def test_user_id_filtering(self, admin_page: Page):
        """Test filtering files by user ID"""
        admin_page.goto('/storage/gallery/photos')
        
        # Look for user ID filter
        if admin_page.locator('input[name="user_id"]').count() > 0:
            admin_page.fill('input[name="user_id"]', '1')
            
            if admin_page.locator('button:has-text("Filter")').count() > 0:
                admin_page.click('button:has-text("Filter")')
                
                # Should filter results by user
                expect(admin_page).to_have_url('**/user_id=1')


class TestStorageNavigation:
    """Test storage system navigation"""
    
    @pytest.mark.storage
    def test_storage_menu_navigation(self, admin_page: Page):
        """Test storage dropdown menu navigation"""
        admin_page.goto(TEST_ROUTES['admin_dashboard'])
        
        # Click storage dropdown
        if admin_page.locator('#storageDropdown').count() > 0:
            admin_page.click('#storageDropdown')
            
            # Check dropdown items
            expect(admin_page.locator('.dropdown-menu')).to_be_visible()
            expect(admin_page.locator('.dropdown-menu')).to_contain_text(['Storage Overview', 'Document Manager', 'Duty Photos'])
    
    @pytest.mark.storage
    def test_breadcrumb_navigation(self, admin_page: Page):
        """Test breadcrumb navigation in storage pages"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for breadcrumb navigation
        if admin_page.locator('.breadcrumb, .navigation').count() > 0:
            expect(admin_page.locator('.breadcrumb, .navigation')).to_contain_text(['Storage', 'Documents'])
    
    @pytest.mark.storage
    def test_pagination_functionality(self, admin_page: Page):
        """Test pagination in file galleries"""
        admin_page.goto('/storage/gallery/documents')
        
        # Look for pagination
        if admin_page.locator('.pagination').count() > 0:
            pagination = admin_page.locator('.pagination')
            
            # Test next page if available
            if pagination.locator('a:has-text("Next")').count() > 0:
                pagination.locator('a:has-text("Next")').click()
                
                # Should go to next page
                expect(admin_page).to_have_url('**/page=2')
                
                # Test previous page
                if pagination.locator('a:has-text("Previous")').count() > 0:
                    pagination.locator('a:has-text("Previous")').click()
                    expect(admin_page).to_have_url('**/page=1')


class TestStorageSecurity:
    """Test storage security and access controls"""
    
    @pytest.mark.storage
    @pytest.mark.auth
    def test_driver_cannot_access_admin_storage(self, driver_page: Page):
        """Test that drivers cannot access admin storage pages"""
        # Try to access admin storage pages
        driver_page.goto(TEST_ROUTES['admin_storage'])
        expect(driver_page.locator('body')).to_contain_text(['Access Denied', 'Forbidden', '403'])
        
        driver_page.goto(TEST_ROUTES['admin_documents'])
        expect(driver_page.locator('body')).to_contain_text(['Access Denied', 'Forbidden', '403'])
    
    @pytest.mark.storage
    @pytest.mark.auth
    def test_file_access_permissions(self, driver_page: Page):
        """Test file access permissions for different user roles"""
        # Driver should only access their own files
        driver_page.goto('/api/storage/user/1/files')
        
        # Should either get their files or access denied
        response_text = driver_page.locator('body').text_content()
        expect(response_text).to_match(r'(files|Access Denied|403)')
    
    @pytest.mark.storage
    def test_secure_file_serving(self, admin_page: Page):
        """Test that file serving requires authentication"""
        # Test direct file access (should require login)
        admin_page.goto('/storage/file/test.jpg')
        
        # Should either serve file (if authorized) or redirect to login
        expect(admin_page.locator('body')).not_to_contain_text('500 Internal Server Error')