#!/usr/bin/env python3
"""
Database Management Commands for PLS Travels

Production-safe database management commands with comprehensive safety features:
- Pre-migration backups
- Schema validation
- Connection testing
- Migration status tracking
- Emergency rollback procedures

Usage:
    python database_commands.py --help
    python database_commands.py status
    python database_commands.py backup
    python database_commands.py migrate --direction upgrade
    python database_commands.py validate
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from app import create_app
from utils.database_manager import database_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_app_context():
    """Setup Flask application context for database operations."""
    # Set a temporary SESSION_SECRET for CLI operations if not set
    if not os.environ.get('SESSION_SECRET'):
        os.environ['SESSION_SECRET'] = 'cli_temp_secret_not_for_production'
    
    app = create_app()
    return app.app_context()

def cmd_status(args):
    """Display comprehensive database status information."""
    with setup_app_context():
        print("=" * 60)
        print("DATABASE STATUS REPORT")
        print("=" * 60)
        
        # Connection test
        conn_success, conn_error = database_manager.test_connection()
        print(f"Connection Status: {'✅ HEALTHY' if conn_success else '❌ FAILED'}")
        if conn_error:
            print(f"Connection Error: {conn_error}")
        
        print()
        
        # Database information
        db_info = database_manager.get_database_info()
        
        print("Database Information:")
        print(f"  Engine: {db_info.get('engine_info', 'Unknown')}")
        print(f"  Version: {db_info.get('database_version', 'Unknown')}")
        print(f"  Size: {db_info.get('database_size', 'Unknown')}")
        print(f"  Tables: {db_info.get('table_count', 'Unknown')}")
        print(f"  Active Connections: {db_info.get('active_connections', 'Unknown')}")
        
        if 'table_statistics' in db_info:
            print(f"\nTable Statistics:")
            for table, count in db_info['table_statistics'].items():
                print(f"  {table}: {count} records")
        
        print()
        
        # Schema validation
        is_valid, issues = database_manager.validate_schema_integrity()
        print(f"Schema Integrity: {'✅ VALID' if is_valid else '❌ ISSUES FOUND'}")
        
        if issues:
            print("Issues Found:")
            for issue in issues:
                print(f"  ⚠️  {issue}")
        
        print(f"\nReport Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def cmd_backup(args):
    """Create a database backup with optional custom name."""
    with setup_app_context():
        print("Creating database backup...")
        
        backup_name = args.name or f"manual_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success, result = database_manager.backup_database(backup_name)
        
        if success:
            print(f"✅ Backup created successfully: {result}")
        else:
            print(f"❌ Backup failed: {result}")
            sys.exit(1)

def cmd_migrate(args):
    """Run database migration with safety checks."""
    with setup_app_context():
        print(f"Running migration: {args.direction}")
        
        if not args.skip_checks:
            print("Performing pre-migration safety checks...")
            
            # Connection test
            conn_success, conn_error = database_manager.test_connection()
            if not conn_success:
                print(f"❌ Connection test failed: {conn_error}")
                if not args.force:
                    print("Use --force to proceed anyway (not recommended)")
                    sys.exit(1)
            else:
                print("✅ Connection test passed")
            
            # Schema validation
            is_valid, issues = database_manager.validate_schema_integrity()
            if not is_valid and args.direction == "upgrade":
                print("⚠️  Schema issues detected:")
                for issue in issues:
                    print(f"    {issue}")
                if not args.force:
                    print("Use --force to proceed anyway")
                    sys.exit(1)
            else:
                print("✅ Schema validation passed")
        
        # Run migration
        success, message = database_manager.run_migration_safely(args.direction)
        
        if success:
            print(f"✅ Migration completed: {message}")
        else:
            print(f"❌ Migration failed: {message}")
            sys.exit(1)

def cmd_validate(args):
    """Validate database schema and integrity."""
    with setup_app_context():
        print("Validating database schema and integrity...")
        
        is_valid, issues = database_manager.validate_schema_integrity()
        
        if is_valid:
            print("✅ Database validation passed - no issues found")
        else:
            print(f"❌ Database validation failed - {len(issues)} issues found:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            sys.exit(1)

def cmd_info(args):
    """Display detailed database information."""
    with setup_app_context():
        db_info = database_manager.get_database_info()
        
        print("=" * 60)
        print("DETAILED DATABASE INFORMATION")
        print("=" * 60)
        
        for key, value in db_info.items():
            if isinstance(value, dict):
                print(f"{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")

def main():
    """Main command line interface."""
    parser = argparse.ArgumentParser(
        description="Database Management Commands for PLS Travels",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Display database status')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--name', help='Custom backup name')
    
    # Migration command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migration')
    migrate_parser.add_argument('--direction', choices=['upgrade', 'downgrade'], 
                               default='upgrade', help='Migration direction')
    migrate_parser.add_argument('--skip-checks', action='store_true',
                               help='Skip pre-migration safety checks')
    migrate_parser.add_argument('--force', action='store_true',
                               help='Force migration even if checks fail')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate database schema')
    
    # Info command  
    info_parser = subparsers.add_parser('info', help='Display detailed database information')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'status':
            cmd_status(args)
        elif args.command == 'backup':
            cmd_backup(args)
        elif args.command == 'migrate':
            cmd_migrate(args)
        elif args.command == 'validate':
            cmd_validate(args)
        elif args.command == 'info':
            cmd_info(args)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()