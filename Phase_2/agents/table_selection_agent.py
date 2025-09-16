from groq import Groq
import json
from typing import Dict, Any

def select_tables(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Selects relevant tables based on the user prompt, schema, and intent.
    It then sets the graph to wait for user confirmation.
    """
    print("---TABLE SELECTION AGENT---")
    if 'error' in state and state.get('error'):
        return state

    user_prompt = state['user_prompt']
    schema = state['schema']
    groq_config = state['groq_config']
    intent_keywords = state.get('intent_keywords', [])

    try:
        client = Groq(api_key=groq_config['groq_api_key'])
        prompt = f"""
        You are an expert database administrator. Your task is to identify the most relevant tables to answer a user's question.
        
        Full Database Schema:
        {schema}

        User Question:
        "{user_prompt}"

        Hint (Identified Intent Keywords): {', '.join(intent_keywords)}

        Based on all the information, provide a JSON object with a single key "suggested_tables", which is a list of the table names required to answer the question.
        Only include tables that exist in the schema.
        """
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a table selection expert for text-to-SQL tasks."},
                {"role": "user", "content": prompt}
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
            response_format={"type": "json_object"},
        )
        response = json.loads(chat_completion.choices[0].message.content)
        state['suggested_tables'] = response.get('suggested_tables', [])
        
        # Signal that we need user input
        state['needs_user_confirmation'] = True
        print(f"Suggested Tables for User Confirmation: {state['suggested_tables']}")

    except Exception as e:
        print(f"Error in Table Selection Agent: {e}")
        state['error'] = f"Failed to select tables: {e}"

    return state