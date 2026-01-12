"""Test script for LLM and Embedding services."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from utils.image_utils import download_image, validate_image


async def test_with_url(image_url: str):
    """Test extraction with an image URL."""
    print(f"\n{'='*60}")
    print(f"Testing with image: {image_url}")
    print('='*60)

    # Download image
    print("\n[1] Downloading image...")
    try:
        image_bytes = await download_image(image_url)
        print(f"    Downloaded {len(image_bytes):,} bytes")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    # Validate image
    print("\n[2] Validating image...")
    try:
        validate_image(image_bytes)
        print("    Image is valid")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    # Test LLM extraction
    print("\n[3] Extracting content with LLM (mock mode)...")
    llm_service = LLMService(llm_type="web", llm_id="gemini-3-flash-preview")

    categories = [
        ("Design", ["documentation", "architecture", "other"]),
        ("Code", ["frontend", "backend", "other"]),
        ("Domain", ["clinical", "non clinical", "other"]),
        ("Misc", ["roadmap", "strategy", "performance", "other"]),
    ]

    try:
        result = await llm_service.extract_content(image_bytes, categories)
        print(f"    Title: {result.title}")
        print(f"    Category: {result.category} / {result.subcategory}")
        print(f"    Raw data: {result.raw_data[:100]}...")
        print(f"    Paraphrased: {result.paraphrased_data[:100]}...")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    # Test embedding generation
    print("\n[4] Generating embedding (mock mode)...")
    embedding_service = EmbeddingService()

    try:
        embedding = await embedding_service.generate_embedding(result.raw_data)
        print(f"    Embedding dimensions: {len(embedding)}")
        print(f"    First 5 values: {embedding[:5]}")
        print(f"    Magnitude: {sum(x**2 for x in embedding) ** 0.5:.4f}")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    print("\n" + "="*60)
    print("TEST PASSED - All services working correctly")
    print("="*60)


async def test_with_local_image():
    """Test with a generated local test image."""
    print(f"\n{'='*60}")
    print("Testing with generated test image")
    print('='*60)

    # Create a simple test PNG image (1x1 red pixel)
    # PNG header + IHDR + IDAT + IEND
    import struct
    import zlib

    def create_test_png():
        """Create a minimal valid PNG."""
        # PNG signature
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk (width=1, height=1, bit_depth=8, color_type=2 RGB)
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

        # IDAT chunk (compressed image data - red pixel)
        raw_data = b'\x00\xff\x00\x00'  # filter byte + RGB
        compressed = zlib.compress(raw_data)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

        # IEND chunk
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

        return signature + ihdr + idat + iend

    image_bytes = create_test_png()
    print(f"\n[1] Created test PNG image ({len(image_bytes)} bytes)")

    # Validate image
    print("\n[2] Validating image...")
    try:
        validate_image(image_bytes)
        print("    Image is valid")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    # Test LLM extraction
    print("\n[3] Extracting content with LLM (mock mode)...")
    llm_service = LLMService(llm_type="web", llm_id="gemini-3-flash-preview")

    categories = [
        ("Design", ["documentation", "architecture", "other"]),
        ("Code", ["frontend", "backend", "other"]),
        ("Domain", ["clinical", "non clinical", "other"]),
        ("Misc", ["roadmap", "strategy", "performance", "other"]),
    ]

    try:
        result = await llm_service.extract_content(image_bytes, categories)
        print(f"    Title: {result.title}")
        print(f"    Category: {result.category} / {result.subcategory}")
        print(f"    Raw data: {result.raw_data[:100]}...")
        print(f"    Paraphrased: {result.paraphrased_data[:100]}...")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test embedding generation
    print("\n[4] Generating embedding (mock mode)...")
    embedding_service = EmbeddingService()

    try:
        embedding = await embedding_service.generate_embedding(result.raw_data)
        print(f"    Embedding dimensions: {len(embedding)}")
        print(f"    First 5 values: {[f'{v:.4f}' for v in embedding[:5]]}")
        print(f"    Magnitude: {sum(x**2 for x in embedding) ** 0.5:.4f}")
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    print("\n" + "="*60)
    print("TEST PASSED - All services working correctly")
    print("="*60)


async def main():
    await test_with_local_image()


if __name__ == "__main__":
    asyncio.run(main())
