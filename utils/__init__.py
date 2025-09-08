# Utils package - import utility functions
import os
import base64
import io
from werkzeug.utils import secure_filename
from datetime import datetime

# Import the generate_employee_id function from utils.py
def generate_employee_id():
    """Generate unique employee ID for driver"""
    import random
    from models import Driver
    
    while True:
        # Generate format: EMP + 6 digit number
        employee_id = f"EMP{random.randint(100000, 999999)}"
        
        # Check if it already exists
        existing = Driver.query.filter_by(employee_id=employee_id).first()
        if not existing:
            return employee_id

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_earnings(duty_scheme, revenue, trip_count):
    """Calculate driver earnings based on duty scheme"""
    if not duty_scheme:
        return {'earnings': 0, 'bmg_applied': 0, 'incentive': 0}
    
    config = duty_scheme.get_config()
    earnings = 0
    bmg_applied = 0
    incentive = 0
    
    if duty_scheme.scheme_type == 'fixed':
        earnings = config.get('daily_amount', 0)
    
    elif duty_scheme.scheme_type == 'per_trip':
        earnings = config.get('per_trip_amount', 0) * trip_count
    
    elif duty_scheme.scheme_type == 'slab':
        slabs = config.get('slabs', [])
        for slab in slabs:
            slab_min = slab.get('min', 0)
            slab_max = slab.get('max', 999999)
            percentage = slab.get('percentage', 0) / 100
            
            if revenue > slab_min:
                applicable_revenue = min(revenue, slab_max) - slab_min
                earnings += applicable_revenue * percentage
                
                if revenue <= slab_max:
                    break
    
    elif duty_scheme.scheme_type == 'mixed':
        base_amount = config.get('base_amount', 0)
        percentage = config.get('percentage', 0) / 100
        incentive = revenue * percentage
        earnings = base_amount + incentive
    
    # Apply BMG if applicable
    if duty_scheme.bmg_amount and earnings < duty_scheme.bmg_amount:
        bmg_applied = duty_scheme.bmg_amount - earnings
        earnings = duty_scheme.bmg_amount
    
    return {
        'earnings': round(earnings, 2),
        'bmg_applied': round(bmg_applied, 2),
        'incentive': round(incentive, 2)
    }

def calculate_advanced_salary(entry):
    """Calculate advanced salary"""
    return 0  # Placeholder implementation

def process_camera_capture(image_data, user_id, document_type):
    """Process camera captured image"""
    return None  # Placeholder implementation
    
def process_file_upload(file, user_id, document_type, use_cloud=False):
    """Process file upload"""
    return None  # Placeholder implementation