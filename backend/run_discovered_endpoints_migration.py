import os
import sys
from alembic.config import Config
from alembic import command
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
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
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Check if the table exists
            result = session.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'discovered_endpoints')")
            table_exists = result.scalar()
            
            if table_exists:
                logger.info("Verified: discovered_endpoints table exists")
            else:
                logger.error("Migration failed: discovered_endpoints table not found")
                sys.exit(1)
                
        finally:
            session.close()
            engine.dispose()
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration() 