"""Layout invariants, over both orientations and several graph shapes.

The earlier geometry tests ran only the LR architecture example, which is why a
completely broken TB placement branch passed the whole suite while producing seven
overlapping node pairs in a five-node diagram. Every invariant here is therefore
parameterised over orientation, grouping, and graph shape.
"""

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import diagram_ir  # noqa: E402
import diagram_layout  # noqa: E402


def rects_overlap(a, b, tol=1.0):
    ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return ox > tol and oy > tol


def bezier_points(path, steps=40):
    """Sample a single-cubic path. Enough to catch a curve crossing a box."""
    try:
        head, rest = path.split(" C ")
        sx, sy = (float(v) for v in head.replace("M ", "").split())
        nums = [float(v) for v in rest.replace(",", " ").split()]
        c1x, c1y, c2x, c2y, ex, ey = nums[:6]
    except (ValueError, IndexError):
        return []
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append(
            (
                u**3 * sx + 3 * u**2 * t * c1x + 3 * u * t**2 * c2x + t**3 * ex,
                u**3 * sy + 3 * u**2 * t * c1y + 3 * u * t**2 * c2y + t**3 * ey,
            )
        )
    return pts


def point_in(rect, pt, pad=-2.0):
    x, y = pt
    return (
        rect["x"] - pad <= x <= rect["x"] + rect["w"] + pad
        and rect["y"] - pad <= y <= rect["y"] + rect["h"] + pad
    )


def fixtures():
    """(name, doc-builder) pairs covering the shapes that break layouts."""
    def build(nodes, edges=None, groups=None, kind="architecture"):
        def make(orientation, grouped):
            doc = {
                "kind": kind,
                "title": "fixture",
                "orientation": orientation,
                "nodes": [{"id": n, "label": f"Node {n}"} for n in nodes],
            }
            if edges:
                doc["edges"] = [{"from": a, "to": b} for a, b in edges]
            if grouped:
                doc["groups"] = groups or [
                    {"label": "first half", "nodes": nodes[: max(1, len(nodes) // 2)]},
                    {"label": "second half", "nodes": nodes[max(1, len(nodes) // 2):]},
                ]
                doc["groups"] = [g for g in doc["groups"] if g["nodes"]]
            return doc
        return make

    n5 = ["a", "b", "c", "d", "e"]
    return [
        ("disconnected", build(n5)),
        ("chain", build(n5, list(zip(n5, n5[1:])))),
        ("fan out", build(n5, [("a", x) for x in n5[1:]])),
        ("fan in", build(n5, [(x, "a") for x in n5[1:]])),
        ("two components", build(n5, [("a", "b"), ("c", "d")])),
        ("cycle", build(n5, list(zip(n5, n5[1:])) + [("e", "a")], kind="lifecycle")),
        ("dense", build(n5[:4], [(x, y) for x in n5[:4] for y in n5[:4] if x != y])),
        ("single node", build(["a"])),
    ]


class TestNodePlacement(unittest.TestCase):
    def test_nodes_never_overlap(self):
        for name, make in fixtures():
            for orientation in ("LR", "TB"):
                for grouped in (False, True):
                    with self.subTest(fixture=name, orientation=orientation, grouped=grouped):
                        doc = make(orientation, grouped)
                        geo = diagram_layout.layout(diagram_ir.validate(doc))
                        nodes = geo["nodes"]
                        bad = [
                            (nodes[i]["id"], nodes[j]["id"])
                            for i in range(len(nodes))
                            for j in range(i + 1, len(nodes))
                            if rects_overlap(nodes[i], nodes[j])
                        ]
                        self.assertEqual(bad, [], f"overlapping nodes: {bad}")

    def test_everything_is_inside_the_declared_canvas(self):
        for name, make in fixtures():
            for orientation in ("LR", "TB"):
                for grouped in (False, True):
                    with self.subTest(fixture=name, orientation=orientation, grouped=grouped):
                        geo = diagram_layout.layout(
                            diagram_ir.validate(make(orientation, grouped))
                        )
                        x0, y0 = geo["min_x"], geo["min_y"]
                        x1, y1 = x0 + geo["width"], y0 + geo["height"]
                        for item in geo["nodes"] + geo["groups"]:
                            self.assertGreaterEqual(round(item["x"], 2), round(x0, 2))
                            self.assertGreaterEqual(round(item["y"], 2), round(y0, 2))
                            self.assertLessEqual(round(item["x"] + item["w"], 2), round(x1, 2))
                            self.assertLessEqual(round(item["y"] + item["h"], 2), round(y1, 2))


class TestGroups(unittest.TestCase):
    def test_group_boxes_never_overlap(self):
        for name, make in fixtures():
            for orientation in ("LR", "TB"):
                with self.subTest(fixture=name, orientation=orientation):
                    geo = diagram_layout.layout(diagram_ir.validate(make(orientation, True)))
                    boxes = geo["groups"]
                    bad = [
                        (boxes[i]["label"], boxes[j]["label"])
                        for i in range(len(boxes))
                        for j in range(i + 1, len(boxes))
                        if rects_overlap(boxes[i], boxes[j])
                    ]
                    self.assertEqual(bad, [], f"overlapping boundaries: {bad}")

    def test_members_are_inside_their_boundary(self):
        for name, make in fixtures():
            for orientation in ("LR", "TB"):
                with self.subTest(fixture=name, orientation=orientation):
                    doc = make(orientation, True)
                    geo = diagram_layout.layout(diagram_ir.validate(doc))
                    by_id = {n["id"]: n for n in geo["nodes"]}
                    for gi, group in enumerate(doc.get("groups", [])):
                        box = geo["groups"][gi]
                        for member in group["nodes"]:
                            node = by_id[member]
                            self.assertTrue(
                                node["x"] >= box["x"]
                                and node["y"] >= box["y"]
                                and node["x"] + node["w"] <= box["x"] + box["w"]
                                and node["y"] + node["h"] <= box["y"] + box["h"],
                                f"{member} escapes boundary {group['label']!r}",
                            )

    def test_a_node_outside_a_group_is_not_swallowed_by_it(self):
        doc = {
            "kind": "architecture",
            "title": "t",
            "nodes": [{"id": x, "label": x.upper()} for x in ("a", "b", "c")],
            "groups": [{"label": "only a", "nodes": ["a"]}],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        box = geo["groups"][0]
        for node in geo["nodes"]:
            if node["id"] != "a":
                self.assertFalse(
                    rects_overlap(box, node),
                    f"{node['id']} sits inside a boundary it is not a member of",
                )


class TestEdgeRouting(unittest.TestCase):
    def test_adjacent_rank_edges_do_not_cross_other_nodes(self):
        """The guarantee the layered layout can actually make.

        An edge between neighbouring ranks has nothing between its endpoints, so
        it must be clear. Longer edges and back edges are NOT guaranteed clear;
        that limitation is documented in SKILL.md rather than asserted here.
        """
        for name, make in fixtures():
            for orientation in ("LR", "TB"):
                with self.subTest(fixture=name, orientation=orientation):
                    geo = diagram_layout.layout(diagram_ir.validate(make(orientation, False)))
                    ranks = {n["id"]: n["rank"] for n in geo["nodes"]}
                    by_id = {n["id"]: n for n in geo["nodes"]}
                    for edge in geo["edges"]:
                        if edge["back"]:
                            continue
                        if abs(ranks[edge["to"]] - ranks[edge["from"]]) != 1:
                            continue
                        pts = bezier_points(edge["path"])
                        for node in geo["nodes"]:
                            if node["id"] in (edge["from"], edge["to"]):
                                continue
                            hits = [p for p in pts if point_in(node, p)]
                            self.assertEqual(
                                hits,
                                [],
                                f"{edge['from']}->{edge['to']} crosses {node['id']}",
                            )

    def test_back_edge_labels_clear_the_node_area(self):
        doc = {
            "kind": "lifecycle",
            "title": "t",
            "nodes": [{"id": x, "label": x} for x in ("a", "b", "c")],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"},
                      {"from": "c", "to": "a", "label": "back"}],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        back = [e for e in geo["edges"] if e["back"]]
        self.assertTrue(back, "no back edge identified in a cyclic graph")
        top = min(n["y"] for n in geo["nodes"])
        for edge in back:
            self.assertLess(edge["ly"], top)
            self.assertEqual(edge["style"], "dashed")

    def test_parallel_edges_are_separated(self):
        doc = {
            "kind": "architecture",
            "title": "t",
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [
                {"from": "a", "to": "b", "label": "read"},
                {"from": "a", "to": "b", "label": "write"},
                {"from": "a", "to": "b", "label": "purge"},
            ],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        self.assertEqual(len({e["path"] for e in geo["edges"]}), 3, "paths coincide")
        self.assertEqual(
            len({(e["lx"], e["ly"]) for e in geo["edges"]}), 3, "labels coincide"
        )

    def test_self_loop_is_a_visible_loop(self):
        doc = {
            "kind": "lifecycle",
            "title": "t",
            "nodes": [{"id": "a", "label": "Retrying"}],
            "edges": [{"from": "a", "to": "a", "label": "retry"}],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        edge = geo["edges"][0]
        pts = bezier_points(edge["path"])
        self.assertTrue(pts, "self-loop produced no drawable path")
        span = max(p[1] for p in pts) - min(p[1] for p in pts)
        self.assertGreater(span, 20, "the self-loop is degenerate, not a loop")
        self.assertLess(edge["ly"], geo["nodes"][0]["y"], "label sits on the node")


class TestTextFitting(unittest.TestCase):
    """Wrapping must keep text inside the box it belongs to.

    Refusing to split an over-long token meant a 1,000-character label measured
    over 9,000px inside a 208px node, and any CJK string (no spaces to wrap at)
    overflowed the same way.
    """

    CASES = {
        "long words": "supercalifragilistic " * 6,
        "one huge token": "A" * 400,
        "long identifier": "com.example.internal.service.LeadCaptureRequestHandlerFactoryImpl",
        "url": "https://example.com/a/very/long/path/that/keeps/going/and/going?x=1&y=2",
        "cjk": "系统架构图与数据流向说明文件" * 8,
        "japanese": "システムアーキテクチャ" * 8,
        "mixed": "API网关 gateway 请求处理 handler " * 4,
        "emoji": "deploy 🚀 pipeline 🔁 rollback ⛔ " * 3,
        "arabic": "مخطط معمارية النظام وتدفق البيانات " * 3,
    }

    def test_wrapped_lines_fit_the_budget(self):
        budget = diagram_layout.NODE_W - 2 * diagram_layout.NODE_PAD_X
        for name, text in self.CASES.items():
            with self.subTest(case=name):
                for line in diagram_layout.wrap(text, budget):
                    self.assertLessEqual(
                        diagram_layout.text_width(line),
                        budget + 1,
                        f"{name}: a wrapped line is wider than the node",
                    )

    def test_no_text_is_lost_when_wrapping(self):
        for name, text in self.CASES.items():
            with self.subTest(case=name):
                joined = "".join(diagram_layout.wrap(text, 160))
                self.assertEqual(
                    joined.replace(" ", ""),
                    text.replace(" ", ""),
                    f"{name}: wrapping dropped or duplicated characters",
                )

    def test_node_height_grows_to_hold_wrapped_text(self):
        doc = {
            "kind": "architecture",
            "title": "t",
            "nodes": [
                {"id": "a", "label": "A" * 300, "note": "系统架构图" * 20},
                {"id": "b", "label": "B"},
            ],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        big = next(n for n in geo["nodes"] if n["id"] == "a")
        small = next(n for n in geo["nodes"] if n["id"] == "b")
        self.assertGreater(big["h"], small["h"], "the box did not grow for its text")
        needed = 22 + len(big["label_lines"]) * diagram_layout.LINE_H
        self.assertGreaterEqual(big["h"], needed)


class TestScale(unittest.TestCase):
    def test_five_hundred_nodes_lays_out_quickly(self):
        ids = [f"n{i}" for i in range(500)]
        doc = {
            "kind": "workflow",
            "title": "big",
            "nodes": [{"id": i, "label": i} for i in ids],
            "edges": [{"from": a, "to": b} for a, b in zip(ids, ids[1:])],
        }
        started = time.monotonic()
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 15.0, f"layout took {elapsed:.1f}s")
        self.assertEqual(len(geo["nodes"]), 500)

    def test_deep_chain_does_not_exhaust_the_stack(self):
        """Cycle detection uses an explicit stack for exactly this case."""
        ids = [f"n{i}" for i in range(2000)]
        doc = {
            "kind": "workflow",
            "title": "deep",
            "nodes": [{"id": i, "label": i} for i in ids],
            "edges": [{"from": a, "to": b} for a, b in zip(ids, ids[1:])]
            + [{"from": ids[-1], "to": ids[0], "label": "loop"}],
        }
        geo = diagram_layout.layout(diagram_ir.validate(doc))
        self.assertEqual(sum(1 for e in geo["edges"] if e["back"]), 1)


if __name__ == "__main__":
    unittest.main()
