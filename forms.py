from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField, FloatField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('driver', 'Driver'), ('manager', 'Manager')], default='driver')
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
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address')
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired()])
    license_number = StringField('License Number', validators=[DataRequired()])
    bank_name = StringField('Bank Name')
    account_number = StringField('Account Number')
    ifsc_code = StringField('IFSC Code')
    account_holder_name = StringField('Account Holder Name')
    
    aadhar_photo = FileField('Aadhar Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    license_photo = FileField('License Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class VehicleForm(FlaskForm):
    registration_number = StringField('Registration Number', validators=[DataRequired()])
    vehicle_type = SelectField('Vehicle Type', choices=[
        ('bus', 'Bus'),
        ('taxi', 'Taxi'),
        ('auto', 'Auto Rickshaw'),
        ('truck', 'Truck'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    model = StringField('Model')
    year = IntegerField('Year', validators=[Optional(), NumberRange(min=1990, max=2030)])
    color = StringField('Color')
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    
    insurance_number = StringField('Insurance Number')
    insurance_expiry = DateField('Insurance Expiry', validators=[Optional()])
    fitness_expiry = DateField('Fitness Expiry', validators=[Optional()])
    permit_expiry = DateField('Permit Expiry', validators=[Optional()])
    
    fastag_number = StringField('FASTag Number')
    device_imei = StringField('Device IMEI')

class DutySchemeForm(FlaskForm):
    name = StringField('Scheme Name', validators=[DataRequired()])
    scheme_type = SelectField('Scheme Type', choices=[
        ('fixed', 'Fixed Amount'),
        ('per_trip', 'Per Trip'),
        ('slab', 'Slab Based'),
        ('mixed', 'Mixed (BMG + Incentive)')
    ], validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[Optional()])
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

class DutyForm(FlaskForm):
    vehicle_id = SelectField('Select Vehicle', coerce=int, validators=[DataRequired()])
    start_odometer = FloatField('Starting Odometer Reading', validators=[DataRequired(), NumberRange(min=0)])
    start_photo = FileField('Start Duty Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class EndDutyForm(FlaskForm):
    end_odometer = FloatField('Ending Odometer Reading', validators=[DataRequired(), NumberRange(min=0)])
    revenue = FloatField('Total Revenue', validators=[DataRequired(), NumberRange(min=0)])
    trip_count = IntegerField('Number of Trips', validators=[DataRequired(), NumberRange(min=0)])
    fuel_amount = FloatField('Fuel Amount', validators=[Optional(), NumberRange(min=0)])
    end_photo = FileField('End Duty Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
