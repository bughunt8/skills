## What and why

<!-- One paragraph. What changes, and which problem it solves. -->

Closes #

## Traceability

<!-- Delete rows that do not apply. -->

| Link | Reference |
|---|---|
| Requirement | `FR-` / `NFR-` |
| Design section | `TRD.md#` |
| Screen | `SCR-` |
| Decision | `docs/adr/` |

## How it was verified

<!-- Name the failing test you wrote first, and paste the command you ran. Show evidence rather than
     asserting success. -->

```
```

## Checklist

- [ ] A failing test was written first, and it now passes
- [ ] `{{CHECK_COMMAND}}` passes locally
- [ ] `scripts/check-docs` passes, if any spine document changed
- [ ] The traceability matrix in `TRD.md` section 4 is updated
- [ ] An ADR was added for any architecturally significant decision
- [ ] A changeset was added, if this is user-visible
- [ ] No secrets, `.env` or `.dev.vars` files are included
- [ ] Conventional Commits format, scoped with the requirement id where one applies

## Notes for reviewers

<!-- Anything worth knowing: deliberate omissions, follow-up work, risky areas. -->
