#!/usr/bin/env python3
"""
Test script for the new advanced salary calculation system
"""

from utils import SalaryCalculator, DutyEntry

def test_salary_schemes():
    """Test both salary calculation schemes"""
    calculator = SalaryCalculator()
    
    print("🚖 PLS TRAVELS - Advanced Salary Calculation Test")
    print("=" * 50)
    
    # Test Scheme 1: 24H Revenue Share
    print("\n📊 SCHEME 1: 24H Revenue Share")
    print("-" * 30)
    
    entry1 = DutyEntry(
        driver_name="Muthu",
        car_number="TN09DE5595",
        scheme=1,
        cash_collected=4000,
        qr_payment=1754,
        outside_cash=0,
        start_cng=5,
        end_cng=3,
        pass_deduction=200
    )
    
    result1 = calculator.calculate(entry1)
    
    print(f"Driver: {result1['driver_name']}")
    print(f"Car: {result1['car_number']}")
    print(f"Total Earnings: ₹{result1['total_earnings']:.2f}")
    print(f"Driver Share Before Deductions: ₹{result1['dsbd']:.2f}")
    print(f"CNG Adjustment: ₹{result1['cng_adjustment']:.2f}")
    print(f"Total Deductions: ₹{result1['deductions']:.2f}")
    print(f"Final Driver Salary: ₹{result1['driver_salary']:.2f}")
    print(f"Company Share: ₹{result1['company_share']:.2f}")
    
    # Test Scheme 2: 12H Monthly Salary
    print("\n📊 SCHEME 2: 12H Monthly Salary")
    print("-" * 30)
    
    entry2 = DutyEntry(
        driver_name="Sakthi",
        car_number="TN09DD4700",
        scheme=2,
        days_worked=26,
        daily_rate=3000
    )
    
    result2 = calculator.calculate(entry2)
    
    print(f"Driver: {result2['driver_name']}")
    print(f"Car: {result2['car_number']}")
    print(f"Monthly Salary: ₹{result2['monthly_salary']:.2f}")
    print(f"Per Day Rate: ₹{result2['per_day_salary']:.2f}")
    print(f"Days Worked: {result2['days_worked']}")
    print(f"Final Driver Salary: ₹{result2['driver_salary']:.2f}")
    
    # Test different daily rates
    print("\n📊 SCHEME 2: Different Daily Rates")
    print("-" * 30)
    
    for rate in [2000, 2500, 3000, 3500, 4000]:
        entry_test = DutyEntry(
            driver_name="Test Driver",
            car_number="TEST001",
            scheme=2,
            days_worked=30,
            daily_rate=rate
        )
        result_test = calculator.calculate(entry_test)
        print(f"Daily Rate ₹{rate} → Monthly: ₹{result_test['monthly_salary']:,} → 30 Days: ₹{result_test['driver_salary']:,.2f}")

if __name__ == "__main__":
    test_salary_schemes()