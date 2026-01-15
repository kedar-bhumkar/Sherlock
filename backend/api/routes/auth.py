"""Authentication API routes for Google Drive and TOTP."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

from services.google_drive_service import get_drive_service
from services.totp_service import get_totp_service

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


# =============================================================================
# TOTP Authentication Endpoints
# =============================================================================


class TOTPVerifyRequest(BaseModel):
    """Request for TOTP verification."""

    code: str = Field(..., description="The 6-digit TOTP code", min_length=6, max_length=6)


class TOTPVerifyResponse(BaseModel):
    """Response after TOTP verification."""

    success: bool = Field(..., description="Whether verification succeeded")
    token: Optional[str] = Field(None, description="Session token if verification succeeded")
    message: str = Field(..., description="Status message")


class TOTPStatusResponse(BaseModel):
    """Response for TOTP status check."""

    enabled: bool = Field(..., description="Whether TOTP authentication is enabled")
    configured: bool = Field(..., description="Whether TOTP secret is configured")


class SessionValidateResponse(BaseModel):
    """Response for session validation."""

    valid: bool = Field(..., description="Whether the session is valid")


@router.get(
    "/auth/totp/status",
    response_model=TOTPStatusResponse,
    summary="Check TOTP Auth Status",
    description="Check if TOTP authentication is enabled and configured",
)
async def check_totp_status() -> TOTPStatusResponse:
    """
    Check the current TOTP authentication status.

    Returns information about:
    - Whether TOTP is enabled in configuration
    - Whether a TOTP secret is configured
    """
    totp_service = get_totp_service()
    settings = totp_service.settings

    return TOTPStatusResponse(
        enabled=settings.totp_enabled,
        configured=bool(settings.totp_secret),
    )


@router.post(
    "/auth/totp/verify",
    response_model=TOTPVerifyResponse,
    summary="Verify TOTP Code",
    description="Verify a TOTP code and get a session token",
)
async def verify_totp(request: TOTPVerifyRequest) -> TOTPVerifyResponse:
    """
    Verify a TOTP code from an authenticator app.

    If verification succeeds, returns a session token for subsequent requests.
    The token is valid for 1 hour.
    """
    totp_service = get_totp_service()

    # Check if TOTP is configured
    if not totp_service.enabled:
        return TOTPVerifyResponse(
            success=True,
            token=None,
            message="TOTP authentication is disabled",
        )

    # Verify the code
    if not totp_service.verify_code(request.code):
        raise HTTPException(
            status_code=401,
            detail="Invalid TOTP code",
        )

    # Generate session token
    token = totp_service.generate_session_token()

    return TOTPVerifyResponse(
        success=True,
        token=token,
        message="Authentication successful",
    )


@router.post(
    "/auth/session/validate",
    response_model=SessionValidateResponse,
    summary="Validate Session",
    description="Check if a session token is valid",
)
async def validate_session(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> SessionValidateResponse:
    """
    Validate a session token.

    Pass the token in the Authorization header as "Bearer <token>".
    """
    totp_service = get_totp_service()

    # If TOTP is disabled, always return valid
    if not totp_service.enabled:
        return SessionValidateResponse(valid=True)

    # Extract token from header
    if not authorization or not authorization.startswith("Bearer "):
        return SessionValidateResponse(valid=False)

    token = authorization[7:]  # Remove "Bearer " prefix
    is_valid = totp_service.validate_session_token(token)

    return SessionValidateResponse(valid=is_valid)


@router.post(
    "/auth/logout",
    response_model=AuthenticateResponse,
    summary="Logout",
    description="Invalidate the current session",
)
async def logout(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> AuthenticateResponse:
    """
    Logout by invalidating the current session token.

    Pass the token in the Authorization header as "Bearer <token>".
    """
    totp_service = get_totp_service()

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        totp_service.invalidate_session(token)

    return AuthenticateResponse(
        success=True,
        message="Logged out successfully",
    )
