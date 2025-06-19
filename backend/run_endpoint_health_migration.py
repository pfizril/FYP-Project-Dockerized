import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='endpoint_health_migration.log'
)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the endpoint health table migration"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Create database engine
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Start transaction
            with connection.begin():
                logger.info("Starting endpoint health table migration...")
                
                # Create temporary columns
                logger.info("Creating temporary columns...")
                connection.execute(text("""
                    ALTER TABLE endpoint_health 
                    ADD COLUMN new_status VARCHAR,
                    ADD COLUMN is_healthy BOOLEAN
                """))
                
                # Update new columns based on old status
                logger.info("Updating status values...")
                connection.execute(text("""
                    UPDATE endpoint_health 
                    SET new_status = CASE 
                        WHEN status = true THEN 'success'
                        ELSE 'error'
                    END,
                    is_healthy = status
                """))
                
                # Drop old status column
                logger.info("Dropping old status column...")
                connection.execute(text("""
                    ALTER TABLE endpoint_health 
                    DROP COLUMN status
                """))
                
                # Rename new status column
                logger.info("Renaming new status column...")
                connection.execute(text("""
                    ALTER TABLE endpoint_health 
                    RENAME COLUMN new_status TO status
                """))
                
                # Make columns non-nullable
                logger.info("Making columns non-nullable...")
                connection.execute(text("""
                    ALTER TABLE endpoint_health 
                    ALTER COLUMN status SET NOT NULL,
                    ALTER COLUMN is_healthy SET NOT NULL
                """))
                
                logger.info("Migration completed successfully!")
                
                # Verify the changes
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'endpoint_health'
                """))
                
                columns = result.fetchall()
                logger.info("Current table structure:")
                for column in columns:
                    logger.info(f"  {column[0]}: {column[1]}")
                
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1) 