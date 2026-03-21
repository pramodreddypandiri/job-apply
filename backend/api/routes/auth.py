"""Auth routes — Gmail OAuth flow."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from backend.config import get_settings
import httpx
from loguru import logger

router = APIRouter()


@router.get("/gmail/connect")
async def gmail_connect():
    """Redirect user to Google OAuth consent screen for Gmail access."""
    settings = get_settings()
    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": settings.gmail_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/gmail/callback")
async def gmail_callback(code: str, request: Request):
    """Handle OAuth callback. Exchange code for tokens, store refresh token."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": settings.gmail_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if response.status_code != 200:
        logger.error(f"Gmail OAuth token exchange failed: {response.text}")
        raise HTTPException(status_code=400, detail="Gmail OAuth failed")

    tokens = response.json()
    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token received. Re-consent required.")

    # TODO: Store encrypted refresh token in users_profile
    # For now, log success and redirect to frontend
    logger.info("Gmail OAuth completed successfully")

    return RedirectResponse("http://localhost:3000/profile?gmail=connected")
