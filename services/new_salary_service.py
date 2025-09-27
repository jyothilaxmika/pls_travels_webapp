"""
New 5-Method Salary Calculation System for PLS TRAVELS
Completely redesigned salary system with HTML-configurable methods
"""

from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, date
import json
import logging
from dataclasses import dataclass
from models import Duty, Driver, db
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

@dataclass
class SalaryCalculationResult:
    """Result of salary calculation with detailed breakdown"""
    method_name: str
    total_salary: float
    base_amount: float
    incentive_amount: float
    deductions: float
    net_salary: float
    breakdown: Dict[str, Any]
    calculation_notes: str

class NewSalaryCalculationService:
    """
    New 5-Method Salary Calculation System
    
    Methods:
    1. Revenue Share - Percentage of total revenue
    2. Fixed Daily Rate - Fixed amount per duty/day
    3. Slab-based Incentive - Tiered rates based on revenue ranges
    4. Hybrid Base+Commission - Fixed base + revenue percentage
    5. Final Settlement - Traditional Tamil style with CNG/deductions
    """
    
    def __init__(self):
        self.audit_service = AuditService()
        
        # Default configurations for each method
        self.default_configs = {
            'd2d': {
                'cng_rate': 90.0,
                'insurance_deduction': 60.0,
                'operator_low_threshold': 4500.0,
                'operator_low_percentage': 30.0,
                'operator_high_percentage': 70.0,
                'out_operator_percentage': 30.0,
                'base_cng_percentage': 30.0,
                'display_labels': {
                    'cash_collected_1': 'Cash Collected 1',
                    'cash_collected_2': 'Cash Collected 2', 
                    'out_cash': 'Out Cash',
                    'operator_1': 'Operator 1',
                    'operator_2': 'Operator 2',
                    'out_operator': 'Out Operator',
                    'pass_deduction': 'Pass Deduction',
                    'start_cng': 'Start CNG',
                    'end_cng': 'End CNG'
                }
            },
            'revenue_share': {
                'driver_percentage': 70.0,
                'company_percentage': 30.0,
                'minimum_guarantee': 0.0,
                'maximum_cap': 0.0,
                'deduction_types': ['insurance', 'fuel_advance', 'maintenance']
            },
            'fixed_daily': {
                'daily_rate': 500.0,
                'overtime_rate_per_hour': 50.0,
                'holiday_bonus_percentage': 20.0,
                'attendance_bonus': 100.0,
                'late_penalty_per_hour': 25.0
            },
            'slab_incentive': {
                'slabs': [
                    {'min_revenue': 0, 'max_revenue': 2000, 'percentage': 60.0},
                    {'min_revenue': 2001, 'max_revenue': 4000, 'percentage': 65.0},
                    {'min_revenue': 4001, 'max_revenue': 6000, 'percentage': 70.0},
                    {'min_revenue': 6001, 'max_revenue': 99999, 'percentage': 75.0}
                ],
                'minimum_guarantee': 400.0
            },
            'hybrid_commission': {
                'base_salary': 300.0,
                'commission_threshold': 2000.0,
                'commission_percentage': 25.0,
                'performance_bonus_targets': {
                    'trips_target': 20,
                    'revenue_target': 5000.0,
                    'bonus_amount': 200.0
                }
            },
            'final_settlement': {
                'revenue_low_threshold': 4500.0,
                'driver_share_low': 30.0,
                'driver_share_high': 70.0,
                'insurance_deduction': 90.0,
                'cng_rate': 90.0,
                'other_deductions': {
                    'permit_fee': 50.0,
                    'maintenance_reserve': 100.0
                }
            }
        }
    
    def calculate_salary(self, duty_id: int, method: str, custom_config: Optional[Dict] = None, 
                        manual_data: Optional[Dict] = None) -> SalaryCalculationResult:
        """
        Calculate salary using specified method
        
        Args:
            duty_id: ID of the duty to calculate for
            method: One of ['revenue_share', 'fixed_daily', 'slab_incentive', 'hybrid_commission', 'final_settlement']
            custom_config: Optional custom configuration (overrides defaults)
            manual_data: Optional manual input data from admin/manager
            
        Returns:
            SalaryCalculationResult with detailed breakdown
        """
        try:
            # Get duty data (auto-fetch)
            duty_data = self._auto_fetch_duty_data(duty_id)
            if not duty_data:
                raise ValueError(f"Could not fetch data for duty {duty_id}")
            
            # Merge with manual data if provided
            if manual_data:
                duty_data.update(manual_data)
                self.audit_service.log_action(
                    'manual_salary_adjustment', 'duty', duty_id,
                    {'manual_data_applied': manual_data}
                )
            
            # Get configuration
            config = self.default_configs.get(method, {}).copy()
            if custom_config:
                config.update(custom_config)
            
            # Calculate based on method
            if method == 'd2d':
                return self._calculate_d2d(duty_data, config)
            elif method == 'revenue_share':
                return self._calculate_revenue_share(duty_data, config)
            elif method == 'fixed_daily':
                return self._calculate_fixed_daily(duty_data, config)
            elif method == 'slab_incentive':
                return self._calculate_slab_incentive(duty_data, config)
            elif method == 'hybrid_commission':
                return self._calculate_hybrid_commission(duty_data, config)
            elif method == 'final_settlement':
                return self._calculate_final_settlement(duty_data, config)
            else:
                raise ValueError(f"Unknown salary calculation method: {method}")
                
        except Exception as e:
            logger.error(f"Error calculating salary for duty {duty_id}: {str(e)}")
            return self._create_error_result(method, str(e))
    
    def _calculate_d2d(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 1: D2D Final Settlement Calculator (Tamil Style)"""
        # Get input values with fallbacks
        cash1 = duty_data.get('cash_collected_1', 0.0)
        cash2 = duty_data.get('cash_collected_2', 0.0) 
        out_cash = duty_data.get('out_cash', 0.0)
        operator1 = duty_data.get('operator_1', 0.0)
        operator2 = duty_data.get('operator_2', 0.0)
        out_operator = duty_data.get('out_operator', 0.0)
        pass_deduction = duty_data.get('pass_deduction', 0.0)
        start_cng = duty_data.get('start_cng', 0.0)
        end_cng = duty_data.get('end_cng', 0.0)
        
        # Configuration values
        cng_rate = config.get('cng_rate', 90.0)
        insurance_deduction = config.get('insurance_deduction', 60.0)
        threshold = config.get('operator_low_threshold', 4500.0)
        low_percentage = config.get('operator_low_percentage', 30.0)
        high_percentage = config.get('operator_high_percentage', 70.0)
        out_percentage = config.get('out_operator_percentage', 30.0)
        base_cng_percentage = config.get('base_cng_percentage', 30.0)
        
        # Calculate totals
        total_cash = cash1 + cash2 + out_cash
        in_house_operator_total = operator1 + operator2
        grand_total_operator = in_house_operator_total + out_operator
        
        # Calculate in-house salary (D2D logic)
        if in_house_operator_total <= threshold:
            in_house_salary = in_house_operator_total * (low_percentage / 100)
        else:
            low_portion = threshold * (low_percentage / 100)
            high_portion = (in_house_operator_total - threshold) * (high_percentage / 100)
            in_house_salary = low_portion + high_portion
        
        # Calculate out operator salary
        out_operator_salary = out_operator * (out_percentage / 100)
        
        # Gross salary
        gross_salary = in_house_salary + out_operator_salary
        
        # Net salary (after insurance deduction)
        net_salary = gross_salary - insurance_deduction
        
        # CNG calculations
        base_cng = grand_total_operator * (base_cng_percentage / 100)
        cng_adjustment = (start_cng - end_cng) * cng_rate
        final_cng = base_cng - cng_adjustment
        
        # Company settlement
        company_settlement = (total_cash - final_cng) + pass_deduction - net_salary
        
        breakdown = {
            'inputs': {
                'cash_collected_1': cash1,
                'cash_collected_2': cash2,
                'out_cash': out_cash,
                'operator_1': operator1,
                'operator_2': operator2,
                'out_operator': out_operator,
                'pass_deduction': pass_deduction,
                'start_cng': start_cng,
                'end_cng': end_cng
            },
            'calculations': {
                'total_cash': total_cash,
                'in_house_operator_total': in_house_operator_total,
                'grand_total_operator': grand_total_operator,
                'in_house_salary': in_house_salary,
                'out_operator_salary': out_operator_salary,
                'gross_salary': gross_salary,
                'insurance_deduction': insurance_deduction,
                'net_salary': net_salary,
                'base_cng': base_cng,
                'cng_adjustment': cng_adjustment,
                'final_cng': final_cng,
                'company_settlement': company_settlement
            },
            'config_used': {
                'cng_rate': cng_rate,
                'insurance_deduction': insurance_deduction,
                'operator_threshold': threshold,
                'low_percentage': low_percentage,
                'high_percentage': high_percentage
            }
        }
        
        return SalaryCalculationResult(
            method_name="D2D Final Settlement",
            total_salary=gross_salary,
            base_amount=gross_salary,
            incentive_amount=0.0,
            deductions=insurance_deduction,
            net_salary=net_salary,
            breakdown=breakdown,
            calculation_notes=f"D2D Settlement: Gross ₹{gross_salary:.2f} - Insurance ₹{insurance_deduction:.2f} = Net ₹{net_salary:.2f}. Company owes: ₹{company_settlement:.2f}"
        )
    
    def _auto_fetch_duty_data(self, duty_id: int) -> Optional[Dict]:
        """Auto-fetch duty data from database"""
        try:
            duty = Duty.query.get(duty_id)
            if not duty:
                return None
            
            # Calculate duty duration
            duration_hours = 0.0
            if duty.actual_start and duty.actual_end:
                duration = duty.actual_end - duty.actual_start
                duration_hours = duration.total_seconds() / 3600
            
            # Check if weekend/holiday
            duty_date = duty.actual_start.date() if duty.actual_start else date.today()
            is_weekend = duty_date.weekday() >= 5  # Saturday=5, Sunday=6
            
            return {
                'duty_id': duty.id,
                'driver_id': duty.driver_id,
                'vehicle_id': duty.vehicle_id,
                'revenue': duty.revenue or 0.0,
                'total_trips': duty.total_trips or 0,
                'duration_hours': duration_hours,
                'fuel_consumed': duty.fuel_consumed or 0.0,
                'start_km': duty.start_km or 0.0,
                'end_km': duty.end_km or 0.0,
                'distance_traveled': (duty.end_km or 0.0) - (duty.start_km or 0.0),
                'is_weekend': is_weekend,
                'duty_date': duty_date,
                'status': duty.status.value if duty.status else 'unknown',
                # Additional fields that may be manually input
                'cash_collected': 0.0,
                'digital_payment': 0.0,
                'advance_taken': 0.0,
                'fuel_expense': 0.0,
                'toll_expense': 0.0,
                'maintenance_expense': 0.0,
                'other_expenses': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error fetching duty data for {duty_id}: {str(e)}")
            return None
    
    def _calculate_revenue_share(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 1: Revenue Share Calculation"""
        revenue = duty_data.get('revenue', 0.0)
        driver_percentage = config.get('driver_percentage', 70.0)
        
        # Calculate driver share
        driver_share = revenue * (driver_percentage / 100)
        
        # Apply minimum guarantee
        min_guarantee = config.get('minimum_guarantee', 0.0)
        if min_guarantee > 0 and driver_share < min_guarantee:
            driver_share = min_guarantee
            
        # Apply maximum cap
        max_cap = config.get('maximum_cap', 0.0)
        if max_cap > 0 and driver_share > max_cap:
            driver_share = max_cap
        
        # Calculate deductions
        deductions = self._calculate_deductions(duty_data, config)
        net_salary = driver_share - deductions
        
        breakdown = {
            'total_revenue': revenue,
            'driver_percentage': driver_percentage,
            'gross_driver_share': driver_share,
            'deductions_breakdown': deductions,
            'minimum_guarantee_applied': min_guarantee if driver_share == min_guarantee else 0,
            'maximum_cap_applied': max_cap if driver_share == max_cap else 0
        }
        
        return SalaryCalculationResult(
            method_name="Revenue Share",
            total_salary=driver_share,
            base_amount=driver_share,
            incentive_amount=0.0,
            deductions=deductions,
            net_salary=net_salary,
            breakdown=breakdown,
            calculation_notes=f"{driver_percentage}% of ₹{revenue:.2f} revenue"
        )
    
    def _calculate_fixed_daily(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 2: Fixed Daily Rate Calculation"""
        base_rate = config.get('daily_rate', 500.0)
        duration_hours = duty_data.get('duration_hours', 8.0)
        is_weekend = duty_data.get('is_weekend', False)
        
        # Base salary
        base_salary = base_rate
        
        # Overtime calculation (>8 hours)
        overtime_amount = 0.0
        if duration_hours > 8:
            overtime_hours = duration_hours - 8
            overtime_rate = config.get('overtime_rate_per_hour', 50.0)
            overtime_amount = overtime_hours * overtime_rate
        
        # Weekend/Holiday bonus
        holiday_bonus = 0.0
        if is_weekend:
            holiday_bonus_pct = config.get('holiday_bonus_percentage', 20.0)
            holiday_bonus = base_salary * (holiday_bonus_pct / 100)
        
        # Attendance bonus (if applicable)
        attendance_bonus = config.get('attendance_bonus', 100.0) if duration_hours >= 8 else 0.0
        
        total_salary = base_salary + overtime_amount + holiday_bonus + attendance_bonus
        deductions = self._calculate_deductions(duty_data, config)
        net_salary = total_salary - deductions
        
        breakdown = {
            'base_daily_rate': base_rate,
            'duty_hours': duration_hours,
            'overtime_hours': max(0, duration_hours - 8),
            'overtime_amount': overtime_amount,
            'weekend_bonus': holiday_bonus,
            'attendance_bonus': attendance_bonus,
            'total_before_deductions': total_salary
        }
        
        return SalaryCalculationResult(
            method_name="Fixed Daily Rate",
            total_salary=total_salary,
            base_amount=base_salary,
            incentive_amount=overtime_amount + holiday_bonus + attendance_bonus,
            deductions=deductions,
            net_salary=net_salary,
            breakdown=breakdown,
            calculation_notes=f"Fixed rate ₹{base_rate} + overtime ₹{overtime_amount:.2f}"
        )
    
    def _calculate_slab_incentive(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 3: Slab-based Incentive Calculation"""
        revenue = duty_data.get('revenue', 0.0)
        slabs = config.get('slabs', [])
        
        # Find applicable slab
        applicable_slab = None
        for slab in slabs:
            if slab['min_revenue'] <= revenue <= slab['max_revenue']:
                applicable_slab = slab
                break
        
        if not applicable_slab:
            # Default to lowest slab
            applicable_slab = slabs[0] if slabs else {'percentage': 50.0}
        
        # Calculate earnings based on slab
        slab_percentage = applicable_slab.get('percentage', 50.0)
        slab_earnings = revenue * (slab_percentage / 100)
        
        # Apply minimum guarantee
        min_guarantee = config.get('minimum_guarantee', 400.0)
        final_salary = max(slab_earnings, min_guarantee)
        
        deductions = self._calculate_deductions(duty_data, config)
        net_salary = final_salary - deductions
        
        breakdown = {
            'revenue': revenue,
            'applicable_slab': applicable_slab,
            'slab_percentage': slab_percentage,
            'slab_earnings': slab_earnings,
            'minimum_guarantee': min_guarantee,
            'guarantee_applied': final_salary > slab_earnings
        }
        
        return SalaryCalculationResult(
            method_name="Slab-based Incentive",
            total_salary=final_salary,
            base_amount=min_guarantee,
            incentive_amount=max(0, final_salary - min_guarantee),
            deductions=deductions,
            net_salary=net_salary,
            breakdown=breakdown,
            calculation_notes=f"Revenue ₹{revenue:.2f} → {slab_percentage}% = ₹{final_salary:.2f}"
        )
    
    def _calculate_hybrid_commission(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 4: Hybrid Base + Commission Calculation"""
        revenue = duty_data.get('revenue', 0.0)
        trips = duty_data.get('total_trips', 0)
        
        # Base salary
        base_salary = config.get('base_salary', 300.0)
        
        # Commission calculation
        commission_threshold = config.get('commission_threshold', 2000.0)
        commission_percentage = config.get('commission_percentage', 25.0)
        
        commission_amount = 0.0
        if revenue > commission_threshold:
            commission_revenue = revenue - commission_threshold
            commission_amount = commission_revenue * (commission_percentage / 100)
        
        # Performance bonus
        performance_bonus = 0.0
        performance_targets = config.get('performance_bonus_targets', {})
        trips_target = performance_targets.get('trips_target', 20)
        revenue_target = performance_targets.get('revenue_target', 5000.0)
        bonus_amount = performance_targets.get('bonus_amount', 200.0)
        
        if trips >= trips_target and revenue >= revenue_target:
            performance_bonus = bonus_amount
        
        total_salary = base_salary + commission_amount + performance_bonus
        deductions = self._calculate_deductions(duty_data, config)
        net_salary = total_salary - deductions
        
        breakdown = {
            'base_salary': base_salary,
            'revenue': revenue,
            'commission_threshold': commission_threshold,
            'commission_revenue': max(0, revenue - commission_threshold),
            'commission_percentage': commission_percentage,
            'commission_amount': commission_amount,
            'trips_completed': trips,
            'performance_targets_met': trips >= trips_target and revenue >= revenue_target,
            'performance_bonus': performance_bonus
        }
        
        return SalaryCalculationResult(
            method_name="Hybrid Base + Commission",
            total_salary=total_salary,
            base_amount=base_salary,
            incentive_amount=commission_amount + performance_bonus,
            deductions=deductions,
            net_salary=net_salary,
            breakdown=breakdown,
            calculation_notes=f"Base ₹{base_salary} + Commission ₹{commission_amount:.2f} + Bonus ₹{performance_bonus:.2f}"
        )
    
    def _calculate_final_settlement(self, duty_data: Dict, config: Dict) -> SalaryCalculationResult:
        """Method 5: Final Settlement (Traditional Tamil Style)"""
        revenue = duty_data.get('revenue', 0.0)
        
        # Revenue sharing logic
        threshold = config.get('revenue_low_threshold', 4500.0)
        low_share = config.get('driver_share_low', 30.0)
        high_share = config.get('driver_share_high', 70.0)
        
        # Calculate driver share before deductions (DSBD)
        if revenue <= threshold:
            dsbd = revenue * (low_share / 100)
        else:
            low_portion = threshold * (low_share / 100)
            high_portion = (revenue - threshold) * (high_share / 100)
            dsbd = low_portion + high_portion
        
        # Standard deductions
        insurance = config.get('insurance_deduction', 90.0)
        
        # Fuel/CNG adjustments
        fuel_consumed = duty_data.get('fuel_consumed', 0.0)
        cng_rate = config.get('cng_rate', 90.0)
        fuel_cost = fuel_consumed * cng_rate
        
        # Other deductions
        other_deductions = config.get('other_deductions', {})
        total_other = sum(other_deductions.values())
        
        # Manual expenses
        advance_taken = duty_data.get('advance_taken', 0.0)
        toll_expense = duty_data.get('toll_expense', 0.0)
        maintenance_expense = duty_data.get('maintenance_expense', 0.0)
        other_expenses = duty_data.get('other_expenses', 0.0)
        
        total_deductions = (insurance + fuel_cost + total_other + 
                          advance_taken + toll_expense + maintenance_expense + other_expenses)
        
        final_salary = dsbd - total_deductions
        
        breakdown = {
            'total_revenue': revenue,
            'revenue_threshold': threshold,
            'driver_share_before_deductions': dsbd,
            'deductions': {
                'insurance': insurance,
                'fuel_cost': fuel_cost,
                'fuel_consumed_liters': fuel_consumed,
                'cng_rate_per_liter': cng_rate,
                'advance_taken': advance_taken,
                'toll_expense': toll_expense,
                'maintenance_expense': maintenance_expense,
                'other_expenses': other_expenses,
                'other_deductions': other_deductions,
                'total_deductions': total_deductions
            },
            'settlement_calculation': {
                'low_share_percentage': low_share,
                'high_share_percentage': high_share,
                'applied_calculation': f"{'Low rate' if revenue <= threshold else 'Mixed rate'}"
            }
        }
        
        return SalaryCalculationResult(
            method_name="Final Settlement (Tamil Style)",
            total_salary=dsbd,
            base_amount=dsbd,
            incentive_amount=0.0,
            deductions=total_deductions,
            net_salary=final_salary,
            breakdown=breakdown,
            calculation_notes=f"DSBD ₹{dsbd:.2f} - Deductions ₹{total_deductions:.2f} = ₹{final_salary:.2f}"
        )
    
    def _calculate_deductions(self, duty_data: Dict, config: Dict) -> float:
        """Calculate standard deductions"""
        deductions = 0.0
        
        # Add manual expenses if provided
        deductions += duty_data.get('advance_taken', 0.0)
        deductions += duty_data.get('fuel_expense', 0.0)
        deductions += duty_data.get('toll_expense', 0.0)
        deductions += duty_data.get('maintenance_expense', 0.0)
        deductions += duty_data.get('other_expenses', 0.0)
        
        return deductions
    
    def _create_error_result(self, method: str, error_msg: str) -> SalaryCalculationResult:
        """Create error result for failed calculations"""
        return SalaryCalculationResult(
            method_name=f"{method} (ERROR)",
            total_salary=0.0,
            base_amount=0.0,
            incentive_amount=0.0,
            deductions=0.0,
            net_salary=0.0,
            breakdown={'error': error_msg},
            calculation_notes=f"Calculation failed: {error_msg}"
        )
    
    def get_method_configuration_template(self, method: str) -> Dict:
        """Get the configuration template for a method (for HTML form generation)"""
        return self.default_configs.get(method, {})
    
    def update_method_configuration(self, method: str, new_config: Dict) -> bool:
        """Update default configuration for a method"""
        if method in self.default_configs:
            self.default_configs[method].update(new_config)
            return True
        return False