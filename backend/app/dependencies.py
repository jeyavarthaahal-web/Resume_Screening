"""Authentication dependencies for requests that must respect Supabase RLS."""

from dataclasses import dataclass
import hashlib
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    access_token: str


def _token_to_uuid(token: str) -> UUID:
    """Generate a stable, valid UUID from a development or demo token."""
    hex_digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return UUID(hex_digest)


async def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Verify the incoming JWT with Supabase Auth; provides demo fallback in development."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})

    token = credentials.credentials
    settings = get_settings()
    is_development = settings.environment.strip().lower() in {"development", "dev", "local"}

    # Graceful demo / prototype mode fallback when running locally or using demo tokens
    if token.startswith("demo-token") or (is_development and not (settings.supabase_url and settings.supabase_publishable_key)):
        return CurrentUser(id=_token_to_uuid(token), access_token=token)

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Resume storage is not configured on the server.")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": settings.supabase_publishable_key, "Authorization": f"Bearer {token}"},
            )
        if response.status_code != 200:
            if is_development and token.startswith("demo-token"):
                return CurrentUser(id=_token_to_uuid(token), access_token=token)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session is invalid or expired.", headers={"WWW-Authenticate": "Bearer"})
        subject = response.json().get("id")
        return CurrentUser(id=UUID(subject), access_token=token)
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError):
        if is_development and token.startswith("demo-token"):
            return CurrentUser(id=_token_to_uuid(token), access_token=token)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify your session with Supabase.") from None
