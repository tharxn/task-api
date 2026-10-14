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
            if request.url.path == "/auth/v1/user":
                if request.headers.get("authorization") == f"Bearer {self.access_token}":
                    return httpx.Response(200, json=USER)
                return httpx.Response(401, json={"msg": "Invalid JWT", "code": "bad_jwt"})
            if request.url.path == "/auth/v1/logout":
                return httpx.Response(204)
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

    def test_public_info_is_open(self):
        response = self.http.get("/public/info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Welcome stranger! This info is public."})
        self.assertEqual(self.calls, [])

    def test_missing_or_malformed_bearer_headers_are_401(self):
        for header in (None, "", "Bearer", "Basic abc", "Bearer a b", "Bearer  "):
            with self.subTest(header=header):
                headers = {"Authorization": header} if header is not None else {}
                response = self.http.get("/protected/profile", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"error": "Access token required"})
        self.assertEqual(self.calls, [])

    def test_unverified_token_cannot_open_the_profile(self):
        response = self.http.get("/protected/profile", headers={"Authorization": "Bearer unverified"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Invalid or expired token"})

    def test_valid_token_is_verified_by_supabase(self):
        response = self.http.get("/protected/profile", headers={"Authorization": f"Bearer {self.access_token}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()), {"id", "email", "created_at"})
        self.assertEqual(response.json()["id"], USER["id"])
        self.assertEqual(self.calls[-1].url.path, "/auth/v1/user")
        self.assertEqual(self.calls[-1].headers["authorization"], f"Bearer {self.access_token}")

    def test_tampered_or_expired_tokens_are_rejected(self):
        for token in (self.access_token + "tampered", "expired.fixture.token"):
            with self.subTest(token=token):
                response = self.http.get("/protected/profile", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"error": "Invalid or expired token"})

    def test_provider_outage_fails_closed_with_503(self):
        self.provider_status = 503
        response = self.http.get("/protected/profile", headers={"Authorization": f"Bearer {self.access_token}"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("provider detail", response.text)

    def test_dashboard_reuses_the_verified_user_dependency(self):
        response = self.http.get("/protected/dashboard", headers={"Authorization": f"Bearer {self.access_token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], USER["id"])

    def test_all_protected_routes_reject_missing_and_invalid_tokens(self):
        for method, path in (("GET", "/protected/profile"), ("GET", "/protected/dashboard"), ("POST", "/auth/logout")):
            for token in (None, "invalid-token"):
                with self.subTest(method=method, path=path, token=token):
                    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
                    self.assertEqual(self.http.request(method, path, headers=headers).status_code, 401)

    def test_logout_verifies_user_then_signs_out_only_their_session(self):
        response = self.http.post("/auth/logout", headers={"Authorization": f"Bearer {self.access_token}"})
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertEqual([call.url.path for call in self.calls], ["/auth/v1/user", "/auth/v1/logout"])
        self.assertEqual(self.calls[-1].headers["authorization"], f"Bearer {self.access_token}")
        self.assertEqual(self.calls[-1].url.params["scope"], "local")

    def test_swagger_marks_only_auth_required_routes_as_locked(self):
        schema = self.http.get("/openapi.json").json()
        self.assertEqual(schema["components"]["securitySchemes"]["SupabaseBearer"]["scheme"], "bearer")
        for path, method in (("/protected/profile", "get"), ("/protected/dashboard", "get"), ("/auth/logout", "post")):
            self.assertEqual(schema["paths"][path][method]["security"], [{"SupabaseBearer": []}])
        for path, method in (("/public/info", "get"), ("/auth/signup", "post"), ("/auth/login", "post")):
            self.assertNotIn("security", schema["paths"][path][method])

    def test_duplicate_authorization_headers_are_rejected(self):
        response = self.http.get("/protected/profile", headers=[
            ("Authorization", f"Bearer {self.access_token}"),
            ("Authorization", "Bearer second-token"),
        ])
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.calls, [])
