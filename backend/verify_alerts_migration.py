#!/usr/bin/env python3
"""
Verify alerts table migration
=============================

This script verifies that the migration was applied correctly by checking:
1. The user_id column exists in the alerts table
2. Row Level Security is enabled
3. The RLS policy exists
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
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
            if not db_password:
                raise ValueError("SUPABASE_DB_PASSWORD must be set for Supabase connection")
            
            db_url = f"postgresql://postgres:{db_password}@{host}:5432/postgres"
        else:
            raise ValueError("Unsupported database URL format")
    
    return psycopg2.connect(db_url)

def verify_migration():
    """Verify the migration was applied correctly"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            print("Verifying alerts table migration...")
            
            # Check if user_id column exists
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'alerts' AND column_name = 'user_id'
            """)
            
            user_id_column = cursor.fetchone()
            if user_id_column:
                print(f"✓ user_id column exists: {user_id_column[1]} (nullable: {user_id_column[2]})")
            else:
                print("✗ user_id column not found")
                return False
            
            # Check if foreign key constraint exists
            cursor.execute("""
                SELECT tc.constraint_name, tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'alerts' AND kcu.column_name = 'user_id'
            """)
            
            fk_constraint = cursor.fetchone()
            if fk_constraint:
                print(f"✓ Foreign key constraint exists: references {fk_constraint[3]}.{fk_constraint[4]}")
            else:
                print("✗ Foreign key constraint not found")
            
            # Check if RLS is enabled
            cursor.execute("""
                SELECT relname, relrowsecurity
                FROM pg_class
                WHERE relname = 'alerts'
            """)
            
            rls_status = cursor.fetchone()
            if rls_status and rls_status[1]:
                print("✓ Row Level Security is enabled")
            else:
                print("✗ Row Level Security is not enabled")
                return False
            
            # Check if RLS policy exists
            cursor.execute("""
                SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
                FROM pg_policies
                WHERE tablename = 'alerts' AND policyname = 'Alert owners'
            """)
            
            policy = cursor.fetchone()
            if policy:
                print(f"✓ RLS policy 'Alert owners' exists")
                print(f"  Policy: {policy[6]}")
            else:
                print("✗ RLS policy 'Alert owners' not found")
                return False
            
            # Check if index exists
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'alerts' AND indexname = 'idx_alerts_user_id'
            """)
            
            index = cursor.fetchone()
            if index:
                print("✓ Index idx_alerts_user_id exists")
            else:
                print("✓ Index idx_alerts_user_id not found (this is optional)")
            
            print("\n✓ Migration verification completed successfully!")
            return True
            
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_migration()
    sys.exit(0 if success else 1)
