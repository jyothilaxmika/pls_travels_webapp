import os
import re
import math
import json
import base64
from datetime import datetime
from dataclasses import dataclass
from werkzeug.utils import secure_filename
from replit import object_storage
import uuid

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# Storage Configuration
STORAGE_BUCKETS = {
    'documents': 'pls-travels-documents',     # Aadhar, License, etc.
    'photos': 'pls-travels-photos',           # Profile photos
    'duty_captures': 'pls-travels-duty',      # Start/End duty photos
    'vehicle_images': 'pls-travels-vehicles', # Vehicle photos
    'assets': 'pls-travels-assets',           # General assets
    'reports': 'pls-travels-reports'          # Generated reports
}

class CloudStorageManager:
    """Manages cloud storage operations for PLS TRAVELS"""
    
    def __init__(self):
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Ensure all required buckets exist"""
        try:
            for bucket_name in STORAGE_BUCKETS.values():
                try:
                    # Try to create an object to check if bucket exists  
                    test_obj = object_storage.Object(f"{bucket_name}/test")
                    # If we can create the object, bucket exists (or will be created)
                    print(f"Bucket ready: {bucket_name}")
                except Exception as e:
                    print(f"Error with bucket {bucket_name}: {e}")
        except Exception as e:
            print(f"Error checking buckets: {e}")
    
    def upload_file(self, file_data, filename, bucket_type='assets', content_type=None):
        """
        Upload file to cloud storage
        
        Args:
            file_data: File data (bytes or base64 string)
            filename: Name of the file
            bucket_type: Type of bucket (documents, photos, duty_captures, etc.)
            content_type: MIME type of the file
            
        Returns:
            str: Cloud storage URL of uploaded file
        """
        try:
            bucket_name = STORAGE_BUCKETS.get(bucket_type, STORAGE_BUCKETS['assets'])
            
            # Generate unique filename
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)
            
            # Handle base64 data
            if isinstance(file_data, str) and file_data.startswith('data:'):
                # Extract base64 data from data URL
                header, encoded = file_data.split(',', 1)
                file_data = base64.b64decode(encoded)
                
                # Extract content type if not provided
                if not content_type and 'image/' in header:
                    content_type = header.split(';')[0].replace('data:', '')
            
            # Create object and upload
            obj = object_storage.Object(f"{bucket_name}/{unique_filename}")
            obj.upload_from_bytes(file_data)
            
            return f"gs://{bucket_name}/{unique_filename}"
            
        except Exception as e:
            print(f"Cloud upload error: {e}")
            return None
    
    def download_file(self, cloud_url):
        """Download file from cloud storage"""
        try:
            if not cloud_url.startswith('gs://'):
                return None
                
            # Parse bucket and filename from cloud URL
            parts = cloud_url.replace('gs://', '').split('/', 1)
            bucket_name, filename = parts[0], parts[1]
            
            obj = object_storage.Object(f"{bucket_name}/{filename}")
            return obj.download_as_bytes()
            
        except Exception as e:
            print(f"Cloud download error: {e}")
            return None
    
    def delete_file(self, cloud_url):
        """Delete file from cloud storage"""
        try:
            if not cloud_url.startswith('gs://'):
                return False
                
            parts = cloud_url.replace('gs://', '').split('/', 1)
            bucket_name, filename = parts[0], parts[1]
            
            obj = object_storage.Object(f"{bucket_name}/{filename}")
            obj.delete()
            return True
            
        except Exception as e:
            print(f"Cloud delete error: {e}")
            return False
    
    def list_files(self, bucket_type='assets', prefix=None):
        """List files in a bucket"""
        try:
            bucket_name = STORAGE_BUCKETS.get(bucket_type, STORAGE_BUCKETS['assets'])
            # For now, return empty list as listing isn't straightforward with Object approach
            return []
            
        except Exception as e:
            print(f"Cloud list error: {e}")
            return []
    
    def get_file_url(self, cloud_url):
        """Get public URL for file (if applicable)"""
        # In Replit Object Storage, files are private by default
        # This returns the cloud storage path for internal use
        return cloud_url

# Initialize global storage manager
storage_manager = CloudStorageManager()

@dataclass
class DutyEntry:
    """Driver duty entry for salary calculation"""
    driver_name: str
    car_number: str
    scheme: int              # 1 = 24H Revenue Share, 2 = 12H Monthly
    cash_collected: float = 0
    qr_payment: float = 0
    outside_cash: float = 0
    start_cng: int = 0
    end_cng: int = 0
    pass_deduction: float = 0
    days_worked: int = 0     # For Scheme 2
    daily_rate: int = 0      # 2000/2500/3000/3500/4000 (for Scheme 2)

class SalaryCalculator:
    """Advanced salary calculator supporting multiple compensation schemes"""
    INSURANCE = 90
    CNG_RATE = 90
    
    # Daily rate mapping to monthly salary
    MONTHLY_SALARY_MAP = {
        2000: 18000,
        2500: 21000,
        3000: 24000,
        3500: 27000,
        4000: 30000,
    }

    def calculate(self, entry: DutyEntry):
        """Calculate salary based on scheme type"""
        if entry.scheme == 1:
            return self._calculate_scheme1(entry)
        elif entry.scheme == 2:
            return self._calculate_scheme2(entry)
        else:
            raise ValueError("Invalid scheme. Use 1 or 2.")

    def _calculate_scheme1(self, entry: DutyEntry):
        """Scheme 1: 24H Revenue Share calculation"""
        total_earnings = entry.cash_collected + entry.qr_payment + entry.outside_cash

        # Driver share before deductions
        dsbd = min(total_earnings, 4500) * 0.30 + max(total_earnings - 4500, 0) * 0.70

        # CNG adjustment
        cng_diff = entry.start_cng - entry.end_cng
        cng_adjustment = cng_diff * self.CNG_RATE  # +ve = deduction, -ve = credit

        # Deductions
        deductions = self.INSURANCE + entry.pass_deduction + max(cng_adjustment, 0)

        # Final driver salary
        driver_salary = dsbd - deductions + (min(cng_adjustment, 0) * -1)

        # Company share
        company_share = total_earnings - dsbd

        return {
            "scheme": "Scheme 1 (24H Revenue Share)",
            "driver_name": entry.driver_name,
            "car_number": entry.car_number,
            "total_earnings": total_earnings,
            "driver_salary": round(driver_salary, 2),
            "company_share": round(company_share, 2),
            "cng_adjustment": cng_adjustment,
            "deductions": deductions,
            "dsbd": round(dsbd, 2)
        }

    def _calculate_scheme2(self, entry: DutyEntry):
        """Scheme 2: 12H Monthly Salary calculation"""
        monthly_salary = self.MONTHLY_SALARY_MAP.get(entry.daily_rate, 0)
        per_day_salary = monthly_salary / 30
        final_salary = per_day_salary * entry.days_worked

        return {
            "scheme": "Scheme 2 (12H Monthly Salary)",
            "driver_name": entry.driver_name,
            "car_number": entry.car_number,
            "monthly_salary": monthly_salary,
            "days_worked": entry.days_worked,
            "per_day_salary": round(per_day_salary, 2),
            "driver_salary": round(final_salary, 2),
            "company_share": 0
        }

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

def calculate_salary_with_formula(duty, formula):
    """
    Calculate driver salary using editable formula with duty data
    
    Available variables:
    - shift_date: duty.actual_start.date() if duty.actual_start else None
    - vehicle_number: duty.vehicle.registration_number
    - uber_trips: duty.uber_trips
    - uber_collected: duty.uber_collected
    - operator_out: duty.operator_out
    - cng_average: duty.cng_average
    - cng_point: duty.cng_point
    - toll: duty.toll_expense
    - qr_payment: duty.qr_payment
    - company_pay: duty.company_pay
    - advance: duty.advance_deduction
    - cash_on_hand: duty.cash_collection
    - pass_amount: duty.pass_amount
    - insurance: duty.insurance_amount
    - start_cng: duty.start_cng
    - end_cng: duty.end_cng
    """
    if not formula or not duty:
        return 0.0
    
    try:
        # Create safe variable context
        variables = {
            'shift_date': duty.actual_start.date() if duty.actual_start else None,
            'vehicle_number': duty.vehicle.registration_number if duty.vehicle else '',
            'uber_trips': float(duty.uber_trips or 0),
            'uber_collected': float(duty.uber_collected or 0),
            'operator_out': float(duty.operator_out or 0),
            'cng_average': float(duty.cng_average or 0),
            'cng_point': duty.cng_point or '',
            'toll': float(duty.toll_expense or 0),
            'qr_payment': float(duty.qr_payment or 0),
            'company_pay': float(duty.company_pay or 0),
            'advance': float(duty.advance_deduction or 0),
            'cash_on_hand': float(duty.cash_collection or 0),
            'pass_amount': float(duty.pass_amount or 0),
            'insurance': float(duty.insurance_amount or 0),
            'start_cng': float(duty.start_cng or 0),
            'end_cng': float(duty.end_cng or 0),
            # Mathematical functions
            'abs': abs,
            'max': max,
            'min': min,
            'round': round,
            'sum': sum,
            'math': math
        }
        
        # Sanitize formula (allow only safe operations)
        safe_formula = re.sub(r'[^a-zA-Z0-9_+\-*/().= <>\s]', '', formula)
        
        # Evaluate formula safely
        result = eval(safe_formula, {"__builtins__": {}}, variables)
        return float(result) if result is not None else 0.0
        
    except Exception as e:
        # Log error and return 0 for safety
        print(f"Formula calculation error: {e}")
        return 0.0

def calculate_advanced_salary(duty_data, scheme_type=1, daily_rate=3000, days_worked=30):
    """
    Advanced salary calculation using the new scheme system
    
    Args:
        duty_data: Duty object with financial data
        scheme_type: 1 for Revenue Share, 2 for Monthly Salary
        daily_rate: Daily rate for scheme 2 (2000, 2500, 3000, 3500, 4000)
        days_worked: Number of days worked for scheme 2
    
    Returns:
        Dictionary with comprehensive salary calculation
    """
    calculator = SalaryCalculator()
    
    # Extract data from duty object
    driver_name = duty_data.driver.full_name if hasattr(duty_data, 'driver') and duty_data.driver else "Unknown"
    car_number = duty_data.vehicle.registration_number if hasattr(duty_data, 'vehicle') and duty_data.vehicle else "Unknown"
    
    # Create duty entry
    entry = DutyEntry(
        driver_name=driver_name,
        car_number=car_number,
        scheme=scheme_type,
        cash_collected=duty_data.cash_collection or 0,
        qr_payment=duty_data.qr_payment or 0,
        outside_cash=duty_data.digital_payments or 0,
        start_cng=int(duty_data.start_cng or 0),
        end_cng=int(duty_data.end_cng or 0),
        pass_deduction=duty_data.penalty_deduction or 0,
        days_worked=days_worked,
        daily_rate=daily_rate
    )
    
    return calculator.calculate(entry)

def calculate_tripsheet(duty_data):
    """
    Comprehensive tripsheet calculation for driver salary and company profit
    
    Args:
        duty_data: Dictionary or Duty object with financial data
    
    Returns:
        Dictionary with all calculated financial values
    """
    # Handle both dictionary input and Duty model object
    if hasattr(duty_data, '__dict__'):
        # Convert Duty object to dictionary
        data = {
            'company_pay': duty_data.company_pay or 0,
            'cash_collected': duty_data.cash_collection or 0,
            'qr_payment': duty_data.qr_payment or 0,
            'outside_cash': duty_data.digital_payments or 0,
            'operator_bill': duty_data.operator_out or 0,
            'toll': duty_data.toll_expense or 0,
            'petrol_expenses': duty_data.fuel_expense or 0,
            'gas_expenses': duty_data.other_expenses or 0,
            'other_expenses': duty_data.maintenance_expense or 0,
            'advance': duty_data.advance_deduction or 0,
            'driver_expenses': duty_data.fuel_deduction or 0,
            'pass_deduction': duty_data.penalty_deduction or 0,
        }
    else:
        data = duty_data

    # 1. Base salary (guarantee)
    company_pay = data.get("company_pay", 0)

    # 2. Incentive (only if earnings > operator bill)
    incentive = max(data.get("cash_collected", 0) - data.get("operator_bill", 0), 0)

    # 3. Deductions
    advance = data.get("advance", 0)
    driver_expenses = data.get("driver_expenses", 0)
    pass_deduction = data.get("pass_deduction", 0)

    # 4. Final Driver Salary
    driver_salary = company_pay + incentive - (advance + driver_expenses + pass_deduction)

    # 5. Company Earnings (all collected amounts)
    earnings = (
        data.get("cash_collected", 0)
        + data.get("qr_payment", 0)
        + data.get("outside_cash", 0)
    )

    # 6. Company Expenses
    expenses = (
        data.get("operator_bill", 0)
        + data.get("toll", 0)
        + data.get("petrol_expenses", 0)
        + data.get("gas_expenses", 0)
        + data.get("other_expenses", 0)
    )

    # 7. Company Profit
    company_profit = earnings - (driver_salary + expenses)

    return {
        "company_pay": round(company_pay, 2),
        "incentive": round(incentive, 2),
        "advance": round(advance, 2),
        "driver_expenses": round(driver_expenses, 2),
        "pass_deduction": round(pass_deduction, 2),
        "driver_salary": round(driver_salary, 2),
        "company_earnings": round(earnings, 2),
        "company_expenses": round(expenses, 2),
        "company_profit": round(company_profit, 2),
    }

def format_currency(amount):
    """Format amount as Indian currency"""
    return f"₹{amount:,.2f}"

def get_file_url(filename):
    """Get URL for uploaded file - now supports both local and cloud storage"""
    if filename:
        if filename.startswith('gs://'):
            # Cloud storage URL - return as is for internal processing
            return filename
        else:
            # Legacy local file
            return f"/uploads/{filename}"
    return None

def ensure_upload_dir():
    """Ensure upload directory exists (for legacy local storage)"""
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir

def upload_to_cloud(file_data, original_filename, bucket_type='assets', content_type=None):
    """
    Upload file to cloud storage with automatic bucket selection
    
    Args:
        file_data: File data (bytes, file object, or base64 string)
        original_filename: Original filename
        bucket_type: Type of content (documents, photos, duty_captures, vehicle_images, assets, reports)
        content_type: MIME type
        
    Returns:
        str: Cloud storage URL or None if failed
    """
    return storage_manager.upload_file(file_data, original_filename, bucket_type, content_type)

def download_from_cloud(cloud_url):
    """Download file from cloud storage"""
    return storage_manager.download_file(cloud_url)

def delete_from_cloud(cloud_url):
    """Delete file from cloud storage"""
    return storage_manager.delete_file(cloud_url)

def process_file_upload(file, user_id, photo_type="photo", use_cloud=True):
    """
    Process traditional file upload with optional cloud storage
    
    Args:
        file: Flask file object from request.files
        user_id: User ID for filename generation
        photo_type: Type of photo for filename (e.g., 'aadhar', 'license', 'profile')
        use_cloud: Whether to use cloud storage (default: True)
    
    Returns:
        str: Cloud URL or local filename if successful, None if failed
    """
    try:
        if not file or not allowed_file(file.filename):
            return None
            
        # Read file data
        file_data = file.read()
        if not file_data:
            return None
            
        # Determine bucket type based on photo type
        bucket_map = {
            'aadhar': 'documents',
            'license': 'documents', 
            'profile': 'photos',
            'duty_start': 'duty_captures',
            'duty_end': 'duty_captures',
            'vehicle': 'vehicle_images'
        }
        bucket_type = bucket_map.get(photo_type, 'assets')
        
        if use_cloud:
            # Try cloud upload first
            cloud_url = upload_to_cloud(file_data, file.filename, bucket_type)
            if cloud_url:
                return cloud_url
        
        # Fallback to local storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{photo_type}_{user_id}_{timestamp}_{file.filename}")
        
        upload_dir = ensure_upload_dir()
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
            
        return filename
        
    except Exception as e:
        print(f"Error processing file upload for {photo_type}: {e}")
        return None

def process_camera_capture(form_data, field_name, user_id, photo_type="photo", use_cloud=True):
    """
    Process camera capture data (base64 image + metadata) and save to file
    
    Args:
        form_data: Flask request.form object
        field_name: Name of the photo field (e.g., 'aadhar_photo', 'start_photo')
        user_id: User ID for filename generation
        photo_type: Type of photo for filename (e.g., 'aadhar', 'license', 'profile', 'duty_start', 'duty_end')
        use_cloud: Whether to use cloud storage (default: True)
    
    Returns:
        tuple: (filename_or_cloud_url, metadata) or (None, None) if no data
    """
    data_key = f"{field_name}_data"
    metadata_key = f"{field_name}_metadata"
    
    # Check if camera capture data exists
    if data_key not in form_data:
        return None, None
    
    try:
        # Get base64 image data
        image_data = form_data[data_key]
        if not image_data or not image_data.startswith('data:image/'):
            return None, None
        
        # Extract metadata if available
        metadata = {}
        if metadata_key in form_data:
            try:
                metadata = json.loads(form_data[metadata_key])
            except json.JSONDecodeError:
                metadata = {}
        
        # Parse base64 data
        header, encoded = image_data.split(',', 1)
        # Determine file extension from header
        if 'jpeg' in header or 'jpg' in header:
            ext = 'jpg'
        elif 'png' in header:
            ext = 'png'
        elif 'webp' in header:
            ext = 'webp'
        else:
            ext = 'jpg'  # Default
        
        # Decode base64 image
        image_bytes = base64.b64decode(encoded)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{photo_type}_{user_id}_{timestamp}.{ext}")
        
        # Determine bucket type based on photo type
        bucket_map = {
            'aadhar': 'documents',
            'license': 'documents', 
            'profile': 'photos',
            'duty_start': 'duty_captures',
            'duty_end': 'duty_captures',
            'vehicle': 'vehicle_images'
        }
        bucket_type = bucket_map.get(photo_type, 'assets')
        
        result_path = None
        
        if use_cloud:
            # Try cloud upload first
            cloud_url = upload_to_cloud(image_bytes, filename, bucket_type)
            if cloud_url:
                result_path = cloud_url
        
        if not result_path:
            # Fallback to local storage
            upload_dir = ensure_upload_dir()
            file_path = os.path.join(upload_dir, filename)
            
            # Save image file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            result_path = filename
        
        # Save metadata as separate JSON file if metadata exists
        if metadata:
            metadata_filename = secure_filename(f"{photo_type}_{user_id}_{timestamp}_metadata.json")
            metadata_path = os.path.join(upload_dir, metadata_filename)
            
            # Add processed timestamp to metadata
            metadata['processed_at'] = datetime.now().isoformat()
            metadata['filename'] = filename
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return result_path, metadata
        
    except Exception as e:
        print(f"Error processing camera capture for {field_name}: {e}")
        return None, None

def get_photo_metadata(filename):
    """
    Get metadata for a photo if it exists
    
    Args:
        filename: Photo filename
    
    Returns:
        dict: Metadata dictionary or empty dict if not found
    """
    if not filename:
        return {}
    
    try:
        # Construct metadata filename
        name, ext = os.path.splitext(filename)
        metadata_filename = f"{name}_metadata.json"
        metadata_path = os.path.join(ensure_upload_dir(), metadata_filename)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    return {}
