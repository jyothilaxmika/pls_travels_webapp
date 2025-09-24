import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from models import Duty, Driver, Vehicle, DutyStatus
from services.audit_service import AuditService
from timezone_utils import get_ist_time_naive

logger = logging.getLogger(__name__)

class AnomalyType:
    REVENUE_OUTLIER = 'revenue_outlier'
    DISTANCE_REVENUE_MISMATCH = 'distance_revenue_mismatch'
    ABNORMAL_DURATION = 'abnormal_duration'
    ODOMETER_INCONSISTENCY = 'odometer_inconsistency' 
    PERFORMANCE_ANOMALY = 'performance_anomaly'
    LOCATION_ANOMALY = 'location_anomaly'
    PATTERN_ANOMALY = 'pattern_anomaly'
    FUEL_EFFICIENCY_ANOMALY = 'fuel_efficiency_anomaly'

class AnomalySeverity:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class AnomalyDetectionService:
    """
    AI-powered anomaly detection service for duty validation.
    Analyzes duty data patterns and flags suspicious activities for admin review.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.audit_service = AuditService()
        
        # Configurable thresholds for anomaly detection
        self.thresholds = {
            'revenue_outlier_factor': 3.0,  # Standard deviations from mean
            'min_duty_duration_minutes': 30,  # Minimum realistic duty duration
            'max_duty_duration_hours': 16,    # Maximum realistic duty duration
            'min_revenue_per_hour': 50,       # Minimum expected revenue per hour
            'max_revenue_per_hour': 2000,     # Maximum realistic revenue per hour
            'min_distance_per_hour': 5,       # Minimum distance per hour (km)
            'max_distance_per_hour': 80,      # Maximum realistic distance per hour
            'min_revenue_per_km': 5,          # Minimum revenue per kilometer
            'max_revenue_per_km': 50,         # Maximum realistic revenue per km
            'odometer_jump_threshold': 500,   # Max reasonable odometer increase
            'fuel_efficiency_min': 8,         # Minimum km per CNG bar
            'fuel_efficiency_max': 25,        # Maximum km per CNG bar
        }

    def analyze_duty_for_anomalies(self, duty_id: int) -> Dict[str, Any]:
        """
        Comprehensive anomaly analysis for a specific duty.
        
        Returns:
            dict: {
                'anomalies_detected': bool,
                'anomalies': [list of detected anomalies],
                'severity': highest severity level,
                'recommendation': admin action recommendation
            }
        """
        try:
            duty = self.db.query(Duty).get(duty_id) if self.db else Duty.query.get(duty_id)
            if not duty:
                return {'error': 'Duty not found', 'anomalies_detected': False}
            
            anomalies = []
            
            # Get historical data for comparison
            historical_data = self._get_historical_duty_data(duty.driver_id, duty.vehicle_id)
            
            # Run individual anomaly checks
            anomalies.extend(self._check_revenue_anomalies(duty, historical_data))
            anomalies.extend(self._check_duration_anomalies(duty, historical_data))
            anomalies.extend(self._check_distance_revenue_anomalies(duty))
            anomalies.extend(self._check_odometer_anomalies(duty, historical_data))
            anomalies.extend(self._check_performance_anomalies(duty, historical_data))
            anomalies.extend(self._check_location_anomalies(duty, historical_data))
            anomalies.extend(self._check_pattern_anomalies(duty, historical_data))
            anomalies.extend(self._check_fuel_efficiency_anomalies(duty))
            
            # Determine overall severity
            severity = self._calculate_overall_severity(anomalies)
            recommendation = self._generate_recommendation(anomalies, severity or AnomalySeverity.LOW)
            
            result = {
                'anomalies_detected': len(anomalies) > 0,
                'anomalies': anomalies,
                'severity': severity,
                'recommendation': recommendation,
                'duty_id': duty_id,
                'analysis_timestamp': get_ist_time_naive().isoformat()
            }
            
            # Log anomalies if detected
            if anomalies:
                self._log_anomalies(duty, anomalies, severity or AnomalySeverity.LOW)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing duty {duty_id} for anomalies: {str(e)}")
            return {'error': str(e), 'anomalies_detected': False}

    def _get_historical_duty_data(self, driver_id: int, vehicle_id: int, days_back: int = 30) -> Dict:
        """Get historical duty statistics for comparison"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Get recent duties for this driver
            driver_duties = (
                self.db.query(Duty).filter(
                    Duty.driver_id == driver_id,
                    Duty.status == DutyStatus.COMPLETED,
                    Duty.actual_start >= cutoff_date
                ).all() if self.db else 
                Duty.query.filter(
                    Duty.driver_id == driver_id,
                    Duty.status == DutyStatus.COMPLETED,
                    Duty.actual_start >= cutoff_date
                ).all()
            )
            
            # Get recent duties for this vehicle
            vehicle_duties = (
                self.db.query(Duty).filter(
                    Duty.vehicle_id == vehicle_id,
                    Duty.status == DutyStatus.COMPLETED,
                    Duty.actual_start >= cutoff_date
                ).all() if self.db else
                Duty.query.filter(
                    Duty.vehicle_id == vehicle_id,
                    Duty.status == DutyStatus.COMPLETED,
                    Duty.actual_start >= cutoff_date
                ).all()
            )
            
            # Calculate statistics
            def calculate_stats(duties):
                if not duties:
                    return {'count': 0, 'mean': 0, 'std_dev': 0, 'median': 0}
                
                revenues = [d.gross_revenue or 0 for d in duties if d.gross_revenue]
                distances = [d.total_distance or 0 for d in duties if d.total_distance]
                durations = []
                
                for d in duties:
                    if d.actual_start and d.actual_end:
                        duration = (d.actual_end - d.actual_start).total_seconds() / 3600  # hours
                        durations.append(duration)
                
                return {
                    'count': len(duties),
                    'revenue': {
                        'mean': statistics.mean(revenues) if revenues else 0,
                        'std_dev': statistics.stdev(revenues) if len(revenues) > 1 else 0,
                        'median': statistics.median(revenues) if revenues else 0
                    },
                    'distance': {
                        'mean': statistics.mean(distances) if distances else 0,
                        'std_dev': statistics.stdev(distances) if len(distances) > 1 else 0,
                        'median': statistics.median(distances) if distances else 0
                    },
                    'duration': {
                        'mean': statistics.mean(durations) if durations else 0,
                        'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0,
                        'median': statistics.median(durations) if durations else 0
                    }
                }
            
            return {
                'driver_stats': calculate_stats(driver_duties),
                'vehicle_stats': calculate_stats(vehicle_duties),
                'analysis_period_days': days_back
            }
            
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return {'driver_stats': {'count': 0}, 'vehicle_stats': {'count': 0}}

    def _check_revenue_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for unusual revenue patterns"""
        anomalies = []
        
        if not duty.gross_revenue:
            return anomalies
        
        revenue = duty.gross_revenue
        driver_stats = historical_data.get('driver_stats', {})
        
        # Check against driver's historical pattern
        if driver_stats.get('count', 0) >= 5:  # Need sufficient data
            mean_revenue = driver_stats.get('revenue', {}).get('mean', 0)
            std_dev = driver_stats.get('revenue', {}).get('std_dev', 0)
            
            if std_dev > 0 and mean_revenue > 0:
                z_score = abs(revenue - mean_revenue) / std_dev
                
                if z_score > self.thresholds['revenue_outlier_factor']:
                    severity = AnomalySeverity.HIGH if z_score > 4 else AnomalySeverity.MEDIUM
                    anomalies.append({
                        'type': AnomalyType.REVENUE_OUTLIER,
                        'severity': severity,
                        'description': f'Revenue ₹{revenue:.2f} is {z_score:.1f} standard deviations from driver average ₹{mean_revenue:.2f}',
                        'details': {
                            'current_revenue': revenue,
                            'historical_mean': mean_revenue,
                            'z_score': z_score,
                            'comparison_period': f"{historical_data.get('analysis_period_days', 30)} days"
                        }
                    })
        
        return anomalies

    def _check_duration_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for abnormal duty durations"""
        anomalies = []
        
        if not duty.actual_start or not duty.actual_end:
            return anomalies
        
        duration_hours = (duty.actual_end - duty.actual_start).total_seconds() / 3600
        duration_minutes = duration_hours * 60
        
        # Check for extremely short duties
        if duration_minutes < self.thresholds['min_duty_duration_minutes']:
            anomalies.append({
                'type': AnomalyType.ABNORMAL_DURATION,
                'severity': AnomalySeverity.HIGH,
                'description': f'Duty duration of {duration_minutes:.0f} minutes is unusually short',
                'details': {
                    'duration_minutes': duration_minutes,
                    'threshold_minutes': self.thresholds['min_duty_duration_minutes']
                }
            })
        
        # Check for extremely long duties
        elif duration_hours > self.thresholds['max_duty_duration_hours']:
            anomalies.append({
                'type': AnomalyType.ABNORMAL_DURATION,
                'severity': AnomalySeverity.MEDIUM,
                'description': f'Duty duration of {duration_hours:.1f} hours is unusually long',
                'details': {
                    'duration_hours': duration_hours,
                    'threshold_hours': self.thresholds['max_duty_duration_hours']
                }
            })
        
        return anomalies

    def _check_distance_revenue_anomalies(self, duty: Duty) -> List[Dict]:
        """Check for mismatches between distance and revenue"""
        anomalies = []
        
        if not duty.total_distance or not duty.gross_revenue:
            return anomalies
        
        distance = duty.total_distance
        revenue = duty.gross_revenue
        
        if distance > 0:
            revenue_per_km = revenue / distance
            
            if revenue_per_km < self.thresholds['min_revenue_per_km']:
                anomalies.append({
                    'type': AnomalyType.DISTANCE_REVENUE_MISMATCH,
                    'severity': AnomalySeverity.MEDIUM,
                    'description': f'Revenue per km (₹{revenue_per_km:.2f}) is unusually low',
                    'details': {
                        'revenue_per_km': revenue_per_km,
                        'total_distance': distance,
                        'total_revenue': revenue,
                        'threshold_min': self.thresholds['min_revenue_per_km']
                    }
                })
            
            elif revenue_per_km > self.thresholds['max_revenue_per_km']:
                anomalies.append({
                    'type': AnomalyType.DISTANCE_REVENUE_MISMATCH,
                    'severity': AnomalySeverity.HIGH,
                    'description': f'Revenue per km (₹{revenue_per_km:.2f}) is unusually high',
                    'details': {
                        'revenue_per_km': revenue_per_km,
                        'total_distance': distance,
                        'total_revenue': revenue,
                        'threshold_max': self.thresholds['max_revenue_per_km']
                    }
                })
        
        return anomalies

    def _check_odometer_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for odometer reading inconsistencies"""
        anomalies = []
        
        if not duty.start_odometer or not duty.end_odometer:
            return anomalies
        
        odometer_increase = duty.end_odometer - duty.start_odometer
        
        # Check for negative odometer readings (rollback)
        if odometer_increase < 0:
            anomalies.append({
                'type': AnomalyType.ODOMETER_INCONSISTENCY,
                'severity': AnomalySeverity.CRITICAL,
                'description': f'Odometer reading decreased by {abs(odometer_increase):.1f} km during duty',
                'details': {
                    'start_odometer': duty.start_odometer,
                    'end_odometer': duty.end_odometer,
                    'difference': odometer_increase
                }
            })
        
        # Check for unrealistic odometer jumps
        elif odometer_increase > self.thresholds['odometer_jump_threshold']:
            anomalies.append({
                'type': AnomalyType.ODOMETER_INCONSISTENCY,
                'severity': AnomalySeverity.HIGH,
                'description': f'Odometer increased by {odometer_increase:.1f} km, which seems excessive',
                'details': {
                    'start_odometer': duty.start_odometer,
                    'end_odometer': duty.end_odometer,
                    'difference': odometer_increase,
                    'threshold': self.thresholds['odometer_jump_threshold']
                }
            })
        
        # Check if reported distance matches odometer difference
        if duty.total_distance and abs(duty.total_distance - odometer_increase) > 50:
            anomalies.append({
                'type': AnomalyType.ODOMETER_INCONSISTENCY,
                'severity': AnomalySeverity.MEDIUM,
                'description': f'Reported distance ({duty.total_distance:.1f} km) differs significantly from odometer change ({odometer_increase:.1f} km)',
                'details': {
                    'reported_distance': duty.total_distance,
                    'odometer_difference': odometer_increase,
                    'discrepancy': abs(duty.total_distance - odometer_increase)
                }
            })
        
        return anomalies

    def _check_performance_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for performance metrics anomalies"""
        anomalies = []
        
        if not duty.actual_start or not duty.actual_end or not duty.gross_revenue:
            return anomalies
        
        duration_hours = (duty.actual_end - duty.actual_start).total_seconds() / 3600
        
        if duration_hours > 0:
            revenue_per_hour = duty.gross_revenue / duration_hours
            
            # Check revenue per hour
            if revenue_per_hour < self.thresholds['min_revenue_per_hour']:
                anomalies.append({
                    'type': AnomalyType.PERFORMANCE_ANOMALY,
                    'severity': AnomalySeverity.MEDIUM,
                    'description': f'Revenue per hour (₹{revenue_per_hour:.2f}) is below expected minimum',
                    'details': {
                        'revenue_per_hour': revenue_per_hour,
                        'threshold_min': self.thresholds['min_revenue_per_hour'],
                        'total_revenue': duty.gross_revenue,
                        'duration_hours': duration_hours
                    }
                })
            
            elif revenue_per_hour > self.thresholds['max_revenue_per_hour']:
                anomalies.append({
                    'type': AnomalyType.PERFORMANCE_ANOMALY,
                    'severity': AnomalySeverity.HIGH,
                    'description': f'Revenue per hour (₹{revenue_per_hour:.2f}) is unusually high',
                    'details': {
                        'revenue_per_hour': revenue_per_hour,
                        'threshold_max': self.thresholds['max_revenue_per_hour'],
                        'total_revenue': duty.gross_revenue,
                        'duration_hours': duration_hours
                    }
                })
        
        return anomalies

    def _check_location_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for unusual location patterns"""
        anomalies = []
        
        # Basic location validation - can be enhanced with geofencing
        if duty.start_location_lat and duty.start_location_lng:
            # Check for locations outside reasonable bounds (India)
            if not (6.0 <= duty.start_location_lat <= 37.0 and 68.0 <= duty.start_location_lng <= 97.0):
                anomalies.append({
                    'type': AnomalyType.LOCATION_ANOMALY,
                    'severity': AnomalySeverity.HIGH,
                    'description': 'Start location appears to be outside India',
                    'details': {
                        'start_lat': duty.start_location_lat,
                        'start_lng': duty.start_location_lng
                    }
                })
        
        if duty.end_location_lat and duty.end_location_lng:
            if not (6.0 <= duty.end_location_lat <= 37.0 and 68.0 <= duty.end_location_lng <= 97.0):
                anomalies.append({
                    'type': AnomalyType.LOCATION_ANOMALY,
                    'severity': AnomalySeverity.HIGH,
                    'description': 'End location appears to be outside India',
                    'details': {
                        'end_lat': duty.end_location_lat,
                        'end_lng': duty.end_location_lng
                    }
                })
        
        return anomalies

    def _check_pattern_anomalies(self, duty: Duty, historical_data: Dict) -> List[Dict]:
        """Check for unusual timing or frequency patterns"""
        anomalies = []
        
        if not duty.actual_start:
            return anomalies
        
        start_hour = duty.actual_start.hour
        
        # Check for duties starting at unusual hours (very late night/early morning)
        if start_hour >= 2 and start_hour <= 5:
            anomalies.append({
                'type': AnomalyType.PATTERN_ANOMALY,
                'severity': AnomalySeverity.MEDIUM,
                'description': f'Duty started at unusual hour: {start_hour:02d}:00',
                'details': {
                    'start_hour': start_hour,
                    'start_time': duty.actual_start.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        
        return anomalies

    def _check_fuel_efficiency_anomalies(self, duty: Duty) -> List[Dict]:
        """Check for fuel efficiency anomalies"""
        anomalies = []
        
        if not duty.start_cng or not duty.end_cng or not duty.total_distance:
            return anomalies
        
        cng_consumed = duty.start_cng - duty.end_cng
        
        if cng_consumed > 0 and duty.total_distance > 0:
            efficiency = duty.total_distance / cng_consumed  # km per CNG bar
            
            if efficiency < self.thresholds['fuel_efficiency_min']:
                anomalies.append({
                    'type': AnomalyType.FUEL_EFFICIENCY_ANOMALY,
                    'severity': AnomalySeverity.MEDIUM,
                    'description': f'Poor fuel efficiency: {efficiency:.1f} km/bar (expected min: {self.thresholds["fuel_efficiency_min"]})',
                    'details': {
                        'efficiency_km_per_bar': efficiency,
                        'distance': duty.total_distance,
                        'cng_consumed': cng_consumed,
                        'threshold_min': self.thresholds['fuel_efficiency_min']
                    }
                })
            
            elif efficiency > self.thresholds['fuel_efficiency_max']:
                anomalies.append({
                    'type': AnomalyType.FUEL_EFFICIENCY_ANOMALY,
                    'severity': AnomalySeverity.MEDIUM,
                    'description': f'Unusually high fuel efficiency: {efficiency:.1f} km/bar (expected max: {self.thresholds["fuel_efficiency_max"]})',
                    'details': {
                        'efficiency_km_per_bar': efficiency,
                        'distance': duty.total_distance,
                        'cng_consumed': cng_consumed,
                        'threshold_max': self.thresholds['fuel_efficiency_max']
                    }
                })
        
        return anomalies

    def _calculate_overall_severity(self, anomalies: List[Dict]) -> Optional[str]:
        """Calculate the overall severity based on individual anomaly severities"""
        if not anomalies:
            return None
        
        severities = [a['severity'] for a in anomalies]
        
        if AnomalySeverity.CRITICAL in severities:
            return AnomalySeverity.CRITICAL
        elif AnomalySeverity.HIGH in severities:
            return AnomalySeverity.HIGH
        elif AnomalySeverity.MEDIUM in severities:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _generate_recommendation(self, anomalies: List[Dict], severity: str) -> str:
        """Generate admin action recommendations based on detected anomalies"""
        if not anomalies:
            return "No action required - duty appears normal"
        
        if severity == AnomalySeverity.CRITICAL:
            return "IMMEDIATE REVIEW REQUIRED - Hold payment and investigate immediately"
        elif severity == AnomalySeverity.HIGH:
            return "PRIORITY REVIEW - Manual verification required before approval"
        elif severity == AnomalySeverity.MEDIUM:
            return "REVIEW RECOMMENDED - Verify details during regular approval process"
        else:
            return "MINOR REVIEW - Flag for awareness during approval"

    def _log_anomalies(self, duty: Duty, anomalies: List[Dict], severity: str):
        """Log detected anomalies to audit trail"""
        try:
            # Get driver and vehicle safely
            from app import db
            driver = db.session.get(Driver, duty.driver_id) if duty.driver_id else None
            vehicle = db.session.get(Vehicle, duty.vehicle_id) if duty.vehicle_id else None
            
            self.audit_service.log_action(
                action='ai_anomaly_detected',
                entity_type='duty',
                entity_id=duty.id,
                details={
                    'driver_name': driver.full_name if driver else 'Unknown',
                    'vehicle_registration': vehicle.registration_number if vehicle else 'Unknown',
                    'anomaly_count': len(anomalies),
                    'overall_severity': severity,
                    'anomalies': anomalies,
                    'ai_analysis_version': '1.0'
                },
                user_id=driver.user_id if driver else None
            )
            
            logger.info(f"AI anomaly detection: {len(anomalies)} anomalies detected for duty {duty.id} (severity: {severity})")
            
        except Exception as e:
            logger.error(f"Error logging anomalies for duty {duty.id}: {str(e)}")

    def bulk_analyze_pending_duties(self, limit: int = 50) -> Dict[str, Any]:
        """
        Analyze multiple pending duties for anomalies.
        Used for batch processing of duties awaiting approval.
        """
        try:
            # Get pending duties
            pending_duties = (
                self.db.query(Duty).filter(
                    Duty.status == DutyStatus.PENDING_APPROVAL
                ).order_by(Duty.submitted_at.desc()).limit(limit).all() if self.db else
                Duty.query.filter(
                    Duty.status == DutyStatus.PENDING_APPROVAL
                ).order_by(Duty.submitted_at.desc()).limit(limit).all()
            )
            
            results = {
                'total_analyzed': len(pending_duties),
                'anomalies_found': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0,
                'duties_with_anomalies': []
            }
            
            for duty in pending_duties:
                analysis = self.analyze_duty_for_anomalies(duty.id)
                
                if analysis.get('anomalies_detected'):
                    results['anomalies_found'] += 1
                    severity = analysis.get('severity')
                    
                    if severity == AnomalySeverity.CRITICAL:
                        results['critical_count'] += 1
                    elif severity == AnomalySeverity.HIGH:
                        results['high_count'] += 1
                    elif severity == AnomalySeverity.MEDIUM:
                        results['medium_count'] += 1
                    else:
                        results['low_count'] += 1
                    
                    # Get driver and vehicle safely
                    from app import db
                    driver = db.session.get(Driver, duty.driver_id) if duty.driver_id else None
                    vehicle = db.session.get(Vehicle, duty.vehicle_id) if duty.vehicle_id else None
                    
                    results['duties_with_anomalies'].append({
                        'duty_id': duty.id,
                        'driver_name': driver.full_name if driver else 'Unknown',
                        'vehicle_registration': vehicle.registration_number if vehicle else 'Unknown',
                        'severity': severity,
                        'anomaly_count': len(analysis.get('anomalies', [])),
                        'recommendation': analysis.get('recommendation')
                    })
            
            logger.info(f"Bulk anomaly analysis completed: {results['anomalies_found']}/{results['total_analyzed']} duties flagged")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk anomaly analysis: {str(e)}")
            return {'error': str(e), 'total_analyzed': 0}