#!/usr/bin/env python3
"""
PostgreSQL Table Creation Script
Creates all tables for the health monitoring system based on SQLAlchemy models
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from datetime import datetime
import os
import subprocess
import time
import sys
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLServerManager:
    """Manages PostgreSQL server startup and status"""
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
    
    def check_postgresql_installed(self) -> bool:
        """Check if PostgreSQL is installed"""
        try:
            if self.is_windows:
                # Check if PostgreSQL is installed on Windows
                result = subprocess.run(['pg_config', '--version'], 
                                      capture_output=True, text=True, shell=True)
                return result.returncode == 0
            else:
                # Check if PostgreSQL is installed on Linux/Mac
                result = subprocess.run(['which', 'psql'], 
                                      capture_output=True, text=True)
                return result.returncode == 0
        except Exception:
            return False
    
    def get_postgresql_service_name(self) -> str:
        """Get PostgreSQL service name based on OS"""
        if self.is_windows:
            # Common PostgreSQL service names on Windows
            service_names = [
                'postgresql-x64-15',
                'postgresql-x64-14', 
                'postgresql-x64-13',
                'postgresql-x64-12',
                'postgresql-x64-11',
                'postgresql'
            ]
            return service_names
        else:
            # Linux/Mac service names
            return ['postgresql', 'postgresql-15', 'postgresql-14', 'postgresql-13']
    
    def start_postgresql_service(self) -> bool:
        """Start PostgreSQL service"""
        try:
            service_names = self.get_postgresql_service_name()
            
            for service_name in service_names:
                logger.info(f"Attempting to start PostgreSQL service: {service_name}")
                
                if self.is_windows:
                    # Windows service management
                    result = subprocess.run([
                        'net', 'start', service_name
                    ], capture_output=True, text=True, shell=True)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully started PostgreSQL service: {service_name}")
                        return True
                    elif "service is already running" in result.stdout.lower():
                        logger.info(f"PostgreSQL service {service_name} is already running")
                        return True
                else:
                    # Linux/Mac service management
                    result = subprocess.run([
                        'sudo', 'systemctl', 'start', service_name
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully started PostgreSQL service: {service_name}")
                        return True
                    elif "already active" in result.stdout.lower():
                        logger.info(f"PostgreSQL service {service_name} is already running")
                        return True
            
            logger.error("Failed to start any PostgreSQL service")
            return False
            
        except Exception as e:
            logger.error(f"Error starting PostgreSQL service: {e}")
            return False
    
    def check_postgresql_running(self, host: str = "localhost", port: int = 5432) -> bool:
        """Check if PostgreSQL is running and accepting connections"""
        try:
            # Try to connect to PostgreSQL
            conn = psycopg2.connect(
                host=host,
                port=port,
                database="postgres",
                user="postgres",
                password="password",
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception:
            return False
    
    def wait_for_postgresql(self, host: str = "localhost", port: int = 5432, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to become available"""
        logger.info(f"Waiting for PostgreSQL to become available on {host}:{port}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_postgresql_running(host, port):
                logger.info("PostgreSQL is now available!")
                return True
            time.sleep(2)
        
        logger.error(f"PostgreSQL did not become available within {timeout} seconds")
        return False

class PostgreSQLTableCreator:
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "health_monitor", username: str = "postgres", 
                 password: str = "password"):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.server_manager = PostgreSQLServerManager()
        
    def ensure_postgresql_running(self) -> bool:
        """Ensure PostgreSQL is running, start it if necessary"""
        logger.info("Checking PostgreSQL installation and status...")
        
        # Check if PostgreSQL is installed
        if not self.server_manager.check_postgresql_installed():
            logger.error("PostgreSQL is not installed or not found in PATH")
            print("\nPostgreSQL Installation Required!")
            print("=" * 40)
            print("PostgreSQL is not installed on your system.")
            print("\nInstallation options:")
            
            if self.server_manager.is_windows:
                print("1. Download from: https://www.postgresql.org/download/windows/")
                print("2. Use Chocolatey: choco install postgresql")
                print("3. Use WSL2 with Ubuntu and install PostgreSQL")
            else:
                print("1. Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib")
                print("2. CentOS/RHEL: sudo yum install postgresql postgresql-server")
                print("3. macOS: brew install postgresql")
            
            print("\nAfter installation, run this script again.")
            return False
        
        # Check if PostgreSQL is running
        if not self.server_manager.check_postgresql_running(self.host, self.port):
            logger.info("PostgreSQL is not running. Attempting to start it...")
            
            if not self.server_manager.start_postgresql_service():
                logger.error("Failed to start PostgreSQL service")
                print("\nPostgreSQL Service Start Failed!")
                print("=" * 40)
                print("Unable to start PostgreSQL service automatically.")
                print("\nManual steps to start PostgreSQL:")
                
                if self.server_manager.is_windows:
                    print("1. Open Services (services.msc)")
                    print("2. Find 'postgresql' service")
                    print("3. Right-click and select 'Start'")
                    print("4. Or run: net start postgresql")
                else:
                    print("1. Run: sudo systemctl start postgresql")
                    print("2. Or run: sudo service postgresql start")
                    print("3. Check status: sudo systemctl status postgresql")
                
                print("\nAfter starting PostgreSQL, run this script again.")
                return False
            
            # Wait for PostgreSQL to become available
            if not self.server_manager.wait_for_postgresql(self.host, self.port):
                return False
        
        logger.info("PostgreSQL is running and ready!")
        return True
        
    def connect(self, create_database: bool = True) -> bool:
        """Connect to PostgreSQL server"""
        try:
            # First ensure PostgreSQL is running
            if not self.ensure_postgresql_running():
                return False
            
            if create_database:
                # First connect to default postgres database to create our database
                try:
                    conn = psycopg2.connect(
                        host=self.host,
                        port=self.port,
                        database="postgres",
                        user=self.username,
                        password=self.password,
                        connect_timeout=10
                    )
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cursor = conn.cursor()
                    
                    # Check if database exists
                    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (self.database,))
                    exists = cursor.fetchone()
                    
                    if not exists:
                        cursor.execute(f'CREATE DATABASE "{self.database}"')
                        logger.info(f"Created database: {self.database}")
                    else:
                        logger.info(f"Database {self.database} already exists")
                    
                    cursor.close()
                    conn.close()
                    
                except psycopg2.OperationalError as e:
                    if "authentication failed" in str(e).lower():
                        logger.error("Authentication failed. Please check your PostgreSQL credentials.")
                        print("\nAuthentication Error!")
                        print("=" * 40)
                        print("PostgreSQL authentication failed.")
                        print("\nPossible solutions:")
                        print("1. Check if the password is correct")
                        print("2. Verify the username exists")
                        print("3. Check pg_hba.conf configuration")
                        print("\nDefault PostgreSQL setup:")
                        print("- Username: postgres")
                        print("- Password: (set during installation)")
                        print("\nTo reset password:")
                        if self.server_manager.is_windows:
                            print("1. Open pgAdmin")
                            print("2. Right-click on PostgreSQL server")
                            print("3. Select 'Properties' and change password")
                        else:
                            print("1. Run: sudo -u postgres psql")
                            print("2. Execute: ALTER USER postgres PASSWORD 'new_password';")
                        return False
                    else:
                        raise e
            
            # Connect to our database
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )
            logger.info(f"Connected to PostgreSQL database: {self.database}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            print(f"\nConnection Error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")
    
    def create_tables(self) -> bool:
        """Create all tables for the health monitoring system"""
        if not self.connection:
            logger.error("Not connected to database")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Create Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Users" (
                    user_id SERIAL PRIMARY KEY,
                    user_name VARCHAR(255) NOT NULL,
                    user_role VARCHAR(100) NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    hashed_psw VARCHAR(255) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_users_user_name ON "Users" (user_name);
                CREATE INDEX IF NOT EXISTS idx_users_user_role ON "Users" (user_role);
                CREATE INDEX IF NOT EXISTS idx_users_user_email ON "Users" (user_email);
                CREATE INDEX IF NOT EXISTS idx_users_hashed_psw ON "Users" (hashed_psw);
            """)
            logger.info("Created Users table")
            
            # Create API endpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_endpoints (
                    endpoint_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    url VARCHAR(500) UNIQUE NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    status BOOLEAN DEFAULT TRUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    requires_auth BOOLEAN DEFAULT FALSE
                );
                CREATE INDEX IF NOT EXISTS idx_api_endpoints_url ON api_endpoints (url);
                CREATE INDEX IF NOT EXISTS idx_api_endpoints_method ON api_endpoints (method);
                CREATE INDEX IF NOT EXISTS idx_api_endpoints_status ON api_endpoints (status);
            """)
            logger.info("Created api_endpoints table")
            
            # Create API keys table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES "Users" (user_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
                CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (key);
                CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys (user_id);
                CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys (is_active);
            """)
            logger.info("Created api_keys table")
            
            # Create Remote servers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remote_servers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    base_url VARCHAR(500) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'offline',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    api_key VARCHAR(255),
                    health_check_url VARCHAR(500),
                    username VARCHAR(255),
                    password VARCHAR(255),
                    auth_type VARCHAR(50) DEFAULT 'basic',
                    token_endpoint VARCHAR(500),
                    access_token TEXT,
                    token_expires_at TIMESTAMP,
                    created_by INTEGER NOT NULL REFERENCES "Users" (user_id)
                );
                CREATE INDEX IF NOT EXISTS idx_remote_servers_name ON remote_servers (name);
                CREATE INDEX IF NOT EXISTS idx_remote_servers_status ON remote_servers (status);
                CREATE INDEX IF NOT EXISTS idx_remote_servers_is_active ON remote_servers (is_active);
                CREATE INDEX IF NOT EXISTS idx_remote_servers_created_by ON remote_servers (created_by);
            """)
            logger.info("Created remote_servers table")
            
            # Create Discovered endpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovered_endpoints (
                    id SERIAL PRIMARY KEY,
                    remote_server_id INTEGER NOT NULL REFERENCES remote_servers (id) ON DELETE CASCADE,
                    path VARCHAR(255) NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    description TEXT,
                    parameters JSONB,
                    response_schema JSONB,
                    discovered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    endpoint_hash VARCHAR(64) UNIQUE NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_discovered_endpoints_remote_server_id ON discovered_endpoints (remote_server_id);
                CREATE INDEX IF NOT EXISTS idx_discovered_endpoints_path ON discovered_endpoints (path);
                CREATE INDEX IF NOT EXISTS idx_discovered_endpoints_method ON discovered_endpoints (method);
                CREATE INDEX IF NOT EXISTS idx_discovered_endpoints_is_active ON discovered_endpoints (is_active);
                CREATE INDEX IF NOT EXISTS idx_discovered_endpoints_endpoint_hash ON discovered_endpoints (endpoint_hash);
            """)
            logger.info("Created discovered_endpoints table")
            
            # Create Endpoint health table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS endpoint_health (
                    endpoint_health_id SERIAL PRIMARY KEY,
                    discovered_endpoint_id INTEGER REFERENCES discovered_endpoints (id) ON DELETE CASCADE,
                    status VARCHAR(50),
                    is_healthy BOOLEAN,
                    response_time FLOAT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status_code INTEGER,
                    error_message TEXT,
                    failure_reason VARCHAR(100)
                );
                CREATE INDEX IF NOT EXISTS idx_endpoint_health_discovered_endpoint_id ON endpoint_health (discovered_endpoint_id);
                CREATE INDEX IF NOT EXISTS idx_endpoint_health_status ON endpoint_health (status);
                CREATE INDEX IF NOT EXISTS idx_endpoint_health_is_healthy ON endpoint_health (is_healthy);
                CREATE INDEX IF NOT EXISTS idx_endpoint_health_checked_at ON endpoint_health (checked_at);
                CREATE INDEX IF NOT EXISTS idx_endpoint_health_status_code ON endpoint_health (status_code);
            """)
            logger.info("Created endpoint_health table")
            
            # Create Threat logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threat_logs (
                    log_id SERIAL PRIMARY KEY,
                    client_ip VARCHAR(45) NOT NULL,
                    activity VARCHAR(255) NOT NULL,
                    detail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_threat_logs_client_ip ON threat_logs (client_ip);
                CREATE INDEX IF NOT EXISTS idx_threat_logs_created_at ON threat_logs (created_at);
            """)
            logger.info("Created threat_logs table")
            
            # Create Attacked endpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attacked_endpoints (
                    attack_id SERIAL PRIMARY KEY,
                    endpoint VARCHAR(500) NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    attack_type VARCHAR(100) NOT NULL,
                    client_ip VARCHAR(45) NOT NULL,
                    attack_count INTEGER DEFAULT 1,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recommended_fix TEXT,
                    severity VARCHAR(20) DEFAULT 'medium',
                    is_resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_attacked_endpoints_endpoint ON attacked_endpoints (endpoint);
                CREATE INDEX IF NOT EXISTS idx_attacked_endpoints_attack_type ON attacked_endpoints (attack_type);
                CREATE INDEX IF NOT EXISTS idx_attacked_endpoints_client_ip ON attacked_endpoints (client_ip);
                CREATE INDEX IF NOT EXISTS idx_attacked_endpoints_severity ON attacked_endpoints (severity);
                CREATE INDEX IF NOT EXISTS idx_attacked_endpoints_is_resolved ON attacked_endpoints (is_resolved);
            """)
            logger.info("Created attacked_endpoints table")
            
            # Create Traffic logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_logs (
                    traffic_id SERIAL PRIMARY KEY,
                    client_ip VARCHAR(45) NOT NULL,
                    request_method VARCHAR(10) NOT NULL,
                    endpoint VARCHAR(500) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_traffic_logs_client_ip ON traffic_logs (client_ip);
                CREATE INDEX IF NOT EXISTS idx_traffic_logs_timestamp ON traffic_logs (timestamp);
                CREATE INDEX IF NOT EXISTS idx_traffic_logs_endpoint ON traffic_logs (endpoint);
            """)
            logger.info("Created traffic_logs table")
            
            # Create Rate limit table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit (
                    id SERIAL PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    request_count INTEGER DEFAULT 0,
                    last_request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_rate_limit_client_id ON rate_limit (client_id);
                CREATE INDEX IF NOT EXISTS idx_rate_limit_last_request_time ON rate_limit (last_request_time);
            """)
            logger.info("Created rate_limit table")
            
            # Create API request table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_request (
                    api_req_id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    endpoint VARCHAR(500) NOT NULL,
                    method VARCHAR(10) NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time FLOAT NOT NULL,
                    client_ip VARCHAR(45) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_api_request_timestamp ON api_request (timestamp);
                CREATE INDEX IF NOT EXISTS idx_api_request_endpoint ON api_request (endpoint);
                CREATE INDEX IF NOT EXISTS idx_api_request_status_code ON api_request (status_code);
                CREATE INDEX IF NOT EXISTS idx_api_request_client_ip ON api_request (client_ip);
            """)
            logger.info("Created api_request table")
            
            # Create Activity logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "Users" (user_id),
                    action VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    client_ip VARCHAR(45) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs (user_id);
                CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs (timestamp);
                CREATE INDEX IF NOT EXISTS idx_activity_logs_client_ip ON activity_logs (client_ip);
            """)
            logger.info("Created activity_logs table")
            
            # Create Vulnerability scans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vulnerability_scans (
                    vuln_id SERIAL PRIMARY KEY,
                    endpoint_id INTEGER REFERENCES api_endpoints (endpoint_id),
                    scan_result JSONB,
                    high_risk_count INTEGER DEFAULT 0,
                    medium_risk_count INTEGER DEFAULT 0,
                    low_risk_count INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_vulnerability_scans_endpoint_id ON vulnerability_scans (endpoint_id);
                CREATE INDEX IF NOT EXISTS idx_vulnerability_scans_timestamp ON vulnerability_scans (timestamp);
            """)
            logger.info("Created vulnerability_scans table")
            
            # Commit all changes
            self.connection.commit()
            cursor.close()
            
            logger.info("All tables created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def create_triggers(self) -> bool:
        """Create triggers for automatic timestamp updates"""
        if not self.connection:
            logger.error("Not connected to database")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Create function for updating updated_at timestamp
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Create triggers for tables with updated_at columns
            tables_with_updated_at = [
                'api_endpoints',
                'attacked_endpoints',
                'remote_servers'
            ]
            
            for table in tables_with_updated_at:
                cursor.execute(f"""
                    DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                    CREATE TRIGGER update_{table}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)
                logger.info(f"Created trigger for {table}")
            
            self.connection.commit()
            cursor.close()
            logger.info("All triggers created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating triggers: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def create_sample_data(self) -> bool:
        """Create sample data for testing"""
        if not self.connection:
            logger.error("Not connected to database")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Create sample user
            cursor.execute("""
                INSERT INTO "Users" (user_name, user_role, user_email, hashed_psw)
                VALUES ('admin', 'Admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4tbQJQKqK')
                ON CONFLICT DO NOTHING;
            """)
            
            # Create sample API endpoints
            cursor.execute("""
                INSERT INTO api_endpoints (name, url, method, status, description, requires_auth)
                VALUES 
                    ('Health Check', '/health', 'GET', TRUE, 'Health check endpoint', FALSE),
                    ('API Status', '/api/status', 'GET', TRUE, 'API status endpoint', TRUE),
                    ('User Info', '/api/users/me', 'GET', TRUE, 'Get current user info', TRUE)
                ON CONFLICT DO NOTHING;
            """)
            
            # Create sample remote server
            cursor.execute("""
                INSERT INTO remote_servers (name, base_url, description, status, created_by)
                VALUES ('Test Server', 'http://localhost:8001', 'Test remote server', 'online', 1)
                ON CONFLICT DO NOTHING;
            """)
            
            self.connection.commit()
            cursor.close()
            logger.info("Sample data created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            if self.connection:
                self.connection.rollback()
            return False

def main():
    """Main function to create PostgreSQL tables"""
    # Configuration - modify these values as needed
    config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'health_monitor'),
        'username': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'password')
    }
    
    print("PostgreSQL Table Creation Script")
    print("=" * 40)
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print(f"Database: {config['database']}")
    print(f"Username: {config['username']}")
    print("=" * 40)
    
    # Create table creator instance
    creator = PostgreSQLTableCreator(**config)
    
    try:
        # Connect to database
        if not creator.connect(create_database=True):
            print("Failed to connect to PostgreSQL. Please check your configuration.")
            return
        
        # Create tables
        if creator.create_tables():
            print(" Tables created successfully!")
        else:
            print(" Failed to create tables")
            return
        
        # Create triggers
        if creator.create_triggers():
            print(" Triggers created successfully!")
        else:
            print(" Failed to create triggers")
        
        # Create sample data
        if creator.create_sample_data():
            print(" Sample data created successfully!")
        else:
            print(" Failed to create sample data")
        
        print("\n Database setup completed successfully!")
        print(f"You can now connect to the database '{config['database']}' and start using the health monitoring system.")
        
    except KeyboardInterrupt:
        print("\n  Operation cancelled by user")
    except Exception as e:
        print(f" Unexpected error: {e}")
    finally:
        creator.disconnect()

if __name__ == "__main__":
    main() 