from typing import Dict, Any
from utils.db_utils import get_db_connection

def connect_to_db(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determines DB type and creates a connection.
    """
    print("---DB CONNECTOR---")
    db_config = state['db_config']
    try:
        connection = get_db_connection(db_config)
        print(f"Successfully connected to {db_config.get('db_type')}")
        state['db_connection'] = connection
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        state['error'] = f"Failed to connect to database: {e}"
    return state