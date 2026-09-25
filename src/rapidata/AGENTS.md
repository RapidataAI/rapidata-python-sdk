# Rapidata SDK — for coding agents

Do not infer how to use this SDK from the source files next to this document.
The maintained guide covers job types, audiences, validation sets, result
fields and the mistakes agents make most often.

Read it first:

```bash
python -m rapidata skill            # print the guide
python -m rapidata skill --install  # install it into the current project
```

## Logging in

`RapidataClient()` needs credentials. With none saved, it opens a browser login
and blocks for up to 5 minutes waiting for the user, so check first:

```bash
python -m rapidata status   # exit 0: authenticated; exit 1: not logged in
python -m rapidata login    # opens the browser and prints the login URL
```

When `status` reports not logged in, run `login` (in the background, or with a
tool timeout above 5 minutes) and show the user the URL it prints. They log in
once; every later `RapidataClient()` reuses the saved credentials. For headless
runs, set `RAPIDATA_CLIENT_ID` and `RAPIDATA_CLIENT_SECRET` instead.

## Online copies

- https://docs.rapidata.ai/llms-full.txt
- https://docs.rapidata.ai/ai_agents/
