import subprocess
import time
import sys
import os
import signal
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='test_run.log'
)
logger = logging.getLogger(__name__)

def run_test_api_server():
    """Run the test API server in a separate process"""
    logger.info("Starting test API server...")
    server_process = subprocess.Popen(
        [sys.executable, "test_api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(2)
    
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        logger.error(f"Failed to start test API server: {stderr}")
        return None
    
    logger.info("Test API server started successfully")
    return server_process

def run_system_test():
    """Run the system test"""
    logger.info("Starting system test...")
    test_process = subprocess.run(
        [sys.executable, "test_system.py"],
        capture_output=True,
        text=True
    )
    
    if test_process.returncode != 0:
        logger.error(f"System test failed: {test_process.stderr}")
        return False
    
    logger.info("System test completed successfully")
    return True

def main():
    """Run the complete test suite"""
    try:
        # Start the test API server
        server_process = run_test_api_server()
        if not server_process:
            logger.error("Failed to start test API server. Exiting...")
            return
        
        try:
            # Run the system test
            success = run_system_test()
            
            # Save test results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = "test_results"
            os.makedirs(results_dir, exist_ok=True)
            
            # Copy log files to results directory
            for log_file in ["system_test.log", "test_run.log"]:
                if os.path.exists(log_file):
                    new_name = f"{results_dir}/{log_file.replace('.log', f'_{timestamp}.log')}"
                    os.rename(log_file, new_name)
            
            # Copy test results JSON
            for json_file in os.listdir():
                if json_file.startswith("system_test_results_") and json_file.endswith(".json"):
                    new_name = f"{results_dir}/{json_file}"
                    os.rename(json_file, new_name)
            
            if success:
                logger.info("All tests completed successfully!")
            else:
                logger.error("System test failed!")
                
        finally:
            # Clean up the server process
            logger.info("Stopping test API server...")
            server_process.terminate()
            server_process.wait(timeout=5)
            
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 