"""End-to-end checks against the running stack. Run: python -I test/test_e2e.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import get_token as kc  # noqa: E402

AUDIENCE = "http://localhost:52773/"


class KeycloakTokenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = kc.get_token("dev1", "123")
        cls.claims = kc.claims(cls.token)

    def test_issuer_is_the_shared_hostname(self):
        self.assertEqual(self.claims["iss"], "http://keycloak:8080/realms/vscode")

    def test_audience_matches_server_manager(self):
        aud = self.claims["aud"]
        self.assertIn(AUDIENCE, aud if isinstance(aud, list) else [aud])

    def test_issued_to_vscode_client(self):
        self.assertEqual(self.claims["azp"], "vscode-iris")
        self.assertEqual(self.claims["preferred_username"], "dev1")

    def test_iris_roles_claim_is_top_level(self):
        self.assertIn("iris:%Developer", self.claims["iris_roles"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
