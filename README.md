# ISATRecruiter 
A tool that helps prospective and current students find their way in the ISAT program. Built using AI & RAG to create ISAT-advisor style responses to questions augmented with information from ISAT resources (ABET, course catalog, ISAT website).

## Prerequisites

- Python 3.11
- PostgreSQL (with pgvector extension)
- Node.js (for frontend)
- npm or yarn

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AI_RAG
```

### 2. Database Setup

Make sure PostgreSQL is running. The database will be created automatically on first run!

The database connection uses these defaults (no configuration needed):
- Host: `localhost`
- Port: `5432`
- Database: `isat_recruiter` (created automatically)
- User: `postgres`
- Password: (empty)

If your setup differs, you can override these with environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

**Note:** The database and required tables are created automatically when you first run the application. The pgvector extension is also enabled automatically.

### 3. Python Environment Setup

Create and activate a virtual environment:

```bash
# Create virtual environment
python3.11 -m venv ISATRecruiter

# Activate virtual environment
# On macOS/Linux:
source ISATRecruiter/bin/activate
# On Windows:
# ISATRecruiter\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 4. Frontend Setup

Navigate to the Frontend directory and install dependencies:

```bash
cd Frontend
npm install
cd ..
```

### 5. Environment Variables

Create a `.env` file in the project root with your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-key-here
```

**Note:** The `.env` file is already in `.gitignore` and will not be committed to the repository.

### 6. Run the Application

Start the Next.js frontend server:

```bash
cd Frontend
npm run dev
```

The application will be available at `http://localhost:3000`

## Project Structure

- `LangGraph/` - Main RAG workflow and chat processing
- `database/` - PostgreSQL database connection and operations
- `chunking/` - Text chunking and embedding generation
- `scrape/` - Web scraping utilities
- `Frontend/` - Next.js React frontend
- `tests/` - Test suite

## Notes

- The database tables (`pages`, `chunks`, `courses`) are created automatically on first connection
- Make sure PostgreSQL is running before starting the application
- The virtual environment (`ISATRecruiter/`) should be activated when running Python scripts
