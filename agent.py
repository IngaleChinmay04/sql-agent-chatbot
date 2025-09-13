"""Fixed SQL Agent implementation for ChatBot"""
import logging
from typing import List, Dict, Tuple
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentExecutor, create_tool_calling_agent
from config import Config
from database import DatabaseDetector
from prompts import PromptTemplates
from tools import SQLExecutor, create_sql_tool, QueryLogger

logger = logging.getLogger(__name__)

class SQLAgent:
    """SQL Agent with safety checks and detailed logging"""
    
    def __init__(self, db: SQLDatabase, groq_api_key: str = None):
        self.db = db
        self.schema = db.get_table_info()
        self.db_type = DatabaseDetector.detect_db_type(db)
        
        logger.info(f"Initializing SQLAgent with database type: {self.db_type}")
        
        # Use provided API key or fall back to config
        api_key = groq_api_key or Config.GROQ_API_KEY
        if not api_key:
            raise ValueError("Groq API key not provided and not found in configuration")
        
        logger.info(f"Using Groq model: {Config.GROQ_MODEL}")
        
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=api_key,
            model=Config.GROQ_MODEL,
            temperature=0,
            max_tokens=None,
            timeout=30,
            max_retries=2,
        )
        
        # Initialize SQL executor with improved handling
        self.sql_executor = SQLExecutor(self.db, self.db_type)
        
        # Create agent
        self._create_agent()
    
    def _create_agent(self):
        """Create the SQL agent using the new LangChain API"""
        
        # Create the tools list
        sql_tool = create_sql_tool(self.sql_executor)
        tools = [sql_tool]
        
        # Get database-specific guidance
        db_guidance = DatabaseDetector.get_db_guidance(self.db_type)
        
        # Create the prompt template
        prompt = PromptTemplates.create_sql_agent_prompt(
            self.db_type, self.schema, db_guidance
        )
        
        # Create the agent
        agent = create_tool_calling_agent(self.llm, tools, prompt)
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=False,
            max_iterations=5,
            max_execution_time=60,
            return_intermediate_steps=True
        )
    
    def chat(self, question: str) -> Tuple[str, List[Dict]]:
        """Chat with the SQL agent and return response with execution details"""
        logger.info(f"Processing user question: {question}")
        
        try:
            result = self.agent_executor.invoke({
                "input": question,
                "chat_history": []
            })
            
            response = result.get("output", "No response generated.")
            intermediate_steps = result.get("intermediate_steps", [])
            
            # Log the execution details
            execution_details = []
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    if hasattr(action, 'tool') and hasattr(action, 'tool_input'):
                        execution_details.append({
                            "tool": action.tool,
                            "input": action.tool_input,
                            "output": observation
                        })
                        
                        # Log query execution if it's SQL
                        if action.tool == 'execute_sql':
                            query = action.tool_input.get('query', '')
                            error = observation.startswith('Error:')
                            QueryLogger.log_query_execution(
                                query, observation, self.db_type, error
                            )
            
            logger.info(f"Agent completed processing. Response length: {len(response)}")
            return response, execution_details
                
        except Exception as e:
            error_msg = f"Error during chat: {str(e)}"
            logger.error(error_msg)
            return error_msg, []
    
    def get_db_info(self) -> Dict[str, str]:
        """Get database information"""
        return {
            "type": self.db_type,
            "schema": self.schema,
            "tables_count": len(self.schema.split("CREATE TABLE")) - 1
        }
    
    def test_query(self, query: str) -> str:
        """Test a query directly for debugging"""
        try:
            result = self.sql_executor.execute_query(query)
            return result
        except Exception as e:
            return f"Error testing query: {str(e)}"