import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from time import time
from typing import Annotated, Dict, List
from fastapi.security import APIKeyHeader
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import requests
from urllib.parse import parse_qs, urlparse
import re
from auth import get_current_user
from models import APIEndpoint, RateLimit, TrafficLog, ThreatLog, AttackedEndpoint, APIRequest, ActivityLog
from database import session
import os
from fastapi.responses import Response
import csv
from io import StringIO
from fastapi import status

# Configure logging
logging.basicConfig(
    filename="security_logs.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter(
    prefix='/security',
    tags=['Threat Detection & Logging']
)

def get_db():
    db = session()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


# Centralized security configuration
SECURITY_CONFIG = {
    'RATE_LIMIT': {
        'requests_per_minute': 100, #for testing use 10 req per minute
        'block_duration': 15 * 60  # 15 minutes
    },
    'THREAT_DETECTION': {
        'failed_login_threshold': 5,
        'failed_login_window': 5 * 60,  # 5 minutes
        'abnormal_traffic_threshold': 50,
        'abnormal_traffic_window': 10  # 10 seconds
    }
}
class EnhancedThreatDetection:
    def __init__(self, db_session):
        self.db = db_session
        # Cache suspicious IPs to reduce database queries
        self.suspicious_ips = set()
        self.last_cache_update = datetime.now()
        self.cache_ttl = timedelta(minutes=5)
        
        # Known patterns for various attacks - made less aggressive
        self.xss_patterns = [
            r'<script\b[^>]*>.*?</script>',  # Basic script tag
            r'javascript:.*\(.*\)',          # JavaScript protocol
            r'onerror\s*=.*alert',           # Only alert in onerror
            r'onload\s*=.*alert',            # Only alert in onload
            r'eval\s*\(.*alert',             # Only alert in eval
            r'document\.cookie.*alert',      # Only alert with cookie
            r'document\.location.*alert',    # Only alert with location
            r'<img\s+src\s*=\s*["\']?javascript:',  # Image with javascript src
            r'<iframe\s+src\s*=\s*["\']?javascript:',  # Iframe with javascript src
            r'<svg\s+onload\s*=',            # SVG onload
            r'<body\s+onload\s*=',           # Body onload
            r'<input\s+onfocus\s*=',         # Input onfocus
            r'<form\s+oninput\s*=',          # Form oninput
        ]
        
        self.sqli_patterns = [
            r'\bUNION\s+ALL\s+SELECT\b',     # UNION ALL SELECT
            r'\bUNION\s+SELECT\b',           # UNION SELECT
            r'\bOR\s+1\s*=\s*1\b',           # OR 1=1
            r'\bAND\s+1\s*=\s*1\b',          # AND 1=1
            r'\bOR\s+\'1\'\s*=\s*\'1\'\b',   # OR '1'='1'
            r'\bAND\s+\'1\'\s*=\s*\'1\'\b',  # AND '1'='1'
            r'--\s*$',                       # Comment at end
            r'#\s*$',                        # Hash comment at end
            r'\/\*.*\*\/',                   # C-style comment
            r'@@version',                    # Version check
            r'SLEEP\s*\(\d+\)',              # SLEEP function
            r'BENCHMARK\s*\(\d+,.*\)',       # BENCHMARK function
            r'WAITFOR\s+DELAY',              # WAITFOR DELAY
            r'DROP\s+TABLE',                 # DROP TABLE
            r'DELETE\s+FROM',                # DELETE FROM
            r'INSERT\s+INTO',                # INSERT INTO
            r'UPDATE\s+SET',                 # UPDATE SET
            r'ALTER\s+TABLE',                # ALTER TABLE
            r'CREATE\s+TABLE',               # CREATE TABLE
            r'EXEC\s*\(',                    # EXEC function
            r'xp_cmdshell',                  # xp_cmdshell
            # Additional patterns for better detection
            r';\s*DROP\s+TABLE',             # ; DROP TABLE
            r';\s*DELETE\s+FROM',            # ; DELETE FROM
            r';\s*INSERT\s+INTO',            # ; INSERT INTO
            r';\s*UPDATE\s+',                # ; UPDATE
            r';\s*ALTER\s+TABLE',            # ; ALTER TABLE
            r';\s*CREATE\s+TABLE',           # ; CREATE TABLE
            r';\s*EXEC\s*\(',                # ; EXEC(
            r';\s*WAITFOR\s+DELAY',          # ; WAITFOR DELAY
            r';\s*SLEEP\s*\(',               # ; SLEEP(
            r';\s*BENCHMARK\s*\(',           # ; BENCHMARK(
            r';\s*UNION\s+SELECT',           # ; UNION SELECT
            r';\s*UNION\s+ALL\s+SELECT',     # ; UNION ALL SELECT
            r';\s*OR\s+1\s*=\s*1',           # ; OR 1=1
            r';\s*AND\s+1\s*=\s*1',          # ; AND 1=1
            r';\s*OR\s+\'1\'\s*=\s*\'1\'',   # ; OR '1'='1'
            r';\s*AND\s+\'1\'\s*=\s*\'1\'',  # ; AND '1'='1'
            r';\s*--',                       # ; --
            r';\s*#',                        # ; #
            r';\s*\/\*',                     # ; /*
            r';\s*\*\/',                     # ; */
            # Standalone SQL keywords that are suspicious
            r'\bDROP\b',                     # DROP
            r'\bDELETE\b',                   # DELETE
            r'\bINSERT\b',                   # INSERT
            r'\bUPDATE\b',                   # UPDATE
            r'\bALTER\b',                    # ALTER
            r'\bCREATE\b',                   # CREATE
            r'\bEXEC\b',                     # EXEC
            r'\bUNION\b',                    # UNION
            r'\bSELECT\b',                   # SELECT
            r'\bFROM\b',                     # FROM
            r'\bWHERE\b',                    # WHERE
            r'\bAND\b',                      # AND
            r'\bOR\b',                       # OR
            r'\bINTO\b',                     # INTO
            r'\bTABLE\b',                    # TABLE
            r'\bDATABASE\b',                 # DATABASE
            r'\bSCHEMA\b',                   # SCHEMA
            r'\bUSER\b',                     # USER
            r'\bPASSWORD\b',                 # PASSWORD
            r'\bADMIN\b',                    # ADMIN
            r'\bROOT\b',                     # ROOT
            r'\bSYSTEM\b',                   # SYSTEM
            r'\bMASTER\b',                   # MASTER
            r'\bINFORMATION_SCHEMA\b',       # INFORMATION_SCHEMA
            r'\bSYS\b',                      # SYS
            r'\bDUAL\b',                     # DUAL
            r'\bNULL\b',                     # NULL
            r'\bTRUE\b',                     # TRUE
            r'\bFALSE\b',                    # FALSE
            r'\b1\s*=\s*1\b',               # 1=1
            r'\b\'1\'\s*=\s*\'1\'\b',       # '1'='1'
            r'\b\'x\'\s*=\s*\'x\'\b',       # 'x'='x'
            r'\b\'a\'\s*=\s*\'a\'\b',       # 'a'='a'
            r'\b\'admin\'\s*--',            # 'admin'--
            r'\b\'root\'\s*--',             # 'root'--
            r'\b\'test\'\s*--',             # 'test'--
            r'\b\'user\'\s*--',             # 'user'--
            r'\b\'pass\'\s*--',             # 'pass'--
            r'\b\'password\'\s*--',         # 'password'--
            r'\b\'username\'\s*--',         # 'username'--
            r'\b\'email\'\s*--',            # 'email'--
            r'\b\'login\'\s*--',            # 'login'--
            r'\b\'auth\'\s*--',             # 'auth'--
            r'\b\'admin\'\s*#',             # 'admin'#
            r'\b\'root\'\s*#',              # 'root'#
            r'\b\'test\'\s*#',              # 'test'#
            r'\b\'user\'\s*#',              # 'user'#
            r'\b\'pass\'\s*#',              # 'pass'#
            r'\b\'password\'\s*#',          # 'password'#
            r'\b\'username\'\s*#',          # 'username'#
            r'\b\'email\'\s*#',             # 'email'#
            r'\b\'login\'\s*#',             # 'login'#
            r'\b\'auth\'\s*#',              # 'auth'#
        ]
        
        self.path_traversal_patterns = [
            r'\.\.\/\.\.\/',                  # Multiple directory traversal
            r'\.\.\\\.\.\\',                  # Multiple directory traversal
            r'%2e%2e%2f%2e%2e%2f',           # Multiple encoded traversal
            r'%252e%252e%252f%252e%252e%252f', # Multiple double-encoded traversal
            r'/etc/passwd\b',                 # Must be word boundary
            r'C:\\Windows\\System32\\cmd\.exe', # Specific dangerous path
            r'WEB-INF/web\.xml\b',           # Must be word boundary
        ]
        
        # Threat score weights - adjusted to be less aggressive
        self.weights = {
            'failed_login': 5,               # Reduced from 10
            'suspicious_traffic': 1,         # Reduced from 2
            'vulnerability': 10,             # Reduced from 20
            'xss_attempt': 8,                # Reduced from 15
            'sqli_attempt': 15,              # Reduced from 25
            'path_traversal': 10,            # Reduced from 20
            'rate_limit': 3                  # Reduced from 5
        }
    
    def _is_suspicious_ip(self, ip):
        """Check if an IP is in the suspicious IPs cache"""
        # Update cache if needed
        if datetime.now() - self.last_cache_update > self.cache_ttl:
            self._update_suspicious_ips_cache()
        
        return ip in self.suspicious_ips

    def _get_recent_threats(self, client_ip: str, time_window: int = 300) -> int:
        """Get the number of recent threats from an IP within the time window (in seconds)"""
        try:
            recent_threats = self.db.query(ThreatLog).filter(
                ThreatLog.client_ip == client_ip,
                ThreatLog.created_at >= datetime.now() - timedelta(seconds=time_window)
            ).count()
            return recent_threats
        except Exception as e:
            logging.error(f"Error getting recent threats: {e}")
            return 0

    def _update_suspicious_ips_cache(self):
        """Update the cache of suspicious IPs"""
        try:
            timeframe = datetime.now() - timedelta(hours=24)
            threat_logs = self.db.query(ThreatLog).filter(
                ThreatLog.created_at >= timeframe
            ).limit(1000).all()
            
            # Count threats by IP
            ip_threat_counts = defaultdict(int)
            for log in threat_logs:
                ip_threat_counts[log.client_ip] += 1
            
            # Mark IPs with multiple threat logs as suspicious
            self.suspicious_ips = {ip for ip, count in ip_threat_counts.items() if count >= 3}
            self.last_cache_update = datetime.now()
        except Exception as e:
            logging.error(f"Error updating suspicious IPs cache: {e}")

    def analyze_request(self, request):
        """Comprehensive request analysis for threats"""
        client_ip = request.headers.get("X-Forwarded-For") or request.client.host
        path = request.url.path
        method = request.method
        headers = dict(request.headers)
        
        threats = []
        
        # Check IP reputation - only if multiple threats
        if self._is_suspicious_ip(client_ip) and len(self._get_recent_threats(client_ip)) > 2:
            threats.append(('suspicious_ip', 'Multiple threats detected from this IP'))
        
        # Check for suspicious path patterns - only if not in allowed paths
        if not any(allowed in path for allowed in ['/api/', '/auth/', '/health']):
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    threats.append(('path_traversal', f'Path traversal attempt detected: {pattern}'))
                    break
        
        # Check headers for XSS attempts - only in user-provided headers
        user_headers = ['x-forwarded-for', 'user-agent', 'referer']
        for header, value in headers.items():
            if header.lower() in user_headers:
                for pattern in self.xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        threats.append(('xss_attempt', f'XSS attempt detected in header: {header}'))
                        break
        
        # Check query parameters for SQL injection
        for param_name, param_value in request.query_params.items():
            if isinstance(param_value, str):
                for pattern in self.sqli_patterns:
                    if re.search(pattern, param_value, re.IGNORECASE):
                        threats.append(('sqli_attempt', f'SQL injection detected in query parameter: {param_name}'))
                        break
        
        # Check if the request has already triggered rate limits - increased threshold
        if self._check_rate_limit(client_ip) and self._get_recent_threats(client_ip) > 5:
            threats.append(('rate_limit', 'Rate limit threshold exceeded'))
        
        # Log threats if found
        for threat_type, description in threats:
            self._log_threat(client_ip, threat_type, description)
        
        return threats
    
    async def analyze_request_body(self, request):
        """Analyze request body for threats"""
        threats = []
        client_ip = request.client.host
        content_type = request.headers.get("content-type", "").lower()
        
        logging.info(f"Analyzing request body from {client_ip}, content-type: {content_type}")
        
        try:
            # Try to get JSON body first
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    logging.info(f"Analyzing JSON body: {str(body)[:100]}...")
                    json_threats = self._scan_json_for_threats(body)
                    threats.extend(json_threats)
                    
                    for threat_type, description in json_threats:
                        self._log_threat(client_ip, threat_type, description)
                        
                except Exception as json_error:
                    logging.warning(f"Error parsing JSON body: {json_error}")
                    
            # Try form data for any POST request
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type or request.method == "POST":
                try:
                    form_data = await request.form()
                    form_dict = dict(form_data)
                    logging.info(f"Analyzing form data: {str(form_dict)[:100]}...")
                    
                    # Check form data for SQL injection patterns
                    for field_name, field_value in form_dict.items():
                        if isinstance(field_value, str):
                            logging.info(f"Checking field '{field_name}' with value: {field_value[:50]}...")
                            for pattern in self.sqli_patterns:
                                if re.search(pattern, field_value, re.IGNORECASE):
                                    threat_desc = f'SQL injection pattern detected in form field: {field_name}'
                                    threats.append(('sqli_attempt', threat_desc))
                                    self._log_threat(client_ip, 'sqli_attempt', threat_desc)
                                    logging.warning(f"SQL injection detected in field '{field_name}': {field_value}")
                                    break
                            
                            # Also check for XSS patterns
                            for pattern in self.xss_patterns:
                                if re.search(pattern, field_value, re.IGNORECASE):
                                    threat_desc = f'XSS pattern detected in form field: {field_name}'
                                    threats.append(('xss_attempt', threat_desc))
                                    self._log_threat(client_ip, 'xss_attempt', threat_desc)
                                    logging.warning(f"XSS detected in field '{field_name}': {field_value}")
                                    break
                                    
                except Exception as form_error:
                    logging.warning(f"Error parsing form data: {form_error}")
                    
            # Try raw body for other content types
            if not threats and content_type and "application/json" not in content_type and "application/x-www-form-urlencoded" not in content_type and "multipart/form-data" not in content_type:
                try:
                    body_bytes = await request.body()
                    body_text = body_bytes.decode('utf-8', errors='ignore')
                    logging.info(f"Analyzing raw body: {body_text[:100]}...")
                    
                    # Check raw body for SQL injection patterns
                    for pattern in self.sqli_patterns:
                        if re.search(pattern, body_text, re.IGNORECASE):
                            threat_desc = f'SQL injection pattern detected in request body'
                            threats.append(('sqli_attempt', threat_desc))
                            self._log_threat(client_ip, 'sqli_attempt', threat_desc)
                            logging.warning(f"SQL injection detected in raw body: {body_text[:100]}")
                            break
                            
                except Exception as raw_error:
                    logging.warning(f"Error parsing raw body: {raw_error}")
                    
        except Exception as e:
            logging.error(f"Error in analyze_request_body: {e}")
        
        logging.info(f"Found {len(threats)} threats in request body")
        return threats
    
    def _scan_json_for_threats(self, data, path=""):
        """Recursively scan JSON data for threat patterns"""
        threats = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, str):
                    # Check for SQL injection patterns
                    for pattern in self.sqli_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            threats.append(('sqli_attempt', f'SQL injection pattern detected in {current_path}'))
                    
                    # Check for XSS patterns
                    for pattern in self.xss_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            threats.append(('xss_attempt', f'XSS pattern detected in {current_path}'))
                
                # Recurse into nested structures
                if isinstance(value, (dict, list)):
                    threats.extend(self._scan_json_for_threats(value, current_path))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    threats.extend(self._scan_json_for_threats(item, current_path))
                elif isinstance(item, str):
                    # Apply the same pattern checks as above
                    for pattern in self.sqli_patterns:
                        if re.search(pattern, item, re.IGNORECASE):
                            threats.append(('sqli_attempt', f'SQL injection pattern detected in {current_path}'))
                    
                    for pattern in self.xss_patterns:
                        if re.search(pattern, item, re.IGNORECASE):
                            threats.append(('xss_attempt', f'XSS pattern detected in {current_path}'))
        
        return threats
    
    def _check_rate_limit(self, client_ip):
        """Check if IP has hit rate limits"""
        from models import RateLimit
        
        rate_limit = self.db.query(RateLimit).filter_by(client_id=client_ip).first()
        if rate_limit and rate_limit.request_count >= 100:  # Using your configured threshold
            return True
        return False
    
    def _log_threat(self, client_ip, threat_type, description):
        """Log detected threat to database"""
        
        
        threat_log = ThreatLog(
            client_ip=client_ip,
            activity=threat_type,
            detail=description
        )
        self.db.add(threat_log)
        self.db.commit()
    
    def _log_attacked_endpoint(self, client_ip, endpoint, method, attack_type, description):
        """Log detailed attack information to attacked_endpoints table"""
        try:
            # Check if this attack already exists for this endpoint/IP combination
            existing_attack = self.db.query(AttackedEndpoint).filter(
                AttackedEndpoint.endpoint == endpoint,
                AttackedEndpoint.client_ip == client_ip,
                AttackedEndpoint.attack_type == attack_type
            ).first()
            
            if existing_attack:
                # Update existing record
                existing_attack.attack_count += 1
                existing_attack.last_seen = datetime.now()
                existing_attack.updated_at = datetime.now()
            else:
                # Create new record
                recommended_fix = self._get_recommended_fix(attack_type)
                severity = self._get_attack_severity(attack_type)
                
                attacked_endpoint = AttackedEndpoint(
                    endpoint=endpoint,
                    method=method,
                    attack_type=attack_type,
                    client_ip=client_ip,
                    recommended_fix=recommended_fix,
                    severity=severity
                )
                self.db.add(attacked_endpoint)
            
            self.db.commit()
        except Exception as e:
            logging.error(f"Error logging attacked endpoint: {e}")
            self.db.rollback()
    
    def _get_recommended_fix(self, attack_type):
        """Get recommended fix based on attack type"""
        fixes = {
            'sql_injection': 'Use parameterized queries or ORM to prevent SQL injection. Validate and sanitize all user inputs.',
            'xss_attempt': 'Implement Content Security Policy (CSP), validate and sanitize user inputs, use proper output encoding.',
            'path_traversal': 'Validate file paths, use whitelist approach for allowed directories, implement proper access controls.',
            'unauthorized_access': 'Implement proper authentication and authorization, use JWT tokens, validate user permissions.',
            'rate_limit_violations': 'Implement rate limiting, use exponential backoff, monitor and block abusive IPs.',
            'suspicious_ip': 'Monitor IP reputation, implement IP-based blocking, use threat intelligence feeds.'
        }
        return fixes.get(attack_type, 'Implement general security best practices and input validation.')
    
    def _get_attack_severity(self, attack_type):
        """Get severity level based on attack type"""
        severity_map = {
            'sql_injection': 'high',
            'xss_attempt': 'medium',
            'path_traversal': 'high',
            'unauthorized_access': 'medium',
            'rate_limit_violations': 'low',
            'suspicious_ip': 'medium'
        }
        return severity_map.get(attack_type, 'medium')
    
    def calculate_threat_score(self, client_ip):
        """Calculate comprehensive threat score with weighted factors"""
        
        now = datetime.now()
        threat_score = 0
        
        # Get all threat logs for this IP in the past 24 hours
        threat_logs = self.db.query(ThreatLog).filter(
            ThreatLog.client_ip == client_ip,
            ThreatLog.created_at >= now - timedelta(hours=24)
        ).all()
        
        # Count by threat type
        threat_counts = defaultdict(int)
        for log in threat_logs:
            threat_counts[log.activity] += 1
        
        # Apply weights based on threat type
        for threat_type, count in threat_counts.items():
            if threat_type == "Failed Login":
                threat_score += count * self.weights['failed_login']
            elif threat_type == "sqli_attempt":
                threat_score += count * self.weights['sqli_attempt']
            elif threat_type == "xss_attempt":
                threat_score += count * self.weights['xss_attempt']
            elif threat_type == "path_traversal":
                threat_score += count * self.weights['path_traversal']
            elif threat_type == "rate_limit":
                threat_score += count * self.weights['rate_limit']
            else:
                # Default weight for other threats
                threat_score += count * 5
        
        # Traffic volume analysis
        traffic_count = self.db.query(TrafficLog).filter(
            TrafficLog.client_ip == client_ip,
            TrafficLog.timestamp >= now - timedelta(hours=1)
        ).count()
        
        # If traffic is abnormally high, add to threat score
        if traffic_count > 300:  # Threshold for 1 hour
            threat_score += (traffic_count // 100) * self.weights['suspicious_traffic']
        
        return min(threat_score, 100)  # Cap at 100
    
class SecurityManager:
    @staticmethod
    def log_security_event(db: Session, event_type: str, details: Dict):
        """
        Centralized method for logging security events
        """
        try:
            threat_log = ThreatLog(
                client_ip=details.get('client_ip', 'Unknown'),
                activity=event_type,
                detail=str(details)
            )
            db.add(threat_log)
            db.commit()
            logging.info(f"Security Event Logged: {event_type} - {details}")
        except Exception as e:
            logging.error(f"Failed to log security event: {e}")


def validate_and_normalize_url(url: str) -> str:
    """
    Validate and normalize URL
    """
    if not url:
        return ""
    
    host = '127.0.0.1:8000' #TODO: change to the actual host after depolymenst 
    parsed_url = urlparse(url)
    
    if not parsed_url.scheme:
        if url.startswith('localhost') or url.startswith('127.0.0.1'):
            url = f"http://localhost:8000{url}"#TODO: change to the actual host after depolymenst 
        else:
            url = f"https://{host}{url}"#TODO: change to the actual host after depolymenst 

    return url

def detect_sql_injection(input_string: str) -> bool:
    """
    Advanced SQL injection detection
    """
    sql_keywords = [
        "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", 
        "UNION", "ALTER", "CREATE", "TABLE", "DATABASE"
    ]
    sql_patterns = [
        r'\b(OR|AND)\s+1\s*=\s*1',  # Classic injection
        r'--\s*',  # Comment injection
        r"'\s*OR\s*'1'='1"  # Another classic pattern
    ]

    # Check for SQL keywords
    if any(keyword.lower() in input_string.lower() for keyword in sql_keywords):
        return True

    # Check regex patterns
    if any(re.search(pattern, input_string, re.IGNORECASE) for pattern in sql_patterns):
        return True

    return False

@router.get("/vulnerability-scan/comprehensive")
async def comprehensive_vulnerability_scan(
    api_key: Annotated[str, Depends(api_key_header)],
    db: db_dependency,
    user: user_dependency,
    page: int = 1,
    page_size: int = 10
):
    """
    Comprehensive vulnerability scanning with pagination
    """
    endpoints = db.query(APIEndpoint).all()
    scan_results = []

    for endpoint in endpoints:
        endpoint_scan = {
            "url": endpoint.url,
            "high_risk_alerts": [],
            "medium_risk_alerts": [],
            "low_risk_alerts": []
        }

        # Authentication check
        if not endpoint.requires_auth:
            endpoint_scan["high_risk_alerts"].append({
                "type": "Authentication Vulnerability",
                "description": "Endpoint lacks authentication"
            })

        # SQL Injection check
        sql_injection_result = detect_sql_injection(endpoint.url)
        if sql_injection_result:
            endpoint_scan["high_risk_alerts"].append({
                "type": "SQL Injection Risk",
                "description": "Potential SQL injection vulnerability detected"
            })

        scan_results.append(endpoint_scan)

    # Calculate pagination
    total_results = len(scan_results)
    total_pages = (total_results + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_results = scan_results[start_idx:end_idx]

    return {
        "total_scanned_endpoints": total_results,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "scan_results": paginated_results,
        "timestamp": datetime.now().isoformat()
    }

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        db: Session = next(get_db())

        # Log all requests
        traffic_log = TrafficLog(
            client_ip=client_ip,
            endpoint=request.url.path,
            request_method=request.method
        )
        db.add(traffic_log)
        db.commit()

        # Threat Detection - Analyze request for security threats
        try:
            detector = EnhancedThreatDetection(db)
            
            # Analyze request headers and path for threats
            threats = detector.analyze_request(request)

            # Analyze request body if it's a POST/PUT/PATCH request, but skip for /auth/token
            if request.method in ["POST", "PUT", "PATCH"] and not request.url.path.startswith("/auth/token"):
                try:
                    body_threats = await detector.analyze_request_body(request)
                    # Extend the existing threats list with body threats
                    threats.extend(body_threats)
                except Exception as e:
                    logging.warning(f"Error analyzing request body: {e}")

            # Log all detected threats (from headers, path, and body)
            for threat_type, description in threats:
                logging.warning(f"Threat detected from {client_ip}: {threat_type} - {description}")
                detector._log_threat(client_ip, threat_type, description) # Log to DB here
                
                # Also log to attacked endpoints table for detailed tracking
                detector._log_attacked_endpoint(
                    client_ip=client_ip,
                    endpoint=request.url.path,
                    method=request.method,
                    attack_type=threat_type,
                    description=description
                )
                
            # If any non-informational threats (not just rate_limit or suspicious_ip) were detected, block the request
            if any(t for t in threats if t[0] not in ['rate_limit', 'suspicious_ip']):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Threat detected in request")
                
        except HTTPException:
            raise # Re-raise if already an HTTPException for threat detection
        except Exception as e:
            logging.error(f"Error during threat detection in middleware: {e}")
            # Do not block the request for internal errors, just log.
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal security error")

        # CSRF Protection for non-GET requests
        if request.method not in ["GET", "HEAD", "OPTIONS"]:
            # Skip CSRF for certain endpoints that don't need it
            csrf_exempt_paths = [
                '/auth/token',  # Login endpoint
                '/csrf/csrf-token',  # CSRF token endpoint
                '/health',  # Health check
            ]
            
            if not any(path in request.url.path for path in csrf_exempt_paths):
                # Check for CSRF token in header
                header_token = request.headers.get("X-CSRF-Token")
                cookie_token = request.cookies.get("csrf_token")
                
                if not header_token and not cookie_token:
                    logging.warning(f"CSRF token missing in request from {client_ip} to {request.url.path}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token missing"
                    )
                
                # If token is in header, it must match the cookie
                if header_token and cookie_token and header_token != cookie_token:
                    logging.warning(f"CSRF token mismatch in request from {client_ip} to {request.url.path}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, 
                        detail="CSRF token validation failed"
                    )

        # Skip rate limiting for analytics and visualization endpoints
        analytics_paths = [
            '/analytics/',
            '/api/analytics/'
        ]
        
        if not any(path in request.url.path for path in analytics_paths):
            # Rate limiting
            rate_limit_record = db.query(RateLimit).filter_by(client_id=client_ip).first()
            current_time = datetime.now()

            if rate_limit_record:
                # Check if request limit exceeded
                if (current_time - rate_limit_record.last_request_time).total_seconds() > 60:
                    rate_limit_record.request_count = 1
                    rate_limit_record.last_request_time = current_time
                elif rate_limit_record.request_count >= SECURITY_CONFIG['RATE_LIMIT']['requests_per_minute']:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                else:
                    rate_limit_record.request_count += 1
                
                db.commit()

        response = await call_next(request)
        return response

@router.get("/traffic-analysis")
async def get_traffic_analysis(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency,db: db_dependency):
    """
    Generate comprehensive traffic analysis report
    """
    # Get traffic logs from the last 24 hours
    now = datetime.now()
    traffic_logs = db.query(TrafficLog).filter(
        TrafficLog.timestamp >= now - timedelta(hours=24)
    ).all()
    
    # Analyze traffic by IP
    ip_traffic = defaultdict(int)
    method_distribution = defaultdict(int)
    endpoint_hits = defaultdict(int)

    for log in traffic_logs:
        ip_traffic[log.client_ip] += 1
        method_distribution[log.request_method] += 1
        endpoint_hits[log.endpoint] += 1

    # Identify top IPs and potentially suspicious traffic
    top_ips = sorted(ip_traffic.items(), key=lambda x: x[1], reverse=True)[:10]
    suspicious_ips = [ip for ip, count in top_ips if count > SECURITY_CONFIG['THREAT_DETECTION']['abnormal_traffic_threshold']]

    return {
        "total_requests": len(traffic_logs),
        "top_ips": [{"ip": ip, "request_count": count} for ip, count in top_ips],
        "suspicious_ips": suspicious_ips,
        "method_distribution": dict(method_distribution),
        "endpoint_hits": dict(endpoint_hits),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/export-logs")
def export_security_logs(api_key: Annotated[str, Depends(api_key_header)], user: user_dependency, db: Session = Depends(get_db)):
    threat_logs = db.query(ThreatLog).all()
    traffic_logs = db.query(TrafficLog).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log Type", "Client IP", "Activity", "Detail", "Timestamp"])

    for log in threat_logs:
        writer.writerow(["ThreatLog", log.client_ip, log.activity, log.detail, log.created_at])

    for log in traffic_logs:
        detail = f"{log.request_method} {log.endpoint}"
        writer.writerow(["TrafficLog", log.client_ip, detail, "Accessed endpoint", log.timestamp])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=security_logs.csv"
    return response

@router.get("/export-threat-logs")
def export_threat_logs(api_key: Annotated[str, Depends(api_key_header)], user: user_dependency, db: Session = Depends(get_db)):
    threat_logs = db.query(ThreatLog).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Client IP", "Activity", "Detail", "Timestamp"])

    for log in threat_logs:
        writer.writerow([log.client_ip, log.activity, log.detail, log.created_at])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=threat_logs.csv"
    return response

@router.get("/export-traffic-logs")
def export_traffic_logs(api_key: Annotated[str, Depends(api_key_header)], user: user_dependency, db: Session = Depends(get_db)):
    traffic_logs = db.query(TrafficLog).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Client IP", "Endpoint", "Request Method", "Timestamp"])

    for log in traffic_logs:
        writer.writerow([log.client_ip, log.endpoint, log.request_method, log.timestamp])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=traffic_logs.csv"
    return response

@router.get("/threat-score")
def get_threat_score(api_key: Annotated[str, Depends(api_key_header)], request: Request, user: user_dependency, db: db_dependency, target_ip: str = None):
    """
    Get threat scores for all IPs with recent threats
    """
    now = datetime.now()
    timeframe = now - timedelta(hours=24)
    
    # Get all unique IPs with threat logs in the last 24 hours
    threat_logs = db.query(ThreatLog).filter(
        ThreatLog.created_at >= timeframe
    ).all()
    
    # Group threats by IP
    ip_threats = defaultdict(list)
    for log in threat_logs:
        ip_threats[log.client_ip].append(log)
    
    threat_scores = []
    detector = EnhancedThreatDetection(db)
    
    # Calculate threat scores for each IP
    for client_ip, threats in ip_threats.items():
        score = detector.calculate_threat_score(client_ip)
        
        # Get the most recent threat for this IP
        latest_threat = max(threats, key=lambda x: x.created_at)
        
        # Determine threat type based on the most recent threat
        threat_type = "normal"
        details = "No recent threats detected"
        
        if latest_threat:
            if "sql" in latest_threat.activity.lower() or "injection" in latest_threat.activity.lower():
                threat_type = "sql_injection"
            elif "xss" in latest_threat.activity.lower():
                threat_type = "xss_attempt"
            elif "path" in latest_threat.activity.lower() or "traversal" in latest_threat.activity.lower():
                threat_type = "path_traversal"
            elif "unauthorized" in latest_threat.activity.lower() or "access" in latest_threat.activity.lower():
                threat_type = "unauthorized_access"
            elif "rate" in latest_threat.activity.lower() or "limit" in latest_threat.activity.lower():
                threat_type = "rate_limit"
            
            details = latest_threat.detail
        
        threat_scores.append({
            "ip": client_ip,
            "score": score,
            "threat_type": threat_type,
            "details": details,
            "timestamp": latest_threat.created_at.isoformat() if latest_threat else datetime.now().isoformat()
        })
    
    # Sort by threat score (highest first) and limit to top 20
    threat_scores.sort(key=lambda x: x["score"], reverse=True)
    threat_scores = threat_scores[:20]
    
    return {
        "threat_scores": threat_scores
    }

def fetch_health_auth_headers():
    login_url = f"http://127.0.0.1:8000/auth/token"
    data = {
        "username": os.getenv("TEST_USERNAME"),
        "password": os.getenv("TEST_PASSWORD")
    }

    session = requests.Session()
    response = session.post(login_url, data=data)

    if response.status_code != 200:
        raise Exception("Failed to login for health check")

    token_data = response.json()
    access_token = token_data.get("access_token")
    csrf_token = token_data.get("csrf_token")

    return {
        "Authorization": f"Bearer {access_token}",
        "X-CSRF-Token": csrf_token,
        "X-API-KEY": os.getenv("HEALTH_CHECK_API_KEY", ""),
        "Cookie": f"csrf_token={csrf_token}"
    }


def check_cors_headers(url: str):
    """
    Check CORS configuration for a given URL
    """
    try:
        normalized_url = validate_and_normalize_url(url)
        headers = fetch_health_auth_headers()
        response = requests.options(normalized_url, timeout=5,headers=headers)
    
        if "Access-Control-Allow-Origin" not in headers or headers.get("Access-Control-Allow-Origin") == "*":
            return {"endpoint": normalized_url, "issue": "CORS misconfiguration"}
        return None
    except requests.RequestException as e:
        logging.warning(f"CORS check error for {url}: {str(e)}")
        return {"endpoint": url, "issue": f"CORS scan error: {str(e)}"}

async def scan_open_endpoints(db: Session):
    """
    Scan for endpoints without authentication
    """
    endpoints = db.query(APIEndpoint).all()
    vulnerabilities = []
    
    for endpoint in endpoints:
        normalized_url = validate_and_normalize_url(endpoint.url)
        
        if not endpoint.requires_auth:
            vulnerabilities.append({
                "endpoint": normalized_url, 
                "issue": "No authentication required"
            })
    
    return vulnerabilities

@router.get("/vulnerability-scan/open-endpoints")
async def scan_exposed_endpoints(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency,db: db_dependency):
    results = await scan_open_endpoints(db)
    return {"open_endpoints": results}

@router.get("/threat-indicators")
async def get_threat_indicators(api_key: Annotated[str, Depends(api_key_header)], user: user_dependency, db: db_dependency):
    """
    Get current threat indicators and counts
    """
    now = datetime.now()
    timeframe = now - timedelta(hours=24)
    
    # Get all threat logs from the last 24 hours
    threat_logs = db.query(ThreatLog).filter(
        ThreatLog.created_at >= timeframe
    ).all()
    
    # Initialize counters
    indicators = {
        "sql_injection": 0,
        "xss_attempts": 0,
        "path_traversal": 0,
        "unauthorized_access": 0,
        "rate_limit_violations": 0,
        "suspicious_ips": 0
    }
    
    # Count different types of threats
    for log in threat_logs:
        if "sql" in log.activity.lower() or "injection" in log.activity.lower():
            indicators["sql_injection"] += 1
        elif "xss" in log.activity.lower():
            indicators["xss_attempts"] += 1
        elif "path" in log.activity.lower() or "traversal" in log.activity.lower():
            indicators["path_traversal"] += 1
        elif "unauthorized" in log.activity.lower() or "access" in log.activity.lower():
            indicators["unauthorized_access"] += 1
        elif "rate" in log.activity.lower() or "limit" in log.activity.lower():
            indicators["rate_limit_violations"] += 1
    
    # Count suspicious IPs
    suspicious_ips = set()
    for log in threat_logs:
        if log.client_ip not in suspicious_ips:
            # Check if this IP has multiple threat logs
            ip_threat_count = sum(1 for l in threat_logs if l.client_ip == log.client_ip)
            if ip_threat_count >= 3:  # Consider IP suspicious if it has 3 or more threat logs
                suspicious_ips.add(log.client_ip)
    
    indicators["suspicious_ips"] = len(suspicious_ips)
    
    return indicators

@router.post("/test-threat-detection")
async def test_threat_detection(
    request: Request,
    db: db_dependency,
    user: user_dependency,
    test_payload: dict = None
):
    """
    Test endpoint for threat detection - allows testing with various payloads
    """
    client_ip = request.client.host
    
    # Create a detector instance
    detector = EnhancedThreatDetection(db)
    
    # Analyze the request
    threats = detector.analyze_request(request)
    
    # If test_payload is provided, also analyze it
    if test_payload:
        payload_threats = detector._scan_json_for_threats(test_payload)
        threats.extend(payload_threats)
    
    # Log any detected threats
    for threat_type, description in threats:
        detector._log_threat(client_ip, threat_type, description)
    
    return {
        "message": "Threat detection test completed",
        "client_ip": client_ip,
        "threats_detected": len(threats),
        "threats": threats,
        "test_payload": test_payload
    }

@router.post("/test-threat-detection-simple")
async def test_threat_detection_simple(
    request: Request,
    db: db_dependency,
    test_data: str = None
):
    """
    Simple test endpoint for threat detection - no authentication required
    """
    client_ip = request.client.host
    
    # Create a detector instance
    detector = EnhancedThreatDetection(db)
    
    # Analyze the request
    threats = detector.analyze_request(request)
    
    # If test_data is provided, also analyze it
    if test_data:
        # Check for SQL injection
        for pattern in detector.sqli_patterns:
            if re.search(pattern, test_data, re.IGNORECASE):
                threats.append(('sqli_attempt', f'SQL injection pattern detected: {pattern}'))
        
        # Check for XSS
        for pattern in detector.xss_patterns:
            if re.search(pattern, test_data, re.IGNORECASE):
                threats.append(('xss_attempt', f'XSS pattern detected: {pattern}'))
    
    # Log any detected threats
    for threat_type, description in threats:
        detector._log_threat(client_ip, threat_type, description)
    
    return {
        "message": "Threat detection test completed",
        "client_ip": client_ip,
        "threats_detected": len(threats),
        "threats": threats,
        "test_data": test_data
    }

@router.get("/threat-trends")
async def get_threat_trends(
    api_key: Annotated[str, Depends(api_key_header)], 
    user: user_dependency, 
    db: db_dependency,
    timeframe: str = "24h",  # "24h", "7d", "30d"
    interval: str = "1h"     # "1h", "1d"
):
    """
    Get threat trends over time with configurable timeframe and interval
    """
    # Calculate time range
    now = datetime.now()
    if timeframe == "24h":
        start_time = now - timedelta(hours=24)
    elif timeframe == "7d":
        start_time = now - timedelta(days=7)
    elif timeframe == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)  # Default to 24h
    
    # Get threat logs in the time range
    threat_logs = db.query(ThreatLog).filter(
        ThreatLog.created_at >= start_time
    ).all()
    
    # Group by time intervals
    trend_data = []
    current_time = start_time
    
    while current_time <= now:
        if interval == "1h":
            next_time = current_time + timedelta(hours=1)
            time_key = current_time.strftime("%Y-%m-%d %H:00:00")
        else:  # 1d
            next_time = current_time + timedelta(days=1)
            time_key = current_time.strftime("%Y-%m-%d")
        
        # Count threats in this interval
        interval_threats = [
            log for log in threat_logs 
            if current_time <= log.created_at < next_time
        ]
        
        # Categorize threats
        threat_counts = {
            'sql_injection': 0,
            'xss_attempts': 0,
            'path_traversal': 0,
            'unauthorized_access': 0,
            'rate_limit_violations': 0,
            'other_threats': 0
        }
        
        for threat in interval_threats:
            if 'sqli' in threat.activity.lower() or 'sql' in threat.activity.lower():
                threat_counts['sql_injection'] += 1
            elif 'xss' in threat.activity.lower():
                threat_counts['xss_attempts'] += 1
            elif 'path' in threat.activity.lower() or 'traversal' in threat.activity.lower():
                threat_counts['path_traversal'] += 1
            elif 'unauthorized' in threat.activity.lower() or 'access' in threat.activity.lower():
                threat_counts['unauthorized_access'] += 1
            elif 'rate' in threat.activity.lower() or 'limit' in threat.activity.lower():
                threat_counts['rate_limit_violations'] += 1
            else:
                threat_counts['other_threats'] += 1
        
        trend_data.append({
            'timestamp': time_key,
            'total_threats': len(interval_threats),
            **threat_counts
        })
        
        current_time = next_time
    
    # Calculate total threats
    total_threats = sum(item['total_threats'] for item in trend_data)
    
    return {
        "timeframe": timeframe,
        "timeInterval": interval,
        "trend_data": trend_data,
        "total_threats": total_threats,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/attacked-endpoints")
async def get_attacked_endpoints(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: db_dependency,
    page: int = 1,
    page_size: int = 10,
    severity: str = None,
    attack_type: str = None,
    is_resolved: bool = None,
    sort_by: str = "last_seen",
    sort_order: str = "desc"
):
    """
    Get attacked endpoints with filtering, sorting, and pagination
    """
    # Build query
    query = db.query(AttackedEndpoint)
    
    # Apply filters
    if severity:
        query = query.filter(AttackedEndpoint.severity == severity)
    if attack_type:
        query = query.filter(AttackedEndpoint.attack_type == attack_type)
    if is_resolved is not None:
        query = query.filter(AttackedEndpoint.is_resolved == is_resolved)
    
    # Apply sorting
    if sort_by == "last_seen":
        if sort_order == "desc":
            query = query.order_by(AttackedEndpoint.last_seen.desc())
        else:
            query = query.order_by(AttackedEndpoint.last_seen.asc())
    elif sort_by == "attack_count":
        if sort_order == "desc":
            query = query.order_by(AttackedEndpoint.attack_count.desc())
        else:
            query = query.order_by(AttackedEndpoint.attack_count.asc())
    elif sort_by == "severity":
        if sort_order == "desc":
            query = query.order_by(AttackedEndpoint.severity.desc())
        else:
            query = query.order_by(AttackedEndpoint.severity.asc())
    elif sort_by == "first_seen":
        if sort_order == "desc":
            query = query.order_by(AttackedEndpoint.first_seen.desc())
        else:
            query = query.order_by(AttackedEndpoint.first_seen.asc())
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    attacked_endpoints = query.offset(offset).limit(page_size).all()
    
    # Convert to dict format
    results = []
    for attack in attacked_endpoints:
        results.append({
            "attack_id": attack.attack_id,
            "endpoint": attack.endpoint,
            "method": attack.method,
            "attack_type": attack.attack_type,
            "client_ip": attack.client_ip,
            "attack_count": attack.attack_count,
            "first_seen": attack.first_seen.isoformat() if attack.first_seen else None,
            "last_seen": attack.last_seen.isoformat() if attack.last_seen else None,
            "recommended_fix": attack.recommended_fix,
            "severity": attack.severity,
            "is_resolved": attack.is_resolved,
            "resolution_notes": attack.resolution_notes,
            "created_at": attack.created_at.isoformat() if attack.created_at else None,
            "updated_at": attack.updated_at.isoformat() if attack.updated_at else None
        })
    
    # Calculate summary statistics
    total_pages = (total_count + page_size - 1) // page_size
    
    # Get severity distribution
    severity_counts = db.query(AttackedEndpoint.severity, func.count(AttackedEndpoint.attack_id)).group_by(AttackedEndpoint.severity).all()
    severity_distribution = {severity: count for severity, count in severity_counts}
    
    # Get attack type distribution
    attack_type_counts = db.query(AttackedEndpoint.attack_type, func.count(AttackedEndpoint.attack_id)).group_by(AttackedEndpoint.attack_type).all()
    attack_type_distribution = {attack_type: count for attack_type, count in attack_type_counts}
    
    return {
        "total_attacks": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "attacked_endpoints": results,
        "severity_distribution": severity_distribution,
        "attack_type_distribution": attack_type_distribution,
        "timestamp": datetime.now().isoformat()
    }

@router.put("/attacked-endpoints/{attack_id}/resolve")
async def resolve_attacked_endpoint(
    attack_id: int,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: db_dependency,
    resolution_notes: str = None
):
    """
    Mark an attacked endpoint as resolved
    """
    attack = db.query(AttackedEndpoint).filter(AttackedEndpoint.attack_id == attack_id).first()
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")
    
    attack.is_resolved = True
    attack.resolution_notes = resolution_notes
    attack.updated_at = datetime.now()
    
    db.commit()
    
    return {
        "message": "Attack marked as resolved",
        "attack_id": attack_id,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/test-sql-injection")
async def test_sql_injection_get(
    request: Request,
    db: db_dependency,
    user: user_dependency,
    username: str = None,
    password: str = None
):
    """
    Test endpoint for SQL injection detection via query parameters
    """
    return {
        "message": "GET request processed",
        "username": username,
        "password": password,
        "query_params": dict(request.query_params),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-sql-injection")
async def test_sql_injection_post(
    request: Request,
    db: db_dependency,
    user: user_dependency
):
    """
    Test endpoint for SQL injection detection via form data and JSON body
    """
    try:
        # Try to get JSON body
        body = await request.json()
    except:
        # If not JSON, try form data
        body = await request.form()
        body = dict(body)
    
    return {
        "message": "POST request processed",
        "body": body,
        "content_type": request.headers.get("content-type"),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/logs/by-ip")
def get_logs_by_ip(ip: str, db: Session = Depends(get_db)):
    """
    Return all logs (threat, traffic, activity, API requests) for a given IP.
    """
    threat_logs = db.query(ThreatLog).filter(ThreatLog.client_ip == ip).all()
    traffic_logs = db.query(TrafficLog).filter(TrafficLog.client_ip == ip).all()
    api_requests = db.query(APIRequest).filter(APIRequest.client_ip == ip).all()
    activity_logs = db.query(ActivityLog).filter(ActivityLog.client_ip == ip).all()
    def serialize(logs):
        return [
            {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in log.__dict__.items() if not k.startswith('_')}
            for log in logs
        ]
    return {
        "threat_logs": serialize(threat_logs),
        "traffic_logs": serialize(traffic_logs),
        "api_requests": serialize(api_requests),
        "activity_logs": serialize(activity_logs),
    }

