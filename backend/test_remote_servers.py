import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Change this if your server runs on a different port
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmaXpyaWwyMDAxIiwiaWQiOjMsInJvbGUiOiJBZG1pbiIsImV4cCI6MTc1MDE0OTM0N30.GmDYS9IKoernnymJvcXptfe6QsIKJ-ijLBsMo05nQqE"

def get_csrf_token() -> str:
    """Get a new CSRF token from the server."""
    try:
        response = requests.get(
            f"{BASE_URL}/csrf/csrf-token",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        if response.status_code == 200:
            return response.json()["csrf_token"]
        else:
            raise Exception(f"Failed to get CSRF token: {response.text}")
    except Exception as e:
        print(f"Error getting CSRF token: {str(e)}")
        raise

def get_headers(csrf_token: str = None) -> Dict[str, str]:
    """Get headers with authentication token and CSRF token if provided."""
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    return headers

def test_create_remote_server() -> None:
    """Test creating a new remote server."""
    endpoint = f"{BASE_URL}/remote-servers/"
    
    # Get CSRF token first
    try:
        csrf_token = get_csrf_token()
        print(f"Got CSRF token: {csrf_token}")
    except Exception as e:
        print(f"Failed to get CSRF token: {str(e)}")
        return
    
    # Test data
    server_data = {
        "name": "Test Server",
        "base_url": "https://api.example.com",
        "description": "A test remote server",
        "api_key": "test_api_key_123",
        "health_check_url": "https://api.example.com/health"
    }
    
    try:
        response = requests.post(
            endpoint,
            headers=get_headers(csrf_token),
            json=server_data
        )
        
        print("\n=== Create Remote Server Test ===")
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✅ Test passed: Server created successfully")
        else:
            print("\n❌ Test failed: Server creation failed")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")

def test_list_remote_servers() -> None:
    """Test listing all remote servers."""
    endpoint = f"{BASE_URL}/remote-servers/"
    
    try:
        response = requests.get(
            endpoint,
            headers=get_headers()  # No CSRF token needed for GET requests
        )
        
        print("\n=== List Remote Servers Test ===")
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✅ Test passed: Servers listed successfully")
        else:
            print("\n❌ Test failed: Failed to list servers")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    print("Starting Remote Server API Tests...")
    test_create_remote_server()
    test_list_remote_servers() 