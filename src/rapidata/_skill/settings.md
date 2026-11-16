# Task settings, SDK configuration, context shortening and shared tokens

> Part of the Rapidata agent skill: `python -m rapidata skill settings`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

## Task settings

Settings control how a task is rendered and behaves for labelers. Pass them as `settings=[...]` on a job definition, audience example, flow or leaderboard.

```python
from rapidata import (
    NoShuffleSetting, AllowNeitherBothSetting, MarkdownSetting,
    MuteVideoSetting, FreeTextMinimumCharactersSetting, FreeTextMaxCharactersSetting,
    SwapContextInstructionSetting, PlayPercentageVideoSetting,
    OriginalLanguageOnlySetting, NoMistakeOptionSetting, DisableAutoloopSetting,
    NoInstructionDisplaySetting, KeyboardNumericSetting,
    LocateMaxPointsSetting, LocateMinPointsSetting,
    ComparePanoramaSetting, CompareEquirectangularSetting,
    ClassifyEquirectangularSetting, TranslateTextAssetsSetting,
    PinContextMediaSetting, ReferenceOverlaySetting, CustomSetting,
)

```

All settings inherit from `RapidataSetting` and are importable from `rapidata`.

Most settings only apply to specific task types. If you add a setting that the job's task type does not support, the SDK logs a non-fatal warning and still sends the flag — it is never dropped and no error is raised. Ranking jobs are treated as Compare for this check.

Settings with a `()` constructor are on/off: adding one turns the behavior on, leaving it out keeps it off. They take no argument — `MuteVideoSetting(False)` or `MuteVideoSetting(value=True)` raises `TypeError`.

| Class | Constructor | Effect |
|-------|-------------|--------|
| `NoShuffleSetting` | `()` | Disable shuffling of answer options (Likert scales) |
| `AllowNeitherBothSetting` | `(delay_ms: int = 5000)` — ≥ 0 | Comparison: show an "Unsure" button (answers "Neither" / "Both") after `delay_ms` milliseconds |
| `MarkdownSetting` | `()` | Render markdown in text |
| `MuteVideoSetting` | `()` | Start videos muted |
| `FreeTextMinimumCharactersSetting` | `(value: int)` — must be ≥ 1 (prints a warning above 40) | Min chars for free-text tasks. Use with caution — see note below the table |
| `FreeTextMaxCharactersSetting` | `(value: int = 1024)` — must be ≥ 1 | Max chars for free-text tasks. Use with caution — see note below the table |
| `SwapContextInstructionSetting` | `()` | Swap positions of context and instruction |
| `PlayPercentageVideoSetting` | `(percentage: int = 95)` — 0–95 | Require labelers to watch N% of video |
| `OriginalLanguageOnlySetting` | `()` | Skip translation; show task in original language. By default the instruction, context and answer options are translated into the labeler's device language. Also overrides `TranslateTextAssetsSetting`. Needs a `LanguageFilter` on the audience or filtered audience, else `assign_job` raises |
| `NoMistakeOptionSetting` | `()` | Add a "No mistakes" button so labelers can confirm the media has no errors |
| `DisableAutoloopSetting` | `()` | Disable automatic media looping |
| `NoInstructionDisplaySetting` | `()` | Hide instruction from task screen (hides the context instead if combined with `SwapContextInstructionSetting`) |
| `KeyboardNumericSetting` | `()` | Open numeric keyboard on mobile |
| `LocateMaxPointsSetting` | `(value: int = 3)` — ≥ 1 | Locate tasks: max points per labeler |
| `LocateMinPointsSetting` | `(value: int = 1)` — ≥ 1 | Locate tasks: min points per labeler |
| `ComparePanoramaSetting` | `()` | Render comparison media as 360° panorama |
| `CompareEquirectangularSetting` | `()` | Render comparison media as equirectangular VR |
| `ClassifyEquirectangularSetting` | `()` | Render classification media as equirectangular 360° view |
| `TranslateTextAssetsSetting` | `()` | Translate text assets (datapoints and text contexts) into the labeler's language. Off unless added; source text is always assumed to be English; results still reference the original text. A job with text assets needs this or a `LanguageFilter`, else `assign_job` raises |
| `PinContextMediaSetting` | `()` | Show the context image or video next to the task for the whole rapid instead of inside the collapsible context drawer. Only use it when the task screen has enough space for the context next to the task — inspect `job_def.preview()` carefully before assigning. A multi-asset context is reduced to its first asset. All task types |
| `ReferenceOverlaySetting` | `()` | Compare tasks: show the media context, labelled "Original", over both options, then reveal the options ("Edit A" / "Edit B"); labelers can toggle back to the original. Use it when both datapoints are edits of the context image. Needs two image options and exactly one image in `media_contexts` — with no media context, or several assets in it, the setting has no effect; options that are not images are not rendered |
| `CustomSetting` | `(key: str, value: str, target: "rapids" \| "campaign" = "rapids")` | Pass a custom key/value through to the backend; `target` controls whether the flag is applied at the rapid level (`"rapids"`) or campaign level (`"campaign"`) |

**Note on `FreeTextMinimumCharactersSetting` / `FreeTextMaxCharactersSetting`:** use these with caution. Free-text responses already pass through a reasonableness check by default, so tightening the bounds is usually unnecessary and will reject otherwise valid answers. Only set them when the question genuinely demands a specific length (e.g. a single word, or a full paragraph).

## SDK configuration (`rapidata_config`)

```python
from rapidata import rapidata_config, logger, CompressionConfig

# Logging
rapidata_config.logging.level = "INFO"       # DEBUG, INFO, WARNING, ERROR, CRITICAL
rapidata_config.logging.log_file = "/path/to/log.txt"
rapidata_config.logging.silent_mode = False  # also suppresses the dashboard preview link printed on job creation
rapidata_config.logging.enable_otlp = True   # OpenTelemetry tracing (auto-disabled for environments without an OTLP collector — only rapidata.ai and rabbitdata.ch have one). Defaults to True, except under pytest (where it defaults to False); can also be disabled via RAPIDATA_DISABLE_OTLP=1, or forced on by passing it explicitly
rapidata_config.logging.environment = "rapidata.ai"  # API environment; derives the OTLP collector host (otlp-sdk.<environment>). Set automatically by RapidataClient from its environment

# Upload tuning
rapidata_config.upload.maxWorkers = 25        # Concurrent upload threads (warns above 200)
rapidata_config.upload.maxRetries = 3
rapidata_config.upload.cacheToDisk = True
rapidata_config.upload.cacheTimeout = 1.0
rapidata_config.upload.batchSize = 1000       # URLs per batch (100–5000; below 100 raises ValueError)
rapidata_config.upload.batchPollInterval = 0.5
rapidata_config.upload.compression = CompressionConfig(
    enabled=True,
    quality=70,        # WebP quality 1–100
    max_dimension=1024, # Max width or height in pixels (images only)
)  # Optional: per-upload compression override for images and videos (None = server default)
rapidata_config.upload.contextShortening = False   # When True, shorten EVERY context (over-long ones are always shortened)
rapidata_config.upload.failureTolerance = 0.0      # Fraction of a job's datapoints allowed to fail (0.0–1.0, 0.0 = strict)
rapidata_config.upload.checkForExplicitContent = None  # None = account default, True = force on, False = request skip

# Client-level maintenance
client.clear_all_caches()
client.reset_credentials()
```

`CompressionConfig` fields (all default `None` = defer to server):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool \| None` | Force compression on or off for **both images and videos**. `False` preserves the original image *and* video (resolution and bitrate) |
| `quality` | `int \| None` | WebP quality (1–100) when image compression runs. **Images only** |
| `max_dimension` | `int \| None` | Max width or height in pixels (≥ 1) when image compression runs. **Images only** (videos have no equivalent knob) |

Governs compression of images **and** videos. Applies to single-asset uploads (`/asset/file` and `/asset/url`) and batched URL uploads (`/asset/batch-upload`).

`failureTolerance` is validated to `0.0..1.0` (`ValueError` otherwise) and is overridden per call by `failure_tolerance` on `create_*_job_definition`.

`checkForExplicitContent = False` only *requests* a skip of the server-side explicit-content check applied on job assignment — it is honored only if your account is permitted; otherwise the check still runs and `assign_job` logs a warning.

`cacheLocation` (`~/.cache/rapidata/upload_cache`) and `cacheShards` (default 32) are immutable at runtime — don't try to assign them; set `cacheShards` via `RAPIDATA_cacheShards`. Each shard holds open file handles, and 32 comfortably covers the default `maxWorkers` of 25.

**`OSError: [Errno 24] Too many open files`:** raise `ulimit -n`, lower `RAPIDATA_cacheShards` / `RAPIDATA_maxWorkers`, or set `cacheToDisk = False` (in-memory cache, no cache file descriptors, but you lose cross-run upload dedup).

All config fields support environment-variable overrides with the `RAPIDATA_` prefix (e.g., `RAPIDATA_maxWorkers=10`, `RAPIDATA_failureTolerance=0.0`, `RAPIDATA_DISABLE_OTLP=1`).

## Context management

Write contexts as one sentence under 150 characters (**Task design rules**, rule 3, in the main guide); shortening is a fallback, not a substitute, and rarely gets a context under 150 characters. Datapoint contexts have a backend maximum of **400 characters** (`MAX_CONTEXT_LENGTH`) and the backend rejects longer ones, so any context over 400 characters is **always** shortened against the task instruction before upload. This cannot be turned off. A warning reports how many contexts were shortened, per-context before/after lengths are logged at info level, and if shortening returns an empty result the original context is kept and a warning is logged.

A context tuned to the question focuses the labeler even when it already fits the limit. Set `rapidata_config.upload.contextShortening = True` (default `False`) to have **every** context shortened, not just the over-long ones:

```python
from rapidata import rapidata_config

rapidata_config.upload.contextShortening = True
```

Shorten contexts directly, without creating a job, via `client.context` (a `ContextManager`, also importable directly: `from rapidata import ContextManager`):

- `client.context.shorten_context(context, question) → str`: shorten a single context for the given question. Results are cached server-side.
- `client.context.shorten_contexts(pairs) → list[str]`: shorten a batch of `(context, question)` pairs, returned in the same order. Batches of ≤10 pairs go out as a single request; larger batches are split into chunks of 10 and sent concurrently using `rapidata_config.upload.maxWorkers`, with a `Shortening contexts` progress bar (suppressed by `rapidata_config.logging.silent_mode`).

```python
short = client.context.shorten_context(
    context="<a very long description ...>",
    question="Does the main character wear the right clothing?",
)
shortened = client.context.shorten_contexts([
    (context_a, question_a),
    (context_b, question_b),
])
```

## Shared token files (distributed training)

When Rapidata is queried from a large distributed job (e.g. hundreds or thousands of GPU workers hitting a ranking flow), don't let every worker authenticate on its own: each `RapidataClient()` exchanges the client credentials for an access token that expires ~1 hour later, so all workers re-auth in the same instant and the burst gets rate-limited. Authenticate **once** and share the token via a file that all workers can read.

### `RapidataClient` authentication parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `leeway` | int | Seconds before token expiry at which the SDK refreshes/re-reads the token (default 60). A coordinator typically uses a larger value, e.g. `leeway=300`, to renew well before workers need a fresh token |
| `token_file` | str | Path to a shared token file to read the access token from; the SDK re-reads it whenever the in-memory token is within `leeway` of expiry. Also settable via the `RAPIDATA_TOKEN_FILE` env var |
| `token` | dict | An access-token dict passed directly; the SDK never re-reads it, so inject a fresh one with `client.set_token(...)` (or construct a new client) once the token expires |

### `client.maintain_token_file(path, interval=60) → threading.Thread`

Writes the token file at `path` immediately, then keeps rewriting it atomically from a background daemon thread every `interval` seconds, creating the directory if needed. Returns the thread; `.join()` blocks the process forever (drop it if the coordinator also does other work).

### `client.get_token() → dict`

Returns the current access token as a dict. Cheap to call at any frequency: it only contacts the auth server once the token is within `leeway` of expiry. Use it to write the shared token file yourself (write atomically, and keep the absolute `expires_at` field so workers know when to re-read).

### `client.set_token(token) → None`

The counterpart to `get_token()`: replace the token a running client authenticates with, effective from its next request, without reconstructing the client. Expects the complete token object (`access_token`, `token_type`, and an absolute `expires_at` timestamp — pass what `get_token()` returned). Together, `get_token()` and `set_token()` let you move the token over any transport (key-value store, RPC, secret manager, message queue) — a **push** system (the coordinator distributes a fresh token to every worker before the old one expires, each worker applies it with `set_token`) or a **pull** system (each worker periodically fetches the current token from your own endpoint).

```python
from rapidata import RapidataClient

# Coordinator: holds the client credentials and keeps the file fresh
coordinator = RapidataClient(leeway=300)
coordinator.maintain_token_file("/shared/rapidata_token.json").join()

# Worker: reads the shared token, never sees the client secret
client = RapidataClient(token_file="/shared/rapidata_token.json")

# Any transport: export from the coordinator, inject into a worker
token = coordinator.get_token()          # refreshes first if near expiry
worker = RapidataClient(token=token)     # bootstrap a worker from a token object
worker.set_token(coordinator.get_token())  # renew a running worker later
```

The token file contains a bearer token: write it only to storage your job alone can access. The SDK reads the token at startup and re-reads the file whenever the in-memory token is within `leeway` of expiry. Whatever the transport, pass the complete token object around and keep its absolute `expires_at` field. On older SDKs without `token_file`, pass the token dict directly with `RapidataClient(token=json.load(f))`; the SDK never re-reads it, so each worker must call `set_token()` (or construct a new client) when the token expires.

## Example

### Sharing a Token Across Workers (Distributed Training)

Authenticate once in a coordinator process and share the token with many workers via a file, so thousands of workers don't all re-authenticate at the same instant.

```python
# --- Coordinator (holds the client credentials) ---
from rapidata import RapidataClient

coordinator = RapidataClient(leeway=300)  # renew 5 min before expiry
# Writes the file now, then keeps it fresh from a background thread.
# .join() blocks forever; drop it if the coordinator also does other work.
coordinator.maintain_token_file("/shared/rapidata_token.json").join()
```

```python
# --- Worker (never sees the client secret) ---
from rapidata import RapidataClient

client = RapidataClient(token_file="/shared/rapidata_token.json")
# or set RAPIDATA_TOKEN_FILE and construct with no arguments.
# The SDK re-reads the file whenever the in-memory token nears expiry.
```

Rolling your own file writer with `get_token()`:

```python
import json, os, time
from rapidata import RapidataClient

TOKEN_FILE = "/shared/rapidata_token.json"
coordinator = RapidataClient(leeway=300)
os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

def write_token(token: dict) -> None:
    tmp = TOKEN_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(token, f)          # keep the absolute expires_at field
    os.replace(tmp, TOKEN_FILE)      # atomic: workers never read a half-written file

while True:
    write_token(coordinator.get_token())  # only re-auths when near expiry
    time.sleep(60)
```

The file is just one transport. To move the token over any transport (key-value store, RPC, secret manager, message queue), pair `get_token()` on the coordinator with `set_token()` on the worker — no shared file needed:

```python
from rapidata import RapidataClient

# --- Coordinator: export the current token (refreshes it first if near expiry) ---
coordinator = RapidataClient(leeway=300)
token = coordinator.get_token()
# ... distribute `token` through any transport you like ...

# --- Worker: bootstrap directly from a token object, then renew in place ---
worker = RapidataClient(token=token)
# Later, when a fresh token arrives, inject it without reconstructing the client:
fresh_token = coordinator.get_token()  # in practice received over your transport
worker.set_token(fresh_token)  # used from the next request on
```
