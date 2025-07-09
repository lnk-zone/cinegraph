#!/usr/bin/env python3
"""
Test script to verify Supabase auth configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_auth_config():
    print("🔍 Testing Supabase Auth Configuration")
    print("=" * 50)
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'✅ Set' if supabase_service_role_key else '❌ Missing'}")
    print(f"SUPABASE_ANON_KEY: {'✅ Set' if supabase_anon_key else '❌ Missing'}")
    
    # Test import of auth module
    try:
        # Test the imports individually
        from fastapi import Depends
        print("✅ Depends import available")
        
        # Test the basic auth imports without initializing the client
        import app.auth
        print("✅ Auth module imports successfully")
        
        # Test that the environment variables are correctly loaded
        print(f"✅ Auth module loaded SUPABASE_URL: {app.auth.SUPABASE_URL is not None}")
        print(f"✅ Auth module loaded SUPABASE_SERVICE_ROLE_KEY: {app.auth.SUPABASE_SERVICE_ROLE_KEY is not None}")
        
    except Exception as e:
        print(f"❌ Error importing auth module: {e}")
        return False
    
    # Test updated files
    print("\n🔧 Testing Updated Files")
    print("-" * 30)
    
    # Test agent factory
    try:
        import agents.agent_factory
        print("✅ Agent factory imports successfully")
        
        # Test that it would load the correct env var
        import inspect
        source = inspect.getsource(agents.agent_factory.create_cinegraph_agent)
        if "SUPABASE_SERVICE_ROLE_KEY" in source:
            print("✅ Agent factory uses SUPABASE_SERVICE_ROLE_KEY")
        else:
            print("❌ Agent factory does not use SUPABASE_SERVICE_ROLE_KEY")
        
    except Exception as e:
        print(f"❌ Error with agent factory: {e}")
    
    print("\n🎉 Configuration test completed!")
    return True

if __name__ == "__main__":
    test_auth_config()
