import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tables():
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('endpoint_health', 'discovered_endpoints')
            """))
            tables = [row[0] for row in result]
            logger.info(f"Existing tables: {tables}")
            
            # Check endpoint_health columns
            if 'endpoint_health' in tables:
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'endpoint_health'
                """))
                logger.info("Endpoint health table columns:")
                for row in result:
                    logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
            
            # Check discovered_endpoints columns
            if 'discovered_endpoints' in tables:
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'discovered_endpoints'
                """))
                logger.info("Discovered endpoints table columns:")
                for row in result:
                    logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
            
            # Check foreign keys
            result = conn.execute(text("""
                SELECT
                    tc.table_name, 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name IN ('endpoint_health', 'discovered_endpoints')
            """))
            logger.info("Foreign key constraints:")
            for row in result:
                logger.info(f"  {row[0]}.{row[1]} -> {row[2]}.{row[3]}")
                
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    check_tables() 