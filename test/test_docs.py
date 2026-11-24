"""The article must quote the same values the stack uses. Run: python -I test/test_docs.py"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class ArticleMatchesStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.article = read("README.md")
        cls.realm = json.loads(read("keycloak", "realm-vscode.json"))
        cls.script = read("test", "configure-iris.script")
        cls.client = cls.realm["clients"][0]

    def test_quotes_issuer(self):
        self.assertIn("http://keycloak:8080/realms/vscode", self.article)

    def test_quotes_client_and_redirect_uri(self):
        self.assertIn(self.client["clientId"], self.article)
        self.assertIn(self.client["redirectUris"][0], self.article)

    def test_quotes_audience_from_realm(self):
        aud = next(m["config"]["included.custom.audience"] for m in self.client["protocolMappers"]
                   if m["protocolMapper"] == "oidc-audience-mapper")
        self.assertIn(aud, self.article)

    def test_quotes_authenticator_settings_from_script(self):
        for literal in ("preferred_username", "iris_roles", "iris:", "VSCode Resource Server",
                        "%OAuth2.ResourceServer.SimpleAuthenticator"):
            self.assertIn(literal, self.script)
            self.assertIn(literal, self.article)

    def test_links_part_one(self):
        self.assertIn("https://openexchange.intersystems.com/package/OAuth2-Native-Authentication-for-Web-Applications",
                      self.article)

    def test_vscode_settings_block_is_valid_json(self):
        block = re.search(r'<code class="language-json">(\{\s*"intersystems\.servers".*?)</code>', self.article, re.S)
        self.assertIsNotNone(block, "settings.json example not found")
        servers = json.loads(block.group(1))["intersystems.servers"]
        server = next(iter(servers.values()))
        self.assertEqual(server["oauth2"], {"authority": "http://keycloak:8080/realms/vscode", "clientId": "vscode-iris"})
        self.assertEqual(server["webServer"], {"scheme": "http", "host": "localhost", "port": 52773})

    def test_open_exchange_listing_exists(self):
        self.assertIn("OAuth2 Login from VS Code", read("docs", "open-exchange.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
