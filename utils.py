import os
import re
import math
from werkzeug.utils import secure_filename

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
            'cash_collected': duty_data.cash_collected or 0,
            'qr_payment': duty_data.qr_payment or 0,
            'outside_cash': duty_data.outside_cash or 0,
            'operator_bill': duty_data.operator_bill or 0,
            'toll': duty_data.toll or 0,
            'petrol_expenses': duty_data.petrol_expenses or 0,
            'gas_expenses': duty_data.gas_expenses or 0,
            'other_expenses': duty_data.other_expenses or 0,
            'advance': duty_data.advance or 0,
            'driver_expenses': duty_data.driver_expenses or 0,
            'pass_deduction': duty_data.pass_deduction or 0,
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
    """Get URL for uploaded file"""
    if filename:
        return f"/uploads/{filename}"
    return None

def ensure_upload_dir():
    """Ensure upload directory exists"""
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir
