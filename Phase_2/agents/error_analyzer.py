from groq import Groq
import json
from typing import Dict, Any

def analyze_sql_error(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes a SQL execution error and provides a suggestion for a fix.
    This node also increments the retry counter.
    """
    print("---ERROR ANALYZER---")
    
    # Increment the retry counter
    retries = state.get('retries', 0) + 1
    state['retries'] = retries

    # If we've retried too many times, give up.
    if retries > 2:
        print("Max retries exceeded. Aborting.")
        state['error'] = f"Failed to correct SQL query after {retries - 1} attempts. Last error: {state.get('error')}"
        state['error_analysis'] = "Max retries exceeded."
        return state

    groq_config = state['groq_config']
    failed_query = state.get('sql_query')
    error_message = state.get('error')
    schema = state.get('pruned_schema', state.get('schema'))

    try:
        client = Groq(api_key=groq_config['groq_api_key'])
        
        prompt = f"""
You are a SQL debugging expert. Your task is to analyze a failed SQL query and its error message to provide a concise, actionable suggestion for a fix.

### Database Schema:
{schema}

### Failed SQL Query:
{failed_query}

### Error Message:
{error_message}

### Your Task:
Based on the schema, the failed query, and the error, explain the likely cause of the error in one sentence and suggest a specific correction.

Example:
- Failed Query: `SELECT count FROM customers;`
- Error Message: `Unknown column 'count' in 'field list'`
- Your Suggestion: The error is because 'count' is not a column. To count all customers, you should use the SQL function `COUNT(*)`.

Respond with a JSON object containing a single key: "suggestion".
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a SQL debugging expert who provides concise suggestions for fixes."},
                {"role": "user", "content": prompt}
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
            response_format={"type": "json_object"},
        )

        response = json.loads(chat_completion.choices[0].message.content)
        state['error_analysis'] = response.get('suggestion')
        # Clear the old error so the graph can continue
        state['error'] = None 
        print(f"Error Analysis Suggestion: {state['error_analysis']}")

    except Exception as e:
        print(f"Failed to analyze error: {e}")
        # If analysis fails, we can't recover, so we set a terminal error
        state['error'] = "Failed to analyze the SQL error, cannot proceed with correction."

    return state