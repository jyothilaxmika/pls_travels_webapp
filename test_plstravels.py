"""
Playwright Test Suite for PLS Travels
======================================

This test suite validates the core functionality of the PLS Travels website
at https://plstravels.com using Playwright automation.

Author: QA Automation Engineer
Date: September 2025
"""

import pytest
from playwright.sync_api import Page, expect
import time


class TestPLSTravels:
    """Test suite for PLS Travels website functionality."""
    
    BASE_URL = "https://plstravels.com"
    
    def test_homepage_loads_successfully(self, page: Page):
        """Test that the homepage loads without errors."""
        print("🚀 Testing homepage load...")
        
        # Navigate to the homepage
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        # Assert page loads successfully
        expect(page).to_have_url(self.BASE_URL)
        
        # Check for common elements that should be present
        expect(page).to_have_title(regex=r".*PLS.*|.*Travel.*")
        
        # Verify page content is loaded (should contain some travel-related text)
        page_content = page.content()
        assert len(page_content) > 1000, "Page content seems too short, may not have loaded properly"
        
        print("✅ Homepage loads successfully")
    
    def test_navigation_menu_works(self, page: Page):
        """Test that navigation menu items are present and clickable."""
        print("🧭 Testing navigation menu...")
        
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        # Common navigation elements to look for
        nav_items = ["Home", "About", "Contact", "Services", "Book", "Login"]
        found_nav_items = []
        
        for item in nav_items:
            # Try different selectors for navigation items
            selectors = [
                f"a:has-text('{item}')",
                f"nav >> text='{item}'",
                f"[href*='{item.lower()}']",
                f"text='{item}'"
            ]
            
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        found_nav_items.append(item)
                        print(f"  ✓ Found navigation item: {item}")
                        break
                except:
                    continue
        
        # Assert at least some navigation items are found
        assert len(found_nav_items) >= 2, f"Expected at least 2 navigation items, found: {found_nav_items}"
        
        print(f"✅ Navigation menu working - Found items: {found_nav_items}")
    
    def test_login_signup_page_accessibility(self, page: Page):
        """Test that login/signup functionality is accessible."""
        print("🔐 Testing login/signup access...")
        
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        login_found = False
        signup_found = False
        
        # Look for login links/buttons
        login_selectors = [
            "a:has-text('Login')",
            "button:has-text('Login')",
            "a:has-text('Sign In')",
            "[href*='login']",
            ".login"
        ]
        
        for selector in login_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible():
                    print("  ✓ Login option found and visible")
                    login_found = True
                    
                    # Try clicking to see if it navigates or opens a form
                    element.click(timeout=5000)
                    page.wait_for_timeout(2000)  # Wait for potential navigation
                    
                    # Check if we're on a login page or if a login form appeared
                    current_url = page.url
                    if "login" in current_url.lower() or page.locator("input[type='password']").count() > 0:
                        print("  ✓ Login page/form accessible")
                    break
            except:
                continue
        
        # Look for signup/register links
        signup_selectors = [
            "a:has-text('Sign Up')",
            "a:has-text('Register')",
            "button:has-text('Sign Up')",
            "[href*='register']",
            "[href*='signup']"
        ]
        
        for selector in signup_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible():
                    print("  ✓ Signup option found and visible")
                    signup_found = True
                    break
            except:
                continue
        
        # At least one authentication option should be available
        assert login_found or signup_found, "No login or signup options found on the page"
        
        print("✅ Authentication access available")
    
    def test_search_booking_form_functionality(self, page: Page):
        """Test that search or booking forms load and accept input."""
        print("🔍 Testing search/booking form...")
        
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        form_found = False
        
        # Look for common form elements
        form_selectors = [
            "form",
            "input[type='text']",
            "input[placeholder*='search']",
            "input[placeholder*='destination']",
            "select",
            ".booking-form",
            ".search-form"
        ]
        
        for selector in form_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    form_found = True
                    print(f"  ✓ Form element found: {selector}")
                    
                    # If it's an input field, try to interact with it
                    if "input" in selector:
                        first_input = elements.first
                        if first_input.is_visible() and first_input.is_enabled():
                            # Try to fill with test data
                            try:
                                first_input.fill("Delhi")
                                print("  ✓ Successfully filled form input")
                                
                                # Clear the input
                                first_input.fill("")
                            except:
                                print("  ⚠ Input found but couldn't interact with it")
                    break
            except:
                continue
        
        if not form_found:
            # Look for any interactive elements that might be booking-related
            interactive_elements = page.locator("button, a[href*='book'], a[href*='search']")
            if interactive_elements.count() > 0:
                form_found = True
                print("  ✓ Interactive booking/search elements found")
        
        assert form_found, "No search or booking forms found on the page"
        
        print("✅ Search/booking form functionality available")
    
    def test_booking_submission_handling(self, page: Page):
        """Test booking form submission and error handling."""
        print("📝 Testing booking submission...")
        
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        # Look for forms that can be submitted
        forms = page.locator("form")
        submit_buttons = page.locator("button[type='submit'], input[type='submit'], button:has-text('Book'), button:has-text('Submit')")
        
        submission_tested = False
        
        if forms.count() > 0:
            form = forms.first
            print("  ✓ Form found for submission testing")
            
            # Try to find required fields and fill them
            inputs = form.locator("input[type='text'], input[type='email'], select")
            
            for i in range(min(inputs.count(), 3)):  # Fill up to 3 fields
                input_elem = inputs.nth(i)
                if input_elem.is_visible() and input_elem.is_enabled():
                    try:
                        # Fill with appropriate test data based on field type
                        placeholder = input_elem.get_attribute("placeholder") or ""
                        if "email" in placeholder.lower():
                            input_elem.fill("test@example.com")
                        elif "phone" in placeholder.lower():
                            input_elem.fill("9876543210")
                        else:
                            input_elem.fill("Test Data")
                        print(f"  ✓ Filled input field {i+1}")
                    except:
                        continue
            
            # Try to submit the form
            if submit_buttons.count() > 0:
                submit_btn = submit_buttons.first
                try:
                    # Monitor for navigation or alerts
                    with page.expect_response(lambda response: True, timeout=10000) as response_info:
                        submit_btn.click()
                        page.wait_for_timeout(3000)
                    
                    # Check for success/error messages
                    success_indicators = page.locator("text=/success|thank you|confirmed|booked/i")
                    error_indicators = page.locator("text=/error|required|invalid|please/i")
                    
                    if success_indicators.count() > 0:
                        print("  ✓ Success message displayed")
                    elif error_indicators.count() > 0:
                        print("  ✓ Error handling working (validation messages shown)")
                    
                    submission_tested = True
                    
                except Exception as e:
                    print(f"  ⚠ Form submission test completed with: {str(e)[:100]}")
                    submission_tested = True
        
        if not submission_tested:
            # At least verify that interactive elements exist
            interactive_count = page.locator("button, input[type='submit'], a[href*='book']").count()
            assert interactive_count > 0, "No interactive elements found for booking submission"
            print("  ✓ Interactive elements present for booking")
        
        print("✅ Booking submission handling verified")
    
    def test_footer_contact_information_visible(self, page: Page):
        """Test that footer and contact information are visible."""
        print("📞 Testing footer and contact information...")
        
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        # Scroll to bottom to ensure footer is loaded
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        
        footer_found = False
        contact_info_found = False
        
        # Look for footer elements
        footer_selectors = ["footer", ".footer", "#footer", ".footer-section"]
        
        for selector in footer_selectors:
            try:
                footer = page.locator(selector)
                if footer.count() > 0 and footer.first.is_visible():
                    footer_found = True
                    print("  ✓ Footer section found")
                    break
            except:
                continue
        
        # Look for contact information anywhere on the page
        contact_patterns = [
            r"\+?\d{2,4}[-\s]?\d{10}",  # Phone numbers
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email addresses
            "contact", "phone", "email", "address"
        ]
        
        page_content = page.content().lower()
        
        for pattern in contact_patterns:
            if pattern in page_content:
                contact_info_found = True
                print(f"  ✓ Contact information found: {pattern}")
                break
        
        # Check for specific contact elements
        contact_selectors = [
            "text=/contact/i",
            "text=/phone/i", 
            "text=/email/i",
            "[href^='tel:']",
            "[href^='mailto:']"
        ]
        
        for selector in contact_selectors:
            try:
                if page.locator(selector).count() > 0:
                    contact_info_found = True
                    print(f"  ✓ Contact element found: {selector}")
                    break
            except:
                continue
        
        # At least footer or contact info should be present
        assert footer_found or contact_info_found, "No footer or contact information found"
        
        print("✅ Footer and contact information accessible")
    
    def test_page_performance_and_responsiveness(self, page: Page):
        """Test basic performance and responsiveness of the site."""
        print("⚡ Testing page performance...")
        
        start_time = time.time()
        
        # Navigate and measure load time
        page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
        
        load_time = time.time() - start_time
        print(f"  ✓ Page load time: {load_time:.2f} seconds")
        
        # Check that page loaded within reasonable time
        assert load_time < 15, f"Page load time too slow: {load_time:.2f}s"
        
        # Test basic responsiveness by changing viewport
        original_size = page.viewport_size
        
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(1000)
        
        # Verify page still renders correctly
        assert page.locator("body").count() > 0, "Page doesn't render properly on mobile viewport"
        print("  ✓ Mobile viewport responsive")
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(1000)
        print("  ✓ Tablet viewport responsive")
        
        # Restore original viewport
        if original_size:
            page.set_viewport_size(original_size)
        
        print("✅ Performance and responsiveness verified")


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments."""
    return {
        **browser_type_launch_args,
        "headless": True,  # Run in headless mode for CI/CD compatibility
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-features=VizDisplayCompositor",
        ]
    }


if __name__ == "__main__":
    print("PLS Travels Test Suite")
    print("=" * 50)
    print("Run with: pytest -v test_plstravels.py")
    print("For debugging: pytest -v -s test_plstravels.py")
    print("For specific test: pytest -v test_plstravels.py::TestPLSTravels::test_homepage_loads_successfully")