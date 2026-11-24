"""Log in to Keycloak the way VS Code Server Manager does (authorization code + PKCE, public client)
and optionally call an IRIS URL with the resulting bearer token.

Usage:
    python -I test/get_token.py <user> <password> [--call <url>]
"""
import base64
import hashlib
import html
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ISSUER = "http://keycloak:8080/realms/vscode"
CLIENT_ID = "vscode-iris"
REDIRECT_URI = "vscode://intersystems-community.servermanager/oauth2-callback"
SCOPE = "openid profile email offline_access"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class _LocalhostPolicy(http.cookiejar.DefaultCookiePolicy):
    # Keycloak marks its login cookies Secure; browsers still send them to plain-http hosts they
    # treat as local, Python does not.
    def return_ok_secure(self, cookie, request):
        return True


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def get_token(user: str, password: str) -> str:
    """Return an access token for user/password via the vscode-iris PKCE flow."""
    endpoint = ISSUER + "/protocol/openid-connect"
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(_LocalhostPolicy())), _NoRedirect)
    verifier = _b64url(os.urandom(40))
    query = urllib.parse.urlencode({
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": REDIRECT_URI, "scope": SCOPE,
        "state": "test", "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256"})
    page = opener.open(f"{endpoint}/auth?{query}").read().decode()
    form = re.search(r'action="([^"]+)"', page)
    if not form:
        raise RuntimeError("Keycloak login form not found")
    try:
        opener.open(html.unescape(form.group(1)),
                    urllib.parse.urlencode({"username": user, "password": password}).encode())
        raise RuntimeError("login did not redirect (wrong credentials or a required action?)")
    except urllib.error.HTTPError as e:
        location = e.headers.get("Location", "")
        e.close()
        if not location:
            raise RuntimeError(f"login returned HTTP {e.code} without a redirect") from None
    code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query).get("code", [None])[0]
    if not code:
        raise RuntimeError(f"no authorization code in redirect: {location[:200]}")
    body = urllib.parse.urlencode({"grant_type": "authorization_code", "client_id": CLIENT_ID, "code": code,
                                   "redirect_uri": REDIRECT_URI, "code_verifier": verifier}).encode()
    return json.load(opener.open(f"{endpoint}/token", body))["access_token"]


def claims(token: str) -> dict:
    """Decode a JWT's payload (no signature check; IRIS does that)."""
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def call(url: str, token: str) -> int:
    """GET url with the bearer token; return the HTTP status."""
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    tok = get_token(sys.argv[1], sys.argv[2])
    print(json.dumps({k: claims(tok).get(k) for k in ("iss", "aud", "azp", "preferred_username", "iris_roles")}))
    if "--call" in sys.argv:
        print("HTTP", call(sys.argv[sys.argv.index("--call") + 1], tok))
