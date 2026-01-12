"""Google Drive service using credentials.json and token.pickle for authentication."""

import io
import os
import pickle
from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from settings.config import get_settings
from utils.retry_utils import with_retry, RetryConfig
from exceptions.ingestion_exceptions import ImageDownloadError


# OAuth 2.0 scopes for Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Supported image MIME types
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
}


@dataclass
class DriveFile:
    """Represents a file from Google Drive."""

    id: str
    name: str
    mime_type: str
    size: int | None = None
    web_view_link: str | None = None
    thumbnail_link: str | None = None


class GoogleDriveService:
    """Service for Google Drive authentication and file operations using credentials.json."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
    ):
        """
        Initialize Google Drive service.

        Args:
            credentials_path: Path to credentials.json (defaults to settings)
            token_path: Path to token.pickle (defaults to settings)
        """
        self.settings = get_settings()
        self._credentials_path = credentials_path or self.settings.google_drive_credentials_path
        self._token_path = token_path or self.settings.google_drive_token_path
        self._service = None
        self._credentials = None

        print(f"[GoogleDrive] Initialized with credentials_path={self._credentials_path}, token_path={self._token_path}")

    @property
    def credentials_path(self) -> Path:
        """Get credentials.json path."""
        return Path(self._credentials_path)

    @property
    def token_path(self) -> Path:
        """Get token.pickle path."""
        return Path(self._token_path)

    def is_configured(self) -> bool:
        """Check if credentials.json exists."""
        exists = self.credentials_path.exists()
        print(f"[GoogleDrive] is_configured: credentials.json exists={exists} at {self.credentials_path}")
        return exists

    def is_authenticated(self) -> bool:
        """Check if valid token exists."""
        print(f"[GoogleDrive] is_authenticated: checking token at {self.token_path}")

        if not self.token_path.exists():
            print("[GoogleDrive] is_authenticated: token.pickle does not exist")
            return False

        try:
            creds = self._load_token()
            is_valid = creds is not None and creds.valid
            print(f"[GoogleDrive] is_authenticated: token loaded, valid={is_valid}")
            return is_valid
        except Exception as e:
            print(f"[GoogleDrive] is_authenticated: error loading token: {e}")
            return False

    def needs_authentication(self) -> bool:
        """Check if authentication is needed (no token or expired)."""
        print("[GoogleDrive] needs_authentication: checking...")

        if not self.token_path.exists():
            print("[GoogleDrive] needs_authentication: YES - no token.pickle")
            return True

        try:
            creds = self._load_token()
            if creds is None:
                print("[GoogleDrive] needs_authentication: YES - token is None")
                return True
            if creds.valid:
                print("[GoogleDrive] needs_authentication: NO - token is valid")
                return False
            # Token exists but expired - try to refresh
            if creds.expired and creds.refresh_token:
                print("[GoogleDrive] needs_authentication: NO - token expired but can be refreshed")
                return False  # Can be refreshed
            print("[GoogleDrive] needs_authentication: YES - token expired, no refresh token")
            return True
        except Exception as e:
            print(f"[GoogleDrive] needs_authentication: YES - error: {e}")
            return True

    def _load_token(self) -> Credentials | None:
        """Load token from pickle file."""
        print(f"[GoogleDrive] _load_token: loading from {self.token_path}")

        if not self.token_path.exists():
            print("[GoogleDrive] _load_token: file does not exist")
            return None

        with open(self.token_path, "rb") as token_file:
            creds = pickle.load(token_file)
            print(f"[GoogleDrive] _load_token: loaded successfully, expired={creds.expired if creds else 'N/A'}")
            return creds

    def _save_token(self, creds: Credentials) -> None:
        """Save token to pickle file."""
        print(f"[GoogleDrive] _save_token: saving to {self.token_path}")

        # Ensure directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.token_path, "wb") as token_file:
            pickle.dump(creds, token_file)

        print("[GoogleDrive] _save_token: saved successfully")

    def authenticate(self, headless: bool = False) -> bool:
        """
        Authenticate with Google Drive.

        If token.pickle exists and is valid, uses it.
        If token is expired but has refresh_token, refreshes it.
        Otherwise, initiates OAuth flow (requires browser interaction).

        Args:
            headless: If True, raises error instead of opening browser

        Returns:
            True if authentication successful

        Raises:
            FileNotFoundError: If credentials.json not found
            RuntimeError: If headless=True and browser auth is needed
        """
        print(f"[GoogleDrive] authenticate: starting, headless={headless}")

        if not self.credentials_path.exists():
            print(f"[GoogleDrive] authenticate: ERROR - credentials.json not found at {self.credentials_path}")
            raise FileNotFoundError(
                f"credentials.json not found at {self.credentials_path}. "
                "Download it from Google Cloud Console."
            )

        creds = None

        # Load existing token
        if self.token_path.exists():
            print("[GoogleDrive] authenticate: loading existing token")
            creds = self._load_token()

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh the token
                print("[GoogleDrive] authenticate: refreshing expired token")
                try:
                    creds.refresh(Request())
                    print("[GoogleDrive] authenticate: token refreshed successfully")
                except Exception as e:
                    print(f"[GoogleDrive] authenticate: token refresh failed: {e}")
                    raise
            else:
                # Need to authenticate via browser
                print("[GoogleDrive] authenticate: need browser authentication")
                if headless:
                    print("[GoogleDrive] authenticate: ERROR - headless mode, cannot open browser")
                    raise RuntimeError(
                        "Authentication required but running in headless mode. "
                        "Run authenticate() interactively first to generate token.pickle."
                    )

                print("[GoogleDrive] authenticate: starting OAuth flow (opening browser)...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
                print("[GoogleDrive] authenticate: OAuth flow completed successfully")

            # Save the credentials for next run
            self._save_token(creds)

        self._credentials = creds
        print("[GoogleDrive] authenticate: SUCCESS")
        return True

    def get_credentials(self) -> Credentials:
        """
        Get valid credentials, refreshing if needed.

        Returns:
            Valid Google credentials

        Raises:
            RuntimeError: If not authenticated
        """
        print("[GoogleDrive] get_credentials: getting credentials")

        if self._credentials is None:
            # Try to load from file
            if self.token_path.exists():
                print("[GoogleDrive] get_credentials: loading from token.pickle")
                self._credentials = self._load_token()

        if self._credentials is None:
            print("[GoogleDrive] get_credentials: ERROR - no credentials available")
            raise RuntimeError(
                "Not authenticated. Call authenticate() first or ensure token.pickle exists."
            )

        # Refresh if expired
        if self._credentials.expired and self._credentials.refresh_token:
            print("[GoogleDrive] get_credentials: refreshing expired credentials")
            self._credentials.refresh(Request())
            self._save_token(self._credentials)
            print("[GoogleDrive] get_credentials: credentials refreshed")

        print("[GoogleDrive] get_credentials: returning valid credentials")
        return self._credentials

    @property
    def service(self):
        """Get authenticated Google Drive service."""
        if self._service is None:
            print("[GoogleDrive] service: building Drive API service")
            creds = self.get_credentials()
            self._service = build("drive", "v3", credentials=creds)
            print("[GoogleDrive] service: Drive API service built successfully")
        return self._service

    async def list_files_in_folder(
        self,
        folder_id: str,
        images_only: bool = True,
        page_size: int = 100,
    ) -> list[DriveFile]:
        """
        List files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID
            images_only: If True, only return image files
            page_size: Number of files per page

        Returns:
            List of DriveFile objects
        """
        print(f"[GoogleDrive] list_files_in_folder: folder_id={folder_id}, images_only={images_only}")

        files = []
        page_token = None

        # Build query
        query = f"'{folder_id}' in parents and trashed = false"
        if images_only:
            mime_queries = [f"mimeType = '{mt}'" for mt in SUPPORTED_IMAGE_TYPES]
            query += f" and ({' or '.join(mime_queries)})"

        print(f"[GoogleDrive] list_files_in_folder: query={query}")

        page_count = 0
        while True:
            page_count += 1
            print(f"[GoogleDrive] list_files_in_folder: fetching page {page_count}")

            response = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, size, webViewLink, thumbnailLink)",
                    pageToken=page_token,
                    pageSize=page_size,
                )
                .execute()
            )

            page_files = response.get("files", [])
            print(f"[GoogleDrive] list_files_in_folder: page {page_count} returned {len(page_files)} files")

            for file in page_files:
                files.append(
                    DriveFile(
                        id=file["id"],
                        name=file["name"],
                        mime_type=file["mimeType"],
                        size=int(file.get("size", 0)) if file.get("size") else None,
                        web_view_link=file.get("webViewLink"),
                        thumbnail_link=file.get("thumbnailLink"),
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        print(f"[GoogleDrive] list_files_in_folder: total files found={len(files)}")
        return files

    async def get_file_metadata(self, file_id: str) -> DriveFile:
        """
        Get metadata for a single file.

        Args:
            file_id: Google Drive file ID

        Returns:
            DriveFile object with file metadata
        """
        print(f"[GoogleDrive] get_file_metadata: file_id={file_id}")

        file = (
            self.service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, size, webViewLink, thumbnailLink",
            )
            .execute()
        )

        print(f"[GoogleDrive] get_file_metadata: name={file['name']}, mimeType={file['mimeType']}")

        return DriveFile(
            id=file["id"],
            name=file["name"],
            mime_type=file["mimeType"],
            size=int(file.get("size", 0)) if file.get("size") else None,
            web_view_link=file.get("webViewLink"),
            thumbnail_link=file.get("thumbnailLink"),
        )

    @with_retry(
        config=RetryConfig(max_attempts=3),
        retryable_exceptions=(ImageDownloadError,),
    )
    async def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes

        Raises:
            ImageDownloadError: If download fails
        """
        print(f"[GoogleDrive] download_file: starting download for file_id={file_id}")

        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            chunk_count = 0
            while not done:
                status, done = downloader.next_chunk()
                chunk_count += 1
                if status:
                    print(f"[GoogleDrive] download_file: chunk {chunk_count}, progress={int(status.progress() * 100)}%")

            file_bytes = file_buffer.getvalue()
            print(f"[GoogleDrive] download_file: SUCCESS - downloaded {len(file_bytes)} bytes")
            return file_bytes

        except Exception as e:
            print(f"[GoogleDrive] download_file: ERROR - {e}")
            raise ImageDownloadError(
                f"drive://{file_id}",
                f"Failed to download from Google Drive: {e}",
            )

    def extract_file_id_from_url(self, url: str) -> str | None:
        """
        Extract file ID from a Google Drive URL.

        Supports formats:
        - https://drive.google.com/file/d/{FILE_ID}/view
        - https://drive.google.com/open?id={FILE_ID}
        - https://docs.google.com/document/d/{FILE_ID}/edit

        Args:
            url: Google Drive URL

        Returns:
            File ID or None if not a valid Drive URL
        """
        import re

        print(f"[GoogleDrive] extract_file_id_from_url: url={url}")

        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"/document/d/([a-zA-Z0-9_-]+)",
            r"/spreadsheets/d/([a-zA-Z0-9_-]+)",
            r"/presentation/d/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)",
            r"/folders/([a-zA-Z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                file_id = match.group(1)
                print(f"[GoogleDrive] extract_file_id_from_url: extracted file_id={file_id}")
                return file_id

        print("[GoogleDrive] extract_file_id_from_url: no file ID found")
        return None

    def extract_folder_id_from_url(self, url: str) -> str | None:
        """
        Extract folder ID from a Google Drive folder URL.

        Args:
            url: Google Drive folder URL

        Returns:
            Folder ID or None if not a valid folder URL
        """
        import re

        print(f"[GoogleDrive] extract_folder_id_from_url: url={url}")

        patterns = [
            r"/folders/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                folder_id = match.group(1)
                print(f"[GoogleDrive] extract_folder_id_from_url: extracted folder_id={folder_id}")
                return folder_id

        print("[GoogleDrive] extract_folder_id_from_url: no folder ID found")
        return None


# Singleton instance for easy access
_drive_service: GoogleDriveService | None = None


def get_drive_service() -> GoogleDriveService:
    """Get the singleton GoogleDriveService instance."""
    global _drive_service
    if _drive_service is None:
        print("[GoogleDrive] get_drive_service: creating singleton instance")
        _drive_service = GoogleDriveService()
    return _drive_service
