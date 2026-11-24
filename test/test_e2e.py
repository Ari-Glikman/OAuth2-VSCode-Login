"""End-to-end checks against the running stack. Run: python -I test/test_e2e.py"""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import get_token as kc  # noqa: E402

AUDIENCE = "http://localhost:52773/"
IRIS = "http://localhost:52773"


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


class AtelierTest(unittest.TestCase):
    """IRIS side: /api/atelier accepts the token the way VS Code presents it."""

    @classmethod
    def setUpClass(cls):
        cls.token = kc.get_token("dev1", "123")

    def test_atelier_accepts_vscode_token(self):
        self.assertEqual(kc.call(IRIS + "/api/atelier/", self.token), 200)

    def test_developer_can_list_user_namespace(self):
        self.assertEqual(kc.call(IRIS + "/api/atelier/v1/USER/docnames/CLS", self.token), 200)

    def test_bogus_token_rejected(self):
        self.assertEqual(kc.call(IRIS + "/api/atelier/", "abc.def.ghi"), 401)

    def test_iris_user_gets_only_prefixed_roles(self):
        out = subprocess.run(
            ["docker", "exec", "-i", "vscode-oauth-iris", "iris", "session", "IRIS", "-U", "%SYS"],
            input='s sc=##class(Security.Users).Get("dev1",.p) w "ROLES=",$g(p("Roles")),!\nhalt\n',
            capture_output=True, text=True).stdout
        self.assertIn("ROLES=%Developer\n", out.replace("\r", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
