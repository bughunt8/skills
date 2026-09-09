import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const html = readFileSync(join(root, "index.html"), "utf8");
const data = JSON.parse(
  readFileSync(join(root, "data.js"), "utf8")
    .replace("window.SKILLDATA=", "")
    .replace(/;\s*$/, "")
);

/*
 * The graph is the opening of the page and its navigation, so these are function tests.
 * Each corresponds to something that was actually wrong in this build, which is the only
 * reason any of them is worth running.
 *
 * Four openings were written before this one. A spiral of all 490 nodes was an even
 * speckle. A four-column dendrogram of the declared taxonomy was tidy and inert — it drew
 * the filing system, and a filing system is not a finding. Then this graph, whose first
 * two versions drew nine names on top of each other in the densest community and pushed
 * the nodes it had just highlighted underneath the chip row, where they were unclickable.
 *
 * So most of what follows measures geometry and reachability in a real browser, because
 * geometry and reachability are what kept being wrong. tests/test_network.py covers the
 * same properties on the engine before it reaches the page.
 */

// Every label that is currently drawn, and whether any two of them collide. Measured
// with getBBox in the SVG's own coordinate system rather than by estimating character
// widths: an estimate was two units short vertically, which is exactly how much the
// collisions that survived the first placer overlapped by.
// Wrapped in an immediately-invoked expression on purpose.
//
// page.evaluate() given a STRING evaluates it as an expression. `() => {...}` is an
// expression whose value is a function, and a function is not serialisable, so Playwright
// returned undefined and every assertion below read properties of it. The test threw instead
// of measuring anything, and it did so only in CI: the Python binding this was prototyped
// against does auto-invoke a function expression, so it passed locally for the wrong reason.
const LABEL_OVERLAPS = `(() => {
  const vb = document.getElementById("gsvg").viewBox.baseVal;
  const els = [...document.querySelectorAll(".g-nlabel, .g-clabel")].filter(
    (e) => getComputedStyle(e).opacity !== "0" && getComputedStyle(e).visibility !== "hidden"
  );
  const boxes = els.map((e) => {
    const b = e.getBBox();
    return { x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height, t: e.textContent };
  });
  const bad = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1) {
        bad.push(a.t + " / " + b.t);
      }
    }
  }
  // A label outside the frame is not an overlap and is not acceptable either: the runtime
  // placer had no boundary test, so selecting a node near the right edge pushed its name to
  // x=1503 in a 1400-wide viewBox, where it cleared every other label by being off screen.
  const clipped = boxes
    .filter((b) => b.x0 < -1 || b.x1 > vb.width + 1 || b.y0 < -1 || b.y1 > vb.height + 1)
    .map((b) => b.t);
  return { visible: els.length, overlaps: bad, clipped: clipped };
})()`;

async function settle(page) {
  // The camera eases over 620ms and the labels are placed against its final scale.
  await page.waitForTimeout(900);
}

test.describe("the graph", () => {
  // Desktop behaviour: hover, path tracing, the camera and the keyboard walk. Below the
  // narrow breakpoint the graph deliberately takes neither pointer nor keyboard input, so
  // running these against a phone profile asserts the opposite of what the page intends -
  // which is what the mobile project was doing, failing eight of them.
  //
  // "the graph on a narrow screen" below covers that width, and it is where the claim that
  // the graph is inert there is actually asserted.
  test.skip(
    ({ viewport }) => !viewport || viewport.width <= 1000 || viewport.height <= 720,
    "the graph is a picture, not a control, below the narrow breakpoint"
  );

  test.beforeEach(async ({ page }) => {
    await page.goto("/index.html", { waitUntil: "load" });
    await settle(page);
  });

  test("every skill is a node, and every node is a link to its own card", async ({
    page
  }) => {
    await expect(page.locator(".g-node")).toHaveCount(data.total);
    // The graph is a table of contents before any script runs, so every node has to
    // resolve to a card that exists. A node pointing at a missing anchor is a dead link
    // for anyone with JavaScript off.
    const broken = await page.evaluate(() =>
      [...document.querySelectorAll(".g-node")]
        .map((n) => n.getAttribute("href"))
        .filter((h) => !h || !document.querySelector(h.replace("#", "#")))
        .slice(0, 5)
    );
    expect(broken).toEqual([]);
  });

  test("the drawn relationships are the ones the data reports", async ({ page }) => {
    await expect(page.locator(".g-edge")).toHaveCount(data.edges.length);
    const stated = data.edges.filter((e) => e[3] === 0).length;
    await expect(page.locator(".g-edge--extracted")).toHaveCount(stated);
    await expect(page.locator(".g-edge--inferred")).toHaveCount(
      data.edges.length - stated
    );
    // The count printed on the filter button is a claim about the graph, and the build
    // owns it. Hand-typing it into the markup is the drift this checks for.
    await expect(page.locator("#gstated span")).toHaveText(String(stated));
  });

  test("both ends of every edge are nodes that exist", async ({ page }) => {
    const orphans = await page.evaluate(() => {
      const keys = new Set(
        [...document.querySelectorAll(".g-node")].map((n) => n.getAttribute("data-key"))
      );
      return [...document.querySelectorAll(".g-edge")]
        .filter(
          (e) => !keys.has(e.getAttribute("data-a")) || !keys.has(e.getAttribute("data-b"))
        )
        .map((e) => e.getAttribute("data-a") + " -> " + e.getAttribute("data-b"))
        .slice(0, 5);
    });
    expect(orphans).toEqual([]);
  });

  test("every skill belongs to a community and the largest are named", async ({
    page
  }) => {
    const unassigned = await page.evaluate(
      () =>
        [...document.querySelectorAll(".g-node")].filter(
          (n) => n.getAttribute("data-comm") === null
        ).length
    );
    expect(unassigned).toBe(0);
    // Every community that got a name placed. Names are cheap and colours are not, so more
    // communities are named than are given a distinct hue.
    const named = await page.locator(".g-clabel").count();
    expect(named).toBeGreaterThan(10);
    expect(named).toBeLessThanOrEqual(data.comms.length);
    // The names are generated from the tokens the members share, so an empty or
    // placeholder name means the generator fell through.
    const names = await page.locator(".g-clabel").allTextContents();
    for (const n of names) {
      expect(n.trim().length).toBeGreaterThan(2);
      expect(n).not.toBe("unnamed");
    }
  });

  test("the page opens on the largest community rather than on nothing", async ({
    page
  }) => {
    // A panel waiting for a hover is an empty box on a touch screen, and the counter on
    // this page once sat at zero until the first scroll, which looked broken.
    await expect(page.locator("#paneltier")).toHaveText(/community/i);
    await expect(page.locator("#panelname")).toHaveText(data.comms[0].label);
    await expect(page.locator("#panelev")).toContainText(String(data.comms[0].size));
    const lit = await page.locator(".g-node.is-on").count();
    expect(lit).toBe(data.comms[0].size);
  });

  test("no two visible names overlap, in any state the reader can reach", async ({
    page
  }) => {
    // The assertion this whole file exists for. Nine names in one pile is what the first
    // version of this graph shipped, and an earlier version of the page had 31
    // overlapping label pairs on one search term.
    const seen = [];
    seen.push(["opening", await page.evaluate(LABEL_OVERLAPS)]);

    const chips = await page.locator(".beat").count();
    for (let i = 1; i <= Math.min(chips, 8); i++) {
      await page.locator(`.beat:nth-child(${i}) a`).click();
      await settle(page);
      seen.push([`community ${i}`, await page.evaluate(LABEL_OVERLAPS)]);
    }

    for (const q of ["review", "design", "principle", "manager", "a", ""]) {
      await page.fill("#gsearch", q);
      await settle(page);
      seen.push([`search ${JSON.stringify(q)}`, await page.evaluate(LABEL_OVERLAPS)]);
    }

    const failures = seen
      .filter(([, r]) => r.overlaps.length > 0)
      .map(([where, r]) => `${where}: ${r.overlaps.slice(0, 3).join(", ")}`);
    expect(failures).toEqual([]);
    const offscreen = seen
      .filter(([, r]) => r.clipped.length > 0)
      .map(([where, r]) => `${where}: ${r.clipped.slice(0, 3).join(", ")}`);
    expect(offscreen).toEqual([]);
    // Every state must actually have drawn something, or the check above passes by
    // measuring nothing.
    for (const [where, r] of seen) {
      expect(r.visible, `${where} drew no labels at all`).toBeGreaterThan(4);
    }
  });

  test("opening a community frames it and counter-scales its names", async ({
    page
  }) => {
    const before = await page.evaluate(() => {
      const el = document.querySelector(".g-clabel");
      return el.getBoundingClientRect().height;
    });
    await page.locator(".beat:nth-child(3) a").click();
    await settle(page);
    const after = await page.evaluate(() => {
      const vp = document.getElementById("vp");
      const el = document.querySelector(".g-clabel");
      return {
        k: +getComputedStyle(vp).getPropertyValue("--k"),
        transform: vp.style.transform,
        height: el.getBoundingClientRect().height
      };
    });
    expect(after.k).toBeGreaterThan(1.05);
    expect(after.transform).toContain("scale(");
    // The point of dividing the font size by the zoom factor: a label is the same size on
    // screen at every zoom level. Without it the labels grew with the zoom until they
    // collided, and the community names disappeared behind their own outline.
    expect(Math.abs(after.height - before)).toBeLessThan(2.5);
  });

  test("hovering a node explains it with its own evidence", async ({ page }) => {
    const hub = await page.evaluate(
      () =>
        [...document.querySelectorAll(".g-node")].sort(
          (a, b) => +b.getAttribute("data-deg") - +a.getAttribute("data-deg")
        )[0].outerHTML.match(/data-key="([^"]+)"/)[1]
    );
    await page.locator(`.g-node[data-key="${hub}"]`).hover();
    await page.waitForTimeout(350);
    const name = await page.locator(`.g-node[data-key="${hub}"]`).getAttribute("data-name");
    const deg = await page.locator(`.g-node[data-key="${hub}"]`).getAttribute("data-deg");
    await expect(page.locator("#panelname")).toHaveText(name);
    await expect(page.locator("#panelev")).toContainText(`${deg} connections`);
    await expect(page.locator("#panelev")).toContainText("stated");
    // Its neighbours light up with it: reading one node means seeing what it reaches.
    const on = await page.locator(".g-node.is-on").count();
    expect(on).toBe(+deg + 1);
  });

  test("a traced path is a real walk along real edges", async ({ page }) => {
    await page.click("#gpath");
    await settle(page);
    await expect(page.locator("#gpath")).toHaveAttribute("aria-pressed", "true");

    // Two well-connected skills from different communities, so the route is more than one
    // hop and crosses the graph.
    const pair = await page.evaluate(() => {
      const ns = [...document.querySelectorAll(".g-node")].sort(
        (a, b) => +b.getAttribute("data-deg") - +a.getAttribute("data-deg")
      );
      const first = ns[0];
      const other = ns.find(
        (n) => n.getAttribute("data-comm") !== first.getAttribute("data-comm")
      );
      return [first.getAttribute("data-key"), other.getAttribute("data-key")];
    });
    for (const key of pair) {
      await page.locator(`.g-node[data-key="${key}"]`).click();
      await settle(page);
    }

    await expect(page.locator("#paneltier")).toHaveText(/\d+ hops/);
    const hops = +(await page.locator("#paneltier").innerText()).split(" ")[0];
    const walk = await page.locator("#panelchain li").allTextContents();
    expect(walk.length).toBe(hops + 1);

    // Every consecutive pair in the reported walk has to be an edge that is actually
    // drawn. A path panel that lists plausible names but not a real route is worse than
    // no path panel.
    const lit = await page.locator(".g-edge.is-path").count();
    expect(lit).toBe(hops);
    const fake = await page.evaluate((names) => {
      const byName = {};
      for (const n of document.querySelectorAll(".g-node")) {
        byName[n.getAttribute("data-name")] = n.getAttribute("data-key");
      }
      const bad = [];
      for (let i = 1; i < names.length; i++) {
        const a = byName[names[i - 1]];
        const b = byName[names[i]];
        const found = [...document.querySelectorAll(".g-edge")].some((e) => {
          const x = e.getAttribute("data-a");
          const y = e.getAttribute("data-b");
          return (x === a && y === b) || (x === b && y === a);
        });
        if (!found) bad.push(names[i - 1] + " -> " + names[i]);
      }
      return bad;
    }, walk);
    expect(fake).toEqual([]);
    // Picking mode releases itself once it has both ends, or the next click silently
    // starts another path.
    await expect(page.locator("#gpath")).toHaveAttribute("aria-pressed", "false");
  });

  test("every node is pickable while a path is being traced", async ({ page }) => {
    // The overlays cover roughly a quarter of the frame. Framing a community moved nodes
    // under the chip row, which swallowed the clicks: the second end of a path could not
    // be picked at all. Entering picking mode has to pull the camera back out and stop
    // the overlays taking clicks.
    await page.locator(".beat:nth-child(2) a").click();
    await settle(page);
    await page.click("#gpath");
    await settle(page);
    const state = await page.evaluate(() => {
      const vp = document.getElementById("vp");
      const names = ["#panel", "#beats", "#rail"];
      return {
        k: +getComputedStyle(vp).getPropertyValue("--k"),
        blocking: names.filter(
          (s) =>
            document.querySelector(s) &&
            getComputedStyle(document.querySelector(s)).pointerEvents !== "none"
        )
      };
    });
    expect(state.k).toBeLessThan(1.05);
    expect(state.blocking).toEqual([]);
  });

  test("the evidence filter hides the inferred relationships and nothing else", async ({
    page
  }) => {
    await page.click("#gstated");
    await page.waitForTimeout(300);
    const shown = await page.evaluate(() => {
      const vis = (e) => getComputedStyle(e).opacity !== "0";
      return {
        inferred: [...document.querySelectorAll(".g-edge--inferred")].filter(vis).length,
        extracted: [...document.querySelectorAll(".g-edge--extracted")].filter(vis).length,
        nodes: document.querySelectorAll(".g-node").length
      };
    });
    expect(shown.inferred).toBe(0);
    expect(shown.extracted).toBe(data.edges.filter((e) => e[3] === 0).length);
    expect(shown.nodes).toBe(data.total);
  });

  test("search dims the library to its matches without hiding it", async ({ page }) => {
    await page.fill("#gsearch", "architect");
    await settle(page);
    const r = await page.evaluate(() => ({
      hits: document.querySelectorAll(".g-node.is-hit").length,
      total: document.querySelectorAll(".g-node").length,
      dim: document.getElementById("top").classList.contains("is-dim")
    }));
    expect(r.dim).toBe(true);
    expect(r.hits).toBeGreaterThan(0);
    expect(r.hits).toBeLessThan(r.total);
    // Matching on the visible name, not on the identity key: the key carries the category,
    // so matching it made "engineering" hit all 105 skills filed under it.
    const wrong = await page.evaluate(() =>
      [...document.querySelectorAll(".g-node.is-hit")]
        .filter((n) => !n.getAttribute("data-name").includes("architect"))
        .map((n) => n.getAttribute("data-name"))
        .slice(0, 3)
    );
    expect(wrong).toEqual([]);
  });

  test("Escape releases every mode at once", async ({ page }) => {
    // A reset that leaves a button pressed, a path lit or the camera zoomed is a fault
    // this page has had: clicking a node appeared to work and then silently stopped
    // holding, because a scroll tick was clearing the selection behind it.
    await page.click("#gstated");
    await page.locator(".beat:nth-child(4) a").click();
    await settle(page);
    await page.fill("#gsearch", "review");
    await settle(page);
    await page.keyboard.press("Escape");
    await settle(page);
    const after = await page.evaluate(() => {
      const stage = document.getElementById("top");
      return {
        stated: document.getElementById("gstated").getAttribute("aria-pressed"),
        path: document.getElementById("gpath").getAttribute("aria-pressed"),
        query: document.getElementById("gsearch").value,
        k: +getComputedStyle(document.getElementById("vp")).getPropertyValue("--k"),
        classes: [...stage.classList].filter((c) => c.startsWith("is-")),
        lit: document.querySelectorAll(".g-node.is-path, .g-node.is-hit").length
      };
    });
    expect(after.stated).toBe("false");
    expect(after.path).toBe("false");
    expect(after.query).toBe("");
    expect(after.k).toBeLessThan(1.05);
    expect(after.lit).toBe(0);
    expect(after.classes).not.toContain("is-dim");
    expect(after.classes).not.toContain("is-extracted-only");
    // Back to the opening statement, not to a blank stage.
    await expect(page.locator("#panelname")).toHaveText(data.comms[0].label);
  });

  test("a node can be reached and read with the keyboard alone", async ({ page }) => {
    const key = await page.evaluate(
      () => document.querySelector(".g-node").getAttribute("data-key")
    );
    const node = page.locator(`.g-node[data-key="${key}"]`);
    await node.focus();
    await page.waitForTimeout(300);
    const name = await node.getAttribute("data-name");
    await expect(page.locator("#panelname")).toHaveText(name);
    // aria-label carries the same two facts the panel does, for a reader who never sees
    // the panel.
    await expect(node).toHaveAttribute("aria-label", new RegExp(`^${name}, \\d+ connection`));
  });


  test("the panel gives the evidence for each connection, not just the count", async ({
    page
  }) => {
    // 52 KB of the data file was an explanation the page had no way to show, while a comment
    // claimed it said what an edge is when you select it. Either surface it or drop it.
    const hub = await page.evaluate(
      () =>
        [...document.querySelectorAll(".g-node")].sort(
          (a, b) => +b.getAttribute("data-deg") - +a.getAttribute("data-deg")
        )[0].getAttribute("data-key")
    );
    await page.locator(`.g-node[data-key="${hub}"]`).hover();
    await page.waitForTimeout(350);
    const lines = await page.locator("#panelchain li").allTextContents();
    expect(lines.length).toBeGreaterThan(2);
    // Every line names a skill and says why it is joined: led by a Solution, packaged
    // together, or which words the two names share.
    const bare = lines.filter((l) => !/ — /.test(l));
    expect(bare).toEqual([]);
    const reasons = lines.map((l) => l.split(" — ")[1]);
    for (const r of reasons) {
      expect(r).toMatch(/^(led by |leads it|steps of |siblings in |names share |named )/);
    }
  });

  test("the graph is one tab stop, not one per skill", async ({ page }) => {
    // Every node is a real link, which is what makes this a table of contents with
    // JavaScript off. With JavaScript on that put 490 sequential stops in the tab order and
    // several hundred Tab presses between the graph and the section below it.
    const stops = await page.evaluate(
      () => document.querySelectorAll('.g-node[tabindex="0"]').length
    );
    expect(stops).toBe(1);
    const rest = await page.evaluate(
      () => document.querySelectorAll('.g-node[tabindex="-1"]').length
    );
    expect(rest).toBe(data.total - 1);
  });

  test("arrow keys walk the graph from the single tab stop", async ({ page }) => {
    await page.locator('.g-node[tabindex="0"]').focus();
    const first = await page.evaluate(() => document.activeElement.getAttribute("data-key"));
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(250);
    const second = await page.evaluate(() =>
      document.activeElement.getAttribute("data-key")
    );
    expect(second).not.toBe(first);
    expect(second).toBeTruthy();
    // The stop travels with the focus, so there is still exactly one way in.
    const stops = await page.evaluate(
      () => document.querySelectorAll('.g-node[tabindex="0"]').length
    );
    expect(stops).toBe(1);
    await expect(page.locator("#panelname")).toHaveText(
      await page.locator(`.g-node[data-key="${second}"]`).getAttribute("data-name")
    );
  });

  test("the frontier ring is exactly the skills with no relationships", async ({
    page
  }) => {
    // The styling says "nothing in the library connects this skill to anything". It was
    // keyed on Solution membership, which drew 158 skills that way while 129 of them had
    // edges, and left five genuine isolates out of it.
    const wrong = await page.evaluate(() => {
      const deg = {};
      for (const e of document.querySelectorAll(".g-edge")) {
        deg[e.getAttribute("data-a")] = (deg[e.getAttribute("data-a")] || 0) + 1;
        deg[e.getAttribute("data-b")] = (deg[e.getAttribute("data-b")] || 0) + 1;
      }
      const bad = [];
      for (const n of document.querySelectorAll(".g-node")) {
        const isolated = !deg[n.getAttribute("data-key")];
        const styled = n.classList.contains("is-loose");
        if (isolated !== styled) bad.push(n.getAttribute("data-name"));
      }
      return bad;
    });
    expect(wrong).toEqual([]);
  });

  test("the community chips walk the largest communities", async ({ page }) => {
    const chips = await page.locator(".beat a").allTextContents();
    expect(chips.length).toBe(data.featured.length);
    const labels = data.featured.map(
      (id) => data.comms.find((c) => c.id === id).label
    );
    expect(chips.map((c) => c.trim())).toEqual(labels);
  });
});

test.describe("the graph on a narrow screen", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("is a picture, not a control", async ({ page }) => {
    await page.goto("/index.html", { waitUntil: "load" });
    await page.waitForTimeout(900);
    // A node's click target is expressed in the graph's own 1,400-unit coordinate system, so
    // it scales with the viewport: about 10 CSS pixels at 1440 wide and under 3.5 at 390.
    // Offering a 3-pixel target, or 490 keyboard stops into 3-pixel targets, is worse than
    // not offering them: the search box and the text list below carry the same information.
    const state = await page.evaluate(() => ({
      pointer: getComputedStyle(document.querySelector(".g-node")).pointerEvents,
      stops: document.querySelectorAll('.g-node[tabindex="0"]').length,
      stillLinks: [...document.querySelectorAll(".g-node")].every((n) =>
        n.getAttribute("href")
      )
    }));
    expect(state.pointer).toBe("none");
    expect(state.stops).toBe(0);
    // Still real links in the document, so the no-JavaScript table of contents survives.
    expect(state.stillLinks).toBe(true);
    await expect(page.locator("#gsearch")).toBeVisible();
    await expect(page.locator(".beat").first()).toBeVisible();
  });
});

test.describe("the graph as markup", () => {
  test("the community and node counts in the document match the data", () => {
    expect((html.match(/class="g-node /g) || []).length).toBe(data.total);
    const namedInMarkup = (html.match(/class="g-clabel /g) || []).length;
    expect(namedInMarkup).toBeGreaterThan(10);
    expect(namedInMarkup).toBeLessThanOrEqual(data.comms.length);
    // A name for every skill, so anything can be revealed on demand. Emitting only the
    // hubs meant opening a community whose strongest member was not one of the library's
    // strongest named nothing at all.
    expect((html.match(/class="g-nlabel/g) || []).length).toBe(data.total);
  });

  test("the graph carries no inline style for the CSP to block", () => {
    // The page ships a Content-Security-Policy without unsafe-inline. An inline style
    // attribute is silently dropped, which is how the hero counter sat at zero on the
    // live site while working locally.
    const svg = html.slice(html.indexOf("<svg"), html.indexOf("</svg>"));
    expect(svg.match(/ style="/g)).toBeNull();
  });
});
