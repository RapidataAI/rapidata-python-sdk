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

## Coordinator

Start the coordinator first — it authenticates with the client credentials
as usual (see [Authentication](authentication.md)), exports its token with
`get_token()`, and keeps the shared file fresh:

```python
import json
import os
import time

from rapidata import RapidataClient

TOKEN_FILE = "/shared/rapidata_token.json"  # (1)!

coordinator = RapidataClient(leeway=300)  # (2)!

os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)


def write_token(token: dict) -> None:
    tmp_path = TOKEN_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(token, f)
    # Atomic replace: a worker reading concurrently sees either the old
    # token or the new one, never a partially written file.
    os.replace(tmp_path, TOKEN_FILE)


while True:
    write_token(coordinator.get_token())  # (3)!
    time.sleep(60)
```

1. For simplicity this example writes to a root-level `/shared` directory —
   point it at whatever storage all your workers actually mount (an NFS
   path, a shared volume, …).
2. The coordinator is the only process that holds the client credentials —
   via `RAPIDATA_CLIENT_ID` / `RAPIDATA_CLIENT_SECRET` or the cached
   credentials file. `leeway=300` treats the token as expired once it is
   within 5 minutes of its actual expiry, so the file is renewed well before
   workers need it.
3. `get_token()` returns the current token — including the absolute
   `expires_at` timestamp workers rely on — and only fetches a new one when
   it is within `leeway` of expiry. Polling it every minute therefore does
   **not** spam the auth server; most iterations just rewrite the same token.

**Write the file atomically** (temp file + `os.replace`, as above) so
workers never parse a half-written file. If you produce the token without
the SDK (e.g. a `curl` call to the token endpoint), you must also add the
absolute `expires_at` yourself — the raw response only carries the relative
`expires_in`, which is meaningless to a later reader.

## Workers

Once the coordinator has written the file, workers pass its path to the
client — or set the `RAPIDATA_TOKEN_FILE` environment variable and construct
the client with no arguments:

```python
from rapidata import RapidataClient

client = RapidataClient(token_file="/shared/rapidata_token.json")
```

The SDK reads the token from the file at startup and re-reads it whenever the
in-memory token is within 60 seconds of expiry (configurable via `leeway`).
As long as the coordinator keeps the file fresh, workers never need to be
restarted or re-authenticated.

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
