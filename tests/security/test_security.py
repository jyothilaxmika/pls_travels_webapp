"""
Security-focused tests for authentication, authorization, and input validation
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import jwt

from app import create_app, db
from models import User, DriverProfile, Branch
from services.security_service import SecurityService
from services.user_service import UserService


@pytest.fixture(scope='function')
def app():
    """Create application for security testing"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': True,  # Enable CSRF for security tests
        'JWT_SECRET_KEY': 'test_jwt_secret_for_security_testing'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for security tests"""
    return app.test_client()


class TestAuthenticationSecurity:
    """Test authentication security measures"""
    
    def test_password_hashing(self, app):
        """Test that passwords are properly hashed"""
        with app.app_context():
            branch = Branch(name='Security Branch', code='SB001', city='Security City')
            db.session.add(branch)
            db.session.commit()
            
            user = User(
                username='securityuser',
                email='security@example.com',
                full_name='Security User',
                role='DRIVER'
            )
            user.set_password('securepassword123')
            db.session.add(user)
            db.session.commit()
            
            # Password should not be stored in plain text
            assert user.password_hash != 'securepassword123'
            assert len(user.password_hash) > 50  # Should be a hash
            
            # But should verify correctly
            assert user.check_password('securepassword123') is True
            assert user.check_password('wrongpassword') is False
    
    def test_login_attempt_rate_limiting(self, app, client):
        """Test rate limiting on login attempts"""
        with app.app_context():
            # Create test user
            branch = Branch(name='Rate Limit Branch', code='RLB001', city='Rate City')
            db.session.add(branch)
            db.session.commit()
            
            user = User(
                username='ratelimituser',
                email='ratelimit@example.com',
                full_name='Rate Limit User',
                role='DRIVER'
            )
            user.set_password('correctpassword')
            db.session.add(user)
            db.session.commit()
            
            # Make multiple failed login attempts
            for i in range(6):  # Assuming rate limit is 5 attempts
                response = client.post('/auth/login', data={
                    'username': 'ratelimituser',
                    'password': 'wrongpassword'
                })
                
            # Next attempt should be rate limited
            response = client.post('/auth/login', data={
                'username': 'ratelimituser',
                'password': 'wrongpassword'
            })
            
            # Should return 429 Too Many Requests or similar
            assert response.status_code == 429 or 'rate limit' in response.get_data(as_text=True).lower()
    
    def test_session_security(self, app, client):
        """Test session security measures"""
        with app.app_context():
            # Create test user
            branch = Branch(name='Session Branch', code='SEB001', city='Session City')
            db.session.add(branch)
            db.session.commit()
            
            user = User(
                username='sessionuser',
                email='session@example.com',
                full_name='Session User',
                role='DRIVER'
            )
            user.set_password('sessionpass123')
            db.session.add(user)
            db.session.commit()
            
            # Login
            response = client.post('/auth/login', data={
                'username': 'sessionuser',
                'password': 'sessionpass123'
            }, follow_redirects=True)
            
            # Check session cookie security flags
            cookies = response.headers.getlist('Set-Cookie')
            session_cookie = [c for c in cookies if c.startswith('session=')]
            
            if session_cookie:
                cookie = session_cookie[0]
                assert 'HttpOnly' in cookie
                assert 'SameSite' in cookie
    
    def test_jwt_token_security(self, app):
        """Test JWT token generation and validation"""
        service = SecurityService()
        
        with app.app_context():
            # Create test payload
            payload = {
                'user_id': 123,
                'role': 'DRIVER',
                'exp': datetime.utcnow() + timedelta(hours=1)
            }
            
            # Generate token
            token = service.generate_jwt_token(payload)
            assert token is not None
            assert len(token) > 20
            
            # Validate token
            decoded = service.validate_jwt_token(token)
            assert decoded['success'] is True
            assert decoded['payload']['user_id'] == 123
            assert decoded['payload']['role'] == 'DRIVER'
            
            # Test expired token
            expired_payload = {
                'user_id': 123,
                'role': 'DRIVER',
                'exp': datetime.utcnow() - timedelta(hours=1)  # Already expired
            }
            
            expired_token = jwt.encode(expired_payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')
            expired_result = service.validate_jwt_token(expired_token)
            assert expired_result['success'] is False
            assert 'expired' in expired_result['error'].lower()


class TestAuthorizationSecurity:
    """Test role-based access control and authorization"""
    
    def test_role_based_access_control(self, app, client):
        """Test that users can only access resources for their role"""
        with app.app_context():
            # Create test users with different roles
            branch = Branch(name='RBAC Branch', code='RBAC001', city='RBAC City')
            db.session.add(branch)
            db.session.commit()
            
            admin_user = User(
                username='adminuser',
                email='admin@example.com',
                full_name='Admin User',
                role='ADMIN'
            )
            admin_user.set_password('adminpass123')
            
            driver_user = User(
                username='driveruser',
                email='driver@example.com',
                full_name='Driver User',
                role='DRIVER'
            )
            driver_user.set_password('driverpass123')
            
            db.session.add(admin_user)
            db.session.add(driver_user)
            db.session.commit()
            
            # Test driver accessing admin-only route
            with client.session_transaction() as sess:
                sess['_user_id'] = str(driver_user.id)
                sess['_fresh'] = True
            
            response = client.get('/admin/drivers')
            assert response.status_code == 403  # Forbidden
            
            # Test admin accessing admin route (should work)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)
                sess['_fresh'] = True
            
            response = client.get('/admin/drivers')
            assert response.status_code == 200  # Should work
    
    def test_branch_isolation(self, app):
        """Test that managers can only access their assigned branches"""
        with app.app_context():
            # Create branches
            branch1 = Branch(name='Branch 1', code='BR001', city='City 1')
            branch2 = Branch(name='Branch 2', code='BR002', city='City 2')
            db.session.add(branch1)
            db.session.add(branch2)
            db.session.commit()
            
            # Create manager for branch 1
            manager = User(
                username='manager1',
                email='manager1@example.com',
                full_name='Manager 1',
                role='MANAGER'
            )
            db.session.add(manager)
            db.session.commit()
            
            # Assign manager to branch 1 only
            from models import ManagerBranch
            manager_branch = ManagerBranch(manager_id=manager.id, branch_id=branch1.id)
            db.session.add(manager_branch)
            db.session.commit()
            
            # Test that manager can access branch 1 data
            service = UserService()
            accessible_branches = service.get_manager_accessible_branches(manager.id)
            
            branch_ids = [b.id for b in accessible_branches]
            assert branch1.id in branch_ids
            assert branch2.id not in branch_ids  # Should not have access to branch 2
    
    def test_driver_data_isolation(self, app):
        """Test that drivers can only access their own data"""
        with app.app_context():
            branch = Branch(name='Isolation Branch', code='IB001', city='Isolation City')
            db.session.add(branch)
            db.session.commit()
            
            # Create two drivers
            driver1 = User(
                username='driver1',
                email='driver1@example.com',
                full_name='Driver 1',
                role='DRIVER'
            )
            driver2 = User(
                username='driver2',
                email='driver2@example.com',
                full_name='Driver 2',
                role='DRIVER'
            )
            
            db.session.add(driver1)
            db.session.add(driver2)
            db.session.commit()
            
            # Create driver profiles
            profile1 = DriverProfile(
                user_id=driver1.id,
                branch_id=branch.id,
                aadhar_number='123456789012',
                license_number='DL12345678'
            )
            profile2 = DriverProfile(
                user_id=driver2.id,
                branch_id=branch.id,
                aadhar_number='123456789013',
                license_number='DL12345679'
            )
            
            db.session.add(profile1)
            db.session.add(profile2)
            db.session.commit()
            
            # Test that driver1 cannot access driver2's profile
            from services.driver_service import DriverService
            service = DriverService()
            
            # This should work - driver accessing own profile
            result1 = service.get_driver_profile(driver1.id, requesting_user_id=driver1.id)
            assert result1['success'] is True
            
            # This should fail - driver accessing another driver's profile
            result2 = service.get_driver_profile(driver2.id, requesting_user_id=driver1.id)
            assert result2['success'] is False
            assert 'access denied' in result2['error'].lower() or 'unauthorized' in result2['error'].lower()


class TestInputValidationSecurity:
    """Test input validation and sanitization"""
    
    def test_sql_injection_prevention(self, app):
        """Test SQL injection prevention"""
        service = SecurityService()
        
        # Test various SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for malicious_input in malicious_inputs:
            sanitized = service.sanitize_input(malicious_input)
            
            # Should not contain dangerous SQL keywords
            sanitized_lower = sanitized.lower()
            assert 'drop table' not in sanitized_lower
            assert 'insert into' not in sanitized_lower
            assert '--' not in sanitized
    
    def test_xss_prevention(self, app):
        """Test XSS prevention"""
        service = SecurityService()
        
        # Test various XSS attempts
        xss_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>"
        ]
        
        for xss_input in xss_inputs:
            sanitized = service.sanitize_input(xss_input)
            
            # Should not contain dangerous scripts
            assert '<script>' not in sanitized.lower()
            assert 'javascript:' not in sanitized.lower()
            assert 'onerror=' not in sanitized.lower()
    
    def test_file_upload_security(self, app):
        """Test file upload security validation"""
        service = SecurityService()
        
        # Test malicious file extensions
        malicious_files = [
            'script.php',
            'malware.exe',
            'virus.bat',
            'shell.asp',
            'backdoor.jsp'
        ]
        
        for filename in malicious_files:
            result = service.validate_file_extension(filename)
            assert result['is_valid'] is False
            assert 'not allowed' in result['error'].lower()
        
        # Test valid extensions
        valid_files = ['document.pdf', 'photo.jpg', 'image.png']
        
        for filename in valid_files:
            result = service.validate_file_extension(filename)
            assert result['is_valid'] is True
    
    def test_phone_number_validation(self, app):
        """Test phone number format validation"""
        service = SecurityService()
        
        # Test valid phone numbers
        valid_numbers = [
            '9999999999',
            '+919999999999',
            '09999999999'
        ]
        
        for number in valid_numbers:
            result = service.validate_phone_number(number)
            assert result['is_valid'] is True
        
        # Test invalid phone numbers
        invalid_numbers = [
            '123',  # Too short
            'abcdefghij',  # Non-numeric
            '12345678901234567890',  # Too long
            '+1234567890123456789'  # Invalid format
        ]
        
        for number in invalid_numbers:
            result = service.validate_phone_number(number)
            assert result['is_valid'] is False


class TestCSRFProtection:
    """Test CSRF protection measures"""
    
    def test_csrf_token_generation(self, app, client):
        """Test CSRF token generation and validation"""
        with app.app_context():
            response = client.get('/auth/login')
            
            # CSRF token should be present in the form
            assert b'csrf_token' in response.data or b'_token' in response.data
    
    def test_csrf_protection_on_forms(self, app, client):
        """Test CSRF protection on form submissions"""
        with app.app_context():
            # Try to submit form without CSRF token
            response = client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'testpass'
                # Missing CSRF token
            })
            
            # Should be rejected due to missing CSRF token
            # (Exact behavior depends on Flask-WTF configuration)
            assert response.status_code in [400, 403] or 'csrf' in response.get_data(as_text=True).lower()


class TestSecurityHeaders:
    """Test security headers in HTTP responses"""
    
    def test_security_headers_present(self, app, client):
        """Test that security headers are present in responses"""
        with app.app_context():
            response = client.get('/auth/login')
            
            # Check for security headers
            headers = dict(response.headers)
            
            assert 'X-Content-Type-Options' in headers
            assert headers['X-Content-Type-Options'] == 'nosniff'
            
            assert 'X-Frame-Options' in headers
            assert headers['X-Frame-Options'] == 'DENY'
            
            assert 'X-XSS-Protection' in headers
            assert 'Content-Security-Policy' in headers
            
            # Check CSP policy
            csp = headers.get('Content-Security-Policy', '')
            assert 'default-src' in csp
            assert "'self'" in csp
    
    def test_hsts_header_in_production(self, app, client):
        """Test HSTS header in production environment"""
        with app.app_context():
            # Mock production environment
            with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
                response = client.get('/auth/login')
                
                headers = dict(response.headers)
                assert 'Strict-Transport-Security' in headers
                
                hsts = headers['Strict-Transport-Security']
                assert 'max-age=' in hsts
                assert 'includeSubDomains' in hsts


class TestPasswordSecurity:
    """Test password security requirements"""
    
    def test_password_complexity_requirements(self, app):
        """Test password complexity validation"""
        service = SecurityService()
        
        # Test weak passwords
        weak_passwords = [
            '123',  # Too short
            'password',  # Common word
            'aaaaaaaa',  # Repetitive
            '12345678'  # Only numbers
        ]
        
        for password in weak_passwords:
            result = service.validate_password_strength(password)
            assert result['is_valid'] is False
            assert 'issues' in result
        
        # Test strong passwords
        strong_passwords = [
            'StrongPass123!',
            'MySecure#Password456',
            'Complex$Password789'
        ]
        
        for password in strong_passwords:
            result = service.validate_password_strength(password)
            assert result['is_valid'] is True
    
    def test_password_history_prevention(self, app):
        """Test prevention of password reuse"""
        with app.app_context():
            branch = Branch(name='Password Branch', code='PB001', city='Password City')
            db.session.add(branch)
            db.session.commit()
            
            user = User(
                username='passworduser',
                email='password@example.com',
                full_name='Password User',
                role='DRIVER'
            )
            user.set_password('OldPassword123!')
            db.session.add(user)
            db.session.commit()
            
            service = UserService()
            
            # Try to change to same password
            result = service.change_password(
                user.id, 
                'OldPassword123!',  # Current password
                'OldPassword123!'   # Same as current - should fail
            )
            
            assert result['success'] is False
            assert 'same as current' in result['error'].lower() or 'reuse' in result['error'].lower()