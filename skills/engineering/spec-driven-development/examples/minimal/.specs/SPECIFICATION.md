# Message preview specification

## Context
A caller submits a message for local preview and receives a decision. The input message must remain absent from observation records.

## Requirements
| ID | Type | Statement |
| --- | --- | --- |
| REQ-1 | event | When a caller submits a nonempty message, the preview service shall return an accepted outcome. |
| REQ-2 | unwanted | If a caller submits an empty message, then the preview service shall return a rejected outcome. |
| REQ-3 | ubiquitous | The preview service shall exclude message contents from observation records. |

## Acceptance criteria
### AC-1: Accept a message (REQ-1)
Given a nonempty message
When the caller requests preview
Then the outcome is accepted

### AC-2: Reject an empty message (REQ-2)
Given an empty message
When the caller requests preview
Then the outcome is rejected

### AC-3: Keep message contents private (REQ-3)
Given a message containing confidential text
When the caller requests preview
Then no observation field contains that text

## Exclusions
Transport, persistence, UI, and production rollout are outside this capability.

## Open questions
None: demonstration boundary assumptions are recorded in evidence/review.txt. A real project owner must validate them before authorizing implementation.
