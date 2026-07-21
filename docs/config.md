# Configuration and Logging

The Rapidata SDK provides a centralized configuration system through the **global** `rapidata_config` object that controls all aspects of the SDK's behavior including logging, output management, upload settings, and data sharing.

## Rapidata Configuration System

All configuration is managed through the **global** `rapidata_config` object, which provides a unified way to configure:

1. **Logging Configuration**: Log levels, file output, formatting, silent mode and OpenTelemetry integration
2. **Upload Configuration**: Worker threads and retry settings

### Basic Usage

```python
from rapidata import rapidata_config, logger

logger.info("This will not be shown") # (1)!
rapidata_config.logging.level = "INFO"
logger.info("This will be shown") # (2)!
```

1. Default level is `WARNING`, so `INFO` messages are suppressed.
2. After changing the level, `INFO` messages are now visible.
!!! note
    The logging system is now fully managed through `rapidata_config.logging`. Changes to the configuration are automatically applied to the logger in real-time.

### Logging Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `str` | `"WARNING"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | `Optional[str]` | `None` | Optional file path for log output |
| `format` | `str` | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | Log message format |
| `silent_mode` | `bool` | `False` | Suppress prints and progress bars (doesn't affect logging) |
| `enable_otlp` | `bool` | `True` | Enable OpenTelemetry trace logs to Rapidata |

!!! note
    Rapidata SDK tracking is limited exclusively to SDK-generated logs and traces. No other data is collected.

### Upload Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `maxWorkers` | `int` | `25` | Maximum concurrent upload threads |
| `maxRetries` | `int` | `3` | Retry attempts for failed uploads |
| `cacheToDisk` | `bool` | `True` | Enable disk-based caching for file uploads |
| `cacheTimeout` | `float` | `1` | Cache operation timeout in seconds |
| `cacheLocation` | `Path` | `~/.cache/rapidata/upload_cache` | Directory for cache storage (immutable) |
| `cacheShards` | `int` | `32` | Number of disk-cache shards for concurrent access (immutable). Each shard holds open file handles — see [Too many open files](#too-many-open-files) |
| `batchSize` | `int` | `1000` | Number of URLs per batch (100–5000) |
| `batchPollInterval` | `float` | `0.5` | Batch polling interval in seconds |
| `compression` | `CompressionConfig \| None` | `None` | Per-upload image-compression settings; see [Compression override](#compression-override) below. |

#### Compression override

```python
from rapidata import rapidata_config, CompressionConfig

# Force the asset service to compress images at quality 70 with a max dimension of 1024px,
# regardless of the server-side default (which is currently off in production).
rapidata_config.upload.compression = CompressionConfig(
    enabled=True,
    quality=70,
    max_dimension=1024,
)
```

Any field left as `None` falls back to the server-side default. Currently applies to single-asset uploads (`/asset/file` and `/asset/url`); batched URL uploads will pick the override up in a follow-up after the OpenAPI client regenerates.

#### Too many open files

Uploading local files opens file descriptors — for the on-disk upload cache (one set of handles per `cacheShards`), the worker pool (`maxWorkers`), and the HTTP connections. On systems with a low `ulimit -n` (1024 is common), a large or highly concurrent upload can exhaust the limit and fail with `OSError: [Errno 24] Too many open files`.

Two ways to resolve it:

- **Raise the OS limit** (per shell): `ulimit -n 8192`.
- **Lower the SDK's footprint** — reduce the cache shards and/or the worker pool:

    ```bash
    export RAPIDATA_cacheShards=16   # fewer cache shards = fewer open handles
    export RAPIDATA_maxWorkers=10    # fewer concurrent uploads
    ```

    `cacheShards` is immutable at runtime, so set it via the environment variable (or a `.env` file); `maxWorkers` can also be set in code (`rapidata_config.upload.maxWorkers = 10`).

The default `cacheShards` of 32 keeps a single upload well under a 1024 limit; lower it further only if you run many upload processes concurrently against the same limit.

## Environment Variables

Every configuration field can also be set through an environment variable prefixed with `RAPIDATA_` followed by the field name (e.g. `RAPIDATA_maxWorkers`). This is useful for CI/CD pipelines, containers, or any context where you want to configure the SDK without changing code.

Environment variables are applied at initialization and act as defaults — values passed explicitly in code always take precedence.

**Precedence** (highest to lowest):

1. Values set in code (e.g. `rapidata_config.upload.maxWorkers = 10`)
2. Environment variables (`RAPIDATA_*`)
3. Built-in defaults

### Client authentication

The `RapidataClient` constructor also picks up credentials and the target environment from the following variables when the matching constructor arguments are omitted:

| Variable | Maps to | Description |
|---|---|---|
| `RAPIDATA_CLIENT_ID` | `client_id` | OAuth client ID |
| `RAPIDATA_CLIENT_SECRET` | `client_secret` | OAuth client secret |
| `RAPIDATA_ENVIRONMENT` | `environment` | API endpoint (defaults to `rapidata.ai`) |

Resolution order for these values:

1. Arguments passed to `RapidataClient(...)`.
2. The environment variables above.
3. Credentials stored under `~/.config/rapidata/credentials.json`.
4. Interactive browser login.

Empty strings are treated as unset, so `RAPIDATA_CLIENT_ID=""` falls through to the next layer instead of attempting to authenticate with an empty value.

### Example `.env` file

```bash
# --- Upload ---
RAPIDATA_maxWorkers=25
RAPIDATA_maxRetries=3
RAPIDATA_cacheToDisk=true
RAPIDATA_cacheTimeout=1
RAPIDATA_cacheLocation=~/.cache/rapidata/upload_cache
RAPIDATA_cacheShards=32
RAPIDATA_batchSize=1000
RAPIDATA_batchPollInterval=0.5

# --- Logging ---
RAPIDATA_level=WARNING
RAPIDATA_log_file=
RAPIDATA_format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
RAPIDATA_silent_mode=false
RAPIDATA_enable_otlp=true
```

### Boolean values

Boolean environment variables accept `1`, `true`, or `yes` (case-insensitive) as truthy. Everything else is treated as `false`.

### Loading a `.env` file

The SDK does not load `.env` files automatically. Use a library like [`python-dotenv`](https://pypi.org/project/python-dotenv/) to load them before importing the SDK:

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env into os.environ

from rapidata import RapidataClient
```
