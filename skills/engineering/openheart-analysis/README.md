# OpenHeart analysis skill

Read [SKILL.md](SKILL.md) to execute the skill. This directory is a complete
standalone package, including the reference snapshot and its MIT notice.
Copy the whole directory, not only its prompt. Generated provenance links to
the root repository's importer, manifest and workflow are maintenance references;
they do not resolve inside a detached standalone copy or affect runtime.

## What it does

The executing agent reads source and reconstructs an evidence-backed model using
OpenHeart's ten analysis stages. Local Python helpers validate that model and
export the 19 upstream view categories plus an additional AST view. They do not
replace the agent with a general-purpose parser or compiler.

Outputs include normalized JSON, Mermaid, PlantUML, a bidirectional source index,
machine-readable reporting and Markdown report templates. ACT is a provisional
activity alias. Native notation covers class, sequence and state; other views
use labelled graph approximations. The limited XMI contains classifier identity
only. No binary SCPG artifacts, server or UI are provided.

## Run the regression example

From this directory, with Python 3.10 or later:

```bash
python3 scripts/openheart.py validate datasets/checkout-model.json --source-root datasets
python3 scripts/openheart.py export datasets/checkout-model.json --source-root datasets --out /tmp/openheart-example-new
python3 -m unittest discover -s tests -v
```

The destination must not exist. The example is a deliberately partial manually
authored model, not a claim of automatic source extraction. Its unsupported
views report insufficient evidence rather than fake data. Fill the generated
reports before presenting an analysis as complete.

## Maintain

After an intentional contract or fixture change, regenerate and test:

```bash
python3 scripts/contract.py --write
python3 scripts/build_fixture.py
python3 -m unittest discover -s tests -v
```

The [source map](references/source-map.md) explains what came from OpenHeart and
what changed. Reference source is managed by the root repository's importer.
Do not modify `references/upstream` or execute its copied scripts.

Read the repository [integration report](../../../docs/openheart-integration.md)
for acceptance evidence. That report is repository documentation, not a runtime
dependency of this skill.
