from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Any, Dict, Optional, List
import os

# Import all agents
from agents import (
    db_connector,
    schema_retriever,
    query_generator,
    query_executor,
    output_parser,
    intent_agent,
    table_selection_agent,
    column_pruning_agent
)

class AgentState(TypedDict):
    # Inputs
    user_prompt: str
    db_config: Dict[str, Any]
    groq_config: Dict[str, Any]
    
    # Connection & Schema
    db_connection: Optional[Any]
    schema: Optional[str]
    pruned_schema: Optional[str]

    # Agent outputs
    intent_decision: str  # NEW: 'RELEVANT' or 'IRRELEVANT'
    intent_keywords: List[str]
    suggested_tables: List[str]
    confirmed_tables: List[str]
    sql_query: Optional[str]
    reasoning: Optional[str]
    results: Optional[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    
    # Control flow
    error: Optional[str]
    needs_user_confirmation: bool

def route_start(state: AgentState) -> str:
    """Determines the first real node to execute."""
    print("---ROUTING FROM START---")
    if state.get("confirmed_tables"):
        return "prune_columns"
    else:
        return "connect_to_db"

# --- NEW ROUTER FOR RELEVANCE ---
def route_after_intent(state: AgentState) -> str:
    """Routes to table selection if relevant, otherwise goes straight to output."""
    print("---ROUTING AFTER INTENT---")
    if state.get('intent_decision') == 'RELEVANT':
        return "select_tables"
    else:
        # If irrelevant, we skip all SQL steps and go to the final output node
        return "format_output"

def should_pause_for_confirmation(state: AgentState) -> str:
    """Determines if the graph should pause for human input."""
    if 'error' in state and state.get('error'):
        return "format_output"
    if state.get('needs_user_confirmation', False):
        return END
    return "continue"

def create_graph():
    """Creates the advanced LangGraph with relevance checking."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("connect_to_db", db_connector.connect_to_db)
    workflow.add_node("retrieve_schema", schema_retriever.retrieve_schema)
    workflow.add_node("identify_intent", intent_agent.identify_intent)
    workflow.add_node("select_tables", table_selection_agent.select_tables)
    workflow.add_node("prune_columns", column_pruning_agent.prune_columns)
    workflow.add_node("generate_sql", query_generator.generate_sql_query)
    workflow.add_node("execute_sql", query_executor.execute_sql_query)
    workflow.add_node("format_output", output_parser.format_final_output)

    # Define edges
    workflow.add_conditional_edges(START, route_start, {
        "connect_to_db": "connect_to_db",
        "prune_columns": "prune_columns",
    })

    workflow.add_edge("connect_to_db", "retrieve_schema")
    workflow.add_edge("retrieve_schema", "identify_intent")

    # --- ADD THE NEW RELEVANCE ROUTE ---
    workflow.add_conditional_edges(
        "identify_intent",
        route_after_intent,
        {
            "select_tables": "select_tables",
            "format_output": "format_output"
        }
    )

    workflow.add_conditional_edges(
        "select_tables",
        should_pause_for_confirmation,
        {
            "continue": "prune_columns",
            "format_output": "format_output",
            END: END 
        }
    )
    
    workflow.add_edge("prune_columns", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "format_output")
    workflow.add_edge("format_output", END)

    return workflow.compile()

def run_initial_pipeline(user_prompt: str, db_config: Dict):
    """Runs the pipeline until it needs user confirmation or finishes."""
    graph = create_graph()
    initial_state = {
        "user_prompt": user_prompt,
        "db_config": db_config,
        "groq_config": { "groq_api_key": os.getenv("GROQ_API_KEY"), "groq_model": os.getenv("GROQ_MODEL", "llama3-8b-8192") },
    }
    # This will now correctly handle irrelevant questions in a single run
    result = graph.invoke(initial_state)
    
    # If the graph finished (e.g., irrelevant question), we have the final output
    if END in result:
        return result
    # Otherwise, it's paused for confirmation
    else:
        return result


def run_pipeline_after_confirmation(state: AgentState):
    """Resumes the pipeline after user confirms tables."""
    graph = create_graph()
    final_state = graph.invoke(state)
    return final_state.get("final_output", {"error": "An unexpected error occurred."})

if __name__ == "__main__":
    graph = create_graph()
    try:
        graph_png_bytes = graph.get_graph().draw_mermaid_png()
        output_filename = "langgraph_diagram.png"
        with open(output_filename, "wb") as f:
            f.write(graph_png_bytes)
        print(f"Graph image saved to {os.path.abspath(output_filename)}")
    except Exception as e:
        print(f"Could not generate graph diagram. Error: {e}")