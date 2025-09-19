"""
Application monitoring and metrics collection for PLS Travels
Provides health checks, performance metrics, and operational insights
"""

import os
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from flask import Flask, request, g, current_app
from sqlalchemy import text
from collections import defaultdict, deque


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a single performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Optional[Dict[str, str]] = None


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    service: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class PerformanceMonitor:
    """
    Tracks application performance metrics and provides insights
    """
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.request_times: deque = deque(maxlen=max_samples)
        self.error_counts: Dict[int, int] = defaultdict(int)
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record a request for performance monitoring"""
        self.request_times.append(duration)
        
        # Track endpoint-specific stats
        key = f"{method} {endpoint}"
        stats = self.endpoint_stats[key]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
        
        if status_code >= 400:
            stats['errors'] += 1
            self.error_counts[status_code] += 1
    
    def record_metric(self, name: str, value: float, unit: str, tags: Optional[Dict[str, str]] = None):
        """Record a custom metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        if not self.request_times:
            return {'message': 'No requests recorded yet'}
        
        request_times_list = list(self.request_times)
        total_requests = sum(stats['count'] for stats in self.endpoint_stats.values())
        
        stats = {
            'requests': {
                'total': total_requests,
                'avg_response_time': sum(request_times_list) / len(request_times_list),
                'min_response_time': min(request_times_list),
                'max_response_time': max(request_times_list),
                'p95_response_time': sorted(request_times_list)[int(0.95 * len(request_times_list))] if len(request_times_list) > 0 else 0,
                'p99_response_time': sorted(request_times_list)[int(0.99 * len(request_times_list))] if len(request_times_list) > 0 else 0
            },
            'errors': dict(self.error_counts),
            'endpoints': {}
        }
        
        # Add endpoint-specific stats
        for endpoint, endpoint_stats in self.endpoint_stats.items():
            if endpoint_stats['count'] > 0:
                stats['endpoints'][endpoint] = {
                    'requests': endpoint_stats['count'],
                    'avg_time': endpoint_stats['total_time'] / endpoint_stats['count'],
                    'min_time': endpoint_stats['min_time'],
                    'max_time': endpoint_stats['max_time'],
                    'error_rate': endpoint_stats['errors'] / endpoint_stats['count']
                }
        
        return stats


class HealthChecker:
    """
    Performs health checks on application components
    """
    
    def __init__(self, app: Flask):
        self.app = app
    
    def check_database(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            with self.app.app_context():
                from app import db
                
                # Simple connectivity test
                result = db.session.execute(text('SELECT 1 as test'))
                test_value = result.scalar()
                
                if test_value != 1:
                    return HealthCheckResult(
                        service='database',
                        status='unhealthy',
                        message='Database query returned unexpected result',
                        response_time_ms=round((time.time() - start_time) * 1000, 2)
                    )
                
                # Check table count as a basic schema validation (database-agnostic)
                try:
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    table_count = len(inspector.get_table_names())
                except Exception:
                    # Fallback for PostgreSQL
                    if 'postgresql' in str(db.engine.url):
                        result = db.session.execute(text("""
                            SELECT COUNT(*) as table_count 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public'
                        """))
                        table_count = result.scalar()
                    else:
                        # SQLite fallback
                        result = db.session.execute(text("""
                            SELECT COUNT(*) as table_count 
                            FROM sqlite_master 
                            WHERE type='table'
                        """))
                        table_count = result.scalar()
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                return HealthCheckResult(
                    service='database',
                    status='healthy',
                    message=f'Database connection successful, {table_count} tables found',
                    response_time_ms=response_time,
                    details={'table_count': table_count}
                )
                
        except Exception as e:
            return HealthCheckResult(
                service='database',
                status='unhealthy',
                message=f'Database connection failed: {str(e)}',
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    def check_memory(self) -> HealthCheckResult:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            
            # Consider memory unhealthy if usage > 90%
            if memory.percent > 90:
                status = 'unhealthy'
                message = f'High memory usage: {memory.percent}%'
            elif memory.percent > 80:
                status = 'degraded'
                message = f'Memory usage above 80%: {memory.percent}%'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {memory.percent}%'
            
            return HealthCheckResult(
                service='memory',
                status=status,
                message=message,
                details={
                    'percent_used': memory.percent,
                    'available_mb': round(memory.available / 1024 / 1024, 2),
                    'used_mb': round(memory.used / 1024 / 1024, 2),
                    'total_mb': round(memory.total / 1024 / 1024, 2)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='memory',
                status='unhealthy',
                message=f'Memory check failed: {str(e)}'
            )
    
    def check_disk(self) -> HealthCheckResult:
        """Check disk space usage"""
        try:
            disk = psutil.disk_usage('/')
            percent_used = (disk.used / disk.total) * 100
            
            # Consider disk unhealthy if usage > 95%
            if percent_used > 95:
                status = 'unhealthy'
                message = f'Disk space critical: {percent_used:.1f}%'
            elif percent_used > 85:
                status = 'degraded'
                message = f'Disk space above 85%: {percent_used:.1f}%'
            else:
                status = 'healthy'
                message = f'Disk space normal: {percent_used:.1f}%'
            
            return HealthCheckResult(
                service='disk',
                status=status,
                message=message,
                details={
                    'percent_used': round(percent_used, 2),
                    'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                    'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                    'total_gb': round(disk.total / 1024 / 1024 / 1024, 2)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='disk',
                status='unhealthy',
                message=f'Disk check failed: {str(e)}'
            )
    
    def check_external_services(self) -> List[HealthCheckResult]:
        """Check external service dependencies"""
        results = []
        
        # Check Twilio (if configured)
        if os.environ.get('TWILIO_ACCOUNT_SID') and os.environ.get('TWILIO_AUTH_TOKEN'):
            try:
                from twilio.rest import Client
                start_time = time.time()
                
                client = Client(
                    os.environ.get('TWILIO_ACCOUNT_SID'),
                    os.environ.get('TWILIO_AUTH_TOKEN')
                )
                
                # Simple API test - get account info  
                account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
                if account_sid:
                    account = client.api.accounts(account_sid).fetch()
                response_time = round((time.time() - start_time) * 1000, 2)
                
                results.append(HealthCheckResult(
                    service='twilio',
                    status='healthy',
                    message=f'Twilio API accessible, account: {account.friendly_name}',
                    response_time_ms=response_time
                ))
                
            except Exception as e:
                response_time = None
                if 'start_time' in locals():
                    response_time = round((time.time() - start_time) * 1000, 2)
                
                results.append(HealthCheckResult(
                    service='twilio',
                    status='unhealthy',
                    message=f'Twilio API check failed: {str(e)}',
                    response_time_ms=response_time
                ))
        
        return results
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        checks = [
            self.check_database(),
            self.check_memory(),
            self.check_disk(),
            *self.check_external_services()
        ]
        
        # Determine overall status
        statuses = [check.status for check in checks]
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': [asdict(check) for check in checks],
            'application': {
                'name': 'PLS Travels',
                'version': os.environ.get('APP_VERSION', '1.0.0'),
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'uptime': self.get_uptime()
            }
        }
    
    def get_uptime(self) -> str:
        """Get application uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{int(days)}d {int(hours)}h {int(minutes)}m"
        except:
            return "unknown"


# Global instances
performance_monitor = PerformanceMonitor()


def setup_monitoring(app: Flask):
    """Set up monitoring middleware and health checks"""
    
    health_checker = HealthChecker(app)
    
    @app.before_request
    def before_request_monitoring():
        """Set up request monitoring"""
        g.start_time = time.time()
        
        # Add user context for logging
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            g.current_user_id = current_user.id
            g.current_username = getattr(current_user, 'username', 'unknown')
    
    @app.after_request
    def after_request_monitoring(response):
        """Record request metrics"""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            performance_monitor.record_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=response.status_code,
                duration=duration
            )
            
            # Log slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                logger.warning(f"Slow request detected", extra={
                    'method': request.method,
                    'path': request.path,
                    'duration': duration,
                    'status_code': response.status_code
                })
        
        return response
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Comprehensive health check endpoint"""
        return health_checker.run_all_checks()
    
    # Performance metrics endpoint
    @app.route('/metrics')
    def performance_metrics():
        """Get performance metrics"""
        return {
            'performance': performance_monitor.get_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    # Simple liveness probe
    @app.route('/ping')
    def ping():
        """Simple liveness check"""
        return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
    
    logger.info("Monitoring middleware and endpoints configured")