from datetime import datetime
import json
from app import db
from flask_login import UserMixin
from sqlalchemy import func

# Association table for manager-branch relationships
manager_branches = db.Table('manager_branches',
    db.Column('manager_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('branch_id', db.Integer, db.ForeignKey('branch.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False, default='driver')  # admin, manager, driver  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    driver_profile = db.relationship('Driver', foreign_keys='Driver.user_id', backref='user', uselist=False)
    managed_branches = db.relationship('Branch', secondary=manager_branches, backref='managers')

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text)
    contact_phone = db.Column(db.String(20))
    target_revenue = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    drivers = db.relationship('Driver', backref='branch', lazy=True)
    vehicles = db.relationship('Vehicle', backref='branch', lazy=True)
    duties = db.relationship('Duty', backref='branch', lazy=True)
    duty_schemes = db.relationship('DutyScheme', backref='branch', lazy=True)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    
    # Personal Information
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    
    # Documents
    aadhar_number = db.Column(db.String(20))
    aadhar_photo = db.Column(db.String(255))
    license_number = db.Column(db.String(50))
    license_photo = db.Column(db.String(255))
    profile_photo = db.Column(db.String(255))
    
    # Bank Details
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(15))
    account_holder_name = db.Column(db.String(100))
    
    # Status and Approval
    status = db.Column(db.String(20), default='pending')  # pending, active, rejected, suspended
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    
    # Performance
    total_earnings = db.Column(db.Float, default=0.0)
    current_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    duties = db.relationship('Duty', backref='driver', lazy=True)
    current_vehicle = db.relationship('Vehicle', foreign_keys=[current_vehicle_id])
    approver = db.relationship('User', foreign_keys=[approved_by], post_update=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    
    # Vehicle Details
    registration_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # bus, taxi, auto
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    color = db.Column(db.String(30))
    
    # Insurance and Compliance
    insurance_number = db.Column(db.String(100))
    insurance_expiry = db.Column(db.Date)
    fitness_expiry = db.Column(db.Date)
    permit_expiry = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, maintenance, retired
    is_available = db.Column(db.Boolean, default=True)
    
    # Assets
    fastag_number = db.Column(db.String(50))
    device_imei = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    duties = db.relationship('Duty', backref='vehicle', lazy=True)

class DutyScheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)  # NULL for global
    
    name = db.Column(db.String(100), nullable=False)
    scheme_type = db.Column(db.String(20), nullable=False)  # fixed, per_trip, slab, mixed
    config = db.Column(db.Text)  # JSON configuration
    bmg_amount = db.Column(db.Float, default=0.0)  # Business Minimum Guarantee
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_config(self):
        return json.loads(self.config) if self.config else {}
    
    def set_config(self, config_dict):
        self.config = json.dumps(config_dict)

class Duty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    duty_scheme_id = db.Column(db.Integer, db.ForeignKey('duty_scheme.id'))
    
    # Duty Details
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    start_photo = db.Column(db.String(255))
    end_photo = db.Column(db.String(255))
    start_odometer = db.Column(db.Float)
    end_odometer = db.Column(db.Float)
    
    # Financial
    revenue = db.Column(db.Float, default=0.0)
    driver_earnings = db.Column(db.Float, default=0.0)
    bmg_applied = db.Column(db.Float, default=0.0)
    incentive = db.Column(db.Float, default=0.0)
    penalty = db.Column(db.Float, default=0.0)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    
    # Trip Details
    trip_count = db.Column(db.Integer, default=0)
    distance_km = db.Column(db.Float, default=0.0)
    fuel_amount = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    duty_scheme = db.relationship('DutyScheme', backref='duties')

class Penalty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    duty_id = db.Column(db.Integer, db.ForeignKey('duty.id'), nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    applied_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    penalty_driver = db.relationship('Driver', backref='penalties')
    duty = db.relationship('Duty', backref='penalties')
    applied_by_user = db.relationship('User', backref='applied_penalties')

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    
    asset_type = db.Column(db.String(50), nullable=False)  # fastag, phone, device
    asset_id = db.Column(db.String(100), nullable=False)  # device number/IMEI
    description = db.Column(db.String(255))
    
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    returned_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='assigned')  # assigned, returned, lost
    
    # Relationships
    asset_driver = db.relationship('Driver', backref='assets')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    action = db.Column(db.String(100), nullable=False)  # login, approve_driver, start_duty, etc.
    entity_type = db.Column(db.String(50))  # driver, duty, vehicle
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON details
    
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_user = db.relationship('User', backref='audit_logs')
