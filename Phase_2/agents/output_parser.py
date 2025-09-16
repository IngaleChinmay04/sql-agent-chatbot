from typing import Dict, Any
import pandas as pd
from groq import Groq

def _is_purpose_question(prompt: str) -> bool:
    """Checks if the user prompt is asking about the database's purpose."""
    purpose_keywords = ['purpose', 'describe', 'about', 'structure', 'point']
    return any(keyword in prompt.lower() for keyword in purpose_keywords)

def _is_list_of_tables(results: Dict) -> bool:
    """Checks if the result is a single-column list, likely of table names."""
    if not results or not results.get('rows'):
        return False
    # Check if there's only one column
    if len(results.get('columns', [])) != 1:
        return False
    # Check if all rows are single-element tuples/lists
    if not all(len(row) == 1 for row in results.get('rows', [])):
        return False
    return True


def format_final_output(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses an LLM to generate a comprehensive final response, with special handling
    for "purpose of the database" questions.
    """
    print("---OUTPUT PARSER / FINAL RESPONSE GENERATOR---")
    
    groq_config = state['groq_config']
    user_prompt = state.get('user_prompt', 'No prompt provided.')
    final_output = {
        "sql_query": state.get('sql_query', 'No SQL Query Generated.'),
        "reasoning": state.get('reasoning', 'No reasoning provided.')
    }

    # Case 1: The question was deemed irrelevant
    if state.get('intent_decision') == 'IRRELEVANT':
        final_output["response"] = "I am a database querying agent and do not have access to general knowledge. Please ask a question related to the database schema."
        state['final_output'] = final_output
        return state

    # Case 2: An error occurred
    if 'error' in state and state.get('error'):
        final_output["response"] = f"An error occurred: {state['error']}"
        state['final_output'] = final_output
        return state

    # Case 3: The query executed, but returned no results
    results = state.get('results')
    if not results or not results.get('rows'):
        final_output["response"] = "The query executed successfully, but it returned no results."
        state['final_output'] = final_output
        return state
        
    try:
        # --- NEW LOGIC FOR PURPOSE QUESTIONS ---
        if _is_purpose_question(user_prompt) and _is_list_of_tables(results):
            print("Handling 'purpose of database' question.")
            table_list = [row[0] for row in results['rows']]
            
            client = Groq(api_key=groq_config['groq_api_key'])
            prompt = f"""
You are an expert data analyst. Your job is to determine the purpose of a database based on its list of tables.

### User's Original Question:
"{user_prompt}"

### Tables found in the database:
{', '.join(table_list)}

### Your Task:
Synthesize this information into a concise, 1-2 sentence summary of the database's purpose. Do NOT simply list the tables again. Explain what they are likely used for together.

Example:
If the tables are `customers`, `products`, and `orders`, a good summary is: "This database appears to be for an e-commerce platform, designed to track customer information, product inventory, and sales transactions."
"""
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst who infers a database's purpose from its table names."},
                    {"role": "user", "content": prompt}
                ],
                model=groq_config.get('groq_model', "llama3-8b-8192"),
                temperature=0,
            )
            final_response = chat_completion.choices[0].message.content
            final_output["response"] = final_response
        else:
            # --- Original logic for all other data-based questions ---
            df = pd.DataFrame(results['rows'], columns=results['columns'])
            markdown_table = df.to_markdown(index=False)
            
            client = Groq(api_key=groq_config['groq_api_key'])
            prompt = f"""
You are a data analyst assistant. Your job is to provide a brief, insightful summary of query results.

### User's Original Question:
"{user_prompt}"

### Query Result Data:
{markdown_table}

### Your Task:
Write a 1-2 sentence summary of the key insight from the data, then append the full Markdown table of the results.

### Final Output Format:
[Your 1-2 sentence summary here]

{markdown_table}
"""
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst assistant who summarizes query results."},
                    {"role": "user", "content": prompt}
                ],
                model=groq_config.get('groq_model', "llama3-8b-8192"),
                temperature=0,
            )
            final_response = chat_completion.choices[0].message.content
            final_output["response"] = final_response

    except Exception as e:
        error_message = f"Failed to format final output: {e}"
        print(error_message)
        final_output["error"] = error_message
        df = pd.DataFrame(results['rows'], columns=results['columns'])
        final_output["response"] = "Here are the results from your query:\n\n" + df.to_markdown(index=False)

    state['final_output'] = final_output
    return state