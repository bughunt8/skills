# Skills library

This repository redistributes agent skills and adds authored skills and
solutions. The vocabulary below distinguishes the parts that carry different
provenance and review rules.

## Language

**Vendored source**:
An upstream project listed in `skills/vendor.manifest.json`, imported and
refreshed only by `scripts/sync_vendor.py`.
_Avoid_: imported folder, copied skill

**Reference source**:
A read-only upstream snapshot imported for inspection, not loaded as a skill.
_Avoid_: reference skill, second skill

**Authored skill**:
A skill written in this repository. It may cite a reference source but does not
copy its text.
_Avoid_: local copy, rewritten upstream

**Licence evidence**:
The upstream file that states the licence when no standalone licence file exists.
It is evidence of a declaration, not proof of the right to license the content.
_Avoid_: licence file, licence copy
