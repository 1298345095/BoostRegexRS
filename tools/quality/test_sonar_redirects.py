"""Check bearer-token audience boundaries without sending real HTTP requests."""

import unittest
from unittest.mock import MagicMock, patch
from urllib.request import Request

import collect_sonar_evidence as collector


class SonarRedirectTests(unittest.TestCase):
    def setUp(self):
        self.handler = collector.ScopedRedirectHandler()
        self.request = Request(
            "https://sonarcloud.io/api/issues/search",
            headers={"Authorization": "Bearer synthetic-test-token", "Accept": "application/json"},
        )

    def redirect(self, destination, request=None):
        return self.handler.redirect_request(
            request or self.request, None, 302, "Found", {}, destination)

    def test_same_origin_preserves_authentication(self):
        redirected = self.redirect("https://SONARCLOUD.IO:443/api/qualitygates/project_status")
        self.assertEqual(redirected.get_header("Authorization"), "Bearer synthetic-test-token")

    def test_cross_host_removes_authentication(self):
        redirected = self.redirect("https://other.example.invalid/result")
        self.assertFalse(redirected.has_header("Authorization"))
        self.assertEqual(redirected.get_header("Accept"), "application/json")
        self.assertEqual(self.request.get_header("Authorization"), "Bearer synthetic-test-token")

    def test_cross_port_removes_authentication(self):
        self.assertFalse(self.redirect("https://sonarcloud.io:8443/result").has_header("Authorization"))

    def test_https_downgrade_removes_authentication(self):
        self.assertFalse(self.redirect("http://sonarcloud.io:443/result").has_header("Authorization"))

    def test_a_later_redirect_cannot_restore_stripped_credentials(self):
        first = self.redirect("https://other.example.invalid/first")
        second = self.redirect("https://other.example.invalid/second", request=first)
        self.assertFalse(second.has_header("Authorization"))

    def test_anonymous_redirects_do_not_add_credentials(self):
        request = Request("https://sonarcloud.io/api/issues/search")
        self.assertFalse(self.redirect("https://sonarcloud.io/result", request=request)
                         .has_header("Authorization"))

    def test_fetch_uses_the_scoped_handler_and_finite_http_timeout(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"valid": true}'
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response
        with patch.object(collector.urllib.request, "build_opener", return_value=opener) as build:
            result = collector.fetch("https://sonarcloud.io/api/authentication/validate", "synthetic-test-token")
        self.assertIsInstance(build.call_args.args[0], collector.ScopedRedirectHandler)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-test-token")
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 30})
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["payload"], {"valid": True})


if __name__ == "__main__":
    unittest.main()
