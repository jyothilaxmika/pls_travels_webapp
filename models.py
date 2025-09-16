
from datetime import datetime, date
import json
import pytz
from app import db
from flask_login import UserMixin
from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from enum import Enum
import uuid
import time
from timezone_utils import get_ist_time_naive

# Enums for better data integrity
class UserRole(Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    DRIVER = 'driver'

class UserStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'

class DriverStatus(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    REJECTED = 'rejected'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'

class VehicleStatus(Enum):
    ACTIVE = 'active'
    MAINTENANCE = 'maintenance'
    RETIRED = 'retired'
    OUT_OF_SERVICE = 'out_of_service'

class DutyStatus(Enum):
    SCHEDULED = 'scheduled'
    ACTIVE = 'active'
    PENDING_APPROVAL = 'pending_approval'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    PAUSED = 'paused'

class AssignmentStatus(Enum):
    SCHEDULED = 'scheduled'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class PaymentStatus(Enum):
    PENDING = 'pending'
    PROCESSED = 'processed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class ResignationStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class PhotoType(Enum):
    DUTY_START = 'duty_start'
    DUTY_END = 'duty_end'
    VEHICLE_INSPECTION = 'vehicle_inspection'
    INCIDENT_REPORT = 'incident'
    ODOMETER_READING = 'odometer'
    FUEL_RECEIPT = 'fuel_receipt'
    GENERAL = 'general'

# Association tables with additional metadata
manager_branches = db.Table('manager_branches',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('manager_id', db.Integer, db.ForeignKey('users.id'), nullable=False),
    db.Column('branch_id', db.Integer, db.ForeignKey('branches.id'), nullable=False),
    db.Column('assigned_at', db.DateTime, default=get_ist_time_naive),
    db.Column('assigned_by', db.Integer, db.ForeignKey('users.id')),
    db.Column('is_primary', db.Boolean, default=False),
    UniqueConstraint('manager_id', 'branch_id', name='unique_manager_branch')
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Enhanced user attributes
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.DRIVER, index=True)
    status = db.Column(db.Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True)
    
    # Profile information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20), unique=True, index=True)
    whatsapp_number = db.Column(db.String(20), index=True)  # Dedicated WhatsApp number
    profile_picture = db.Column(db.String(255))
    
    # Authentication and security
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    failed_login_attempts = db.Column(db.Integer, default=0)
    password_changed_at = db.Column(db.DateTime, default=get_ist_time_naive)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    
    # Password reset functionality
    reset_token = db.Column(db.String(6))
    reset_token_expiry = db.Column(db.DateTime)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=get_ist_time_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    driver_profile = db.relationship('Driver', foreign_keys='Driver.user_id', backref='user', uselist=False, cascade='all, delete-orphan')
    managed_branches = db.relationship('Branch', 
                                     secondary=manager_branches, 
                                     primaryjoin='User.id == manager_branches.c.manager_id',
                                     secondaryjoin='Branch.id == manager_branches.c.branch_id',
                                     backref='managers')
    
    @hybrid_property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'

class Region(db.Model):
    __tablename__ = 'regions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
    state = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False, default='India')
    timezone = db.Column(db.String(50), default='Asia/Kolkata')
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    branches = db.relationship('Branch', backref='region', lazy=True)

class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    
    # Location details
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    city = db.Column(db.String(50), nullable=False, index=True)
    address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Contact information
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    manager_name = db.Column(db.String(100))
    
    # Business metrics
    target_revenue_monthly = db.Column(db.Float, default=0.0)
    target_trips_daily = db.Column(db.Integer, default=0)
    operational_hours_start = db.Column(db.Time)
    operational_hours_end = db.Column(db.Time)
    
    # Status and settings
    is_active = db.Column(db.Boolean, default=True, index=True)
    auto_assignment_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    drivers = db.relationship('Driver', backref='branch', lazy=True)
    vehicles = db.relationship('Vehicle', backref='branch', lazy=True)
    duties = db.relationship('Duty', backref='branch', lazy=True)
    duty_schemes = db.relationship('DutyScheme', backref='branch', lazy=True)
    
    @hybrid_property
    def target_revenue(self):
        return self.target_revenue_monthly
    
    def __repr__(self):
        return f'<Branch {self.name}>'

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    
    # Personal Information
    full_name = db.Column(db.String(100), nullable=False, index=True)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Multiple contact numbers (stored as JSON array)
    additional_phones = db.Column(db.Text)  # JSON string of phone numbers
    
    # Address
    current_address = db.Column(db.Text)
    permanent_address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    
    # Documents with enhanced tracking
    aadhar_number = db.Column(db.String(20), unique=True, index=True)
    aadhar_document_front = db.Column(db.String(255))
    aadhar_document_back = db.Column(db.String(255))
    aadhar_verified = db.Column(db.Boolean, default=False)
    aadhar_verified_at = db.Column(db.DateTime)
    
    license_number = db.Column(db.String(50), unique=True, index=True)
    license_document_front = db.Column(db.String(255))
    license_document_back = db.Column(db.String(255))
    license_type = db.Column(db.String(20))  # LMV, HMV, etc.
    license_expiry = db.Column(db.Date)
    license_verified = db.Column(db.Boolean, default=False)
    license_verified_at = db.Column(db.DateTime)
    
    profile_photo = db.Column(db.String(255))
    
    # Bank Details with encryption consideration
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))  # Should be encrypted in production
    ifsc_code = db.Column(db.String(15))
    account_holder_name = db.Column(db.String(100))
    bank_verified = db.Column(db.Boolean, default=False)
    
    # Employment details
    join_date = db.Column(db.Date)
    probation_end_date = db.Column(db.Date)
    employment_type = db.Column(db.String(20), default='full_time')  # full_time, part_time, contract
    salary_type = db.Column(db.String(20), default='daily')  # daily, monthly, commission
    
    # Status and Approval
    status = db.Column(db.Enum(DriverStatus), nullable=False, default=DriverStatus.PENDING, index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    
    # Performance metrics
    total_earnings = db.Column(db.Float, default=0.0)
    total_trips = db.Column(db.Integer, default=0)
    total_distance = db.Column(db.Float, default=0.0)
    rating_average = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    
    # Current assignment
    current_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    current_shift_start = db.Column(db.DateTime)
    current_shift_end = db.Column(db.DateTime)
    
    # Uber Fleet Integration
    uber_driver_id = db.Column(db.String(100), unique=True, index=True)  # Uber's driver ID
    uber_driver_uuid = db.Column(db.String(100), unique=True)  # Uber's driver UUID
    uber_sync_status = db.Column(db.String(20), default='none', index=True)  # none, synced, failed, pending
    uber_last_sync = db.Column(db.DateTime)  # Last successful sync timestamp
    uber_sync_error = db.Column(db.Text)  # Last sync error message
    uber_profile_data = db.Column(db.Text)  # JSON: Cached Uber profile data
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    duties = db.relationship('Duty', backref='driver', lazy=True)
    current_vehicle = db.relationship('Vehicle', foreign_keys=[current_vehicle_id])
    approver = db.relationship('User', foreign_keys=[approved_by], post_update=True)
    
    # Note: user relationship is defined in User model as driver_profile
    
    def get_additional_phones(self):
        """Get list of additional phone numbers"""
        if self.additional_phones:
            try:
                return json.loads(self.additional_phones)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_additional_phones(self, phone_list):
        """Set additional phone numbers from list"""
        if phone_list:
            # Filter out empty strings
            filtered_phones = [phone.strip() for phone in phone_list if phone and phone.strip()]
            if filtered_phones:
                self.additional_phones = json.dumps(filtered_phones)
            else:
                self.additional_phones = None
        else:
            self.additional_phones = None
    
    def get_all_phones(self):
        """Get all phone numbers (primary + additional)"""
        phones = []
        # Use backref 'user' which is properly defined in the User model
        if hasattr(self, 'user') and self.user and self.user.phone:
            phones.append(self.user.phone)
        phones.extend(self.get_additional_phones())
        return phones
    
    # Indexes
    __table_args__ = (
        Index('idx_driver_status_branch', 'status', 'branch_id'),
        Index('idx_driver_created', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Driver {self.full_name}>'

class VehicleType(db.Model):
    __tablename__ = 'vehicle_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # Bus, Taxi, Auto, etc.
    category = db.Column(db.String(30), nullable=False)  # Public, Private, Commercial
    capacity_passengers = db.Column(db.Integer)
    fuel_type = db.Column(db.String(20))  # Petrol, Diesel, CNG, Electric
    base_fare = db.Column(db.Float, default=0.0)
    per_km_rate = db.Column(db.Float, default=0.0)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    # Relationships
    vehicles = db.relationship('Vehicle', backref='vehicle_type_info', lazy=True, overlaps="vehicle_instances,vehicle_type_obj")

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey('vehicle_types.id'), nullable=True)
    
    # Vehicle identification
    registration_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    chassis_number = db.Column(db.String(50), unique=True)
    engine_number = db.Column(db.String(50), unique=True)
    
    # Vehicle details
    make = db.Column(db.String(50))  # Maruti, Tata, etc.
    model = db.Column(db.String(100))
    variant = db.Column(db.String(50))
    manufacturing_year = db.Column(db.Integer)
    purchase_date = db.Column(db.Date)
    color = db.Column(db.String(30))
    
    # Capacity and specifications
    seating_capacity = db.Column(db.Integer)
    fuel_tank_capacity = db.Column(db.Float)
    mileage = db.Column(db.Float)  # km per liter
    
    # Insurance and compliance with enhanced tracking
    insurance_provider = db.Column(db.String(100))
    insurance_policy_number = db.Column(db.String(100))
    insurance_start_date = db.Column(db.Date)
    insurance_expiry_date = db.Column(db.Date, index=True)
    insurance_premium = db.Column(db.Float)
    
    fitness_certificate_number = db.Column(db.String(50))
    fitness_expiry_date = db.Column(db.Date, index=True)
    
    permit_number = db.Column(db.String(50))
    permit_type = db.Column(db.String(30))  # All India, State, City
    permit_expiry_date = db.Column(db.Date, index=True)
    
    pollution_certificate_number = db.Column(db.String(50))
    pollution_expiry_date = db.Column(db.Date)
    
    # Technology assets
    gps_device_id = db.Column(db.String(50))
    gps_sim_number = db.Column(db.String(20))
    fastag_id = db.Column(db.String(50))
    fastag_balance = db.Column(db.Float, default=0.0)
    
    # Operational status
    status = db.Column(db.Enum(VehicleStatus), nullable=False, default=VehicleStatus.ACTIVE, index=True)
    is_available = db.Column(db.Boolean, default=True, index=True)
    last_service_date = db.Column(db.Date)
    next_service_date = db.Column(db.Date)
    current_odometer = db.Column(db.Float, default=0.0)
    
    # Financial tracking
    purchase_price = db.Column(db.Float)
    current_market_value = db.Column(db.Float)
    total_maintenance_cost = db.Column(db.Float, default=0.0)
    
    # Vehicle documents storage
    registration_document = db.Column(db.String(255))  # Vehicle registration certificate
    insurance_document = db.Column(db.String(255))  # Insurance policy document  
    fitness_document = db.Column(db.String(255))  # Fitness certificate document
    permit_document = db.Column(db.String(255))  # Permit document
    pollution_document = db.Column(db.String(255))  # Pollution certificate document
    other_document = db.Column(db.String(255))  # Other important documents
    
    # Uber Fleet Integration
    uber_vehicle_id = db.Column(db.String(100), unique=True, index=True)  # Uber's vehicle ID
    uber_vehicle_uuid = db.Column(db.String(100), unique=True)  # Uber's vehicle UUID
    uber_sync_status = db.Column(db.String(20), default='none', index=True)  # none, synced, failed, pending
    uber_last_sync = db.Column(db.DateTime)  # Last successful sync timestamp
    uber_sync_error = db.Column(db.Text)  # Last sync error message
    uber_vehicle_data = db.Column(db.Text)  # JSON: Cached Uber vehicle data
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    vehicle_type_obj = db.relationship('VehicleType', backref=db.backref('vehicle_instances', overlaps="vehicles,vehicle_type_info"), lazy=True, overlaps="vehicle_type_info,vehicles")
    duties = db.relationship('Duty', backref='vehicle', lazy=True)
    maintenance_records = db.relationship('MaintenanceRecord', backref='vehicle', lazy=True)
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_vehicle_status_branch', 'status', 'branch_id'),
        Index('idx_vehicle_expiry_dates', 'insurance_expiry_date', 'fitness_expiry_date', 'permit_expiry_date'),
    )
    
    @hybrid_property
    def is_compliant(self):
        today = date.today()
        return (self.insurance_expiry_date and self.insurance_expiry_date > today and
                self.fitness_expiry_date and self.fitness_expiry_date > today and
                self.permit_expiry_date and self.permit_expiry_date > today)
    
    @hybrid_property
    def vehicle_type(self):
        return self.vehicle_type_obj.name if self.vehicle_type_obj else None
    
    @hybrid_property
    def year(self):
        return self.manufacturing_year
    
    @hybrid_property
    def insurance_number(self):
        return self.insurance_policy_number
    
    @hybrid_property
    def insurance_expiry(self):
        return self.insurance_expiry_date
    
    @hybrid_property
    def fitness_expiry(self):
        return self.fitness_expiry_date
    
    @hybrid_property
    def permit_expiry(self):
        return self.permit_expiry_date
    
    @hybrid_property
    def fastag_number(self):
        return self.fastag_id
    
    @hybrid_property
    def device_imei(self):
        return self.gps_device_id
    
    def __repr__(self):
        return f'<Vehicle {self.registration_number}>'

class DutyScheme(db.Model):
    __tablename__ = 'duty_schemes'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)  # NULL for global
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey('vehicle_types.id'), nullable=True)
    
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    scheme_type = db.Column(db.String(20), nullable=False, index=True)  # scheme_1, scheme_2, scheme_3, scheme_4, scheme_5
    
    # Configuration stored as JSON with validation
    configuration = db.Column(db.Text)  # JSON configuration
    
    # Editable calculation formula for this scheme
    calculation_formula = db.Column(db.Text)  # Mathematical formula for salary calculation
    
    # Minimum guarantees and limits
    minimum_guarantee = db.Column(db.Float, default=0.0)
    maximum_earning_cap = db.Column(db.Float)
    
    # Validity and scheduling
    effective_from = db.Column(db.Date, nullable=False)
    effective_until = db.Column(db.Date)
    applicable_days = db.Column(db.String(20), default='1,2,3,4,5,6,7')  # Comma-separated day numbers
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_default = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # === APPROVAL CONTROL SETTINGS ===
    # Whether duties using this scheme require admin approval
    requires_approval = db.Column(db.Boolean, default=False, index=True)
    
    # Auto-approval thresholds (if any threshold is exceeded, approval is required)
    auto_approve_max_revenue = db.Column(db.Float, default=10000.0)  # Max revenue for auto-approval
    auto_approve_max_trips = db.Column(db.Integer, default=50)  # Max trips for auto-approval  
    auto_approve_max_hours = db.Column(db.Float, default=12.0)  # Max duty hours for auto-approval
    
    # Risk factors that trigger approval requirements
    require_approval_on_anomaly = db.Column(db.Boolean, default=True)  # Unusual patterns
    require_approval_weekend = db.Column(db.Boolean, default=False)  # Weekend duties
    require_approval_night_shift = db.Column(db.Boolean, default=False)  # Night shifts (10pm-6am)
    
    # Approval notes and settings
    approval_notes = db.Column(db.Text)  # Instructions for approvers
    approval_priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    
    # Relationships
    duties = db.relationship('Duty', backref='duty_scheme', lazy=True)
    
    def needs_approval(self, duty_data):
        """Check if a duty with given data needs approval based on this scheme's settings"""
        if not self.requires_approval:
            return False, "Scheme doesn't require approval"
            
        # Check revenue threshold
        revenue = duty_data.get('revenue', 0)
        if revenue > self.auto_approve_max_revenue:
            return True, f"Revenue ₹{revenue:,.2f} exceeds threshold ₹{self.auto_approve_max_revenue:,.2f}"
            
        # Check trip count threshold
        trips = duty_data.get('trips', 0)
        if trips > self.auto_approve_max_trips:
            return True, f"Trip count {trips} exceeds threshold {self.auto_approve_max_trips}"
            
        # Check duty hours threshold
        hours = duty_data.get('hours', 0)
        if hours > self.auto_approve_max_hours:
            return True, f"Duty hours {hours:.1f} exceeds threshold {self.auto_approve_max_hours:.1f}"
            
        # Check weekend requirement
        if self.require_approval_weekend and duty_data.get('is_weekend', False):
            return True, "Weekend duty requires approval"
            
        # Check night shift requirement
        if self.require_approval_night_shift and duty_data.get('is_night_shift', False):
            return True, "Night shift duty requires approval"
            
        # Check for anomalies
        if self.require_approval_on_anomaly and duty_data.get('has_anomaly', False):
            return True, "Duty has detected anomalies"
            
        return False, "Auto-approved based on scheme settings"
    
    def get_configuration(self):
        return json.loads(self.configuration) if self.configuration else {}
    
    def set_configuration(self, config_dict):
        self.configuration = json.dumps(config_dict)
    
    def set_config(self, config_dict):
        """Alias for set_configuration for compatibility"""
        self.set_configuration(config_dict)
    
    @hybrid_property
    def bmg_amount(self):
        return self.minimum_guarantee
    
    def __repr__(self):
        return f'<DutyScheme {self.name}>'

class Duty(db.Model):
    __tablename__ = 'duties'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Core relationships
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    duty_scheme_id = db.Column(db.Integer, db.ForeignKey('duty_schemes.id'))
    
    # Timing with enhanced tracking
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    actual_start = db.Column(db.DateTime, index=True)
    actual_end = db.Column(db.DateTime)
    break_duration = db.Column(db.Integer, default=0)  # minutes
    
    # Location and verification data
    start_location_lat = db.Column(db.Float)
    start_location_lng = db.Column(db.Float)
    start_location_accuracy = db.Column(db.Float)
    start_photo = db.Column(db.String(255))
    start_odometer = db.Column(db.Float)
    
    end_location_lat = db.Column(db.Float)
    end_location_lng = db.Column(db.Float)
    end_location_accuracy = db.Column(db.Float)
    end_photo = db.Column(db.String(255))
    end_odometer = db.Column(db.Float)
    
    # Trip and performance data
    total_trips = db.Column(db.Integer, default=0)
    total_distance = db.Column(db.Float, default=0.0)
    total_passengers = db.Column(db.Integer, default=0)
    fuel_consumed = db.Column(db.Float, default=0.0)
    
    # Revenue breakdown (enhanced)
    cash_collection = db.Column(db.Float, default=0.0)  # CASH ON HAND
    digital_payments = db.Column(db.Float, default=0.0)
    card_payments = db.Column(db.Float, default=0.0)
    wallet_payments = db.Column(db.Float, default=0.0)
    
    # Uber/Rideshare specific fields
    uber_trips = db.Column(db.Integer, default=0)  # UBER TRIPS
    uber_collected = db.Column(db.Float, default=0.0)  # UBER COLLECTED
    
    # Payment methods
    qr_payment = db.Column(db.Float, default=0.0)  # QR PAYMENT
    
    # Operator and company payments
    operator_out = db.Column(db.Float, default=0.0)  # OPERATOR OUT
    company_pay = db.Column(db.Float, default=0.0)  # COMPANY PAY
    
    # CNG related fields
    start_cng = db.Column(db.Float, default=0.0)  # START CNG
    end_cng = db.Column(db.Float, default=0.0)  # END CNG
    cng_average = db.Column(db.Float, default=0.0)  # CNG AVERAGE
    cng_point = db.Column(db.String(100))  # CNG POINT
    
    # Other tracking fields
    pass_amount = db.Column(db.Float, default=0.0)  # PASS
    insurance_amount = db.Column(db.Float, default=0.0)  # INSURANCE
    
    # Company expenses (enhanced)
    fuel_expense = db.Column(db.Float, default=0.0)
    toll_expense = db.Column(db.Float, default=0.0)
    parking_expense = db.Column(db.Float, default=0.0)
    maintenance_expense = db.Column(db.Float, default=0.0)
    other_expenses = db.Column(db.Float, default=0.0)
    expense_description = db.Column(db.Text)
    
    # Driver payments and deductions
    base_payment = db.Column(db.Float, default=0.0)
    incentive_payment = db.Column(db.Float, default=0.0)
    bonus_payment = db.Column(db.Float, default=0.0)
    overtime_payment = db.Column(db.Float, default=0.0)
    
    advance_deduction = db.Column(db.Float, default=0.0)
    penalty_deduction = db.Column(db.Float, default=0.0)
    fuel_deduction = db.Column(db.Float, default=0.0)
    other_deductions = db.Column(db.Float, default=0.0)
    deduction_description = db.Column(db.Text)
    
    # Calculated totals
    gross_revenue = db.Column(db.Float, default=0.0)
    net_revenue = db.Column(db.Float, default=0.0)
    driver_earnings = db.Column(db.Float, default=0.0)
    company_profit = db.Column(db.Float, default=0.0)
    
    # Status and notes
    status = db.Column(db.Enum(DutyStatus), nullable=False, default=DutyStatus.SCHEDULED, index=True)
    notes = db.Column(db.Text)
    supervisor_notes = db.Column(db.Text)
    
    # Approval workflow
    submitted_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_duty_date_branch', 'actual_start', 'branch_id'),
        Index('idx_duty_status_driver', 'status', 'driver_id'),
        Index('idx_duty_revenue', 'gross_revenue', 'driver_earnings'),
    )
    
    @hybrid_property
    def duty_duration(self):
        if self.actual_start and self.actual_end:
            return self.actual_end - self.actual_start
        return None
    
    @hybrid_property
    def total_revenue(self):
        return (self.cash_collection or 0) + (self.digital_payments or 0) + (self.card_payments or 0) + (self.wallet_payments or 0)
    
    @hybrid_property
    def start_time(self):
        return self.actual_start
    
    @hybrid_property
    def revenue(self):
        return self.gross_revenue
    
    @hybrid_property
    def distance_km(self):
        return self.total_distance
    
    def __repr__(self):
        return f'<Duty {self.uuid}>'

class VehicleAssignment(db.Model):
    __tablename__ = 'vehicle_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    
    # Assignment period
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, index=True)
    shift_type = db.Column(db.String(20), default='full_day')  # full_day, morning, evening, night
    
    # Assignment details
    assignment_type = db.Column(db.String(20), default='regular')  # regular, temporary, replacement
    priority = db.Column(db.Integer, default=1)  # 1=high, 2=medium, 3=low
    notes = db.Column(db.Text)
    
    # Status tracking
    status = db.Column(db.Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.SCHEDULED, index=True)
    
    # Workflow
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    driver = db.relationship('Driver', backref='assignments')
    vehicle = db.relationship('Vehicle', backref='vehicle_assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    @hybrid_property
    def assignment_notes(self):
        return self.notes
    
    @hybrid_property
    def assignment_driver(self):
        return self.driver
    
    @hybrid_property
    def assignment_vehicle(self):
        return self.vehicle
    
    # Constraints
    __table_args__ = (
        Index('idx_assignment_dates', 'start_date', 'end_date'),
        CheckConstraint('end_date IS NULL OR end_date >= start_date'),
    )
    
    def __repr__(self):
        return f'<VehicleAssignment {self.driver.full_name} - {self.vehicle.registration_number}>'

class AssignmentTemplate(db.Model):
    __tablename__ = 'assignment_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Template identification
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    
    # Template configuration stored as JSON
    template_data = db.Column(db.Text)  # JSON with assignments pattern
    
    # Template metadata
    shift_pattern = db.Column(db.String(20))  # daily, weekly, monthly
    days_of_week = db.Column(db.String(20))  # 1,2,3,4,5,6,7 for Mon-Sun
    default_shift_type = db.Column(db.String(20), default='full_day')
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    # Audit fields
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    branch = db.relationship('Branch', backref='assignment_templates')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def get_template_data(self):
        import json
        return json.loads(self.template_data) if self.template_data else {}
    
    def set_template_data(self, data_dict):
        import json
        self.template_data = json.dumps(data_dict)
    
    def __repr__(self):
        return f'<AssignmentTemplate {self.name}>'

class PaymentRecord(db.Model):
    __tablename__ = 'payment_records'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    
    # Payment details
    payment_period_start = db.Column(db.Date, nullable=False)
    payment_period_end = db.Column(db.Date, nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # salary, incentive, bonus, reimbursement
    
    # Amounts
    gross_amount = db.Column(db.Float, nullable=False)
    deductions = db.Column(db.Float, default=0.0)
    tax_deduction = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, nullable=False)
    
    # Payment method
    payment_method = db.Column(db.String(20), nullable=False)  # bank_transfer, cash, cheque
    transaction_reference = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Notes
    description = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    # Relationships
    driver = db.relationship('Driver', backref='payment_records')
    processor = db.relationship('User', foreign_keys=[processed_by])
    
    __table_args__ = (
        Index('idx_payment_period_driver', 'payment_period_start', 'payment_period_end', 'driver_id'),
    )

class MaintenanceRecord(db.Model):
    __tablename__ = 'maintenance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    
    # Maintenance details
    maintenance_type = db.Column(db.String(30), nullable=False)  # routine, repair, accident, inspection
    description = db.Column(db.Text, nullable=False)
    odometer_reading = db.Column(db.Float)
    
    # Service details
    service_provider = db.Column(db.String(100))
    service_location = db.Column(db.String(200))
    mechanic_name = db.Column(db.String(100))
    
    # Dates
    scheduled_date = db.Column(db.Date)
    start_date = db.Column(db.Date, nullable=False)
    completion_date = db.Column(db.Date)
    next_service_due = db.Column(db.Date)
    
    # Financial
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    parts_cost = db.Column(db.Float, default=0.0)
    labor_cost = db.Column(db.Float, default=0.0)
    
    # Documentation
    invoice_number = db.Column(db.String(50))
    warranty_period = db.Column(db.Integer)  # days
    
    # Status
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_progress, completed, cancelled
    priority = db.Column(db.String(10), default='medium')  # high, medium, low
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])

class Penalty(db.Model):
    __tablename__ = 'penalties'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=True)
    
    # Penalty details
    penalty_type = db.Column(db.String(30), nullable=False)  # late_arrival, absence, violation, damage
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Evidence and documentation
    evidence_photos = db.Column(db.Text)  # JSON array of photo URLs
    witness_details = db.Column(db.Text)
    incident_date = db.Column(db.DateTime)
    incident_location = db.Column(db.String(200))
    
    # Workflow
    applied_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    disputed_by_driver = db.Column(db.Boolean, default=False)
    dispute_reason = db.Column(db.Text)
    
    # Status and resolution
    status = db.Column(db.String(20), default='pending')  # pending, active, waived, disputed, resolved
    waived_amount = db.Column(db.Float, default=0.0)
    waived_reason = db.Column(db.Text)
    
    applied_at = db.Column(db.DateTime, default=get_ist_time_naive)
    approved_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    driver = db.relationship('Driver', backref='penalties')
    duty = db.relationship('Duty', backref='penalties')
    applier = db.relationship('User', foreign_keys=[applied_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

class ResignationRequest(db.Model):
    __tablename__ = 'resignation_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    
    # Resignation details
    reason = db.Column(db.String(500), nullable=False)
    detailed_reason = db.Column(db.Text)
    preferred_last_working_date = db.Column(db.Date, nullable=False)
    actual_last_working_date = db.Column(db.Date)  # Set when approved
    
    # Document handover
    handover_notes = db.Column(db.Text)
    documents_returned = db.Column(db.Boolean, default=False)
    vehicle_returned = db.Column(db.Boolean, default=False)
    assets_returned = db.Column(db.Boolean, default=False)
    
    # 30-day notice period tracking
    notice_period_start = db.Column(db.Date)  # When admin approves
    notice_period_end = db.Column(db.Date)    # 30 days from start
    is_notice_period_waived = db.Column(db.Boolean, default=False)
    waiver_reason = db.Column(db.Text)
    
    # Financial settlement
    final_settlement_amount = db.Column(db.Float)
    pending_dues = db.Column(db.Float, default=0.0)
    settlement_notes = db.Column(db.Text)
    
    # Status and workflow
    status = db.Column(db.Enum(ResignationStatus), nullable=False, default=ResignationStatus.PENDING, index=True)
    
    # Admin actions
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    admin_comments = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    
    # Timestamps
    submitted_at = db.Column(db.DateTime, default=get_ist_time_naive)
    approved_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    driver = db.relationship('Driver', backref='resignation_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    # Constraints
    __table_args__ = (
        Index('idx_resignation_status_date', 'status', 'submitted_at'),
        CheckConstraint('actual_last_working_date IS NULL OR actual_last_working_date >= preferred_last_working_date'),
        CheckConstraint('notice_period_end IS NULL OR notice_period_end >= notice_period_start'),
    )
    
    def __repr__(self):
        return f'<ResignationRequest {self.driver.full_name if self.driver else "Unknown"} - {self.status.value}>'
    
    @hybrid_property
    def is_notice_period_active(self):
        if not self.notice_period_start or not self.notice_period_end:
            return False
        today = date.today()
        return self.notice_period_start <= today <= self.notice_period_end
    
    @hybrid_property
    def days_remaining_in_notice(self):
        if not self.notice_period_end:
            return None
        today = date.today()
        return max(0, (self.notice_period_end - today).days)
    
    @hybrid_property
    def can_be_completed(self):
        if self.status != ResignationStatus.APPROVED:
            return False
        if self.is_notice_period_waived:
            return True
        return self.notice_period_end and date.today() >= self.notice_period_end

class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Asset identification
    asset_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    asset_type = db.Column(db.String(50), nullable=False)  # device, uniform, toolkit, etc.
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Assignment details
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    
    # Status and tracking
    status = db.Column(db.String(20), default='available')  # available, assigned, returned, lost, damaged
    condition = db.Column(db.String(20), default='good')  # good, fair, poor, damaged
    
    # Assignment tracking
    assigned_at = db.Column(db.DateTime)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    returned_at = db.Column(db.DateTime)
    returned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Financial details
    purchase_cost = db.Column(db.Float)
    purchase_date = db.Column(db.Date)
    depreciation_rate = db.Column(db.Float)  # annual percentage
    current_value = db.Column(db.Float)
    
    # Metadata
    serial_number = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    warranty_expiry = db.Column(db.Date)
    
    # Notes and documentation
    notes = db.Column(db.Text)
    photos = db.Column(db.Text)  # JSON array of photo URLs
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    driver = db.relationship('Driver', backref='assets')
    branch = db.relationship('Branch', backref='assets')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    returner = db.relationship('User', foreign_keys=[returned_by])

class ManualEarningsCalculation(db.Model):
    """
    Manual earnings calculation form for admin/manager audit review
    Stores gamified salary calculation data with auto-fetch from duty
    """
    __tablename__ = 'manual_earnings_calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Links to duty and user
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=False, index=True)
    calculated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # Admin/Manager who filled form
    
    # Scheme configuration
    scheme_type = db.Column(db.String(50), nullable=False, default='revenue_share')  # revenue_share, fixed_daily, custom
    
    # Income fields
    online_hours = db.Column(db.Float, default=0.0)  # Online hours worked
    uber_trips = db.Column(db.Integer, default=0)    # No of Uber Trips
    cash_collected = db.Column(db.Float, default=0.0)  # Cash collected
    cash_collected_2 = db.Column(db.Float, default=0.0)  # Cash collected 2
    operator_bill = db.Column(db.Float, default=0.0)    # Operator bill
    operator_bill_2 = db.Column(db.Float, default=0.0)  # Operator bill 2
    outside_cash_amount = db.Column(db.Float, default=0.0)  # Outside cash Amount
    outside_operator_bill = db.Column(db.Float, default=0.0)  # Outside operator bill
    qr_payment = db.Column(db.Float, default=0.0)      # QR payment
    
    # Deduction fields
    pass_deduction = db.Column(db.Float, default=0.0)  # PASS DEDUCTION
    advance_deduction = db.Column(db.Float, default=0.0)  # ADVANCE
    toll_expense = db.Column(db.Float, default=0.0)    # TOLL
    
    # CNG fields
    end_cng = db.Column(db.Float, default=0.0)         # END CNG
    start_cng = db.Column(db.Float, default=0.0)       # Auto-fetched from duty
    
    # Calculation results
    gross_earnings = db.Column(db.Float, default=0.0)     # Total before deductions
    total_deductions = db.Column(db.Float, default=0.0)   # Sum of all deductions
    net_earnings = db.Column(db.Float, default=0.0)       # Final driver earnings
    company_share = db.Column(db.Float, default=0.0)      # Company portion
    
    # Additional calculation details
    driver_share_percentage = db.Column(db.Float, default=70.0)  # Driver share %
    calculation_notes = db.Column(db.Text)                       # Manual notes
    
    # Auto-fetch indicators
    auto_fetched_fields = db.Column(db.Text)  # JSON list of fields auto-populated from duty
    
    # Status and workflow
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, draft
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)  # Reason for rejection
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_ist_time_naive, index=True)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    duty = db.relationship('Duty', backref='manual_calculations')
    calculated_by_user = db.relationship('User', foreign_keys=[calculated_by])  # Primary relationship for template compatibility
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<ManualEarningsCalculation {self.duty.driver.full_name if self.duty else "Unknown"} - ₹{self.net_earnings}>'
    
    @hybrid_property
    def driver_name(self):
        return self.duty.driver.full_name if self.duty and self.duty.driver else 'Unknown'
    
    @hybrid_property 
    def vehicle_number(self):
        return self.duty.vehicle.registration_number if self.duty and self.duty.vehicle else 'Unknown'
        
    @hybrid_property
    def total_income(self):
        """Calculate total income from all sources"""
        return (self.cash_collected + self.cash_collected_2 + 
                self.operator_bill + self.operator_bill_2 + 
                self.outside_cash_amount + self.outside_operator_bill + 
                self.qr_payment)
    
    def set_auto_fetched_fields(self, fields_list):
        """Store list of auto-fetched field names as JSON"""
        self.auto_fetched_fields = json.dumps(fields_list) if fields_list else None
    
    def get_auto_fetched_fields(self):
        """Get list of auto-fetched field names"""
        return json.loads(self.auto_fetched_fields) if self.auto_fetched_fields else []

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(100))
    
    # Action details
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), index=True)
    entity_id = db.Column(db.Integer)
    entity_uuid = db.Column(db.String(36))
    
    # Change tracking
    old_values = db.Column(db.Text)  # JSON
    new_values = db.Column(db.Text)  # JSON
    changed_fields = db.Column(db.Text)  # JSON array
    
    # Request context
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    request_url = db.Column(db.String(500))
    request_method = db.Column(db.String(10))
    
    # Additional metadata
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # milliseconds
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive, index=True)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    # Partitioning index for performance
    __table_args__ = (
        Index('idx_audit_date_user', 'created_at', 'user_id'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )

class VehicleTracking(db.Model):
    """
    Track vehicle odometer readings and CNG usage with full continuity
    """
    __tablename__ = 'vehicle_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Core relationships
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=True, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    
    # Tracking data with timestamps
    recorded_at = db.Column(db.DateTime, nullable=False, default=get_ist_time_naive, index=True)
    
    # Odometer tracking
    odometer_reading = db.Column(db.Float, nullable=False)
    odometer_type = db.Column(db.String(20), nullable=False)  # 'start', 'end', 'maintenance', 'manual'
    distance_traveled = db.Column(db.Float, default=0.0)  # Calculated from previous reading
    
    # CNG/Fuel tracking
    cng_level = db.Column(db.Float)  # CNG level in kg or percentage
    cng_point = db.Column(db.String(100))  # CNG station name/location
    cng_cost = db.Column(db.Float)  # Cost of CNG filled
    cng_quantity = db.Column(db.Float)  # Quantity filled in kg
    
    # Location data
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location_accuracy = db.Column(db.Float)
    location_name = db.Column(db.String(200))
    
    # Validation and continuity
    is_validated = db.Column(db.Boolean, default=False)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_at = db.Column(db.DateTime)
    continuity_error = db.Column(db.Text)  # Store any continuity issues
    
    # Additional metadata
    notes = db.Column(db.Text)
    source = db.Column(db.String(50), default='duty')  # 'duty', 'maintenance', 'manual', 'gps'
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    vehicle = db.relationship('Vehicle', backref='tracking_records')
    driver = db.relationship('Driver', backref='vehicle_tracking')
    duty = db.relationship('Duty', backref='tracking_record')
    validator = db.relationship('User', foreign_keys=[validated_by])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_vehicle_tracking_vehicle_date', 'vehicle_id', 'recorded_at'),
        Index('idx_vehicle_tracking_driver_date', 'driver_id', 'recorded_at'),
        Index('idx_vehicle_tracking_odometer', 'vehicle_id', 'odometer_reading'),
        Index('idx_vehicle_tracking_validation', 'is_validated', 'continuity_error'),
    )
    
    @classmethod
    def get_vehicle_continuity(cls, vehicle_id, start_date=None, end_date=None):
        """Get vehicle tracking records in chronological order for continuity analysis"""
        query = cls.query.filter_by(vehicle_id=vehicle_id)
        
        if start_date:
            query = query.filter(cls.recorded_at >= start_date)
        if end_date:
            query = query.filter(cls.recorded_at <= end_date)
            
        return query.order_by(cls.recorded_at.asc()).all()
    
    @classmethod
    def validate_continuity(cls, vehicle_id):
        """Validate odometer reading continuity for a vehicle"""
        records = cls.get_vehicle_continuity(vehicle_id)
        errors = []
        
        for i in range(1, len(records)):
            prev_record = records[i-1]
            curr_record = records[i]
            
            # Check if odometer is increasing
            if curr_record.odometer_reading < prev_record.odometer_reading:
                errors.append(f"Odometer decreased: {prev_record.odometer_reading} -> {curr_record.odometer_reading} on {curr_record.recorded_at}")
            
            # Check for large gaps (more than 1000km in one duty)
            distance_gap = curr_record.odometer_reading - prev_record.odometer_reading
            if distance_gap > 1000:
                errors.append(f"Large distance gap: {distance_gap}km between readings on {curr_record.recorded_at}")
        
        return errors
    
    @hybrid_property
    def fuel_efficiency(self):
        """Calculate fuel efficiency if CNG data is available"""
        if self.distance_traveled and self.cng_quantity and self.cng_quantity > 0:
            return round(self.distance_traveled / self.cng_quantity, 2)
        return None
    
    def __repr__(self):
        return f'<VehicleTracking Vehicle:{self.vehicle_id} Odometer:{self.odometer_reading}>'

class SystemConfiguration(db.Model):
    __tablename__ = 'system_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), nullable=False)  # string, integer, float, boolean, json
    category = db.Column(db.String(50), nullable=False)  # system, business, integration
    description = db.Column(db.Text)
    
    # Validation
    is_encrypted = db.Column(db.Boolean, default=False)
    validation_regex = db.Column(db.String(500))
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    
    # Metadata
    is_user_configurable = db.Column(db.Boolean, default=True)
    requires_restart = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])

class UberSyncJob(db.Model):
    """Track Uber API synchronization jobs"""
    __tablename__ = 'uber_sync_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Job details
    job_type = db.Column(db.String(50), nullable=False, index=True)  # vehicles, drivers, trips
    sync_direction = db.Column(db.String(20), nullable=False)  # to_uber, from_uber, bidirectional
    status = db.Column(db.String(20), default='pending', index=True)  # pending, running, completed, failed
    
    # Timing
    scheduled_at = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Results
    records_processed = db.Column(db.Integer, default=0)
    records_successful = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    
    # Error tracking
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON: Detailed error information
    
    # Configuration
    sync_config = db.Column(db.Text)  # JSON: Job-specific configuration
    
    # Metadata
    initiated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    # Relationships
    initiator = db.relationship('User', foreign_keys=[initiated_by])
    sync_logs = db.relationship('UberSyncLog', backref='sync_job', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UberSyncJob {self.job_type}:{self.status}>'

class UberSyncLog(db.Model):
    """Detailed logs for Uber sync operations"""
    __tablename__ = 'uber_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_job_id = db.Column(db.Integer, db.ForeignKey('uber_sync_jobs.id'), nullable=False, index=True)
    
    # Record details
    record_type = db.Column(db.String(30), nullable=False)  # driver, vehicle, trip
    local_record_id = db.Column(db.Integer)  # ID in our system
    uber_record_id = db.Column(db.String(100))  # ID in Uber's system
    
    # Operation details
    operation = db.Column(db.String(20), nullable=False)  # create, update, delete, sync
    status = db.Column(db.String(20), nullable=False, index=True)  # success, failed, skipped
    
    # Data
    request_data = db.Column(db.Text)  # JSON: Data sent to Uber
    response_data = db.Column(db.Text)  # JSON: Response from Uber
    error_message = db.Column(db.Text)
    
    # Timing
    timestamp = db.Column(db.DateTime, default=get_ist_time_naive, index=True)
    
    def __repr__(self):
        return f'<UberSyncLog {self.record_type}:{self.operation}:{self.status}>'

class UberIntegrationSettings(db.Model):
    """Configuration settings for Uber integration"""
    __tablename__ = 'uber_integration_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Integration status
    is_enabled = db.Column(db.Boolean, default=False)
    last_full_sync = db.Column(db.DateTime)
    sync_frequency_hours = db.Column(db.Integer, default=24)  # How often to sync
    
    # Sync preferences
    auto_sync_vehicles = db.Column(db.Boolean, default=True)
    auto_sync_drivers = db.Column(db.Boolean, default=True)
    auto_sync_trips = db.Column(db.Boolean, default=False)  # Might be resource intensive
    
    # Data mapping preferences
    sync_direction_vehicles = db.Column(db.String(20), default='bidirectional')  # to_uber, from_uber, bidirectional
    sync_direction_drivers = db.Column(db.String(20), default='to_uber')
    
    # Error handling
    max_retry_attempts = db.Column(db.Integer, default=3)
    error_notification_email = db.Column(db.String(120))
    
    # API limits and throttling
    api_calls_per_minute = db.Column(db.Integer, default=60)
    batch_size = db.Column(db.Integer, default=50)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])

class WhatsAppSettings(db.Model):
    """Configuration settings for WhatsApp integration"""
    __tablename__ = 'whatsapp_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # WhatsApp contact numbers (10-digit Indian numbers)
    primary_admin_whatsapp = db.Column(db.String(10))  # Main admin contact
    secondary_admin_whatsapp = db.Column(db.String(10))  # Backup admin contact
    manager_whatsapp = db.Column(db.String(10))  # Manager contact
    
    # Priority settings for advance requests
    priority_contact = db.Column(db.String(20), default='admin')  # admin, manager, both
    
    # Message settings
    is_enabled = db.Column(db.Boolean, default=True)
    include_location = db.Column(db.Boolean, default=True)  # Include GPS location in messages
    include_duty_details = db.Column(db.Boolean, default=True)  # Include duty info
    
    # Metadata
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])
    
    @classmethod
    def get_settings(cls):
        """Get the current WhatsApp settings (singleton pattern)"""
        settings = cls.query.first()
        if not settings:
            # Create default settings
            settings = cls(
                primary_admin_whatsapp=None,
                priority_contact='admin',
                is_enabled=True,
                include_location=True,
                include_duty_details=True
            )
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def get_contact_numbers(self):
        """Get list of contact numbers based on priority"""
        numbers = []
        
        if self.priority_contact == 'admin':
            if self.primary_admin_whatsapp:
                numbers.append(self.primary_admin_whatsapp)
            if self.secondary_admin_whatsapp:
                numbers.append(self.secondary_admin_whatsapp)
            if self.manager_whatsapp:
                numbers.append(self.manager_whatsapp)
        elif self.priority_contact == 'manager':
            if self.manager_whatsapp:
                numbers.append(self.manager_whatsapp)
            if self.primary_admin_whatsapp:
                numbers.append(self.primary_admin_whatsapp)
            if self.secondary_admin_whatsapp:
                numbers.append(self.secondary_admin_whatsapp)
        else:  # both
            contacts = []
            if self.primary_admin_whatsapp:
                contacts.append(self.primary_admin_whatsapp)
            if self.manager_whatsapp:
                contacts.append(self.manager_whatsapp)
            if self.secondary_admin_whatsapp:
                contacts.append(self.secondary_admin_whatsapp)
            numbers = contacts
            
        return [num for num in numbers if num]  # Filter out None values
    
    def __repr__(self):
        return f'<UberIntegrationSettings enabled:{self.is_enabled}>'

class Photo(db.Model):
    """Store photos captured during duties"""
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # File details
    filename = db.Column(db.String(255), nullable=False)
    local_file_path = db.Column(db.String(500))
    server_url = db.Column(db.String(500))
    
    # Photo metadata
    photo_type = db.Column(db.Enum(PhotoType), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Associations
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Upload status
    is_uploaded = db.Column(db.Boolean, default=False)
    upload_retry_count = db.Column(db.Integer, default=0)
    upload_error = db.Column(db.Text)
    
    # Timestamps
    timestamp = db.Column(db.BigInteger, default=lambda: int(time.time() * 1000))  # Milliseconds
    uploaded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    # Relationships
    duty = db.relationship('Duty', backref='photos')
    user = db.relationship('User', backref='photos')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_photo_duty_type', 'duty_id', 'photo_type'),
        Index('idx_photo_user_timestamp', 'user_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<Photo {self.filename}:{self.photo_type.value}>'

class TrackingSession(db.Model):
    __tablename__ = 'tracking_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    
    # Session details
    session_start = db.Column(db.DateTime, nullable=False, default=get_ist_time_naive)
    session_end = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Tracking configuration
    sampling_interval = db.Column(db.Integer, default=30)  # seconds
    min_distance = db.Column(db.Float, default=10.0)  # meters
    accuracy_threshold = db.Column(db.Float, default=50.0)  # meters
    
    # Session metadata
    total_points = db.Column(db.Integer, default=0)
    distance_covered = db.Column(db.Float, default=0.0)  # kilometers
    duration = db.Column(db.Integer, default=0)  # seconds
    
    # Device info
    device_info = db.Column(db.Text)  # JSON string with device details
    app_version = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    duty = db.relationship('Duty', backref='tracking_sessions')
    driver = db.relationship('Driver', backref='tracking_sessions')
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_tracking_session_active', 'is_active', 'session_start'),
        Index('idx_tracking_session_duty_driver', 'duty_id', 'driver_id'),
        # Prevent multiple active sessions per duty
        UniqueConstraint('duty_id', 'driver_id', 'is_active', name='uq_active_session_per_duty'),
    )
    
    def __repr__(self):
        return f'<TrackingSession duty:{self.duty_id} driver:{self.driver_id}>'

class DriverLocation(db.Model):
    __tablename__ = 'driver_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=True, index=True)
    tracking_session_id = db.Column(db.Integer, db.ForeignKey('tracking_sessions.id'), nullable=True, index=True)
    
    # Location data
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)  # meters
    speed = db.Column(db.Float, nullable=True)  # m/s
    bearing = db.Column(db.Float, nullable=True)  # degrees
    
    # Timestamps
    captured_at = db.Column(db.DateTime, nullable=False, index=True)
    received_at = db.Column(db.DateTime, nullable=False, default=get_ist_time_naive, index=True)
    
    # Device and source info
    source = db.Column(db.String(20), default='mobile')  # mobile, web, manual
    client_event_id = db.Column(db.String(100), nullable=True)  # for deduplication
    battery_level = db.Column(db.Integer, nullable=True)  # percentage
    is_mocked = db.Column(db.Boolean, default=False, index=True)
    
    # Additional metadata
    address = db.Column(db.String(500), nullable=True)  # reverse geocoded address
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # Network and signal info
    network_type = db.Column(db.String(20), nullable=True)  # wifi, cellular, etc.
    signal_strength = db.Column(db.Integer, nullable=True)
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    is_anonymized = db.Column(db.Boolean, default=False, index=True)  # For privacy compliance
    
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    # Relationships
    driver = db.relationship('Driver', backref='locations')
    duty = db.relationship('Duty', backref='location_points')
    tracking_session = db.relationship('TrackingSession', backref='location_points')
    
    # Indexes and constraints for performance and data integrity
    __table_args__ = (
        # Performance indexes for time-series queries
        Index('idx_driver_locations_driver_captured_desc', 'driver_id', 'captured_at'),
        Index('idx_driver_locations_duty_captured', 'duty_id', 'captured_at'),
        Index('idx_driver_locations_session_captured', 'tracking_session_id', 'captured_at'),
        Index('idx_driver_locations_source_mocked', 'source', 'is_mocked'),
        Index('idx_driver_locations_coords', 'latitude', 'longitude'),
        Index('idx_driver_locations_received_processed', 'received_at', 'is_processed'),
        
        # Data integrity constraints
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude_range'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude_range'),
        CheckConstraint('accuracy IS NULL OR accuracy >= 0', name='check_accuracy_positive'),
        CheckConstraint('speed IS NULL OR speed >= 0', name='check_speed_positive'),
        CheckConstraint('bearing IS NULL OR (bearing >= 0 AND bearing <= 360)', name='check_bearing_range'),
        CheckConstraint('battery_level IS NULL OR (battery_level >= 0 AND battery_level <= 100)', name='check_battery_range'),
        
        # Deduplication per driver
        UniqueConstraint('driver_id', 'client_event_id', name='uq_driver_event_id'),
    )
    
    def __repr__(self):
        return f'<DriverLocation driver:{self.driver_id} at {self.latitude},{self.longitude}>'
    
    @property
    def coordinates(self):
        """Return coordinates as [lat, lng] for mapping libraries"""
        return [self.latitude, self.longitude]
    
    def distance_from(self, other_location):
        """Calculate distance from another location in kilometers using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        if not other_location:
            return 0
            
        # Convert to radians
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other_location.latitude), radians(other_location.longitude)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r

class AdvancePaymentRequest(db.Model):
    """Model for tracking advance payment requests during duty"""
    __tablename__ = 'advance_payment_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False, index=True)
    
    # Request details
    amount_requested = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(100), default='fuel')  # fuel, maintenance, emergency
    notes = db.Column(db.Text)
    
    # WhatsApp integration fields
    admin_phone = db.Column(db.String(20))  # Phone number message was sent to
    whatsapp_message_sent = db.Column(db.Boolean, default=False)
    whatsapp_sent_at = db.Column(db.DateTime)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, cancelled
    response_notes = db.Column(db.Text)
    responded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    responded_at = db.Column(db.DateTime)
    
    # Amount actually approved/disbursed
    approved_amount = db.Column(db.Float, default=0.0)
    
    # Location where request was made
    request_lat = db.Column(db.Float)
    request_lng = db.Column(db.Float)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=get_ist_time_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_ist_time_naive, onupdate=get_ist_time_naive)
    
    # Relationships
    duty = db.relationship('Duty', backref='advance_requests')
    driver = db.relationship('Driver', backref='advance_payment_requests')
    responder = db.relationship('User', foreign_keys=[responded_by])
    
    def __repr__(self):
        return f'<AdvancePaymentRequest ₹{self.amount_requested} for Duty {self.duty_id}>'

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(db.Model):
    __tablename__ = 'oauth_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    browser_session_key = db.Column(db.String, nullable=False)
    token = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_time_naive)
    
    user = db.relationship('User', backref='oauth_tokens')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'browser_session_key', 'provider', 
                           name='uq_user_browser_session_key_provider'),
    )
    
    def __repr__(self):
        return f'<OAuth {self.provider}:{self.user_id}>'


# Create all indexes
def create_performance_indexes():
    """Create additional performance indexes"""
    # Composite indexes for common queries
    Index('idx_duty_date_status_branch', Duty.actual_start, Duty.status, Duty.branch_id)
    Index('idx_vehicle_status_available', Vehicle.status, Vehicle.is_available)
    Index('idx_driver_status_branch_active', Driver.status, Driver.branch_id, Driver.user_id)
    Index('idx_payment_status_period', PaymentRecord.status, PaymentRecord.payment_period_start)
    
    # Uber integration indexes
    Index('idx_uber_sync_job_type_status', UberSyncJob.job_type, UberSyncJob.status)
    Index('idx_uber_sync_log_timestamp', UberSyncLog.timestamp)
    Index('idx_uber_sync_log_record', UberSyncLog.record_type, UberSyncLog.local_record_id)
