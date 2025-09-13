# SQL Agent ChatBot

A modular SQL Agent ChatBot built with Streamlit and LangChain that allows you to chat with your databases using natural language.

## Features

- 🤖 AI-powered SQL query generation and execution
- 🔒 Read-only operations with safety checks
- 📊 Support for SQLite, MySQL, and PostgreSQL
- 🎨 Clean and intuitive Streamlit interface
- 📝 Query logging and execution details
- 🔧 Environment-based configuration

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd sql-agent-chatbot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:

```bash
streamlit run main.py
```

## Project Structure

```
sql-agent-chatbot/
├── main.py              # Main application entry point
├── config.py            # Configuration management
├── database.py          # Database connection utilities
├── prompts.py           # Prompt templates
├── tools.py             # SQL execution tools
├── agent.py             # Main SQL agent implementation
├── ui.py                # Streamlit UI components
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
└── README.md           # This file
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and fill in your values:

### Required

- `GROQ_API_KEY`: Your Groq API key from [console.groq.com](https://console.groq.com/keys)

### Optional

- `MAX_QUERY_RESULTS`: Maximum number of results per query (default: 10)
- MySQL/PostgreSQL connection details

## Usage

1. Start the application with `streamlit run main.py`
2. Configure your database connection in the sidebar
3. Connect to your database
4. Start asking questions in natural language!

### Example Questions

- "Show me all tables in this database"
- "What are the top 10 records from the largest table?"
- "How many records are in each table?"
- "Show me the schema of all tables"

## Safety Features

- Read-only operations only (SELECT statements)
- Automatic LIMIT addition to prevent large result sets
- SQL injection protection
- Query validation and sanitization

## Development

The codebase is modular with clear separation of concerns:

- **config.py**: Centralized configuration management
- **database.py**: Database connection and detection utilities
- **prompts.py**: LangChain prompt templates
- **tools.py**: SQL execution tools with safety checks
- **agent.py**: Main agent implementation
- **ui.py**: Streamlit UI components
- **main.py**: Application orchestration
