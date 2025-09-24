#!/usr/bin/env python3
"""
Database migration script to add tracking pause fields to duties table
Usage: python migration_add_tracking_pause_fields.py
"""

import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    """Add tracking pause fields to duties table"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("Adding tracking pause fields to duties table...")
            
            # Add new columns for tracking pause functionality
            migration_queries = [
                """
                ALTER TABLE duties 
                ADD COLUMN IF NOT EXISTS tracking_pause_count INTEGER DEFAULT 0
                """,
                """
                ALTER TABLE duties 
                ADD COLUMN IF NOT EXISTS tracking_pause_duration INTEGER DEFAULT 0
                """,
                """
                ALTER TABLE duties 
                ADD COLUMN IF NOT EXISTS tracking_paused_at TIMESTAMP
                """,
                """
                ALTER TABLE duties 
                ADD COLUMN IF NOT EXISTS tracking_pause_reason VARCHAR(100)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_duties_tracking_paused 
                ON duties(tracking_paused_at) 
                WHERE tracking_paused_at IS NOT NULL
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_duties_pause_count 
                ON duties(tracking_pause_count)
                WHERE tracking_pause_count > 0
                """
            ]
            
            for query in migration_queries:
                print(f"Executing: {query.strip()}")
                conn.execute(text(query))
                conn.commit()
            
            print("✅ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
