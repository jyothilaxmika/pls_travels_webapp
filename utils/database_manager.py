"""
Database Management Utilities for Production-Safe Operations

This module provides comprehensive database management functionality including:
- Safe migration commands with rollback capabilities
- Database backup and restoration
- Schema validation and integrity checks
- Transaction helpers for complex operations
- Health monitoring and connection testing
"""

import os
import logging
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from flask import current_app
from sqlalchemy import text, inspect, MetaData
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from app import db

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Comprehensive database management system for production-safe operations.
    """
    
    def __init__(self):
        self.backup_dir = "database_backups"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test database connection and return status.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test: SUCCESS")
            return True, None
        except Exception as e:
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive database information for monitoring.
        
        Returns:
            Dict[str, Any]: Database information including version, size, connections
        """
        try:
            from flask import current_app
            effective_db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'Unknown')
            
            info = {
                'connection_successful': False,
                'database_url_configured': bool(os.environ.get('DATABASE_URL')),
                'effective_database_url': str(effective_db_url).split('@')[0] + '@***' if '@' in str(effective_db_url) else str(effective_db_url),
                'engine_info': str(db.engine.url).split('@')[0] + '@***',  # Hide credentials
                'pool_size': getattr(db.engine.pool, 'size', 'N/A'),
                'checked_out_connections': getattr(db.engine.pool, 'checkedout', 'N/A'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            with db.engine.connect() as conn:
                # Database-specific queries
                database_url = str(db.engine.url)
                
                if 'postgresql' in database_url:
                    # PostgreSQL specific info
                    result = conn.execute(text("SELECT version()"))
                    info['database_version'] = result.scalar()
                    
                    result = conn.execute(text("""
                        SELECT pg_size_pretty(pg_database_size(current_database())) as size
                    """))
                    info['database_size'] = result.scalar()
                    
                    result = conn.execute(text("""
                        SELECT count(*) as active_connections 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """))
                    info['active_connections'] = result.scalar()
                    
                elif 'sqlite' in database_url:
                    # SQLite specific info
                    result = conn.execute(text("SELECT sqlite_version()"))
                    info['database_version'] = f"SQLite {result.scalar()}"
                    
                    # Get database file size
                    db_path = database_url.replace('sqlite:///', '')
                    if os.path.exists(db_path):
                        size_bytes = os.path.getsize(db_path)
                        info['database_size'] = f"{size_bytes / (1024*1024):.2f} MB"
                    else:
                        info['database_size'] = "Unknown"
                    
                    info['active_connections'] = 1  # SQLite single connection
                
                # Count tables and records
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                info['table_count'] = len(tables)
                
                # Count records in major tables
                table_stats = {}
                important_tables = ['users', 'drivers', 'vehicles', 'duties', 'branches']
                for table in important_tables:
                    if table in tables:
                        try:
                            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                            table_stats[table] = result.scalar()
                        except Exception as e:
                            table_stats[table] = f"Error: {str(e)}"
                
                info['table_statistics'] = table_stats
                info['connection_successful'] = True
                
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            info['error'] = str(e)
            info['connection_successful'] = False
        
        return info
    
    def validate_schema_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate database schema integrity and constraints.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Required tables check
            required_tables = [
                'users', 'drivers', 'vehicles', 'duties', 'branches', 
                'regions', 'audit_logs', 'duty_schemes'
            ]
            
            for table in required_tables:
                if table not in tables:
                    issues.append(f"Missing required table: {table}")
            
            # Check foreign key constraints
            with db.engine.connect() as conn:
                database_url = str(db.engine.url)
                
                if 'postgresql' in database_url:
                    # PostgreSQL constraint validation
                    result = conn.execute(text("""
                        SELECT conname, conrelid::regclass 
                        FROM pg_constraint 
                        WHERE contype = 'f' AND NOT convalidated
                    """))
                    invalid_fks = result.fetchall()
                    for fk in invalid_fks:
                        issues.append(f"Invalid foreign key constraint: {fk[0]} on {fk[1]}")
                
                # Check for orphaned records (basic checks)
                orphan_checks = [
                    ("drivers", "user_id", "users", "id"),
                    ("drivers", "branch_id", "branches", "id"), 
                    ("duties", "driver_id", "drivers", "id"),
                    ("duties", "vehicle_id", "vehicles", "id"),
                    ("vehicles", "branch_id", "branches", "id")
                ]
                
                for child_table, child_col, parent_table, parent_col in orphan_checks:
                    if child_table in tables and parent_table in tables:
                        try:
                            result = conn.execute(text(f"""
                                SELECT COUNT(*) FROM {child_table} c 
                                LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col}
                                WHERE c.{child_col} IS NOT NULL AND p.{parent_col} IS NULL
                            """))
                            orphan_count = result.scalar()
                            if orphan_count > 0:
                                issues.append(f"Found {orphan_count} orphaned records in {child_table}.{child_col}")
                        except Exception as e:
                            issues.append(f"Could not check orphans in {child_table}: {str(e)}")
            
            is_valid = len(issues) == 0
            if is_valid:
                logger.info("Database schema validation: PASSED")
            else:
                logger.warning(f"Database schema validation: FAILED with {len(issues)} issues")
                
            return is_valid, issues
            
        except Exception as e:
            error_msg = f"Schema validation error: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def backup_database(self, backup_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a database backup with timestamp.
        
        Args:
            backup_name: Optional custom backup name
            
        Returns:
            Tuple[bool, str]: (success, backup_path_or_error)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not backup_name:
                backup_name = f"backup_{timestamp}"
            
            database_url = str(db.engine.url)
            
            if 'postgresql' in database_url:
                # PostgreSQL backup using pg_dump
                backup_file = os.path.join(self.backup_dir, f"{backup_name}.sql")
                
                # Extract connection details
                from urllib.parse import urlparse
                parsed = urlparse(database_url.replace('postgresql+psycopg2://', 'postgresql://'))
                
                env = os.environ.copy()
                env['PGPASSWORD'] = parsed.password or ''
                
                cmd = [
                    'pg_dump',
                    '-h', parsed.hostname or 'localhost',
                    '-p', str(parsed.port or 5432),
                    '-U', parsed.username or 'postgres',
                    '-d', parsed.path[1:] if parsed.path else 'postgres',
                    '--no-password',
                    '--verbose',
                    '-f', backup_file
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"PostgreSQL backup created: {backup_file}")
                    return True, backup_file
                else:
                    error_msg = f"pg_dump failed: {result.stderr}"
                    logger.error(error_msg)
                    return False, error_msg
            
            elif 'sqlite' in database_url:
                # SQLite backup using file copy
                source_path = database_url.replace('sqlite:///', '')
                backup_file = os.path.join(self.backup_dir, f"{backup_name}.db")
                
                if os.path.exists(source_path):
                    import shutil
                    shutil.copy2(source_path, backup_file)
                    logger.info(f"SQLite backup created: {backup_file}")
                    return True, backup_file
                else:
                    error_msg = f"Source database not found: {source_path}"
                    logger.error(error_msg)
                    return False, error_msg
            
            else:
                error_msg = f"Backup not supported for database type: {database_url}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def run_migration_safely(self, direction: str = "upgrade") -> Tuple[bool, str]:
        """
        Run database migration with safety checks and backup.
        
        Args:
            direction: 'upgrade' or 'downgrade'
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Step 1: Validate current schema
            logger.info("Step 1: Validating current database schema...")
            is_valid, issues = self.validate_schema_integrity()
            if not is_valid and direction == "upgrade":
                logger.warning(f"Schema issues found: {issues}")
                logger.info("Proceeding with migration despite issues...")
            
            # Step 2: Create backup
            logger.info("Step 2: Creating pre-migration backup...")
            backup_success, backup_result = self.backup_database(f"pre_migration_{direction}")
            if not backup_success:
                return False, f"Backup failed: {backup_result}"
            
            logger.info(f"Backup created: {backup_result}")
            
            # Step 3: Test connection
            logger.info("Step 3: Testing database connection...")
            conn_success, conn_error = self.test_connection()
            if not conn_success:
                return False, f"Connection test failed: {conn_error}"
            
            # Step 4: Run migration
            logger.info(f"Step 4: Running migration ({direction})...")
            
            cmd = ['flask', '--app', 'app:create_app', 'db', direction]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                logger.info(f"Migration {direction} completed successfully")
                
                # Step 5: Post-migration validation
                logger.info("Step 5: Post-migration validation...")
                post_valid, post_issues = self.validate_schema_integrity()
                
                if post_valid:
                    return True, f"Migration {direction} completed successfully with validation passed"
                else:
                    logger.warning(f"Post-migration validation issues: {post_issues}")
                    return True, f"Migration {direction} completed but validation found issues: {post_issues}"
            else:
                error_msg = f"Migration {direction} failed: {result.stderr or result.stdout}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Migration process failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# Singleton instance
database_manager = DatabaseManager()