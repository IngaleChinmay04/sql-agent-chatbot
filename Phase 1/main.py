"""Enhanced main application for SQL Agent ChatBot with better table display"""
import streamlit as st
import logging
from config import Config
from ui import DatabaseUI, ChatUI, ConnectionManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="SQL Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
    default_states = {
        "messages": [],
        "db_connected": False,
        "agent": None,
        "db_schema": None,
        "query_logs": []
    }
    
    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_sidebar():
    """Render the sidebar with database configuration"""
    with st.sidebar:
        st.header("⚙️ Database Configuration")
        
        # Show environment status
        DatabaseUI.show_environment_status()
        
        # Show query logs
        DatabaseUI.show_query_logs()
        
        # Database configuration form
        db_type, connection_config, has_groq_key = DatabaseUI.render_database_config()
        
        # Connect button
        if st.button("🔌 Connect to Database", type="primary"):
            if not has_groq_key:
                st.error("Please set GROQ_API_KEY in your .env file")
            else:
                ConnectionManager.attempt_connection(db_type, connection_config, Config.GROQ_API_KEY)
        
        # Disconnect button
        if st.session_state.db_connected:
            if st.button("🔌 Disconnect", type="secondary"):
                ConnectionManager.disconnect()

def render_main_content():
    """Render the main content area"""
    st.title("🤖 SQL Agent Chat Interface")
    st.markdown("Connect to your database and chat with an AI agent that can answer questions using SQL queries.")
    
    if not st.session_state.db_connected:
        ChatUI.show_setup_guide()
    else:
        render_chat_interface()

def render_chat_interface():
    """Render the chat interface when connected"""
    # Database schema info
    with st.expander("📊 Database Schema", expanded=False):
        if st.session_state.db_schema:
            st.code(st.session_state.db_schema, language="sql")
    
    # Debug section for testing
    with st.expander("🔧 Debug Tools", expanded=False):
        st.write("**Test Query Execution**")
        test_query = st.text_input("Enter a test query:", placeholder="SELECT * FROM customers LIMIT 5")
        if st.button("Test Query") and test_query and st.session_state.agent:
            with st.spinner("Testing query..."):
                result = st.session_state.agent.test_query(test_query)
                st.write("**Test Result:**")
                
                # Try to display as table
                if "RESULT:" in result:
                    result_part = result.split("RESULT:", 1)[1].strip()
                    success = ChatUI._try_display_as_table(result_part)
                    if not success:
                        st.code(result)
                else:
                    st.code(result)
    
    # Chat interface
    st.subheader("💬 Chat with your database")
    
    # Display chat messages with enhanced rendering
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "execution_details" in message:
                # Use enhanced display for assistant messages
                ChatUI.display_chat_response_enhanced(
                    message["content"], 
                    message["execution_details"]
                )
                
                # Show execution details in expander
                ChatUI.display_execution_details(message["execution_details"])
            else:
                # Regular display for user messages
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your database..."):
        handle_user_input(prompt)
    
    # Quick action buttons
    quick_action = ChatUI.render_quick_actions()
    if quick_action:
        handle_user_input(quick_action)

def handle_user_input(prompt: str):
    """Handle user input and get AI response with enhanced display"""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, execution_details = st.session_state.agent.chat(prompt)
            
            # Use enhanced display for the response
            ChatUI.display_chat_response_enhanced(response, execution_details)
            
            # Show execution details
            ChatUI.display_execution_details(execution_details)
            
            # Store message with execution details
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "execution_details": execution_details
            })

def main():
    """Main application function"""
    initialize_session_state()
    render_sidebar()
    render_main_content()

if __name__ == "__main__":
    main()