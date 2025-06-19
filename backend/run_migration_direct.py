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
        logging.FileHandler('migration_direct.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_migration():
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
                # Check if table already exists
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'discovered_endpoints')"))
                if result.scalar():
                    logger.warning("Table 'discovered_endpoints' already exists!")
                    return
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
        
        # Run the migration
        logger.info("Starting migration for discovered_endpoints table...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migration completed successfully!")
        
        # Verify the migration
        with engine.connect() as conn:
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'discovered_endpoints')"))
            if result.scalar():
                logger.info("Verified: discovered_endpoints table exists")
                # Check table structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'discovered_endpoints'
                """))
                columns = result.fetchall()
                logger.info("Table structure:")
                for col in columns:
                    logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.error("Migration failed: discovered_endpoints table not found")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    run_migration() 