import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.client import ClientOptions

from app.auth.errors import AuthError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
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
                ),
            )
        except (ValueError, TypeError) as error:
            raise AuthError(503, "Authentication configuration is invalid") from error
        yield client
