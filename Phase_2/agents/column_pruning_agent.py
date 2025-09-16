from groq import Groq
import json
from typing import Dict, Any

def prune_columns(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses an LLM to identify relevant columns from the confirmed tables
    and creates a pruned schema for the query generator.
    """
    print("---COLUMN PRUNING AGENT---")
    if 'error' in state and state.get('error'):
        return state

    groq_config = state['groq_config']
    full_schema = state['schema']
    confirmed_tables = state['confirmed_tables']
    user_prompt = state['user_prompt']

    # Filter the full schema to only include the CREATE TABLE statements for confirmed tables
    schema_for_pruning = ""
    current_schema_lines = full_schema.split('CREATE TABLE')
    for table_name in confirmed_tables:
        for schema_part in current_schema_lines:
            # Check if the schema part starts with the table name (handling backticks)
            if schema_part.strip().startswith(f"`{table_name}`") or schema_part.strip().startswith(table_name):
                schema_for_pruning += "CREATE TABLE" + schema_part
                break

    if not schema_for_pruning:
        state['error'] = "Could not find schema for confirmed tables."
        return state

    try:
        client = Groq(api_key=groq_config['groq_api_key'])
        prompt = f"""
You are a database schema optimization expert. Based on the following database schema and user question, provide a pruned version of the schema that only includes the tables and columns relevant to answering the question.

Full Schema:
{schema_for_pruning}

User Question:
"{user_prompt}"

Respond with the pruned schema as a single, valid SQL string. Only include the CREATE TABLE statements for the relevant tables and only the relevant columns within those tables. Do not include any other text or explanation.
"""
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a database schema optimization expert."},
                {"role": "user", "content": prompt}
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
        )

        pruned_schema = chat_completion.choices[0].message.content
        
        # --- THE CRITICAL FIX IS HERE ---
        # We must add the result back into the state for the next agent to use.
        state['pruned_schema'] = pruned_schema
        
        print(f"Pruned Schema for Query Generation:\n{pruned_schema}")

    except Exception as e:
        error_message = f"Failed to prune columns: {e}"
        print(error_message)
        state['error'] = error_message
        # If pruning fails, we can fallback to the full schema to allow the next step to proceed
        state['pruned_schema'] = state.get('schema', '')

    return state