from typing import Dict, Any
from langchain_community.utilities import SQLDatabase

def retrieve_schema(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gets relevant table/schema info from the SQLDatabase object.
    """
    print("---SCHEMA RETRIEVER---")
    if 'error' in state and state.get('error'):
        return state

    try:
        db: SQLDatabase = state['db_connection']
        # The SQLDatabase object has a convenient method for this
        schema = db.get_table_info()
        
        print("Schema Retrieved:\n", schema)
        state['schema'] = schema
    except Exception as e:
        print(f"Error retrieving schema: {e}")
        state['error'] = f"Failed to retrieve schema: {e}"

    return state