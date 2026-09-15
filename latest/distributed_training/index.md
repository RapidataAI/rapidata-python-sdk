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
as usual (see [Authentication](authentication.md)) and keeps the shared file
fresh with `maintain_token_file()`:

```python
from rapidata import RapidataClient

coordinator = RapidataClient(leeway=300)  # (1)!
coordinator.maintain_token_file("/shared/rapidata_token.json").join()  # (2)!
```

1. The coordinator is the only process that holds the client credentials —
   via `RAPIDATA_CLIENT_ID` / `RAPIDATA_CLIENT_SECRET` or the cached
   credentials file. `leeway=300` renews the token once it is within
   5 minutes of expiry, well before workers need a new one.
2. Writes the file immediately, then keeps rewriting it atomically from a
   background thread (every 60 seconds by default), creating the directory
   if needed. `.join()` blocks the process forever — drop it if your
   coordinator also does other work, e.g. when rank 0 both trains and
   refreshes the token. The root-level `/shared` is just for the example —
   use whatever storage all your workers actually mount (an NFS path, a
   shared volume, …).

!!! warning "Keep the token file secure"
    The file contains a bearer token — anyone who can read it can act on
    your Rapidata account until the token expires. Write it only to storage
    that your training job alone can access, and restrict the file
    permissions accordingly.

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

## Building your own token distribution

The shared file is just one transport. The SDK exposes the underlying
primitives directly, so you can move the token around however fits your
infrastructure — a key-value store, an RPC from the launcher, a secret
manager, a message queue:

```python
from rapidata import RapidataClient

# 1. Export — the credential-holding client hands out its current token,
#    refreshing it first if it is about to expire.
token = coordinator.get_token()

# ... distribute it through any transport you like ...

# 2. Bootstrap — create a worker client directly from a token object.
worker = RapidataClient(token=token)

# 3. Renew — inject a newer token into a running client at any time;
#    it is used from the next request on.
worker.set_token(fresh_token)
```

With these three calls you can build a **push** system (the coordinator
distributes a fresh token to every worker before the old one expires, each
worker applies it with `set_token`) or a **pull** system (each worker
periodically fetches the current token from your own endpoint). `get_token()`
is cheap to call at any frequency: it returns the current token and only
contacts the auth server once the token is within `leeway` of expiry.

Whatever the transport, pass the **complete token object** around and keep
its absolute `expires_at` field — it's how a client decides when a token has
expired. `expires_at` is **Unix epoch seconds** (`time.time()`-style), which
is timezone-independent: the coordinator and the workers can run in
different timezones or regions without any conversion. If you produce tokens
without the SDK (e.g. a `curl` call to the token endpoint), the response
only carries the relative `expires_in`, so add
`expires_at = time.time() + expires_in` yourself — as epoch seconds, never a
formatted datetime string or local wall-clock arithmetic, otherwise clients
cannot check expiry and keep using the token after it has expired. And if
your transport is a shared file, write it atomically (temp file +
`os.replace`) so readers never see a partial token.
