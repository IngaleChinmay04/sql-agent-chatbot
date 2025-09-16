from groq import Groq
import json
from typing import Dict, Any, List

def identify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identifies if the user's prompt is relevant to the database schema.
    If it is, it extracts keywords. If not, it flags it as irrelevant.
    """
    print("---INTENT AGENT---")
    if 'error' in state and state.get('error'):
        return state

    groq_config = state['groq_config']
    user_prompt = state['user_prompt']
    schema = state.get('schema')

    if not user_prompt or not schema:
        state['error'] = "Missing user prompt or schema for intent identification."
        return state

    try:
        client = Groq(api_key=groq_config['groq_api_key'])
        
        # --- NEW, MORE POWERFUL PROMPT ---
        prompt = f"""
You are a database gatekeeper. Your job is to determine if a user's question can be answered using the provided database schema.

### Database Schema
{schema}

### User Question
"{user_prompt}"

### Your Task
Analyze the user question and the schema. Respond with a JSON object containing two keys:
1. "decision": A string that is either "RELEVANT" or "IRRELEVANT".
   - "RELEVANT": If the question is asking about concepts, entities, or data that could plausibly exist within the provided schema.
   - "IRRELEVANT": If the question is about general knowledge, current events, or topics completely unrelated to the schema (e.g., "Who is the prime minister?", "What is the weather today?").
2. "keywords": If the decision is "RELEVANT", provide a list of keywords from the user's question that are most pertinent to generating a SQL query. If "IRRELEVANT", this can be an empty list.

Example for a relevant question:
User Question: "How many customers are from California?"
Schema: Contains a 'customers' table with a 'state' column.
Your Response:
{{
  "decision": "RELEVANT",
  "keywords": ["customers", "count", "California"]
}}

Example for an irrelevant question:
User Question: "What is the capital of France?"
Schema: Contains tables about products and sales.
Your Response:
{{
  "decision": "IRRELEVANT",
  "keywords": []
}}
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a database gatekeeper determining question relevance based on a schema."},
                {"role": "user", "content": prompt}
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
            response_format={"type": "json_object"},
        )

        response = json.loads(chat_completion.choices[0].message.content)
        
        # Add the decision and keywords to the state
        state['intent_decision'] = response.get('decision', 'IRRELEVANT').upper()
        state['intent_keywords'] = response.get('keywords', [])

        print(f"Intent Decision: {state['intent_decision']}")
        print(f"Intent Keywords: {state['intent_keywords']}")

    except Exception as e:
        error_message = f"Failed to identify intent: {e}"
        print(error_message)
        state['error'] = error_message
        state['intent_decision'] = 'IRRELEVANT' # Default to irrelevant on error

    return state