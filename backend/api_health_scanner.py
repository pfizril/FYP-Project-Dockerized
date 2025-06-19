#!/usr/bin/env python
"""
Enhanced health monitoring script with smart endpoint configuration
Can be run on-demand or as a separate process
"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aiohttp
from cleanup_test_data import cleanup_test_data
from enhanced_health_check import EnhancedHealthChecker
import base64

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("health_monitor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("health_monitor")

# Load environment variables
load_dotenv()

# Import your database and models
sys.path.append('.')
try:
    from database import get_db_session
    from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

async def check_server_availability():
    """Check if the server is available"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/docs") as response:
                return response.status == 200
    except:
        return False

async def run_health_scan():
    """Run health scan for all endpoints"""
    try:
        # Check if server is available
        if not await check_server_availability():
            logger.error("Server is not available")
            return None
            
        # Initialize health checker
        health_checker = EnhancedHealthChecker()
        await health_checker.initialize()
        
        # Run health checks
        results = await health_checker.check_all_main_endpoints()
        
        # Log results
        healthy = sum(1 for r in results if r.get("status", False))
        logger.info(f"Completed health checks: {healthy}/{len(results)} endpoints healthy")
        
        # Log unhealthy endpoints
        for result in results:
            if not result.get("status", False):
                logger.warning(f"Unhealthy endpoint: {result}")
        
        # Clean up test data
        logger.info("Cleaning up test data after scan...")
        cleanup_test_data()
        logger.info("Test data cleanup completed")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in health scan: {e}")
        return None
    finally:
        await health_checker.close()

async def run_remote_server_health_scan(server_id: int):
    """Run health scan for a specific remote server"""
    logger.info(f"Starting health scan for remote server {server_id}")
    
    try:
        # Get remote server details
        with get_db_session() as db:
            remote_server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
            if not remote_server:
                raise ValueError(f"Remote server {server_id} not found")
            
            logger.info(f"Remote server details: base_url={remote_server.base_url}, auth_type={remote_server.auth_type}")
            
            # Initialize health checker with remote server details
            health_checker = EnhancedHealthChecker()
            
            # Set up authentication based on server type
            if remote_server.auth_type == "basic":
                basic_auth = (remote_server.username, remote_server.password)
                await health_checker.initialize(base_url=remote_server.base_url, basic_auth=basic_auth)
            else:
                await health_checker.initialize(base_url=remote_server.base_url)
            
            # First check if the server is accessible by checking /docs endpoint
            docs_url = f"{remote_server.base_url.rstrip('/')}/docs"
            logger.info(f"Checking remote server docs endpoint: {docs_url}")
            
            headers = {}
            if remote_server.auth_type == "basic":
                auth_str = f"{remote_server.username}:{remote_server.password}"
                auth_bytes = auth_str.encode('ascii')
                base64_auth = base64.b64encode(auth_bytes).decode('ascii')
                headers["Authorization"] = f"Basic {base64_auth}"
                logger.info("Added Basic Auth headers")
            
            logger.info(f"Making request to {docs_url} with headers: {headers}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(docs_url, headers=headers) as response:
                    logger.info(f"Remote server /docs status: {response.status}")
                    if response.status == 200:
                        body = await response.text()
                        logger.info(f"Response body:\n{body[:500]}...")  # Log first 500 chars
                        
                        # Save docs health check result
                        with get_db_session() as db:
                            health_record = EndpointHealth(
                                discovered_endpoint_id=None,
                                status=True,
                                is_healthy=True,
                                response_time=0,
                                checked_at=datetime.now(),
                                status_code=200,
                                error_message=None,
                                failure_reason=None
                            )
                            db.add(health_record)
                            db.commit()
                            logger.info("Saved docs health check result: healthy=True")
            
            # Get discovered endpoints for this server
            with get_db_session() as db:
                discovered_endpoints = db.query(DiscoveredEndpoint).filter(
                    DiscoveredEndpoint.remote_server_id == server_id,
                    DiscoveredEndpoint.is_active == True
                ).all()
                logger.info(f"Found {len(discovered_endpoints)} discovered endpoints for remote server {server_id}")
            
            # Run health checks
            results = await health_checker.check_all_discovered_endpoints(server_id)
            
            # Log results
            healthy_count = sum(1 for r in results if r.get('status', False))
            logger.info(f"Completed health checks: {healthy_count}/{len(results)} endpoints healthy for remote server {server_id}")
            
            # Log unhealthy endpoints
            for result in results:
                if not result.get('status', False):
                    logger.warning(f"Unhealthy endpoint: {result}")
            
            # Clean up test data
            logger.info("Cleaning up test data after scan...")
            cleanup_test_data()
            logger.info("Test data cleanup completed")
            
            # Close health checker
            await health_checker.close()
            logger.info(f"Health scan for remote server {server_id} completed")
            
            return results
            
    except Exception as e:
        logger.error(f"Error running health scan for remote server {server_id}: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_health_scan())