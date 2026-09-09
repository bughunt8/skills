#!/usr/bin/env python3
"""Local interaction/geometry audit. Uses the installed Python Playwright browser."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / ".cache" / "ui-implementation-audit"
OUT.mkdir(parents=True, exist_ok=True)
URL = os.environ.get("WORKSPACE_URL", "http://127.0.0.1:8123/")
MEASURE = """() => {
  const rect = el => {const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom};};
  const labels=[...document.querySelectorAll('#graph-labels text')].filter(e=>getComputedStyle(e).display!=='none').map(e=>{
    const m=e.getScreenCTM(),style=getComputedStyle(e);
    return {text:e.textContent,key:e.dataset.key||e.dataset.comm,font:parseFloat(style.fontSize)*Math.hypot(m.a,m.b),rect:rect(e)};
  });
  const graph=rect(document.getElementById('gsvg'));
  const nodes=[...document.querySelectorAll('.g-node[data-in-context="true"] .g-dot')].map(rect);
  const largest=[...document.querySelectorAll('.g-node[data-in-context="true"]')].filter(e=>e.dataset.comm===String(SKILLDATA.comms[0].id)).map(e=>rect(e.querySelector('.g-dot')));
  const bounds=rs=>rs.length?{width:Math.max(...rs.map(r=>r.right))-Math.min(...rs.map(r=>r.x)),height:Math.max(...rs.map(r=>r.bottom))-Math.min(...rs.map(r=>r.y))}:null;
  const visible=nodes.filter(r=>r.x+r.w/2>=graph.x&&r.x+r.w/2<=graph.right&&r.y+r.h/2>=graph.y&&r.y+r.h/2<=graph.bottom);
  return {state:{...document.getElementById('top').dataset},camera:{...document.getElementById('vp').dataset},
    title:document.getElementById('workspace-title').textContent,
    results:[...document.querySelectorAll('#gresults button')].map(e=>({key:e.dataset.key,h:rect(e).h})),
    regions:Object.fromEntries(['workspace-header','graph-region','gsvg','inspector','panel','statusbar'].map(id=>[id,rect(document.getElementById(id))])),
    labels,dots:nodes,visible:visible.length,expandedBounds:bounds(nodes),largestCommunityBounds:bounds(largest),
    overflow:document.documentElement.scrollWidth-innerWidth,
    scripts:[...document.scripts].map(e=>e.src),status:document.getElementById('statusbar').innerText};
}"""


def context(page):
    return page.evaluate("""() => {
      const r=document.getElementById('top');
      return {mode:r.dataset.mode,query:r.dataset.query,selected:r.dataset.selectedKey,
        title:document.getElementById('workspace-title').textContent,
        panel:document.getElementById('panelname').textContent,
        results:[...document.querySelectorAll('#gresults button')].map(e=>e.dataset.key)};
    }""")


def run():
    report = {"url": URL, "viewports": [], "errors": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width, height in [(1440, 900), (1280, 800), (1024, 768), (390, 844), (375, 812)]:
            ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme="dark",
                                      has_touch=width < 768)
            page = ctx.new_page()
            page.on("pageerror", lambda error: report["errors"].append(str(error)))
            page.goto(URL)
            page.locator('#top[data-ready="true"]').wait_for()
            page.evaluate("document.fonts.ready")
            entry = {"viewport": [width, height], "default": page.evaluate(MEASURE)}
            page.screenshot(path=str(OUT / f"default-{width}.png"))
            page.locator("#goverview").click()
            entry["overview"] = page.evaluate(MEASURE)
            page.locator("#greset").click()
            page.locator("#gsearch").fill("NDA")
            page.wait_for_timeout(1200)
            entry["search"] = page.evaluate(MEASURE)
            if page.locator("#gresults button").count():
                page.locator("#gresults button").first.click()
                entry["selected"] = page.evaluate(MEASURE)
                before = context(page)
                graph = page.locator("#gsvg").bounding_box()
                for i in range(1, 10):
                    page.mouse.move(graph["x"] + graph["width"] * i / 10,
                                    graph["y"] + graph["height"] * (.25 if i % 2 else .7), steps=5)
                page.wait_for_timeout(1100)
                entry["pointer_stable"] = context(page) == before
                page.locator("#gsearch").focus()
                page.keyboard.press("Tab")
                entry["focus_stable"] = context(page) == before
                page.mouse.move(graph["x"] + graph["width"] / 2, graph["y"] + graph["height"] / 2)
                page.mouse.down()
                page.mouse.move(graph["x"] + graph["width"] / 2 + 60, graph["y"] + graph["height"] / 2 + 35, steps=8)
                page.mouse.up()
                entry["drag_stable"] = context(page) == before
                entry["after_drag"] = page.evaluate(MEASURE)
                page.locator("#gzoom-in").click()
                page.locator("#gzoom-out").click()
                entry["zoom_stable"] = context(page) == before
                page.set_viewport_size({"width": width + 20, "height": height})
                page.wait_for_timeout(100)
                entry["resize_stable"] = context(page) == before
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(100)
                page.mouse.move(graph["x"] + graph["width"] / 2, graph["y"] + graph["height"] / 2)
                page.mouse.wheel(0, 200)
                page.wait_for_timeout(100)
                page.mouse.wheel(0, -200)
                page.wait_for_timeout(100)
                entry["scroll_stable"] = context(page) == before
                page.locator("#gfit").click()
                page.screenshot(path=str(OUT / f"nda-selected-{width}.png"))
                entry["source"] = page.locator("#panelsource").get_attribute("href")
                for control in ["gzoom-in", "gzoom-out"]:
                    for _ in range(35):
                        button = page.locator("#" + control)
                        if button.is_disabled():
                            break
                        button.click()
                    entry[control] = page.evaluate(MEASURE)
                page.locator("#gfit").click()
                page.locator("#gsvg").focus()
                for _ in range(30):
                    page.keyboard.press("ArrowRight")
                entry["offscreen"] = page.evaluate(MEASURE)
                entry["offscreen_stable"] = context(page) == before
                page.locator("#gfit").click()
            page.locator("#gclear").click()
            page.locator("#gsearch").fill("zzzz-no-skill-98765")
            entry["empty"] = page.evaluate(MEASURE)
            page.locator("#gclear").click()
            if width < 768:
                page.locator("#gfilters summary").click()
            options = page.locator("#gcommunity option").evaluate_all("(els)=>els.map(e=>({value:e.value,text:e.textContent}))")
            isolated = next(x for x in options if x["text"].endswith("(1)"))
            page.locator("#gcommunity").select_option(isolated["value"])
            if width < 768:
                page.locator("#gfilters summary").click()
            page.locator("#gfit").click()
            entry["isolated"] = page.evaluate(MEASURE)
            page.screenshot(path=str(OUT / f"isolated-{width}.png"))
            page.locator("#greset").click()
            page.locator("#gresults button").first.click()
            page.locator("#gpath").click()
            if page.locator("#gresults button").count() > 1:
                page.locator("#gresults button").nth(1).click()
                entry["path"] = page.evaluate(MEASURE)
            report["viewports"].append(entry)
            ctx.close()
        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        page = nojs.new_page()
        page.goto(URL)
        page.locator("#library > summary").click()
        page.locator(".lib__cat > summary").first.click()
        report["nojs"] = {"cards": page.locator(".card").count(), "solutions": page.locator(".sol").count(),
                          "visible_card": page.locator(".card").first.is_visible()}
        nojs.close()
        browser.close()
    findings = []
    for entry in report["viewports"]:
        viewport = entry["viewport"]
        for name, value in entry.items():
            if not isinstance(value, dict) or "labels" not in value:
                continue
            graph = value["regions"]["gsvg"]
            if value["overflow"] > 0:
                findings.append(f"{viewport}/{name}: horizontal overflow")
            if value["visible"] != int(value["state"]["visibleCount"]):
                findings.append(f"{viewport}/{name}: visible count does not match geometry")
            for label in value["labels"]:
                box = label["rect"]
                if label["font"] < 16 - .01:
                    findings.append(f"{viewport}/{name}: label below 16 CSS pixels")
                if box["x"] < graph["x"] - 1 or box["right"] > graph["right"] + 1 or box["y"] < graph["y"] - 1 or box["bottom"] > graph["bottom"] + 1:
                    findings.append(f"{viewport}/{name}: clipped label {label['text']}")
                for dot in value["dots"]:
                    if box["x"] < dot["right"] and box["right"] > dot["x"] and box["y"] < dot["bottom"] and box["bottom"] > dot["y"]:
                        findings.append(f"{viewport}/{name}: label overlaps a node dot: {label['text']}")
            for i, label in enumerate(value["labels"]):
                a = label["rect"]
                for other in value["labels"][i + 1:]:
                    b = other["rect"]
                    if a["x"] < b["right"] and a["right"] > b["x"] and a["y"] < b["bottom"] and a["bottom"] > b["y"]:
                        findings.append(f"{viewport}/{name}: labels overlap")
        for key in ["pointer_stable", "focus_stable", "drag_stable", "zoom_stable", "resize_stable", "scroll_stable", "offscreen_stable"]:
            if not entry.get(key):
                findings.append(f"{viewport}: {key} failed")
    report["findings"] = findings
    (OUT / "measurements.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"report": str(OUT / "measurements.json"), "errors": report["errors"],
        "summary": [{ "viewport": e["viewport"],
            "labels": len(e["default"]["labels"]),
            "min_label_font": min([l["font"] for l in e["default"]["labels"]] or [0]),
            "bounds": e["default"]["expandedBounds"],
            "status_bottom": e["default"]["regions"]["statusbar"]["bottom"],
            "graph_size": e["default"]["regions"]["gsvg"],
            "nda_results": len(e["search"]["results"]),
            "stable": all(e.get(k) for k in ["pointer_stable", "focus_stable", "drag_stable", "zoom_stable"]),
            "overflow": e["default"]["overflow"]
        } for e in report["viewports"]], "nojs": report["nojs"], "findings": findings}, indent=2))
    if report["errors"] or findings:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
