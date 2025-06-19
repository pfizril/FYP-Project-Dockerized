-- =============================================================================
-- API Security System - Database Initialization Script
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS api_security;

-- Set search path
SET search_path TO api_security, public;

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'user', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE endpoint_status AS ENUM ('active', 'inactive', 'maintenance');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE threat_level AS ENUM ('low', 'medium', 'high', 'critical');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp ON api_requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_endpoint_health_endpoint_id ON endpoint_health(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_remote_servers_status ON remote_servers(status);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant necessary permissions
GRANT USAGE ON SCHEMA api_security TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA api_security TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA api_security TO postgres;

-- Create a view for dashboard statistics
CREATE OR REPLACE VIEW dashboard_stats AS
SELECT 
    COUNT(*) as total_endpoints,
    COUNT(CASE WHEN status = true THEN 1 END) as active_endpoints,
    COUNT(CASE WHEN status = false THEN 1 END) as inactive_endpoints
FROM endpoints;

-- Create a view for recent security events
CREATE OR REPLACE VIEW recent_security_events AS
SELECT 
    timestamp,
    endpoint,
    method,
    status_code,
    client_ip,
    response_time
FROM api_requests 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Log successful initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;

-- Set default timezone
SET timezone = 'UTC';

-- Optimize database settings for the application
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf(); 