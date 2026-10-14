import os
import unittest
from unittest.mock import patch

from app.auth.client import get_supabase_client, supabase_settings
from app.auth.errors import AuthError


class SupabaseClientTests(unittest.TestCase):
    def test_missing_configuration_is_explicit(self):
        with patch.dict(os.environ, {
            "SUPABASE_URL": "", "SUPABASE_KEY": "",
            "NEXT_PUBLIC_SUPABASE_URL": "", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "",
        }):
            with self.assertRaises(AuthError) as error:
                next(get_supabase_client())
        self.assertEqual(error.exception.status_code, 503)

    def test_frontend_style_environment_names_are_supported(self):
        with patch.dict(os.environ, {
            "SUPABASE_URL": "", "SUPABASE_KEY": "",
            "NEXT_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
            "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "test-publishable-key",
        }):
            self.assertEqual(supabase_settings(), ("https://example.supabase.co", "test-publishable-key"))

    def test_clients_and_sessions_are_isolated_and_closed(self):
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "test-publishable-key",
        }):
            first_request, second_request = get_supabase_client(), get_supabase_client()
            try:
                first, second = next(first_request), next(second_request)
                self.assertIsNot(first, second)
                self.assertIsNone(first.auth.get_session())
                self.assertIsNone(second.auth.get_session())
                first_http = first.options.httpx_client
                second_http = second.options.httpx_client
            finally:
                first_request.close()
                second_request.close()
            self.assertTrue(first_http.is_closed)
            self.assertTrue(second_http.is_closed)
