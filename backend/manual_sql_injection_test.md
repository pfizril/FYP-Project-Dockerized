# Manual SQL Injection Test Guide

## Overview
This guide shows how to test SQL injection detection on **ANY API endpoint** in your system, not just the test endpoint.

## How SQL Injection Detection Works

The security middleware (`SecurityMiddleware`) is applied to **ALL API endpoints** and detects SQL injection in:

1. **Query Parameters** (GET requests)
2. **JSON Body** (POST/PUT/PATCH requests)
3. **Form Data** (POST requests)

## Test Cases

### 1. Test GET Endpoint with Query Parameters

**Endpoint:** `GET /admin-dashboard`
**URL:** `http://localhost:8000/admin-dashboard?user=admin'--&id=1' OR '1'='1`

**Headers:**
```
X-API-Key: your-api-key
Authorization: Bearer your-jwt-token
```

**Expected Result:** 
- Status: `403 Forbidden`
- Message: "Threat detected in request"

### 2. Test POST Endpoint with JSON Body

**Endpoint:** `POST /auth/login`
**URL:** `http://localhost:8000/auth/login`

**Headers:**
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "username": "admin'--",
  "password": "' OR '1'='1",
  "email": "'; DROP TABLE users; --"
}
```

**Expected Result:**
- Status: `403 Forbidden`
- Message: "Threat detected in request"

### 3. Test POST Endpoint with Form Data

**Endpoint:** `POST /auth/register`
**URL:** `http://localhost:8000/auth/register`

**Headers:**
```
X-API-Key: your-api-key
Content-Type: application/x-www-form-urlencoded
```

**Body (Form Data):**
```
username=admin'--
password=' OR '1'='1
email='; INSERT INTO users VALUES ('hacker', 'password'); --
```

**Expected Result:**
- Status: `403 Forbidden`
- Message: "Threat detected in request"

### 4. Test Analytics Endpoint

**Endpoint:** `GET /analytics/traffic`
**URL:** `http://localhost:8000/analytics/traffic?filter=1' UNION SELECT * FROM users --&sort=id' OR '1'='1`

**Headers:**
```
X-API-Key: your-api-key
Authorization: Bearer your-jwt-token
```

**Expected Result:**
- Status: `403 Forbidden`
- Message: "Threat detected in request"

## SQL Injection Payloads to Test

### Basic SQL Injection
```
' OR '1'='1
' OR 1=1--
admin'--
'; DROP TABLE users; --
```

### Union-Based SQL Injection
```
' UNION SELECT * FROM users --
' UNION SELECT username,password FROM users --
' UNION SELECT NULL,NULL,NULL--
```

### Time-Based SQL Injection
```
'; WAITFOR DELAY '00:00:05'--
'; SLEEP(5)--
'; BENCHMARK(5000000,MD5(1))--
```

### Boolean-Based SQL Injection
```
' AND '1'='1
' AND 1=1--
' AND (SELECT COUNT(*) FROM users)>0--
```

## Verification Steps

1. **Check Dashboard:** After sending malicious requests, check the Security Dashboard
   - Go to `/security` in your frontend
   - Check "Threat Detection" tab
   - Look for SQL injection entries

2. **Check Database:** Verify attacks are logged
   - Check `threat_logs` table for SQL injection entries
   - Check `attacked_endpoints` table for detailed attack info

3. **Check Logs:** Monitor server logs
   - Look for "Threat detected" messages
   - Check for "SQL injection detected" entries

## Expected Behavior

✅ **Requests with SQL injection should be:**
- Blocked with 403 status
- Logged in threat_logs table
- Logged in attacked_endpoints table
- Visible in Security Dashboard

❌ **Requests without SQL injection should:**
- Pass through normally (200/201 status)
- Not be logged as threats

## Troubleshooting

If SQL injection is not being detected:

1. **Check Middleware Order:** Ensure `SecurityMiddleware` is added before other middleware
2. **Check Endpoint Exclusions:** Verify the endpoint isn't in exclusion list
3. **Check Authentication:** Ensure you have proper API key and JWT token
4. **Check Logs:** Look for middleware errors in server logs

## Test Script

You can also run the automated test script:
```bash
python test_sql_injection_any_endpoint.py
```

This will test multiple endpoints automatically and provide a summary of results. 