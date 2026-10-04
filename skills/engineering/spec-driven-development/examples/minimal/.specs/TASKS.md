# Message preview tasks

## Tasks
| ID | Requirements | Invariants | Observations | Depends | Tests | Files | Verify | Cwd | Exit | Done |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-1 | REQ-1, REQ-2, REQ-3 | INV-1, INV-2 | OBS-1 | - | tests/test_app.py#test_accept, tests/test_app.py#test_reject, tests/test_app.py#test_safe_event, tests/test_app.py#test_confidential_not_logged | app.py, tests/test_app.py | python3 -m unittest discover -s tests -v | . | 0 | Exact outcomes and safe field allowlist verified by assertions and human review. |

## Execution log
| ID | Status | Red | Green | Refactor | Verification |
| --- | --- | --- | --- | --- | --- |
| TASK-1 | planned | - | - | - | - |

## Verification
This is a green example, not fabricated Red-Green-Refactor history. In a real build, record actual red assertion output, green output, and refactor rerun before requesting verification. Stop after TASK-1 and await human review; tests alone cannot authorize rollout.
