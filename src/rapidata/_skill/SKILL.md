---
name: rapidata
description: Explains how to use the Rapidata API to get real and fast human annotations for your data. Use when writing code that creates labeling tasks, compares models (one-call templates compare two image or video models on prompt alignment, preference and coherence), collects human feedback, or integrates with the Rapidata Python SDK.
---

# Rapidata Python SDK

Rapidata connects you with human labelers worldwide. Run `pip install -U rapidata` (or `uv add rapidata --upgrade`) first: outdated versions can fail against the API. Upgrade when `RapidataClient()` says a new version exists, then re-read this guide.

## Task design rules

Follow these for every job definition, audience example and leaderboard. The SDK only rejects instructions over 250 characters and contexts over 400; design to the limits below, not to the SDK's.

1. **Keep `responses_per_datapoint` at 10 or more.** Never lower it to cut cost; label fewer datapoints instead. Comparisons: keep the default `AdaptiveStopping()`.
2. **Ask one short question about one criterion, in under 80 characters.** One job definition per aspect. Definitions and edge cases never go into the instruction.
3. **Keep each context to one sentence under 150 characters**, holding only what the question checks. Never pass the full generation prompt.
4. **Use plain words that translate cleanly** in the instruction, context and answer options.
5. **Design each task to be answered in about 10 seconds, 15 at most, including playback.** Audio clips add up, videos don't. Longer tasks: contact Rapidata (info@rapidata.ai) first.
6. **Set `min_responses_per_matchup` to 5 or more on every leaderboard.** The SDK default of 3 is too low.

**Next, print your task's guide:** `python -m rapidata skill <guide>`, e.g. `comparison` (two models, A vs B), `classification`, `ranking`, `annotation`, `benchmarks`, `audiences`, `flows`. Full index and rule details below.

## Which guide to read

Each guide describes the installed SDK version, like this one.

| Task | Guide |
|---|---|
| Compare two image or video models (prompt alignment, preference, AI artifacts) with a one-call template, or any A-vs-B comparison job | `comparison` |
| Put items into categories, yes/no questions, rating scales (Likert), quorum stopping | `classification` |
| Rank 3 or more items within a group | `ranking` |
| Tap points (locate), color in regions (draw), select words in a sentence, free-text answers | `annotation` |
| Rank AI models on a leaderboard (benchmark / MRI): create, leaderboards, evaluate models | `benchmarks` |
| Benchmark participants: uploads and recovery, pricing, prompt tags and assets | `benchmark-participants` |
| Benchmark standings, win/loss matrices, voter demographics | `benchmark-results` |
| Custom or qualified audiences, qualification examples, recruiting, queueing jobs | `audiences` |
| Country / language recruitment filters, filtered audiences by age, gender, device | `filters` |
| Continuous small-batch collection (ranking and classify flows), validation sets | `flows` |
| DPO / RLHF preference data, best-of-N with flows | `flows-for-preference-data` |
| Run a labeling job on a schedule | `signals` |
| Cost estimates, billing period, remaining credit | `billing` |
| Task settings (shuffling, video, translation, markdown, …), SDK configuration, context shortening, shared token files | `settings` |
| Shared parameters, editing job definitions, stopping rules, result fields, progress | `reference` |
| Failed uploads, `FailedUploadException`, jobs stuck in review or out of funds | `errors` |

## Task design rules in detail

Labelers answer validation tasks in the same session, mostly on phones, and within the 10–15 seconds they read the instruction and the context and play the media. A task they can't take in at a glance gets guessed. A task that passes the SDK's checks can still be far too long.

1. **Responses.** 10 is the default for every job type except comparison. With 3 responses, a single labeler who misread the task can flip the result. `AdaptiveStopping()` (the comparison default) already stops each pair as soon as its verdict is settled; leave it on. For classification with one correct answer, `QuorumStopping(threshold, max_responses)` stops early.
2. **Instruction.** The instruction is the question and nothing else. To judge several aspects (motion, on-screen text, sound, …), create one job definition per aspect. Cover definitions and edge cases ("what counts", "what does not count", which side is which) with an answer option such as `"Can't tell"`, by marking the target in the media itself, or with qualification examples on a custom audience (`python -m rapidata skill audiences`). Over 250 characters raises `ValueError: instruction is <n> characters; maximum is 250`; between 80 and 250 is accepted without a warning but is still too long. Ask about one thing ("What animal is in the image?", not "Does this contain a rabbit, dog, or cat?"), frame it positively ("Which is more realistic?", not "Which is less AI-generated?") and keep answer options distinct ("Poor / Acceptable / Excellent", not "Bad / Not Good / Fine / Good / Great").
   - ✅ `"Which video matches the description better?"`
   - ✅ `"Is there a real dog in the red circle?"` with options `["Yes", "No", "Can't tell"]`
   - ❌ `"Which video is better overall? Consider the motion, timing, camera, style, on-screen text and sound."` (several criteria)
   - ❌ `"Is there a real dog in the red circle? It is small and often blurred. A dog on a poster or a toy dog does not count."` (one criterion, but definitions and edge cases make it 116 characters)
   - ❌ `"Which option best describes the image? Select one answer."` (classification and comparison already accept exactly one answer, so "Select one answer" only adds words to translate and read)
3. **Context.** Nobody reads 300 characters and judges two videos in 15 seconds. The backend rejects contexts over 400 characters, so longer ones are always shortened against the instruction before upload (a warning says how many). Shortening (`python -m rapidata skill settings`, **Context management**) focuses a context on the question but rarely gets it under 150 characters, so write the short version yourself.
4. **Translation.** The instruction, context and answer options are machine-translated into each labeler's device language by default (Key Gotcha 9), so most labelers read a translation, not your English. Use common words and literal phrasing; avoid idioms, slang, wordplay, abbreviations and words with several meanings, which come out wrong or meaningless in translation.
   - ✅ `"Does the video match the description?"` with options `["Yes", "No"]`
   - ❌ `"Does the clip nail the vibe of the prompt?"` with options `["Spot on", "Way off"]` (idiom and slang; "nail" and "spot on" translate literally)
5. **Playback.** Videos play at the same time and muted, so a comparison of two 10-second videos takes 10 seconds. Audio clips play one after the other, so both sides of an audio comparison add up: keep the audio to about 10 seconds in total per task, for example two clips of at most 5 seconds, and trim longer clips to the part the question checks before uploading. A single video that shows A and then B counts in full. After creating a job definition, the SDK checks up to 100 datapoints and logs a warning when one needs more than 15 seconds of playback (audio summed, videos by the longest): trim the clips and create the definition again before assigning it.
   - ✅ Video comparison: two 10-second videos
   - ✅ Audio comparison: two 4-second clips
   - ❌ Audio comparison: two 10-second clips (20 seconds of listening before the labeler can answer)
   - ❌ One 18-second video showing A and then B, with `PlayPercentageVideoSetting(95)` (labelers must sit through 17 seconds)
6. **Responses per matchup.** With 3 responses, one labeler who misreads the question decides a third of a matchup. Pass `min_responses_per_matchup=5` (or more) to `create_leaderboard` or `leaderboard.update`, and pick a `level_of_detail` budget that covers it (`python -m rapidata skill benchmarks`).

## Installation & Authentication

```python
from rapidata import RapidataClient
client = RapidataClient()  # env vars → ~/.config/rapidata/credentials.json → browser login
client = RapidataClient(client_id="...", client_secret="...")  # saved to ~/.config/rapidata/credentials.json
client = RapidataClient(organization_id="org_...")  # pin saved credentials to one organization
# Env vars: RAPIDATA_CLIENT_ID + RAPIDATA_CLIENT_SECRET (no browser), RAPIDATA_ENVIRONMENT (default rapidata.ai),
# RAPIDATA_TOKEN_FILE (shared access token, same as token_file=). Empty values count as unset.
```

With `organization_id`, the browser login opens on that organization, credentials are saved per environment and organization, and switching organization in the dashboard does not move them; without it, any saved credential for the environment is reused. Without saved credentials, `RapidataClient()` blocks on a browser login for up to 5 minutes. As a coding agent, check auth first from the CLI:

```bash
python -m rapidata status [--environment ENV] [--organization ORG]  # exit 0: "Authenticated for {env} via {source}."; exit 1: not logged in. Never starts a login
python -m rapidata login  [--environment ENV] [--organization ORG]  # browser login; saves credentials (exit 0), or "Login did not complete..." on stderr (exit 1). No-op if already authenticated; blocks up to 5 minutes
```

- Both check `RAPIDATA_TOKEN_FILE` → `RAPIDATA_CLIENT_ID` + `RAPIDATA_CLIENT_SECRET` → credentials saved for `https://auth.{environment}` (and `--organization`, when given). `--environment` defaults to `RAPIDATA_ENVIRONMENT`, else `rapidata.ai`.
- Run `python -m rapidata status` before the first `RapidataClient()`. If it reports not logged in, run `python -m rapidata login` in the background (or with a tool timeout above 5 minutes) and show the user the URL it prints — the login URL is always printed to stderr, even in silent mode. After the user logs in once, every later `RapidataClient()` reuses the saved credentials.
- For headless runs, set `RAPIDATA_CLIENT_ID` and `RAPIDATA_CLIENT_SECRET` instead.
- Many workers (e.g. distributed training hitting a flow) must not each authenticate: share one token through a file (`python -m rapidata skill settings`, **Shared token files**).

## Core Concepts

- **Job Definition**: a reusable configuration for a labeling task (task type, instruction, datapoints, answer options). Types: classification, comparison, ranking, locate, draw, select words, free text.
- **Audience**: annotators selected for **one specific task**. **global** is the generic pool with no setup (`client.audience.get_audience_by_id("global")`), **curated** pools are pre-trained on a domain (alignment: `aud_MU1GZYoESyO`), **custom** audiences are trained on your own qualification examples (Key Gotcha 3; `python -m rapidata skill audiences`).
- **Job**: a running instance of a job definition assigned to an audience.
- **Flow**: continuously collect responses in small batches without full job setup: **ranking flows** (Elo-style comparison) and **classify flows** (sort each datapoint into one of a fixed set of categories).
- **MRI/Benchmark**: compare and rank AI models on leaderboards.

**Client entry points:** `client.job.template` (**start here to compare two image or video models**: Rapidata's field-tested alignment, preference and coherence setups, 11 votes per pair on the right audience, in one call; suggest it before building a comparison job definition) · `client.job` (job definitions) · `client.audience` · `client.flow` · `client.mri` (benchmarks; rank three or more models) · `client.signals` (scheduled jobs) · `client.context` (shorten contexts against a question) · `client.billing` (organization-level cost, credit and outstanding balance) · `client.asset` (`client.asset.upload(path_or_url)` → `UploadedAsset`, reusable in any job definition) · `client.validation` (validation sets, only for a flow's `validation_set_id`; jobs qualify labelers through audience examples instead).

## Step-by-step workflow

```python
from rapidata import RapidataClient

client = RapidataClient()

# 1. Get an audience. Default: the global pool — ready to go, zero setup.
audience = client.audience.get_audience_by_id("global")
# Curated domain pool (e.g. alignment): client.audience.get_audience_by_id("aud_MU1GZYoESyO")
# Only if you need task-specific qualification: client.audience.create_audience(name="My Evaluators")
#   — then add >= min_tasks qualification examples AND call audience.start_recruiting()
#   BEFORE assign_job (Key Gotcha 3).

# 2. Create a job definition (print the task's guide first)
job_def = client.job.create_classification_job_definition(
    name="Animal Classification",
    instruction="What animal is in this image?",
    answer_options=["Cat", "Dog", "Bird"],
    datapoints=["https://example.com/img1.jpg", "img2.jpg"],
    responses_per_datapoint=10,
)

# 3. Assign to audience (starts labeling)
job = audience.assign_job(job_def)

# 4. Watch responses come in (opens browser on the running job)
job.view()

# 5. Monitor and get results
progress = job.get_progress()   # Non-blocking snapshot: state, completion_percentage, recruiting
job.display_progress_bar()      # Or block on a live progress bar
results = job.get_results()     # dict: {"info", "results": [...], "summary"}; shape per job type in its guide
df = results.to_pandas()
```

## Key Gotchas

1. **Watch early responses** — after assigning, call `job.view()` to open the running job in the browser and check that labelers understand the instruction as intended
2. **Use `NoShuffleSetting()` for Likert scales** — ordered answer options get shuffled by default
3. **Custom audiences need ≥ `min_tasks` examples AND an explicit `start_recruiting()`** — recruiting never begins on its own. Add **at least `min_tasks` qualification examples** (default 10, min 3; otherwise `start_recruiting()` raises), then call `audience.start_recruiting()` **once**, before `assign_job`. Skip either step and the audience recruits nobody: the job is still created (with a warning), but it can never receive responses, so `get_results()` / `display_progress_bar()` raise an error saying the audience can never produce responses. Use `client.audience.get_audience_by_id("global")` when you don't need task-specific qualification.
   - **One audience = one task.** A custom audience is qualified for the specific task its examples describe. Reusing it for a different, unrelated task is a misuse — the qualification no longer applies and the quality guarantee is lost. Reuse it only for repeated/scheduled runs of the *same* task; spin up a new audience for a new task.
4. **Responses may exceed `responses_per_datapoint`** — concurrent labelers can cause slight overflow
5. **Stopping rules go in `responses_per_datapoint`** — `AdaptiveStopping()` (compare only, the compare default; raises on other job types), `QuorumStopping(threshold, max_responses)` (classification and compare), or an `int` for a fixed count. A compare pair uses ~21 responses on average with the default, ~31 for the hardest pairs. `quorum_threshold` and `confidence_threshold` are deprecated (`DeprecationWarning`); they cannot be set together, and raise `ValueError` combined with either class. With the compare default left in place they use a cap of 15
6. **Failed uploads abort job-definition creation** — if more than `failure_tolerance` (default `0.0`) of the datapoints fail to upload, **no job definition is created**. Fix the failing datapoints and call `e.retry()` on the `FailedUploadException`, which re-uploads only the failed ones and finishes the definition (`python -m rapidata skill errors`)
7. **Preview link printed on job creation** — creating a job definition prints a dashboard preview link; suppress prints with `rapidata_config.logging.silent_mode = True`
8. **Jobs can pause for manual review or funds** — `assign_job` always creates the job, but if its estimated cost exceeds your account balance it logs a cost warning and the job may pause until you top up. A job can also enter manual review (`ManualApproval`), become spend-limited (`SpendLimited`), or be `Blocked` because a rapid was flagged; since none of these completes on its own, `get_results()` raises an informative error naming the state instead of blocking — top up, wait for a reviewer, or unflag the rapid on `job.job_details_page` in the app, then retry.
9. **Don't restrict evaluations to English speakers for comprehension** — the instruction, the `context` string and answer options are translated into each labeler's device language automatically, so the global pool understands an English task. Turn this off with `OriginalLanguageOnlySetting()`. Two exceptions:
   - **Text assets are NOT translated by default** — datapoints uploaded with `data_type="text"` (and text `context_assets`) are shown exactly as supplied unless you add `TranslateTextAssetsSetting()`, which translates them into each labeler's language. That setting **always treats the source text as English** — for non-English text, leave it off and target speakers of the text's language with `LanguageFilter`. Results keep referencing the original text. `OriginalLanguageOnlySetting` wins over it. A job with text assets needs `TranslateTextAssetsSetting()` or a `LanguageFilter` (same rules as below), else `assign_job` and `update_filters` raise.
   - **Text inside images and videos is never translated.** To measure it (e.g. rendered text in a generated image), run it as its own job or leaderboard that asks only about that dimension, on an audience filtered with `LanguageFilter` for the text's language — not `CountryFilter`, since a country's labelers don't all read its language. Keep the other dimensions on the unfiltered audience.
   - **`OriginalLanguageOnlySetting` needs a `LanguageFilter`** on the audience or its `audience.filter([...])` (unlisted audiences are exempt): `assign_job` raises `ValueError` otherwise. Change them together: `update_filters` also raises when new filters drop language while an active job needs it. Override both checks only on the user's explicit request: `rapidata_config.skipLanguageFilterCheck = True`.
10. **Don't retry a template run blindly** — a `RapidataError` from `client.job.template.run_*()` saying "… so a job may have started" means exactly that: call `client.job.find_jobs(name)` first, and only call the method again if no job named exactly `name` was created after the call began. `find_jobs` also returns older jobs and longer names that contain the text, so never take its first result blindly.
11. **`assign_job` runs the object's revision, not the latest** — it sends `job_def.revision` and raises `RuntimeError` while the object has unsaved changes; `save()` first. Two objects loaded at the same revision never see each other's changes: each `save()` creates its own revision from what it loaded, and the last save becomes the latest. Use `save(require_latest=True)` to refuse instead: it raises `RevisionConflictError` (`e.latest_revision`) when someone saved since you loaded, creating nothing; then `discard_changes()`, `reload()`, reapply and save

## Migration from the removed Order API

The order-based API (`client.order`, `RapidataOrder`, `RapidataOrderManager`, `create_*_order()`) no longer exists — never generate code that uses it. Replace each `create_*_order()` with the matching `create_*_job_definition()` on `client.job`, validation sets with audience qualification examples, and `order.run()` with `audience.assign_job(job_def)`.
