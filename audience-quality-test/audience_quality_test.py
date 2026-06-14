#!/usr/bin/env python3
"""Measure whether Rapidata's global audience is good enough to judge image edits.

Before committing to a full image-editing benchmark, this script runs a small
diagnostic cycle on the *raw global crowd* (no quality filtering) using
comparisons whose correct answer you already know, and reports how reliably the
crowd recovers it. It then simulates whether reliability-weighting or a
validation set would close any gap -- so you learn what (if anything) to add
before scaling up, without biasing the measurement.

Orders collect responses asynchronously, so the flow is two phases:

    # 1. launch the diagnostic order on the global audience
    python audience_quality_test.py launch --manifest sample_pairs.json

    # 2. once responses have come in (minutes-to-hours), analyse them
    python audience_quality_test.py analyze

Useful flags:
    --dry-run                 validate the manifest and print the plan; no order
    --filter-countries US,GB  launch on a country-filtered crowd instead of global
                              (re-run into a second --state file to compare)
    --preliminary             analyse before the order is fully complete

Auth: the SDK reads your Rapidata credentials the usual way (RapidataClient()).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict

STATE_DEFAULT = "audience_test_state.json"

# Verdict thresholds. Tune to your standards -- these are deliberately strict
# because a benchmark's whole value is that its rankings are trustworthy.
TH_TRAP_MAJORITY = 0.95   # fraction of trap pairs the crowd majority must get right
TH_TRAP_RESPONSE = 0.85   # fraction of individual trap responses that must be right
TH_GOLD_MAJORITY = 0.90   # fraction of gold pairs the crowd majority must get right
TH_GOLD_RESPONSE = 0.70   # individual gold responses correct (individuals are noisy)
TH_SPLITHALF = 0.80       # two random halves of votes must pick the same winner this often
SEED = 7


# --------------------------------------------------------------------------- #
# Manifest + helpers
# --------------------------------------------------------------------------- #
def basename(url: str) -> str:
    """Asset identifier Rapidata reports back == the file name (no query string)."""
    return os.path.basename(str(url).split("?")[0])


def load_manifest(path: str) -> dict:
    with open(path) as f:
        m = json.load(f)

    pairs = m.get("pairs", [])
    if not pairs:
        sys.exit(f"Manifest {path!r} has no 'pairs'.")

    has_input = [bool(p.get("input")) for p in pairs]
    if any(has_input) and not all(has_input):
        sys.exit(
            "media_contexts must be all-or-nothing: either every pair has an "
            "'input' (the source image shown to the annotator) or none do."
        )

    # Asset basenames must be unique across the order; results are keyed by them.
    seen: Counter = Counter()
    for p in pairs:
        for side in ("a", "b"):
            seen[basename(p[side])] += 1
    dupes = [k for k, v in seen.items() if v > 1]
    if dupes:
        sys.exit(f"Duplicate asset file names (results can't be matched): {dupes}")

    for p in pairs:
        b = p.get("bucket")
        if b not in ("trap", "gold", "real"):
            sys.exit(f"Each pair needs bucket in trap/gold/real, got {b!r}")
        if b in ("trap", "gold") and p.get("truth") not in ("a", "b"):
            sys.exit(f"{b} pairs need truth = 'a' or 'b' (pair: {p.get('edit')!r})")
    return m


# --------------------------------------------------------------------------- #
# Phase 1: launch
# --------------------------------------------------------------------------- #
def launch(args) -> None:
    m = load_manifest(args.manifest)
    pairs = m["pairs"]
    instruction = m.get(
        "instruction",
        "Which image more accurately applies the requested edit while leaving "
        "everything else unchanged?",
    )
    rpd = int(m.get("responses_per_datapoint", 30))

    datapoints = [[p["a"], p["b"]] for p in pairs]
    contexts = [p.get("edit", "") for p in pairs]
    media_contexts = [[p["input"]] for p in pairs] if pairs[0].get("input") else None

    counts = Counter(p["bucket"] for p in pairs)
    print("Plan:")
    print(f"  pairs:    {len(pairs)}  (trap={counts['trap']} "
          f"gold={counts['gold']} real={counts['real']})")
    print(f"  per pair: {rpd} responses  ->  ~{len(pairs) * rpd} total responses")
    print(f"  audience: {'countries=' + args.filter_countries if args.filter_countries else 'GLOBAL (no filter)'}")
    print(f"  shows input image as context: {bool(media_contexts)}")
    if args.dry_run:
        print("\n--dry-run: manifest is valid, no order created.")
        return

    from rapidata import RapidataClient  # imported here so --dry-run needs no creds

    filters = None
    if args.filter_countries:
        from rapidata import CountryFilter
        filters = [CountryFilter([c.strip().upper() for c in args.filter_countries.split(",")])]

    client = RapidataClient()
    order = client.order.create_compare_order(
        name=m.get("name", "Audience quality diagnostic"),
        instruction=instruction,
        datapoints=datapoints,
        contexts=contexts,
        media_contexts=media_contexts,
        responses_per_datapoint=rpd,
        filters=filters,
    ).run()

    # Persist everything analyze() needs to match results back to ground truth.
    state = {
        "order_id": order.id,
        "instruction": instruction,
        "audience": args.filter_countries or "global",
        "pairs": [
            {
                "bucket": p["bucket"],
                "edit": p.get("edit", ""),
                "a": basename(p["a"]),
                "b": basename(p["b"]),
                "truth": basename(p[p["truth"]]) if p.get("truth") in ("a", "b") else None,
            }
            for p in pairs
        ],
    }
    with open(args.state, "w") as f:
        json.dump(state, f, indent=2)
    print(f"\nLaunched order {order.id}. State saved to {args.state}.")
    print(f"Analyse later with:  python {sys.argv[0]} analyze --state {args.state}")


# --------------------------------------------------------------------------- #
# Phase 2: analyze
# --------------------------------------------------------------------------- #
def _pair_index(state: dict) -> dict:
    """frozenset({assetA, assetB}) -> pair metadata, for matching result items."""
    return {frozenset((p["a"], p["b"])): p for p in state["pairs"]}


def _match(result_item: dict, index: dict):
    agg = result_item.get("aggregatedResults", {})
    key = frozenset(agg.keys())
    return index.get(key)


def _responses(result_item: dict) -> list[dict]:
    """Flatten detailedResults into [{voted, country, language, score}]."""
    out = []
    for d in result_item.get("detailedResults", []) or []:
        ud = d.get("userDetails", {}) or {}
        out.append({
            "voted": d.get("votedFor"),
            "country": ud.get("country"),
            "language": ud.get("language"),
            "score": (ud.get("userScores") or {}).get("global"),
        })
    return out


def _majority_correct(votes_for_truth: list[bool]) -> float:
    """1.0 if majority correct, 0.5 on a tie, 0.0 otherwise."""
    if not votes_for_truth:
        return 0.0
    right = sum(votes_for_truth)
    half = len(votes_for_truth) / 2
    return 1.0 if right > half else (0.5 if right == half else 0.0)


def analyze(args) -> None:
    with open(args.state) as f:
        state = json.load(f)

    from rapidata import RapidataClient
    client = RapidataClient()
    order = client.order.get_order_by_id(state["order_id"])
    results = order.get_results(preliminary_results=args.preliminary)
    report(state, dict(results))


def report(state: dict, results: dict) -> None:
    """Pure analysis: given the saved state and a results payload, print the
    report + verdict. Separated from the SDK fetch so it can be unit-tested."""
    index = _pair_index(state)
    items = results.get("results", [])
    print(f"Order {state['order_id']}  audience={state['audience']}  "
          f"datapoints returned={len(items)}\n")

    # Bucket the per-pair, per-response data --------------------------------- #
    rng = random.Random(SEED)
    gold_pair_majority: list[float] = []
    gold_pair_majority_weighted: list[float] = []
    gold_resp_correct: list[bool] = []
    gold_vote_lists: list[list[bool]] = []        # per gold pair: votes correct?
    trap_pair_majority: list[float] = []
    trap_resp_correct: list[bool] = []
    real_decisiveness: list[float] = []           # max ratio on real pairs
    gold_decisiveness: list[float] = []
    splithalf_agree: list[float] = []             # over all pairs with >=4 votes
    user_scores: list[float] = []
    by_score_band: dict[str, list[bool]] = defaultdict(list)  # gold accuracy by band
    by_country: dict[str, list[bool]] = defaultdict(list)
    by_language: dict[str, list[bool]] = defaultdict(list)
    unmatched = 0

    for item in items:
        p = _match(item, index)
        if p is None:
            unmatched += 1
            continue
        bucket, truth = p["bucket"], p["truth"]
        resp = _responses(item)
        agg = item.get("aggregatedResults", {})
        total = sum(agg.values()) or 1
        decisiveness = max(agg.values()) / total

        # split-half winner agreement (reliability), any pair with enough votes
        voters_a = [r["voted"] == p["a"] for r in resp]
        if len(voters_a) >= 4:
            agree = 0
            for _ in range(200):
                shuffled = voters_a[:]
                rng.shuffle(shuffled)
                h = len(shuffled) // 2
                w1 = sum(shuffled[:h]) > h / 2
                w2 = sum(shuffled[h:]) > (len(shuffled) - h) / 2
                agree += (w1 == w2)
            splithalf_agree.append(agree / 200)

        for r in resp:
            if r["score"] is not None:
                user_scores.append(r["score"])

        if bucket == "real":
            real_decisiveness.append(decisiveness)
            continue

        # trap / gold: we know the truth
        gold_decisiveness.append(decisiveness) if bucket == "gold" else None
        votes_for_truth = [r["voted"] == truth for r in resp]

        # unweighted majority
        maj = _majority_correct(votes_for_truth)
        # reliability-weighted majority (simulates what summedUserScores buys you)
        w_truth = sum((r["score"] or 0) for r in resp if r["voted"] == truth)
        w_other = sum((r["score"] or 0) for r in resp if r["voted"] != truth)
        maj_w = 1.0 if w_truth > w_other else (0.5 if w_truth == w_other else 0.0)

        if bucket == "trap":
            trap_pair_majority.append(maj)
            trap_resp_correct.extend(votes_for_truth)
        else:
            gold_pair_majority.append(maj)
            gold_pair_majority_weighted.append(maj_w)
            gold_resp_correct.extend(votes_for_truth)
            gold_vote_lists.append(votes_for_truth)
            for r in resp:
                correct = r["voted"] == truth
                s = r["score"]
                band = "unknown" if s is None else ("lo <0.4" if s < 0.4 else ("mid 0.4-0.6" if s < 0.6 else "hi >0.6"))
                by_score_band[band].append(correct)
                if r["country"]:
                    by_country[r["country"]].append(correct)
                if r["language"]:
                    by_language[r["language"]].append(correct)

    # --- Report ------------------------------------------------------------- #
    def pct(xs):
        return f"{100 * statistics.mean(xs):.1f}%" if xs else "n/a"

    print("=" * 64)
    print("ATTENTION / SPAM  (trap pairs: obvious good vs broken)")
    print(f"  pairs evaluated:        {len(trap_pair_majority)}")
    print(f"  crowd-majority correct: {pct(trap_pair_majority)}   (target >= {TH_TRAP_MAJORITY:.0%})")
    print(f"  individual responses:   {pct(trap_resp_correct)}   (target >= {TH_TRAP_RESPONSE:.0%})")

    print("\n" + "=" * 64)
    print("EDIT-QUALITY PERCEPTION  (gold pairs: correct vs plausibly-wrong edit)")
    print(f"  pairs evaluated:           {len(gold_pair_majority)}")
    print(f"  crowd-majority correct:    {pct(gold_pair_majority)}   (target >= {TH_GOLD_MAJORITY:.0%})")
    print(f"  reliability-weighted maj.: {pct(gold_pair_majority_weighted)}   (what a validation set / weighting buys)")
    print(f"  individual responses:      {pct(gold_resp_correct)}   (target >= {TH_GOLD_RESPONSE:.0%})")

    # accuracy vs number of votes -> recommended responses_per_datapoint
    if gold_vote_lists:
        print("\n  majority accuracy vs #responses aggregated (bootstrap):")
        maxk = max(len(v) for v in gold_vote_lists)
        for k in [1, 3, 5, 7, 10, 15, 20, 30]:
            if k > maxk:
                break
            accs = []
            for votes in gold_vote_lists:
                if len(votes) < k:
                    continue
                hits = 0
                for _ in range(300):
                    accs_sample = rng.sample(votes, k)
                    hits += _majority_correct(accs_sample)
                accs.append(hits / 300)
            if accs:
                print(f"    k={k:>2}:  {100 * statistics.mean(accs):5.1f}%")

    print("\n" + "=" * 64)
    print("RELIABILITY  (do two halves of the votes agree on the winner?)")
    print(f"  split-half winner agreement: {pct(splithalf_agree)}   (target >= {TH_SPLITHALF:.0%})")
    print(f"  decisiveness  gold pairs:    {pct(gold_decisiveness)}   (how lopsided the vote is)")
    print(f"  decisiveness  real pairs:    {pct(real_decisiveness)}   (near 50% => coin-flip / true ties)")

    print("\n" + "=" * 64)
    print("WHO IS VOTING  (does filtering / weighting help?)")
    if user_scores:
        print(f"  annotator global userScore: median={statistics.median(user_scores):.2f} "
              f"mean={statistics.mean(user_scores):.2f} n={len(user_scores)}")
    print("  gold accuracy by reliability band:")
    for band in ("hi >0.6", "mid 0.4-0.6", "lo <0.4", "unknown"):
        xs = by_score_band.get(band)
        if xs:
            print(f"    {band:<12} {pct(xs):>7}  (n={len(xs)})")
    top_countries = sorted(by_country.items(), key=lambda kv: -len(kv[1]))[:6]
    if top_countries:
        print("  gold accuracy by top countries:")
        for c, xs in top_countries:
            print(f"    {c:<4} {pct(xs):>7}  (n={len(xs)})")

    if unmatched:
        print(f"\n  note: {unmatched} returned datapoints could not be matched to the manifest.")

    # --- Verdict ------------------------------------------------------------ #
    print("\n" + "#" * 64)
    checks = {
        "trap majority": (statistics.mean(trap_pair_majority) if trap_pair_majority else 0) >= TH_TRAP_MAJORITY,
        "trap responses": (statistics.mean(trap_resp_correct) if trap_resp_correct else 0) >= TH_TRAP_RESPONSE,
        "gold majority": (statistics.mean(gold_pair_majority) if gold_pair_majority else 0) >= TH_GOLD_MAJORITY,
        "gold responses": (statistics.mean(gold_resp_correct) if gold_resp_correct else 0) >= TH_GOLD_RESPONSE,
        "split-half": (statistics.mean(splithalf_agree) if splithalf_agree else 0) >= TH_SPLITHALF,
    }
    passed = sum(checks.values())
    if passed == len(checks):
        verdict = "PASS -- global audience is good enough for this task as-is."
    elif checks["trap majority"] and checks["gold majority"]:
        verdict = "MARGINAL -- usable, but tighten it (see recommendations)."
    else:
        verdict = "FAIL -- the raw global crowd does not reliably judge these edits."
    print(f"VERDICT: {verdict}")
    for name, ok in checks.items():
        print(f"   [{'x' if ok else ' '}] {name}")

    # Targeted, data-driven recommendations
    print("\nRecommendations:")
    gm = statistics.mean(gold_pair_majority) if gold_pair_majority else 0
    gmw = statistics.mean(gold_pair_majority_weighted) if gold_pair_majority_weighted else 0
    if gmw - gm >= 0.05:
        print("  - Reliability weighting helps materially: use summedUserScores (not raw\n"
              "    vote counts) and add a validation set so weak annotators are screened.")
    hi = by_score_band.get("hi >0.6"); lo = by_score_band.get("lo <0.4")
    if hi and lo and (statistics.mean(hi) - statistics.mean(lo)) >= 0.1:
        print("  - High-userScore annotators are clearly more accurate: a userScore filter\n"
              "    or a ConditionalValidationSelection will raise quality.")
    if not checks["trap responses"]:
        print("  - Low trap pass-rate => spam/inattentive responses. Add trap items and a\n"
              "    validation set to gate them out.")
    if gold_vote_lists:
        print("  - Use the 'accuracy vs #responses' curve above to pick responses_per_datapoint\n"
              "    (the smallest k where majority accuracy plateaus near its max).")
    print("  - Re-run with --filter-countries / --filter-languages into a second --state\n"
          "    file and compare verdicts to quantify what a geo/language filter buys you.")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("launch", help="create the diagnostic order")
    pl.add_argument("--manifest", default="sample_pairs.json")
    pl.add_argument("--state", default=STATE_DEFAULT)
    pl.add_argument("--filter-countries", default="", help="e.g. US,GB,DE (default: global)")
    pl.add_argument("--dry-run", action="store_true")
    pl.set_defaults(func=launch)

    an = sub.add_parser("analyze", help="fetch responses and print the report")
    an.add_argument("--state", default=STATE_DEFAULT)
    an.add_argument("--preliminary", action="store_true", help="analyse before completion")
    an.set_defaults(func=analyze)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
