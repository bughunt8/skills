# The Skill Library

A static graph workspace for finding agent skills, reading their evidence and
following their connections. Search is at the top. The initial view opens the
largest detected community. There is no scroll animation or pinning.

- Production: <https://skills.ronald.ng>
- Staging: the `staging` branch deploys to Hostinger through GitHub Actions.
  The staging GitHub Environment supplies its `SITE_URL`.

## Use the workspace

Search skill names and complete frontmatter descriptions. A short query such as
`NDA` matches word starts and the phrase `non-disclosure`, not incidental letters
inside `standards`. Explicit community, category and Solution filters combine.
The initial community focus does not constrain global search.

Select a member or result to expand its neighborhood and open its description,
source-file link, licence and connection evidence in the docked inspector.
The result list and query remain available. Hover, focus passage, background
clicks, scrolling, pan and resize never select a different skill. Back restores
the previous context and camera. Clear restores the search's originating view,
or preserves newly chosen dropdown filters; Reset returns to the
largest community with no filters. Escape is the explicit Reset shortcut.

Drag the graph to pan. Use the zoom buttons and Fit view, or focus the graph and
use the arrow keys, +, − and Home. Every member is also a native list button,
so selecting a node never requires hitting a tiny dot. On phones, filters open
from a disclosure in the header; graph and compact details/results stack.

Trace path uses the selected skill as the start, or lets you choose two results.
It computes exact unweighted breadth-first search over the active evidence
graph. Stated-only excludes inferred edges and recomputes an existing path.
Every path edge includes its supplied evidence. A missing path is reported as
missing, never replaced by an approximate route.

The bottom bar reports current context, matching results, nodes actually visible,
nodes in the current graph view, selection, zoom and displayed evidence counts.
Full Solutions and the text library are behind explicit disclosures below the
workspace. They remain real `.sol` and `.card` HTML with JavaScript disabled.

The behavior and stable browser selectors are specified in [UI_NAVIGATION.md](UI_NAVIGATION.md).

## Build and validate

Run from `site/`:

```bash
python3 build.py --write
python3 build.py --check
npm ci
npm run lint:html
npm run lint:secrets
npm test
npm run serve
```

`index.html` and `data.js` are generated. Change `build.py`, then regenerate.
Do not hand-edit either generated region in `index.html`.
`python3 build.py --refresh --write` deliberately updates upstream pins;
ordinary builds never move them.

The builder uses the Python standard library. It reads the host repository
from the working tree and external repositories at the exact `sources.json`
commit pins. Counts are generated, not maintained in prose. Identity uses
category, bundle and name; byte-identical files are deduplicated. Distinct skills
with the same name keep separate identities and visible qualifiers.

| File | Responsibility |
| --- | --- |
| `build.py` | Collect source metadata and prerender the graph shell, skill cards and Solutions |
| `network.py` | Evidence graph, deterministic communities, layout and agreement metrics |
| `compose.py` | Solution membership and evidence |
| `app.js` | Explicit workspace state, search, filtering, BFS and viewport controls |
| `styles.css` | Responsive layout, 16px body/labels, system light/dark themes |
| `data.js` | Generated identity keys, edges, evidence and community metadata |
| `fonts/` | Existing self-hosted Inter and Space Grotesk WOFF2 files |
| `tests/` | Browser and Python behavior/geometry checks |
| `scripts/smoke.mjs` | Post-deploy verification against the actual host |

## Graph evidence and readability

Solid edges are stated in source material: Solution relationships, Solution steps
and packaged siblings. Dashed edges are inferred from shared subjects in names.
Inferred does not mean repository-declared. Communities come from deterministic
Louvain clustering of the evidence graph, not the declared categories.
The stated-only filter changes visible edges and paths, not community assignments.

The data engine and its agreement measures remain unchanged. Purity assigns a
majority category to each detected community; the generated data also reports
purity without isolated singletons and normalized mutual information.

Only geometry belongs inside `#vp`. Labels sit in `#graph-labels`, outside that
transform, in a viewport-sized SVG. Their CSS-pixel scale is independent of camera
zoom. Label placement uses measured local font widths and rejects both label and
visible node-dot collisions. It has no fixed count cap; offset names use leaders.
The selected skill's full name remains anchored to its dot, wrapping at hyphens
or spaces instead of truncating. A clamped callout and status instruction identify
offscreen selections. The root SVG has no runtime viewBox, so header resizing
cannot temporarily scale the label layer.
The member list carries names that do not fit in the graph.

Browser checks must measure `font-size × getScreenCTM()` and actual label bounds,
not only CSS declarations. They also measure graph/inspector non-overlap and
test delayed pointer travel after selecting a search result. Screenshots alone
are not proof of interaction correctness.

## Sources and licences

| Indexed repository | Licence |
| --- | --- |
| [bughunt8/skills](https://github.com/bughunt8/skills) | MIT, with vendored imports retaining upstream licences |
| [haowjy/creative-writing-skills](https://github.com/haowjy/creative-writing-skills) | Apache-2.0 |
| [eternityspring/shuohao-skills](https://github.com/eternityspring/shuohao-skills) | Apache-2.0 |

Source links open the actual `SKILL.md` file. External source links use the
configured commit pin; the locally indexed repository uses its main branch.
No CDN, font service, API or third-party request is needed to use the page.
The application adds no cloud service or backend.

## CI/CD

Validation and deployment remain in GitHub Actions. Staging and production
publish the same static artifact to Hostinger through the existing reusable
workflow. The GitHub Environment supplies the deployment secrets. Route 53
continues to hold DNS; CI does not change it.

| Branch | GitHub Environment | Destination |
| --- | --- | --- |
| `staging` | `staging` | Hostinger staging, from `SITE_URL` |
| `main` | `production` | <https://skills.ronald.ng> |

Promotion remains the manual **Site promote staging to main** workflow with
typed confirmation. See [DEPLOYMENT.md](DEPLOYMENT.md).
There is no GitHub Pages or preview-hosting deployment path.

The page, builder and tests are MIT. Indexed skills retain their own licences
and attribution in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Built by [Ronald Ng](https://ronald.ng).
