# Billing and cost estimates

> Part of the Rapidata agent skill: `python -m rapidata skill billing`. The **Task design rules** and **Key Gotchas** in the main guide (`python -m rapidata skill`) apply to everything here; parameters shared by every job type are in `python -m rapidata skill reference`.

## Cost estimates

Both `RapidataJobDefinition` and `RapidataJob` expose an `estimated_cost` property returning a `CostEstimate` — an approximate estimate of what the job will cost to run to completion. Reading it from a job definition lets you check the cost of a run **before** assigning it to an audience. `CostEstimate` is importable from the top-level `rapidata` package.

The estimate is priced shortly after the definition/job is created, so the first read blocks briefly while polling until the estimate is available (raising `TimeoutError` if it is still not ready after a few minutes), then caches the result.

```python
job_def = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[["midjourney.jpg", "flux.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

estimate = job_def.estimated_cost   # blocks briefly until priced
print(f"About {estimate.estimated_cost} for {estimate.required_responses} responses")

# The same property is available once the job is running
job = audience.assign_job(job_def)
print(job.estimated_cost.estimated_cost)
```

### `CostEstimate` fields

| Field | Type | Description |
|-------|------|-------------|
| `estimated_cost` | float | Estimated total cost of running the job to completion, in your account's billing currency |
| `datapoint_count` | int | Number of datapoints the job will label |
| `required_responses` | int | Total number of responses the job collects to complete |

This is an **estimate, not the final bill**: it is based on a sample of the job's tasks scaled to the number of responses requested, so the amount actually charged can differ. Early stopping can also lower the final cost by collecting fewer responses than the maximum. For adaptive compare jobs (the compare default) there is no forecast for the expected response count yet, so the estimate uses the `max_responses` setting per pair, which is well above the expected cost.

## Billing

`client.billing` (a `RapidataBillingManager`, created during client construction) reads how much the current billing period has cost so far and how much credit is left. Billing is settled per **organization**, so its figures cover everything the organization spent — not only the jobs this client created.

```python
period = client.billing.get_current_billing_period()   # BillingPeriod
print(f"${period.outstanding_cost} accrued over {period.response_count} responses")
```

### `client.billing.get_current_billing_period() → BillingPeriod`

Returns the billing period currently accruing cost. Raises `RapidataError` with status `404` if the organization has no active billing period (a period only opens once there is something to bill).

### `client.billing.get_outstanding_balance() → float`

Returns the total the organization currently owes, in US dollars rounded to the cent (`0.0` when nothing is owed). Covers finalized-but-unpaid invoices plus the settled cost of ended periods not yet invoiced; it does **not** include the current, still-accruing period. The figure is already net of vouchers and discounts, and is settled per organization.

```python
owed = client.billing.get_outstanding_balance()   # e.g. 42.50
print(f"${owed} outstanding")
```

### Automatic top-ups

Prepaid organizations only, and only their owners and admins; anyone else gets a `RapidataError`. While enabled, the saved card is charged `amount` whenever the balance falls below `threshold` (US dollars).

- `client.billing.get_auto_top_up() → AutoTopUp`: frozen dataclass with `enabled` (bool), `threshold`, `amount` (`float | None`), `card_brand`, `card_last4` (`str | None`) and `failed_at` (`datetime | None`).
- `client.billing.configure_auto_top_up(threshold, amount) → str | None`: `amount` must be at least 20, greater than `threshold`, with at most two decimals. Returns `None` when a card is already saved and the settings apply at once. Otherwise returns the url of a hosted checkout page: nothing is enabled until a **person** opens it and saves a card, so hand the url to the user instead of treating the call as done.
- `client.billing.disable_auto_top_up() → None`: switches them off **and removes the saved card**.

A declined charge pauses them (`enabled` is `False`, `failed_at` is set, the card stays saved); `configure_auto_top_up()` resumes. Configuring spends the organization's money later, so only call it when the user asked for it.

```python
checkout_url = client.billing.configure_auto_top_up(threshold=50, amount=200)
if checkout_url is not None:
    print(f"Open this page and save a card to start automatic top-ups: {checkout_url}")
```

### `BillingPeriod` fields

A frozen dataclass. All amounts are in **US dollars**, rounded to the cent. Values are a snapshot — fetch again for an up-to-date figure. `BillingPeriod`, `AutoTopUp` (and `RapidataBillingManager`) are importable from the top-level `rapidata` package (and re-exported from `rapidata.rapidata_client`).

```python
from rapidata import AutoTopUp, BillingPeriod, RapidataBillingManager
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | The billing period's id |
| `start_date` / `end_date` | datetime | When the period starts and ends |
| `status` | str | Lifecycle status: `"Open"` while still accruing cost; otherwise one of `"Invoiced"`, `"Void"`, `"Reconciling"`, `"PendingReview"`, `"Closed"` |
| `outstanding_cost` | float | Net cost accrued so far (`gross_cost` minus `discount`) — what the period would be invoiced for today |
| `gross_cost` | float | Cost accrued so far, before discounts |
| `discount` | float | Discounts applied to the period so far |
| `response_count` | int | Number of billable responses collected in the period |
| `credits` | `float \| None` | Prepaid credit still available, or `None` when the organization is billed for usage rather than from a prepaid balance. An organization-level balance that carries across periods |
| `effective_limit` | `float \| None` | The most the organization may spend this period, or `None` when it spends without a cap. On a prepaid plan this is the total credit granted, and `credits` is what remains of it |

## Examples

### Estimating Job Cost Before Launch

Check what a run is expected to cost before committing to it. `estimated_cost` is available on a job definition (before assigning it to an audience) and on a running job.

```python
from rapidata import RapidataClient

client = RapidataClient()
audience = client.audience.get_audience_by_id("aud_MU1GZYoESyO")

job_def = client.job.create_compare_job_definition(
    name="Example Image Prompt Alignment",
    instruction="Which image matches the description better?",
    datapoints=[["midjourney.jpg", "flux.jpg"]],
    contexts=["A small blue book sitting on a large red book."],
)

# Reading estimated_cost blocks briefly until the estimate is priced.
# No forecast for the expected response count yet: adaptive compare jobs are estimated at max_responses per pair.
estimate = job_def.estimated_cost
print(
    f"About {estimate.estimated_cost} for {estimate.required_responses} responses "
    f"across {estimate.datapoint_count} datapoints"
)

# The same property is available once the job is running.
job = audience.assign_job(job_def)
print(job.estimated_cost.estimated_cost)
```

### Checking Billing Spend and Remaining Credit

Read how much the current billing period has cost so far and how much credit is
left. Billing is settled per **organization**, so these figures cover everything
the organization spent, not only the jobs this client created.

```python
from rapidata import RapidataClient
from rapidata.rapidata_client.exceptions import RapidataError

client = RapidataClient()

try:
    # Returns the period currently accruing cost. All amounts are in US dollars,
    # rounded to the cent, and are a snapshot — fetch again for an up-to-date figure.
    period = client.billing.get_current_billing_period()
except RapidataError as e:
    # A period only opens once there is something to bill.
    if e.status_code == 404:
        print("No active billing period yet.")
        raise
    raise

# outstanding_cost is gross_cost minus discount — what the period would be
# invoiced for today. status is "Open" while still accruing cost.
print(
    f"[{period.status}] {period.start_date:%Y-%m-%d} → {period.end_date:%Y-%m-%d}: "
    f"${period.outstanding_cost} outstanding "
    f"(${period.gross_cost} gross - ${period.discount} discount) "
    f"over {period.response_count} responses"
)

# credits is the prepaid balance still available (an org-level balance that carries
# across periods), or None when billed for usage rather than from a prepaid balance.
# effective_limit is the most the org may spend this period, or None when uncapped.
if period.credits is not None:
    print(f"${period.credits} credit remaining of ${period.effective_limit} granted")

# The outstanding balance is what the organization currently owes: finalized-but-unpaid
# invoices plus the settled cost of ended periods not yet invoiced. It excludes the
# current, still-accruing period, is already net of vouchers and discounts, and is
# returned in US dollars rounded to the cent (0.0 when nothing is owed).
owed = client.billing.get_outstanding_balance()
print(f"Outstanding balance: ${owed}")
```
