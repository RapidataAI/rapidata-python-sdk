# Billing

While [cost estimates](cost_estimates.md) tell you what a job is expected to cost *before* you run it, `client.billing` tells you what you have actually spent so far. Use it to check where the current period stands, or to guard a large run against running out of credit.

## Reading the Current Period

```py
from rapidata import RapidataClient

client = RapidataClient()

period = client.billing.get_current_billing_period()

print(f"{period.start_date:%Y-%m-%d} to {period.end_date:%Y-%m-%d}")
print(f"Outstanding: ${period.outstanding_cost}")
print(f"Credits left: {period.credits}") # (1)!
```

1. `credits` is `None` when your organization is billed for its usage rather than from a prepaid balance. On a prepaid plan, `credits` is what remains of `effective_limit`.

## What the Period Contains

| Field | Description |
|---|---|
| `id` | The billing period's id. |
| `start_date` / `end_date` | When the period starts and ends. |
| `status` | `Open` while the period is still accruing cost; `Invoiced`, `Void`, `Reconciling`, `PendingReview` or `Closed` afterwards. |
| `outstanding_cost` | The net cost accrued so far — what the period would be invoiced for today. |
| `gross_cost` | The cost accrued so far, before discounts. |
| `discount` | The discounts applied to the period so far. |
| `response_count` | The number of billable responses collected in the period. |
| `credits` | The prepaid credit still available, or `None` on a usage-billed plan. |
| `effective_limit` | The most you may spend this period, or `None` when you spend without a cap. |

All amounts are in US dollars, rounded to the cent.

!!! note
    Billing is settled per **organization**, so these figures cover everything your organization spent in the period — not only the jobs this client created. Costs accrue while jobs run, so the values are a snapshot: fetch the period again for an up-to-date figure.

A period only opens once there is something to bill. If your organization has never run a billable job, `get_current_billing_period()` raises a `RapidataError` with status `404` — see [Error Handling](error_handling.md).

## Reading the Outstanding Balance

While the current period tells you what is accruing *now*, `get_outstanding_balance()` tells you what is already **due** — unpaid invoices plus ended periods that have settled but are not yet invoiced.

```py
from rapidata import RapidataClient

client = RapidataClient()

owed = client.billing.get_outstanding_balance()
print(f"Total owed: ${owed}")
```

The figure is in US dollars, rounded to the cent, and is already net of any vouchers and discounts. It does **not** include the current, still-accruing period — nothing is due until a period ends and settles. Like the current period, this is settled per **organization**.

## Automatic Top-Ups

On a prepaid plan, automatic top-ups keep jobs running when the balance runs low: whenever it falls below a threshold, a saved card is charged a fixed amount. Only owners and admins of the organization can read or change these settings.

```py
from rapidata import RapidataClient

client = RapidataClient()

checkout_url = client.billing.configure_auto_top_up(threshold=50, amount=200) # (1)!
if checkout_url is not None:
    print(f"Save a card to start automatic top-ups: {checkout_url}") # (2)!

settings = client.billing.get_auto_top_up()
print(settings.enabled, settings.threshold, settings.amount)
```

1. Amounts are in US dollars. `amount` must be at least 20, greater than `threshold`, and have at most two decimals.
2. With no card saved yet, the settings only take effect once someone opens this hosted checkout page and saves a card. With a card already saved, `configure_auto_top_up()` returns `None` and the settings apply at once.

| Field | Description |
|---|---|
| `enabled` | Whether the saved card is charged automatically when the balance runs low. |
| `threshold` | The balance below which the card is charged, or `None` when never configured. |
| `amount` | What each top-up adds to the balance, or `None` when never configured. |
| `card_brand` / `card_last4` | The saved card, or `None` when no card is saved. |
| `failed_at` | When a declined charge paused automatic top-ups, or `None`. |

A declined charge pauses automatic top-ups: `enabled` turns `False` and `failed_at` is set, while the card stays saved. Call `configure_auto_top_up()` again to resume.

To switch automatic top-ups off and remove the saved card:

```py
client.billing.disable_auto_top_up()
```
