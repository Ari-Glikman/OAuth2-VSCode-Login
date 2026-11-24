# VS Code OAuth2 Login to IRIS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A minimal Open Exchange repo (IRIS + Keycloak) plus a draft article showing VS Code Server Manager signing in to IRIS with native OAuth2.

**Architecture:** Docker Compose runs `iris-community` and Keycloak. Keycloak's realm import is fully pre-configured. IRIS is configured by the reader in the Management Portal (article walkthrough); a test-only script applies the same configuration so the stack can be verified end to end with a scripted PKCE login.

**Tech Stack:** Docker Compose, `containers.intersystems.com/intersystems/iris-community:latest-cd`, `quay.io/keycloak/keycloak:26.4`, Python 3 stdlib (test script), VS Code Server Manager ≥ 3.14.

**Spec:** `docs/superpowers/specs/2026-11-24-vscode-oauth2-login-design.md`

## Global Constraints

- Repo root: `OAuth/OAuth2-VSCode-Login/` (sibling of the part 1 repo).
- Realm `vscode`; issuer `http://keycloak:8080/realms/vscode` (hosts entry `127.0.0.1 keycloak` required, as in part 1).
- Keycloak client `vscode-iris`: public, standard flow only, PKCE `S256`, redirect URI `vscode://intersystems-community.servermanager/oauth2-callback`.
- Audience value everywhere: `http://localhost:52773/` (trailing slash).
- Role claim `iris_roles` (top-level, multivalued); Keycloak role `iris:%Developer`; SimpleAuthenticator `Prefix` `iris:`, `UserClaim` `preferred_username`, `RoleClaim` `iris_roles`.
- Demo user `dev1` / `123`. Keycloak admin `admin` / `admin`.
- Host ports 52773 (IRIS web) and 8080 (Keycloak). Container names `vscode-oauth-iris`, `vscode-oauth-keycloak`; compose service names `iris`, `keycloak`.
- `/api/atelier` authentication = OAuth2 **only** (`AutheEnabled=67108864`).
- No ObjectScript classes in the repo. No HTTPS. No bank demo content.
- LICENSE: MIT, same holder as part 1.

## Review Focus

- Reader whose `keycloak` hosts entry is missing → VS Code login page fails to load; article Step 0 must state the entry, troubleshooting must name the symptom.
- Port 8080/52773 already taken (e.g. part 1 stack still running) → compose fails to start; README must say to stop part 1 first.
- Unprefixed realm roles (`offline_access`, `default-roles-vscode`) reaching IRIS → must be filtered by `Prefix`; Task 2 test asserts IRIS user roles equal exactly `%Developer`.
- `%Developer` lacking USER database access → Atelier opens but namespace listing fails; Task 2 test calls `/api/atelier/v1/USER/docnames` and expects 200.
- Cached VS Code session after reconfiguring → silent 401; troubleshooting section covers sign-out.

> **Execution note:** the user's existing `iris` and `keycloak` containers (part 1 / Clalit work) hold ports 52773 and 8080. Before Tasks 1–2 verification, ask the user to approve stopping them (`docker stop iris keycloak kc26`) and restart them afterwards (`docker start keycloak kc26 iris`).

---

### Task 1: Compose stack and Keycloak realm

**Files:**
- Create: `docker-compose.yml`
- Create: `keycloak/realm-vscode.json`
- Create: `test/get_token.py`
- Create: `.gitignore` (`iris/durable/`), `LICENSE`

**Interfaces:**
- Produces: running Keycloak at `http://keycloak:8080` with realm `vscode`; IRIS container `vscode-oauth-iris` on `http://localhost:52773` (community default `_SYSTEM/SYS`; Task 2's script un-expires passwords so the portal doesn't force a change).
- Produces: `python -I test/get_token.py <user> <password> [--call <url>]` → prints token claims JSON (`iss`, `aud`, `azp`, `preferred_username`, `iris_roles`); with `--call`, prints `HTTP <status>` of a GET with the bearer token. Exit code 0 on token obtained.

- [ ] **Step 1: Write `test/get_token.py`** — PKCE auth-code flow against `http://keycloak:8080/realms/vscode/protocol/openid-connect`, client `vscode-iris`, scope `openid profile email offline_access`, redirect URI as above; scrape the login form `action`, post credentials, read `code` from the `Location` header (no redirect follow), exchange with `code_verifier`. Cookie policy must allow `Secure` cookies on http (`return_ok_secure` → True). Reuse the logic of `C:\temp\kc-test\get_token.py` from the session.
- [ ] **Step 2: Run it before the stack exists** — Run: `python -I test/get_token.py dev1 123` — Expected: connection error (stack not up).
- [ ] **Step 3: Write `docker-compose.yml`** — `keycloak`: `start-dev --import-realm --hostname=http://keycloak:8080`, `KC_BOOTSTRAP_ADMIN_USERNAME/PASSWORD=admin`, mount realm file to `/opt/keycloak/data/import/`; `iris`: community image, ports `52773:52773`, `1972:1972`, durable dir `ISC_DATA_DIRECTORY=/durable` on `./iris/durable`. Both on one network.
- [ ] **Step 4: Write `keycloak/realm-vscode.json`** — realm `vscode`, enabled; role `iris:%Developer`; user `dev1` (email verified, first/last name set so no "update profile" required action) with password `123` (non-temporary) and role `iris:%Developer`; client `vscode-iris` per Global Constraints with attribute `pkce.code.challenge.method=S256`, `directAccessGrantsEnabled=false`, protocol mappers: `oidc-audience-mapper` (`included.custom.audience=http://localhost:52773/`, access token on) and `oidc-usermodel-realm-role-mapper` (`claim.name=iris_roles`, `multivalued=true`, access token on).
- [ ] **Step 5: Start and verify** — Run: `docker compose up -d`, wait for discovery `http://keycloak:8080/realms/vscode/.well-known/openid-configuration` = 200, then `python -I test/get_token.py dev1 123`. Expected: `iss=http://keycloak:8080/realms/vscode`, `aud` contains `http://localhost:52773/`, `azp=vscode-iris`, `preferred_username=dev1`, `iris_roles` contains `iris:%Developer`. Also from IRIS: `%Net.HttpRequest` GET `keycloak:8080/realms/vscode` → 200.
- [ ] **Step 6: Commit** — `git init` (if needed), add files, `git commit -m "feat: IRIS + Keycloak stack with VS Code client realm"`.

### Task 2: IRIS configuration (test helper) and end-to-end Atelier check

**Files:**
- Create: `test/configure-iris.script` (ObjectScript terminal script, run with `iris session IRIS -U %SYS < ...`; not referenced by the article as the main path — mentioned only as "skip the walkthrough")

**Interfaces:**
- Consumes: Task 1 stack and `test/get_token.py --call`.
- Produces: IRIS objects whose names the article uses verbatim: server description issuer `http://keycloak:8080/realms/vscode`; resource server `VSCode Resource Server`; mapping `%Service_WebGateway` + `/api/atelier`; `/api/atelier` `AutheEnabled=67108864`.

- [ ] **Step 1: Verify failing state** — Run: `python -I test/get_token.py dev1 123 --call http://localhost:52773/api/atelier/` — Expected: `HTTP 401`.
- [ ] **Step 2: Write `test/configure-iris.script`** — idempotent: unexpire passwords; `%SYS.OAuth2.Registration.Discover` (or create `OAuth2.ServerDefinition` via discovery) for the issuer; create/update `OAuth2.ResourceServer` `VSCode Resource Server` (`ServerDefinition`, `AccessTokenIsJWT=1`, `Audiences=$lb("http://localhost:52773/")`, `Enabled=1`, `Authenticator=##class(%OAuth2.ResourceServer.SimpleAuthenticator).%New({"UserClaim":"preferred_username","RoleClaim":"iris_roles","Prefix":"iris:"})`); create mapping; set system `AutheEnabled` OAuth2 bit (67108864) on; set `/api/atelier` `AutheEnabled=67108864`. Write each step's status. Follow objectscript-guardrails.
- [ ] **Step 3: Apply** — Run: `docker exec -i vscode-oauth-iris iris session IRIS -U %SYS < test/configure-iris.script` — Expected: every step reports OK.
- [ ] **Step 4: End-to-end checks** — Run `get_token.py dev1 123 --call http://localhost:52773/api/atelier/` → `HTTP 200`; `--call http://localhost:52773/api/atelier/v1/USER/docnames/CLS` → `HTTP 200`; IRIS `Security.Users` row `dev1` has roles exactly `%Developer`. A request with a bogus bearer → 401.
- [ ] **Step 5: Real VS Code check (user)** — Ask the user to add the server definition from the article to VS Code and sign in as `dev1/123`; expected: server tree shows namespaces.
- [ ] **Step 6: Commit** — `git commit -m "test: scripted IRIS config and end-to-end Atelier check"`.

### Task 3: Article draft and Open Exchange description

**Files:**
- Create: `README.md` (the article; Developer Community HTML-in-markdown style, matching part 1's README)
- Create: `docs/open-exchange.md` (OEX listing: name "OAuth2 Login from VS Code", one-paragraph description, requirements, link to part 1 package)

**Interfaces:**
- Consumes: exact names/values from Global Constraints and Task 2 Produces.

- [ ] **Step 1: Write `README.md`** — sections: intro linking part 1 (`https://openexchange.intersystems.com/package/OAuth2-Native-Authentication-for-Web-Applications`); characters (VS Code = client, Keycloak = AS, IRIS `/api/atelier` = resource server); Step 0 prerequisites (hosts entry, stop part 1, `docker compose up -d`); Step 1 Keycloak (pre-configured; explain the three things that matter: public client + PKCE, VS Code redirect URI, Audience mapper — and the roles mapper); Step 2 server description; Step 3 resource server with SimpleAuthenticator values; Step 4 enable OAuth2 system-wide and on `/api/atelier` only; Step 5 VS Code settings JSON (`webServer` localhost:52773 http, `oauth2: { "authority": "http://keycloak:8080/realms/vscode", "clientId": "vscode-iris" }`) and sign-in; Troubleshooting (Audience vs Audience Resolve; confidential client → "Invalid client credentials"; delegated + OAuth2 together → delegated wins; ERROR #936 existing user of another type; cached session → sign out via Accounts menu; how to read the audit log). Screenshot placeholders as `<!-- screenshot: ... -->`.
- [ ] **Step 2: Verify article against the stack** — every value in the article (issuer, client id, audience, claim names, prefix, resource server name, AutheEnabled behaviour) matches `docker-compose.yml`, `realm-vscode.json`, and `configure-iris.script`; grep each literal.
- [ ] **Step 3: Write `docs/open-exchange.md`.**
- [ ] **Step 4: Commit** — `git commit -m "docs: article draft and Open Exchange listing"`.
