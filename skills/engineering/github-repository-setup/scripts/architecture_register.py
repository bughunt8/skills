"""Offline draft generator and structural readiness checks, not approval automation."""
import argparse
import pathlib
import sys

import yaml

CATALOG = pathlib.Path(__file__).resolve().parents[1] / "templates/architecture-catalog.yml"


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently replacing decisions."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, (str, int, float, bool)) or key in result:
            raise ValueError(f"Invalid or duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def load(path):
    return yaml.load(pathlib.Path(path).read_text(), Loader=UniqueLoader)


def catalog():
    return {
        key: topic
        for group in load(CATALOG)["groups"]
        for key, topic in group["topics"].items()
    }


def initial():
    related = load(CATALOG)["related"]
    records = []
    for key, topic in catalog().items():
        record = dict.fromkeys((
            "rationale", "owner", "workload_constraints", "selected_approach",
            "document", "approval", "epic", "feature", "story", "impact", "revisit"
        ), "")
        record.update(
            id=key, topic=topic, applicability="pending",
            decision_state="unresolved", implementation_state="not_started",
            requirements=[], alternatives=[], tests=[], evidence=[],
            related_to=[other for pair in related if key in pair
                        for other in pair if other != key],
        )
        records.append(record)
    return {"schema_version": 1, "records": records}


def validate(data, stage="draft", ids=()):
    errors = []
    if stage not in ("draft", "plan", "story", "release"):
        return ["Unknown stage"]
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["Expected schema_version: 1 and records"]
    rows = data.get("records")
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return ["records must be a list of mappings"]
    baseline = catalog()
    keyed = {}
    for row in rows:
        key = row.get("id")
        if not isinstance(key, str) or not key:
            errors.append("Every record requires a string id")
            continue
        if key in keyed:
            errors.append(f"{key}: duplicate id")
        keyed[key] = row
        if key not in baseline and not key.startswith("CUSTOM-"):
            errors.append(f"{key}: unknown ID; use CUSTOM- for extensions")
        if key in baseline and row.get("topic") != baseline[key]:
            errors.append(f"{key}: catalog topic mismatch")
    for key in baseline.keys() - keyed.keys():
        errors.append(f"{key}: missing catalog topic")
    selected = set(ids)
    if stage in ("story", "release") and not selected:
        errors.append("Story/release checks require a reviewed nonempty --ids impact set")
    for key in selected - keyed.keys():
        errors.append(f"{key}: unknown impact ID")

    text_fields = (
        "topic", "rationale", "owner", "workload_constraints", "selected_approach",
        "document", "approval", "epic", "feature", "story", "impact", "revisit"
    )
    for key, row in keyed.items():
        def need(*fields):
            for field in fields:
                value = row.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{key}: requires {field}")

        for field in text_fields:
            if not isinstance(row.get(field), str):
                errors.append(f"{key}: {field} must be a string")
        for field in ("requirements", "alternatives", "tests", "related_to"):
            value = row.get(field)
            if not isinstance(value, list) or not all(
                isinstance(v, str) and v.strip() for v in value
            ):
                errors.append(f"{key}: {field} must be a list of nonempty strings")
        relations = row.get("related_to", [])
        if isinstance(relations, list):
            for other in relations:
                if not isinstance(other, str) or other not in keyed or other == key:
                    errors.append(f"{key}: invalid related_to reference")
        app = row.get("applicability")
        decision = row.get("decision_state")
        impl = row.get("implementation_state")
        if app not in ("pending", "applicable", "not_applicable"):
            errors.append(f"{key}: invalid applicability")
        if decision not in ("unresolved", "accepted", "deferred", "rejected", "superseded"):
            errors.append(f"{key}: invalid decision_state")
        if impl not in ("not_started", "in_progress", "implemented", "verified", "not_applicable"):
            errors.append(f"{key}: invalid implementation_state")
        if app != "pending":
            need("rationale", "owner")
        if app == "not_applicable" and impl != "not_applicable":
            errors.append(f"{key}: excluded topic must have not_applicable implementation")
        if impl == "not_applicable" and app != "not_applicable":
            errors.append(f"{key}: implementation exclusion requires applicability exclusion")
        if decision == "accepted":
            need("selected_approach", "document", "approval")
            if app == "pending":
                errors.append(f"{key}: cannot accept pending applicability")
        if decision == "deferred":
            need("impact", "revisit", "owner", "rationale")
        if decision in ("rejected", "superseded"):
            need("document", "rationale", "owner")
        evidence = row.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{key}: evidence must be a list")
            evidence = []
        for item in evidence:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(f), str) and item[f].strip()
                for f in ("reference", "revision", "environment", "result")
            ):
                errors.append(f"{key}: evidence requires reference/revision/environment/result")
            elif item["result"] not in ("passed", "failed", "blocked"):
                errors.append(f"{key}: invalid evidence result")
        if impl == "verified":
            if app != "applicable" or decision != "accepted" or not row.get("tests"):
                errors.append(f"{key}: verification requires applicable accepted decision and tests")
            if not evidence or any(not isinstance(e, dict) or e.get("result") != "passed"
                                   for e in evidence):
                errors.append(f"{key}: verification requires passing evidence")
        if stage == "plan":
            if app == "pending":
                errors.append(f"{key}: plan requires applicability disposition")
            if app == "applicable" and decision in ("unresolved", "deferred"):
                need("impact", "revisit")
        if stage in ("story", "release") and key in selected:
            if app == "not_applicable":
                need("approval")
            elif app != "applicable" or decision != "accepted":
                errors.append(f"{key}: affected implementation decision is not accepted")
            else:
                need("epic", "feature", "story", "workload_constraints")
                for field in ("requirements", "tests"):
                    if not row.get(field):
                        errors.append(f"{key}: readiness requires {field}")
                if stage == "release" and impl != "verified":
                    errors.append(f"{key}: release requires verified implementation")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "check"))
    parser.add_argument("path", type=pathlib.Path)
    parser.add_argument("--stage", choices=("draft", "plan", "story", "release"), default="draft")
    parser.add_argument("--ids", nargs="*", default=[])
    args = parser.parse_args()
    try:
        if args.command == "init":
            with args.path.open("x") as output:
                yaml.safe_dump(initial(), output, sort_keys=False)
            print("Created unresolved draft; no approvals or runtime capabilities asserted.")
            return 0
        errors = validate(load(args.path), args.stage, args.ids)
        for error in errors:
            print(error, file=sys.stderr)
        if not errors:
            print(f"{args.stage} structural check passed; human evidence/impact review still required.")
        return int(bool(errors))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
