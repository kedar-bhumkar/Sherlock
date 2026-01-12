# Ollama Integration Setup Guide

This guide explains how to set up and use Ollama for local vision-enabled LLM inference in the Sherlock backend.

## Overview

Ollama integration allows you to run vision-enabled language models locally for image content extraction, eliminating the need for cloud-based API calls and associated costs.

## Supported Models

- **qwen3-vl:4b** (Recommended) - 4B parameter vision-language model
- **llava:7b** - 7B parameter vision model
- **llava:13b** - 13B parameter vision model (requires more GPU memory)
- **bakllava:latest** - BakLLaVA vision model

## Installation

### 1. Install Ollama

#### macOS and Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows
Download and install from [https://ollama.ai/download](https://ollama.ai/download)

### 2. Pull a Vision Model

```bash
# Recommended: Qwen3 VL 4B (lightweight, fast, good quality)
ollama pull qwen3-vl:4b

# Alternative: LLaVA 7B
ollama pull llava:7b

# Alternative: LLaVA 13B (better quality, needs more resources)
ollama pull llava:13b
```

### 3. Verify Installation

```bash
# List available models
ollama list

# Test the model
ollama run qwen3-vl:4b "Hello, can you see images?"
```

## Configuration

### Environment Variables

Add to your `backend/.env` file:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
```

If Ollama is running on a different machine or port:
```bash
OLLAMA_BASE_URL=http://your-ollama-server:11434
```

### Supabase Config Table

Add Ollama to your LLM configuration in the Supabase `config` table:

```json
{
  "llms": {
    "web": [
      {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "default": false
      }
    ],
    "local": [
      {
        "id": "qwen3-vl:4b",
        "name": "Qwen3 VL 4B",
        "provider": "ollama",
        "model": "qwen3-vl:4b",
        "default": true
      },
      {
        "id": "llava:7b",
        "name": "LLaVA 7B",
        "provider": "ollama",
        "model": "llava:7b",
        "default": false
      }
    ]
  }
}
```

## Usage

### Via API

When calling the ingestion API, specify `llm_type: "local"` and the model ID:

```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.png",
    "llm_type": "local",
    "llm": "qwen3-vl:4b"
  }'
```

### Via Python Code

```python
from services.ollama_service import OllamaService
from services.llm_service import LLMService

# Direct usage
ollama = OllamaService(model_name="qwen3-vl:4b")
response = await ollama.generate_with_image(
    prompt="Extract text from this image",
    image_bytes=image_data,
)

# Via LLMService (recommended)
llm_service = LLMService(llm_type="local", llm_id="qwen3-vl:4b")
result = await llm_service.extract_content(
    image_bytes=image_data,
    available_categories=categories,
)
```

## Testing

Run the provided test script to verify your Ollama setup:

```bash
cd backend
python test_ollama_integration.py
```

The test script will:
1. Check Ollama server health
2. List available models
3. Verify qwen3-vl:4b is available
4. Test vision extraction with a sample image
5. Test LLMService integration

## Troubleshooting

### Ollama Server Not Accessible

**Error:** `Cannot connect to Ollama at http://localhost:11434`

**Solutions:**
1. Check if Ollama is running:
   ```bash
   # macOS/Linux
   ps aux | grep ollama

   # Windows
   tasklist | findstr ollama
   ```

2. Start Ollama manually:
   ```bash
   ollama serve
   ```

3. Verify the port:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Model Not Found

**Error:** `Model 'qwen3-vl:4b' not found`

**Solution:**
```bash
# Pull the model
ollama pull qwen3-vl:4b

# Verify it's available
ollama list
```

### Slow Response Times

**Issue:** First request takes 30-60 seconds

**Explanation:** Ollama loads models into memory on first use. Subsequent requests are much faster (1-5 seconds).

**Solutions:**
1. Keep Ollama running continuously
2. Preload models:
   ```bash
   ollama run qwen3-vl:4b "preload" --keepalive 24h
   ```

### Out of Memory

**Error:** Model fails to load or crashes

**Solutions:**
1. Use a smaller model:
   ```bash
   ollama pull qwen3-vl:4b  # Instead of llava:13b
   ```

2. Close other applications to free memory

3. Check system requirements:
   - qwen3-vl:4b: ~8GB RAM
   - llava:7b: ~8GB RAM
   - llava:13b: ~16GB RAM

### Invalid Response Format

**Issue:** Model doesn't return valid JSON

**Solutions:**
1. Adjust the prompt in `llm_service.py`
2. Use temperature=0.1 for more deterministic output
3. Try a different model (qwen3-vl is better at structured output)

## Performance Comparison

| Model | Size | Speed | Quality | Memory | Recommended For |
|-------|------|-------|---------|--------|-----------------|
| qwen3-vl:4b | 4B | Fast | Good | 8GB | General use, production |
| llava:7b | 7B | Medium | Good | 8GB | Balanced performance |
| llava:13b | 13B | Slow | Better | 16GB | High quality needed |

## Architecture

The Ollama integration follows the Sherlock modular architecture:

```
backend/
├── services/
│   ├── ollama_service.py      # Dedicated Ollama service
│   ├── llm_service.py          # Main LLM orchestrator
│   └── __init__.py             # Service exports
├── settings/
│   └── config.py               # Configuration with ollama_base_url
└── exceptions/
    └── llm_exceptions.py       # LLM-specific errors
```

### Key Design Principles

1. **Separation of Concerns:** `ollama_service.py` handles all Ollama-specific logic
2. **Reusability:** OllamaService can be used independently or via LLMService
3. **Error Handling:** Comprehensive exception handling with retry logic
4. **Configuration:** Environment-based configuration with sensible defaults
5. **Type Safety:** Full type hints for all methods

## API Reference

### OllamaService

```python
class OllamaService:
    def __init__(self, model_name: str = "qwen3-vl:4b")

    async def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        temperature: float = 0.1,
        timeout: float = 120.0,
    ) -> str

    async def check_health(self) -> bool
    async def list_models(self) -> list[str]
    async def check_model_exists(self, model_name: Optional[str] = None) -> bool
```

## Best Practices

1. **Keep Ollama Running:** Start Ollama as a service for faster response times
2. **Use Appropriate Models:** Choose model size based on your use case and resources
3. **Monitor Resources:** Ollama can consume significant CPU/GPU during inference
4. **Handle Timeouts:** Set appropriate timeouts for vision tasks (60-120s)
5. **Validate Responses:** Always parse and validate JSON responses from models
6. **Retry Logic:** The service includes automatic retry with exponential backoff

## Advanced Configuration

### Custom Ollama Server

If running Ollama on a different machine:

```bash
# .env
OLLAMA_BASE_URL=http://192.168.1.100:11434
```

### GPU Acceleration

Ollama automatically uses GPU if available. To force CPU:

```bash
OLLAMA_NUM_GPU=0 ollama serve
```

### Model Parameters

Customize model behavior in the code:

```python
response = await ollama.generate_with_image(
    prompt="Your prompt",
    image_bytes=image_data,
    temperature=0.0,  # More deterministic (0.0-1.0)
    timeout=180.0,    # Longer timeout for complex images
)
```

## Support

For issues with:
- **Ollama itself:** https://github.com/ollama/ollama/issues
- **Sherlock integration:** Check backend logs and test script output
- **Model quality:** Try different models or adjust prompts

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/README.md)
- [Ollama Model Library](https://ollama.ai/library)
- [Qwen3-VL Model Card](https://ollama.ai/library/qwen3-vl)
- [LLaVA Model Card](https://ollama.ai/library/llava)
