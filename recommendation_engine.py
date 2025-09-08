"""
Smart Duty Assignment Recommendation Engine for PLS TRAVELS

This module provides intelligent recommendations for driver-vehicle assignments
based on multiple factors including performance, compatibility, availability,
and historical data.
"""

import math
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from sqlalchemy import func, desc, and_
from models import (
    Driver, Vehicle, Duty, VehicleAssignment, Branch, 
    DriverStatus, VehicleStatus, DutyStatus, AssignmentStatus, db
)

@dataclass
class RecommendationScore:
    """Container for recommendation scores and reasoning"""
    driver_id: int
    vehicle_id: int
    total_score: float
    performance_score: float
    compatibility_score: float
    availability_score: float
    experience_score: float
    location_score: float
    reasoning: List[str]

class SmartRecommendationEngine:
    """
    Advanced recommendation engine that analyzes multiple factors to suggest
    optimal driver-vehicle assignments.
    """
    
    def __init__(self):
        self.weights = {
            'performance': 0.25,    # Driver performance metrics
            'compatibility': 0.20,  # Driver-vehicle compatibility
            'availability': 0.20,   # Current availability status
            'experience': 0.15,     # Experience with vehicle type
            'location': 0.10,       # Geographic proximity
            'workload': 0.10       # Workload balancing
        }
    
    def get_recommendations(self, 
                          branch_id: Optional[int] = None,
                          shift_type: str = 'full_day',
                          date_range: Tuple[datetime, datetime] = None,
                          limit: int = 10,
                          strategy: str = 'balanced') -> List[RecommendationScore]:
        """
        Generate smart recommendations for driver-vehicle assignments
        
        Args:
            branch_id: Filter by specific branch
            shift_type: Type of shift (full_day, morning, evening, night)
            date_range: Date range for assignment (start, end)
            limit: Maximum number of recommendations
            strategy: Recommendation strategy ('performance', 'balanced', 'availability')
        
        Returns:
            List of RecommendationScore objects sorted by total score
        """
        # Adjust weights based on strategy
        self._adjust_strategy_weights(strategy)
        
        # Get available drivers and vehicles
        drivers = self._get_available_drivers(branch_id)
        vehicles = self._get_available_vehicles(branch_id)
        
        if not drivers or not vehicles:
            return []
        
        recommendations = []
        
        # Generate recommendations for each driver-vehicle combination
        for driver in drivers:
            for vehicle in vehicles:
                # Skip if driver and vehicle are from different branches
                if driver.branch_id != vehicle.branch_id:
                    continue
                
                # Calculate recommendation score
                score = self._calculate_recommendation_score(driver, vehicle, shift_type, date_range)
                recommendations.append(score)
        
        # Sort by total score and return top recommendations
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return recommendations[:limit]
    
    def get_driver_recommendations(self, vehicle_id: int, limit: int = 5) -> List[RecommendationScore]:
        """Get best driver recommendations for a specific vehicle"""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return []
        
        drivers = self._get_available_drivers(vehicle.branch_id)
        recommendations = []
        
        for driver in drivers:
            score = self._calculate_recommendation_score(driver, vehicle, 'full_day')
            recommendations.append(score)
        
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return recommendations[:limit]
    
    def get_vehicle_recommendations(self, driver_id: int, limit: int = 5) -> List[RecommendationScore]:
        """Get best vehicle recommendations for a specific driver"""
        driver = Driver.query.get(driver_id)
        if not driver:
            return []
        
        vehicles = self._get_available_vehicles(driver.branch_id)
        recommendations = []
        
        for vehicle in vehicles:
            score = self._calculate_recommendation_score(driver, vehicle, 'full_day')
            recommendations.append(score)
        
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        return recommendations[:limit]
    
    def _adjust_strategy_weights(self, strategy: str):
        """Adjust scoring weights based on recommendation strategy"""
        if strategy == 'performance':
            self.weights.update({
                'performance': 0.40,
                'experience': 0.25,
                'compatibility': 0.15,
                'availability': 0.10,
                'location': 0.05,
                'workload': 0.05
            })
        elif strategy == 'availability':
            self.weights.update({
                'availability': 0.35,
                'location': 0.20,
                'workload': 0.20,
                'compatibility': 0.15,
                'performance': 0.05,
                'experience': 0.05
            })
        # 'balanced' uses default weights
    
    def _get_available_drivers(self, branch_id: Optional[int] = None) -> List[Driver]:
        """Get list of available drivers"""
        query = Driver.query.filter_by(status=DriverStatus.ACTIVE)
        
        if branch_id:
            query = query.filter_by(branch_id=branch_id)
        
        return query.all()
    
    def _get_available_vehicles(self, branch_id: Optional[int] = None) -> List[Vehicle]:
        """Get list of available vehicles"""
        query = Vehicle.query.filter_by(
            status=VehicleStatus.ACTIVE,
            is_available=True
        )
        
        if branch_id:
            query = query.filter_by(branch_id=branch_id)
        
        return query.all()
    
    def _calculate_recommendation_score(self, 
                                      driver: Driver, 
                                      vehicle: Vehicle, 
                                      shift_type: str = 'full_day',
                                      date_range: Tuple[datetime, datetime] = None) -> RecommendationScore:
        """Calculate comprehensive recommendation score for driver-vehicle pair"""
        
        reasoning = []
        
        # 1. Performance Score (0-100)
        performance_score = self._calculate_performance_score(driver, reasoning)
        
        # 2. Compatibility Score (0-100)
        compatibility_score = self._calculate_compatibility_score(driver, vehicle, reasoning)
        
        # 3. Availability Score (0-100)
        availability_score = self._calculate_availability_score(driver, vehicle, shift_type, date_range, reasoning)
        
        # 4. Experience Score (0-100)
        experience_score = self._calculate_experience_score(driver, vehicle, reasoning)
        
        # 5. Location Score (0-100)
        location_score = self._calculate_location_score(driver, vehicle, reasoning)
        
        # 6. Workload Score (0-100)
        workload_score = self._calculate_workload_score(driver, reasoning)
        
        # Calculate weighted total score
        total_score = (
            performance_score * self.weights['performance'] +
            compatibility_score * self.weights['compatibility'] +
            availability_score * self.weights['availability'] +
            experience_score * self.weights['experience'] +
            location_score * self.weights['location'] +
            workload_score * self.weights['workload']
        )
        
        return RecommendationScore(
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            total_score=round(total_score, 2),
            performance_score=round(performance_score, 2),
            compatibility_score=round(compatibility_score, 2),
            availability_score=round(availability_score, 2),
            experience_score=round(experience_score, 2),
            location_score=round(location_score, 2),
            reasoning=reasoning
        )
    
    def _calculate_performance_score(self, driver: Driver, reasoning: List[str]) -> float:
        """Calculate driver performance score based on historical data"""
        score = 50.0  # Base score
        
        # Factor 1: Average rating
        if driver.rating_average > 0:
            rating_score = (driver.rating_average / 5.0) * 30
            score += rating_score - 15  # Normalize around base
            if driver.rating_average >= 4.5:
                reasoning.append(f"Excellent rating: {driver.rating_average:.1f}/5.0")
            elif driver.rating_average >= 4.0:
                reasoning.append(f"Good rating: {driver.rating_average:.1f}/5.0")
        
        # Factor 2: Completion rate from recent duties
        recent_duties = Duty.query.filter_by(driver_id=driver.id).filter(
            Duty.start_time >= datetime.now() - timedelta(days=30)
        ).all()
        
        if recent_duties:
            completed = len([d for d in recent_duties if d.status == DutyStatus.COMPLETED])
            completion_rate = completed / len(recent_duties)
            completion_score = completion_rate * 20
            score += completion_score - 10  # Normalize
            
            if completion_rate >= 0.95:
                reasoning.append(f"High completion rate: {completion_rate:.1%}")
            elif completion_rate < 0.8:
                reasoning.append(f"Low completion rate: {completion_rate:.1%}")
        
        # Factor 3: Total experience (duties completed)
        if driver.total_trips > 100:
            experience_bonus = min((driver.total_trips - 100) / 1000 * 10, 10)
            score += experience_bonus
            if driver.total_trips > 500:
                reasoning.append(f"Highly experienced: {driver.total_trips} trips")
        
        return min(max(score, 0), 100)
    
    def _calculate_compatibility_score(self, driver: Driver, vehicle: Vehicle, reasoning: List[str]) -> float:
        """Calculate driver-vehicle compatibility score"""
        score = 50.0  # Base score
        
        # Factor 1: Vehicle type experience
        past_assignments = VehicleAssignment.query.join(Vehicle).filter(
            VehicleAssignment.driver_id == driver.id,
            Vehicle.vehicle_type_id == vehicle.vehicle_type_id,
            VehicleAssignment.status.in_([AssignmentStatus.COMPLETED, AssignmentStatus.ACTIVE])
        ).count()
        
        if past_assignments > 0:
            experience_bonus = min(past_assignments * 5, 25)
            score += experience_bonus
            reasoning.append(f"Experience with {vehicle.vehicle_type.name}: {past_assignments} assignments")
        else:
            score -= 10  # Penalty for no experience
            reasoning.append(f"No prior experience with {vehicle.vehicle_type.name}")
        
        # Factor 2: Fuel type familiarity
        fuel_experience = Duty.query.join(Vehicle).filter(
            Duty.driver_id == driver.id,
            Vehicle.fuel_type == vehicle.fuel_type
        ).count()
        
        if fuel_experience > 10:
            score += 10
            reasoning.append(f"Familiar with {vehicle.fuel_type} vehicles")
        
        # Factor 3: Branch compatibility (already filtered, so bonus)
        score += 15
        reasoning.append("Same branch assignment")
        
        return min(max(score, 0), 100)
    
    def _calculate_availability_score(self, driver: Driver, vehicle: Vehicle, 
                                    shift_type: str, date_range: Tuple[datetime, datetime],
                                    reasoning: List[str]) -> float:
        """Calculate availability score based on current assignments"""
        score = 100.0  # Start with perfect availability
        
        # Check driver current assignment
        if driver.current_vehicle_id:
            score -= 30
            reasoning.append("Driver currently assigned to another vehicle")
        
        # Check for conflicting assignments in date range
        if date_range:
            start_date, end_date = date_range
            
            conflicting_assignments = VehicleAssignment.query.filter(
                and_(
                    VehicleAssignment.driver_id == driver.id,
                    VehicleAssignment.status.in_([AssignmentStatus.ACTIVE, AssignmentStatus.SCHEDULED]),
                    VehicleAssignment.start_date <= end_date.date(),
                    (VehicleAssignment.end_date.is_(None)) | (VehicleAssignment.end_date >= start_date.date())
                )
            ).first()
            
            if conflicting_assignments:
                score -= 50
                reasoning.append("Conflicting assignment in date range")
        
        # Check recent duty patterns
        recent_duties = Duty.query.filter_by(driver_id=driver.id).filter(
            Duty.start_time >= datetime.now() - timedelta(days=7)
        ).count()
        
        if recent_duties > 20:  # Very busy
            score -= 20
            reasoning.append("Heavy workload in past week")
        elif recent_duties < 5:  # Underutilized
            score += 10
            reasoning.append("Available for more duties")
        
        return min(max(score, 0), 100)
    
    def _calculate_experience_score(self, driver: Driver, vehicle: Vehicle, reasoning: List[str]) -> float:
        """Calculate experience score with this specific vehicle"""
        score = 30.0  # Base score
        
        # Experience with this exact vehicle
        vehicle_duties = Duty.query.filter_by(
            driver_id=driver.id,
            vehicle_id=vehicle.id
        ).count()
        
        if vehicle_duties > 0:
            vehicle_bonus = min(vehicle_duties * 10, 40)
            score += vehicle_bonus
            reasoning.append(f"Previous experience with this vehicle: {vehicle_duties} duties")
        
        # Experience with similar vehicles (same type)
        similar_duties = Duty.query.join(Vehicle).filter(
            Duty.driver_id == driver.id,
            Vehicle.vehicle_type_id == vehicle.vehicle_type_id,
            Vehicle.id != vehicle.id
        ).count()
        
        if similar_duties > 10:
            score += 20
            reasoning.append(f"Experience with similar vehicles: {similar_duties} duties")
        
        # Total driving experience
        if driver.total_trips > 1000:
            score += 10
            reasoning.append("Highly experienced driver")
        
        return min(max(score, 0), 100)
    
    def _calculate_location_score(self, driver: Driver, vehicle: Vehicle, reasoning: List[str]) -> float:
        """Calculate location/proximity score"""
        score = 70.0  # Base score for same branch
        
        # Same branch is already a good match
        reasoning.append(f"Both in {driver.branch.name} branch")
        
        # Could add more sophisticated location scoring here
        # For now, same branch gets a good score
        
        return min(max(score, 0), 100)
    
    def _calculate_workload_score(self, driver: Driver, reasoning: List[str]) -> float:
        """Calculate workload balance score"""
        score = 50.0
        
        # Check current month duties
        current_month_duties = Duty.query.filter(
            Duty.driver_id == driver.id,
            func.extract('month', Duty.start_time) == datetime.now().month,
            func.extract('year', Duty.start_time) == datetime.now().year
        ).count()
        
        # Average duties per driver in same branch
        branch_drivers = Driver.query.filter_by(branch_id=driver.branch_id, status=DriverStatus.ACTIVE).all()
        if branch_drivers:
            total_branch_duties = sum(
                Duty.query.filter(
                    Duty.driver_id == d.id,
                    func.extract('month', Duty.start_time) == datetime.now().month,
                    func.extract('year', Duty.start_time) == datetime.now().year
                ).count() for d in branch_drivers
            )
            avg_duties = total_branch_duties / len(branch_drivers)
            
            if current_month_duties < avg_duties * 0.8:
                score += 30
                reasoning.append("Below average workload - good for assignment")
            elif current_month_duties > avg_duties * 1.5:
                score -= 20
                reasoning.append("Above average workload")
        
        return min(max(score, 0), 100)

    def get_analytics_summary(self, branch_id: Optional[int] = None) -> Dict:
        """Get analytics summary for the recommendation engine"""
        
        # Driver performance distribution
        drivers = self._get_available_drivers(branch_id)
        performance_scores = []
        
        for driver in drivers:
            score = self._calculate_performance_score(driver, [])
            performance_scores.append({
                'driver_id': driver.id,
                'driver_name': driver.full_name,
                'performance_score': score,
                'rating': driver.rating_average,
                'total_trips': driver.total_trips
            })
        
        # Vehicle utilization
        vehicles = self._get_available_vehicles(branch_id)
        vehicle_stats = []
        
        for vehicle in vehicles:
            recent_duties = Duty.query.filter(
                Duty.vehicle_id == vehicle.id,
                Duty.start_time >= datetime.now() - timedelta(days=30)
            ).count()
            
            vehicle_stats.append({
                'vehicle_id': vehicle.id,
                'registration': vehicle.registration_number,
                'vehicle_type': vehicle.vehicle_type.name,
                'recent_duties': recent_duties,
                'is_available': vehicle.is_available
            })
        
        return {
            'total_drivers': len(drivers),
            'total_vehicles': len(vehicles),
            'performance_scores': sorted(performance_scores, key=lambda x: x['performance_score'], reverse=True),
            'vehicle_utilization': sorted(vehicle_stats, key=lambda x: x['recent_duties'], reverse=True),
            'recommendation_weights': self.weights,
            'generated_at': datetime.now().isoformat()
        }

# Global instance
recommendation_engine = SmartRecommendationEngine()