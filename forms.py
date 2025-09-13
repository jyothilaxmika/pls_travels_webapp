from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField, FloatField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, ValidationError
from datetime import date

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
    
    # Document Uploads - Front and Back
    aadhar_photo_front = FileField('Aadhar Front', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    aadhar_photo_back = FileField('Aadhar Back', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo_front = FileField('License Front', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo_back = FileField('License Back', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
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
    
    aadhar_photo_front = FileField('Aadhar Front', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    aadhar_photo_back = FileField('Aadhar Back', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo_front = FileField('License Front', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
    license_photo_back = FileField('License Back', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images and PDFs only!')])
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
    scheme_type = SelectField('Salary Method', choices=[
        ('daily_payout', 'Daily Salary - Immediate payment after each duty'),
        ('monthly_payout', 'Monthly Salary - Accumulated earnings paid monthly'),
        ('performance_based', 'Performance Based - Earnings tied to targets and KPIs'),
        ('hybrid_commission', 'Hybrid Commission - Base + Commission + Bonuses'),
        ('revenue_sharing', 'Revenue Sharing - Percentage of total vehicle revenue'),
        ('fixed_salary', 'Fixed Salary - Guaranteed monthly amount'),
        ('piece_rate', 'Piece Rate - Payment per trip/task completed'),
        ('slab_incentive', 'Slab Incentive - Tiered earnings based on revenue slabs'),
        ('custom_formula', 'Custom Formula - User-defined calculation method')
    ], validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[Optional()], default=0)
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
    
    # Performance and bonus fields
    target_trips_daily = IntegerField('Daily Trip Target', validators=[Optional(), NumberRange(min=1)])
    target_revenue_daily = FloatField('Daily Revenue Target', validators=[Optional(), NumberRange(min=0)])
    bonus_per_extra_trip = FloatField('Bonus per Extra Trip', validators=[Optional(), NumberRange(min=0)])
    bonus_target_achievement = FloatField('Target Achievement Bonus', validators=[Optional(), NumberRange(min=0)])
    
    # Deduction management
    fuel_deduction_percent = FloatField('Fuel Deduction %', validators=[Optional(), NumberRange(min=0, max=100)])
    maintenance_deduction = FloatField('Maintenance Deduction', validators=[Optional(), NumberRange(min=0)])
    insurance_deduction = FloatField('Insurance Deduction', validators=[Optional(), NumberRange(min=0)])
    other_deductions = FloatField('Other Deductions', validators=[Optional(), NumberRange(min=0)])
    
    # Advanced salary components
    overtime_rate_multiplier = FloatField('Overtime Rate Multiplier', validators=[Optional(), NumberRange(min=1)], default=1.5)
    weekend_bonus_percent = FloatField('Weekend Bonus %', validators=[Optional(), NumberRange(min=0, max=100)])
    holiday_bonus_percent = FloatField('Holiday Bonus %', validators=[Optional(), NumberRange(min=0, max=100)])
    
    # Revenue sharing specifics
    revenue_share_percent = FloatField('Revenue Share %', validators=[Optional(), NumberRange(min=0, max=100)])
    company_expense_deduction = FloatField('Company Expense Deduction', validators=[Optional(), NumberRange(min=0)])
    
    # Fixed salary components
    fixed_monthly_salary = FloatField('Fixed Monthly Salary', validators=[Optional(), NumberRange(min=0)])
    allowances = FloatField('Monthly Allowances', validators=[Optional(), NumberRange(min=0)])
    
    # Editable calculation formula
    calculation_formula = TextAreaField('Custom Calculation Formula', 
                                      description='Enter mathematical formula using variables: uber_trips, uber_collected, operator_out, toll, advance, etc.',
                                      validators=[Optional()])
    
    def validate_scheme_type(self, field):
        """Custom validation for scheme-specific required fields"""
        scheme_type = field.data
        
        if scheme_type == 'daily_payout':
            if not self.daily_base_amount.data and not self.daily_incentive_percent.data:
                raise ValidationError('Daily payout requires either base amount or incentive percentage')
                
        elif scheme_type == 'monthly_payout':
            if not self.monthly_base_salary.data and not self.monthly_incentive_percent.data:
                raise ValidationError('Monthly payout requires either base salary or incentive percentage')
                
        elif scheme_type == 'performance_based':
            if not self.target_trips_daily.data or not self.target_revenue_daily.data:
                raise ValidationError('Performance based method requires both daily trip and revenue targets')
                
        elif scheme_type == 'hybrid_commission':
            if not self.base_amount.data or not self.incentive_percent.data:
                raise ValidationError('Hybrid commission requires both base amount and incentive percentage')
                
        elif scheme_type == 'revenue_sharing':
            if not self.revenue_share_percent.data:
                raise ValidationError('Revenue sharing requires a revenue share percentage')
                
        elif scheme_type == 'fixed_salary':
            if not self.fixed_monthly_salary.data:
                raise ValidationError('Fixed salary method requires a monthly salary amount')
                
        elif scheme_type == 'piece_rate':
            if not self.per_trip_amount.data:
                raise ValidationError('Piece rate method requires an amount per trip')
                
        elif scheme_type == 'slab_incentive':
            if not self.slab1_max.data or not self.slab1_percent.data:
                raise ValidationError('Slab incentive requires at least first slab configuration')
                
        elif scheme_type == 'custom_formula':
            if not self.calculation_formula.data or not self.calculation_formula.data.strip():
                raise ValidationError('Custom formula method requires a calculation formula')

class AssignmentTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    branch_id = SelectField('Branch', coerce=int, validators=[Optional()])
    
    # Template pattern configuration
    shift_pattern = SelectField('Shift Pattern', choices=[
        ('daily', 'Daily Recurring'),
        ('weekly', 'Weekly Recurring'),
        ('monthly', 'Monthly Recurring'),
        ('custom', 'Custom Pattern')
    ], default='weekly', validators=[DataRequired()])
    
    days_of_week = StringField('Days of Week', validators=[Optional()],
                              description='Comma-separated day numbers (1=Mon, 7=Sun), e.g., "1,2,3,4,5"')
    
    default_shift_type = SelectField('Default Shift Type', choices=[
        ('full_day', 'Full Day (24 Hours)'),
        ('morning', 'Morning Shift (6AM-2PM)'),
        ('evening', 'Evening Shift (2PM-10PM)'),
        ('night', 'Night Shift (10PM-6AM)')
    ], default='full_day', validators=[DataRequired()])
    
    # Template assignments data
    template_assignments = TextAreaField('Assignment Pattern (JSON)', validators=[Optional()],
                                       description='JSON format assignment pattern or leave empty to configure manually')
    
    is_default = BooleanField('Set as Default Template', default=False)

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

class ForgotPasswordRequestForm(FlaskForm):
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)], 
                       render_kw={"placeholder": "Enter your registered phone number"})

class ForgotPasswordVerifyForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[DataRequired(), Length(min=6, max=6)],
                                   render_kw={"placeholder": "Enter 6-digit code"})

class ForgotPasswordResetForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
