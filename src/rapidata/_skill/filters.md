# Audience filters and filtered audiences

> Part of the Rapidata agent skill: `python -m rapidata skill filters`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here.

Creating and training audiences: `python -m rapidata skill audiences`.

## Demographic filters

All filters are importable from the top-level `rapidata` package.

```python
from rapidata import (
    CountryFilter, LanguageFilter, UserScoreFilter,
    AgeFilter, GenderFilter, DeviceFilter, CampaignFilter, CustomFilter,
    AgeGroup, Gender, DeviceType,
    NotFilter, OrFilter, AndFilter,
)

# --- Recruitment filters on an audience: CountryFilter and LanguageFilter
#     (plus the And/Or/Not combinators). UserScoreFilter/CampaignFilter/CustomFilter
#     raise NotImplementedError here; demographic/device targeting belongs on .filter() (below). ---
audience.update_filters([
    CountryFilter(country_codes=["US", "CA", "GB"]),                  # 2-letter ISO codes (uppercased)
    LanguageFilter(language_codes=["en", "fr"]),                      # ISO 639-1 codes (lowercased); unknown codes raise ValueError
])

# Combine filters with logic operators
combined = OrFilter([filter1, filter2])
audience.update_filters([NotFilter(combined)])

# Derive a filtered subset of a trained audience without re-onboarding labelers.
# Supported filters for .filter(): CountryFilter, LanguageFilter, AgeFilter,
# GenderFilter, DeviceFilter (plus And/Or/Not combinators). Multiple filters are ANDed.
filtered = base_audience.filter([
    CountryFilter(["US"]),
    LanguageFilter(["en"]),
    AgeFilter([AgeGroup.BETWEEN_18_29]),
])
job = filtered.assign_job(job_def)  # filtered is a RapidataFilteredAudience

# Combine filters with &, |, ~ operators
us_or_ca_not_fr = base_audience.filter([
    (CountryFilter(["US"]) | CountryFilter(["CA"])) & ~LanguageFilter(["fr"]),
])
```

### Filter signatures

| Filter | Signature | Works on audiences? |
|--------|-----------|---------------------|
| `CountryFilter` | `(country_codes: list[str])` | yes |
| `LanguageFilter` | `(language_codes: list[str])` | yes |
| `UserScoreFilter` | `(lower_bound: float = 0.0, upper_bound: float = 1.0, dimension: str \| None = None)` — bounds 0–1 | no (raises `NotImplementedError`) |
| `AgeFilter` | `(age_groups: list[AgeGroup])` | `.filter()` only |
| `GenderFilter` | `(genders: list[Gender])` | `.filter()` only |
| `DeviceFilter` | `(device_types: list[DeviceType])` | `.filter()` only |
| `CampaignFilter` | `(campaign_ids: list[str])` | no (raises `NotImplementedError`) |
| `CustomFilter` | `(identifier: str, values: list[str])` | no (raises `NotImplementedError`) |
| `NotFilter` | `(filter: RapidataFilter)` | both |
| `OrFilter` | `(filters: list[RapidataFilter])` | both |
| `AndFilter` | `(filters: list[RapidataFilter])` | both |

Note: use `CountryFilter`, `LanguageFilter`, and the `And`/`Or`/`Not` combinators as recruitment filters (`create_audience(filters=...)` / `audience.update_filters(...)`). Target by age, gender or device with `audience.filter(...)` (deriving a filtered audience from graduates) using `AgeFilter`, `GenderFilter`, and `DeviceFilter`. There is no `DemographicFilter` class. `AgeGroup` members: `UNDER_18`, `BETWEEN_18_29`, `BETWEEN_30_39`, `BETWEEN_40_49`, `BETWEEN_50_64`, `OVER_65`; `Gender`: `MALE`, `FEMALE`, `OTHER`; `DeviceType`: `UNKNOWN`, `PHONE`, `TABLET`. `UserScoreFilter`, `CampaignFilter`, and `CustomFilter` cannot be attached to audiences at all (they raise `NotImplementedError`).

## Examples

### Audience with Demographic Filters

```python
from rapidata import (
    RapidataClient, CountryFilter, LanguageFilter,
)

client = RapidataClient()
audience = client.audience.create_audience(name="US English Evaluators", min_tasks=3)
audience.update_filters([
    CountryFilter(country_codes=["US", "CA"]),
    LanguageFilter(language_codes=["en"]),
])

# Recruiting is explicit: a custom audience recruits nobody until you add >= min_tasks qualification
# examples (default 10, min 3) AND then call start_recruiting(). A job assigned before recruiting starts can never
# receive responses (get_results() raises). So: add examples, start_recruiting, THEN assign.
EXAMPLES = [
    ("clear.jpg", ["Excellent"]),
    ("decent.jpg", ["Good"]),
    ("blurry.jpg", ["Poor"]),
]
for datapoint, truth in EXAMPLES:
    audience.add_classification_example(
        instruction="Rate the image quality",
        answer_options=["Poor", "Good", "Excellent"],
        datapoint=datapoint,
        truth=truth,
        data_type="media",
    )

audience.start_recruiting()  # required — without this the job below never gets responses

job_def = client.job.create_classification_job_definition(
    name="Image Quality (US/EN)",
    instruction="Rate the image quality",
    answer_options=["Poor", "Good", "Excellent"],
    datapoints=["img1.jpg", "img2.jpg"],
    responses_per_datapoint=10,
)
job = audience.assign_job(job_def)
job.display_progress_bar()
results = job.get_results()

# If you DON'T need task-specific qualification, skip create_audience + examples entirely
# and use the ready-to-go global pool: client.audience.get_audience_by_id("global").
#
# update_filters sets recruitment filters: CountryFilter / LanguageFilter (+ And/Or/Not).
# AgeFilter / GenderFilter / DeviceFilter narrow the graduates, so use them with
# audience.filter(...) (see below).
```

### Filtered Audience

Derive a filtered subset of a trained audience without re-onboarding labelers:

```python
from rapidata import RapidataClient, CountryFilter, LanguageFilter, AgeFilter, AgeGroup

client = RapidataClient()

base = client.audience.get_audience_by_id("audience_id")

# .filter() narrows an audience's graduates. Beyond CountryFilter / LanguageFilter it
# accepts AgeFilter, GenderFilter and DeviceFilter, plus And/Or/Not (& | ~).
# Multiple filters in the list are ANDed.
filtered = base.filter([
    CountryFilter(["US"]),
    LanguageFilter(["en"]),
    AgeFilter([AgeGroup.BETWEEN_18_29]),
])

job_def = client.job.create_classification_job_definition(
    name="US Young Adult Classification",
    instruction="What product is shown?",
    answer_options=["Phone", "Laptop", "Tablet"],
    datapoints=["p1.jpg", "p2.jpg"],
)
job = filtered.assign_job(job_def)
job.display_progress_bar()
results = job.get_results()
```
