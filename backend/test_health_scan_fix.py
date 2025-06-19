#!/usr/bin/env python
"""
Test script to verify health scan authentication fix
"""
import asyncio
import logging
from enhanced_health_check import health_checker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_health_scan():
    """Test the health scan functionality"""
    try:
        logger.info("Testing health scan authentication fix...")
        
        # Initialize health checker
        await health_checker.initialize()
        logger.info("Health checker initialized successfully")
        
        # Test authentication
        if health_checker.auth_token:
            logger.info("Authentication successful - token obtained")
        else:
            logger.error("Authentication failed - no token obtained")
            return False
        
        # Test a simple endpoint check
        logger.info("Testing endpoint health check...")
        results = await health_checker.check_all_main_endpoints(batch_size=2)
        
        logger.info(f"Health check completed. Found {len(results)} endpoints")
        for result in results[:3]:  # Show first 3 results
            logger.info(f"Endpoint: {result.get('url', 'N/A')} - Status: {result.get('status', False)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        await health_checker.close()

if __name__ == "__main__":
    success = asyncio.run(test_health_scan())
    if success:
        print("✅ Health scan authentication fix test PASSED")
    else:
        print("❌ Health scan authentication fix test FAILED") 