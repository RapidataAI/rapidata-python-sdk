# Audience quality diagnostic for an image-editing benchmark

A small, cheap test cycle to answer one question before you build the full
benchmark: **can Rapidata's global audience reliably judge image edits?**

It runs comparisons whose correct answer you already know on the *raw global
crowd* (no quality filtering), measures how close the crowd gets, and then
*simulates* whether reliability-weighting or a validation set would close any
gap — so you learn what to add before scaling, without biasing the measurement.

## The idea

Three kinds of comparison pairs (set `bucket` in the manifest):

| Bucket | What it is | Truth | Tells you |
|---|---|---|---|
| `trap` | good edit vs an **obviously broken** image | known | spam / bot / inattention floor — should be ~100% |
| `gold` | correct edit vs a **plausibly-wrong** edit (edit not done, wrong object, artifacts, identity drift) | known | the real signal: does the crowd *perceive edit quality* like an expert? |
| `real` | genuine **model-vs-model** edit | none | consensus strength + split-half reliability on real data |

Aim for ~10–15 gold, ~3–5 trap, ~5–10 real pairs to start. The gold pairs are
the heart of it — invest your effort making the "wrong" option plausible but
genuinely worse, because that is exactly the discrimination your benchmark needs.

## Ready-to-run job: GPT Image 2 vs Nano Banana Pro

`gpt_vs_nano_pairs.json` wires up the 5 real edit comparisons in `inputs/` +
`edits/` (documented in `edits/README.md`). These are **real** model-vs-model
pairs with no ground-truth winner, so the report leads with a **model
comparison** (per-edit winner + overall weighted vote share) plus the
reliability metrics. Run it from inside this folder so the relative image paths
resolve:

```bash
python audience_quality_test.py launch --manifest gpt_vs_nano_pairs.json --dry-run   # validate
python audience_quality_test.py launch --manifest gpt_vs_nano_pairs.json             # launch
python audience_quality_test.py analyze                                              # later
```

Because this set has no gold/trap pairs, the verdict reflects *reliability and
model preference, not accuracy*. To also test whether the crowd judges edits
*correctly*, add gold/trap pairs (see the template below).

## Usage

```bash
# from this folder, with the rapidata SDK importable and creds configured
pip install rapidata        # or: uv pip install rapidata

# 0. validate your manifest, see the plan + cost, create nothing
python audience_quality_test.py launch --manifest sample_pairs.json --dry-run

# 1. launch on the GLOBAL audience
python audience_quality_test.py launch --manifest sample_pairs.json

# 2. later (responses arrive over minutes–hours), analyse + get a verdict
python audience_quality_test.py analyze
#    add --preliminary to peek before the order is fully complete
```

To quantify what a filter buys you, re-run into a separate state file and compare:

```bash
python audience_quality_test.py launch --manifest sample_pairs.json \
    --filter-countries US,GB,CA,AU --state filtered_state.json
python audience_quality_test.py analyze --state filtered_state.json
```

## What you get

The report covers four things, each with a target threshold, then a single
`PASS / MARGINAL / FAIL` verdict and data-driven recommendations:

- **Attention/spam** — trap-pair majority + individual accuracy.
- **Edit-quality perception** — gold-pair majority accuracy, individual
  accuracy, and a **reliability-weighted** majority (what a validation set /
  `summedUserScores` weighting would buy). Plus an **accuracy-vs-#responses
  curve** so you can pick `responses_per_datapoint` (the smallest k where
  majority accuracy plateaus).
- **Reliability** — split-half winner agreement, and decisiveness on gold vs
  real pairs (real pairs near 50% are coin-flips / true ties, not noise).
- **Who is voting** — gold accuracy broken down by annotator userScore band and
  by country, which tells you whether weighting or a geo/language filter helps.

Thresholds live at the top of `audience_quality_test.py` (`TH_*`) — tune them to
your standards.

## Why this design

This mirrors what KontextBench discovered the hard way. They first ran an "Image
persistence" leaderboard with no quality control, then re-ran it *with a
validation set* and the winner changed (gpt-image-1 dropped from 1st to a tie
for 2nd). Same crowd, same task — the difference was screening out unreliable
voters. Rather than pay to discover that after the fact, this script estimates
the value of weighting/validation up front from the `userScore` breakdown, so
you can decide whether the global audience is good enough **as-is**, good enough
**with weighting/validation**, or **not good enough** for a given edit category.

## Notes

- Asset file names must be unique across the manifest — results are matched back
  to ground truth by file name.
- `input` (the source image) is optional but recommended for editing: an edit
  can't be judged without seeing what it started from. Include it on all pairs
  or none.
- The diagnostic deliberately uses **no validation set** so it measures the raw
  global crowd. The analysis simulates the benefit of validation instead.
