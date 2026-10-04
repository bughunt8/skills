# Message preview design

## Approach
Implement preview as a plain function returning a decision and one event dictionary. An empty string is rejected; every other string is accepted.

## Contracts
The caller owns the function-input boundary. preview accepts text and correlation_id strings and returns an outcome plus event, outcome, correlation_id fields. Unit tests check the exact shape; no transport contract exists.

## Data
N/A: no persistence or database is used by the demonstration.

## Security
Allowed path accepts a nonempty message. Denied path rejects an empty message. An event allowlist excludes raw text, secrets, and personal identifiers; the correlation token must already be non-sensitive.

## Simplicity
A function is sufficient. No framework, queue, transport, or third-party dependency is justified.

## UI
N/A: the demonstration has no user interface, so browser and keyboard evidence would add nothing.
