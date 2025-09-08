# Utils package - import utility functions from main utils module
import os
import sys

# Add parent directory to path to import utils_main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import all functions from the main utils file
try:
    from utils_main import (
        calculate_tripsheet, 
        SalaryCalculator, 
        DutyEntry,
        calculate_earnings,
        calculate_advanced_salary,
        calculate_salary_with_formula,
        allowed_file,
        format_currency,
        get_file_url,
        ensure_upload_dir,
        upload_to_cloud,
        download_from_cloud,
        delete_from_cloud,
        process_file_upload,
        process_camera_capture,
        storage_manager,
        CloudStorageManager,
        STORAGE_BUCKETS,
        ALLOWED_EXTENSIONS
    )
    print("Successfully imported functions from utils_main")
except ImportError as e:
    print(f"Failed to import from utils_main: {e}")

# Also keep local functions for compatibility
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

# Local ALLOWED_EXTENSIONS for compatibility
if 'ALLOWED_EXTENSIONS' not in globals():
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# Local allowed_file function for compatibility
if 'allowed_file' not in globals():
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Local calculate_earnings function for compatibility
if 'calculate_earnings' not in globals():
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