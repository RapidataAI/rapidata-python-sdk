# Distributed Training

When you use Rapidata from a large distributed job — for example a ranking
flow queried from hundreds or thousands of GPU workers — don't let every
worker authenticate on its own. Each `RapidataClient()` exchanges the client
credentials for an access token at startup, and because all those tokens
expire at the same time (~1 hour later), every worker hits the auth server
again in the same instant. At scale this looks like a coordinated burst and
leads to rate limiting and failed requests.

The fix is to authenticate **once** and share the token:

- A single **coordinator** process (your launcher, or rank 0) holds the
  client credentials. It fetches the access token, refreshes it *before* it
  expires, and writes it to a file on storage all workers can read (a shared
  filesystem like NFS, or a mounted volume).
- Every **worker** points the SDK at that file. Workers never see the client
  secret, make no auth-server calls of their own, and automatically re-read
  the file when the current token expires.

## Workers

Pass the file path to the client, or set the `RAPIDATA_TOKEN_FILE`
environment variable and construct the client with no arguments:

```python
from rapidata import RapidataClient

client = RapidataClient(token_file="/shared/rapidata_token.json")
```

The SDK reads the token from the file at startup and re-reads it whenever the
in-memory token is within 60 seconds of expiry (configurable via `leeway`).
As long as the coordinator keeps the file fresh, workers never need to be
restarted or re-authenticated.

## Coordinator

The coordinator exchanges the client credentials for a token (see
[Authentication](authentication.md)) and rewrites the shared file ahead of
expiry:

```python
import json
import os
import time

import requests

TOKEN_URL = "https://auth.rapidata.ai/connect/token"
TOKEN_FILE = "/shared/rapidata_token.json"


def fetch_token() -> dict:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["RAPIDATA_CLIENT_ID"],
            "client_secret": os.environ["RAPIDATA_CLIENT_SECRET"],
            "scope": "openid roles email api",
        },
    )
    response.raise_for_status()
    token = response.json()
    # Workers decide when to re-read the file based on this absolute
    # timestamp — the relative expires_in is meaningless to a later reader.
    token["expires_at"] = int(time.time()) + token["expires_in"]
    return token


def write_token(token: dict) -> None:
    tmp_path = TOKEN_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(token, f)
    # Atomic replace: a worker reading concurrently sees either the old
    # token or the new one, never a partially written file.
    os.replace(tmp_path, TOKEN_FILE)


while True:
    token = fetch_token()
    write_token(token)
    # Refresh 5 minutes before expiry so workers never read a stale token.
    time.sleep(max(token["expires_in"] - 300, 60))
```

Two details matter:

1. **Write an absolute `expires_at`** (Unix timestamp, seconds). Without it
   the SDK cannot tell that a token read from the file is about to expire.
2. **Write atomically** (temp file + `os.replace`), so workers never parse a
   half-written file.

## Practical tips

- **Stagger worker startup.** Even with a shared token, thousands of workers
  constructing their first client and firing their first API call in the
  same second is an unnecessary burst. A few seconds of random jitter before
  the first call smooths it out.
- **Create one client per process and keep it.** The client refreshes its
  token from the file transparently; there is no need to reconstruct it.
- **Keep the coordinator alive for the whole run.** If it stops refreshing,
  workers fail with an invalid-token error once the token in the file
  expires.

## Older SDK versions

Before `token_file` was available, the same pattern worked by passing the
token dict directly — but the SDK never re-reads the file, so each worker
must construct a new client when the token expires:

```python
import json

from rapidata import RapidataClient

with open("/shared/rapidata_token.json") as f:
    client = RapidataClient(token=json.load(f))
```
