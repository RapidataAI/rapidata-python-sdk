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
