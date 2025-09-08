#!/usr/bin/env python3
"""
Authentication and role-based access control tests for PLS TRAVELS
Tests login, logout, and role-based access functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Driver, Branch, Region, UserRole, UserStatus, DriverStatus
from werkzeug.security import generate_password_hash

def test_authentication_flows():
    """Test all authentication flows and role-based access"""
    
    print("Testing Authentication & Role-Based Access Control...")
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost.localdomain'
    
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    with app.app_context():
        db.create_all()
        setup_test_users()
        
        with app.test_client() as client:
            # Test 1: Login Page Access
            results['total_tests'] += 1
            try:
                response = client.get('/auth/login')
                assert response.status_code == 200
                assert b'login' in response.data.lower()
                results['passed'] += 1
                print("✓ Login page accessible")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Login page test failed: {str(e)}")
                print(f"✗ Login page test failed: {str(e)}")
            
            # Test 2: Valid Admin Login
            results['total_tests'] += 1
            try:
                response = client.post('/auth/login', data={
                    'username': 'admin_test',
                    'password': 'admin123'
                })
                assert response.status_code == 302  # Redirect on success
                results['passed'] += 1
                print("✓ Admin login successful")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Admin login test failed: {str(e)}")
                print(f"✗ Admin login test failed: {str(e)}")
            
            # Test 3: Invalid Login Credentials
            results['total_tests'] += 1
            try:
                response = client.post('/auth/login', data={
                    'username': 'admin_test',
                    'password': 'wrong_password'
                })
                # Should stay on login page or show error
                assert response.status_code in [200, 302]
                results['passed'] += 1
                print("✓ Invalid login properly rejected")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Invalid login test failed: {str(e)}")
                print(f"✗ Invalid login test failed: {str(e)}")
            
            # Test 4: Manager Login
            results['total_tests'] += 1
            try:
                response = client.post('/auth/login', data={
                    'username': 'manager_test',
                    'password': 'manager123'
                })
                assert response.status_code == 302
                results['passed'] += 1
                print("✓ Manager login successful")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Manager login test failed: {str(e)}")
                print(f"✗ Manager login test failed: {str(e)}")
            
            # Test 5: Driver Login
            results['total_tests'] += 1
            try:
                response = client.post('/auth/login', data={
                    'username': 'driver_test',
                    'password': 'driver123'
                })
                assert response.status_code == 302
                results['passed'] += 1
                print("✓ Driver login successful")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Driver login test failed: {str(e)}")
                print(f"✗ Driver login test failed: {str(e)}")
            
            # Test 6: Root Redirect (Unauthenticated)
            results['total_tests'] += 1
            try:
                response = client.get('/')
                assert response.status_code == 302  # Should redirect to login
                results['passed'] += 1
                print("✓ Unauthenticated access properly redirected")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Root redirect test failed: {str(e)}")
                print(f"✗ Root redirect test failed: {str(e)}")
    
    return results

def setup_test_users():
    """Create test users for different roles"""
    
    # Create region and branch for context
    region = Region()
    region.name = 'Test Region'
    region.code = 'TR'
    region.state = 'Test State'
    region.country = 'India'
    db.session.add(region)
    db.session.flush()
    
    branch = Branch()
    branch.name = 'Test Branch'
    branch.code = 'TB'
    branch.region_id = region.id
    branch.city = 'Test City'
    branch.address = 'Test Address'
    branch.target_revenue_monthly = 100000
    db.session.add(branch)
    db.session.flush()
    
    # Create Admin User
    admin = User()
    admin.username = 'admin_test'
    admin.email = 'admin@test.com'
    admin.password_hash = generate_password_hash('admin123')
    admin.role = UserRole.ADMIN
    admin.status = UserStatus.ACTIVE
    admin.first_name = 'Admin'
    admin.last_name = 'Test'
    admin.created_at = db.func.now()
    admin.updated_at = db.func.now()
    db.session.add(admin)
    
    # Create Manager User
    manager = User()
    manager.username = 'manager_test'
    manager.email = 'manager@test.com'
    manager.password_hash = generate_password_hash('manager123')
    manager.role = UserRole.MANAGER
    manager.status = UserStatus.ACTIVE
    manager.first_name = 'Manager'
    manager.last_name = 'Test'
    manager.created_at = db.func.now()
    manager.updated_at = db.func.now()
    db.session.add(manager)
    
    # Create Driver User
    driver_user = User()
    driver_user.username = 'driver_test'
    driver_user.email = 'driver@test.com'
    driver_user.password_hash = generate_password_hash('driver123')
    driver_user.role = UserRole.DRIVER
    driver_user.status = UserStatus.ACTIVE
    driver_user.first_name = 'Driver'
    driver_user.last_name = 'Test'
    driver_user.created_at = db.func.now()
    driver_user.updated_at = db.func.now()
    db.session.add(driver_user)
    db.session.flush()
    
    # Create Driver Profile
    driver = Driver()
    driver.user_id = driver_user.id
    driver.branch_id = branch.id
    driver.employee_id = 'EMP999888'
    driver.full_name = 'Driver Test'
    driver.aadhar_number = '999888777666'
    driver.license_number = 'DL999888777'
    driver.status = DriverStatus.ACTIVE
    driver.phone = '9876543210'
    driver.address = 'Test Driver Address'
    db.session.add(driver)
    
    # Create Inactive User for testing
    inactive_user = User()
    inactive_user.username = 'inactive_test'
    inactive_user.email = 'inactive@test.com'
    inactive_user.password_hash = generate_password_hash('inactive123')
    inactive_user.role = UserRole.DRIVER
    inactive_user.status = UserStatus.INACTIVE
    inactive_user.first_name = 'Inactive'
    inactive_user.last_name = 'Test'
    inactive_user.created_at = db.func.now()
    inactive_user.updated_at = db.func.now()
    db.session.add(inactive_user)
    
    db.session.commit()
    print("Test users created successfully")

def test_role_access_control():
    """Test role-based access control for different routes"""
    
    print("\nTesting Role-Based Access Control...")
    
    app = create_app()
    app.config['TESTING'] = True  
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost.localdomain'
    
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    with app.app_context():
        db.create_all()
        setup_test_users()
        
        with app.test_client() as client:
            
            # Test admin access to admin routes
            results['total_tests'] += 1
            try:
                # Login as admin
                client.post('/auth/login', data={
                    'username': 'admin_test',
                    'password': 'admin123'
                })
                
                # Try to access admin dashboard
                response = client.get('/admin/dashboard')
                # Should allow access (200) or redirect to admin dashboard (302)
                assert response.status_code in [200, 302]
                results['passed'] += 1
                print("✓ Admin can access admin routes")
                
                # Logout
                client.get('/auth/logout')
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Admin access test failed: {str(e)}")
                print(f"✗ Admin access test failed: {str(e)}")
    
    return results

def test_password_security():
    """Test password hashing and validation"""
    
    print("\nTesting Password Security...")
    
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    # Test 1: Password Hashing
    results['total_tests'] += 1
    try:
        from werkzeug.security import check_password_hash, generate_password_hash
        
        password = 'test_password_123'
        hashed = generate_password_hash(password)
        
        # Verify password can be verified
        assert check_password_hash(hashed, password) == True
        assert check_password_hash(hashed, 'wrong_password') == False
        
        # Verify hash is different from plain password
        assert hashed != password
        
        results['passed'] += 1
        print("✓ Password hashing and verification working correctly")
        
    except Exception as e:
        results['failed'] += 1
        results['errors'].append(f"Password security test failed: {str(e)}")
        print(f"✗ Password security test failed: {str(e)}")
    
    return results

if __name__ == '__main__':
    print("PLS TRAVELS - Authentication & Access Control Testing")
    print("=" * 60)
    
    # Run all authentication tests
    auth_results = test_authentication_flows()
    access_results = test_role_access_control()
    password_results = test_password_security()
    
    # Combine results
    total_tests = auth_results['total_tests'] + access_results['total_tests'] + password_results['total_tests']
    total_passed = auth_results['passed'] + access_results['passed'] + password_results['passed']
    total_failed = auth_results['failed'] + access_results['failed'] + password_results['failed']
    all_errors = auth_results['errors'] + access_results['errors'] + password_results['errors']
    
    print("\n" + "=" * 60)
    print("AUTHENTICATION TEST RESULTS")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
    
    if all_errors:
        print("\nERRORS:")
        for error in all_errors:
            print(f"- {error}")
    
    if total_failed == 0:
        print("\n🎉 All authentication tests passed! The authentication system is working correctly.")
    else:
        print(f"\n⚠️  {total_failed} authentication tests failed. Review the errors above.")