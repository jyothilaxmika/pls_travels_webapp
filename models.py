
from datetime import datetime, date
import json
from app import db
from flask_login import UserMixin
from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from enum import Enum
import uuid

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
    COMPLETED = 'completed'
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

# Association tables with additional metadata
manager_branches = db.Table('manager_branches',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('manager_id', db.Integer, db.ForeignKey('users.id'), nullable=False),
    db.Column('branch_id', db.Integer, db.ForeignKey('branches.id'), nullable=False),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow),
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
    phone = db.Column(db.String(20), index=True)
    profile_picture = db.Column(db.String(255))
    
    # Authentication and security
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    failed_login_attempts = db.Column(db.Integer, default=0)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    # Address
    current_address = db.Column(db.Text)
    permanent_address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    
    # Documents with enhanced tracking
    aadhar_number = db.Column(db.String(20), unique=True, index=True)
    aadhar_document = db.Column(db.String(255))
    aadhar_verified = db.Column(db.Boolean, default=False)
    aadhar_verified_at = db.Column(db.DateTime)
    
    license_number = db.Column(db.String(50), unique=True, index=True)
    license_document = db.Column(db.String(255))
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    duties = db.relationship('Duty', backref='driver', lazy=True)
    current_vehicle = db.relationship('Vehicle', foreign_keys=[current_vehicle_id])
    approver = db.relationship('User', foreign_keys=[approved_by], post_update=True)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vehicles = db.relationship('Vehicle', backref='vehicle_type_info', lazy=True)

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
    
    # Uber Fleet Integration
    uber_vehicle_id = db.Column(db.String(100), unique=True, index=True)  # Uber's vehicle ID
    uber_vehicle_uuid = db.Column(db.String(100), unique=True)  # Uber's vehicle UUID
    uber_sync_status = db.Column(db.String(20), default='none', index=True)  # none, synced, failed, pending
    uber_last_sync = db.Column(db.DateTime)  # Last successful sync timestamp
    uber_sync_error = db.Column(db.Text)  # Last sync error message
    uber_vehicle_data = db.Column(db.Text)  # JSON: Cached Uber vehicle data
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vehicle_type_obj = db.relationship('VehicleType', backref='vehicle_instances', lazy=True)
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    duties = db.relationship('Duty', backref='duty_scheme', lazy=True)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    driver = db.relationship('Driver', backref='penalties')
    duty = db.relationship('Duty', backref='penalties')
    applier = db.relationship('User', foreign_keys=[applied_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='assets')
    branch = db.relationship('Branch', backref='assets')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    returner = db.relationship('User', foreign_keys=[returned_by])

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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
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
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])
    
    def __repr__(self):
        return f'<UberIntegrationSettings enabled:{self.is_enabled}>'

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
