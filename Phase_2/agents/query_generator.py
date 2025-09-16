from groq import Groq
import json
from typing import Dict, Any

def _get_db_name(db_config: Dict[str, Any]) -> str:
    """Extracts the database name from the config, handling different DB types."""
    db_type = db_config.get("db_type")
    if db_type == "mysql":
        return db_config.get("mysql_database", "")
    elif db_type == "postgres":
        return db_config.get("postgres_database", "")
    elif db_type == "sqlite":
        return db_config.get("sqlite_db_path", "")
    return ""


def generate_sql_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses an LLM to generate a SQL query from the user's prompt, the pruned schema,
    and a strict set of rules.
    """
    print("---QUERY GENERATOR---")
    if 'error' in state and state.get('error'):
        return state

    groq_config = state['groq_config']
    user_prompt = state['user_prompt']
    pruned_schema = state.get('pruned_schema', state.get('schema'))
    db_name = _get_db_name(state.get('db_config', {}))
    db_type = state.get('db_config', {}).get('db_type', 'unknown')

    try:
        client = Groq(api_key=groq_config['groq_api_key'])
        
        # --- NEW PROMPT INCORPORATING YOUR RULES ---
        prompt = f"""
You are a master SQL generator for a '{db_type}' database. Your sole purpose is to generate a single, syntactically correct SQL query based on the user's question and the provided schema.

### CRITICAL RULES:
- NEVER make up column or table names. Use ONLY the table and column names provided in the schema.
- NEVER SELECT * — only select the specific columns needed to answer the question.
- Unless the user specifies a different number, ALWAYS LIMIT your query to 20 results to avoid overwhelming the user.
- ALWAYS order results by a relevant column (like a date or a total) to return the most interesting and relevant data.
- Do NOT make any DML statements (INSERT, UPDATE, DELETE, DROP, etc.). Only generate SELECT queries.
- For MySQL, if asked to simply list tables, use 'SHOW TABLES;' for simplicity. For other database types or more complex requests, use the INFORMATION_SCHEMA.

### Database Context
Database Type: {db_type}
Database Name: {db_name}
Database Schema:
{pruned_schema}

### User Question
"{user_prompt}"

### Your Task
Respond with a JSON object containing two keys: "sql_query" and "reasoning".
1. "sql_query": A single, valid SQL query string that adheres to all the critical rules.
2. "reasoning": A brief, one-sentence explanation of why you chose to write the query in this way.
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are a SQL query generation expert for {db_type} databases who follows rules strictly."},
                {"role": "user", "content": prompt}
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
            response_format={"type": "json_object"},
        )

        response = json.loads(chat_completion.choices[0].message.content)
        state['sql_query'] = response.get('sql_query', '')
        state['reasoning'] = response.get('reasoning', '')

        if not state['sql_query']:
            raise ValueError("LLM failed to generate a SQL query.")

        print(f"Generated SQL: {state['sql_query']}")
        print(f"Reasoning: {state['reasoning']}")

    except Exception as e:
        error_message = f"Failed to generate SQL query: {e}"
        print(error_message)
        state['error'] = error_message
        state['sql_query'] = "No SQL Query Generated."
        state['reasoning'] = "No reasoning provided."

    return state