# Signals (scheduled labeling)

> Part of the Rapidata agent skill: `python -m rapidata skill signals`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

A signal runs the same labeling job on a repeating schedule: bind a job definition to an audience and an interval, and Rapidata creates a new job on every tick.

```python
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[["flux_book.jpg", "mj_book.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

signal = client.signals.create_signal(
    name="Daily prompt alignment",
    audience=audience,           # also accepts id string
    job_definition=job_def,      # also accepts id string
    interval_hours=24,           # float
    # description="...",         # Optional
    # revision_number=...,       # Optional: pin a specific job-definition revision
    # is_public=True,            # Optional: let others in your org read the signal
)

# Inspect jobs created by the signal
for job in signal.get_jobs(page_size=10):
    print(job, job.get_status())

# Fire one job immediately instead of waiting for the schedule
signal.trigger()
job = signal.wait_for_next_job(timeout=600)  # blocks until the job is created
print(job.get_results())

# Manage the signal
signal.pause()
signal.resume()
signal.update(name="Hourly prompt alignment", interval_hours=1)  # also description=
signal.delete()

# Look signals up later
signal = client.signals.get_signal_by_id("signal_id")
signals = client.signals.find_signals(name="alignment", amount=10, page=1)
```

Each firing creates one `RapidataJob`.

## `client.signals.create_signal`

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Human-readable name for the signal |
| `audience` | `RapidataAudience` \| str | Audience (or id string) the spawned jobs will target |
| `job_definition` | `RapidataJobDefinition` \| str | Job definition (or id string) each firing creates a job from |
| `interval_hours` | float | Hours between consecutive firings; must be positive (`ValueError` otherwise) |
| `description` | str \| None | Optional description |
| `revision_number` | int \| None | Optional: pin a specific job-definition revision; omit for "latest at fire time" |
| `is_public` | bool | Default `False`. If `True`, the signal is readable by every authenticated user in your org |

## Signal methods

| Method | Description |
|--------|-------------|
| `signal.get_jobs(page=1, page_size=20, sort_descending=True)` | List `RapidataJob` objects created by this signal (newest first by default) |
| `signal.trigger()` | Fire one job immediately; returns right away — job created asynchronously |
| `signal.wait_for_next_job(timeout=300, poll_interval=5.0)` | Block until the next firing creates its job and return it |
| `signal.pause()` | Pause the scheduler (manual `trigger()` calls still fire); returns the signal |
| `signal.resume()` | Resume a paused signal; returns the signal |
| `signal.update(name=..., description=..., interval_hours=...)` | Keyword-only; update any of name, description, cadence; returns the signal |
| `signal.delete()` | Delete the signal and all its runs |

## Signal manager methods

| Method | Description |
|--------|-------------|
| `client.signals.get_signal_by_id("signal_id")` | Look up a signal by id |
| `client.signals.find_signals(name="", amount=10, page=1)` | Find signals by name |

## Signal properties

| Property | Description |
|----------|-------------|
| `id` | Unique signal id |
| `name` / `description` | Display name and optional description |
| `audience_id` | The audience each job targets |
| `job_definition_id` | The job definition each job is created from |
| `revision_number` | Pinned revision, or `None` for "latest at fire time" |
| `interval_hours` | How often the signal fires, in hours (float) |
| `next_run_at` / `last_run_at` | Timestamps of the next and most recent firings |
| `is_paused` | Whether the scheduler is currently skipping this signal |
| `is_public` | Whether other users can discover and read it |
| `created_at` | When the signal was created |

## Example

```python
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Prompt Alignment Job",
    instruction="Which image follows the prompt more accurately?",
    datapoints=[["flux_book.jpg", "mj_book.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

# Create a signal that fires every 24 hours
signal = client.signals.create_signal(
    name="Daily prompt alignment",
    audience=audience,
    job_definition=job_def,
    interval_hours=24,
)

# Inspect jobs created by the signal so far
for job in signal.get_jobs(page_size=10):
    print(job, job.get_status())

# Trigger a job immediately without waiting for the schedule
signal.trigger()
job = signal.wait_for_next_job(timeout=600)
results = job.get_results()

# Pause / resume / update
signal.pause()
signal.resume()
signal.update(name="Hourly prompt alignment", interval_hours=1)

# Look up later
signal = client.signals.get_signal_by_id("signal_id")
signals = client.signals.find_signals(name="alignment")

# Delete when no longer needed
signal.delete()
```
