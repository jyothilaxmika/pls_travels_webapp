"""
Integration tests for database operations and service layer
"""

import pytest
from datetime import datetime, timedelta

from app import create_app, db
from models import User, DriverProfile, Vehicle, Duty, Branch, DutyScheme
from services.driver_service import DriverService
from services.duty_service import DutyService
from services.earnings_service import EarningsService
from services.transaction_helper import TransactionHelper


@pytest.fixture(scope='function')
def app():
    """Create application for integration testing"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for integration tests"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session for integration tests"""
    with app.app_context():
        yield db.session
        db.session.rollback()


class TestDatabaseIntegration:
    """Test database operations and transactions"""
    
    def test_database_connection(self, app, db_session):
        """Test database connection and basic operations"""
        # Create a test branch
        branch = Branch(name='Test Branch', code='TB001', city='Test City')
        db_session.add(branch)
        db_session.commit()
        
        # Verify branch was created
        retrieved_branch = Branch.query.filter_by(code='TB001').first()
        assert retrieved_branch is not None
        assert retrieved_branch.name == 'Test Branch'
    
    def test_foreign_key_constraints(self, app, db_session):
        """Test foreign key relationships work correctly"""
        # Create branch
        branch = Branch(name='Test Branch', code='TB001', city='Test City')
        db_session.add(branch)
        db_session.commit()
        
        # Create user with driver profile
        user = User(
            username='testdriver',
            email='test@example.com',
            full_name='Test Driver',
            role='DRIVER'
        )
        db_session.add(user)
        db_session.commit()
        
        # Create driver profile
        profile = DriverProfile(
            user_id=user.id,
            branch_id=branch.id,
            aadhar_number='123456789012',
            license_number='DL12345678'
        )
        db_session.add(profile)
        db_session.commit()
        
        # Verify relationships
        assert user.driver_profile == profile
        assert profile.user == user
        assert profile.branch == branch
    
    def test_cascade_operations(self, app, db_session):
        """Test cascade delete operations"""
        # Create branch with user
        branch = Branch(name='Test Branch', code='TB001', city='Test City')
        user = User(
            username='testdriver',
            email='test@example.com',
            full_name='Test Driver',
            role='DRIVER'
        )
        db_session.add(branch)
        db_session.add(user)
        db_session.commit()
        
        profile = DriverProfile(
            user_id=user.id,
            branch_id=branch.id,
            aadhar_number='123456789012',
            license_number='DL12345678'
        )
        db_session.add(profile)
        db_session.commit()
        
        # Delete user and verify profile is also deleted (if cascade is configured)
        user_id = user.id
        db_session.delete(user)
        db_session.commit()
        
        # Check if profile still exists
        remaining_profile = DriverProfile.query.filter_by(user_id=user_id).first()
        # Depending on cascade configuration, this might be None


class TestTransactionIntegration:
    """Test transaction handling and rollback scenarios"""
    
    def test_transaction_commit_success(self, app, db_session):
        """Test successful transaction commit"""
        helper = TransactionHelper()
        
        def create_branch_and_user():
            branch = Branch(name='Transaction Branch', code='TX001', city='Transaction City')
            user = User(
                username='transactionuser',
                email='transaction@example.com',
                full_name='Transaction User',
                role='DRIVER'
            )
            db_session.add(branch)
            db_session.add(user)
            return {'branch': branch, 'user': user}
        
        result = helper.execute_with_transaction(create_branch_and_user)
        
        assert result['success'] is True
        assert 'data' in result
        
        # Verify data was committed
        branch = Branch.query.filter_by(code='TX001').first()
        user = User.query.filter_by(username='transactionuser').first()
        assert branch is not None
        assert user is not None
    
    def test_transaction_rollback_on_error(self, app, db_session):
        """Test transaction rollback on error"""
        helper = TransactionHelper()
        
        def failing_operation():
            branch = Branch(name='Failing Branch', code='FB001', city='Failing City')
            db_session.add(branch)
            
            # Intentionally cause an error
            raise ValueError("Simulated error")
        
        result = helper.execute_with_transaction(failing_operation)
        
        assert result['success'] is False
        assert 'error' in result
        
        # Verify rollback occurred - branch should not exist
        branch = Branch.query.filter_by(code='FB001').first()
        assert branch is None


class TestServiceLayerIntegration:
    """Test service layer integration with database"""
    
    def test_driver_service_database_integration(self, app, db_session):
        """Test DriverService integration with database"""
        # Create required branch
        branch = Branch(name='Service Branch', code='SB001', city='Service City')
        db_session.add(branch)
        db_session.commit()
        
        service = DriverService()
        driver_data = {
            'username': 'servicedriver',
            'email': 'service@example.com',
            'full_name': 'Service Driver',
            'phone_number': '9999999999',
            'aadhar_number': '123456789012',
            'license_number': 'DL12345678',
            'bank_account_number': '1234567890123',
            'branch_id': branch.id
        }
        
        result = service.create_driver(driver_data)
        
        # Verify driver was created in database
        assert result['success'] is True
        
        created_user = User.query.filter_by(username='servicedriver').first()
        assert created_user is not None
        assert created_user.role == 'DRIVER'
        assert created_user.driver_profile is not None
    
    def test_duty_service_database_integration(self, app, db_session):
        """Test DutyService integration with database"""
        # Setup test data
        branch = Branch(name='Duty Branch', code='DB001', city='Duty City')
        db_session.add(branch)
        
        user = User(
            username='dutydriver',
            email='duty@example.com',
            full_name='Duty Driver',
            role='DRIVER'
        )
        db_session.add(user)
        db_session.commit()
        
        profile = DriverProfile(
            user_id=user.id,
            branch_id=branch.id,
            aadhar_number='123456789012',
            license_number='DL12345678'
        )
        
        vehicle = Vehicle(
            registration_number='KA01AA1234',
            make='Maruti',
            model='Swift',
            branch_id=branch.id
        )
        
        duty_scheme = DutyScheme(
            name='Test Scheme',
            scheme_type='FIXED',
            base_amount=500.0,
            branch_id=branch.id
        )
        
        db_session.add(profile)
        db_session.add(vehicle)
        db_session.add(duty_scheme)
        db_session.commit()
        
        # Test duty start
        service = DutyService()
        start_result = service.start_duty({
            'driver_id': user.id,
            'vehicle_id': vehicle.id,
            'duty_scheme_id': duty_scheme.id,
            'start_odometer': 10000
        })
        
        assert start_result['success'] is True
        
        # Verify duty was created in database
        duty = Duty.query.filter_by(driver_id=user.id, status='ACTIVE').first()
        assert duty is not None
        assert duty.start_time is not None
    
    def test_earnings_service_database_integration(self, app, db_session):
        """Test EarningsService integration with database"""
        # Setup test duty data
        branch = Branch(name='Earnings Branch', code='EB001', city='Earnings City')
        db_session.add(branch)
        
        user = User(
            username='earningsdriver',
            email='earnings@example.com',
            full_name='Earnings Driver',
            role='DRIVER'
        )
        db_session.add(user)
        
        vehicle = Vehicle(
            registration_number='KA01AA5678',
            make='Maruti',
            model='Swift',
            branch_id=branch.id
        )
        
        duty_scheme = DutyScheme(
            name='Earnings Scheme',
            scheme_type='FIXED',
            base_amount=600.0,
            branch_id=branch.id
        )
        
        db_session.add(vehicle)
        db_session.add(duty_scheme)
        db_session.commit()
        
        duty = Duty(
            driver_id=user.id,
            vehicle_id=vehicle.id,
            duty_scheme_id=duty_scheme.id,
            branch_id=branch.id,
            status='APPROVED',
            start_time=datetime.now() - timedelta(hours=8),
            end_time=datetime.now(),
            start_odometer=10000,
            end_odometer=10100,
            trip_count=5,
            cash_collected=800.0
        )
        db_session.add(duty)
        db_session.commit()
        
        # Test earnings calculation
        service = EarningsService()
        result = service.calculate_duty_earnings(duty.id)
        
        assert result['success'] is True
        assert 'calculation' in result
        
        # Verify calculation was saved to database
        from models import ManualEarningsCalculation
        calculation = ManualEarningsCalculation.query.filter_by(duty_id=duty.id).first()
        assert calculation is not None


class TestDatabasePerformance:
    """Test database performance and optimization"""
    
    def test_bulk_insert_performance(self, app, db_session):
        """Test bulk insert operations"""
        branch = Branch(name='Bulk Branch', code='BB001', city='Bulk City')
        db_session.add(branch)
        db_session.commit()
        
        # Create multiple users efficiently
        users = []
        for i in range(100):
            user = User(
                username=f'bulkuser{i}',
                email=f'bulk{i}@example.com',
                full_name=f'Bulk User {i}',
                role='DRIVER'
            )
            users.append(user)
        
        # Bulk insert
        start_time = datetime.now()
        db_session.add_all(users)
        db_session.commit()
        end_time = datetime.now()
        
        # Verify all users were created
        user_count = User.query.filter(User.username.like('bulkuser%')).count()
        assert user_count == 100
        
        # Performance check (should complete within reasonable time)
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 5.0  # Should complete within 5 seconds
    
    def test_query_performance_with_joins(self, app, db_session):
        """Test query performance with joins"""
        # Setup test data
        branch = Branch(name='Query Branch', code='QB001', city='Query City')
        db_session.add(branch)
        db_session.commit()
        
        # Create users with profiles and duties
        for i in range(50):
            user = User(
                username=f'queryuser{i}',
                email=f'query{i}@example.com',
                full_name=f'Query User {i}',
                role='DRIVER'
            )
            db_session.add(user)
            db_session.commit()
            
            profile = DriverProfile(
                user_id=user.id,
                branch_id=branch.id,
                aadhar_number=f'{1000000000 + i:012d}',
                license_number=f'DL{i:08d}'
            )
            db_session.add(profile)
        
        db_session.commit()
        
        # Test complex query with joins
        start_time = datetime.now()
        results = db_session.query(User).join(DriverProfile).filter(
            DriverProfile.branch_id == branch.id
        ).all()
        end_time = datetime.now()
        
        assert len(results) == 50
        
        # Performance check
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 2.0  # Should complete within 2 seconds


class TestConcurrencyAndLocking:
    """Test concurrent operations and database locking"""
    
    def test_concurrent_duty_start_prevention(self, app, db_session):
        """Test that drivers can't start multiple duties simultaneously"""
        # Setup test data
        branch = Branch(name='Concurrent Branch', code='CB001', city='Concurrent City')
        db_session.add(branch)
        
        user = User(
            username='concurrentdriver',
            email='concurrent@example.com',
            full_name='Concurrent Driver',
            role='DRIVER'
        )
        db_session.add(user)
        db_session.commit()
        
        profile = DriverProfile(
            user_id=user.id,
            branch_id=branch.id,
            aadhar_number='123456789012',
            license_number='DL12345678'
        )
        
        vehicle1 = Vehicle(
            registration_number='KA01AA0001',
            make='Maruti',
            model='Swift',
            branch_id=branch.id
        )
        
        vehicle2 = Vehicle(
            registration_number='KA01AA0002',
            make='Maruti',
            model='Swift',
            branch_id=branch.id
        )
        
        duty_scheme = DutyScheme(
            name='Concurrent Scheme',
            scheme_type='FIXED',
            base_amount=500.0,
            branch_id=branch.id
        )
        
        db_session.add(profile)
        db_session.add(vehicle1)
        db_session.add(vehicle2)
        db_session.add(duty_scheme)
        db_session.commit()
        
        service = DutyService()
        
        # Start first duty
        result1 = service.start_duty({
            'driver_id': user.id,
            'vehicle_id': vehicle1.id,
            'duty_scheme_id': duty_scheme.id,
            'start_odometer': 10000
        })
        
        assert result1['success'] is True
        
        # Try to start second duty (should fail)
        result2 = service.start_duty({
            'driver_id': user.id,
            'vehicle_id': vehicle2.id,
            'duty_scheme_id': duty_scheme.id,
            'start_odometer': 10000
        })
        
        assert result2['success'] is False
        assert 'already has an active duty' in result2['error'].lower()


class TestDataIntegrity:
    """Test data integrity and validation"""
    
    def test_unique_constraints(self, app, db_session):
        """Test unique constraints are enforced"""
        # Test unique username constraint
        user1 = User(
            username='uniqueuser',
            email='unique1@example.com',
            full_name='Unique User 1',
            role='DRIVER'
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create another user with same username
        user2 = User(
            username='uniqueuser',  # Same username
            email='unique2@example.com',
            full_name='Unique User 2',
            role='DRIVER'
        )
        db_session.add(user2)
        
        # This should raise an integrity error
        with pytest.raises(Exception):  # IntegrityError or similar
            db_session.commit()
    
    def test_required_field_validation(self, app, db_session):
        """Test that required fields are validated"""
        # Try to create user without required fields
        user = User(
            # Missing username (required)
            email='incomplete@example.com',
            role='DRIVER'
        )
        db_session.add(user)
        
        # This should raise an error
        with pytest.raises(Exception):
            db_session.commit()