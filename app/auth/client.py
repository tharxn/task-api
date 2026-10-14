import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import Client, SupabaseException, create_client
from supabase.client import ClientOptions

from app.auth.errors import AuthError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def supabase_settings() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    return url.strip(), key.strip()


def get_supabase_client():
    url, key = supabase_settings()
    if not url or not key:
        raise AuthError(503, "Authentication is not configured")
    # Each request gets its own client; one user's session cannot affect another.
    with httpx.Client(timeout=10) as http_client:
        try:
            client: Client = create_client(
                url,
                key,
                options=ClientOptions(
                    persist_session=False,
                    auto_refresh_token=False,
                    httpx_client=http_client,
                    flow_type="implicit",
                ),
            )
        except (SupabaseException, ValueError, TypeError) as error:
            raise AuthError(503, "Authentication configuration is invalid") from error
        yield client


def check_supabase_connection() -> None:
    url, key = supabase_settings()
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url.rstrip("/") + "/auth/v1/health", headers={"apikey": key})
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise AuthError(503, "Authentication service unavailable") from error
