Here's your `claude.md` file:

```markdown
# Sherlock - Image Knowledge Extraction System

## Overview
A web-based application that ingests images, extracts content using vision-enabled LLMs, paraphrases extracted text, stores structured data in Supabase with vector embeddings, and provides RAG capabilities through a React frontend with MCP-compatible API.

---

## Tech Stack

### Frontend
- **Framework:** React
- **Icons:** Lucide React (use consistently throughout)
- **Styling:** Minimal, clean UI with low visual clutter

### Backend
- **Language:** Python
- **API Framework:** FastAPI
- **Database:** Supabase (PostgreSQL)
- **Vector Store:** Supabase pgvector
- **LLMs:** Configurable (local or web-based)
- **Hosting:** Fly.io

---

## Project Structure

### Backend Organization
```
backend/
├── api/          # FastAPI routes and endpoints
├── services/     # Business logic and LLM integrations
├── utils/        # Helper functions and utilities
├── db/           # Database models, queries, and migrations
├── settings/     # Configuration and credentials (.env)
└── exceptions/   # Custom error handling
```

### Frontend Organization
```
frontend/
├── components/   # React components
├── services/     # API client and data fetching
├── utils/        # Helper functions
├── hooks/        # Custom React hooks
└── assets/       # Static assets and icons
```

---

## Coding Standards

### Backend (Python)
- Write clean, modular, maintainable code
- Use type hints for all function signatures
- Follow PEP 8 style guidelines
- Implement proper error handling with custom exceptions
- Use async/await for I/O operations
- Document all functions with docstrings

### Frontend (React)
- Use functional components with hooks
- Keep components small and focused
- Implement proper prop typing
- Use Lucide React icons exclusively
- Maintain minimal, visually pleasing UI
- Prioritize clarity and readability

---

## Database Schema

### Supabase Tables

#### `Knowledge` Table
Required columns:
- `id` (primary key)
- `category` (string)
- `subcategory` (string)
- `title` (string)
- `raw_data` (text)
- `paraphrased_data` (text)
- `image` (string/url)
- `url` (string)
- `status` (string) - "pending" | "processing" | "completed" | "failed"
- `last_error` (text, nullable) - error details if status is "failed"
- `retry_count` (integer, default: 0) - number of retry attempts
- `embedding` (vector(1536)) - for pgvector with text-embedding-3-small
- `created_at` (timestamp)
- `updated_at` (timestamp)

#### `Config` Table
Configuration storage (JSON):
- `key` = `"tags"`: Category and subcategory definitions
- `key` = `"llms"`: LLM provider configurations

---

## Features & Functionality

### 1. Image Ingestion
**Supported Input Types:**
- Single image from web URL
- Single image from Google Drive shared link
- Batch images from Google Drive folder
- Batch images from local filesystem folder

**Processing:**
- Queue-based sequential processing
- Error handling for failed ingestions
- Progress tracking

### 2. Content Extraction with Vision LLMs
**LLM Requirements:**
- Must support vision/image input
- Dynamically selectable from config
- Support for multiple providers:
  - Web: OpenAI GPT-5.2 (default), Claude Opus 4.5, Gemini 3.0 Flash
  - Local: Configurable local models

**Extraction Output:**
- Raw extracted text
- Paraphrased version
- Short, meaningful title
- Category assignment (from config tags)
- Subcategory assignment (from config tags)

### 3. Vectorization
**Requirements:**
- Vectorize raw extracted content only
- Store in Supabase pgvector
- Include metadata:
  - Image URL
  - Category
  - Subcategory
  - Title

### 4. Frontend Layout
**Application Name:** Sherlock

**Three-Column Layout:**

**Header:**
- App name with icon
- Global actions/settings

**Left Pane (Navigation):**
- Tree-style category/subcategory browser
- Collapsible sections
- Selection triggers filtering and pagination

**Main Pane (Content Grid):**
- Thumbnail grid of images with titles
- Pagination controls
- Click thumbnail → Open modal with:
  - Full-size image
  - Title
  - Two-column layout:
    - Left: Raw Data
    - Right: Paraphrased Data

### 5. Retry & Resilience
**Retry Strategy:**
- Use exponential backoff with jitter for all retryable operations
- Default: 3 retries with base delay of 1 second (1s, 2s, 4s + jitter)
- Configurable via environment variables

**Retryable Operations:**
| Operation | Retry On | Max Retries |
|-----------|----------|-------------|
| LLM Vision Parsing | Rate limits, timeouts, 5xx errors | 3 |
| Database Writes | Connection errors, deadlocks, timeouts | 3 |
| Embedding Generation | Rate limits, timeouts | 3 |
| Google Drive API | Rate limits, auth refresh | 3 |

**Non-Retryable Errors:**
- 4xx client errors (except 429 rate limit)
- Invalid image format
- Authentication failures (after token refresh attempt)

**Failure Handling:**
- Mark record with `status: "failed"` after exhausting retries
- Store error details in `last_error` field
- Support manual retry via API endpoint:
  ```
  POST /api/knowledge/{id}/retry
  ```
- Batch retry for all failed records:
  ```
  POST /api/knowledge/retry-failed
  ```

---

## API Endpoints

### 1. Ingestion & Vectorization
```
POST /api/ingest
```
**Parameters:**
- `folder_type`: `"local"` | `"google_drive"`
- `folder_location`: path or URL (optional)
- `image_url`: web URL or Google Drive link (optional)
- `llm_type`: `"local"` | `"web"`
- `llm`: LLM identifier (default: `"GPT-5.2"`)

**Returns:**
- Job ID for tracking
- Processing status

### 2. Visualization Data
```
GET /api/knowledge
```
**Query Parameters:**
- `category`: filter by category (default: `"All"`)
- `subcategory`: filter by subcategory (default: `"All"`)
- `page`: page number (default: `1`)
- `page_size`: records per page (default: `20`)

**Returns:**
- Paginated list of knowledge items
- Total count
- Pagination metadata

### 3. RAG / MCP Query (SSE)
```
POST /api/rag/query
```
**MCP-compatible with Server-Sent Events**

**Parameters:**
- `query`: user input string

**Returns:**
- SSE stream of generated response
- Retrieved context snippets
- Source references

### 4. Retry Failed Records
```
POST /api/knowledge/{id}/retry
```
**Description:** Retry processing for a single failed record

**Returns:**
- New job ID for tracking
- Processing status

```
POST /api/knowledge/retry-failed
```
**Description:** Batch retry all records with `status: "failed"`

**Query Parameters:**
- `category`: filter by category (optional)
- `limit`: max records to retry (default: 100)

**Returns:**
- Number of records queued for retry
- Job IDs for tracking

---

## Configuration

### LLM Configuration (Supabase Config)
```json
{
  "llms": {
    "web": [
      {
        "id": "gpt-5.2",
        "name": "GPT-5.2",
        "provider": "openai",
        "model": "gpt-5.2-vision",
        "default": true
      },
      {
        "id": "claude-opus-4.5",
        "name": "Claude Opus 4.5",
        "provider": "anthropic",
        "model": "claude-opus-4.5"
      },
      {
        "id": "gemini-3.0-flash",
        "name": "Gemini 3.0 Flash",
        "provider": "google",
        "model": "gemini-3.0-flash"
      }
    ],
    "local": []
  }
}
```

### Tags Configuration (Supabase Config)
```json
{
  "tags": {
    "categories": [
      {
        "name": "Design",
        "subcategories": ["documentation",  "architecture", "other"]
      },
      {
        "name": "Code",
        "subcategories": ["frontend", "backend","other"]
      },
      {
        "name": "Domain",
        "subcategories": ["clinical", "non clinical", "other"]
      },
      {
        "name": "Misc",
        "subcategories": ["roadmap", "strategy", "performance", "other"]
      }
    ]
  }
}
```

---

## Development Priorities

1. **Modularity:** Keep services decoupled and testable
2. **Error Handling:** Comprehensive exception handling throughout
3. **Async Operations:** Use async/await for I/O-bound operations
4. **Type Safety:** Use type hints (Python) and PropTypes/TypeScript (React)
5. **Configuration-Driven:** Store dynamic config in Supabase, not hardcoded
6. **Clean UI:** Minimal design, maximum clarity
7. **Progressive Enhancement:** Build core features first, optimize later

---

## Deployment

- **Platform:** Fly.io
- **Environment Variables:** Store in secrets manager
- **Database:** Supabase (managed PostgreSQL with pgvector)
- **Static Assets:** Serve via CDN if needed

---

## Next Steps

1. Set up Supabase project and tables
2. Implement ingestion API with queue system
3. Integrate vision LLM providers
4. Build vectorization pipeline
5. Create React frontend layout
6. Implement RAG/MCP endpoint with SSE
7. Deploy to Fly.io
```

This `claude.md` file provides comprehensive context for Claude Code to understand your project structure, requirements, and conventions. Save it as `claude.md` in your project root, and Claude Code will use it to make informed decisions when building your application.