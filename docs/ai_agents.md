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

The installed skill is a short pointer: it tells the agent to install the SDK and read the full guide that ships with it. Already have the SDK? You can skip the install and read the guide directly:

```bash
rapidata skill                                # print the guide (same as python -m rapidata skill)
rapidata skill reference                      # companion guides: reference, examples, flows-for-preference-data
rapidata skill --install                      # write it to .claude/skills/rapidata/SKILL.md
rapidata skill --install --agent cursor       # or codex, generic (AGENTS.md)
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

The full guide ships inside the SDK, so upgrading the SDK upgrades the guide:

```bash
pip install -U rapidata   # or: uv add -U rapidata
```

The installed skill from the table above only points the agent at `python -m rapidata skill`, so it rarely needs an update. Pull one anyway with `claude plugin marketplace update` (Claude Code) or `npx skills update rapidata` (everything else).

Copies written by `rapidata skill --install` record the SDK version that wrote them in their front matter (`metadata.rapidata-sdk-version`) and open with a short check. That check tells the agent to compare the recorded version with `rapidata.__version__` and reinstall on a mismatch. After an SDK upgrade, the next import by a coding agent also prints the reinstall command. Both checks are local and need no network.

## Editing the skill

The guide lives in the SDK repository at [`src/rapidata/_skill/`](https://github.com/RapidataAI/rapidata-python-sdk/tree/main/src/rapidata/_skill) and is edited only there. A pull request that changes SDK behaviour updates it in the same change; the `Agent Skill` check asks the reviewer to confirm when it does not.

## The import-time hint

When the SDK is imported by a coding agent (Claude Code, Codex, Cursor, Gemini CLI) that has not read the guide yet, it prints a short pointer to `python -m rapidata skill` on stderr. It shows once per agent session and stops as soon as that session reads the guide. Humans running the SDK directly never see it.

Processes an agent merely started — a dev server, a script whose stderr is parsed — inherit its environment and would show the hint too. Set `RAPIDATA_AGENT_HINT=0` for those.
