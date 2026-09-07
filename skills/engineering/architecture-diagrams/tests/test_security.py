"""Escaping and injection tests.

These exist because the original `test_escaping` checked one script tag in one
node label, and a valid document was nonetheless able to install a working
`onfocus` handler in the generated file. The cause was composition, not a missing
`escape()` call: `render_html` applied one global `str.replace()` per template
token, so text inserted by an earlier token was rescanned by later ones. A node id
of `__A11Y_DESC__` survived attribute escaping, was matched by the later
replacement, and received a text-escaped description whose quotes broke out of
the attribute.

So the payloads below are applied to **every** user-controlled field, and the
output is parsed as HTML rather than string-matched. A file intended to be sent to
a client must not be able to carry the author's JavaScript, let alone a third
party's.
"""

import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import diagram_ir  # noqa: E402
import diagram_layout  # noqa: E402
import render_diagram  # noqa: E402

# Attribute breakout, element injection, template-token collision, and the
# specific string that produced the original working exploit.
PAYLOADS = [
    '" onfocus="globalThis.PWN=1" x="',
    "' onfocus='globalThis.PWN=1' x='",
    "<script>globalThis.PWN=1</script>",
    "<img src=x onerror=globalThis.PWN=1>",
    "</title><script>globalThis.PWN=1</script>",
    "</desc></svg><script>globalThis.PWN=1</script>",
    "__A11Y_DESC__",
    "__TITLE__",
    "__BODY__",
    "__CSS__",
    '__A11Y_DESC__" onfocus="globalThis.PWN=1',
    "javascript:alert(1)",
    "&quot;&gt;<svg onload=globalThis.PWN=1>",
    "\\\" onfocus=\\\"globalThis.PWN=1",
]


class Collector(HTMLParser):
    """Records every attribute and every script body in the parsed document."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.attrs = []
        self.tags = []
        self.in_script = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for name, value in attrs:
            self.attrs.append((tag, name.lower(), value or ""))
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)


def parse(html):
    c = Collector()
    c.feed(html)
    return c


def graph_doc(payload):
    return {
        "kind": "architecture",
        "title": payload,
        "subtitle": payload,
        "footer": payload,
        "legend": [payload],
        "groups": [{"label": payload, "nodes": [payload]}],
        "nodes": [
            {"id": payload, "label": payload, "note": payload, "tech": payload},
            {"id": payload + "2", "label": payload},
        ],
        "edges": [{"from": payload, "to": payload + "2", "label": payload}],
    }


def sequence_doc(payload):
    return {
        "kind": "sequence",
        "title": payload,
        "subtitle": payload,
        "footer": payload,
        "participants": [
            {"id": payload, "label": payload, "note": payload},
            {"id": payload + "2", "label": payload},
        ],
        "messages": [
            {"from": payload, "to": payload + "2", "label": payload, "note": payload}
        ],
    }


class TestNoInjection(unittest.TestCase):
    def _check(self, html, payload, what):
        doc = parse(html)

        # 1. No event-handler attribute may exist anywhere.
        handlers = [a for a in doc.attrs if a[1].startswith("on")]
        self.assertEqual(
            handlers, [], f"{what}: payload {payload!r} produced handlers {handlers}"
        )

        # 2. Exactly one script element, the viewer's own.
        self.assertEqual(
            doc.tags.count("script"),
            1,
            f"{what}: payload {payload!r} changed the script count",
        )

        # 3. The payload must not appear as executable code in that script.
        for body in doc.scripts:
            self.assertNotIn(
                "globalThis.PWN",
                body,
                f"{what}: payload {payload!r} reached the script body",
            )

        # 4. No URL-bearing attribute may carry a javascript: URL. Scoped to
        # attributes a browser actually dereferences: a meta description whose
        # text happens to read "javascript:..." is inert, and flagging it would
        # be the test crying wolf rather than finding a defect.
        url_attrs = {"href", "src", "action", "formaction", "xlink:href", "data", "poster"}
        for tag, name, value in doc.attrs:
            if name in url_attrs:
                self.assertFalse(
                    value.strip().lower().replace("\t", "").startswith("javascript:"),
                    f"{what}: {tag}[{name}] holds a javascript: URL",
                )

        # 5. The numeric values injected into the script must be plain numbers.
        for body in doc.scripts:
            if "var box = {" in body:
                fragment = body.split("var box = {", 1)[1].split("}", 1)[0]
                for part in fragment.split(","):
                    _, _, val = part.partition(":")
                    if val.strip():
                        float(val.strip())  # raises if it is not a number

    def test_graph_fields(self):
        for payload in PAYLOADS:
            with self.subTest(payload=payload):
                doc = graph_doc(payload)
                diagram_ir.validate(doc)
                html = render_diagram.render_html(doc, diagram_layout.layout(doc))
                self._check(html, payload, "graph")

    def test_sequence_fields(self):
        for payload in PAYLOADS:
            with self.subTest(payload=payload):
                doc = sequence_doc(payload)
                diagram_ir.validate(doc)
                html = render_diagram.render_html(doc, diagram_layout.layout(doc))
                self._check(html, payload, "sequence")

    def test_bare_svg_output_is_also_escaped(self):
        for payload in PAYLOADS:
            with self.subTest(payload=payload):
                doc = graph_doc(payload)
                svg = render_diagram.render_svg(doc, diagram_layout.layout(doc))
                parsed = parse(svg)
                handlers = [a for a in parsed.attrs if a[1].startswith("on")]
                self.assertEqual(handlers, [], f"svg: {payload!r} -> {handlers}")
                self.assertEqual(parsed.tags.count("script"), 0, "svg gained a script")

    def test_placeholder_in_user_data_is_emitted_literally(self):
        """The exact original exploit: an id equal to a later template token."""
        doc = {
            "kind": "architecture",
            "title": 'x" onfocus="globalThis.PWN=1" data-z="',
            "nodes": [{"id": "__A11Y_DESC__", "label": "Focus me"}],
            "edges": [],
        }
        html = render_diagram.render_html(doc, diagram_layout.layout(doc))
        parsed = parse(html)
        self.assertEqual(
            [a for a in parsed.attrs if a[1].startswith("on")],
            [],
            "the template-token collision exploit has regressed",
        )
        # The id is data, so it must survive verbatim rather than being expanded.
        ids = [v for _, n, v in parsed.attrs if n == "data-id"]
        self.assertIn("__A11Y_DESC__", ids)

    def test_substitution_is_single_pass(self):
        """Guard the mechanism, not just its current outcome."""
        filled = render_diagram.fill(
            "<p>__A__</p><p>__B__</p>", {"__A__": "__B__", "__B__": "safe"}
        )
        self.assertEqual(
            filled,
            "<p>__B__</p><p>safe</p>",
            "a substituted value was rescanned for placeholders",
        )

    def test_attribute_escaper_escapes_quotes(self):
        self.assertNotIn('"', render_diagram.attr('a " b'))
        self.assertNotIn("'", render_diagram.attr("a ' b"))
        self.assertIn("&amp;", render_diagram.attr("a & b"))


if __name__ == "__main__":
    unittest.main()
