"""
Uber Fleet Data Synchronization Jobs

This module handles bidirectional data synchronization between PLS TRAVELS
and Uber Fleet Supplier APIs including vehicles, drivers, and trip data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import and_, or_
from app import db
from models import (
    Vehicle, Driver, Duty, UberSyncJob, UberSyncLog, UberIntegrationSettings,
    User, Branch, DriverStatus, VehicleStatus
)
from uber_service import uber_service, UberAPIError

# Configure logging
logger = logging.getLogger(__name__)

class UberDataSync:
    """
    Main class for handling Uber Fleet data synchronization
    """
    
    def __init__(self):
        self.service = uber_service
    
    def get_sync_settings(self) -> Optional[UberIntegrationSettings]:
        """Get current Uber integration settings"""
        return UberIntegrationSettings.query.first()
    
    def create_default_settings(self, user_id: int) -> UberIntegrationSettings:
        """Create default integration settings"""
        settings = UberIntegrationSettings(
            is_enabled=False,
            sync_frequency_hours=24,
            auto_sync_vehicles=True,
            auto_sync_drivers=True,
            auto_sync_trips=False,
            sync_direction_vehicles='bidirectional',
            sync_direction_drivers='to_uber',
            max_retry_attempts=3,
            api_calls_per_minute=60,
            batch_size=50,
            updated_by=user_id
        )
        db.session.add(settings)
        db.session.commit()
        return settings
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Uber APIs"""
        try:
            result = self.service.test_connection()
            logger.info(f"Uber connection test: {result['status']}")
            return result
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}',
                'authenticated': False
            }
    
    def create_sync_job(self, job_type: str, sync_direction: str, user_id: int, 
                       config: Dict[str, Any] = None) -> UberSyncJob:
        """Create a new sync job"""
        job = UberSyncJob(
            job_type=job_type,
            sync_direction=sync_direction,
            status='pending',
            scheduled_at=datetime.utcnow(),
            sync_config=json.dumps(config or {}),
            initiated_by=user_id
        )
        db.session.add(job)
        db.session.commit()
        return job
    
    def log_sync_operation(self, job_id: int, record_type: str, local_id: Optional[int], 
                          uber_id: Optional[str], operation: str, status: str,
                          request_data: Optional[Dict] = None, response_data: Optional[Dict] = None, 
                          error_message: Optional[str] = None):
        """Log individual sync operations"""
        log = UberSyncLog(
            sync_job_id=job_id,
            record_type=record_type,
            local_record_id=local_id,
            uber_record_id=uber_id,
            operation=operation,
            status=status,
            request_data=json.dumps(request_data) if request_data else None,
            response_data=json.dumps(response_data) if response_data else None,
            error_message=error_message
        )
        db.session.add(log)
    
    def sync_vehicles_to_uber(self, job: UberSyncJob) -> Tuple[int, int]:
        """Sync vehicles from PLS system to Uber"""
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.session.commit()
        
        successful = 0
        failed = 0
        
        try:
            # Get vehicles that need syncing
            vehicles = Vehicle.query.filter(
                and_(
                    Vehicle.status == VehicleStatus.ACTIVE,
                    or_(
                        Vehicle.uber_sync_status.in_(['none', 'failed']),
                        Vehicle.uber_sync_status.is_(None)
                    )
                )
            ).limit(50).all()
            
            job.records_processed = len(vehicles)
            
            for vehicle in vehicles:
                try:
                    # Prepare vehicle data for Uber API
                    vehicle_data = self._prepare_vehicle_data_for_uber(vehicle)
                    
                    if vehicle.uber_vehicle_id:
                        # Update existing vehicle
                        response = self.service.update_vehicle(vehicle.uber_vehicle_id, vehicle_data)
                        operation = 'update'
                    else:
                        # Create new vehicle
                        response = self.service.create_vehicle(vehicle_data)
                        operation = 'create'
                        
                        # Store Uber IDs
                        vehicle.uber_vehicle_id = response.get('id')
                        vehicle.uber_vehicle_uuid = response.get('uuid')
                    
                    # Update sync status
                    vehicle.uber_sync_status = 'synced'
                    vehicle.uber_last_sync = datetime.utcnow()
                    vehicle.uber_sync_error = None
                    vehicle.uber_vehicle_data = json.dumps(response)
                    
                    # Log success
                    self.log_sync_operation(
                        job.id, 'vehicle', vehicle.id, vehicle.uber_vehicle_id,
                        operation, 'success', vehicle_data, response
                    )
                    
                    successful += 1
                    logger.info(f"Successfully synced vehicle {vehicle.registration_number} to Uber")
                    
                except UberAPIError as e:
                    vehicle.uber_sync_status = 'failed'
                    vehicle.uber_sync_error = str(e)
                    
                    self.log_sync_operation(
                        job.id, 'vehicle', vehicle.id, vehicle.uber_vehicle_id,
                        'sync', 'failed', vehicle_data, None, str(e)
                    )
                    
                    failed += 1
                    logger.error(f"Failed to sync vehicle {vehicle.registration_number}: {str(e)}")
                
                except Exception as e:
                    vehicle.uber_sync_status = 'failed'
                    vehicle.uber_sync_error = str(e)
                    
                    self.log_sync_operation(
                        job.id, 'vehicle', vehicle.id, vehicle.uber_vehicle_id,
                        'sync', 'failed', None, None, str(e)
                    )
                    
                    failed += 1
                    logger.error(f"Unexpected error syncing vehicle {vehicle.registration_number}: {str(e)}")
            
            # Update job status
            job.records_successful = successful
            job.records_failed = failed
            job.status = 'completed' if failed == 0 else 'completed'  # Mark as completed even with failures
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            logger.error(f"Vehicle sync job failed: {str(e)}")
        
        finally:
            db.session.commit()
        
        return successful, failed
    
    def sync_drivers_to_uber(self, job: UberSyncJob) -> Tuple[int, int]:
        """Sync drivers from PLS system to Uber"""
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.session.commit()
        
        successful = 0
        failed = 0
        
        try:
            # Get active drivers that need syncing
            drivers = Driver.query.filter(
                and_(
                    Driver.status.in_([DriverStatus.ACTIVE, DriverStatus.PENDING]),
                    or_(
                        Driver.uber_sync_status.in_(['none', 'failed']),
                        Driver.uber_sync_status.is_(None)
                    )
                )
            ).limit(50).all()
            
            job.records_processed = len(drivers)
            
            for driver in drivers:
                try:
                    # Prepare driver data for Uber API
                    driver_data = self._prepare_driver_data_for_uber(driver)
                    
                    if driver.uber_driver_id:
                        # Update existing driver
                        response = self.service.update_driver(driver.uber_driver_id, driver_data)
                        operation = 'update'
                    else:
                        # Create new driver
                        response = self.service.create_driver(driver_data)
                        operation = 'create'
                        
                        # Store Uber IDs
                        driver.uber_driver_id = response.get('id')
                        driver.uber_driver_uuid = response.get('uuid')
                    
                    # Update sync status
                    driver.uber_sync_status = 'synced'
                    driver.uber_last_sync = datetime.utcnow()
                    driver.uber_sync_error = None
                    driver.uber_profile_data = json.dumps(response)
                    
                    # Log success
                    self.log_sync_operation(
                        job.id, 'driver', driver.id, driver.uber_driver_id,
                        operation, 'success', driver_data, response
                    )
                    
                    successful += 1
                    logger.info(f"Successfully synced driver {driver.full_name} to Uber")
                    
                except UberAPIError as e:
                    driver.uber_sync_status = 'failed'
                    driver.uber_sync_error = str(e)
                    
                    self.log_sync_operation(
                        job.id, 'driver', driver.id, driver.uber_driver_id,
                        'sync', 'failed', driver_data, None, str(e)
                    )
                    
                    failed += 1
                    logger.error(f"Failed to sync driver {driver.full_name}: {str(e)}")
                
                except Exception as e:
                    driver.uber_sync_status = 'failed'
                    driver.uber_sync_error = str(e)
                    
                    self.log_sync_operation(
                        job.id, 'driver', driver.id, driver.uber_driver_id,
                        'sync', 'failed', None, None, str(e)
                    )
                    
                    failed += 1
                    logger.error(f"Unexpected error syncing driver {driver.full_name}: {str(e)}")
            
            # Update job status
            job.records_successful = successful
            job.records_failed = failed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            logger.error(f"Driver sync job failed: {str(e)}")
        
        finally:
            db.session.commit()
        
        return successful, failed
    
    def sync_trips_from_uber(self, job: UberSyncJob, start_date: datetime, end_date: datetime) -> Tuple[int, int]:
        """Sync trip data from Uber to PLS system"""
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.session.commit()
        
        successful = 0
        failed = 0
        
        try:
            # Get trip data from Uber
            trips = self.service.get_trips(start_date, end_date, limit=50)
            job.records_processed = len(trips)
            
            for trip_data in trips:
                try:
                    # Process trip data and create/update duty records
                    duty = self._create_or_update_duty_from_uber_trip(trip_data)
                    
                    if duty:
                        self.log_sync_operation(
                            job.id, 'trip', duty.id, trip_data.get('id'),
                            'import', 'success', None, trip_data
                        )
                        successful += 1
                        logger.info(f"Successfully imported trip {trip_data.get('id')}")
                    else:
                        self.log_sync_operation(
                            job.id, 'trip', None, trip_data.get('id'),
                            'import', 'skipped', None, trip_data, 'Unable to match driver/vehicle'
                        )
                        
                except Exception as e:
                    self.log_sync_operation(
                        job.id, 'trip', None, trip_data.get('id'),
                        'import', 'failed', None, trip_data, str(e)
                    )
                    failed += 1
                    logger.error(f"Failed to import trip {trip_data.get('id')}: {str(e)}")
            
            # Update job status
            job.records_successful = successful
            job.records_failed = failed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            logger.error(f"Trip sync job failed: {str(e)}")
        
        finally:
            db.session.commit()
        
        return successful, failed
    
    def _prepare_vehicle_data_for_uber(self, vehicle: Vehicle) -> Dict[str, Any]:
        """Prepare vehicle data for Uber API format"""
        return {
            'external_id': f'pls_{vehicle.id}',
            'registration_number': vehicle.registration_number,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.manufacturing_year,
            'color': vehicle.color,
            'vehicle_type': vehicle.vehicle_type or 'car',
            'license_plate': vehicle.registration_number,
            'vin': vehicle.chassis_number,
            'insurance_expiry': vehicle.insurance_expiry_date.isoformat() if vehicle.insurance_expiry_date else None,
            'status': 'active' if vehicle.status == VehicleStatus.ACTIVE else 'inactive',
            'custom_fields': {
                'branch_id': vehicle.branch_id,
                'gps_device_id': vehicle.gps_device_id,
                'fastag_id': vehicle.fastag_id
            }
        }
    
    def _prepare_driver_data_for_uber(self, driver: Driver) -> Dict[str, Any]:
        """Prepare driver data for Uber API format"""
        return {
            'external_id': f'pls_{driver.id}',
            'first_name': driver.full_name.split(' ')[0] if driver.full_name else '',
            'last_name': ' '.join(driver.full_name.split(' ')[1:]) if driver.full_name and ' ' in driver.full_name else '',
            'email': driver.user.email if driver.user else None,
            'phone_number': driver.user.phone if driver.user else None,
            'license_number': driver.license_number,
            'license_expiry': driver.license_expiry.isoformat() if driver.license_expiry else None,
            'status': 'active' if driver.status in [DriverStatus.ACTIVE, DriverStatus.PENDING] else 'inactive',
            'custom_fields': {
                'employee_id': driver.employee_id,
                'branch_id': driver.branch_id,
                'aadhar_number': driver.aadhar_number
            }
        }
    
    def _create_or_update_duty_from_uber_trip(self, trip_data: Dict[str, Any]) -> Optional[Duty]:
        """Create or update a duty record from Uber trip data"""
        try:
            # Try to find the driver and vehicle by Uber IDs
            driver = Driver.query.filter_by(uber_driver_uuid=trip_data.get('driver_uuid')).first()
            vehicle = Vehicle.query.filter_by(uber_vehicle_uuid=trip_data.get('vehicle_uuid')).first()
            
            if not driver or not vehicle:
                logger.warning(f"Could not find matching driver/vehicle for trip {trip_data.get('id')}")
                return None
            
            # Check if duty already exists for this trip
            existing_duty = Duty.query.filter(
                and_(
                    Duty.driver_id == driver.id,
                    Duty.vehicle_id == vehicle.id,
                    # Match by start time (within 5 minutes)
                    Duty.actual_start.between(
                        datetime.fromisoformat(trip_data['start_time'].replace('Z', '+00:00')) - timedelta(minutes=5),
                        datetime.fromisoformat(trip_data['start_time'].replace('Z', '+00:00')) + timedelta(minutes=5)
                    )
                )
            ).first()
            
            if existing_duty:
                # Update existing duty with Uber trip data
                duty = existing_duty
            else:
                # Create new duty
                duty = Duty(
                    driver_id=driver.id,
                    vehicle_id=vehicle.id,
                    branch_id=driver.branch_id,
                    actual_start=datetime.fromisoformat(trip_data['start_time'].replace('Z', '+00:00')),
                    status='completed'
                )
                db.session.add(duty)
            
            # Update duty with trip data
            if trip_data.get('end_time'):
                duty.actual_end = datetime.fromisoformat(trip_data['end_time'].replace('Z', '+00:00'))
            
            if trip_data.get('distance'):
                duty.total_distance = float(trip_data['distance'])
            
            if trip_data.get('revenue'):
                duty.gross_revenue = float(trip_data['revenue'])
            
            # Store Uber trip data
            if trip_data.get('trips'):
                duty.uber_trips = int(trip_data['trips'])
            
            if trip_data.get('uber_collected'):
                duty.uber_collected = float(trip_data['uber_collected'])
            
            # Store trip notes with metadata
            trip_metadata = {
                'uber_trip_id': trip_data.get('id'),
                'uber_trip_uuid': trip_data.get('uuid'),
                'trip_source': 'uber'
            }
            duty.notes = f"Uber Trip Data: {json.dumps(trip_metadata)}"
            
            db.session.commit()
            return duty
            
        except Exception as e:
            logger.error(f"Error creating/updating duty from trip data: {str(e)}")
            db.session.rollback()
            return None
    
    def run_sync_job(self, job_id: int) -> Dict[str, Any]:
        """Execute a sync job"""
        job = UberSyncJob.query.get(job_id)
        if not job:
            return {'status': 'error', 'message': 'Job not found'}
        
        if job.status != 'pending':
            return {'status': 'error', 'message': f'Job is already {job.status}'}
        
        try:
            if job.job_type == 'vehicles' and job.sync_direction in ['to_uber', 'bidirectional']:
                successful, failed = self.sync_vehicles_to_uber(job)
                return {
                    'status': 'completed',
                    'successful': successful,
                    'failed': failed,
                    'message': f'Vehicle sync completed: {successful} successful, {failed} failed'
                }
            
            elif job.job_type == 'drivers' and job.sync_direction in ['to_uber', 'bidirectional']:
                successful, failed = self.sync_drivers_to_uber(job)
                return {
                    'status': 'completed',
                    'successful': successful,
                    'failed': failed,
                    'message': f'Driver sync completed: {successful} successful, {failed} failed'
                }
            
            elif job.job_type == 'trips' and job.sync_direction in ['from_uber', 'bidirectional']:
                config = json.loads(job.sync_config) if job.sync_config else {}
                start_date = datetime.fromisoformat(config.get('start_date', (datetime.utcnow() - timedelta(days=1)).isoformat()))
                end_date = datetime.fromisoformat(config.get('end_date', datetime.utcnow().isoformat()))
                
                successful, failed = self.sync_trips_from_uber(job, start_date, end_date)
                return {
                    'status': 'completed',
                    'successful': successful,
                    'failed': failed,
                    'message': f'Trip sync completed: {successful} successful, {failed} failed'
                }
            
            else:
                job.status = 'failed'
                job.error_message = f'Unsupported job type/direction: {job.job_type}/{job.sync_direction}'
                job.completed_at = datetime.utcnow()
                db.session.commit()
                return {'status': 'error', 'message': job.error_message}
                
        except Exception as e:
            logger.error(f"Error running sync job {job_id}: {str(e)}")
            return {'status': 'error', 'message': str(e)}

# Global sync instance
uber_sync = UberDataSync()