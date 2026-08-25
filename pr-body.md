## What

Exposes `GET /billing/outstanding` in the SDK. The generated API client already had `billing_outstanding_get`; this adds the high-level wrapper on `client.billing` that was missing.

## Changes

1. New `OutstandingBalance` dataclass wrapping `GetOutstandingCostEndpointOutput` (money rounded to the cent, mirroring `BillingPeriod`).
2. `RapidataBillingManager.get_outstanding_balance()` — calls the endpoint, returns `OutstandingBalance`.
3. Exported `OutstandingBalance` from `rapidata` and `rapidata.rapidata_client`.
4. Documented in `docs/billing.md`.

## Usage

```py
balance = client.billing.get_outstanding_balance()
print(balance.total_outstanding, balance.currency)
```

`total_outstanding` = unpaid invoices + settled-but-uninvoiced periods. The current, still-accruing period is reported separately in `current_period_accrued` and is not part of the total.

## Checks

- `pyright src/rapidata/rapidata_client` — 0 errors
- `black src/rapidata/rapidata_client` — formatted
- import smoke test — passes

🔗 Session: https://poseidon.rapidata.internal/chat/session-df6cd7ed
