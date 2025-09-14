"""Fixed SQL execution tools for SQL Agent ChatBot with better result handling"""
import re
import logging
import pandas as pd
import ast
import json
from typing import Tuple, Optional, List, Any, Union
from datetime import datetime
from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase
from config import Config

logger = logging.getLogger(__name__)

class SQLExecutor:
    """SQL query execution with safety checks and improved result handling"""
    
    def __init__(self, db: SQLDatabase, db_type: str):
        self.db = db
        self.db_type = db_type
        
        # Safety patterns
        self.deny_re = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE|GRANT|REVOKE)\b", re.I)
        self.has_limit_tail_re = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")
    
    def _safe_sql(self, query: str, max_results: int = None) -> str:
        """Ensure SQL query is safe for execution"""
        if max_results is None:
            max_results = Config.MAX_QUERY_RESULTS
            
        logger.info(f"Validating SQL query: {query[:100]}...")
        
        query = query.strip()
        
        # Block multiple statements
        if query.count(";") > 1 or (query.endswith(";") and ";" in query[:-1]):
            logger.warning("Blocked multiple statements")
            return "Error: multiple statements are not allowed."
        query = query.rstrip(";").strip()

        # Read-only gate
        if not query.lower().startswith("select"):
            logger.warning(f"Blocked non-SELECT statement: {query[:50]}")
            return "Error: only SELECT statements are allowed."
        if self.deny_re.search(query):
            logger.warning(f"Blocked DML/DDL statement: {query[:50]}")
            return "Error: DML/DDL detected. Only read-only queries are permitted."

        # Special cases where we don't want to add LIMIT automatically
        no_limit_patterns = [
            "information_schema.tables",
            "sqlite_master",
            "pg_tables",
            "count(*)",
            "group by",
            "having"
        ]
        
        should_add_limit = not any(pattern in query.lower() for pattern in no_limit_patterns)
        
        # Add LIMIT if not present and query should have one
        if not self.has_limit_tail_re.search(query) and should_add_limit:
            query += f" LIMIT {max_results}"
            logger.info(f"Added LIMIT {max_results} to query")
        
        logger.info(f"Query validated successfully: {query}")
        return query
    
    def execute_query(self, query: str) -> str:
        """Execute a READ-ONLY SQL query and return results"""
        logger.info(f"Executing SQL query: {query}")
        
        safe_query = self._safe_sql(query)
        if safe_query.startswith("Error:"):
            return safe_query
        
        try:
            # Execute the query and get raw result
            result = self.db.run(safe_query)
            logger.info(f"Raw result type: {type(result)}")
            logger.info(f"Raw result preview: {str(result)[:200]}...")
            
            # Handle the result based on its type
            formatted_result = self._handle_query_result(result, safe_query)
            
            logger.info(f"Query executed successfully. Formatted result length: {len(formatted_result)}")
            
            # Return formatted result with query
            return f"QUERY: {safe_query}\n\nRESULT:\n{formatted_result}"
            
        except Exception as e:
            error_msg = f"Error: {e}"
            logger.error(f"Query execution failed: {e}")
            return error_msg
    
    def _handle_query_result(self, result: Any, query: str) -> str:
        """Handle different types of query results"""
        try:
            # Case 1: Result is already a list of tuples/rows
            if isinstance(result, list):
                return self._format_list_result(result, query)
            
            # Case 2: Result is a string representation
            elif isinstance(result, str):
                return self._parse_string_result(result, query)
            
            # Case 3: Result is a pandas DataFrame
            elif hasattr(result, 'to_dict'):
                return self._format_dataframe_result(result)
            
            # Case 4: Other types - convert to string
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
                return str(result)
                
        except Exception as e:
            logger.error(f"Error handling query result: {e}")
            return f"Error formatting result: {str(e)}\nRaw result: {str(result)[:500]}..."
    
    def _format_list_result(self, result: List, query: str) -> str:
        """Format a list result into a readable table"""
        try:
            if not result:
                return "No data returned"
            
            # Convert to DataFrame for better formatting
            df = pd.DataFrame(result)
            
            # Try to get column names from the query
            column_names = self._extract_column_names_from_query(query, len(df.columns))
            if column_names:
                df.columns = column_names
            else:
                df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
            
            # Format as markdown table
            try:
                return df.to_markdown(index=False, tablefmt='pipe')
            except ImportError:
                # Fallback if tabulate is not available
                return self._format_dataframe_basic(df)
                
        except Exception as e:
            logger.error(f"Error formatting list result: {e}")
            # Fallback to simple string representation
            formatted_rows = []
            for i, row in enumerate(result[:10]):  # Limit to first 10 rows
                formatted_rows.append(f"Row {i+1}: {row}")
            return "\n".join(formatted_rows)
    
    def _parse_string_result(self, result_str: str, query: str) -> str:
        """Parse string result with multiple strategies"""
        try:
            # Strategy 1: Try to evaluate as Python literal
            if result_str.startswith("[") and result_str.endswith("]"):
                try:
                    # Clean the string of any problematic content
                    cleaned_str = self._clean_result_string(result_str)
                    data = ast.literal_eval(cleaned_str)
                    return self._format_list_result(data, query)
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"ast.literal_eval failed: {e}")
            
            # Strategy 2: Try JSON parsing
            try:
                data = json.loads(result_str)
                return self._format_list_result(data, query)
            except json.JSONDecodeError:
                logger.warning("JSON parsing failed")
            
            # Strategy 3: Parse as delimited text
            lines = result_str.strip().split('\n')
            if len(lines) > 1:
                return self._parse_delimited_text(lines, query)
            
            # Strategy 4: Return as-is if single line
            return result_str
            
        except Exception as e:
            logger.error(f"Error parsing string result: {e}")
            return result_str
    
    def _clean_result_string(self, result_str: str) -> str:
        """Clean result string of problematic content"""
        try:
            # Remove any ast.Call objects or similar problematic content
            import re
            
            # Pattern to match problematic AST objects
            ast_pattern = r'<ast\.\w+\s+object\s+at\s+0x[0-9a-fA-F]+>'
            cleaned = re.sub(ast_pattern, '"[OBJECT]"', result_str)
            
            # Additional cleaning patterns
            patterns_to_clean = [
                (r'<[\w\.]+\s+object\s+at\s+0x[0-9a-fA-F]+>', '"[OBJECT]"'),
                (r'Decimal\([\'"]([0-9\.]+)[\'"]\)', r'\1'),  # Handle Decimal objects
                (r'datetime\.datetime\([^)]+\)', '"[DATETIME]"'),  # Handle datetime objects
            ]
            
            for pattern, replacement in patterns_to_clean:
                cleaned = re.sub(pattern, replacement, cleaned)
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Error cleaning result string: {e}")
            return result_str
    
    def _parse_delimited_text(self, lines: List[str], query: str) -> str:
        """Parse delimited text into table format"""
        try:
            data = []
            for line in lines:
                if line.strip():
                    # Try different delimiters
                    if '\t' in line:
                        row = line.split('\t')
                    elif '|' in line:
                        row = line.split('|')
                    elif ',' in line:
                        row = line.split(',')
                    else:
                        row = [line]
                    
                    # Clean up the row
                    row = [cell.strip() for cell in row if cell.strip()]
                    if row:
                        data.append(row)
            
            if data:
                return self._format_list_result(data, query)
            else:
                return "No valid data found"
                
        except Exception as e:
            logger.error(f"Error parsing delimited text: {e}")
            return "\n".join(lines)
    
    def _format_dataframe_result(self, df) -> str:
        """Format DataFrame result"""
        try:
            return df.to_markdown(index=False, tablefmt='pipe')
        except ImportError:
            return self._format_dataframe_basic(df)
        except Exception as e:
            logger.error(f"Error formatting DataFrame: {e}")
            return str(df)
    
    def _format_dataframe_basic(self, df: pd.DataFrame) -> str:
        """Basic DataFrame formatting without tabulate dependency"""
        try:
            lines = []
            
            # Header
            header = " | ".join(str(col) for col in df.columns)
            lines.append(header)
            lines.append("-" * len(header))
            
            # Data rows (limit to first 20 rows)
            for _, row in df.head(20).iterrows():
                row_str = " | ".join(str(val) for val in row)
                lines.append(row_str)
            
            if len(df) > 20:
                lines.append(f"... and {len(df) - 20} more rows")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error in basic DataFrame formatting: {e}")
            return str(df)
    
    def _extract_column_names_from_query(self, query: str, num_columns: int) -> Optional[List[str]]:
        """Extract column names from SQL query"""
        try:
            query_upper = query.upper()
            if "SELECT" in query_upper and "FROM" in query_upper:
                select_part = query_upper.split("FROM")[0].replace("SELECT", "").strip()
                
                if select_part == "*":
                    return None  # Will use generic names
                else:
                    # Extract column names
                    columns = []
                    for col in select_part.split(","):
                        col = col.strip()
                        # Handle aliases (AS keyword)
                        if " AS " in col:
                            col = col.split(" AS ")[1].strip()
                        # Handle simple aliases (space)
                        elif " " in col and not any(func in col for func in ["COUNT", "SUM", "AVG", "MIN", "MAX"]):
                            parts = col.split()
                            col = parts[-1]
                        columns.append(col)
                    
                    # Return only if we have the right number of columns
                    if len(columns) == num_columns:
                        return columns
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting column names: {e}")
            return None

def create_sql_tool(sql_executor: SQLExecutor):
    """Create the SQL execution tool"""
    
    @tool
    def execute_sql(query: str) -> str:
        """Execute a READ-ONLY SQL query and return results."""
        return sql_executor.execute_query(query)
    
    return execute_sql

class QueryLogger:
    """Handle query logging for debugging and monitoring"""
    
    @staticmethod
    def log_query_execution(query: str, result: str, db_type: str, error: bool = False):
        """Log query execution details"""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "result_preview": result[:200] + "..." if len(result) > 200 else result,
            "result_length": len(result),
            "error": error,
            "db_type": db_type
        }
        
        # Add to session state for frontend display
        try:
            import streamlit as st
            if "query_logs" in st.session_state:
                st.session_state.query_logs.append(log_entry)
                # Keep only last 50 queries
                if len(st.session_state.query_logs) > 50:
                    st.session_state.query_logs = st.session_state.query_logs[-50:]
        except ImportError:
            # If streamlit is not available, just log to console
            pass
        
        # Log to console/file
        if error:
            logger.error(f"Query failed: {query} | Error: {result}")
        else:
            logger.info(f"Query executed successfully: {query} | Result length: {len(result)}")

# Alternative direct result formatting function for immediate use
def format_query_result_direct(result: Any, query: str = "") -> str:
    """Direct formatting function that can handle various result types"""
    try:
        # Log the result type and content for debugging
        logger.info(f"Formatting result of type: {type(result)}")
        logger.info(f"Result content preview: {str(result)[:100]}...")
        
        # Handle list results (most common)
        if isinstance(result, list):
            if not result:
                return "No data returned"
            
            # Try to create a DataFrame
            try:
                df = pd.DataFrame(result)
                
                # Simple column naming
                df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
                
                # Format as simple table
                lines = []
                
                # Header
                header = " | ".join(df.columns)
                lines.append(header)
                lines.append("-" * len(header))
                
                # Data rows (limit to 20)
                for _, row in df.head(20).iterrows():
                    row_str = " | ".join(str(val) for val in row)
                    lines.append(row_str)
                
                if len(df) > 20:
                    lines.append(f"... and {len(df) - 20} more rows")
                
                return "\n".join(lines)
                
            except Exception as e:
                logger.warning(f"DataFrame creation failed: {e}")
                # Fallback to simple list formatting
                formatted = []
                for i, row in enumerate(result[:10]):
                    formatted.append(f"Row {i+1}: {row}")
                return "\n".join(formatted)
        
        # Handle string results
        elif isinstance(result, str):
            return result
        
        # Handle other types
        else:
            return str(result)
            
    except Exception as e:
        logger.error(f"Error in direct result formatting: {e}")
        return f"Error formatting result: {str(e)}\nRaw: {str(result)[:200]}..."