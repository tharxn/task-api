import base64
import json
import time
import unittest

import httpx
from fastapi.testclient import TestClient
from supabase import create_client
from supabase.client import ClientOptions

from app.auth.client import get_supabase_client
from app.main import app


USER = {
    "id": "d9ef0b1c-5821-471f-b23e-7faaf61154c7",
    "aud": "authenticated",
    "role": "authenticated",
    "email": "person@example.com",
    "created_at": "2026-10-14T00:00:00Z",
    "app_metadata": {"provider": "email"},
    "user_metadata": {},
}


def test_access_token():
    # Fixture only: the mocked Auth server decides validity. Production never
    # decodes an unverified JWT or accepts these test credentials.
    encode = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    return f"{encode({'alg': 'HS256'})}.{encode({'sub': USER['id'], 'exp': int(time.time()) + 3600})}.fixture"


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.access_token = test_access_token()
        self.provider_status = None

        def transport(request):
            self.calls.append(request)
            if self.provider_status:
                return httpx.Response(
                    self.provider_status,
                    json={"msg": "provider detail must not leak", "code": "invalid_credentials"},
                )
            if request.url.path == "/auth/v1/signup":
                return httpx.Response(200, json=USER)
            if request.url.path == "/auth/v1/token":
                return httpx.Response(200, json={
                    "access_token": self.access_token,
                    "refresh_token": "fixture-refresh-token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "expires_at": int(time.time()) + 3600,
                    "user": USER,
                })
            return httpx.Response(404)

        self.transport = transport

        def mock_supabase():
            with httpx.Client(transport=httpx.MockTransport(self.transport)) as http_client:
                yield create_client(
                    "https://example.supabase.co", "test-publishable-key",
                    options=ClientOptions(
                        httpx_client=http_client, auto_refresh_token=False, persist_session=False,
                    ),
                )

        app.dependency_overrides[get_supabase_client] = mock_supabase
        self.addCleanup(app.dependency_overrides.clear)
        self.http = TestClient(app)
        self.addCleanup(self.http.close)

    def test_signup_returns_user_and_confirmation_state(self):
        response = self.http.post("/auth/signup", json={"email": USER["email"], "password": "valid-password"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["user"]["id"], USER["id"])
        self.assertTrue(response.json()["confirmation_required"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(json.loads(self.calls[0].content)["password"], "valid-password")

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.http.post("/auth/login", json={"email": USER["email"], "password": "valid-password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["access_token"], self.access_token)
        self.assertEqual(response.json()["refresh_token"], "fixture-refresh-token")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.calls[0].url.params["grant_type"], "password")

    def test_missing_or_blank_credentials_return_400(self):
        bodies = (None, {}, {"email": USER["email"]}, {"password": "password"},
                  {"email": " ", "password": "password"}, {"email": USER["email"], "password": " "})
        for path in ("/auth/signup", "/auth/login"):
            for body in bodies:
                with self.subTest(path=path, body=body):
                    response = self.http.post(path, json=body)
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(response.json(), {"error": "Email and password are required"})
        self.assertEqual(self.calls, [])

    def test_wrong_password_returns_safe_401(self):
        self.provider_status = 400
        response = self.http.post("/auth/login", json={"email": USER["email"], "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Invalid login credentials"})
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_signup_provider_rejection_is_400(self):
        self.provider_status = 422
        response = self.http.post("/auth/signup", json={"email": "invalid", "password": "short"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("provider detail", response.text)

    def test_rate_limit_is_not_misreported_as_wrong_credentials(self):
        self.provider_status = 429
        response = self.http.post("/auth/login", json={"email": USER["email"], "password": "password"})
        self.assertEqual(response.status_code, 429)
