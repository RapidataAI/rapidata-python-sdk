# Logging and Output Management

The Rapidata SDK provides two complementary systems for managing output and logging:

1. **Logger Module**: For structured logging with different levels and destinations
2. **Output Manager**: For controlling print statements and progress bars throughout the SDK

## Logger Module

The logger module provides centralized logging configuration for the Rapidata SDK. It sets up a logger instance that can be used throughout the SDK to provide consistent logging behavior and formatting.

### Basic Usage

```python
from rapidata import logger

# Log different types of messages
logger.debug("Detailed debug information")
logger.info("General information about program execution")
logger.warning("Something unexpected happened")
logger.error("A serious problem occurred")
logger.critical("A very serious error occurred")
```

### Configuration

The logger can be customized using the `configure_logger` function:

```python
from rapidata import configure_logger

# Configure with custom settings
configure_logger(
    level="DEBUG",
    log_file="/path/to/logs/rapidata.log",
    format_string="%(asctime)s - %(levelname)s - %(message)s"
)
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `str` | `"WARNING"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | `str` or `None` | `None` | Optional file path for log output |
| `format_string` | `str` | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | Custom format for log messages |

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General information about program execution  
- **WARNING**: Something unexpected happened (default level)
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

### Examples

#### Development Configuration
```python
# Enable debug logging for development
configure_logger(level="DEBUG")

logger.debug("This will now be visible")
logger.info("Processing started")
```

#### Production Configuration
```python
# Configure for production with file logging
configure_logger(
    level="INFO",
    log_file="/var/log/rapidata/app.log"
)

logger.info("Application started")
logger.error("Connection failed, retrying...")
```

#### Custom Format
```python
# Simple format without timestamps
configure_logger(
    level="INFO",
    format_string="[%(levelname)s] %(message)s"
)
```

## Output Manager

The output manager provides control over print statements throughout the SDK. It includes a silent mode feature that allows suppressing all print outputs while preserving logging functionality.

### Key Features

- **Silent Mode**: Suppress all prints and progress bars
- **Independent of Logging**: Print suppression doesn't affect log messages

### Silent Mode Control

```python
from rapidata import RapidataClient, RapidataOutputManager

# Enable silent mode
RapidataOutputManager.enable_silent_mode()

rapi = RapidataClient()

# This will not display the progress bar or anything else
order = rapi.order.create_compare_order(
    name="Example Image Comparison",
    instruction="Which image matches the description better?",
    contexts=["A small blue book sitting on a large red book."],
    datapoints=[["https://assets.rapidata.ai/midjourney-5.2_37_3.jpg", 
                "https://assets.rapidata.ai/flux-1-pro_37_0.jpg"]],
)

# Disable silent mode
RapidataOutputManager.disable_silent_mode()
# This will give you the confirmation message
order.run()

# Check current state
if RapidataOutputManager.silent_mode:
    print("Currently in silent mode")
```
