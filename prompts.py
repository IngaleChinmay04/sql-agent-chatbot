"""Prompt templates for SQL Agent ChatBot"""
from langchain_core.prompts import ChatPromptTemplate
from config import Config

class PromptTemplates:
    """SQL Agent prompt templates"""
    
    @staticmethod
    def create_sql_agent_prompt(db_type: str, schema: str, db_guidance: str) -> ChatPromptTemplate:
        """Create the main SQL agent prompt template"""
        
        system_message = f"""You are a helpful SQL analyst assistant.

Database Type: {db_type.upper()}
Database Schema:
{schema}

{db_guidance}

Rules:
- Only generate SELECT statements
- Think step-by-step before writing queries
- If you get an error, analyze it and try to fix the query
- For listing tables, use the appropriate query for {db_type}:
  * SQLite: SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
  * MySQL: SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
  * PostgreSQL: SELECT tablename FROM pg_tables WHERE schemaname = 'public'
- Limit results to {Config.MAX_QUERY_RESULTS} rows unless specifically asked for more
- Use proper SQL syntax for {db_type}
- Provide clear explanations of your queries
- If the tool returns 'Error:', revise the SQL and try again
- Maximum 3 attempts per question
- Always show the SQL query you're executing in code blocks
- Be helpful and explain the results in a user-friendly way
- For counting or aggregation queries, you don't need LIMIT
- When showing data results, ALWAYS include the formatted data tables in your response
- IMPORTANT: When the execute_sql tool returns formatted data, include that formatted data in your response
- Don't just say "shown above" - actually include the data tables in your response
- Format your response to include both explanation and the actual data
- Use markdown formatting to make tables readable"""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

class UIPrompts:
    """UI-related prompts and text"""
    
    SETUP_INSTRUCTIONS = """
    Create a `.env` file in your project directory with the following variables:
    
    ```bash
    # Groq Configuration (Required)
    GROQ_API_KEY=your_groq_api_key_here
    GROQ_MODEL=llama3-70b-8192
    MAX_QUERY_RESULTS=10
    
    # MySQL Configuration (optional)
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=your_mysql_username
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_DATABASE=your_database_name
    
    # PostgreSQL Configuration (optional)
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=your_postgres_username
    POSTGRES_PASSWORD=your_postgres_password
    POSTGRES_DATABASE=your_database_name
    ```
    
    **Get your Groq API key:** [https://console.groq.com/keys](https://console.groq.com/keys)
    """
    
    EXAMPLE_QUESTIONS = [
        "Show me all tables in this database",
        "What are the top 10 records from the largest table?",
        "How many records are in each table?",
        "Show me the schema of all tables",
        "What's the most recent data in the database?",
        "Find tables with more than 1000 records",
        "Show me columns that might contain dates"
    ]