# Rapidata in your AI agent

Let your coding agent write the Rapidata integration for you. The official Rapidata skill teaches agents how to use the SDK — create labeling jobs, configure audiences, run benchmarks, and more — so you can just describe what you want in plain English.

## Install

Pick your agent. One command. Done.

| Agent | Install |
|-------|---------|
| **Claude Code** | `claude plugin marketplace add RapidataAI/skills && claude plugin install rapidata-sdk-plugin@rapidata-sdk-marketplace` |
| **Cursor** | `npx skills add RapidataAI/skills -a cursor` |
| **Windsurf** | `npx skills add RapidataAI/skills -a windsurf` |
| **Copilot** | `npx skills add RapidataAI/skills -a github-copilot` |
| **Cline** | `npx skills add RapidataAI/skills -a cline` |
| **Codex** | `npx skills add RapidataAI/skills -a codex` |
| **Gemini CLI** | `npx skills add RapidataAI/skills -a gemini-cli` |
| **Any other** | `npx skills add RapidataAI/skills` |

Install once. Works in every session after that. That's it.

??? note "No install — just the raw SKILL.md"

    If your framework doesn't match any of the above, drop the raw file into your agent's context:

    [**SKILL.md on GitHub**](https://github.com/RapidataAI/skills/blob/main/plugins/rapidata-sdk-plugin/skills/rapidata/SKILL.md)

    Raw URL for fetching:

    ```
    https://raw.githubusercontent.com/RapidataAI/skills/main/plugins/rapidata-sdk-plugin/skills/rapidata/SKILL.md
    ```


## Usage

### Automatic

The agent loads the skill when it sees Rapidata-related work. Just ask naturally:

```
Create a comparison job that evaluates image quality between two models
```

```
Set up a custom audience with 3 qualification examples for prompt adherence
```

### Manual

On Claude Code, invoke the skill directly:

```
/rapidata
```

```
/rapidata How do I set up early stopping with a confidence threshold?
```

Other agents follow their own conventions — Cursor rules, Copilot instructions, etc. The skill activates whenever the file is loaded into context.

## Keeping the skill up to date

The Rapidata SDK evolves constantly — new task types, new audience features, better defaults. Pull the latest version so your agent stays in sync.

**Claude Code**:

```bash
claude plugin marketplace update
```

**Everything else**:

```bash
npx skills update rapidata
```

Or update every skill you've installed at once:

```bash
npx skills update
```
