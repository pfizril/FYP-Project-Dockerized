import os
import sys
from alembic.config import Config
from alembic import command
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_all.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_migrations():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        logger.info(f"Using database URL: {DATABASE_URL}")
        
        # Test database connection
        engine = create_engine(DATABASE_URL)
        try:
            with engine.connect() as conn:
                logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
        
        # Get the directory containing this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_ini_path = os.path.join(current_dir, "alembic.ini")
        
        logger.info(f"Looking for alembic.ini at: {alembic_ini_path}")
        
        if not os.path.exists(alembic_ini_path):
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")
        
        # Create Alembic configuration
        alembic_cfg = Config(alembic_ini_path)
        
        # Set the script location and database URL
        alembic_cfg.set_main_option("script_location", os.path.join(current_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        # Run the migrations
        logger.info("Starting migrations...")
        
        # First, run the discovered_endpoints table migration
        logger.info("Running discovered_endpoints table migration...")
        command.upgrade(alembic_cfg, "add_discovered_endpoints_table")
        logger.info("Discovered endpoints table migration completed")
        
        # Then, run the endpoint_health table update
        logger.info("Running endpoint_health table update...")
        command.upgrade(alembic_cfg, "update_endpoint_health_table")
        logger.info("Endpoint health table update completed")
        
        # Finally, run the endpoint_health schema update
        logger.info("Running endpoint_health schema update...")
        command.upgrade(alembic_cfg, "update_endpoint_health_schema")
        logger.info("Endpoint health schema update completed")
        
        # Verify the migrations
        with engine.connect() as conn:
            # Check discovered_endpoints table
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'discovered_endpoints'
                )
            """))
            if not result.scalar():
                raise Exception("discovered_endpoints table not found")
            logger.info("Verified: discovered_endpoints table exists")
            
            # Check endpoint_health table structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'endpoint_health'
            """))
            columns = result.fetchall()
            logger.info("Endpoint health table structure:")
            for col in columns:
                logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Verify foreign key
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_endpoint_health_discovered_endpoint'
                )
            """))
            if not result.scalar():
                raise Exception("Foreign key constraint not found")
            logger.info("Verified: Foreign key constraint exists")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    run_migrations() 