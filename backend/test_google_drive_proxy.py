"""Test script for Google Drive image proxy endpoint."""

import asyncio
from services.google_drive_service import get_drive_service


async def test_google_drive_service():
    """Test Google Drive service authentication and basic operations."""
    print("\n=== Testing Google Drive Service ===\n")

    # Get service instance
    drive_service = get_drive_service()

    # Check configuration
    print(f"1. Configuration Check")
    print(f"   Credentials path: {drive_service.credentials_path}")
    print(f"   Token path: {drive_service.token_path}")
    print(f"   Is configured: {drive_service.is_configured()}")
    print(f"   Is authenticated: {drive_service.is_authenticated()}")
    print(f"   Needs authentication: {drive_service.needs_authentication()}")
    print()

    # Test authentication
    if drive_service.needs_authentication():
        print("2. Authentication Required")
        print("   Please run authentication interactively first:")
        print("   python -c 'from services.google_drive_service import get_drive_service; get_drive_service().authenticate()'")
        return
    else:
        print("2. Authentication Status: OK")
        print()

    # Test URL extraction
    print("3. Testing URL File ID Extraction")
    test_urls = [
        "https://drive.google.com/file/d/1abc123XYZ-456/view",
        "https://drive.google.com/open?id=1abc123XYZ-456",
        "https://drive.google.com/uc?id=1abc123XYZ-456",
        "https://docs.google.com/document/d/1abc123XYZ-456/edit",
    ]

    for url in test_urls:
        file_id = drive_service.extract_file_id_from_url(url)
        print(f"   URL: {url}")
        print(f"   File ID: {file_id}")
        print()

    print("=== Test Complete ===\n")


def test_url_helpers():
    """Test frontend URL helper functions (Python equivalent)."""
    print("\n=== Testing URL Helper Functions ===\n")

    from services.google_drive_service import get_drive_service

    drive_service = get_drive_service()

    test_cases = [
        ("https://drive.google.com/file/d/1abc123/view", "1abc123"),
        ("https://drive.google.com/open?id=1xyz789", "1xyz789"),
        ("https://example.com/image.jpg", None),
        ("https://docs.google.com/document/d/1doc456/edit", "1doc456"),
    ]

    for url, expected_id in test_cases:
        file_id = drive_service.extract_file_id_from_url(url)
        status = "PASS" if file_id == expected_id else "FAIL"
        print(f"[{status}] URL: {url}")
        print(f"      Expected: {expected_id}, Got: {file_id}")
        print()

    print("=== Test Complete ===\n")


if __name__ == "__main__":
    # Test URL helpers
    test_url_helpers()

    # Test Google Drive service
    asyncio.run(test_google_drive_service())
