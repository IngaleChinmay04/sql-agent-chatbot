from groq import Groq
from pydantic import BaseModel, Field
import json
from typing import Dict, Any

class EnhancedPrompt(BaseModel):
    enhanced_prompt: str = Field(description="A refined, clearer version of the user's question, optimized for a text-to-SQL model.")

def enhance_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refines the user's question for clarity using an LLM.
    """
    print("---PROMPT ENHANCER---")
    if 'error' in state and state['error']:
        return state

    user_prompt = state['user_prompt']
    groq_config = state['groq_config']

    # If the prompt is already clear and concise, we can skip the LLM call.
    # This is a simple heuristic; more advanced logic could be used here.
    if len(user_prompt.split()) > 50 or len(user_prompt.split()) < 3:
         print("Prompt is too long, too short, or complex. Skipping enhancement.")
         state['enhanced_prompt'] = user_prompt
         return state

    try:
        client = Groq(api_key=groq_config['groq_api_key'])

        prompt_template = f"""
        You are an expert in refining user questions for text-to-SQL systems.
        Your task is to rephrase the following user question to be as clear and unambiguous as possible for a downstream SQL generation model.
        Return your answer as a JSON object with a single key: "enhanced_prompt".

        Original Question: "{user_prompt}"
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a prompt optimization assistant for text-to-SQL models.",
                },
                {
                    "role": "user",
                    "content": prompt_template,
                }
            ],
            model=groq_config.get('groq_model', "llama3-8b-8192"),
            temperature=0,
            response_format={"type": "json_object"},
        )

        response_json_str = chat_completion.choices[0].message.content
        print(f"Groq Response for Enhancement: {response_json_str}")

        # Parse and validate the response
        response_data = json.loads(response_json_str)
        enhanced_prompt_obj = EnhancedPrompt(**response_data)

        state['enhanced_prompt'] = enhanced_prompt_obj.enhanced_prompt
        print(f"Original Prompt: '{user_prompt}'")
        print(f"Enhanced Prompt: '{state['enhanced_prompt']}'")

    except Exception as e:
        print(f"Error during prompt enhancement: {e}. Falling back to original prompt.")
        # If enhancement fails, we fall back to the original prompt to not break the chain.
        state['enhanced_prompt'] = user_prompt
        # Optionally, you could log the error to the state
        # state['error'] = f"Prompt enhancement failed: {e}"

    return state