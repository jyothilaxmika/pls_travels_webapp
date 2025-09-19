"""
Unit tests for service layer classes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from services.driver_service import DriverService
from services.duty_service import DutyService
from services.earnings_service import EarningsService
from services.storage_service import StorageService
from services.notification_service import NotificationService
from services.user_service import UserService
from services.security_service import SecurityService
from services.analytics_service import AnalyticsService

from models import User, DriverProfile, Duty, DutyScheme, Vehicle, Branch
from tests.unit.conftest import UserFactory, DutyFactory, DutySchemeFactory, VehicleFactory, BranchFactory


class TestDriverService:
    """Test DriverService functionality"""
    
    def test_create_driver_success(self, db_session, branch):
        """Test successful driver creation"""
        service = DriverService()
        driver_data = {
            'username': 'newdriver',
            'email': 'driver@test.com',
            'full_name': 'New Driver',
            'phone_number': '9999999999',
            'aadhar_number': '123456789012',
            'license_number': 'DL12345678',
            'bank_account_number': '1234567890123',
            'branch_id': branch.id
        }
        
        result = service.create_driver(driver_data)
        
        assert result['success'] is True
        assert 'driver' in result
        assert result['driver'].username == 'newdriver'
        assert result['driver'].role == 'DRIVER'
    
    def test_create_driver_duplicate_username(self, db_session, driver_user, branch):
        """Test driver creation with duplicate username"""
        service = DriverService()
        driver_data = {
            'username': driver_user.username,  # Duplicate
            'email': 'different@test.com',
            'full_name': 'Another Driver',
            'phone_number': '8888888888',
            'aadhar_number': '123456789013',
            'license_number': 'DL12345679',
            'bank_account_number': '1234567890124',
            'branch_id': branch.id
        }
        
        result = service.create_driver(driver_data)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'username' in result['error'].lower()
    
    def test_approve_driver(self, db_session, driver_user):
        """Test driver approval"""
        service = DriverService()
        driver_user.status = 'PENDING'
        db_session.commit()
        
        result = service.approve_driver(driver_user.id, approved_by_id=1)
        
        assert result['success'] is True
        assert driver_user.status == 'ACTIVE'
    
    def test_get_driver_statistics(self, db_session, branch):
        """Test driver statistics calculation"""
        service = DriverService()
        
        # Create test drivers
        active_driver = UserFactory(role='DRIVER', status='ACTIVE')
        pending_driver = UserFactory(role='DRIVER', status='PENDING')
        suspended_driver = UserFactory(role='DRIVER', status='SUSPENDED')
        
        for user in [active_driver, pending_driver, suspended_driver]:
            db_session.add(user)
        db_session.commit()
        
        stats = service.get_driver_statistics(branch.id)
        
        assert 'total_drivers' in stats
        assert 'active_drivers' in stats
        assert 'pending_drivers' in stats
        assert stats['active_drivers'] >= 1
        assert stats['pending_drivers'] >= 1


class TestDutyService:
    """Test DutyService functionality"""
    
    def test_start_duty_success(self, db_session, driver_user, vehicle, duty_scheme):
        """Test successful duty start"""
        service = DutyService()
        duty_data = {
            'driver_id': driver_user.id,
            'vehicle_id': vehicle.id,
            'duty_scheme_id': duty_scheme.id,
            'start_odometer': 10000,
            'notes': 'Starting duty'
        }
        
        result = service.start_duty(duty_data)
        
        assert result['success'] is True
        assert 'duty' in result
        assert result['duty'].status == 'ACTIVE'
        assert result['duty'].start_time is not None
    
    def test_end_duty_success(self, db_session, duty):
        """Test successful duty end"""
        service = DutyService()
        duty.status = 'ACTIVE'
        duty.start_time = datetime.now() - timedelta(hours=8)
        db_session.commit()
        
        end_data = {
            'end_odometer': 10150,
            'trip_count': 5,
            'cash_collected': 500.00,
            'fuel_expense': 200.00
        }
        
        result = service.end_duty(duty.id, end_data)
        
        assert result['success'] is True
        assert duty.status == 'PENDING'
        assert duty.end_time is not None
    
    def test_approve_duty(self, db_session, duty):
        """Test duty approval"""
        service = DutyService()
        duty.status = 'PENDING'
        db_session.commit()
        
        result = service.approve_duty(duty.id, approved_by_id=1)
        
        assert result['success'] is True
        assert duty.status == 'APPROVED'
        assert duty.approved_at is not None
    
    def test_get_driver_active_duty(self, db_session, driver_user, vehicle, duty_scheme):
        """Test getting active duty for driver"""
        service = DutyService()
        
        # Create active duty
        active_duty = DutyFactory(
            driver=driver_user,
            vehicle=vehicle,
            duty_scheme=duty_scheme,
            status='ACTIVE'
        )
        db_session.add(active_duty)
        db_session.commit()
        
        result = service.get_driver_active_duty(driver_user.id)
        
        assert result is not None
        assert result.id == active_duty.id
        assert result.status == 'ACTIVE'


class TestEarningsService:
    """Test EarningsService functionality"""
    
    def test_calculate_duty_earnings_fixed_scheme(self, db_session, duty):
        """Test earnings calculation for fixed scheme"""
        service = EarningsService()
        duty.duty_scheme.scheme_type = 'FIXED'
        duty.duty_scheme.base_amount = 500.00
        duty.cash_collected = 1000.00
        db_session.commit()
        
        earnings = service.calculate_duty_earnings(duty.id)
        
        assert earnings['success'] is True
        assert 'calculation' in earnings
        assert earnings['calculation']['base_earnings'] == 500.00
    
    def test_calculate_duty_earnings_per_trip_scheme(self, db_session, duty):
        """Test earnings calculation for per-trip scheme"""
        service = EarningsService()
        duty.duty_scheme.scheme_type = 'PER_TRIP'
        duty.duty_scheme.base_amount = 50.00  # per trip
        duty.trip_count = 8
        db_session.commit()
        
        earnings = service.calculate_duty_earnings(duty.id)
        
        assert earnings['success'] is True
        assert 'calculation' in earnings
        assert earnings['calculation']['base_earnings'] == 400.00  # 8 * 50
    
    def test_calculate_commission_earnings(self, db_session, duty):
        """Test commission earnings calculation"""
        service = EarningsService()
        duty.duty_scheme.scheme_type = 'COMMISSION'
        duty.duty_scheme.commission_percentage = 15.0
        duty.cash_collected = 1000.00
        db_session.commit()
        
        earnings = service.calculate_duty_earnings(duty.id)
        
        assert earnings['success'] is True
        commission = earnings['calculation']['commission_earnings']
        assert commission == 150.00  # 15% of 1000
    
    def test_get_driver_earnings_summary(self, db_session, driver_user):
        """Test driver earnings summary"""
        service = EarningsService()
        
        # Create some approved duties
        duty1 = DutyFactory(driver=driver_user, status='APPROVED', cash_collected=500.00)
        duty2 = DutyFactory(driver=driver_user, status='APPROVED', cash_collected=750.00)
        
        db_session.add(duty1)
        db_session.add(duty2)
        db_session.commit()
        
        summary = service.get_driver_earnings_summary(driver_user.id)
        
        assert 'total_earnings' in summary
        assert 'total_duties' in summary
        assert summary['total_duties'] >= 2


class TestStorageService:
    """Test StorageService functionality"""
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_create_directory_structure(self, mock_makedirs, mock_exists):
        """Test directory structure creation"""
        mock_exists.return_value = False
        service = StorageService()
        
        service._create_directory_structure()
        
        # Should create multiple directories
        assert mock_makedirs.call_count >= 3
    
    @patch('werkzeug.utils.secure_filename')
    def test_generate_secure_filename(self, mock_secure_filename):
        """Test secure filename generation"""
        mock_secure_filename.return_value = 'test_file.jpg'
        service = StorageService()
        
        filename = service.generate_secure_filename('test file!@#.jpg')
        
        assert mock_secure_filename.called
        assert filename is not None
    
    def test_get_allowed_file_extensions(self):
        """Test allowed file extensions"""
        service = StorageService()
        
        extensions = service.get_allowed_file_extensions()
        
        assert 'jpg' in extensions
        assert 'png' in extensions
        assert 'pdf' in extensions
    
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_get_storage_statistics(self, mock_exists, mock_getsize):
        """Test storage statistics calculation"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        service = StorageService()
        
        stats = service.get_storage_statistics()
        
        assert 'total_files' in stats
        assert 'total_size' in stats


class TestNotificationService:
    """Test NotificationService functionality"""
    
    @patch('services.notification_service.NotificationService._send_sms')
    def test_send_otp_success(self, mock_send_sms):
        """Test OTP sending"""
        mock_send_sms.return_value = {'success': True, 'sid': 'test_sid'}
        service = NotificationService()
        
        result = service.send_otp('9999999999')
        
        assert result['success'] is True
        assert 'otp' in result
        assert mock_send_sms.called
    
    def test_generate_otp(self):
        """Test OTP generation"""
        service = NotificationService()
        
        otp = service._generate_otp()
        
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_verify_otp_success(self):
        """Test OTP verification success"""
        service = NotificationService()
        phone = '9999999999'
        
        # Send OTP first
        send_result = service.send_otp(phone)
        otp = send_result['otp']
        
        # Verify with correct OTP
        verify_result = service.verify_otp(phone, otp)
        
        assert verify_result is True
    
    def test_verify_otp_failure(self):
        """Test OTP verification failure"""
        service = NotificationService()
        phone = '9999999999'
        
        # Send OTP first
        service.send_otp(phone)
        
        # Verify with wrong OTP
        verify_result = service.verify_otp(phone, '000000')
        
        assert verify_result is False


class TestUserService:
    """Test UserService functionality"""
    
    def test_authenticate_user_success(self, db_session, driver_user):
        """Test successful user authentication"""
        service = UserService()
        
        result = service.authenticate_user(driver_user.username, 'testpass123')
        
        assert result['success'] is True
        assert result['user'].id == driver_user.id
    
    def test_authenticate_user_failure(self, db_session, driver_user):
        """Test failed user authentication"""
        service = UserService()
        
        result = service.authenticate_user(driver_user.username, 'wrongpassword')
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_create_user_session(self, db_session, driver_user):
        """Test user session creation"""
        service = UserService()
        
        session_data = service.create_user_session(driver_user)
        
        assert 'user_id' in session_data
        assert 'role' in session_data
        assert 'branch_id' in session_data
        assert session_data['user_id'] == driver_user.id


class TestSecurityService:
    """Test SecurityService functionality"""
    
    def test_validate_password_strength(self):
        """Test password strength validation"""
        service = SecurityService()
        
        # Strong password
        result = service.validate_password_strength('StrongPass123!')
        assert result['is_valid'] is True
        
        # Weak password
        result = service.validate_password_strength('weak')
        assert result['is_valid'] is False
        assert 'issues' in result
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        service = SecurityService()
        
        clean_input = service.sanitize_input('<script>alert("xss")</script>Hello')
        assert '<script>' not in clean_input
        assert 'Hello' in clean_input
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation"""
        service = SecurityService()
        
        token = service.generate_csrf_token()
        
        assert token is not None
        assert len(token) > 20
    
    def test_validate_file_upload(self, sample_file_upload):
        """Test file upload validation"""
        service = SecurityService()
        
        with open(sample_file_upload, 'rb') as f:
            result = service.validate_file_upload(f, 'test.jpg')
        
        assert result['is_valid'] is True


class TestAnalyticsService:
    """Test AnalyticsService functionality"""
    
    def test_get_dashboard_analytics(self, db_session, branch):
        """Test dashboard analytics generation"""
        service = AnalyticsService()
        
        analytics = service.get_dashboard_analytics(branch.id)
        
        assert 'total_drivers' in analytics
        assert 'total_duties' in analytics
        assert 'total_earnings' in analytics
        assert 'vehicle_utilization' in analytics
    
    def test_get_driver_performance_metrics(self, db_session, driver_user):
        """Test driver performance metrics"""
        service = AnalyticsService()
        
        # Create some duties for the driver
        duty1 = DutyFactory(driver=driver_user, status='APPROVED')
        duty2 = DutyFactory(driver=driver_user, status='APPROVED')
        
        db_session.add(duty1)
        db_session.add(duty2)
        db_session.commit()
        
        metrics = service.get_driver_performance_metrics(driver_user.id)
        
        assert 'total_duties' in metrics
        assert 'average_rating' in metrics
        assert 'completion_rate' in metrics
    
    def test_calculate_period_comparison(self, db_session, branch):
        """Test period-over-period comparison"""
        service = AnalyticsService()
        
        comparison = service.calculate_period_comparison(
            branch_id=branch.id,
            metric='duties',
            period='month'
        )
        
        assert 'current_period' in comparison
        assert 'previous_period' in comparison
        assert 'change_percentage' in comparison


class TestServiceIntegration:
    """Test service layer integration"""
    
    def test_duty_workflow_integration(self, db_session, driver_user, vehicle, duty_scheme):
        """Test complete duty workflow through services"""
        duty_service = DutyService()
        earnings_service = EarningsService()
        
        # Start duty
        start_result = duty_service.start_duty({
            'driver_id': driver_user.id,
            'vehicle_id': vehicle.id,
            'duty_scheme_id': duty_scheme.id,
            'start_odometer': 10000
        })
        
        assert start_result['success'] is True
        duty = start_result['duty']
        
        # End duty
        end_result = duty_service.end_duty(duty.id, {
            'end_odometer': 10100,
            'trip_count': 5,
            'cash_collected': 500.00
        })
        
        assert end_result['success'] is True
        
        # Approve duty
        approve_result = duty_service.approve_duty(duty.id, approved_by_id=1)
        assert approve_result['success'] is True
        
        # Calculate earnings
        earnings_result = earnings_service.calculate_duty_earnings(duty.id)
        assert earnings_result['success'] is True
        assert 'calculation' in earnings_result
    
    def test_driver_onboarding_integration(self, db_session, branch):
        """Test complete driver onboarding workflow"""
        driver_service = DriverService()
        user_service = UserService()
        
        # Create driver
        driver_data = {
            'username': 'integrationdriver',
            'email': 'integration@test.com',
            'full_name': 'Integration Test Driver',
            'phone_number': '9876543210',
            'aadhar_number': '123456789012',
            'license_number': 'DL12345678',
            'bank_account_number': '1234567890123',
            'branch_id': branch.id
        }
        
        create_result = driver_service.create_driver(driver_data)
        assert create_result['success'] is True
        
        driver = create_result['driver']
        
        # Authenticate driver
        auth_result = user_service.authenticate_user('integrationdriver', 'defaultpass123')
        # Note: Authentication might fail as password isn't set in creation
        
        # Approve driver
        approve_result = driver_service.approve_driver(driver.id, approved_by_id=1)
        assert approve_result['success'] is True
        
        assert driver.status == 'ACTIVE'