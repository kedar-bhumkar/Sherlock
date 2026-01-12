"""Authentication API routes for Google Drive."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.google_drive_service import get_drive_service

router = APIRouter()


class AuthStatusResponse(BaseModel):
    """Response for auth status check."""

    configured: bool = Field(..., description="Whether credentials.json exists")
    authenticated: bool = Field(..., description="Whether valid token.pickle exists")
    needs_auth: bool = Field(..., description="Whether authentication is needed")
    credentials_path: str = Field(..., description="Path to credentials.json")
    token_path: str = Field(..., description="Path to token.pickle")


class AuthenticateResponse(BaseModel):
    """Response after authentication attempt."""

    success: bool = Field(..., description="Whether authentication succeeded")
    message: str = Field(..., description="Status message")


@router.get(
    "/auth/google/status",
    response_model=AuthStatusResponse,
    summary="Check Google Drive Auth Status",
    description="Check if Google Drive is configured and authenticated",
)
async def check_google_auth_status() -> AuthStatusResponse:
    """
    Check the current Google Drive authentication status.

    Returns information about:
    - Whether credentials.json exists (configured)
    - Whether token.pickle exists and is valid (authenticated)
    - Whether authentication is needed
    """
    print("[Auth] GET /auth/google/status: checking Google Drive auth status")

    drive_service = get_drive_service()

    configured = drive_service.is_configured()
    authenticated = drive_service.is_authenticated()
    needs_auth = drive_service.needs_authentication()

    print(f"[Auth] GET /auth/google/status: configured={configured}, authenticated={authenticated}, needs_auth={needs_auth}")

    return AuthStatusResponse(
        configured=configured,
        authenticated=authenticated,
        needs_auth=needs_auth,
        credentials_path=str(drive_service.credentials_path),
        token_path=str(drive_service.token_path),
    )


@router.post(
    "/auth/google/authenticate",
    response_model=AuthenticateResponse,
    summary="Authenticate with Google Drive",
    description="Trigger OAuth flow to authenticate with Google Drive (opens browser)",
)
async def authenticate_google_drive() -> AuthenticateResponse:
    """
    Authenticate with Google Drive.

    This will:
    1. Check if credentials.json exists
    2. If token.pickle exists and is valid, use it
    3. If token is expired, refresh it
    4. Otherwise, open a browser for OAuth consent

    Note: This endpoint opens a browser window for authentication.
    For headless/server environments, generate token.pickle locally first.
    """
    print("[Auth] POST /auth/google/authenticate: starting authentication")

    drive_service = get_drive_service()

    if not drive_service.is_configured():
        print(f"[Auth] POST /auth/google/authenticate: ERROR - credentials.json not found at {drive_service.credentials_path}")
        raise HTTPException(
            status_code=400,
            detail=f"credentials.json not found at {drive_service.credentials_path}. "
            "Download it from Google Cloud Console.",
        )

    try:
        print("[Auth] POST /auth/google/authenticate: calling authenticate(headless=False)")
        drive_service.authenticate(headless=False)
        print("[Auth] POST /auth/google/authenticate: SUCCESS")
        return AuthenticateResponse(
            success=True,
            message="Successfully authenticated with Google Drive",
        )
    except RuntimeError as e:
        print(f"[Auth] POST /auth/google/authenticate: RuntimeError - {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Auth] POST /auth/google/authenticate: ERROR - {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {e}",
        )


@router.post(
    "/auth/google/authenticate-headless",
    response_model=AuthenticateResponse,
    summary="Authenticate (headless mode)",
    description="Verify/refresh existing token without opening browser",
)
async def authenticate_google_drive_headless() -> AuthenticateResponse:
    """
    Authenticate with Google Drive in headless mode.

    This will:
    1. Check if credentials.json exists
    2. If token.pickle exists and is valid, use it
    3. If token is expired, refresh it
    4. If no token exists, return an error (won't open browser)

    Use this for server environments where browser interaction is not possible.
    """
    print("[Auth] POST /auth/google/authenticate-headless: starting headless authentication")

    drive_service = get_drive_service()

    if not drive_service.is_configured():
        print(f"[Auth] POST /auth/google/authenticate-headless: ERROR - credentials.json not found at {drive_service.credentials_path}")
        raise HTTPException(
            status_code=400,
            detail=f"credentials.json not found at {drive_service.credentials_path}. "
            "Download it from Google Cloud Console.",
        )

    try:
        print("[Auth] POST /auth/google/authenticate-headless: calling authenticate(headless=True)")
        drive_service.authenticate(headless=True)
        print("[Auth] POST /auth/google/authenticate-headless: SUCCESS")
        return AuthenticateResponse(
            success=True,
            message="Successfully authenticated with Google Drive (token refreshed)",
        )
    except RuntimeError as e:
        print(f"[Auth] POST /auth/google/authenticate-headless: RuntimeError - {e}")
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
    except Exception as e:
        print(f"[Auth] POST /auth/google/authenticate-headless: ERROR - {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {e}",
        )


@router.post(
    "/auth/google/revoke",
    response_model=AuthenticateResponse,
    summary="Revoke Google Auth",
    description="Delete stored token.pickle",
)
async def revoke_google_auth() -> AuthenticateResponse:
    """
    Revoke Google Drive authentication by deleting token.pickle.

    This will require re-authentication on next use.
    """
    print("[Auth] POST /auth/google/revoke: revoking Google Drive authentication")

    drive_service = get_drive_service()

    try:
        if drive_service.token_path.exists():
            print(f"[Auth] POST /auth/google/revoke: deleting {drive_service.token_path}")
            drive_service.token_path.unlink()
            print("[Auth] POST /auth/google/revoke: SUCCESS - token deleted")
            return AuthenticateResponse(
                success=True,
                message="Google Drive token revoked successfully",
            )
        else:
            print("[Auth] POST /auth/google/revoke: no token to revoke")
            return AuthenticateResponse(
                success=True,
                message="No token to revoke",
            )
    except Exception as e:
        print(f"[Auth] POST /auth/google/revoke: ERROR - {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke token: {e}",
        )
