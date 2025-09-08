from datetime import datetime, timedelta, date
from models import VehicleAssignment, Driver, Vehicle, AssignmentStatus
from app import db
from collections import defaultdict

def check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, shift_type):
    """
    Check for assignment conflicts for a given driver and vehicle within a date range
    """
    conflicts = {
        'driver_conflict': None,
        'vehicle_conflict': None
    }
    
    # Check driver conflicts
    driver_conflict = VehicleAssignment.query.filter(
        VehicleAssignment.driver_id == driver_id,
        VehicleAssignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.ACTIVE]),
        VehicleAssignment.start_date <= (end_date or start_date),
        (VehicleAssignment.end_date.is_(None)) | (VehicleAssignment.end_date >= start_date)
    ).first()
    
    if driver_conflict:
        # For shift conflicts, check if shifts overlap
        if shift_type != 'full_day' and driver_conflict.shift_type != 'full_day':
            if not do_shifts_overlap(shift_type, driver_conflict.shift_type):
                driver_conflict = None
    
    conflicts['driver_conflict'] = driver_conflict
    
    # Check vehicle conflicts
    vehicle_conflict = VehicleAssignment.query.filter(
        VehicleAssignment.vehicle_id == vehicle_id,
        VehicleAssignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.ACTIVE]),
        VehicleAssignment.start_date <= (end_date or start_date),
        (VehicleAssignment.end_date.is_(None)) | (VehicleAssignment.end_date >= start_date)
    ).first()
    
    if vehicle_conflict:
        # For shift conflicts, check if shifts overlap
        if shift_type != 'full_day' and vehicle_conflict.shift_type != 'full_day':
            if not do_shifts_overlap(shift_type, vehicle_conflict.shift_type):
                vehicle_conflict = None
    
    conflicts['vehicle_conflict'] = vehicle_conflict
    
    return conflicts

def do_shifts_overlap(shift1, shift2):
    """
    Check if two shifts overlap in time
    """
    shift_times = {
        'morning': (6, 14),    # 6AM-2PM
        'evening': (14, 22),   # 2PM-10PM  
        'night': (22, 6),      # 10PM-6AM
        'full_day': (0, 24)    # Full day
    }
    
    if shift1 == 'full_day' or shift2 == 'full_day':
        return True
    
    start1, end1 = shift_times.get(shift1, (0, 24))
    start2, end2 = shift_times.get(shift2, (0, 24))
    
    # Handle overnight shifts (night shift)
    if start1 > end1:  # Night shift
        if start2 > end2:  # Both are night shifts
            return True
        else:
            return start2 < end1 or end2 > start1
    elif start2 > end2:  # Only shift2 is night shift
        return start1 < end2 or end1 > start2
    else:  # Normal day shifts
        return not (end1 <= start2 or end2 <= start1)

def generate_assignment_suggestions(driver_id, vehicle_id, start_date, end_date, shift_type):
    """
    Generate alternative assignment suggestions when conflicts exist
    """
    suggestions = []
    
    # Find alternative drivers for the same vehicle
    alternative_drivers = Driver.query.filter(
        Driver.status == 'ACTIVE',
        Driver.id != driver_id
    ).all()
    
    for driver in alternative_drivers[:5]:  # Limit to 5 suggestions
        conflicts = check_assignment_conflicts(driver.id, vehicle_id, start_date, end_date, shift_type)
        if not conflicts['driver_conflict']:
            suggestions.append({
                'type': 'alternative_driver',
                'driver_id': driver.id,
                'driver_name': driver.full_name,
                'vehicle_id': vehicle_id
            })
    
    # Find alternative vehicles for the same driver
    alternative_vehicles = Vehicle.query.filter(
        Vehicle.status == 'ACTIVE',
        Vehicle.is_available == True,
        Vehicle.id != vehicle_id
    ).all()
    
    for vehicle in alternative_vehicles[:5]:  # Limit to 5 suggestions
        conflicts = check_assignment_conflicts(driver_id, vehicle.id, start_date, end_date, shift_type)
        if not conflicts['vehicle_conflict']:
            suggestions.append({
                'type': 'alternative_vehicle',
                'driver_id': driver_id,
                'vehicle_id': vehicle.id,
                'vehicle_name': f"{vehicle.registration_number} - {vehicle.model or 'Unknown'}"
            })
    
    # Suggest different time slots
    if shift_type != 'full_day':
        alternative_shifts = ['morning', 'evening', 'night']
        alternative_shifts.remove(shift_type)
        
        for alt_shift in alternative_shifts:
            conflicts = check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, alt_shift)
            if not conflicts['driver_conflict'] and not conflicts['vehicle_conflict']:
                suggestions.append({
                    'type': 'alternative_shift',
                    'driver_id': driver_id,
                    'vehicle_id': vehicle_id,
                    'shift_type': alt_shift,
                    'shift_name': alt_shift.title() + ' Shift'
                })
    
    return suggestions

def build_assignment_calendar(assignments, start_date_str, end_date_str):
    """
    Build calendar data structure for displaying assignments
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    calendar_data = defaultdict(lambda: defaultdict(list))
    
    for assignment in assignments:
        # Find all dates this assignment covers within our range
        assignment_start = max(assignment.start_date, start_date)
        assignment_end = min(assignment.end_date or end_date, end_date)
        
        current_date = assignment_start
        while current_date <= assignment_end:
            calendar_data[current_date.strftime('%Y-%m-%d')]['assignments'].append({
                'id': assignment.id,
                'driver_name': assignment.driver.full_name,
                'vehicle_reg': assignment.vehicle.registration_number,
                'shift_type': assignment.shift_type,
                'status': assignment.status.value,
                'priority': assignment.priority,
                'assignment_type': assignment.assignment_type
            })
            current_date += timedelta(days=1)
    
    return dict(calendar_data)

def create_bulk_assignments(assignments_data, assigned_by_user_id):
    """
    Create multiple assignments from bulk data
    """
    created_assignments = []
    errors = []
    
    for assignment_data in assignments_data:
        try:
            # Validate assignment data
            driver_id = assignment_data.get('driver_id')
            vehicle_id = assignment_data.get('vehicle_id')
            start_date = datetime.strptime(assignment_data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(assignment_data.get('end_date'), '%Y-%m-%d').date() if assignment_data.get('end_date') else None
            shift_type = assignment_data.get('shift_type', 'full_day')
            
            # Check for conflicts
            conflicts = check_assignment_conflicts(driver_id, vehicle_id, start_date, end_date, shift_type)
            
            if conflicts['driver_conflict'] or conflicts['vehicle_conflict']:
                driver = Driver.query.get(driver_id)
                vehicle = Vehicle.query.get(vehicle_id)
                driver_name = driver.full_name if driver else "Unknown Driver"
                vehicle_name = vehicle.registration_number if vehicle else "Unknown Vehicle"
                errors.append(f"Conflict for {driver_name} - {vehicle_name} on {start_date}")
                continue
            
            # Create assignment
            assignment = VehicleAssignment()
            assignment.driver_id = driver_id
            assignment.vehicle_id = vehicle_id
            assignment.start_date = start_date
            assignment.end_date = end_date
            assignment.shift_type = shift_type
            assignment.assignment_type = assignment_data.get('assignment_type', 'regular')
            assignment.priority = assignment_data.get('priority', 2)
            assignment.notes = assignment_data.get('notes', '')
            assignment.assigned_by = assigned_by_user_id
            
            # Set status based on start date
            if start_date <= datetime.now().date():
                assignment.status = AssignmentStatus.ACTIVE
            else:
                assignment.status = AssignmentStatus.SCHEDULED
            
            db.session.add(assignment)
            created_assignments.append(assignment)
            
        except Exception as e:
            errors.append(f"Error creating assignment: {str(e)}")
    
    try:
        db.session.commit()
        return {
            'success': True,
            'created_count': len(created_assignments),
            'errors': errors
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'created_count': 0,
            'errors': errors + [f"Database error: {str(e)}"]
        }

def create_recurring_assignments(base_assignment_data, pattern, until_date, assigned_by_user_id):
    """
    Create recurring assignments based on a pattern
    """
    assignments_to_create = []
    start_date = datetime.strptime(base_assignment_data['start_date'], '%Y-%m-%d').date()
    current_date = start_date
    
    while current_date <= until_date:
        assignment_data = base_assignment_data.copy()
        assignment_data['start_date'] = current_date.strftime('%Y-%m-%d')
        
        # Calculate end date based on original duration
        if base_assignment_data.get('end_date'):
            original_duration = datetime.strptime(base_assignment_data['end_date'], '%Y-%m-%d').date() - start_date
            assignment_data['end_date'] = (current_date + original_duration).strftime('%Y-%m-%d')
        
        assignments_to_create.append(assignment_data)
        
        # Move to next occurrence based on pattern
        if pattern == 'daily':
            current_date += timedelta(days=1)
        elif pattern == 'weekly':
            current_date += timedelta(weeks=1)
        elif pattern == 'monthly':
            # Add one month (approximate)
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    return create_bulk_assignments(assignments_to_create, assigned_by_user_id)