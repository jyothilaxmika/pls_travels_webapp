"""
Fallback Test Suite for PLS Travels
===================================

This alternative test suite works in environments where full browser
automation isn't available (like Replit). It uses HTTP requests and
basic validation to test website functionality.

Usage: pytest -v fallback_tests.py
"""

import requests
import pytest
import time
from urllib.parse import urljoin
import re


class TestPLSTravelsHTTP:
    """HTTP-based tests for PLS Travels website."""
    
    BASE_URL = "https://plstravels.com"
    
    def test_website_is_accessible(self):
        """Test that the website responds to HTTP requests."""
        print("🌐 Testing website accessibility...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        
        assert response.status_code == 200, f"Website returned status {response.status_code}"
        assert len(response.content) > 1000, "Response content too small - site may not be loading properly"
        
        print(f"  ✅ Status: {response.status_code}")
        print(f"  ✅ Content length: {len(response.content)} bytes")
        
    def test_page_contains_travel_content(self):
        """Test that the page contains travel-related content."""
        print("🧳 Testing travel content presence...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text.lower()
        
        # Look for travel-related keywords
        travel_keywords = ['travel', 'pls', 'book', 'trip', 'journey', 'transport', 'cab', 'taxi', 'ride']
        found_keywords = [keyword for keyword in travel_keywords if keyword in content]
        
        assert len(found_keywords) >= 2, f"Expected travel keywords not found. Found: {found_keywords}"
        
        print(f"  ✅ Found travel keywords: {found_keywords}")
        
    def test_basic_html_structure(self):
        """Test that the page has basic HTML structure."""
        print("🏗️ Testing HTML structure...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text.lower()
        
        # Check for essential HTML elements
        required_tags = ['<html', '<head', '<body', '</html>']
        missing_tags = [tag for tag in required_tags if tag not in content]
        
        assert len(missing_tags) == 0, f"Missing HTML tags: {missing_tags}"
        
        # Check for common website elements
        common_elements = ['<title', '<nav', '<footer', '<form', '<a href']
        found_elements = [element for element in common_elements if element in content]
        
        assert len(found_elements) >= 3, f"Expected common elements not found. Found: {found_elements}"
        
        print(f"  ✅ HTML structure valid")
        print(f"  ✅ Found elements: {found_elements}")
        
    def test_response_performance(self):
        """Test that the website responds within acceptable time."""
        print("⚡ Testing response performance...")
        
        start_time = time.time()
        response = requests.get(self.BASE_URL, timeout=30)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 10, f"Response too slow: {response_time:.2f}s"
        
        print(f"  ✅ Response time: {response_time:.2f} seconds")
        
    def test_contact_information_present(self):
        """Test that contact information is present on the site."""
        print("📞 Testing contact information...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text
        
        # Look for contact patterns
        phone_pattern = r'\+?\d{2,4}[-\s]?\d{10,}'
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        phones_found = re.findall(phone_pattern, content)
        emails_found = re.findall(email_pattern, content)
        
        contact_keywords = ['contact', 'phone', 'email', 'address', 'call', 'reach']
        keyword_count = sum(1 for keyword in contact_keywords if keyword in content.lower())
        
        # At least some contact method should be present
        contact_score = len(phones_found) + len(emails_found) + min(keyword_count, 3)
        assert contact_score >= 2, f"Insufficient contact information found. Score: {contact_score}"
        
        print(f"  ✅ Contact information found - Phones: {len(phones_found)}, Emails: {len(emails_found)}")
        
    def test_meta_tags_present(self):
        """Test that important meta tags are present."""
        print("🏷️ Testing meta tags...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text.lower()
        
        # Check for important meta tags
        meta_checks = {
            'title': '<title' in content,
            'description': 'name="description"' in content or 'property="og:description"' in content,
            'viewport': 'name="viewport"' in content,
            'charset': 'charset=' in content
        }
        
        present_tags = [tag for tag, present in meta_checks.items() if present]
        
        assert len(present_tags) >= 2, f"Important meta tags missing. Present: {present_tags}"
        
        print(f"  ✅ Meta tags present: {present_tags}")
        
    def test_external_resources_loading(self):
        """Test that external resources (CSS, JS) are referenced."""
        print("📦 Testing external resources...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text.lower()
        
        # Look for CSS and JS references
        css_present = '.css' in content or '<style' in content
        js_present = '.js' in content or '<script' in content
        
        resources_found = []
        if css_present:
            resources_found.append('CSS')
        if js_present:
            resources_found.append('JavaScript')
            
        assert len(resources_found) >= 1, f"No CSS or JS resources found: {resources_found}"
        
        print(f"  ✅ Resources found: {resources_found}")
        
    def test_forms_present(self):
        """Test that forms are present on the website."""
        print("📝 Testing forms presence...")
        
        response = requests.get(self.BASE_URL, timeout=30)
        content = response.text.lower()
        
        # Look for form elements
        form_elements = ['<form', '<input', '<button', '<select', '<textarea']
        found_elements = [element for element in form_elements if element in content]
        
        assert len(found_elements) >= 2, f"Insufficient form elements. Found: {found_elements}"
        
        # Look for common form types
        form_indicators = ['submit', 'search', 'contact', 'book', 'login']
        found_indicators = [indicator for indicator in form_indicators if indicator in content]
        
        print(f"  ✅ Form elements found: {found_elements}")
        print(f"  ✅ Form types indicated: {found_indicators}")


# Additional utility functions for manual testing
def quick_site_check(url="https://plstravels.com"):
    """Quick manual check of site status."""
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Site Status: {response.status_code}")
        print(f"✅ Response Time: {response.elapsed.total_seconds():.2f}s")
        print(f"✅ Content Length: {len(response.content)} bytes")
        return True
    except Exception as e:
        print(f"❌ Site Check Failed: {e}")
        return False


if __name__ == "__main__":
    print("PLS Travels HTTP Test Suite")
    print("=" * 50)
    
    # Quick check
    if quick_site_check():
        print("\n🚀 Run full tests with: pytest -v fallback_tests.py")
    else:
        print("\n⚠️ Site may be down or unreachable")