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

balance = client.billing.get_outstanding_balance()

print(f"Total owed: ${balance.total_outstanding} {balance.currency}")
print(f"Unpaid invoices: {balance.unpaid_invoice_count}")
print(f"Accruing now (not yet due): ${balance.current_period_accrued}")
```

| Field | Description |
|---|---|
| `total_outstanding` | The total currently owed — `unpaid_invoices_amount` plus `awaiting_invoice_amount`. Excludes the current period. |
| `unpaid_invoices_amount` | The amount owed on finalized invoices that have not been paid. |
| `unpaid_invoice_count` | How many unpaid invoices make up `unpaid_invoices_amount`. |
| `awaiting_invoice_amount` | The settled cost of ended periods not yet invoiced. |
| `awaiting_invoice_period_count` | How many periods make up `awaiting_invoice_amount`. |
| `current_period_accrued` | Spend accrued in the current, still-open period. Not part of `total_outstanding`. |
| `currency` | The currency the amounts are in, or `None` when nothing is outstanding. |
| `settlement_stale` | `True` when a period behind `awaiting_invoice_amount` is awaiting a settlement recompute, so that figure may still change. |

Amounts are in US dollars, rounded to the cent. Like the current period, this is settled per **organization**.
