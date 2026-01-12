"""Test Ollama vision with a real image file."""

import asyncio
import base64
import httpx
from pathlib import Path


async def test_with_real_image():
    """Test vision with a real image."""
    base_url = "http://localhost:11434"
    model = "qwen3-vl:4b"

    # Create a simple valid PNG image (10x10 colored squares)
    # Using PIL to create a test image
    try:
        from PIL import Image
        import io

        # Create a simple 100x100 image with colors
        img = Image.new('RGB', (100, 100), color='blue')
        # Draw some shapes
        for x in range(50):
            for y in range(50):
                img.putpixel((x, y), (255, 0, 0))  # Red square
        for x in range(50, 100):
            for y in range(50, 100):
                img.putpixel((x, y), (0, 255, 0))  # Green square

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        print(f"Created test image: {len(image_bytes)} bytes")

    except ImportError:
        print("PIL not available, using a minimal PNG")
        # Fallback: use a small but valid PNG (4x4 pixels)
        import struct
        import zlib

        def create_png(width, height, color):
            """Create a minimal valid PNG."""
            def png_chunk(chunk_type, data):
                chunk = chunk_type + data
                crc = zlib.crc32(chunk) & 0xffffffff
                return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)

            # PNG signature
            png = b'\x89PNG\r\n\x1a\n'
            # IHDR chunk
            ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
            png += png_chunk(b'IHDR', ihdr)
            # IDAT chunk (raw RGB data)
            raw = b''
            for y in range(height):
                raw += b'\x00'  # Filter type
                for x in range(width):
                    raw += bytes(color)
            compressed = zlib.compress(raw)
            png += png_chunk(b'IDAT', compressed)
            # IEND chunk
            png += png_chunk(b'IEND', b'')
            return png

        image_bytes = create_png(50, 50, (255, 128, 64))
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        print(f"Created fallback PNG: {len(image_bytes)} bytes")

    print(f"\nTesting /api/chat with {model}...")
    print(f"Image base64 length: {len(image_b64)} chars")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "What colors do you see in this image? Answer briefly.",
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Sending request...")
            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})
                content = message.get("content", "")
                thinking = message.get("thinking", "")
                print(f"\n[SUCCESS] Response:")
                print(f"Content: {content}")
                if thinking:
                    print(f"Thinking: {thinking[:200]}...")
            else:
                print(f"[FAIL] {response.text}")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(test_with_real_image())
