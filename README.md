<h2><u><strong>Logging in to IRIS from VS Code with OAuth2</strong></u></h2>
<p>As of IRIS 2025.2, OAuth2 is a native authentication type for web applications: a client presents an access token from your identity provider, and IRIS validates it and turns its claims into an IRIS user with roles. No custom login code is needed.</p>
<p>This article applies that to a client you use every day: <strong>VS Code</strong>. Since version 3.14, the InterSystems Server Manager extension can sign in to IRIS with OAuth2. You log in once in the browser with your identity provider, and VS Code uses the resulting access token for every request it sends to IRIS. There is no IRIS password in your <code>settings.json</code>, and no IRIS password at all for the developer.</p>
<p>The setup is small: a Keycloak realm with one client, one IRIS resource server, and one web application setting. No ObjectScript is required.</p>

<h3>How it fits together</h3>
<ul>
<li><strong>Client:</strong> VS Code (InterSystems Server Manager). It runs the login in your browser using the authorization code flow with PKCE.</li>
<li><strong>Authorization Server:</strong> Keycloak. It authenticates the developer and issues the access token.</li>
<li><strong>Resource Server:</strong> IRIS, specifically the <code>/api/atelier</code> web application, which is the REST API VS Code uses for everything (browsing namespaces, opening and saving classes, compiling).</li>
</ul>
<p>Every request from VS Code to <code>/api/atelier</code> carries <code>Authorization: Bearer &lt;token&gt;</code>. IRIS validates the token and maps its claims to an IRIS username and roles.</p>

<h3>Step 0: Prerequisites</h3>
<p><strong>Note:</strong> This demo uses HTTP to keep the setup simple. In production, use HTTPS everywhere; an access token is as good as a password while it is valid.</p>
<ul>
<li>Docker, VS Code, and the <a href="https://marketplace.visualstudio.com/items?itemName=intersystems-community.servermanager" target="_blank">InterSystems Server Manager</a> extension, version <strong>3.14 or later</strong>.</li>
<li>A hosts entry for Keycloak. Add this line to <em>C:\Windows\System32\drivers\etc\hosts</em> (Windows) or <em>/etc/hosts</em> (Linux/Mac):
<blockquote><p>127.0.0.1 keycloak</p></blockquote>
The token's issuer (<code>iss</code>) must be identical for VS Code, which runs on your machine, and for IRIS, which runs in a container. Using the name <code>keycloak</code> in both places guarantees that.</li>
<li>Ports 8080 (Keycloak) and 52773 (IRIS) free on your machine. Stop any other container or local service using them.</li>
</ul>
<p>Clone the repository and start the two containers (Keycloak takes a few seconds to come up):</p>
<pre class="codeblock-container" idlang="0" lang="Shell" tabsize="4"><code class="language-bash">git clone https://github.com/Ari-Glikman/OAuth2-VSCode-Login
cd OAuth2-VSCode-Login
docker compose up -d</code></pre>
<p>The IRIS Management Portal is at <a href="http://localhost:52773/csp/sys/UtilHome.csp" target="_blank">http://localhost:52773/csp/sys/UtilHome.csp</a> (<code>_SYSTEM</code> / <code>SYS</code>). The compose file keeps the default passwords for this demo, so there's no password-change prompt. <code>SuperUser</code> and <code>Admin</code> also use <code>SYS</code>.</p>

<h3>Step 1: Configure the Authorization Server (Keycloak)</h3>
<p>Open the Keycloak admin console at <a href="http://keycloak:8080/admin/" target="_blank">http://keycloak:8080/admin/</a> and log in as <code>admin</code> / <code>admin</code>. You'll create a realm, a role, a user, and the client VS Code will use. The client settings are the part to reproduce in your own identity provider later.</p>

<h4>1a. Realm</h4>
<p>Create a realm named <code>vscode</code>. Its issuer, <code>http://keycloak:8080/realms/vscode</code>, is the URL both IRIS and VS Code will use.</p>

<h4>1b. Role and user</h4>
<ul>
<li><em>Realm roles &gt; Create role</em>: name it <code>iris:%Developer</code>. The <code>iris:</code> prefix marks it as a role meant for IRIS; Step 3 explains how IRIS uses it.</li>
<li><em>Users &gt; Create new user</em>: username <code>dev1</code>, with an email, first name and last name filled in and <em>Email verified</em> on. Otherwise Keycloak asks the user to complete their profile at the first login.</li>
<li>On the user's <em>Credentials</em> tab, set the password <code>123</code> with <em>Temporary</em> off.</li>
<li>On the user's <em>Role mapping</em> tab, <em>Assign role</em>: <code>iris:%Developer</code> (filter by realm roles).</li>
</ul>
<!-- screenshot: dev1 role mapping -->

<h4>1c. The client</h4>
<p><em>Clients &gt; Create client</em>:</p>
<ul>
<li><strong>General settings:</strong> client type <em>OpenID Connect</em>, Client ID <code>vscode-iris</code>.</li>
<li><strong>Capability config:</strong> <em>Client authentication</em> <strong>off</strong>, <em>Standard flow</em> on, <em>Direct access grants</em> off, PKCE method <code>S256</code>.</li>
<li><strong>Login settings:</strong> <em>Valid redirect URIs</em> <code>vscode://intersystems-community.servermanager/oauth2-callback</code>.</li>
</ul>
<!-- [CONFIRM] PKCE field location in your Keycloak version (Capability config "PKCE Method", or Advanced tab "Proof Key for Code Exchange Code Challenge Method") -->
<!-- screenshot: Capability config -->
<p>Why these settings:</p>
<ul>
<li><strong>Public client with PKCE.</strong> VS Code is a desktop application and can't keep a client secret, so Server Manager never sends one. If the client requires authentication, the login succeeds in the browser and then fails with <em>Invalid client or Invalid client credentials</em>.</li>
<li><strong>The <code>vscode://</code> redirect URI.</strong> After you log in, Keycloak redirects your browser to this URI and the operating system hands it to VS Code. It never travels over the network, so it works wherever Keycloak runs.</li>
</ul>

<h4>1d. Two mappers: audience and roles</h4>
<p>Open the client's <em>Client scopes</em> tab, click <code>vscode-iris-dedicated</code>, then <em>Configure a new mapper</em> (later: <em>Add mapper &gt; By configuration</em>):</p>
<ol>
<li><strong>Audience</strong>: name <code>iris-audience</code>, <em>Included Custom Audience</em> <code>http://localhost:52773/</code>, <em>Add to access token</em> on.<br>
IRIS only accepts tokens addressed to it, by checking the token's <code>aud</code> claim. Server Manager asks for an audience equal to the server's URL (<code>&lt;scheme&gt;://&lt;host&gt;:&lt;port&gt;/</code>), but Keycloak ignores that request parameter. Without this mapper the token's audience is just <code>account</code> and IRIS rejects it. Pick the mapper type <strong>Audience</strong>; the similarly named <em>Audience Resolve</em> does something else.</li>
<li><strong>User Realm Role</strong>: name <code>iris-roles</code>, <em>Token Claim Name</em> <code>iris_roles</code>, <em>Multivalued</em> on, <em>Add to access token</em> on.<br>
Keycloak normally nests realm roles inside <code>realm_access.roles</code>. This mapper also puts them in a top-level claim, <code>iris_roles</code>, which IRIS's built-in authenticator can read.</li>
</ol>
<!-- screenshot: vscode-iris-dedicated mappers list -->

<h3>Step 2: Tell IRIS who the Authorization Server is</h3>
<p><em>System Administration &gt; Security &gt; OAuth 2.0 &gt; Client</em>, <em>Create Server Description</em>, Issuer <code>http://keycloak:8080/realms/vscode</code>, then <em>Discover and Save</em>. IRIS downloads the realm's metadata: its endpoints and the keys it signs tokens with.</p>
<p>Leave <em>SSL/TLS configuration</em> empty. The portal only requires it when discovery uses HTTPS, and this demo's issuer is plain <code>http://</code>. With an <code>https://</code> issuer, as in production, first create a client SSL/TLS configuration (<em>System Administration &gt; Security &gt; SSL/TLS Configurations</em>) that trusts your identity provider's certificate, and select it here.</p>
<!-- screenshot: server description after discovery -->

<h3>Step 3: Create the Resource Server</h3>
<p><em>System Administration &gt; Security &gt; OAuth 2.0 &gt; Resource Server</em>, <em>Create Resource Server</em>:</p>
<ul>
<li><strong>Name:</strong> <code>VSCode Resource Server</code></li>
<li><strong>Server Definition:</strong> <code>http://keycloak:8080/realms/vscode</code></li>
<li><strong>Audiences:</strong> <code>http://localhost:52773/</code> (the same value as the Keycloak mapper, including the trailing slash)</li>
<li><strong>Authenticator:</strong> <code>%OAuth2.ResourceServer.SimpleAuthenticator</code>, with
  <ul>
  <li>User claim: <code>preferred_username</code></li>
  <li>Role claim: <code>iris_roles</code></li>
  <li>Prefix: <code>iris:</code></li>
  </ul></li>
</ul>
<p>The authenticator decides which IRIS user and roles a token becomes. You can write your own by subclassing <code>%OAuth2.ResourceServer.Authenticator</code>, but the built-in one is enough here. The <strong>prefix</strong> does two jobs: it ignores every role that doesn't start with <code>iris:</code> (Keycloak adds its own, such as <code>offline_access</code>), and it strips the prefix from the ones that do. <code>iris:%Developer</code> in Keycloak becomes the IRIS role <code>%Developer</code>.</p>
<!-- screenshot: resource server page with the authenticator settings -->
<!-- [CONFIRM] exact portal labels for the SimpleAuthenticator fields -->

<h3>Step 4: Enable OAuth2 on /api/atelier</h3>
<p>First allow OAuth2 system-wide (once per instance): <em>System Administration &gt; Security &gt; System Security &gt; Authentication/Web Session Options</em>, check <em>Allow OAuth2 authentication</em>.</p>
<!-- [CONFIRM] exact checkbox label -->
<p>Then open <em>System Administration &gt; Security &gt; Applications &gt; Web Applications &gt; /api/atelier</em>. Under <em>Allowed Authentication Methods</em>, select <strong>OAuth2 only</strong>, and choose <code>VSCode Resource Server</code> as the resource server for this application.</p>
<!-- [CONFIRM] where the portal associates the resource server with /api/atelier (per-application vs default) -->
<!-- screenshot: /api/atelier authentication methods -->
<p>Why only OAuth2? Keep it simple: when other methods are enabled alongside it, one of them can claim the request first. For example, a <code>ZAUTHENTICATE</code> routine whose <code>GetCredentials</code> always supplies credentials makes Delegated win, and the token is never looked at.</p>

<h3>Step 5: Sign in from VS Code</h3>
<p>Add the server to your VS Code <code>settings.json</code>. The new part is the <code>oauth2</code> block: the issuer as <code>authority</code>, and the Keycloak client ID.</p>
<pre class="codeblock-container" idlang="3" lang="JSON" tabsize="4"><code class="language-json">{
  "intersystems.servers": {
    "oauth-demo": {
      "webServer": {
        "scheme": "http",
        "host": "localhost",
        "port": 52773
      },
      "oauth2": {
        "authority": "http://keycloak:8080/realms/vscode",
        "clientId": "vscode-iris"
      },
      "description": "IRIS with OAuth2 (Keycloak)"
    }
  }
}</code></pre>
<p>In the InterSystems view, expand <em>oauth-demo</em>. VS Code opens your browser at the Keycloak login page; sign in as <code>dev1</code> / <code>123</code>, allow the browser to open VS Code, and the server's namespaces appear.</p>
<!-- screenshot: Keycloak login page opened by VS Code -->
<!-- screenshot: Server Manager tree showing namespaces -->
<p>In the Management Portal, under <em>Security &gt; Users</em>, you will now find the user <code>dev1</code> with the role <code>%Developer</code>. IRIS created it from the token's claims on the first request.</p>

<h3>Troubleshooting</h3>
<ul>
<li><strong>Keycloak says <em>Invalid parameter: redirect_uri</em>.</strong> The client's <em>Valid redirect URIs</em> doesn't contain <code>vscode://intersystems-community.servermanager/oauth2-callback</code>.</li>
<li><strong>VS Code says <em>Token exchange failed - Invalid client or Invalid client credentials</em>.</strong> The Keycloak client still requires client authentication. Make it public.</li>
<li><strong>Login works, IRIS answers 401.</strong> Check the audit log (<em>System Administration &gt; Security &gt; Auditing &gt; View Audit Database</em>, event <em>LoginFailure</em>). Its message tells you which part failed:
  <ul>
  <li><em>Delegated login failed</em>: another method on <code>/api/atelier</code> claimed the request. Make OAuth2 the only one.</li>
  <li><em>ERROR #936: User ... is not an OAuth2 user</em>: an IRIS user with that name already exists and was created by a different login method (for example, Delegated). Use another username or a prefix, or remove the old user.</li>
  <li>A token audience or issuer error: compare the token's <code>aud</code> and <code>iss</code> (paste it into a JWT decoder) with the resource server's Audiences and the server description's issuer. They must match exactly, trailing slash included.</li>
  </ul></li>
<li><strong>VS Code doesn't prompt you and still gets 401.</strong> It reuses its cached session. Sign out using the Accounts icon (bottom left) &gt; InterSystems Server Credentials, then connect again.</li>
<li><strong>VS Code says <em>OAuth2: Failed to discover endpoints from http://keycloak:8080/realms/vscode/.well-known/openid-configuration</em>, and no browser opens.</strong> VS Code itself contacts Keycloak (for discovery, and later for the token exchange), so the <code>127.0.0.1 keycloak</code> hosts entry is missing, or Keycloak is still starting.</li>
</ul>

<h3>Wrapping up</h3>
<p>Three IRIS building blocks, a server description, a resource server, and OAuth2 on a web application, are all it takes to protect the API VS Code talks to. The result: developers sign in to IRIS with the same identity provider they use for everything else, roles come from that identity provider, and no IRIS passwords live on developer machines.</p>
<p><strong>Related:</strong> to protect your own REST APIs the same way, with roles derived from OAuth2 scopes and a custom authenticator class, see <a href="https://openexchange.intersystems.com/package/OAuth2-Native-Authentication-for-Web-Applications" target="_blank">OAuth2 Native Authentication for Web Applications</a>.</p>
