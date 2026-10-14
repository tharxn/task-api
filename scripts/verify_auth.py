"""Verify the live API and Supabase Auth without printing credentials or tokens.

Set AUTH_TEST_EMAIL and AUTH_TEST_PASSWORD in .env. Run with
--signup-if-needed once to register a new app user when login returns 401.
"""

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{os.getenv('PORT', '8000')}").rstrip("/")


def call(method, url, payload=None, token=None, api_key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["apikey"] = api_key
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=body, method=method, headers=headers)
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        data = response.read()
        return response.status, json.loads(data) if data else None


def api(method, path, expected, payload=None, token=None):
    status, data = call(method, BASE_URL + path, payload, token)
    if status != expected:
        raise SystemExit(f"FAIL: {method} {path}: expected {expected}, received {status}")
    print(f"PASS: {method} {path} -> {status}", flush=True)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signup-if-needed", action="store_true")
    args = parser.parse_args()
    email, password = os.getenv("AUTH_TEST_EMAIL"), os.getenv("AUTH_TEST_PASSWORD")
    if not email or not password:
        raise SystemExit("Set AUTH_TEST_EMAIL and AUTH_TEST_PASSWORD in the ignored .env file.")
    credentials = {"email": email, "password": password}

    api("GET", "/public/info", 200)
    api("GET", "/protected/profile", 401)
    api("POST", "/auth/login", 400, {})
    status, session = call("POST", BASE_URL + "/auth/login", credentials)
    if status == 401 and args.signup_if_needed:
        signup = api("POST", "/auth/signup", 201, credentials)
        if signup["confirmation_required"]:
            print("ACTION REQUIRED: Confirm the signup email, then rerun this script without --signup-if-needed.", flush=True)
            return 2
        status, session = call("POST", BASE_URL + "/auth/login", credentials)
    if status != 200:
        raise SystemExit(f"Login returned {status}. Confirm the app user's email and check the test password.")
    print("PASS: POST /auth/login -> 200; access and refresh tokens received (not printed)", flush=True)
    token = session["access_token"]
    refresh_token = session["refresh_token"]
    assert token and refresh_token

    api("POST", "/auth/login", 401, {"email": email, "password": f"wrong-{uuid4()}"})
    profile = api("GET", "/protected/profile", 200, token=token)
    assert profile["id"] and profile["created_at"]
    assert profile["email"].casefold() == email.casefold()
    dashboard = api("GET", "/protected/dashboard", 200, token=token)
    assert dashboard["user_id"] == profile["id"]

    parts = token.split(".")
    signature = parts[2]
    parts[2] = ("B" if signature[0] == "A" else "A") + signature[1:]
    api("GET", "/protected/profile", 401, token=".".join(parts))
    api("GET", "/protected/dashboard", 401, token="not-a-jwt")
    api("POST", "/auth/logout", 401)
    api("POST", "/auth/logout", 204, token=token)

    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    refresh_status, _ = call(
        "POST", supabase_url.rstrip("/") + "/auth/v1/token?grant_type=refresh_token",
        {"refresh_token": refresh_token}, api_key=key,
    )
    if refresh_status not in (400, 401):
        raise SystemExit(f"FAIL: Refresh token after logout returned {refresh_status}")
    print(f"PASS: Supabase rejects the revoked refresh token -> {refresh_status}", flush=True)
    access_status, _ = call("GET", BASE_URL + "/protected/profile", token=token)
    assert access_status in (200, 401)
    print(f"INFO: Access JWT after logout -> {access_status}; Supabase JWTs can remain valid until expiry.", flush=True)
    print("PASS: Live Supabase authentication flow completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
