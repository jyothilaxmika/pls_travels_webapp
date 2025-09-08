from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField, FloatField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class RegisterForm(FlaskForm):
    # Account Credentials
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('driver', 'Driver'), ('manager', 'Manager')], default='driver')
    
    # Driver Profile Information (for drivers only)
    full_name = StringField('Full Name', validators=[Optional()])
    phone = StringField('Primary Phone', validators=[Optional()])
    additional_phone_1 = StringField('Additional Phone 1', validators=[Optional()])
    additional_phone_2 = StringField('Additional Phone 2', validators=[Optional()])
    additional_phone_3 = StringField('Additional Phone 3', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    aadhar_number = StringField('Aadhar Number', validators=[Optional()])
    license_number = StringField('License Number', validators=[Optional()])
    
    # Bank Details
    bank_name = StringField('Bank Name', validators=[Optional()])
    account_number = StringField('Account Number', validators=[Optional()])
    ifsc_code = StringField('IFSC Code', validators=[Optional()])
    account_holder_name = StringField('Account Holder Name', validators=[Optional()])
    
    # Document Uploads
    aadhar_photo = FileField('Aadhar Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo = FileField('License Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    
    # Branch Selection
    branch = SelectField('Branch', coerce=int, validators=[Optional()])

class DriverForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address')
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired()])
    license_number = StringField('License Number', validators=[DataRequired()])
    bank_name = StringField('Bank Name')
    account_number = StringField('Account Number')
    ifsc_code = StringField('IFSC Code')
    account_holder_name = StringField('Account Holder Name')
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])

class DriverProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Primary Phone', validators=[DataRequired()])
    additional_phone_1 = StringField('Additional Phone 1')
    additional_phone_2 = StringField('Additional Phone 2') 
    additional_phone_3 = StringField('Additional Phone 3')
    address = TextAreaField('Address')
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired()])
    license_number = StringField('License Number', validators=[DataRequired()])
    bank_name = StringField('Bank Name')
    account_number = StringField('Account Number')
    ifsc_code = StringField('IFSC Code')
    account_holder_name = StringField('Account Holder Name')
    
    aadhar_photo = FileField('Aadhar Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo = FileField('License Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class VehicleAssignmentForm(FlaskForm):
    driver_id = SelectField('Driver', coerce=int, validators=[DataRequired()])
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    shift_type = SelectField('Shift Type', choices=[
        ('full_day', 'Full Day (24 Hours)'),
        ('morning', 'Morning Shift (6AM-2PM)'),
        ('evening', 'Evening Shift (2PM-10PM)'),
        ('night', 'Night Shift (10PM-6AM)')
    ], default='full_day')
    assignment_type = SelectField('Assignment Type', choices=[
        ('regular', 'Regular Assignment'),
        ('temporary', 'Temporary Assignment'),
        ('replacement', 'Replacement Assignment'),
        ('training', 'Training Assignment')
    ], default='regular')
    priority = SelectField('Priority', choices=[
        (1, 'High Priority'),
        (2, 'Medium Priority'),
        (3, 'Low Priority')
    ], coerce=int, default=2)
    assignment_notes = TextAreaField('Notes')
    
class ScheduledAssignmentForm(FlaskForm):
    # Multiple assignment scheduling
    assignments_data = TextAreaField('Assignments JSON', validators=[Optional()])
    bulk_start_date = DateField('Bulk Start Date', validators=[DataRequired()])
    bulk_end_date = DateField('Bulk End Date', validators=[Optional()])
    bulk_shift_type = SelectField('Default Shift Type', choices=[
        ('full_day', 'Full Day (24 Hours)'),
        ('morning', 'Morning Shift (6AM-2PM)'),
        ('evening', 'Evening Shift (2PM-10PM)'),
        ('night', 'Night Shift (10PM-6AM)')
    ], default='full_day')
    recurring_pattern = SelectField('Recurring Pattern', choices=[
        ('', 'No Recurrence'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], default='')
    recurring_until = DateField('Recurring Until', validators=[Optional()])
    
class QuickAssignmentForm(FlaskForm):
    date_range = StringField('Date Range', validators=[DataRequired()])
    drivers = StringField('Driver IDs', validators=[DataRequired()])
    vehicles = StringField('Vehicle IDs', validators=[DataRequired()])
    shift_type = SelectField('Shift Type', choices=[
        ('full_day', 'Full Day'),
        ('morning', 'Morning Shift'),
        ('evening', 'Evening Shift'),
        ('night', 'Night Shift')
    ], default='full_day')

class VehicleForm(FlaskForm):
    registration_number = StringField('Registration Number', validators=[DataRequired(), Length(min=3, max=20)])
    vehicle_type_id = SelectField('Vehicle Type', coerce=int, validators=[DataRequired()])
    model = StringField('Model', validators=[Optional(), Length(max=100)])
    manufacturing_year = IntegerField('Year', validators=[Optional(), NumberRange(min=1990, max=2030)])
    color = StringField('Color', validators=[Optional(), Length(max=30)])
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    
    insurance_number = StringField('Insurance Number', validators=[Optional(), Length(max=100)])
    insurance_expiry = DateField('Insurance Expiry', validators=[Optional()])
    fitness_expiry = DateField('Fitness Expiry', validators=[Optional()])
    permit_expiry = DateField('Permit Expiry', validators=[Optional()])
    
    fastag_number = StringField('FASTag Number', validators=[Optional(), Length(max=50)])
    device_imei = StringField('Device IMEI', validators=[Optional(), Length(max=20)])

class DutySchemeForm(FlaskForm):
    name = StringField('Scheme Name', validators=[DataRequired()])
    scheme_type = SelectField('Payout Scheme', choices=[
        ('daily_payout', 'Daily Salary Payout - Immediate payment after each duty'),
        ('monthly_payout', 'Monthly Payout - Accumulated earnings paid monthly'),
        ('scheme_3', 'Custom Scheme 3'),
        ('scheme_4', 'Custom Scheme 4'),
        ('scheme_5', 'Custom Scheme 5')
    ], validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=str, validators=[Optional()])
    bmg_amount = FloatField('BMG Amount', validators=[Optional(), NumberRange(min=0)])
    
    # Fixed scheme fields
    fixed_amount = FloatField('Daily Fixed Amount', validators=[Optional()])
    
    # Per trip scheme fields
    per_trip_amount = FloatField('Per Trip Amount', validators=[Optional()])
    
    # Slab scheme fields
    slab1_max = FloatField('Slab 1 Max Revenue', validators=[Optional()])
    slab1_percent = FloatField('Slab 1 Percentage', validators=[Optional()])
    slab2_max = FloatField('Slab 2 Max Revenue', validators=[Optional()])
    slab2_percent = FloatField('Slab 2 Percentage', validators=[Optional()])
    slab3_percent = FloatField('Slab 3 Percentage', validators=[Optional()])
    
    # Mixed scheme fields
    base_amount = FloatField('Base Amount', validators=[Optional()])
    incentive_percent = FloatField('Incentive Percentage', validators=[Optional()])
    
    # Payout frequency configuration
    payout_frequency = SelectField('Payout Frequency', choices=[
        ('immediate', 'Immediate - After each duty completion'),
        ('daily', 'Daily - At end of each day'),
        ('weekly', 'Weekly - Every Friday'),
        ('monthly', 'Monthly - Last day of month')
    ], default='immediate', validators=[Optional()])
    
    # Monthly payout specific fields
    monthly_base_salary = FloatField('Monthly Base Salary', validators=[Optional(), NumberRange(min=0)])
    monthly_incentive_percent = FloatField('Monthly Incentive Percentage', validators=[Optional(), NumberRange(min=0, max=100)])
    
    # Daily payout specific fields
    daily_base_amount = FloatField('Daily Base Amount', validators=[Optional(), NumberRange(min=0)])
    daily_incentive_percent = FloatField('Daily Incentive Percentage', validators=[Optional(), NumberRange(min=0, max=100)])
    
    # Effective dates
    effective_from = DateField('Effective From', default=date.today, validators=[DataRequired()])
    effective_until = DateField('Effective Until', validators=[Optional()])
    
    # Editable calculation formula
    calculation_formula = TextAreaField('Calculation Formula', 
                                      description='Enter mathematical formula using field names like uber_trips, uber_collected, etc.',
                                      validators=[Optional()])

class DutyForm(FlaskForm):
    vehicle_id = SelectField('Select Vehicle', coerce=int, validators=[DataRequired()])
    duty_scheme_id = SelectField('Duty Scheme (for salary calculation)', coerce=int, validators=[DataRequired()])
    start_odometer = FloatField('Starting Odometer Reading', validators=[DataRequired(), NumberRange(min=0)])
    start_photo = FileField('Start Duty Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class EndDutyForm(FlaskForm):
    end_odometer = FloatField('Ending Odometer Reading', validators=[DataRequired(), NumberRange(min=0)])
    
    # Basic trip data
    total_trips = IntegerField('Total Trips', validators=[DataRequired(), NumberRange(min=0)])
    
    # Uber/Rideshare data
    uber_trips = IntegerField('Uber Trips', validators=[Optional(), NumberRange(min=0)])
    uber_collected = FloatField('Uber Collected', validators=[Optional(), NumberRange(min=0)])
    
    # Revenue collection methods
    cash_collection = FloatField('Cash on Hand', validators=[Optional(), NumberRange(min=0)])
    qr_payment = FloatField('QR Payment', validators=[Optional(), NumberRange(min=0)])
    digital_payments = FloatField('Digital Payments', validators=[Optional(), NumberRange(min=0)])
    
    # Company and operator payments  
    operator_out = FloatField('Operator Out', validators=[Optional(), NumberRange(min=0)])
    company_pay = FloatField('Company Pay', validators=[Optional(), NumberRange(min=0)])
    
    # CNG tracking
    start_cng = FloatField('Start CNG', validators=[Optional(), NumberRange(min=0)])
    end_cng = FloatField('End CNG', validators=[Optional(), NumberRange(min=0)])
    cng_average = FloatField('CNG Average', validators=[Optional(), NumberRange(min=0)])
    cng_point = StringField('CNG Point', validators=[Optional(), Length(max=100)])
    
    # Expenses and deductions
    toll_expense = FloatField('Toll', validators=[Optional(), NumberRange(min=0)])
    advance_deduction = FloatField('Advance', validators=[Optional(), NumberRange(min=0)])
    pass_amount = FloatField('Pass', validators=[Optional(), NumberRange(min=0)])
    insurance_amount = FloatField('Insurance', validators=[Optional(), NumberRange(min=0)])
    
    # Photo verification
    end_photo = FileField('End Duty Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
