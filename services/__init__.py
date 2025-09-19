"""
Service Layer Architecture

This package contains business logic services that encapsulate complex operations
previously scattered throughout route handlers. Services provide:

1. **Transaction Management**: Atomic operations with proper rollback
2. **Business Logic Separation**: Clean separation of concerns from route handlers  
3. **Testability**: Easy to unit test business logic independently
4. **Reusability**: Business logic can be reused across different endpoints
5. **Error Handling**: Centralized error handling and logging

Services Architecture:
- **DriverService**: Driver lifecycle, approval workflows, profile management
- **DutyService**: Duty management, validation, calculations, GPS tracking
- **VehicleService**: Vehicle allocation, maintenance, availability tracking
- **ReportingService**: Dashboard statistics, revenue calculations, analytics
- **FileService**: File upload handling, document management, photo processing
- **NotificationService**: WhatsApp, SMS, email notifications
- **AuditService**: Centralized audit logging and security tracking
"""

from .driver_service import DriverService
from .duty_service import DutyService
from .vehicle_service import VehicleService
from .reporting_service import ReportingService
from .file_service import FileService
from .notification_service import NotificationService
from .audit_service import AuditService
from .transaction_helper import TransactionHelper

__all__ = [
    'DriverService',
    'DutyService', 
    'VehicleService',
    'ReportingService',
    'FileService',
    'NotificationService',
    'AuditService',
    'TransactionHelper'
]