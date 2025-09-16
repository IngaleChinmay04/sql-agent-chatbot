"""Fixed Streamlit UI components for SQL Agent ChatBot with better table display"""
import streamlit as st
import tempfile
import os
import pandas as pd
import ast
import re
from typing import List, Dict, Any
from config import Config
from database import DatabaseConfig
from agent import SQLAgent  # Use the fixed agent
from prompts import UIPrompts

class DatabaseUI:
    """Database configuration UI components"""
    
    @staticmethod
    def show_environment_status():
        """Display environment variables status"""
        config = Config.to_dict()
        validation = Config.validate()
        
        with st.expander("🔧 Environment Status", expanded=False):
            st.write("**Environment Variables Status:**")
            st.write(f"✅ GROQ_API_KEY: {'Set' if validation['groq_api_key'] else '❌ Not Set'}")
            st.write(f"📊 GROQ_MODEL: {config['groq_model']}")
            st.write(f"📈 MAX_QUERY_RESULTS: {config['max_results']}")
            
            if config['mysql_user']:
                st.write(f"🐬 MySQL Config: {config['mysql_user']}@{config['mysql_host']}:{config['mysql_port']}")
            if config['postgres_user']:
                st.write(f"🐘 PostgreSQL Config: {config['postgres_user']}@{config['postgres_host']}:{config['postgres_port']}")
    
    @staticmethod
    def show_query_logs():
        """Display query execution logs"""
        if st.session_state.get("query_logs", []):
            with st.expander("📊 Query Logs", expanded=False):
                for i, log in enumerate(reversed(st.session_state.query_logs[-10:])):  # Show last 10
                    status = "❌" if log['error'] else "✅"
                    st.write(f"{status} **{log['timestamp']}**")
                    st.code(log['query'], language="sql")
                    if log['error']:
                        st.error(log['result_preview'])
                    else:
                        st.success(f"Result: {log['result_length']} chars")
                    st.divider()
    
    @staticmethod
    def render_database_config():
        """Render database configuration form"""
        config = Config.to_dict()
        validation = Config.validate()
        
        # Groq API Key status
        if not validation['groq_api_key']:
            st.error("❌ Groq API Key not found in environment variables")
            st.info("Please set GROQ_API_KEY in your .env file")
        else:
            st.success("✅ Groq API Key loaded from environment")
        
        # Database type selection
        db_type = st.selectbox("Database Type", ["SQLite", "MySQL", "PostgreSQL"])
        
        connection_config = None
        
        if db_type == "SQLite":
            connection_config = DatabaseUI._render_sqlite_config()
        elif db_type == "MySQL":
            connection_config = DatabaseUI._render_mysql_config(config, validation)
        elif db_type == "PostgreSQL":
            connection_config = DatabaseUI._render_postgresql_config(config, validation)
        
        return db_type, connection_config, validation['groq_api_key']
    
    @staticmethod
    def _render_sqlite_config():
        """Render SQLite configuration"""
        st.subheader("SQLite Configuration")
        
        sqlite_option = st.radio("SQLite Source", ["Upload .db file", "Enter file path"])
        
        db_file_path = None
        
        if sqlite_option == "Upload .db file":
            uploaded_file = st.file_uploader(
                "Upload SQLite database file",
                type=["db", "sqlite", "sqlite3"]
            )
            
            if uploaded_file is not None:
                # Save uploaded file to temp directory
                temp_dir = tempfile.mkdtemp()
                db_file_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(db_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.success(f"File uploaded: {uploaded_file.name}")
        else:
            db_file_path = st.text_input(
                "Database file path",
                placeholder="/path/to/your/database.db"
            )
        
        return {"file_path": db_file_path}
    
    @staticmethod
    def _render_mysql_config(config: Dict[str, Any], validation: Dict[str, bool]):
        """Render MySQL configuration"""
        st.subheader("MySQL Configuration")
        
        mysql_config = {
            "host": st.text_input("Host", value=config['mysql_host']),
            "port": st.number_input("Port", value=config['mysql_port'], min_value=1, max_value=65535),
            "user": st.text_input("Username", value=config['mysql_user'] or ""),
            "password": st.text_input("Password", 
                                    value=config['mysql_password'] or "", 
                                    type="password"),
            "database": st.text_input("Database Name", value=config['mysql_database'] or "")
        }
        
        if validation['mysql_complete']:
            st.success("✅ MySQL credentials loaded from environment")
        
        return mysql_config
    
    @staticmethod
    def _render_postgresql_config(config: Dict[str, Any], validation: Dict[str, bool]):
        """Render PostgreSQL configuration"""
        st.subheader("PostgreSQL Configuration")
        
        postgres_config = {
            "host": st.text_input("Host", value=config['postgres_host']),
            "port": st.number_input("Port", value=config['postgres_port'], min_value=1, max_value=65535),
            "user": st.text_input("Username", value=config['postgres_user'] or ""),
            "password": st.text_input("Password", 
                                    value=config['postgres_password'] or "", 
                                    type="password"),
            "database": st.text_input("Database Name", value=config['postgres_database'] or "")
        }
        
        if validation['postgres_complete']:
            st.success("✅ PostgreSQL credentials loaded from environment")
        
        return postgres_config

class ChatUI:
    """Chat interface UI components with enhanced table display"""
    
    @staticmethod
    def display_execution_details(execution_details: List[Dict]):
        """Display execution details in the frontend with enhanced table rendering"""
        if execution_details:
            with st.expander("🔍 Execution Details", expanded=False):
                for i, detail in enumerate(execution_details):
                    st.write(f"**Step {i+1}: {detail['tool']}**")
                    
                    if detail['tool'] == 'execute_sql':
                        ChatUI._display_sql_execution_enhanced(detail)
                    
                    st.divider()
    
    @staticmethod
    def _display_sql_execution_enhanced(detail: Dict):
        """Enhanced SQL execution display with better table handling"""
        output = detail['output']
        
        if "QUERY:" in output and "RESULT:" in output:
            parts = output.split("RESULT:", 1)
            query_part = parts[0].replace("QUERY:", "").strip()
            result_part = parts[1].strip()
            
            st.write("**SQL Query:**")
            st.code(query_part, language="sql")
            
            st.write("**Query Result:**")
            
            # Try to parse and display the result data
            success = ChatUI._try_display_as_table(result_part)
            
            if not success:
                # Fallback to code display
                st.code(result_part)
        else:
            # Fallback for other formats
            query = detail['input'].get('query', 'Unknown query')
            st.write("**SQL Query:**")
            st.code(query, language="sql")
            st.write("**Query Result:**")
            
            # Try to parse and display the result data
            success = ChatUI._try_display_as_table(output)
            
            if not success:
                st.code(output)
    
    @staticmethod
    def _try_display_as_table(result_text: str) -> bool:
        """Try to display result as a formatted table, return True if successful"""
        try:
            # Strategy 1: Check if it's already a markdown table
            if "|" in result_text and "Column_" in result_text:
                lines = result_text.strip().split('\n')
                if len(lines) >= 3:  # Header, separator, at least one data row
                    st.markdown(result_text)
                    return True
            
            # Strategy 2: Try to parse as list of tuples and create DataFrame
            if result_text.startswith("[(") and result_text.endswith(")]"):
                try:
                    # Clean and parse the data
                    cleaned_data = ChatUI._clean_tuple_string(result_text)
                    data = ast.literal_eval(cleaned_data)
                    
                    if isinstance(data, list) and data:
                        # Create DataFrame
                        df = pd.DataFrame(data)
                        
                        # Set generic column names
                        df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
                        
                        # Display as interactive table
                        st.dataframe(df, use_container_width=True)
                        
                        # Also display basic stats
                        st.caption(f"📊 {len(df)} rows × {len(df.columns)} columns")
                        return True
                        
                except (ValueError, SyntaxError) as e:
                    st.warning(f"Could not parse data: {e}")
            
            # Strategy 3: Check for simple table format (pipe-separated)
            lines = result_text.strip().split('\n')
            if len(lines) >= 2 and all('|' in line for line in lines[:3] if line.strip()):
                st.markdown(result_text)
                return True
            
            # Strategy 4: Try to format as simple list if it looks like data
            if result_text.startswith("[") and result_text.endswith("]"):
                try:
                    data = ast.literal_eval(result_text)
                    if isinstance(data, list) and len(data) <= 20:  # Don't show huge lists
                        for i, item in enumerate(data, 1):
                            st.write(f"{i}. {item}")
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            st.warning(f"Error displaying table: {e}")
            return False
    
    @staticmethod
    def _clean_tuple_string(data_str: str) -> str:
        """Clean tuple string for parsing"""
        try:
            # Handle Decimal objects
            cleaned = re.sub(r"Decimal\('([^']+)'\)", r"float('\1')", data_str)
            
            # Handle datetime objects - convert to string representation
            cleaned = re.sub(r"datetime\.datetime\([^)]+\)", "'[DATETIME]'", cleaned)
            
            # Handle any other objects that might cause issues
            cleaned = re.sub(r"<[^>]+>", "'[OBJECT]'", cleaned)
            
            return cleaned
            
        except Exception as e:
            st.warning(f"Error cleaning data string: {e}")
            return data_str
    
    @staticmethod
    def render_quick_actions():
        """Render quick action buttons"""
        st.subheader("🚀 Quick Actions")
        col1, col2, col3, col4 = st.columns(4)
        
        actions = {
            "📋 Show tables": "Show me all tables in this database",
            "📊 Table stats": "How many records are in each table?",
            "🔍 Recent data": "Show me sample data from the main tables with proper formatting",
            "🗑️ Clear chat": None
        }
        
        with col1:
            if st.button("📋 Show tables"):
                return actions["📋 Show tables"]
        
        with col2:
            if st.button("📊 Table stats"):
                return actions["📊 Table stats"]
        
        with col3:
            if st.button("🔍 Recent data"):
                return actions["🔍 Recent data"]
        
        with col4:
            if st.button("🗑️ Clear chat"):
                st.session_state.messages = []
                st.rerun()
        
        return None
    
    @staticmethod
    def show_setup_guide():
        """Show setup instructions when not connected"""
        st.info("👈 Please configure and connect to a database in the sidebar to start chatting.")
        
        # st.subheader("🚀 Quick Setup Guide")
        
        # Environment setup instructions
        # with st.expander("📝 Environment Setup (.env file)", expanded=True):
        #     st.markdown(UIPrompts.SETUP_INSTRUCTIONS)
        
        # Show example questions
        st.subheader("📋 Example Questions You Can Ask:")
        for example in UIPrompts.EXAMPLE_QUESTIONS:
            st.markdown(f"• {example}")
    
    @staticmethod
    def display_chat_response_enhanced(response: str, execution_details: List[Dict]):
        """Enhanced chat response display with better table rendering"""
        # Display the main response
        st.markdown(response)
        
        # Extract and display any table data from execution details
        for detail in execution_details:
            if detail.get('tool') == 'execute_sql':
                output = detail.get('output', '')
                if "RESULT:" in output:
                    result_part = output.split("RESULT:", 1)[1].strip()
                    
                    # Try to display as table in main chat area
                    if ChatUI._try_display_as_table(result_part):
                        st.success("✅ Data displayed above")
                    else:
                        # If table display failed, show a sample of the data
                        st.info("📄 Raw data (first 200 characters):")
                        st.code(result_part[:200] + "..." if len(result_part) > 200 else result_part)

class ConnectionManager:
    """Handle database connections"""
    
    @staticmethod
    def attempt_connection(db_type: str, connection_config: Dict, groq_api_key: str) -> bool:
        """Attempt to connect to database"""
        try:
            with st.spinner("Connecting to database..."):
                if db_type == "SQLite":
                    db_file_path = connection_config.get("file_path")
                    if not db_file_path or not os.path.exists(db_file_path):
                        st.error("Please provide a valid SQLite database file")
                        return False
                    
                    db = DatabaseConfig.create_sqlite_connection(db_file_path)
                    st.session_state.agent = SQLAgent(db, groq_api_key)
                    st.session_state.db_connected = True
                    st.session_state.db_schema = db.get_table_info()
                    st.success("Connected to SQLite database!")
                    return True
                
                elif db_type == "MySQL":
                    if not all(connection_config.values()):
                        st.error("Please fill in all MySQL connection details")
                        return False
                    
                    db = DatabaseConfig.create_mysql_connection(connection_config)
                    st.session_state.agent = SQLAgent(db, groq_api_key)
                    st.session_state.db_connected = True
                    st.session_state.db_schema = db.get_table_info()
                    st.success("Connected to MySQL database!")
                    return True
                
                elif db_type == "PostgreSQL":
                    if not all(connection_config.values()):
                        st.error("Please fill in all PostgreSQL connection details")
                        return False
                    
                    db = DatabaseConfig.create_postgresql_connection(connection_config)
                    st.session_state.agent = SQLAgent(db, groq_api_key)
                    st.session_state.db_connected = True
                    st.session_state.db_schema = db.get_table_info()
                    st.success("Connected to PostgreSQL database!")
                    return True
        
        except Exception as e:
            error_msg = f"Failed to connect: {str(e)}"
            st.error(error_msg)
            return False
        
        return False
    
    @staticmethod
    def disconnect():
        """Disconnect from database"""
        st.session_state.db_connected = False
        st.session_state.agent = None
        st.session_state.db_schema = None
        st.session_state.messages = []
        st.session_state.query_logs = []
        st.success("Disconnected from database")
        st.rerun()