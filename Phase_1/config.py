"""Configuration management for SQL Agent ChatBot"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Groq Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    
    # Query Configuration
    MAX_QUERY_RESULTS = int(os.getenv("MAX_QUERY_RESULTS", "10"))
    
    # MySQL Configuration
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "sql_agent.log")
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "groq_api_key": cls.GROQ_API_KEY,
            "groq_model": cls.GROQ_MODEL,
            "max_results": cls.MAX_QUERY_RESULTS,
            "mysql_host": cls.MYSQL_HOST,
            "mysql_port": cls.MYSQL_PORT,
            "mysql_user": cls.MYSQL_USER,
            "mysql_password": cls.MYSQL_PASSWORD,
            "mysql_database": cls.MYSQL_DATABASE,
            "postgres_host": cls.POSTGRES_HOST,
            "postgres_port": cls.POSTGRES_PORT,
            "postgres_user": cls.POSTGRES_USER,
            "postgres_password": cls.POSTGRES_PASSWORD,
            "postgres_database": cls.POSTGRES_DATABASE,
        }
    
    @classmethod
    def validate(cls) -> Dict[str, bool]:
        """Validate configuration"""
        return {
            "groq_api_key": bool(cls.GROQ_API_KEY),
            "mysql_complete": bool(cls.MYSQL_USER and cls.MYSQL_PASSWORD and cls.MYSQL_DATABASE),
            "postgres_complete": bool(cls.POSTGRES_USER and cls.POSTGRES_PASSWORD and cls.POSTGRES_DATABASE)
        }