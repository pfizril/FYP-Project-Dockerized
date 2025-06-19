import requests
import time

API_BASE = "http://localhost:8000"  # Change to your API base URL if needed

# Endpoints to test (customize as needed)
ENDPOINTS = [
    ("/login", "POST"),
    ("/comments", "POST"),
    ("/api/data", "GET"),
    ("/admin", "GET"),
]

# Malicious payloads
PAYLOADS = [
    # SQL Injection
    {"type": "SQLi", "data": {"username": "admin' OR 1=1--", "password": "irrelevant"}},
    # XSS
    {"type": "XSS", "data": {"comment": "<script>alert('xss')</script>"}},
    # Path Traversal
    {"type": "PathTraversal", "data": {"file": "../../etc/passwd"}},
    # Unauthorized Access (no token)
    {"type": "Unauthorized", "data": {}},
]

def test_endpoint(endpoint, method, payload_type, data):
    url = API_BASE + endpoint
    headers = {}
    if payload_type == "Unauthorized":
        # Don't send auth headers
        pass
    else:
        headers = {"Authorization": "Bearer invalidtoken"}  # Simulate bad/expired token

    try:
        if method == "POST":
            resp = requests.post(url, json=data, headers=headers)
        else:
            resp = requests.get(url, params=data, headers=headers)
        print(f"[{payload_type}] {method} {endpoint} -> Status: {resp.status_code}")
    except Exception as e:
        print(f"[{payload_type}] {method} {endpoint} -> ERROR: {e}")

def main():
    for endpoint, method in ENDPOINTS:
        for payload in PAYLOADS:
            test_endpoint(endpoint, method, payload["type"], payload["data"])
            time.sleep(0.5)  # Space out requests for rate-limit testing

    # Rate-limit test: burst requests from same IP
    print("\n[RateLimit] Sending burst requests to /api/data ...")
    for i in range(15):
        test_endpoint("/api/data", "GET", "RateLimit", {})
        time.sleep(0.1)

if __name__ == "__main__":
    main()