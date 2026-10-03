# Message preview observability

## Policy
Runtime events use a strict allowlist with event, outcome, and correlation_id only. Exclude message contents and credentials. Correlation IDs are caller-supplied non-sensitive tokens. The local event is returned, not persisted or transmitted, so retention is the caller's in-memory lifetime. N/A: sampling and alerting because the demonstration has no event backend. Ordinary CLI test output is allowed.

## Observations
| ID | Requirements | Invariants | Event | Fields | Privacy | Test |
| --- | --- | --- | --- | --- | --- | --- |
| OBS-1 | REQ-1, REQ-2, REQ-3 | INV-1, INV-2 | preview_decision | event,outcome,correlation_id | allowlist=event,outcome,correlation_id; exclude=message,password,secret,token | tests/test_app.py#test_safe_event |

## UI applicability
N/A: no UI exists. No analytics SDK or UI telemetry is required.
