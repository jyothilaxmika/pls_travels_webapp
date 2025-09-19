"""
Unit test configuration and fixtures for PLS TRAVELS application
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta

# Set test environment before importing app
os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'true',
    'SESSION_SECRET': 'test_secret_key_for_testing_only',
    'JWT_SECRET_KEY': 'test_jwt_secret_for_testing_only',
    'DATABASE_URL': 'sqlite:///:memory:',
    'TWILIO_ACCOUNT_SID': 'test_sid',
    'TWILIO_AUTH_TOKEN': 'test_token',
    'TWILIO_PHONE_NUMBER': '+1234567890'
})

from app import create_app, db
from models import User, DriverProfile, Vehicle, Duty, Branch, DutyScheme, Penalty, Bonus, ManualEarningsCalculation
import factory
from factory import Faker
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SERVER_NAME': 'localhost.localdomain'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        yield db.session
        db.session.rollback()


# Factory classes for test data generation
class BranchFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Branch
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Branch {n}")
    code = factory.Sequence(lambda n: f"BR{n:03d}")
    city = Faker('city')
    address = Faker('address')


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password_hash = factory.LazyFunction(lambda: generate_password_hash('testpass123'))
    role = 'DRIVER'
    full_name = Faker('name')
    phone_number = Faker('phone_number')
    status = 'ACTIVE'


class AdminUserFactory(UserFactory):
    role = 'ADMIN'
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.Sequence(lambda n: f"admin{n}@test.com")


class ManagerUserFactory(UserFactory):
    role = 'MANAGER'
    username = factory.Sequence(lambda n: f"manager{n}")
    email = factory.Sequence(lambda n: f"manager{n}@test.com")


class DriverProfileFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = DriverProfile
        sqlalchemy_session_persistence = "commit"

    aadhar_number = factory.Sequence(lambda n: f"{1000000000 + n:012d}")
    license_number = factory.Sequence(lambda n: f"DL{n:08d}")
    bank_account_number = factory.Sequence(lambda n: f"{1000000000 + n:013d}")
    emergency_contact = Faker('phone_number')
    date_of_birth = factory.LazyFunction(lambda: datetime.now().date() - timedelta(days=9125))  # 25 years ago


class VehicleFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Vehicle
        sqlalchemy_session_persistence = "commit"

    registration_number = factory.Sequence(lambda n: f"KA01AA{n:04d}")
    make = "Maruti"
    model = "Swift Dzire"
    year = 2022
    status = 'ACTIVE'
    fuel_type = 'PETROL'


class DutySchemeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = DutyScheme
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Scheme {n}")
    scheme_type = 'FIXED'
    base_amount = 500.00
    commission_percentage = 15.0
    requires_approval = False
    is_active = True


class DutyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Duty
        sqlalchemy_session_persistence = "commit"

    status = 'PENDING'
    start_odometer = 10000
    end_odometer = 10050
    trip_count = 5
    cash_collected = 500.00
    fuel_expense = 200.00


class PenaltyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Penalty
        sqlalchemy_session_persistence = "commit"

    amount = 100.00
    reason = "Late submission"
    status = 'APPROVED'


class BonusFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Bonus
        sqlalchemy_session_persistence = "commit"

    amount = 200.00
    reason = "Excellent performance"
    status = 'APPROVED'


# Fixtures for test data
@pytest.fixture
def branch(db_session):
    """Create test branch"""
    branch = BranchFactory()
    db_session.add(branch)
    db_session.commit()
    return branch


@pytest.fixture
def admin_user(db_session):
    """Create admin user"""
    user = AdminUserFactory()
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def manager_user(db_session, branch):
    """Create manager user"""
    user = ManagerUserFactory()
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def driver_user(db_session, branch):
    """Create driver user with profile"""
    user = UserFactory()
    profile = DriverProfileFactory(user=user, branch=branch)
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    return user


@pytest.fixture
def vehicle(db_session, branch):
    """Create test vehicle"""
    vehicle = VehicleFactory(branch=branch)
    db_session.add(vehicle)
    db_session.commit()
    return vehicle


@pytest.fixture
def duty_scheme(db_session, branch):
    """Create test duty scheme"""
    scheme = DutySchemeFactory(branch=branch)
    db_session.add(scheme)
    db_session.commit()
    return scheme


@pytest.fixture
def duty(db_session, driver_user, vehicle, duty_scheme):
    """Create test duty"""
    duty = DutyFactory(
        driver=driver_user,
        vehicle=vehicle,
        duty_scheme=duty_scheme,
        branch=driver_user.driver_profile.branch
    )
    db_session.add(duty)
    db_session.commit()
    return duty


@pytest.fixture
def authenticated_client(client, driver_user):
    """Client with authenticated driver"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(driver_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Client with authenticated admin"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client


# Mock data for testing
@pytest.fixture
def sample_file_upload():
    """Create a temporary file for upload testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        tmp.write(b"fake image data")
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def mock_otp_verification(monkeypatch):
    """Mock OTP verification for testing"""
    def mock_verify(*args, **kwargs):
        return True
    monkeypatch.setattr('services.notification_service.NotificationService.verify_otp', mock_verify)