from typing import Dict, Any, List
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text
import re

def _extract_column_names_from_query(query: str) -> List[str]:
    """Extracts column names from a SELECT query."""
    try:
        query_upper = query.upper().strip()
        match = re.search(r"SELECT\s+(.*?)\s+FROM", query_upper)
        if not match:
            return []
        select_part = match.group(1)
        if select_part.strip() == "*":
            return []
        parts = re.split(r",(?![^\(]*\))", select_part)
        columns = []
        for part in parts:
            part = part.strip()
            if ' AS ' in part:
                alias = part.split(' AS ')[-1].strip()
                columns.append(alias.strip('`"\''))
            else:
                alias = part.split()[-1].strip()
                columns.append(alias.strip('`"\''))
        return columns
    except Exception:
        return []

def execute_sql_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs the SQL query, reliably capturing both column names and rows.
    """
    print("---QUERY EXECUTOR---")
    if 'error' in state and state.get('error'):
        return state

    try:
        db: SQLDatabase = state['db_connection']
        sql_query = state['sql_query'].strip().rstrip(';')
        print(f"Executing Query: {sql_query}")

        with db._engine.connect() as connection:
            result_proxy = connection.execute(text(sql_query))
            
            # First, try to get columns from the query itself
            columns = _extract_column_names_from_query(sql_query)
            
            # --- THE FIX IS HERE ---
            # If parsing the query fails (like for 'SHOW TABLES'),
            # get the column names directly from the cursor description.
            if not columns:
                columns = list(result_proxy.keys())
            
            rows = result_proxy.fetchall()

        print(f"Query Results - Columns: {columns}, Rows: {len(rows)}")

        state['results'] = {
            "columns": columns,
            "rows": [tuple(row) for row in rows]
        }

    except Exception as e:
        error_message = f"Failed to execute SQL query: {e}"
        print(error_message)
        state['error'] = error_message
        state['results'] = {"columns": [], "rows": []}

    return state