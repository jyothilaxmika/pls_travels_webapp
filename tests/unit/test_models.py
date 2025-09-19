"""
Unit tests for database models
"""

import pytest
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash

from models import User, DriverProfile, Vehicle, Duty, Branch, DutyScheme, Penalty, Bonus
from tests.unit.conftest import (
    BranchFactory, UserFactory, AdminUserFactory, DriverProfileFactory, 
    VehicleFactory, DutySchemeFactory, DutyFactory, PenaltyFactory, BonusFactory
)


class TestUserModel:
    """Test User model functionality"""
    
    def test_create_user(self, db_session):
        """Test user creation"""
        user = UserFactory()
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username is not None
        assert user.email is not None
        assert check_password_hash(user.password_hash, 'testpass123')
        assert user.created_at is not None
        
    def test_user_roles(self, db_session):
        """Test different user roles"""
        admin = AdminUserFactory()
        manager = UserFactory(role='MANAGER')
        driver = UserFactory(role='DRIVER')
        
        for user in [admin, manager, driver]:
            db_session.add(user)
        db_session.commit()
        
        assert admin.role == 'ADMIN'
        assert manager.role == 'MANAGER'
        assert driver.role == 'DRIVER'
    
    def test_user_is_active_property(self, db_session):
        """Test user active status"""
        active_user = UserFactory(status='ACTIVE')
        inactive_user = UserFactory(status='SUSPENDED')
        
        for user in [active_user, inactive_user]:
            db_session.add(user)
        db_session.commit()
        
        assert active_user.is_active is True
        assert inactive_user.is_active is False
    
    def test_user_string_representation(self, db_session):
        """Test user __str__ method"""
        user = UserFactory(username='testuser', full_name='Test User')
        db_session.add(user)
        db_session.commit()
        
        expected = 'testuser (Test User)'
        assert str(user) == expected


class TestDriverProfileModel:
    """Test DriverProfile model functionality"""
    
    def test_create_driver_profile(self, db_session, driver_user):
        """Test driver profile creation"""
        profile = driver_user.driver_profile
        
        assert profile is not None
        assert profile.user_id == driver_user.id
        assert profile.aadhar_number is not None
        assert profile.license_number is not None
        assert profile.bank_account_number is not None
        assert profile.date_of_birth is not None
    
    def test_driver_profile_age_calculation(self, db_session):
        """Test age calculation from date of birth"""
        birth_date = datetime.now().date() - timedelta(days=9125)  # ~25 years ago
        user = UserFactory()
        profile = DriverProfileFactory(user=user, date_of_birth=birth_date)
        
        db_session.add(user)
        db_session.add(profile)
        db_session.commit()
        
        # Age should be approximately 25 (allowing for some variation)
        assert 24 <= profile.age <= 26
    
    def test_driver_profile_relationships(self, db_session, branch):
        """Test driver profile relationships"""
        user = UserFactory()
        profile = DriverProfileFactory(user=user, branch=branch)
        
        db_session.add(user)
        db_session.add(profile)
        db_session.commit()
        
        assert profile.user == user
        assert profile.branch == branch
        assert user.driver_profile == profile


class TestVehicleModel:
    """Test Vehicle model functionality"""
    
    def test_create_vehicle(self, db_session, branch):
        """Test vehicle creation"""
        vehicle = VehicleFactory(branch=branch)
        db_session.add(vehicle)
        db_session.commit()
        
        assert vehicle.id is not None
        assert vehicle.registration_number is not None
        assert vehicle.make is not None
        assert vehicle.model is not None
        assert vehicle.status == 'ACTIVE'
        assert vehicle.branch_id == branch.id
    
    def test_vehicle_string_representation(self, db_session, branch):
        """Test vehicle __str__ method"""
        vehicle = VehicleFactory(
            registration_number='KA01AA1234',
            make='Maruti',
            model='Swift Dzire',
            branch=branch
        )
        db_session.add(vehicle)
        db_session.commit()
        
        expected = 'KA01AA1234 - Maruti Swift Dzire'
        assert str(vehicle) == expected


class TestDutyModel:
    """Test Duty model functionality"""
    
    def test_create_duty(self, db_session, driver_user, vehicle, duty_scheme):
        """Test duty creation"""
        duty = DutyFactory(
            driver=driver_user,
            vehicle=vehicle,
            duty_scheme=duty_scheme,
            branch=driver_user.driver_profile.branch
        )
        db_session.add(duty)
        db_session.commit()
        
        assert duty.id is not None
        assert duty.driver_id == driver_user.id
        assert duty.vehicle_id == vehicle.id
        assert duty.duty_scheme_id == duty_scheme.id
        assert duty.status == 'PENDING'
    
    def test_duty_duration_calculation(self, db_session, driver_user, vehicle, duty_scheme):
        """Test duty duration calculation"""
        start_time = datetime.now() - timedelta(hours=8)
        end_time = datetime.now()
        
        duty = DutyFactory(
            driver=driver_user,
            vehicle=vehicle,
            duty_scheme=duty_scheme,
            branch=driver_user.driver_profile.branch,
            start_time=start_time,
            end_time=end_time
        )
        db_session.add(duty)
        db_session.commit()
        
        # Duration should be approximately 8 hours
        duration = duty.duration_hours
        assert 7.9 <= duration <= 8.1  # Allow small variance
    
    def test_duty_distance_calculation(self, db_session, driver_user, vehicle, duty_scheme):
        """Test duty distance calculation"""
        duty = DutyFactory(
            driver=driver_user,
            vehicle=vehicle,
            duty_scheme=duty_scheme,
            branch=driver_user.driver_profile.branch,
            start_odometer=10000,
            end_odometer=10150
        )
        db_session.add(duty)
        db_session.commit()
        
        assert duty.distance_km == 150


class TestDutySchemeModel:
    """Test DutyScheme model functionality"""
    
    def test_create_duty_scheme(self, db_session, branch):
        """Test duty scheme creation"""
        scheme = DutySchemeFactory(branch=branch)
        db_session.add(scheme)
        db_session.commit()
        
        assert scheme.id is not None
        assert scheme.name is not None
        assert scheme.scheme_type is not None
        assert scheme.base_amount is not None
        assert scheme.is_active is True
    
    def test_duty_scheme_types(self, db_session, branch):
        """Test different duty scheme types"""
        fixed_scheme = DutySchemeFactory(scheme_type='FIXED', branch=branch)
        per_trip_scheme = DutySchemeFactory(scheme_type='PER_TRIP', branch=branch)
        slab_scheme = DutySchemeFactory(scheme_type='SLAB_BASED', branch=branch)
        
        for scheme in [fixed_scheme, per_trip_scheme, slab_scheme]:
            db_session.add(scheme)
        db_session.commit()
        
        assert fixed_scheme.scheme_type == 'FIXED'
        assert per_trip_scheme.scheme_type == 'PER_TRIP'
        assert slab_scheme.scheme_type == 'SLAB_BASED'


class TestBranchModel:
    """Test Branch model functionality"""
    
    def test_create_branch(self, db_session):
        """Test branch creation"""
        branch = BranchFactory()
        db_session.add(branch)
        db_session.commit()
        
        assert branch.id is not None
        assert branch.name is not None
        assert branch.code is not None
        assert branch.city is not None
        assert branch.created_at is not None
    
    def test_branch_string_representation(self, db_session):
        """Test branch __str__ method"""
        branch = BranchFactory(name='Main Branch', city='Bangalore')
        db_session.add(branch)
        db_session.commit()
        
        expected = 'Main Branch - Bangalore'
        assert str(branch) == expected


class TestPenaltyBonusModels:
    """Test Penalty and Bonus models"""
    
    def test_create_penalty(self, db_session, driver_user):
        """Test penalty creation"""
        penalty = PenaltyFactory(driver=driver_user)
        db_session.add(penalty)
        db_session.commit()
        
        assert penalty.id is not None
        assert penalty.driver_id == driver_user.id
        assert penalty.amount > 0
        assert penalty.reason is not None
        assert penalty.status == 'APPROVED'
    
    def test_create_bonus(self, db_session, driver_user):
        """Test bonus creation"""
        bonus = BonusFactory(driver=driver_user)
        db_session.add(bonus)
        db_session.commit()
        
        assert bonus.id is not None
        assert bonus.driver_id == driver_user.id
        assert bonus.amount > 0
        assert bonus.reason is not None
        assert bonus.status == 'APPROVED'


class TestModelRelationships:
    """Test model relationships and foreign keys"""
    
    def test_user_driver_profile_relationship(self, db_session, driver_user):
        """Test User -> DriverProfile relationship"""
        assert driver_user.driver_profile is not None
        assert driver_user.driver_profile.user_id == driver_user.id
        assert driver_user.driver_profile.user == driver_user
    
    def test_driver_duties_relationship(self, db_session, driver_user, vehicle, duty_scheme):
        """Test Driver -> Duties relationship"""
        duty1 = DutyFactory(driver=driver_user, vehicle=vehicle, duty_scheme=duty_scheme)
        duty2 = DutyFactory(driver=driver_user, vehicle=vehicle, duty_scheme=duty_scheme)
        
        db_session.add(duty1)
        db_session.add(duty2)
        db_session.commit()
        
        assert len(driver_user.duties) == 2
        assert duty1 in driver_user.duties
        assert duty2 in driver_user.duties
    
    def test_branch_relationships(self, db_session, branch):
        """Test Branch relationships"""
        # Create users and vehicles in the branch
        driver = UserFactory()
        profile = DriverProfileFactory(user=driver, branch=branch)
        vehicle = VehicleFactory(branch=branch)
        scheme = DutySchemeFactory(branch=branch)
        
        db_session.add(driver)
        db_session.add(profile)
        db_session.add(vehicle)
        db_session.add(scheme)
        db_session.commit()
        
        assert profile.branch_id == branch.id
        assert vehicle.branch_id == branch.id
        assert scheme.branch_id == branch.id