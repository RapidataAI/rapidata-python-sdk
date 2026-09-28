# Flows for Preference Data (DPO / RLHF / Best-of-N)

Guidance for using ranking flows as the human-preference signal in a training loop: collecting DPO/RLHF pairs while a model generates, or picking the best of N candidates at inference time. The flow API itself is documented in the "Flows" section of the main guide (`python -m rapidata skill`).

## Flows or jobs?

- **Use a flow** when candidates are generated on the fly and each group should go to evaluation as soon as it exists: DPO data collected alongside generation, online RLHF, best-of-N.
- **Use a ranking job definition** when all candidates exist upfront and you can submit one large batch.

Before choosing settings, answer four questions:

1. **Turnaround:** what latency per group is desired, and what is the maximum you can tolerate? A few minutes per group is a sensible DPO target. Online RL and best-of-N need tighter bounds.
2. **Volume:** how many groups, and how often?
3. **Parallelism:** flows get faster in aggregate with more groups in flight. One flow item takes at least a minute or two, but many items running in parallel finish in about the same time as one.
4. **Bandwidth:** turnaround × volume gives the sustained responses per minute that training needs. If that rate is high, talk to Rapidata about a guaranteed-throughput setup before scaling.

## How a flow item completes

A flow item ends when one of these happens:

- It reaches the flow's `max_response_threshold` (for classify flows, `max_responses_per_datapoint`).
- Its `time_to_live` (set per batch in `create_new_flow_batch`, up to 3600 s, default 240 s; at least 60 s with the default flow settings) expires.

**Most items are expected to end by TTL.** (`min_response_threshold` defaults to the max; set it lower explicitly.) To avoid overflow, Rapidata stops handing out an item somewhere between the min and max thresholds. The item then waits for its TTL without collecting more votes. If it ended below the minimum it is `Incomplete`, but its results are still returned.

**The consequence:** the TTL, not the max threshold, usually sets turnaround. A long TTL makes items sit idle for most of their lifetime. Set `time_to_live` close to your turnaround target (e.g. `240`–`300` for a few minutes), not to the 3600 s ceiling.

## DPO / RLHF collection

- **Match turnaround to generation time.** With several generator workers in parallel, one flow item's turnaround should roughly equal the time to generate one group, so generators never wait on ratings. Tune `time_to_live` to that.
- **Keep many items in flight.** Submit each group as soon as it is generated rather than batching groups up.
- **Turn results into pairs.** A ranking item's `get_results()` returns an Elo score per candidate (`FlowItemResult.datapoints`). Take the top and bottom as chosen/rejected, or use `get_win_loss_matrix()` for per-pair preference counts, which lets you drop pairs with a narrow margin.
- **Validation tasks** mixed into the flow (`validation_set_id=` on `create_ranking_flow`, built with `client.validation`) strengthen the signal. For help tuning them, contact Rapidata.

```python
flow = client.flow.create_ranking_flow(
    name="DPO preference collection",
    instruction="Which image looks more realistic?",
    max_response_threshold=30,
    min_response_threshold=20,
)

# Per generated group, as soon as it exists:
item = flow.create_new_flow_batch(
    datapoints=candidate_paths,
    time_to_live=300,
)
result = item.get_results()                      # blocks until the item completes
ranked = sorted(result.datapoints.items(), key=lambda kv: kv[1], reverse=True)
chosen, rejected = ranked[0][0], ranked[-1][0]
```

## Best-of-N

Latency matters most here, even at the cost of efficiency:

- **Low thresholds.** Set a small `min_response_threshold` / `max_response_threshold` so an item can finish quickly.
- **Short TTL.** Set it to the latency you can tolerate.
- **Preheat.** Call `client.flow.preheat()` ~5 minutes before a latency-sensitive burst.
- **Aggressive distribution.** Rapidata can serve an item to many more annotators than needed upfront, trading overflow for speed, and can load tasks one at a time so they are never stale when shown. Neither is exposed in the SDK; ask Rapidata to enable them.

## Designing the comparison

These tips apply to any Rapidata task. They matter most when the signal trains a model, because a confounded preference is learned as faithfully as a real one.

- **Show only the context the dimension needs.** Unnecessary context is the most common confounder.
  - Rating photorealism? Leave out the prompt, or ratings drift toward prompt adherence.
  - Rating counting? Include only the counting part of the prompt, not the scene, colours or lighting.
  - Rating text rendering? Crop to the text (e.g. a collage of the crops) so nothing else in the image competes.
- **One criterion per task.** Several criteria folded into one question reduce consistency. Split them into separate flows or leaderboards.
- **Plain, short instructions.** No jargon; labelers answer in ~25 seconds, mostly on phones.
- **Match annotators to the content.** When rating text in a script, target people who read that script. Flows take no audience or filters in the SDK: ask Rapidata to restrict a flow's annotators, or use a ranking job definition on a filtered audience (`LanguageFilter` / `CountryFilter`).
- **Check the layout with a preview** before scaling. Some content renders better with a setting (see Settings in the main guide, `python -m rapidata skill`).
- **Pilot small.** Try a few setups (instruction wording, context, thresholds) at small scale, compare agreement, then roll out the best one.
