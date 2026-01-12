"""Quick test for Ollama chat API with qwen3-vl vision model."""

import asyncio
import base64
import httpx


async def test_ollama_chat_vision():
    """Test the /api/chat endpoint with a simple image."""
    base_url = "http://localhost:11434"
    model = "qwen3-vl:4b"

    # Create a simple test image (1x1 red pixel PNG)
    # This is a minimal valid PNG for testing connectivity
    test_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    image_b64 = base64.b64encode(test_png).decode("utf-8")

    # Test 1: Health check
    print("1. Testing Ollama health...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                print("   [OK] Ollama is running")
            else:
                print(f"   [FAIL] Unexpected status: {response.status_code}")
                return
    except Exception as e:
        print(f"   [FAIL] Cannot connect to Ollama: {e}")
        return

    # Test 2: Chat endpoint with image
    print(f"\n2. Testing /api/chat with {model}...")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "What do you see in this image? Reply briefly.",
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("   Sending request (this may take a moment)...")
            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})
                content = message.get("content", "")
                print(f"   [OK] Success! Response:\n   {content[:200]}...")
            else:
                print(f"   [FAIL] HTTP {response.status_code}: {response.text[:200]}")

    except httpx.TimeoutException:
        print("   [FAIL] Request timed out (model may be loading)")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 3: Try with a real test image URL
    print(f"\n3. Testing with a downloaded image...")

    try:
        # Download a small test image
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_response = await client.get(
                "https://via.placeholder.com/100x100.png?text=Test"
            )
            if img_response.status_code == 200:
                real_image_b64 = base64.b64encode(img_response.content).decode("utf-8")

                payload["messages"][0]["images"] = [real_image_b64]
                payload["messages"][0]["content"] = "Describe what you see in this image. Be brief."

                print("   Sending request with real image...")
                response = await client.post(
                    f"{base_url}/api/chat",
                    json=payload,
                    timeout=120.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "")
                    print(f"   [OK] Success! Response:\n   {content[:300]}")
                else:
                    print(f"   [FAIL] HTTP {response.status_code}: {response.text[:200]}")
            else:
                print(f"   [FAIL] Could not download test image")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    print("\n" + "="*50)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_ollama_chat_vision())
