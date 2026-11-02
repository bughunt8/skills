# Licence evidence for upstreams that declare but do not ship a licence

Status: proposed

Maintainer acceptance of this policy is pending. The import that motivated it is
in review; this ADR records the mechanism, not approval of the redistribution.

Some upstreams state a licence in `README.md` but ship no standalone licence
file. Blocking every such import keeps useful reference material out; inventing a
licence file is worse. The manifest may therefore record `license_evidence_path`
instead of `license_path`. The importer copies that file verbatim into
`LICENSE.upstream` behind a header saying it is a declaration, not a licence text,
and attribution and notices say "declared; no standalone licence file". The two
fields are mutually exclusive and one is required.

## Considered options

- **Block the import.** Safe but leaves the library without the reference and
  does not help the upstream fix the gap.
- **Write the standard MIT text ourselves.** Rejected: it fabricates a licence
  file and a copyright line the upstream did not publish.
- **Link to upstream without importing.** Rejected for this case: the user asked
  for the references and templates to be integrated, and a link is not an import.

## Consequences

`--validate-manifest` checks required fields and the presence of the generated
metadata files. It does not inspect or authenticate the declaration, and it does
not prove the upstream had the right to license the content. A reviewer still
judges the evidence. If upstream later adds a licence file, switch the source to
`license_path` and regenerate.
