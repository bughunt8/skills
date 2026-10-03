# Technical stack

## Stack
This is a non-deployed demonstration tested on Python 3.12.13 with standard-library unittest. The skill checker supports Python 3.10 or later, which is an install compatibility range, not a production runtime pin. No deployment runtime or external dependencies exist, so no dependency lockfile exists. A production adopter must pin an exact deployed Python release, capture integrity in a committed lockfile or equivalent build manifest, and review every update.

## Project tree
app.py contains preview. tests/test_app.py contains behavior, violation, and telemetry tests. evidence/review.txt records fixture context, not authorization.

## Commands
Cwd is the examples/minimal directory. Command is python3 --version, expected exit 0; record the actual version and compare to the project's reviewed pin before running. Command is python3 -m unittest discover -s tests -v, expected exit 0 for supplied green demonstration. For real TDD, first add a new assertion and record an actual exit 1 caused by that assertion. Do not call an import failure a red behavior test.

## Style
Use explicit names, plain functions, and standard-library types. Avoid new abstraction layers for this operation.

## Test strategy
Unit tests exercise accepted and denied input plus exact event field allowlist. N/A: integration and browser tests because this demonstration has no external boundary or UI.
