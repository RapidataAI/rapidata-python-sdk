# Configuration and Logging

The Rapidata SDK provides a centralized configuration system through the **global** `rapidata_config` object that controls all aspects of the SDK's behavior including logging, output management, upload settings, and data sharing.

## Rapidata Configuration System

All configuration is managed through the **global** `rapidata_config` object, which provides a unified way to configure:

1. **Logging Configuration**: Log levels, file output, formatting, silent mode and OpenTelemetry integration
2. **Upload Configuration**: Worker threads and retry settings

### Basic Usage

```python
from rapidata import rapidata_config, logger

logger.info("This will not be shown")
rapidata_config.logging.level = "INFO"
logger.info("This will be shown")
```
>Note: The logging system is now fully managed through `rapidata_config.logging`. Changes to the configuration are automatically applied to the logger in real-time.

### Logging Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `str` | `"WARNING"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | `Optional[str]` | `None` | Optional file path for log output |
| `format` | `str` | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | Log message format |
| `silent_mode` | `bool` | `False` | Suppress prints and progress bars (doesn't affect logging) |
| `enable_otlp` | `bool` | `True` | Enable OpenTelemetry trace logs to Rapidata |

>Note: Rapidata SDK tracking is limited exclusively to SDK-generated logs and traces. No other data is collected.

### Upload Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `maxWorkers` | `int` | `25` | Maximum concurrent upload threads |
| `maxRetries` | `int` | `3` | Retry attempts for failed uploads |
| `cacheToDisk` | `bool` | `True` | Enable disk-based caching for file uploads |
| `cacheTimeout` | `float` | `1` | Cache operation timeout in seconds |
| `cacheLocation` | `Path` | `~/.cache/rapidata/upload_cache` | Directory for cache storage (immutable) |
| `cacheShards` | `int` | `128` | Number of cache shards for parallel access (immutable) |
| `batchSize` | `int` | `1000` | Number of URLs per batch (100–5000) |
| `batchPollInterval` | `float` | `0.5` | Batch polling interval in seconds |

## Environment Variables

Every configuration field can also be set through an environment variable prefixed with `RAPIDATA_` followed by the field name (e.g. `RAPIDATA_maxWorkers`). This is useful for CI/CD pipelines, containers, or any context where you want to configure the SDK without changing code.

Environment variables are applied at initialization and act as defaults — values passed explicitly in code always take precedence.

**Precedence** (highest to lowest):

1. Values set in code (e.g. `rapidata_config.upload.maxWorkers = 10`)
2. Environment variables (`RAPIDATA_*`)
3. Built-in defaults

### Example `.env` file

```bash
# --- Upload ---
RAPIDATA_maxWorkers=25
RAPIDATA_maxRetries=3
RAPIDATA_cacheToDisk=true
RAPIDATA_cacheTimeout=1
RAPIDATA_cacheLocation=~/.cache/rapidata/upload_cache
RAPIDATA_cacheShards=128
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
