# Mission

## Problem
A local preview operation needs to accept short nonempty messages and reject empty input without exposing message contents in logs.

## Outcomes
An accepted message produces an accepted outcome. Rejected input produces a rejected outcome and no accepted result.

## Scope
One independently testable capability, message preview. Network transport and user interfaces are excluded.

## Assumptions
The caller supplies text and a non-sensitive correlation token. The owner confirms this boundary in evidence/review.txt. No claims about production load are made.
