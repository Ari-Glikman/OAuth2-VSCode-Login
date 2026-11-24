# Open Exchange listing (draft)

**Name:** OAuth2 Login from VS Code

**Short description:** Sign in to InterSystems IRIS from VS Code with OAuth2. Keycloak issues the token and IRIS validates it natively. No passwords, no ObjectScript.

**Description:**
A minimal, ready-to-run example of logging in to IRIS from VS Code (InterSystems Server Manager 3.14+) with OAuth2, using IRIS's native OAuth2 authentication for web applications (IRIS 2025.2+). Docker Compose starts IRIS and a pre-configured Keycloak realm: a public PKCE client for VS Code, an audience mapper, and a role mapper. The article walks through the three IRIS settings needed: a server description, a resource server using the built-in `%OAuth2.ResourceServer.SimpleAuthenticator`, and OAuth2 on `/api/atelier`. A script applies the same settings in one step, and a small Python test performs the same login as VS Code.

Sequel to [OAuth2 Native Authentication for Web Applications](https://openexchange.intersystems.com/package/OAuth2-Native-Authentication-for-Web-Applications).

**Requirements:** Docker; VS Code with InterSystems Server Manager 3.14+; hosts entry `127.0.0.1 keycloak`; IRIS 2025.2+ (the demo uses `iris-community:latest-cd`).

**Category / tags:** Security, OAuth2, VS Code, Keycloak, Docker

**Repository:** https://github.com/Ari-Glikman/OAuth2-VSCode-Login *(to be created)*

**License:** MIT
