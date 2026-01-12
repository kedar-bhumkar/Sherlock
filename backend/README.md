# Sherlock Backend

Image Knowledge Extraction System - A FastAPI backend that ingests images, extracts content using vision-enabled LLMs, and provides RAG capabilities through an MCP-compatible API.

## Features

- **Image Ingestion**: Support for web URLs, Google Drive links, and local folders
- **Vision LLM Extraction**: Extract text from images using GPT-4o, Claude, Gemini, or Ollama
- **Vector Embeddings**: Store and search content using Supabase pgvector
- **MCP Server**: Model Context Protocol compatible API for RAG queries
- **Retry & Resilience**: Exponential backoff with jitter for all retryable operations

## Tech Stack

- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL + pgvector)
- **LLM Providers**: OpenAI, Anthropic, Google, Ollama
- **Embeddings**: OpenAI text-embedding-3-small

## Project Structure

```
backend/
├── api/              # FastAPI routes and endpoints
│   └── routes/       # Route handlers (ingest, knowledge, config, mcp)
├── services/         # Business logic and LLM integrations
├── utils/            # Helper functions (retry, image processing)
├── db/               # Database models, repositories, and client
│   ├── models/       # Pydantic models
│   └── repositories/ # Data access layer
├── schemas/          # Request/response schemas
├── settings/         # Configuration management
├── exceptions/       # Custom error handling
└── main.py           # Application entry point
```

## Setup

### Prerequisites

- Python 3.10+
- Supabase account with pgvector extension enabled
- API keys for LLM providers (OpenAI, Anthropic, Google)
- Google Cloud credentials for Drive integration (optional)

### Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Run the server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Health Check
```
GET /health
```

### Ingestion
```
POST /api/ingest
```
Ingest images from URL, Google Drive, or local folder.

### Knowledge
```
GET /api/knowledge
```
Query extracted knowledge with filtering and pagination.

```
POST /api/knowledge/{id}/retry
```
Retry a failed ingestion.

### MCP (Model Context Protocol)
```
GET /api/mcp/sse
```
Server-Sent Events endpoint for MCP clients.

### Config
```
GET /api/config/tags
GET /api/config/llms
```
Retrieve category tags and LLM configurations.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase anon/service key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key | No |
| `GOOGLE_API_KEY` | Google AI API key | No |
| `OLLAMA_BASE_URL` | Ollama server URL | No |
| `RETRY_MAX_ATTEMPTS` | Max retry attempts (default: 3) | No |
| `RETRY_BASE_DELAY` | Base delay in seconds (default: 1.0) | No |
| `DEBUG` | Enable debug mode | No |

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
| `status` | TEXT | Processing status |
| `embedding` | VECTOR(1536) | Content embedding |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

## MCP Integration

Connect to Sherlock from Claude Code or other MCP clients:

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

Available MCP tools:
- `search_knowledge`: Search the knowledge base using natural language
- `get_knowledge_by_id`: Retrieve a specific document by ID
- `list_categories`: List all categories, subcategories, and topics

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
ruff format .
ruff check --fix .
```

## Deployment

Deploy to Fly.io:
```bash
fly launch
fly secrets set SUPABASE_URL=... SUPABASE_KEY=... OPENAI_API_KEY=...
fly deploy
```

## License

Proprietary - All rights reserved.
