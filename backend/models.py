from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, DateTime, Float, Text, Interval
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

class Users(Base):
    __tablename__ = 'Users'

    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String , index = True)
    user_role = Column(String , index = True)
    user_email = Column(String, index = True)
    hashed_psw = Column(String, index=True)

    # Add relationship to RemoteServer model
    remote_servers = relationship("RemoteServer", back_populates="creator")

class APIEndpoint(Base):
    __tablename__ = "api_endpoints"

    endpoint_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  
    url = Column(String, unique=True, nullable=False)  
    method = Column(String, nullable=False)  
    status = Column(Boolean, default=True)  
    description = Column(String, nullable=True)  
    created_at = Column(DateTime, default=datetime.now())  
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    requires_auth = Column(Boolean, default=False) 


class EndpointHealth(Base):
    __tablename__ = 'endpoint_health'

    endpoint_health_id = Column(Integer, primary_key=True, index=True)
    discovered_endpoint_id = Column(Integer, ForeignKey('discovered_endpoints.id', ondelete='CASCADE'), nullable=True)
    status = Column(String)  # Changed from Boolean to String to store 'success' or 'error'
    is_healthy = Column(Boolean)  # Added to store boolean health status
    response_time = Column(Float)  # in ms
    checked_at = Column(DateTime, default=datetime.now)
    status_code = Column(Integer, nullable=True)  # HTTP status code
    error_message = Column(Text, nullable=True)  # Detailed error message
    failure_reason = Column(String, nullable=True)  # Categorized failure reason

    # Relationship to DiscoveredEndpoint
    endpoint = relationship("DiscoveredEndpoint", back_populates="health_records")

class APIKey(Base):
    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

class ThreatLog(Base):
    __tablename__ = "threat_logs"

    log_id = Column(Integer, primary_key=True)
    client_ip = Column(String, index=True)
    activity = Column(String)
    detail = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class AttackedEndpoint(Base):
    __tablename__ = "attacked_endpoints"

    attack_id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False)
    attack_type = Column(String, nullable=False, index=True)  # sql_injection, xss, path_traversal, etc.
    client_ip = Column(String, nullable=False, index=True)
    attack_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    recommended_fix = Column(Text, nullable=True)
    severity = Column(String, default="medium")  # low, medium, high, critical
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class TrafficLog(Base):
    __tablename__ = "traffic_logs"
    
    traffic_id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String, index=True)
    request_method = Column(String)
    endpoint = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    # request_body = Column(String, nullable=True)  

class RateLimit(Base):
    __tablename__ = "rate_limit"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, index=True)
    request_count = Column(Integer, default=0)
    last_request_time = Column(DateTime, default=datetime.now)

class APIRequest(Base):
    __tablename__ = "api_request"
    
    api_req_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    endpoint = Column(String, index=True)
    method = Column(String)
    status_code = Column(Integer)
    response_time = Column(Float)
    client_ip = Column(String, index=True)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    action = Column(String)  # e.g., "Created Endpoint", "Revoked API Key"
    timestamp = Column(DateTime, default=datetime.now)
    client_ip = Column(String, index=True)


class VulnerabilityScan(Base):
    __tablename__ = "vulnerability_scans"
    
    vuln_id = Column(Integer, primary_key=True)
    endpoint_id = Column(Integer, ForeignKey('api_endpoints.endpoint_id'))
    scan_result = Column(JSON)
    high_risk_count = Column(Integer)
    medium_risk_count = Column(Integer)
    low_risk_count = Column(Integer)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

class DiscoveredEndpoint(Base):
    __tablename__ = "discovered_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    remote_server_id = Column(Integer, ForeignKey("remote_servers.id", ondelete="CASCADE"))
    path = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    discovered_at = Column(DateTime, nullable=False)
    last_checked = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    endpoint_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Relationships
    remote_server = relationship("RemoteServer", back_populates="discovered_endpoints")
    health_records = relationship("EndpointHealth", back_populates="endpoint", cascade="all, delete-orphan")

class RemoteServer(Base):
    __tablename__ = "remote_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    base_url = Column(String)
    description = Column(String, nullable=True)
    status = Column(String, default="offline")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    api_key = Column(String, nullable=True)
    health_check_url = Column(String, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    auth_type = Column(String, default="basic")
    token_endpoint = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("Users.user_id"), nullable=False)

    # Add relationship to Users model
    creator = relationship("Users", back_populates="remote_servers")

    # Add relationship to DiscoveredEndpoint
    discovered_endpoints = relationship("DiscoveredEndpoint", back_populates="remote_server")