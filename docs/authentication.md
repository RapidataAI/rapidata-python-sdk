# Authentication

The Rapidata API uses **OAuth 2.0 / OpenID Connect**. The authorization server is
`https://auth.rapidata.ai`, and its discovery document is published at
[`/.well-known/openid-configuration`](https://auth.rapidata.ai/.well-known/openid-configuration).

For programmatic access (the SDK, scripts, agents) you authenticate with the
**client credentials** grant using a client ID and secret.

## Get credentials

Create a client ID and secret under [Rapidata Settings → Tokens](https://app.rapidata.ai/settings/tokens).

## With the SDK

The SDK performs the token exchange for you. Pass the credentials directly:

```python
from rapidata import RapidataClient

client = RapidataClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
)
```

or set `RAPIDATA_CLIENT_ID` and `RAPIDATA_CLIENT_SECRET` in the environment
(useful for headless or containerised runs) and construct `RapidataClient()`
with no arguments. On a workstation, calling `RapidataClient()` with no
credentials instead opens a browser login once and caches the token in
`~/.config/rapidata/credentials.json`.

## Direct token request

To call the API without the SDK, request a token from the token endpoint and
send it as a bearer token:

```bash
curl -X POST https://auth.rapidata.ai/connect/token \
  -d grant_type=client_credentials \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d scope="openid email roles"

# → {"access_token": "...", "token_type": "Bearer", "expires_in": 3600}

curl https://api.rapidata.ai/order/openapi/v1.json \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

## Scopes

Tokens are scoped. The SDK requests `openid roles email` by default, which is
sufficient for all SDK operations. Request only the scopes you need. Every
endpoint in the [OpenAPI specification](https://docs.rapidata.ai/openapi.json)
declares the scopes it requires under its `OpenIdConnect` security scheme.

| Scope | Grants |
|-------|--------|
| `openid` | Required for OIDC; identifies the token subject. |
| `email` | Access to the account email claim. |
| `roles` | The account's role claims, which gate API operations. |
| `offline_access` | A refresh token for long-lived sessions. |
