# VS Code OAuth2 login to IRIS — design (short)

## Intent
Sequel to the article/Open Exchange package "OAuth2 Native Authentication for Web Applications"
(bank demo). Show one thing only: signing in to IRIS from VS Code (Server Manager) with OAuth2,
using IRIS's native OAuth2 web-app authentication. Audience: developers who read part 1.

## Goals / non-goals
- Goal: smallest working stack plus an article a reader can follow in ~15 minutes.
- Non-goals: bank demo, delegated auth / ZAUTHENTICATE, custom login pages, HTTPS, production hardening.
- Anti-goal: requiring any ObjectScript.

## Approaches considered
1. **Built-in SimpleAuthenticator, Keycloak pre-configured, IRIS configured manually (chosen).**
   No code; mirrors part 1's structure (Keycloak ready, IRIS steps in the article).
2. Custom authenticator class (as in part 1) — more to read, adds nothing for this use case.
3. Fully scripted IRIS config — less to teach; the portal walkthrough is the point of the article.

## Decisions
- New repo `OAuth2-VSCode-Login` next to the part 1 repo.
- `docker-compose.yml`: `iris-community` (port 52773) + Keycloak (`quay.io/keycloak/keycloak:26.4`, `start-dev`, port 8080).
- Hostname `keycloak` via hosts file (same as part 1) so the issuer `http://keycloak:8080/realms/vscode`
  is identical from the host and from inside the IRIS container.
- Realm import `vscode`:
  - public client `vscode-iris`, standard flow only, PKCE S256,
    redirect URI `vscode://intersystems-community.servermanager/oauth2-callback`;
  - Audience mapper (custom audience `http://localhost:52773/` — Server Manager's audience is
    `<scheme>://<host>:<port>/` of the server definition; Keycloak ignores the `audience` parameter);
  - realm role mapper exposing realm roles as top-level claim `iris_roles`;
  - realm role `iris:%Developer`; user `dev1` / `123` holding it. (Builder's call: the `iris:` prefix
    lets SimpleAuthenticator's `Prefix` drop Keycloak's own roles such as `offline_access`.)
- IRIS, configured by the reader in the portal (article steps):
  1. OAuth2 server description, issuer `http://keycloak:8080/realms/vscode`.
  2. Resource server: audience `http://localhost:52773/`, authenticator
     `%OAuth2.ResourceServer.SimpleAuthenticator` (UserClaim `preferred_username`, RoleClaim `iris_roles`,
     Prefix `iris:`).
  3. Enable OAuth2 system-wide; set `/api/atelier` to OAuth2 **only**.
  4. VS Code `intersystems.servers` entry with `oauth2: { authority, clientId }`.
- Troubleshooting section: Audience vs Audience Resolve mapper; public client required;
  don't combine OAuth2 with delegated on `/api/atelier`; ERROR #936 when the IRIS username already
  exists with another login type; sign out of the cached VS Code session.
- Article format: HTML-ish markdown like part 1's README (Developer Community post style).

## Left to the builder
Screenshots (placeholders in the draft), exact Open Exchange metadata text, LICENSE (MIT, as part 1).
