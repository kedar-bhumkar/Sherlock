# Ollama Quick Start Guide

Get up and running with Ollama in the Sherlock backend in 5 minutes.

## Prerequisites

- Python 3.12+ environment set up
- Backend dependencies installed (`pip install -r requirements.txt`)

## Step 1: Install Ollama (2 minutes)

### macOS/Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download and install from: https://ollama.ai/download

## Step 2: Pull Vision Model (2 minutes)

```bash
ollama pull qwen3-vl:4b
```

Wait for download to complete (~2.5GB).

## Step 3: Verify Installation (30 seconds)

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# List installed models
ollama list

# You should see: qwen3-vl:4b
```

## Step 4: Configure Environment (30 seconds)

Your `.env` file should already have:
```bash
OLLAMA_BASE_URL=http://localhost:11434
```

If not, add it.

## Step 5: Test the Integration (1 minute)

```bash
cd backend
python test_ollama_integration.py
```

Expected output:
```
OLLAMA INTEGRATION TEST SUITE
Configuration:
  OLLAMA_BASE_URL: http://localhost:11434
  USE_MOCK: False

Testing Ollama Server Health
✓ Ollama server is healthy and accessible

Listing Available Models
Found 1 model(s):
  - qwen3-vl:4b

Checking for Model: qwen3-vl:4b
✓ Model 'qwen3-vl:4b' is available

TEST SUMMARY
  health              : ✓ PASS
  list_models         : ✓ PASS
  model_exists        : ✓ PASS
  vision              : ✓ PASS
  llm_service         : ✓ PASS

✓ All tests passed!
```

## Step 6: Use in Your Code

### Via API
```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.png",
    "llm_type": "local",
    "llm": "qwen3-vl:4b"
  }'
```

### Via Python
```python
from services.llm_service import LLMService

llm_service = LLMService(llm_type="local", llm_id="qwen3-vl:4b")
result = await llm_service.extract_content(
    image_bytes=image_data,
    available_categories=[
        ("Design", ["documentation", "architecture"]),
        ("Code", ["frontend", "backend"]),
    ],
)

print(f"Title: {result.title}")
print(f"Category: {result.category}")
```

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Check if Ollama is running
ps aux | grep ollama  # macOS/Linux
tasklist | findstr ollama  # Windows

# Start Ollama
ollama serve
```

### "Model not found"
```bash
# Pull the model
ollama pull qwen3-vl:4b

# Verify
ollama list
```

### "Slow response"
- First request: 30-60 seconds (model loads into memory)
- Subsequent requests: 1-5 seconds
- This is normal behavior

## What's Next?

1. **Update Supabase Config:** Add Ollama to your LLM configuration
2. **Read Full Guide:** See `OLLAMA_SETUP.md` for detailed documentation
3. **Review Implementation:** Check `OLLAMA_IMPLEMENTATION_SUMMARY.md`
4. **Start Using:** Begin ingesting images with local LLM!

## Need Help?

- Full Setup Guide: `OLLAMA_SETUP.md`
- Implementation Details: `OLLAMA_IMPLEMENTATION_SUMMARY.md`
- Test Script: `test_ollama_integration.py`
- Ollama Docs: https://github.com/ollama/ollama

## Summary

You now have:
- Ollama service module (`services/ollama_service.py`)
- Integration with LLMService
- Test suite for verification
- Complete documentation

Start using local vision LLMs in Sherlock!
