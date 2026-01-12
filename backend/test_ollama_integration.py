"""
Test script for Ollama integration.

This script demonstrates how to use the Ollama service for vision-based
content extraction from images.

Prerequisites:
    1. Ollama installed and running
    2. Vision model pulled: ollama pull qwen3-vl:4b
    3. OLLAMA_BASE_URL configured in .env (default: http://localhost:11434)

Usage:
    python test_ollama_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ollama_service import OllamaService
from services.llm_service import LLMService
from settings.config import get_settings


async def test_ollama_health():
    """Test if Ollama server is accessible."""
    print("=" * 60)
    print("Testing Ollama Server Health")
    print("=" * 60)

    ollama = OllamaService()
    is_healthy = await ollama.check_health()

    if is_healthy:
        print("✓ Ollama server is healthy and accessible")
        return True
    else:
        print("✗ Ollama server is not accessible")
        print(f"  URL: {ollama.base_url}")
        print("  Make sure Ollama is running: ollama serve")
        return False


async def test_list_models():
    """Test listing available models in Ollama."""
    print("\n" + "=" * 60)
    print("Listing Available Models")
    print("=" * 60)

    ollama = OllamaService()

    try:
        models = await ollama.list_models()
        if models:
            print(f"Found {len(models)} model(s):")
            for model in models:
                print(f"  - {model}")
        else:
            print("No models found. Pull a model first:")
            print("  ollama pull qwen3-vl:4b")
        return models
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return []


async def test_model_exists(model_name: str = "qwen3-vl:4b"):
    """Test if a specific model exists."""
    print("\n" + "=" * 60)
    print(f"Checking for Model: {model_name}")
    print("=" * 60)

    ollama = OllamaService(model_name=model_name)
    exists = await ollama.check_model_exists()

    if exists:
        print(f"✓ Model '{model_name}' is available")
        return True
    else:
        print(f"✗ Model '{model_name}' not found")
        print(f"  Pull it with: ollama pull {model_name}")
        return False


async def test_vision_extraction():
    """Test vision-based content extraction with sample prompt."""
    print("\n" + "=" * 60)
    print("Testing Vision Extraction (Mock)")
    print("=" * 60)

    # Create a simple test image (1x1 pixel PNG)
    # This is a valid PNG image in base64
    test_image_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    import base64
    test_image_bytes = base64.b64decode(test_image_b64)

    prompt = """Analyze this image and extract information.
Return a JSON object with: title, raw_data, category, subcategory."""

    ollama = OllamaService(model_name="qwen3-vl:4b")

    print(f"Model: {ollama.model_name}")
    print(f"Base URL: {ollama.base_url}")
    print(f"Image size: {len(test_image_bytes)} bytes")
    print(f"Prompt: {prompt[:80]}...")

    try:
        # Note: This will only work if Ollama is running with qwen3-vl:4b
        print("\nAttempting to generate response...")
        print("(This may take 30-60 seconds for the first request)")

        response = await ollama.generate_with_image(
            prompt=prompt,
            image_bytes=test_image_bytes,
            temperature=0.1,
            timeout=120.0,
        )

        print("\n✓ Response received:")
        print("-" * 60)
        print(response[:500])  # Print first 500 chars
        if len(response) > 500:
            print(f"\n... (truncated, total length: {len(response)} chars)")
        print("-" * 60)

        return True

    except Exception as e:
        print(f"\n✗ Vision extraction failed: {e}")
        print("\nThis is expected if:")
        print("  1. Ollama is not running")
        print("  2. Model qwen3-vl:4b is not pulled")
        print("  3. Model is not vision-enabled")
        return False


async def test_llm_service_integration():
    """Test LLMService integration with Ollama."""
    print("\n" + "=" * 60)
    print("Testing LLMService Integration")
    print("=" * 60)

    # Create a simple test image
    test_image_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    import base64
    test_image_bytes = base64.b64decode(test_image_b64)

    # Test categories
    categories = [
        ("Design", ["documentation", "architecture", "other"]),
        ("Code", ["frontend", "backend", "other"]),
    ]

    llm_service = LLMService(llm_type="local", llm_id="qwen3-vl:4b")

    print(f"LLM Type: {llm_service.llm_type}")
    print(f"LLM ID: {llm_service.llm_id}")

    try:
        print("\nAttempting extraction via LLMService...")
        print("(This uses the _extract_with_ollama method)")

        result = await llm_service.extract_content(
            image_bytes=test_image_bytes,
            available_categories=categories,
        )

        print("\n✓ Extraction successful:")
        print(f"  Title: {result.title}")
        print(f"  Category: {result.category}")
        print(f"  Subcategory: {result.subcategory}")
        print(f"  Raw Data: {result.raw_data[:100]}...")
        print(f"  Paraphrased: {result.paraphrased_data[:100]}...")

        return True

    except Exception as e:
        print(f"\n✗ LLMService extraction failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OLLAMA INTEGRATION TEST SUITE")
    print("=" * 60)

    settings = get_settings()
    print(f"\nConfiguration:")
    print(f"  OLLAMA_BASE_URL: {settings.ollama_base_url}")
    print(f"  USE_MOCK: {settings.use_mock}")

    # Run tests
    results = {}

    # Test 1: Health check
    results["health"] = await test_ollama_health()

    if not results["health"]:
        print("\n" + "=" * 60)
        print("SKIPPING REMAINING TESTS - Ollama not accessible")
        print("=" * 60)
        return

    # Test 2: List models
    models = await test_list_models()
    results["list_models"] = len(models) > 0

    # Test 3: Check for qwen3-vl:4b
    results["model_exists"] = await test_model_exists("qwen3-vl:4b")

    # Test 4: Vision extraction (only if model exists)
    if results["model_exists"]:
        results["vision"] = await test_vision_extraction()
        results["llm_service"] = await test_llm_service_integration()
    else:
        print("\n" + "=" * 60)
        print("SKIPPING VISION TESTS - Model not available")
        print("=" * 60)
        results["vision"] = False
        results["llm_service"] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name:20s}: {status}")

    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {total_tests - passed_tests} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())
