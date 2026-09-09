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
 * The tree is the opening of the page and its navigation, so these are function
 * tests. Each one below corresponds to something that was actually wrong at some
 * point in this build, which is the only reason any of them are worth running.
 *
 * The layout went through three arrangements before this one. All 50 Solutions in a
 * single column put them 9 units apart, too close to label. Spreading one domain's
 * Solutions over the full height while its groups stayed on their rows made 19 edges
 * fan out of a 90-unit cluster and cross each other. Moving the groups onto their
 * Solutions fixed the crossings and collided with the groups of other domains. So
 * several tests here are about geometry, because geometry is what kept being wrong.
 */

const LAYERS = ["domain", "practice", "solution", "skill"];

test.describe("the four-layer tree", () => {
  test("is prerendered, not drawn by script", async ({ page }) => {
    // Asserted against the shipped file first: if the tree only exists after
    // JavaScript runs, the opening image of the page is a blank box for anyone the
    // script fails for.
    for (const layer of LAYERS) {
      expect(
        (html.match(new RegExp(`data-layer="${layer}"`, "g")) || []).length,
        `${layer} nodes in the built file`
      ).toBeGreaterThan(0);
    }
    expect((html.match(/data-layer="solution"/g) || []).length).toBe(data.solutions);
    expect((html.match(/data-layer="skill"/g) || []).length).toBe(data.total);
    expect((html.match(/class="g-edge/g) || []).length).toBeGreaterThan(500);

    await page.goto("/index.html");
    await expect(page.locator('.g-node[data-layer="solution"]')).toHaveCount(
      data.solutions
    );
    await expect(page.locator('.g-node[data-layer="skill"]')).toHaveCount(data.total);
    await expect(page.locator(".sol")).toHaveCount(data.solutions);
    await expect(page.locator(".card")).toHaveCount(data.total);
  });

  test("every node has exactly one parent, and the layers nest correctly", async ({
    page
  }) => {
    await page.goto("/index.html");
    const bad = await page.evaluate((layers) => {
      const nodes = [...document.querySelectorAll(".g-node")];
      const byId = {};
      nodes.forEach((n) => {
        byId[n.getAttribute("data-id")] = n;
      });
      const problems = [];
      let roots = 0;
      nodes.forEach((n) => {
        const id = n.getAttribute("data-id");
        const layer = n.getAttribute("data-layer");
        const parent = n.getAttribute("data-parent");
        if (!parent) {
          roots++;
          if (layer !== "domain") problems.push(`${id} is a root but a ${layer}`);
          return;
        }
        const p = byId[parent];
        if (!p) return problems.push(`${id} points at a missing parent ${parent}`);
        const pl = p.getAttribute("data-layer");
        // A skill may hang off a Solution or, when no Solution leads it, off a group.
        // Everything else must sit exactly one layer below its parent.
        const ok =
          layer === "skill"
            ? pl === "solution" || pl === "practice"
            : layers.indexOf(pl) === layers.indexOf(layer) - 1;
        if (!ok) problems.push(`a ${layer} (${id}) hangs off a ${pl}`);
        if (n.getAttribute("data-dom") !== p.getAttribute("data-dom")) {
          problems.push(`${id} is in a different domain from its parent`);
        }
      });
      if (roots !== 7) problems.push(`${roots} roots, expected 7`);
      return problems;
    }, LAYERS);
    expect(bad, "the tree does not nest").toEqual([]);
  });

  test("the counts on the nodes agree with the tree under them", async ({ page }) => {
    await page.goto("/index.html");
    // Every group label carries a skill count. They all read 0 at one point, because
    // the count was being looked up under the domain's key rather than the node's.
    const wrong = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll(".g-node")];
      const kids = {};
      nodes.forEach((n) => {
        const p = n.getAttribute("data-parent");
        if (p) (kids[p] = kids[p] || []).push(n);
      });
      function countSkills(id) {
        const mine = kids[id] || [];
        return mine.reduce(
          (sum, k) =>
            sum +
            (k.getAttribute("data-layer") === "skill"
              ? 1
              : countSkills(k.getAttribute("data-id"))),
          0
        );
      }
      const bad = [];
      nodes.forEach((n) => {
        const layer = n.getAttribute("data-layer");
        if (layer === "skill") return;
        const id = n.getAttribute("data-id");
        const claimed = +n.getAttribute("data-skills");
        const actual = countSkills(id);
        if (claimed !== actual) bad.push(`${id} says ${claimed}, has ${actual}`);
        if (layer === "practice") {
          const shown = (
            document.querySelector(`.g-label[data-id="${id}"]`) || { textContent: "" }
          ).textContent;
          if (shown.indexOf(String(actual)) < 0) {
            bad.push(`${id} label reads "${shown.trim()}", should show ${actual}`);
          }
        }
      });
      return bad;
    });
    expect(wrong, "node counts disagree with the tree").toEqual([]);
  });

  test("every skill in the library is a leaf of the tree exactly once", async ({
    page
  }) => {
    await page.goto("/index.html");
    const check = await page.evaluate(() => {
      const leaves = [...document.querySelectorAll('.g-node[data-layer="skill"]')].map(
        (n) => n.getAttribute("data-key")
      );
      const cards = [...document.querySelectorAll(".card")].map((c) =>
        c.getAttribute("data-id")
      );
      const seen = {};
      const dupes = [];
      leaves.forEach((k) => {
        if (seen[k]) dupes.push(k);
        seen[k] = true;
      });
      return {
        dupes,
        missing: cards.filter((k) => !seen[k]),
        extra: leaves.filter((k) => cards.indexOf(k) < 0)
      };
    });
    expect(check.dupes, "skills drawn twice").toEqual([]);
    expect(check.missing, "skills in the library with no node").toEqual([]);
    expect(check.extra, "nodes with no skill").toEqual([]);
  });

  test("opening a domain shows its Solutions and no others", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(900);

    const domains = await page.evaluate(() =>
      [...document.querySelectorAll('.g-node[data-layer="domain"]')].map((n) => ({
        id: n.getAttribute("data-id"),
        sols: +n.getAttribute("data-sols")
      }))
    );
    expect(domains.length).toBe(7);

    for (const d of domains) {
      await page.locator(`.g-node[data-id="${d.id}"]`).dispatchEvent("click");
      const state = await page.evaluate((domId) => {
        const open = [...document.querySelectorAll(".g-node--solution.is-open")];
        return {
          open: open.length,
          foreign: open.filter((n) => n.getAttribute("data-dom") !== domId).length,
          groups: [...document.querySelectorAll(".g-node--practice.is-open")].length,
          groupsForeign: [
            ...document.querySelectorAll(".g-node--practice.is-open")
          ].filter((n) => n.getAttribute("data-dom") !== domId).length,
          skills: [...document.querySelectorAll(".g-node--skill.is-open")].length,
          stage: document.getElementById("top").getAttribute("data-domain")
        };
      }, d.id);
      expect(state.open, `${d.id} opens its Solutions`).toBe(d.sols);
      expect(state.foreign, `${d.id} shows no other domain's Solutions`).toBe(0);
      expect(state.groupsForeign, `${d.id} shows no other domain's groups`).toBe(0);
      expect(state.groups, `${d.id} opens its groups`).toBeGreaterThan(0);
      // Opening a domain must close the branch that was open in the previous one,
      // or a column of skills belonging to an off-screen Solution stays behind.
      expect(state.skills, `${d.id} starts with no branch open`).toBe(0);
      expect(state.stage).toBe(d.id);
    }
  });

  test("opening a Solution shows exactly the skills its card lists", async ({
    page
  }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(900);

    const sols = await page.evaluate(() =>
      [...document.querySelectorAll('.g-node[data-layer="solution"]')].map((n) => ({
        id: n.getAttribute("data-id"),
        key: n.getAttribute("data-key"),
        dom: n.getAttribute("data-dom"),
        name: n.getAttribute("data-name")
      }))
    );
    expect(sols.length).toBe(data.solutions);

    for (const s of sols) {
      // Its domain has to be open before it can be clicked, which is the whole
      // interaction model: depth is reached by opening, not by scrolling.
      await page.locator(`.g-node[data-id="${s.dom}"]`).dispatchEvent("click");
      await page.locator(`.g-node[data-id="${s.id}"]`).dispatchEvent("click");
      const seen = await page.evaluate((sol) => {
        const card = document.querySelector(`.sol[data-sol="${sol.key}"]`);
        const steps = [...card.querySelectorAll(".sol__step")].map((x) =>
          x.getAttribute("data-id")
        );
        const open = [...document.querySelectorAll(".g-node--skill.is-open")].map((n) =>
          n.getAttribute("data-key")
        );
        return {
          steps: steps.sort(),
          // The lead is drawn as a leaf of its own Solution as well as being the
          // Solution, so it is expected on screen and is not in the step list.
          open: open.sort(),
          panel: (document.getElementById("panelname") || {}).textContent || "",
          chain: document.querySelectorAll("#panelchain li").length
        };
      }, s);

      // Every step the card lists must be on screen. code-review is led by two
      // Solutions and can only be a child of one of them, so the second reveals it
      // through the cross-link — which is exactly the case that showed two skills
      // for a three-step Solution.
      const missing = seen.steps.filter((k) => seen.open.indexOf(k) < 0);
      expect(missing, `${s.name} does not show all of its steps`).toEqual([]);
      expect(seen.panel, `panel for ${s.name}`).toContain(s.name);
      expect(seen.chain, `panel chain for ${s.name}`).toBe(seen.steps.length);
    }
  });

  test("selecting a skill lights the whole path back to its domain", async ({
    page
  }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(900);
    await page.locator('.g-node[data-layer="solution"].is-open').first().dispatchEvent("click");
    await page.waitForTimeout(300);

    const leaf = page.locator(".g-node--skill.is-open").first();
    await leaf.dispatchEvent("click");
    const lit = await page.evaluate(() => {
      const on = [...document.querySelectorAll(".g-node.is-on")];
      return {
        layers: on.map((n) => n.getAttribute("data-layer")).sort(),
        edges: [...document.querySelectorAll(".g-edge.is-on")].length
      };
    });
    // One of each layer at least: the skill, its Solution, its group, its domain.
    for (const layer of LAYERS) {
      expect(lit.layers, `the path includes a ${layer}`).toContain(layer);
    }
    expect(lit.edges, "the path's edges are lit").toBeGreaterThan(2);
  });

  test("clicking commits, hovering only previews", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(900);

    const two = await page.evaluate(() =>
      [...document.querySelectorAll(".g-node--solution.is-open")]
        .slice(0, 2)
        .map((n) => n.getAttribute("data-id"))
    );
    expect(two.length).toBe(2);

    await page.locator(`.g-node[data-id="${two[0]}"]`).dispatchEvent("click");
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", two[0]);

    // Hovering elsewhere must not silently replace a committed selection. Before the
    // pin existed, moving the pointer off a clicked node onto any neighbour changed
    // the panel, so it described something the reader had not chosen.
    await page.locator(`.g-node[data-id="${two[1]}"]`).dispatchEvent("mouseenter");
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", two[0]);
    await expect(page.locator("#top")).toHaveAttribute("data-focused", two[0]);

    await page.keyboard.press("Escape");
    await expect(page.locator("#top")).toHaveAttribute("data-pinned", "");

    // And hovering works again once the pin is released.
    await page.mouse.move(5, 5);
    await page.locator(`.g-node[data-id="${two[1]}"]`).dispatchEvent("mouseenter");
    await expect(page.locator("#top")).toHaveAttribute("data-focused", two[1]);
  });

  test("a real pointer click hits a node at every layer", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1200);

    // Wait for scrolling to come to rest before measuring anything. Lenis eases the
    // scroll position, so a coordinate measured while it is still settling is stale
    // by the time the pointer arrives and the click lands on the background.
    await page.waitForFunction(
      () => {
        const y = Math.round(window.scrollY);
        if (window.__lastY === y) return true;
        window.__lastY = y;
        return false;
      },
      null,
      { timeout: 5000, polling: 250 }
    );

    // The rest of the suite dispatches events, so this is the one test that proves the
    // nodes are big enough to hit with a pointer and that nothing is layered over the
    // tree intercepting clicks. The panel and the intro used to sit on top of it.
    for (const sel of [
      '.g-node[data-layer="domain"]',
      ".g-node--practice.is-open",
      ".g-node--solution.is-open"
    ]) {
      // Bring it on screen first. elementFromPoint only sees the viewport, and on a
      // phone the stage is an ordinary scrolling column, so a node can sit below the
      // fold — which reads as "covered by nothing" rather than "not visible".
      await page.locator(sel).first().scrollIntoViewIfNeeded();
      await page.waitForTimeout(250);

      const pt = await page.evaluate((selector) => {
        const el = document.querySelector(selector);
        const r = el.querySelector(".g-hit").getBoundingClientRect();
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top + r.height / 2);
        const top = document.elementFromPoint(cx, cy);
        const owner = top && top.closest ? top.closest(".g-node") : null;
        return {
          cx,
          cy,
          id: el.getAttribute("data-id"),
          onTop: owner && owner.getAttribute("data-id")
        };
      }, sel);

      expect(pt.onTop, `what is on top at ${sel}`).toBe(pt.id);
      await page.mouse.move(pt.cx, pt.cy);
      await page.mouse.down();
      await page.mouse.up();
      await expect(page.locator("#top")).toHaveAttribute("data-pinned", pt.id);
    }
  });

  test("search finds skills and opens the branch holding them", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(900);

    // A hit deeper than the open branch is a hit nobody can see, so searching has to
    // open the domain and the Solution that hold it.
    await page.fill("#gsearch", "code-review");
    await page.waitForTimeout(500);
    const found = await page.evaluate(() => ({
      nodes: [...document.querySelectorAll(".g-node.is-hit")].map((n) => ({
        layer: n.getAttribute("data-layer"),
        name: n.getAttribute("data-name"),
        visible: +getComputedStyle(n).opacity > 0.05
      })),
      cards: document.querySelectorAll(".card.is-hit").length
    }));
    const skillHits = found.nodes.filter((n) => n.layer === "skill");
    expect(skillHits.length, "code-review is somewhere in the tree").toBeGreaterThan(0);
    expect(
      skillHits.some((n) => n.visible),
      "at least one hit is actually on screen"
    ).toBe(true);
    expect(found.cards, "the library shows the hit too").toBeGreaterThan(0);

    await page.fill("#gsearch", "");
    await page.waitForTimeout(400);
    expect(await page.locator(".g-node.is-hit").count()).toBe(0);
  });

  test("the provenance filters select by tier", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(700);
    await page.click('.chip[data-tier="curated"]');
    await page.waitForTimeout(400);
    const lit = await page.evaluate(() =>
      [...document.querySelectorAll('.g-node[data-layer="solution"].is-hit')].map((n) =>
        n.getAttribute("data-tier")
      )
    );
    expect(lit.length).toBeGreaterThan(0);
    expect([...new Set(lit)]).toEqual(["curated"]);
  });

  test("scrolling opens each domain in turn", async ({ page, isMobile }) => {
    // Desktop only, deliberately. Below the stacking breakpoint the stage is a single
    // column with its own height and there is no pin, because pinning a stage taller
    // than the viewport hides its own controls for the length of the pin.
    test.skip(!!isMobile, "no traversal without a pin");

    await page.goto("/index.html");
    await page.waitForTimeout(800);
    const seen = new Set();
    for (let i = 0; i < 9; i++) {
      await page.mouse.wheel(0, 320);
      await page.waitForTimeout(320);
      const open = await page.getAttribute("#top", "data-domain");
      if (open) seen.add(open);
      expect(
        await page.locator(".beat.is-on").count(),
        "exactly one chapter marker is active"
      ).toBe(1);
    }
    expect(seen.size, "scrolling moves through more than one domain").toBeGreaterThan(2);
  });

  test("no two visible labels are drawn across each other", async ({ page }) => {
    await page.goto("/index.html");
    await page.waitForTimeout(1200);

    const overlapping = () =>
      page.evaluate(() => {
        const vis = [...document.querySelectorAll(".g-label")]
          .filter((e) => +getComputedStyle(e).opacity > 0.4)
          .map((e) => ({ n: e.textContent.trim(), b: e.getBoundingClientRect() }));
        const pairs = [];
        for (let i = 0; i < vis.length; i++) {
          for (let j = i + 1; j < vis.length; j++) {
            const a = vis[i].b;
            const b = vis[j].b;
            if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) {
              pairs.push(`${vis[i].n} / ${vis[j].n}`);
            }
          }
        }
        return pairs;
      });

    expect(await overlapping(), "labels overlapping at rest").toEqual([]);

    // And with the largest branch in the library open, which is the densest state the
    // drawing ever reaches: 22 skills in one column.
    const biggest = await page.evaluate(() => {
      const all = [...document.querySelectorAll('.g-node[data-layer="solution"]')];
      all.sort((a, b) => +b.getAttribute("data-skills") - +a.getAttribute("data-skills"));
      return { id: all[0].getAttribute("data-id"), dom: all[0].getAttribute("data-dom") };
    });
    await page.locator(`.g-node[data-id="${biggest.dom}"]`).dispatchEvent("click");
    await page.locator(`.g-node[data-id="${biggest.id}"]`).dispatchEvent("click");
    await page.waitForTimeout(500);
    expect(await overlapping(), "labels overlapping with the largest branch open").toEqual(
      []
    );
  });

  test("every node is a link that resolves, so the tree works without scripting", async ({
    page
  }) => {
    await page.goto("/index.html");

    // The nodes used to be role="button" with a click handler, which made every one of
    // them inert on a page whose whole claim is that it works with JavaScript off.
    const bad = await page.evaluate(() =>
      [...document.querySelectorAll(".g-node")]
        .map((n) => ({
          id: n.getAttribute("data-id"),
          href: n.getAttribute("href")
        }))
        .filter((n) => !n.href || !document.querySelector(n.href))
    );
    expect(bad, "nodes whose link goes nowhere").toEqual([]);

    await page.locator('.g-node[data-layer="domain"]').first().focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(300);
    await expect(page.locator("#panelname")).not.toBeEmpty();
  });

  test("activating a node does not scroll the tree out from under you", async ({
    page,
    isMobile
  }) => {
    // On desktop the script shows the selection in the panel instead of following the
    // link. On a phone there is no panel beside the tree and no pin, so following the
    // link to the card is the correct outcome, not a regression.
    test.skip(!!isMobile, "no panel beside the tree on a phone");
    await page.goto("/index.html");
    await page.waitForTimeout(900);
    await page.locator(".g-node--solution.is-open").first().dispatchEvent("click");
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => Math.round(window.scrollY))).toBeLessThan(60);
  });
});

test.describe("the page states its size honestly", () => {
  test("the headline never reads zero", async ({ page }) => {
    // The first version animated its number up from 0 as you scrolled, so the first
    // thing every visitor read was "0 skills, 24 categories". A headline's resting
    // state should not be a false statement.
    await page.goto("/index.html");
    const h1 = await page.locator("h1").innerText();
    expect(h1).not.toMatch(/\b0\b/);
    expect(h1).toContain(String(data.total));
    expect(h1).toContain(String(data.solutions));

    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(400);
    expect(await page.locator("h1").innerText()).toContain(String(data.total));
  });

  test("the whole page fits in a sane amount of scrolling", async ({ page }) => {
    // The version before this one was 76,095px tall, most of it pinned chapters, and
    // reaching a named skill meant travelling past hundreds of others. Depth is now
    // reached by opening a branch, which costs no page height at all.
    await page.goto("/index.html");
    await page.waitForTimeout(1500);
    const height = await page.evaluate(() => document.body.scrollHeight);
    expect(height).toBeLessThan(26000);
    expect(height).toBeGreaterThan(2000);
  });
});
