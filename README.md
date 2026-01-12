# Sherlock

Image Knowledge Extraction System - A web application that ingests images, extracts content using vision-enabled LLMs, stores structured data with vector embeddings, and provides RAG capabilities through an MCP-compatible API.

## Overview

Sherlock transforms visual content into searchable knowledge. Upload images from various sources, and Sherlock will:

1. **Extract** text and information using vision LLMs (GPT-4o, Claude, Gemini, Ollama)
2. **Categorize** content automatically based on configurable tags
3. **Vectorize** extracted content for semantic search
4. **Serve** knowledge through a React UI and MCP-compatible API

## Features

- **Multi-source Image Ingestion**
  - Web URLs
  - Google Drive (files and folders)
  - Local filesystem

- **Vision LLM Support**
  - OpenAI GPT-4o (default)
  - Anthropic Claude
  - Google Gemini
  - Ollama (local models)

- **Knowledge Management**
  - Automatic categorization and tagging
  - Raw and paraphrased content extraction
  - Vector embeddings for semantic search
  - Full-text search capabilities

- **MCP Integration**
  - Model Context Protocol compatible API
  - Use with Claude Code, Claude Desktop, or custom MCP clients
  - Natural language knowledge queries

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React, TypeScript, Vite, Lucide React |
| **Backend** | Python, FastAPI, Pydantic |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **LLMs** | OpenAI, Anthropic, Google, Ollama |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Deployment** | Fly.io |

## Project Structure

```
sherlock/
├── backend/                 # FastAPI backend
│   ├── api/                 # Route handlers
│   │   └── routes/          # Endpoint definitions
│   ├── services/            # Business logic & LLM integrations
│   ├── db/                  # Database models & repositories
│   ├── schemas/             # Request/response schemas
│   ├── utils/               # Helper functions
│   ├── settings/            # Configuration
│   ├── exceptions/          # Custom errors
│   └── main.py              # Application entry
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client
│   │   ├── hooks/           # Custom hooks
│   │   └── utils/           # Helper functions
│   └── index.html
│
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Supabase account
- API keys for LLM providers

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your backend URL

# Run development server
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## MCP Integration

Connect Sherlock to Claude Code or other MCP clients:

```json
{
  "mcpServers": {
    "sherlock": {
      "url": "http://localhost:8000/api/mcp/sse",
      "transport": "sse"
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_knowledge` | Search knowledge base using natural language |
| `get_knowledge_by_id` | Retrieve specific document by ID |
| `list_categories` | List all categories, subcategories, and topics |

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/ingest` | Ingest images |
| `GET` | `/api/knowledge` | Query knowledge (paginated) |
| `POST` | `/api/knowledge/{id}/retry` | Retry failed ingestion |
| `GET` | `/api/config/tags` | Get category configuration |
| `GET` | `/api/config/llms` | Get LLM configuration |
| `GET` | `/api/mcp/sse` | MCP SSE endpoint |

## Environment Variables

### Backend (.env)

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434

# Google Drive (optional)
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_TOKEN_PATH=token.pickle

# Settings
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
DEBUG=true
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

## Database Schema

### Knowledge Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `category` | TEXT | Content category |
| `subcategory` | TEXT | Content subcategory |
| `topic` | TEXT | Content topic |
| `title` | TEXT | Generated title |
| `raw_data` | TEXT | Extracted raw text |
| `paraphrased_data` | TEXT | Paraphrased content |
| `image` | TEXT | Source image URL |
| `status` | TEXT | pending/processing/completed/failed |
| `embedding` | VECTOR(1536) | Content embedding |
| `created_at` | TIMESTAMP | Creation timestamp |

## Deployment

### Fly.io

```bash
# Backend
cd backend
fly launch
fly secrets set SUPABASE_URL=... SUPABASE_KEY=... OPENAI_API_KEY=...
fly deploy

# Frontend
cd frontend
fly launch
fly deploy
```

## Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Code Quality

```bash
# Backend
ruff format .
ruff check --fix .

# Frontend
npm run lint
npm run format
```

## License

Proprietary - All rights reserved.
