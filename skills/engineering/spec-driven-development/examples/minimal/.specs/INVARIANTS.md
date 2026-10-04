# Message preview invariants

## Rules
| ID | Requirements | Rule | Positive | Negative |
| --- | --- | --- | --- | --- |
| INV-1 | REQ-1, REQ-2 | Only a nonempty message receives an accepted outcome. | tests/test_app.py#test_accept | tests/test_app.py#test_reject |
| INV-2 | REQ-3 | Message contents never appear in an observation field. | tests/test_app.py#test_safe_event | tests/test_app.py#test_confidential_not_logged |

## Test strategy
The positive decision test accepts valid input; its violation test attempts empty input. The positive privacy test checks the exact allowlist; its violation test submits a distinctive confidential marker and asserts it remains absent.
