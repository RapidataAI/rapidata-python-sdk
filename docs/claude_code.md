# Using Rapidata with Claude Code

The Rapidata SDK has an official [Claude Code](https://claude.ai/claude-code) plugin that teaches Claude how to use the SDK. Once installed, Claude can help you write Rapidata integration code, create labeling jobs, set up audiences, and more — either automatically when it detects you're working with Rapidata, or on demand via the `/rapidata` command.

## Installation

### 1. Add the marketplace

In Claude Code, run:

```
/plugin marketplace add rapidataAI/skills
```

### 2. Install the plugin

```
/plugin install rapidata-sdk-plugin@rapidata-sdk-marketplace
```

That's it. The `/rapidata` skill is now available.

## Usage

### Automatic

Claude will automatically use its knowledge of the Rapidata SDK when it detects you're working with Rapidata code. Just ask naturally:

```
Create a comparison job that evaluates image quality between two models
```

```
Set up a custom audience with 3 qualification examples for prompt adherence
```

### Manual

Invoke the skill directly for SDK guidance:

```
/rapidata
```

Or with a specific question:

```
/rapidata How do I set up early stopping with a confidence threshold?
```

## What the plugin provides

The plugin gives Claude detailed knowledge of:

- **Classification, comparison, and ranking jobs** — creating job definitions, configuring parameters, and interpreting results
- **Audiences** — finding curated audiences, creating custom audiences with qualification examples, applying demographic filters
- **Flows** — continuous ranking without full job setup
- **MRI / Benchmarks** — comparing and ranking AI models on leaderboards
- **Settings** — `NoShuffle`, `AllowNeitherBoth`, `Markdown`, and other display options
- **Error handling** — working with `FailedUploadException` for partial upload failures
- **Legacy order API** — backwards-compatible order creation

## Keeping the plugin up to date

To pull the latest version of the plugin:

```
/plugin marketplace update
```

## Adding the plugin to your project

To make the plugin available to all contributors of a project automatically, add this to your project's `.claude/settings.json`:

```json
{
    "extraKnownMarketplaces": {
        "rapidata-sdk-marketplace": {
            "source": {
                "source": "github",
                "repo": "rapidataAI/skills"
            }
        }
    },
    "enabledPlugins": {
        "rapidata-sdk-plugin@rapidata-sdk-marketplace": true
    }
}
```

Contributors will be prompted to install the marketplace and plugin when they open the project.
