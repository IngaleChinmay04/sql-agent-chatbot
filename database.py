"""Database connection utilities for SQL Agent ChatBot"""
from urllib.parse import quote_plus
from typing import Dict, Any
import logging
from langchain_community.utilities import SQLDatabase

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Handle different database configurations"""
    
    @staticmethod
    def create_sqlite_connection(db_file_path: str) -> SQLDatabase:
        """Create SQLite connection from file path"""
        logger.info(f"Creating SQLite connection to: {db_file_path}")
        return SQLDatabase.from_uri(f"sqlite:///{db_file_path}")
    
    @staticmethod
    def create_mysql_connection(config: Dict[str, Any]) -> SQLDatabase:
        """Create MySQL connection from config, safely encoding special chars in password"""
        encoded_password = quote_plus(config['password'])
        mysql_uri = (
            f"mysql+pymysql://{config['user']}:{encoded_password}"
            f"@{config['host']}:{config['port']}/{config['database']}"
        )
        logger.info(f"Creating MySQL connection to: {config['host']}:{config['port']}/{config['database']}")
        return SQLDatabase.from_uri(mysql_uri)
    
    @staticmethod
    def create_postgresql_connection(config: Dict[str, Any]) -> SQLDatabase:
        """Create PostgreSQL connection from config"""
        postgres_uri = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        logger.info(f"Creating PostgreSQL connection to: {config['host']}:{config['port']}/{config['database']}")
        return SQLDatabase.from_uri(postgres_uri)

class DatabaseDetector:
    """Database type detection utilities"""
    
    @staticmethod
    def detect_db_type(db: SQLDatabase) -> str:
        """Detect database type from URI"""
        try:
            # Try different ways to get the database URL
            if hasattr(db, 'engine') and hasattr(db.engine, 'url'):
                uri = str(db.engine.url)
            elif hasattr(db, '_engine') and hasattr(db._engine, 'url'):
                uri = str(db._engine.url)
            elif hasattr(db, 'db_chain') and hasattr(db.db_chain, 'database'):
                # For newer LangChain versions
                engine = db.db_chain.database.engine
                uri = str(engine.url)
            else:
                # Fallback: try to get dialect name directly
                if hasattr(db, 'dialect'):
                    dialect = str(db.dialect)
                elif hasattr(db, '_engine'):
                    dialect = str(db._engine.dialect.name)
                else:
                    logger.warning("Could not detect database type - no recognizable attributes")
                    return 'unknown'
                
                if 'mysql' in dialect.lower():
                    return 'mysql'
                elif 'postgresql' in dialect.lower() or 'postgres' in dialect.lower():
                    return 'postgresql'
                elif 'sqlite' in dialect.lower():
                    return 'sqlite'
                else:
                    return 'unknown'
            
            # Parse URI to determine database type
            if uri.startswith('sqlite'):
                return 'sqlite'
            elif uri.startswith('mysql'):
                return 'mysql'
            elif uri.startswith('postgresql'):
                return 'postgresql'
            else:
                logger.warning(f"Unknown database URI format: {uri}")
                return 'unknown'
                
        except Exception as e:
            logger.warning(f"Could not detect database type: {e}")
            # Try to inspect the database object further
            try:
                # Alternative detection method
                if hasattr(db, 'run'):
                    # Test with a simple query to detect type
                    test_queries = {
                        'sqlite': "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1",
                        'mysql': "SELECT TABLE_NAME FROM information_schema.TABLES LIMIT 1",
                        'postgresql': "SELECT tablename FROM pg_tables LIMIT 1"
                    }
                    
                    for db_type, query in test_queries.items():
                        try:
                            result = db.run(query)
                            logger.info(f"Database type detected as {db_type} via test query")
                            return db_type
                        except Exception:
                            continue
                    
                logger.warning("Could not detect database type via test queries either")
                return 'unknown'
            except Exception as e2:
                logger.error(f"Failed all database type detection methods: {e2}")
                return 'unknown'
    
    @staticmethod
    def get_db_guidance(db_type: str) -> str:
        """Get database-specific guidance"""
        guidance = {
            'sqlite': """
For SQLite:
- List tables: SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
- Table info: PRAGMA table_info(table_name)
""",
            'mysql': """
For MySQL:
- List tables: SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
- Table info: DESCRIBE table_name or SELECT * FROM information_schema.COLUMNS WHERE TABLE_NAME = 'table_name' AND TABLE_SCHEMA = DATABASE()
""",
            'postgresql': """
For PostgreSQL:
- List tables: SELECT tablename FROM pg_tables WHERE schemaname = 'public'
- Table info: SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'table_name'
""",
            'unknown': """
For Unknown Database Type:
- Try standard SQL queries
- Use INFORMATION_SCHEMA if available
- Check database documentation for specific syntax
"""
        }
        return guidance.get(db_type, guidance['unknown'])