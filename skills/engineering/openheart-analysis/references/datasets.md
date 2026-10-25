# Datasets and evaluation

The regression suite uses local, originally authored fixtures. No external
benchmark is downloaded or executed by this skill.

| Dataset | Purpose | Ground truth and boundary |
| --- | --- | --- |
| `datasets/checkout.py` | Branches, call sites, classes and return paths | `datasets/checkout-model.json` has a deliberately partial manually authored graph |
| `datasets/scenarios.json` | Negative cases and routing checks | Expected behavior, not claimed benchmark accuracy |
| `datasets/observer-java-model.json` with four pinned Observer Java inputs under `references/upstream/source/examples/test_patterns_codebase` | Source-aligned declaration and relationship fixture | Independently authored four-class model, signatures, two realizations and one type-use edge |
| Bundled upstream samples under `references/upstream` | Inspect source output shape and attribution | Historical example outputs, not truth about the fixture or a target repository |

Run `python3 -m unittest discover -s tests -v` from the skill directory.
Tests validate source consistency, reject invalid models, export all categories,
check graph direction/ordering, test escaping and prevent overwriting outputs.
They test the tool and curated models, not an LLM's general extraction accuracy.
Three scenario cases link to executable validation tests. The other seven are
explicit manual host/agent evaluation prompts and have not been behaviorally
qualified. Upstream web example outputs are historical shape references; they
are not the golden outputs for the Java fixture.

## Extracted upstream dataset plan

The pinned upstream test scripts refer to the following evaluation sources.
They are external dependencies, not bundled datasets and not automatically
licensed by OpenHeart's MIT notice.

- Spring PetClinic at https://github.com/spring-projects/spring-petclinic.
  Upstream expects local `target_repos/spring-petclinic/src/main/java` and tests
  CLI artifact presence, selected classes and the server response.
- Java Design Patterns at https://github.com/iluwatar/java-design-patterns.
  Upstream compares selected patterns against `.urm.puml` files. Pin the repo
  revision and record each source/diagram licence before acquiring fixtures.
- PlantUCD, described in upstream
  [test_ruthless_popular_datasets.py](https://github.com/AhmadHassan-BTed/OpenHeart/blob/0bf962fc06e975e9ea7610242b8997b1391fec05/scripts/test_ruthless_popular_datasets.py).
  Resolve its actual dataset URL, version and terms before use. The name alone
  is not a reproducible dataset reference.
- Authored GoF/enterprise Java examples within the pinned OpenHeart tree.
  These are source examples with selected expectations, not an independent
  language-wide oracle.
- `ruthless_verify.py` discovers `target_repos` and uses configurable regex,
  filesystem and package-statement oracles. Regex agreement is not a complete
  semantic accuracy test.

## Reproducible benchmark recipe

1. Obtain permission before network acquisition. Record URL, revision, selected
   files, licences, hashes and task scope in a dataset manifest.
2. Author expected qualified node sets and typed directed edge sets independently
   from the extraction. Include duplicate short names, overloads, misleading
   comments, dynamic dispatch, exception/finally and absent deployment evidence.
3. Run the skill and preserve the model, prompt, agent/model identity, actual
   tool versions, output hashes and full validation receipts.
4. Compare nodes and edges separately. Store TP, FP, FN and the actual differing
   IDs. Compute precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, F1 and phantom
   rate `FP/(TP+FP)`. Use null for undefined metrics, not a perfect score.
5. Review sampled source relationships independently. Mark untested languages,
   cases and host behavior unqualified. Never present the upstream README's
   F1 or compression claims as a result of this skill.
