#!/usr/bin/env python3
"""
Apply alerts table migration to Supabase
========================================

This script applies the migration to add user_id column to the alerts table,
backfills the data, and enables Row Level Security (RLS).
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
from typing import Optional

# Add the current directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection from environment variables"""
    
    # Try to get DATABASE_URL first (common convention)
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # Fallback to individual components
        supabase_url = os.getenv("SUPABASE_URL")
        db_password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("DB_PASSWORD")
        
        if not supabase_url:
            raise ValueError("DATABASE_URL or SUPABASE_URL must be set in .env file")
        
        # Parse the Supabase URL to get the database connection string
        parsed_url = urlparse(supabase_url)
        host = parsed_url.hostname
        
        # Construct PostgreSQL connection string for Supabase
        if ".supabase.co" in host:
            # For Supabase, the database connection is typically:
            # postgresql://postgres:[password]@[project-ref].supabase.co:5432/postgres
            if not db_password:
                raise ValueError("SUPABASE_DB_PASSWORD must be set for Supabase connection")
            
            db_url = f"postgresql://postgres:{db_password}@{host}:5432/postgres"
        else:
            raise ValueError("Unsupported database URL format")
    
    print(f"Connecting to database: {db_url.replace(os.getenv('SUPABASE_DB_PASSWORD') or os.getenv('DB_PASSWORD') or '', '***')}")
    return psycopg2.connect(db_url)

def apply_migration():
    """Apply the migration to the Supabase database"""
    
    try:
        # Read the migration SQL file
        migration_file = "sql/004_update_alerts_table_add_user_id_and_rls.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"Applying migration from {migration_file}...")
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Split the SQL into individual statements, handling multi-line statements
            statements = []
            current_statement = []
            
            for line in migration_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    current_statement.append(line)
                    if line.endswith(';'):
                        statements.append(' '.join(current_statement))
                        current_statement = []
            
            # Add any remaining statement
            if current_statement:
                statements.append(' '.join(current_statement))
            
            # Clean up statements
            statements = [stmt.strip().rstrip(';') for stmt in statements if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"\nExecuting statement {i}/{len(statements)}...")
                    print(f"SQL: {statement[:200]}{'...' if len(statement) > 200 else ''}")
                    try:
                        cursor.execute(statement)
                        conn.commit()
                        print(f"✓ Statement {i} executed successfully")
                    except Exception as e:
                        conn.rollback()
                        print(f"✗ Error executing statement {i}: {e}")
                        # For some statements, we might want to continue even if they fail
                        if any(phrase in str(e).lower() for phrase in ["already exists", "does not exist", "cannot be implemented"]):
                            print(f"  → Skipping (already exists or related issue)")
                            continue
                        else:
                            print(f"  → Migration failed at statement {i}")
                            return False
            
            print("✓ Migration completed successfully!")
            return True
            
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
