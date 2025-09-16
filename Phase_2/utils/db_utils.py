"""
Database connection utilities using LangChain's SQLDatabase wrapper.
This version includes connection timeouts to prevent the application from hanging.
"""
from typing import Dict, Any
import logging
from langchain_community.utilities import SQLDatabase
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

def get_db_connection(config: Dict[str, Any]) -> SQLDatabase:
    """
    Creates and returns a database connection using the appropriate method.
    """
    db_type = config.get('db_type')
    if not db_type:
        raise ValueError("db_type not specified in config")

    logger.info(f"Attempting to create {db_type} connection...")

    if db_type == 'sqlite':
        return create_sqlite_connection(config.get('sqlite_path', 'my_database.db'))
    
    elif db_type == 'mysql':
        return create_mysql_connection(config)

    elif db_type == 'postgres':
        return create_postgresql_connection(config)
        
    else:
        raise ValueError(f"Unsupported db_type: {db_type}")

def create_sqlite_connection(db_file_path: str) -> SQLDatabase:
    """Create SQLite connection from file path."""
    logger.info(f"Creating SQLite connection to: {db_file_path}")
    # The 'connect_args' is how we pass the timeout to the underlying sqlite3 driver
    return SQLDatabase.from_uri(f"sqlite:///{db_file_path}", engine_args={'connect_args': {'timeout': 10}})

def create_mysql_connection(config: Dict[str, Any]) -> SQLDatabase:
    """Create MySQL connection from config, safely encoding password and adding a timeout."""
    encoded_password = quote_plus(config['mysql_password'])
    # We add the timeout parameter directly to the URI string for SQLAlchemy
    mysql_uri = (
        f"mysql+pymysql://{config['mysql_user']}:{encoded_password}"
        f"@{config['mysql_host']}:{config['mysql_port']}/{config['mysql_database']}"
        f"?connect_timeout=10"  # <-- **THE CRITICAL FIX**
    )
    logger.info(f"Creating MySQL connection to: {config['mysql_host']}:{config['mysql_port']}")
    return SQLDatabase.from_uri(mysql_uri)

def create_postgresql_connection(config: Dict[str, Any]) -> SQLDatabase:
    """Create PostgreSQL connection from config with a timeout."""
    # For psycopg2, the timeout is passed as a keyword argument to the engine
    postgres_uri = (
        f"postgresql+psycopg2://{config['postgres_user']}:{config['postgres_password']}"
        f"@{config['postgres_host']}:{config['postgres_port']}/{config['postgres_database']}"
    )
    logger.info(f"Creating PostgreSQL connection to: {config['postgres_host']}:{config['postgres_port']}")
    return SQLDatabase.from_uri(postgres_uri, engine_args={'connect_args': {'connect_timeout': 10}})