#!/usr/bin/env python3
"""
Test script for Zoho synchronization functionality
"""
import requests
import json
import time
from datetime import datetime

# Base URL - update this to match your deployment
BASE_URL = "https://test-knight-50030314031.development.catalystappsail.in"

# Authentication credentials
AUTH = {
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
}

def test_endpoint(endpoint, data=None, method="POST"):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    if data is None:
        data = AUTH
    else:
        data.update(AUTH)
    
    print(f"\n{'='*60}")
    print(f"Testing: {method} {endpoint}")
    print(f"{'='*60}")
    
    try:
        if method == "POST":
            response = requests.post(url, json=data)
        else:
            response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("Zoho Synchronization Test Suite")
    print("================================\n")
    
    # Test 1: Check Zoho connection status
    print("1. Testing Zoho Connection Status")
    status = test_endpoint("/zoho/status")
    
    # Test 2: Check scheduler status
    print("\n2. Testing Scheduler Status")
    scheduler_status = test_endpoint("/zoho/scheduler/status")
    
    # Test 3: Test queue lookup with a sample queue_id
    print("\n3. Testing Queue Lookup")
    test_queue_data = {
        "queue_id": "ab2661ac-2f7e-414b-a860-dba5c85763be"  # Replace with actual queue_id
    }
    queue_result = test_endpoint("/zoho/test-queue-lookup", test_queue_data)
    
    # Test 4: Start scheduler if not running
    if scheduler_status and not scheduler_status.get("is_running", False):
        print("\n4. Starting Scheduler")
        test_endpoint("/zoho/scheduler/start")
        
        # Wait and check status again
        time.sleep(2)
        print("\n5. Rechecking Scheduler Status")
        test_endpoint("/zoho/scheduler/status")
    
    # Test 5: Trigger manual sync
    print("\n6. Triggering Manual Sync")
    sync_result = test_endpoint("/zoho/sync")
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)
    
    if status:
        print(f"✓ Zoho API Connection: {'Success' if status.get('status') == 'success' else 'Failed'}")
        if status.get('pending_records_count') is not None:
            print(f"  - Pending Records: {status.get('pending_records_count')}")
    
    if scheduler_status:
        print(f"✓ Scheduler Status: {'Running' if scheduler_status.get('is_running') else 'Stopped'}")
        if scheduler_status.get('last_sync_time'):
            print(f"  - Last Sync: {scheduler_status.get('last_sync_time')}")
        if scheduler_status.get('stats'):
            stats = scheduler_status.get('stats')
            print(f"  - Total Synced: {stats.get('total_synced', 0)}")
            print(f"  - Total Failed: {stats.get('total_failed', 0)}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()