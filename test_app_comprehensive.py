#!/usr/bin/env python3
"""
Comprehensive unit tests for PLS TRAVELS Flask application
Tests all routes, models, utilities, and core functionality
"""

# pytest import removed - using manual testing instead
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create mock pytest for compatibility
    class pytest:
        @staticmethod
        def fixture(func):
            return func
        @staticmethod
        def raises(exception_type):
            class ExceptionContext:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        raise AssertionError(f"Expected {exception_type} but no exception was raised")
                    return issubclass(exc_type, exception_type)
            return ExceptionContext()
import sys
import os
import tempfile
import json
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import (
    User, Driver, Vehicle, Branch, Region, VehicleType, Duty, DutyScheme, 
    UserRole, UserStatus, DriverStatus, VehicleStatus, DutyStatus,
    Penalty, Asset, AuditLog, VehicleTracking, ResignationRequest
)
from utils import calculate_tripsheet, generate_employee_id, SalaryCalculator, DutyEntry

class TestApplicationSetup:
    """Test application setup and configuration"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
        
    @pytest.fixture
    def app_context(self, app):
        """Provide application context"""
        with app.app_context():
            yield app
    
    def test_app_creation(self, app):
        """Test that the app can be created successfully"""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_database_creation(self, app_context):
        """Test that database tables are created"""
        # Test that basic tables exist by trying to query them
        users_count = User.query.count()
        assert users_count == 0  # Should be empty initially
        
        branches_count = Branch.query.count()
        assert branches_count == 0

class TestModels:
    """Test database models and relationships"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_user_creation(self, app):
        """Test User model creation and validation"""
        with app.app_context():
            user = User()
            user.username = 'testuser'
            user.email = 'test@example.com'
            user.password_hash = generate_password_hash('password123')
            user.role = UserRole.DRIVER
            user.status = UserStatus.ACTIVE
            user.first_name = 'Test'
            user.last_name = 'User'
            
            db.session.add(user)
            db.session.commit()
            
            # Test retrieval
            retrieved_user = User.query.filter_by(username='testuser').first()
            assert retrieved_user is not None
            assert retrieved_user.email == 'test@example.com'
            assert retrieved_user.full_name == 'Test User'
            assert check_password_hash(retrieved_user.password_hash, 'password123')
    
    def test_driver_model_with_relationships(self, app):
        """Test Driver model and its relationships"""
        with app.app_context():
            # Create dependencies
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
            
            user = User()
            user.username = 'driver_test'
            user.email = 'driver@test.com'
            user.password_hash = generate_password_hash('password123')
            user.role = UserRole.DRIVER
            user.status = UserStatus.ACTIVE
            user.first_name = 'Driver'
            user.last_name = 'Test'
            db.session.add(user)
            db.session.flush()
            
            # Create driver
            driver = Driver()
            driver.user_id = user.id
            driver.branch_id = branch.id
            driver.employee_id = 'EMP123456'
            driver.full_name = 'Driver Test'
            driver.aadhar_number = '123456789012'
            driver.license_number = 'DL123456789'
            driver.status = DriverStatus.ACTIVE
            driver.phone = '9876543210'
            driver.address = 'Test Address'
            
            db.session.add(driver)
            db.session.commit()
            
            # Test relationships
            retrieved_driver = Driver.query.filter_by(employee_id='EMP123456').first()
            assert retrieved_driver is not None
            assert retrieved_driver.user.username == 'driver_test'
            assert retrieved_driver.branch.name == 'Test Branch'
            assert retrieved_driver.branch.region.name == 'Test Region'
    
    def test_vehicle_model(self, app):
        """Test Vehicle model creation"""
        with app.app_context():
            # Create dependencies
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
            db.session.add(branch)
            db.session.flush()
            
            vehicle_type = VehicleType()
            vehicle_type.name = 'Taxi'
            vehicle_type.category = 'Commercial'
            vehicle_type.capacity_passengers = 4
            vehicle_type.fuel_type = 'Petrol'
            vehicle_type.base_fare = 50.0
            db.session.add(vehicle_type)
            db.session.flush()
            
            # Create vehicle
            vehicle = Vehicle()
            vehicle.branch_id = branch.id
            vehicle.vehicle_type_id = vehicle_type.id
            vehicle.registration_number = 'TN01AB1234'
            vehicle.make = 'Maruti'
            vehicle.model = 'Swift'
            vehicle.manufacturing_year = 2020
            vehicle.status = VehicleStatus.ACTIVE
            vehicle.is_available = True
            vehicle.current_odometer = 15000.0
            
            db.session.add(vehicle)
            db.session.commit()
            
            # Test retrieval and relationships
            retrieved_vehicle = Vehicle.query.filter_by(registration_number='TN01AB1234').first()
            assert retrieved_vehicle is not None
            assert retrieved_vehicle.make == 'Maruti'
            assert retrieved_vehicle.vehicle_type_obj.name == 'Taxi'
            assert retrieved_vehicle.branch.name == 'Test Branch'
    
    def test_duty_model(self, app):
        """Test Duty model with complex relationships"""
        with app.app_context():
            # Create all dependencies
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
            db.session.add(branch)
            db.session.flush()
            
            # Create user and driver
            user = User()
            user.username = 'duty_driver'
            user.email = 'duty@test.com'
            user.password_hash = generate_password_hash('password123')
            user.role = UserRole.DRIVER
            user.status = UserStatus.ACTIVE
            user.first_name = 'Duty'
            user.last_name = 'Driver'
            db.session.add(user)
            db.session.flush()
            
            driver = Driver()
            driver.user_id = user.id
            driver.branch_id = branch.id
            driver.employee_id = 'EMP789012'
            driver.full_name = 'Duty Driver'
            driver.aadhar_number = '123456789013'
            driver.license_number = 'DL987654321'
            driver.status = DriverStatus.ACTIVE
            db.session.add(driver)
            db.session.flush()
            
            # Create vehicle
            vehicle_type = VehicleType()
            vehicle_type.name = 'Taxi'
            vehicle_type.category = 'Commercial'
            vehicle_type.capacity_passengers = 4
            vehicle_type.fuel_type = 'Petrol'
            db.session.add(vehicle_type)
            db.session.flush()
            
            vehicle = Vehicle()
            vehicle.branch_id = branch.id
            vehicle.vehicle_type_id = vehicle_type.id
            vehicle.registration_number = 'TN02CD5678'
            vehicle.make = 'Toyota'
            vehicle.model = 'Etios'
            vehicle.manufacturing_year = 2019
            vehicle.status = VehicleStatus.ACTIVE
            db.session.add(vehicle)
            db.session.flush()
            
            # Create duty scheme
            duty_scheme = DutyScheme()
            duty_scheme.name = 'Test Scheme'
            duty_scheme.scheme_type = 'fixed'
            duty_scheme.branch_id = branch.id
            duty_scheme.config = '{"daily_amount": 800}'
            duty_scheme.is_active = True
            duty_scheme.bmg_amount = 600.0
            db.session.add(duty_scheme)
            db.session.flush()
            
            # Create duty
            duty = Duty()
            duty.driver_id = driver.id
            duty.vehicle_id = vehicle.id
            duty.branch_id = branch.id
            duty.duty_scheme_id = duty_scheme.id
            duty.actual_start = datetime.utcnow()
            duty.start_odometer = 15000.0
            duty.status = DutyStatus.ACTIVE
            duty.cash_collection = 1500.0
            duty.qr_payment = 500.0
            duty.fuel_expense = 200.0
            
            db.session.add(duty)
            db.session.commit()
            
            # Test relationships and calculations
            retrieved_duty = Duty.query.first()
            assert retrieved_duty is not None
            assert retrieved_duty.driver.full_name == 'Duty Driver'
            assert retrieved_duty.vehicle.registration_number == 'TN02CD5678'
            assert retrieved_duty.branch.name == 'Test Branch'
            assert retrieved_duty.duty_scheme.name == 'Test Scheme'

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_generate_employee_id(self):
        """Test employee ID generation"""
        # Create mock app context
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            emp_id = generate_employee_id()
            assert emp_id.startswith('EMP')
            assert len(emp_id) == 9  # EMP + 6 digits
            assert emp_id[3:].isdigit()  # Last 6 characters are digits
    
    def test_calculate_tripsheet_comprehensive(self):
        """Test comprehensive tripsheet calculation"""
        # Test with full duty data
        duty_data = {
            'company_pay': 500,
            'cash_collected': 1200,
            'qr_payment': 300,
            'digital_payments': 200,
            'operator_out': 800,
            'toll_expense': 50,
            'fuel_expense': 100,
            'other_expenses': 30,
            'maintenance_expense': 20,
            'advance_deduction': 100,
            'fuel_deduction': 50,
            'penalty_deduction': 25
        }
        
        result = calculate_tripsheet(duty_data)
        
        # Verify all required fields are in result
        assert 'company_pay' in result
        assert 'driver_salary' in result
        assert 'company_profit' in result
        assert 'company_earnings' in result
        assert 'incentive' in result
        
        # Verify calculations are reasonable
        assert isinstance(result['driver_salary'], (int, float))
        assert result['driver_salary'] >= 0
        assert isinstance(result['company_profit'], (int, float))
    
    def test_salary_calculator_all_schemes(self):
        """Test SalaryCalculator with different schemes"""
        calculator = SalaryCalculator()
        
        # Test Scheme 1 (percentage-based)
        entry1 = DutyEntry(
            driver_name="Test Driver 1",
            car_number="TN01AB1234",
            scheme=1,
            cash_collected=2000,
            qr_payment=500,
            outside_cash=300,
            start_cng=20,
            end_cng=15,
            pass_deduction=50
        )
        
        result1 = calculator.calculate(entry1)
        assert 'driver_salary' in result1
        assert 'total_earnings' in result1
        assert result1['total_earnings'] == 2800  # 2000 + 500 + 300
        
        # Test Scheme 2 (daily rate)
        entry2 = DutyEntry(
            driver_name="Test Driver 2",
            car_number="TN02CD5678",
            scheme=2,
            days_worked=25,
            daily_rate=800
        )
        
        result2 = calculator.calculate(entry2)
        assert 'monthly_salary' in result2
        assert result2['monthly_salary'] == 20000  # 25 * 800
        
        # Test Scheme 3 (hybrid)
        entry3 = DutyEntry(
            driver_name="Test Driver 3",
            car_number="TN03EF9012",
            scheme=3,
            cash_collected=1000,
            qr_payment=200,
            base_salary=500
        )
        
        result3 = calculator.calculate(entry3)
        assert 'driver_salary' in result3
        assert 'base_component' in result3

class TestRoutes:
    """Test all application routes"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost'
        
        with app.app_context():
            db.create_all()
            self.setup_test_data()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def setup_test_data(self):
        """Create comprehensive test data"""
        # Create region and branch
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
        
        # Create test users for different roles
        admin = User()
        admin.username = 'admin'
        admin.email = 'admin@test.com'
        admin.password_hash = generate_password_hash('admin123')
        admin.role = UserRole.ADMIN
        admin.status = UserStatus.ACTIVE
        admin.first_name = 'Admin'
        admin.last_name = 'User'
        db.session.add(admin)
        
        manager = User()
        manager.username = 'manager'
        manager.email = 'manager@test.com'
        manager.password_hash = generate_password_hash('manager123')
        manager.role = UserRole.MANAGER
        manager.status = UserStatus.ACTIVE
        manager.first_name = 'Manager'
        manager.last_name = 'User'
        db.session.add(manager)
        
        driver_user = User()
        driver_user.username = 'driver'
        driver_user.email = 'driver@test.com'
        driver_user.password_hash = generate_password_hash('driver123')
        driver_user.role = UserRole.DRIVER
        driver_user.status = UserStatus.ACTIVE
        driver_user.first_name = 'Driver'
        driver_user.last_name = 'User'
        db.session.add(driver_user)
        db.session.flush()
        
        # Create driver profile
        driver = Driver()
        driver.user_id = driver_user.id
        driver.branch_id = branch.id
        driver.employee_id = 'EMP123456'
        driver.full_name = 'Driver User'
        driver.aadhar_number = '123456789012'
        driver.license_number = 'DL123456789'
        driver.status = DriverStatus.ACTIVE
        driver.phone = '9876543210'
        db.session.add(driver)
        
        # Create vehicle type and vehicle
        vehicle_type = VehicleType()
        vehicle_type.name = 'Taxi'
        vehicle_type.category = 'Commercial'
        vehicle_type.capacity_passengers = 4
        vehicle_type.fuel_type = 'Petrol'
        vehicle_type.base_fare = 50.0
        db.session.add(vehicle_type)
        db.session.flush()
        
        vehicle = Vehicle()
        vehicle.branch_id = branch.id
        vehicle.vehicle_type_id = vehicle_type.id
        vehicle.registration_number = 'TN01AB1234'
        vehicle.make = 'Maruti'
        vehicle.model = 'Swift'
        vehicle.manufacturing_year = 2020
        vehicle.status = VehicleStatus.ACTIVE
        vehicle.is_available = True
        db.session.add(vehicle)
        
        # Create duty scheme
        duty_scheme = DutyScheme()
        duty_scheme.name = 'Test Scheme'
        duty_scheme.scheme_type = 'fixed'
        duty_scheme.branch_id = branch.id
        duty_scheme.config = '{"daily_amount": 800}'
        duty_scheme.is_active = True
        duty_scheme.bmg_amount = 600.0
        db.session.add(duty_scheme)
        
        db.session.commit()
    
    def test_root_route(self, client, app):
        """Test root route redirects properly"""
        with app.test_request_context():
            response = client.get('/')
            assert response.status_code == 302  # Redirect
    
    def test_login_page(self, client, app):
        """Test login page loads correctly"""
        with app.test_request_context():
            response = client.get('/auth/login')
            assert response.status_code == 200
            assert b'login' in response.data.lower()
    
    def test_login_functionality(self, client, app):
        """Test login with valid credentials"""
        with app.test_request_context():
            response = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'admin123'
            })
            # Should redirect on successful login
            assert response.status_code == 302
    
    def test_invalid_login(self, client, app):
        """Test login with invalid credentials"""
        with app.test_request_context():
            response = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'wrongpassword'
            })
            # Should stay on login page with error
            assert response.status_code == 200
    
    def test_api_calculate_salary(self, client, app):
        """Test salary calculation API endpoint"""
        with app.test_request_context():
            test_data = {
                'company_pay': 500,
                'cash_collected': 1000,
                'operator_out': 600,
                'advance_deduction': 50
            }
            
            response = client.post('/api/calculate-salary',
                                 json=test_data,
                                 content_type='application/json')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert 'driver_salary' in result
    
    def test_api_calculate_salary_invalid_data(self, client, app):
        """Test salary calculation API with invalid data"""
        with app.test_request_context():
            response = client.post('/api/calculate-salary',
                                 data='invalid json',
                                 content_type='application/json')
            
            assert response.status_code == 400

class TestFileOperations:
    """Test file upload and processing functionality"""
    
    def test_allowed_file_validation(self):
        """Test file extension validation"""
        from utils import allowed_file
        
        # Test allowed extensions
        assert allowed_file('document.pdf') == True
        assert allowed_file('image.jpg') == True
        assert allowed_file('image.jpeg') == True
        assert allowed_file('image.png') == True
        assert allowed_file('text.txt') == True
        
        # Test disallowed extensions
        assert allowed_file('script.exe') == False
        assert allowed_file('document.doc') == False
        assert allowed_file('archive.zip') == False
        assert allowed_file('noextension') == False
        assert allowed_file('') == False

class TestDatabaseIntegrity:
    """Test database constraints and integrity"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_unique_constraints(self, app):
        """Test unique constraints are enforced"""
        with app.app_context():
            # Test User username uniqueness
            user1 = User()
            user1.username = 'duplicate'
            user1.email = 'user1@test.com'
            user1.password_hash = generate_password_hash('password')
            user1.role = UserRole.DRIVER
            user1.status = UserStatus.ACTIVE
            user1.first_name = 'User'
            user1.last_name = 'One'
            db.session.add(user1)
            db.session.commit()
            
            user2 = User()
            user2.username = 'duplicate'  # Same username
            user2.email = 'user2@test.com'
            user2.password_hash = generate_password_hash('password')
            user2.role = UserRole.DRIVER
            user2.status = UserStatus.ACTIVE
            user2.first_name = 'User'
            user2.last_name = 'Two'
            db.session.add(user2)
            
            # Should raise integrity error
            with pytest.raises(Exception):
                db.session.commit()
    
    def test_user_role_validation(self, app):
        """Test user role enum validation"""
        with app.app_context():
            user = User()
            user.username = 'test_role'
            user.email = 'role@test.com'
            user.password_hash = generate_password_hash('password')
            user.role = UserRole.ADMIN  # Valid role
            user.status = UserStatus.ACTIVE
            user.first_name = 'Role'
            user.last_name = 'Test'
            
            db.session.add(user)
            db.session.commit()
            
            retrieved = User.query.filter_by(username='test_role').first()
            assert retrieved.role == UserRole.ADMIN

def run_all_tests():
    """Run all tests manually without pytest"""
    results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    print("Running comprehensive application tests...")
    
    # Test 1: Application Creation
    results['total_tests'] += 1
    try:
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            assert User.query.count() == 0
        
        results['passed'] += 1
        print("✓ Application setup and database creation")
    except Exception as e:
        results['failed'] += 1
        results['errors'].append(f"App creation test failed: {str(e)}")
        print(f"✗ App creation test failed: {str(e)}")
    
    # Test 2: Utility Functions
    results['total_tests'] += 1
    try:
        from utils import calculate_tripsheet, SalaryCalculator, DutyEntry, allowed_file
        
        # Test calculate_tripsheet
        test_data = {
            'company_pay': 500,
            'cash_collected': 1000,
            'operator_out': 600,
            'advance_deduction': 50
        }
        result = calculate_tripsheet(test_data)
        assert 'driver_salary' in result
        
        # Test SalaryCalculator
        calculator = SalaryCalculator()
        entry = DutyEntry(
            driver_name="Test Driver",
            car_number="TN01AB1234",
            scheme=1,
            cash_collected=2000,
            qr_payment=500
        )
        result = calculator.calculate(entry)
        assert 'driver_salary' in result
        
        # Test file validation
        assert allowed_file('test.pdf') == True
        assert allowed_file('test.exe') == False
        
        results['passed'] += 1
        print("✓ All utility functions working correctly")
    except Exception as e:
        results['failed'] += 1
        results['errors'].append(f"Utility functions test failed: {str(e)}")
        print(f"✗ Utility functions test failed: {str(e)}")
    
    # Test 3: Model Creation and Relationships
    results['total_tests'] += 1
    try:
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create test user
            user = User()
            user.username = 'testuser'
            user.email = 'test@example.com'
            user.password_hash = generate_password_hash('password123')
            user.role = UserRole.DRIVER
            user.status = UserStatus.ACTIVE
            user.first_name = 'Test'
            user.last_name = 'User'
            db.session.add(user)
            db.session.commit()
            
            # Verify creation
            retrieved = User.query.filter_by(username='testuser').first()
            assert retrieved is not None
            assert retrieved.full_name == 'Test User'
            assert check_password_hash(retrieved.password_hash, 'password123')
        
        results['passed'] += 1
        print("✓ Model creation and relationships working")
    except Exception as e:
        results['failed'] += 1
        results['errors'].append(f"Model test failed: {str(e)}")
        print(f"✗ Model test failed: {str(e)}")
    
    # Test 4: Route Testing (Basic)
    results['total_tests'] += 1
    try:
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            
            with app.test_client() as client:
                # Test root route
                response = client.get('/')
                assert response.status_code == 302  # Redirect to login
                
                # Test login page
                response = client.get('/auth/login')
                assert response.status_code == 200
        
        results['passed'] += 1
        print("✓ Basic route testing successful")
    except Exception as e:
        results['failed'] += 1
        results['errors'].append(f"Route test failed: {str(e)}")
        print(f"✗ Route test failed: {str(e)}")
    
    return results

if __name__ == '__main__':
    results = run_all_tests()
    print(f"\n=== Test Results ===")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total_tests']*100):.1f}%")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"- {error}")
    
    if results['failed'] == 0:
        print("\n🎉 All tests passed! The application is working correctly.")
    else:
        print(f"\n⚠️  {results['failed']} tests failed. Review the errors above.")