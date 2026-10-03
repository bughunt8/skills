# Observability

Status: Draft

## Policy
FILL_ME: Define runtime structured events, field allowlists, redaction, correlation, retention, access control, sampling, and alerts. This does not prohibit ordinary CLI stdout.

## Observations
| ID | Requirements | Invariants | Event | Fields | Privacy | Test |
| --- | --- | --- | --- | --- | --- | --- |
| OBS-1 | REQ-1 | INV-1 | FILL_ME | event,outcome,correlation_id | allowlist=event,outcome,correlation_id; exclude=message,password,secret,token | tests/test_feature.py#test_safe_event |

## UI applicability
FILL_ME: Describe needed UI observations, or N/A with reason. Do not add analytics just because a UI exists.
