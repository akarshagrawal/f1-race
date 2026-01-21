"""
Simple test script to verify database functionality.

This script tests database initialization and basic operations.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import init_database, get_session, check_session_exists
from src.database.models import Session, Driver

def test_database_init():
    """Test database initialization"""
    print("Testing database initialization...")
    
    try:
        engine = init_database()
        print("✓ Database initialized successfully")
        print(f"  Database file: {os.path.abspath('f1_telemetry.db')}")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


def test_session_operations():
    """Test basic session operations"""
    print("\nTesting session operations...")
    
    try:
        session = get_session()
        
        # Check if any sessions exist
        count = session.query(Session).count()
        print(f"✓ Database query successful")
        print(f"  Sessions in database: {count}")
        
        session.close()
        return True
    except Exception as e:
        print(f"✗ Session operations failed: {e}")
        return False


def test_check_session_exists():
    """Test check_session_exists function"""
    print("\nTesting check_session_exists function...")
    
    try:
        # Test with a session that likely doesn't exist
        exists = check_session_exists(2024, 1, 'R')
        print(f"✓ check_session_exists works")
        print(f"  Session 2024 Round 1 Race exists: {exists}")
        return True
    except Exception as e:
        print(f"✗ check_session_exists failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("F1 Telemetry Database Test Suite")
    print("=" * 60)
    
    tests = [
        test_database_init,
        test_session_operations,
        test_check_session_exists
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ All tests passed! Database is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
