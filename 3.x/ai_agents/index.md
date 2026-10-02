# Rapidata in your AI agent

Let your coding agent write the Rapidata integration for you. The official Rapidata skill teaches agents how to use the SDK — create labeling jobs, configure audiences, run benchmarks, and more — so you can just describe what you want in plain English.

## Install

The skill ships inside the SDK, so installing the SDK is all it takes:

```bash
pip install -U rapidata   # or: uv add rapidata
```

When a coding agent imports `rapidata`, the SDK points it at the guide. To read it yourself, or to keep a copy in the project so your agent loads it in every session:

```bash
python -m rapidata skill                             # print the guide
python -m rapidata skill reference                   # companion guides: reference, examples, flows-for-preference-data
python -m rapidata skill --install                   # write it to .claude/skills/rapidata/SKILL.md
python -m rapidata skill --install --agent cursor    # or codex, generic (AGENTS.md)
```

The guide is versioned with the SDK, so it always describes the version you have installed.

## Logging in

The first `RapidataClient()` on a machine opens a browser login and waits for you. An agent can check and trigger it on its own:

```bash
python -m rapidata status   # is this machine authenticated? (no login started)
python -m rapidata login    # opens the browser and prints the login URL
```

If the browser doesn't open, the agent shows you the printed URL. You log in once; later runs reuse the saved credentials.

## Usage

### Automatic

With the skill installed into the project, the agent loads it when it sees Rapidata-related work. Just ask naturally:

```
Create a comparison job that evaluates image quality between two models
```

```
Set up a custom audience with 3 qualification examples for prompt adherence
```

### Manual

On Claude Code, invoke an installed skill directly:

```
/rapidata
```

```
/rapidata How do I set up early stopping with a confidence threshold?
```

Other agents follow their own conventions — Cursor rules, Copilot instructions, etc. The skill activates whenever the file is loaded into context.

## Keeping the skill up to date

The full guide ships inside the SDK, so upgrading the SDK upgrades the guide:

```bash
pip install -U rapidata   # or: uv lock --upgrade-package rapidata
```

Copies written by `python -m rapidata skill --install` record the SDK version that wrote them in their front matter (`metadata.rapidata-sdk-version`) and open with a short check. That check tells the agent to compare the recorded version with `rapidata.__version__` and reinstall on a mismatch. After an SDK upgrade, the next import by a coding agent also prints the reinstall command. Both checks are local and need no network.

## Editing the skill

The guide lives in the SDK repository at [`src/rapidata/_skill/`](https://github.com/RapidataAI/rapidata-python-sdk/tree/main/src/rapidata/_skill) and is edited only there. A pull request that changes SDK behaviour updates it in the same change; the `Agent Skill` check asks the reviewer to confirm when it does not.

## The import-time hint

When the SDK is imported by a coding agent (Claude Code, Codex, Cursor, Gemini CLI) that has not read the guide yet, it prints a short pointer to `python -m rapidata skill` on stderr. It shows once per agent session and stops as soon as that session reads the guide. Humans running the SDK directly never see it.

Processes an agent merely started — a dev server, a script whose stderr is parsed — inherit its environment and would show the hint too. Set `RAPIDATA_AGENT_HINT=0` for those.
