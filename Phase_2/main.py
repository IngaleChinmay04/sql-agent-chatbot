"""
Main application for the Advanced SQL Agent, with a fix for the multiselect options.
"""
import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
import re 

# --- Backend Imports ---
from langraph_main import create_graph, run_initial_pipeline, run_pipeline_after_confirmation
from utils.db_utils import get_db_connection
from streamlit_mermaid import st_mermaid

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration Class ---
class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- UI and Connection Helper Classes ---
class DatabaseUI:
    @staticmethod
    def render_database_config():
        db_type = st.selectbox("Database Type", ["mysql", "postgres", "sqlite"], index=0)
        db_config = {"db_type": db_type}
        if db_type == "mysql":
            db_config.update({
                "mysql_host": st.text_input("Host", os.getenv("MYSQL_HOST", "localhost")),
                "mysql_port": st.text_input("Port", os.getenv("MYSQL_PORT", "3306")),
                "mysql_user": st.text_input("User", os.getenv("MYSQL_USER", "root")),
                "mysql_password": st.text_input("Password", type="password", value=os.getenv("MYSQL_PASSWORD")),
                "mysql_database": st.text_input("Database", os.getenv("MYSQL_DATABASE"))
            })
        return db_config

class ChatUI:
    @staticmethod
    def display_execution_details(details):
        with st.expander("Show Execution Details", expanded=False):
            st.code(details.get('sql_query', 'No SQL Query Generated.'), language="sql")
            st.info(f"**Reasoning:** {details.get('reasoning', 'No reasoning provided.')}")

class ConnectionManager:
    @staticmethod
    def attempt_connection(db_config):
        try:
            with st.spinner("Connecting and fetching schema..."):
                db = get_db_connection(db_config)
                schema = db.get_table_info()
                st.session_state.db_connected = True
                st.session_state.db_config = db_config
                st.session_state.db_schema = schema
                st.sidebar.success("Connection successful!")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Connection failed: {e}")

    @staticmethod
    def disconnect():
        keys_to_reset = ["db_connected", "db_config", "db_schema", "messages", "current_graph_state", "new_prompt"]
        for key in keys_to_reset:
            st.session_state[key] = None
        initialize_session_state()
        st.rerun()

# --- Main Application Logic ---
st.set_page_config(page_title="SQL Agent Chat", page_icon="🤖", layout="wide")

def initialize_session_state():
    defaults = {
        "messages": [], "db_connected": False, "db_config": None, "db_schema": None,
        "query_logs": [], "current_graph_state": None, "new_prompt": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Database Configuration")
        if st.session_state.db_connected:
            st.success(f"Connected to `{st.session_state.db_config['db_type']}`")
            if st.button("🔌 Disconnect", use_container_width=True):
                ConnectionManager.disconnect()
        else:
            db_config = DatabaseUI.render_database_config()
            if st.button("🔌 Connect to Database", type="primary", use_container_width=True):
                if not Config.GROQ_API_KEY:
                    st.error("Please set GROQ_API_KEY in your .env file")
                else:
                    ConnectionManager.attempt_connection(db_config)

def render_main_content():
    st.title("🤖 SQL Agent Chat Interface")
    if not st.session_state.db_connected:
        st.info("Please connect to a database using the sidebar to begin chatting.")
        return
    render_chat_interface()

def render_chat_interface():
    with st.expander("👁️ View Agent Architecture"):
        st_mermaid(create_graph().get_graph().draw_mermaid(), height="500px")
    with st.expander("📊 View Database Schema"):
        st.code(st.session_state.db_schema, language="sql")

    st.subheader("💬 Chat with your database")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("details"):
                ChatUI.display_execution_details(msg["details"])

    if st.session_state.new_prompt:
        prompt_to_process = st.session_state.new_prompt
        st.session_state.new_prompt = None
        with st.spinner("Agent is analyzing your request... (Phase 1: Selecting Tables)"):
            graph_state = run_initial_pipeline(prompt_to_process, st.session_state.db_config)
            st.session_state.current_graph_state = graph_state
        st.rerun()

    elif st.session_state.current_graph_state and st.session_state.current_graph_state.get('needs_user_confirmation'):
        handle_table_confirmation_step()
    
    else:
        if prompt := st.chat_input("Ask a question about your database..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.new_prompt = prompt
            st.rerun()

def handle_table_confirmation_step():
    state = st.session_state.current_graph_state
    suggested_tables = state.get('suggested_tables', [])
    
    with st.chat_message("assistant"):
        st.markdown("I suggest using the following tables. Please review and confirm to continue.")
        with st.form("table_confirmation_form"):
            
            schema_string = state.get('schema', '')
            all_tables = re.findall(r"CREATE TABLE `?(\w+)`?", schema_string)

            confirmed_tables = st.multiselect(
                "Select or modify the tables for the query:",
                options=all_tables,
                default=suggested_tables
            )
            
            if st.form_submit_button("✅ Confirm and Generate SQL"):
                state['confirmed_tables'] = confirmed_tables
                state['needs_user_confirmation'] = False
                
                with st.spinner("Agent is generating and executing the SQL query... (Phase 2)"):
                    final_result = run_pipeline_after_confirmation(state)
                
                # --- THE FINAL UI FIX ---
                # Display the 'response' which is now a pre-formatted Markdown table.
                response_content = final_result.get("response", "No response generated.")
                
                if "error" in final_result and final_result["error"]:
                    st.error(response_content)
                else:
                    st.markdown(response_content) # Use st.markdown to render the table

                st.session_state.messages.append({"role": "assistant", "content": response_content, "details": final_result})
                st.session_state.current_graph_state = None
                st.rerun()

# --- Main App Execution ---
if __name__ == "__main__":
    initialize_session_state()
    render_sidebar()
    render_main_content()