import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const data = JSON.parse(
  readFileSync(new URL("../data.js", import.meta.url), "utf8")
    .replace(/^window\.SKILLDATA=/, "")
    .replace(/;\s*$/, "")
);
const nameOf = (key) => key.split("~~").pop();
const categoryOf = (key) => (key.includes("~~") ? key.split("~~")[0] : key.split("/")[0]);
const domainOf = (key) => data.catDomain[categoryOf(key)] || "";
const sizeOf = Object.fromEntries(data.comms.map((c) => [c.id, c.size]));
const smallCommunityNodes = data.commOf.filter((id) => sizeOf[id] < 3).length;

async function openIntro(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/intro.html");
  await expect(page.locator("body")).toHaveAttribute("data-ready", "true", { timeout: 15000 });
  // data-ready is set before the 700 ms opening camera move. Reading data-scale
  // immediately after it samples a frame in flight, which inverts the wheel
  // assertion and makes the first hover land on a moving dot. Wait for the scale to
  // hold across two polls instead of sleeping for a guessed duration.
  await page.waitForFunction(() => {
    const scale = window.__intro.network.getScale().toFixed(4);
    const previous = window.__scaleSeen;
    window.__scaleSeen = scale;
    return previous === scale && document.body.dataset.scale !== undefined;
  }, null, { polling: 250 });
  return errors;
}

async function waitForCameraSettled(page) {
  await page.waitForFunction(() => {
    const scale = window.__intro.network.getScale().toFixed(4);
    const previous = window.__cameraSettled;
    window.__cameraSettled = scale;
    return previous === scale;
  }, null, { polling: 100 });
}

async function freeNodePoint(page) {
  return page.evaluate(() => {
    const network = window.__intro.network;
    const canvas = document.getElementById("net").getBoundingClientRect();
    const blocked = ["#hero", "#crowd"]
      .map((selector) => document.querySelector(selector))
      .filter(Boolean)
      .map((element) => element.getBoundingClientRect());
    const positions = network.getPositions();
    // Hidden dots are still in getPositions(). The intro hides sparse
    // communities below the focus scale, and a pointer over a hidden dot
    // resolves to nothing, so pick a dot the page will actually answer for.
    const eligible = new Set(window.__intro.eligible());
    for (const key of Object.keys(positions)) {
      const id = Number(key);
      if (!eligible.has(id)) continue;
      const point = network.canvasToDOM(positions[key]);
      const x = point.x + canvas.left;
      const y = point.y + canvas.top;
      if (x < 20 || y < 150 || y > window.innerHeight - 120) continue;
      if (blocked.some((r) => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom)) continue;
      return { x, y, id };
    }
    return null;
  });
}

test.describe("cinematic navigation", () => {
  test("one fixed screen, and the wheel zooms instead of scrolling", async ({ page, isMobile }) => {
    const errors = await openIntro(page);
    const fits = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
      overflow: getComputedStyle(document.body).overflowY
    }));
    expect(fits.scrollHeight).toBeLessThanOrEqual(fits.innerHeight + 1);
    expect(fits.overflow).toBe("hidden");
    expect(await page.evaluate(() => window.scrollY)).toBe(0);

    if (!isMobile) {
      const before = Number(await page.locator("body").getAttribute("data-scale"));
      await page.mouse.move(700, 400);
      await page.mouse.wheel(0, -900);
      await page.waitForFunction(() => {
        const scale = window.__intro.network.getScale().toFixed(4);
        const previous = window.__wheelSeen;
        window.__wheelSeen = scale;
        return previous === scale;
      }, null, { polling: 250 });
      expect(Number(await page.locator("body").getAttribute("data-scale"))).toBeGreaterThan(before);
      expect(await page.evaluate(() => window.scrollY)).toBe(0);
    }
    expect(errors).toEqual([]);
  });

  test("the eight problem types filter the map and the community list", async ({ page }) => {
    await openIntro(page);
    const chips = page.locator("#domains .chip");
    await expect(chips).toHaveCount(Object.keys(data.domains).length);
    await expect(chips).toHaveCount(8);

    await chips.filter({ hasText: "Build and ship" }).click();
    await expect(page.locator("body")).toHaveAttribute("data-domain", "build");
    const hidden = Number(await page.locator("body").getAttribute("data-hidden"));
    const notBuild = data.nodes.filter((key) => domainOf(key) !== "build").length;
    expect(hidden).toBe(notBuild);

    const listed = await page.locator("#crowd-list .crowd__item").evaluateAll((items) =>
      items.map((item) => Number(item.dataset.comm))
    );
    const expected = data.comms
      .filter((c) =>
        data.nodes.some(
          (key, index) => data.commOf[index] === c.id && domainOf(key) === "build"
        )
      )
      .map((c) => c.id);
    expect(listed.sort()).toEqual(expected.sort());
    await expect(page.locator("#crowd-title")).toHaveText("Build and ship");
    await expect(page.locator("#crowd-list .crowd__item").first()).toContainText("of");
  });

  test("focusing a community keeps the chosen problem type and the keyboard focus", async ({ page }) => {
    await openIntro(page);
    await page.locator('#domains .chip[data-domain="build"]').click();
    const first = page.locator("#crowd-list .crowd__item").first();
    const cid = Number(await first.getAttribute("data-comm"));
    const listed = await page.locator("#crowd-list .crowd__item").count();

    await first.click();
    await expect(page.locator("body")).toHaveAttribute("data-domain", "build");
    await expect(page.locator("body")).toHaveAttribute("data-community", String(cid));
    await expect(page.locator("#crowd-title")).toHaveText("Build and ship");
    await expect(page.locator("#crowd-list .crowd__item")).toHaveCount(listed);
    await expect(page.locator(`#crowd-list .crowd__item[data-comm="${cid}"]`))
      .toHaveAttribute("aria-current", "true");
    expect(await page.evaluate(() => document.activeElement?.dataset.comm)).toBe(String(cid));
  });

  test("the community card link is clickable with a mouse", async ({ page }) => {
    await openIntro(page);
    const target = data.comms.slice().sort((a, b) => b.size - a.size)[0];
    await page.locator(`#crowd-list .crowd__item[data-comm="${target.id}"]`).click();
    await expect(page.locator("#hovercard")).toBeVisible();
    await page.locator("#hc-cta").click();
    await page.waitForURL(new RegExp(`index\\.html\\?community=${target.id}$`));
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "community");
    await expect(page.locator("#gcommunity")).toHaveValue(String(target.id));
  });

  test("switching between communities refits from the new visibility state", async ({ page }) => {
    await openIntro(page);
    const ranked = data.comms.slice().sort((a, b) => b.size - a.size);
    const first = ranked[0];
    const second = ranked[1];

    await page.locator(`#crowd-list .crowd__item[data-comm="${first.id}"]`).click();
    await expect(page.locator("body")).toHaveAttribute(
      "data-hidden", String(data.nodes.length - first.size)
    );

    await page.locator(`#crowd-list .crowd__item[data-comm="${second.id}"]`).click();
    await expect(page.locator("body")).toHaveAttribute(
      "data-hidden", String(data.nodes.length - second.size)
    );
    expect(Number(await page.locator("body").getAttribute("data-scale"))).toBeGreaterThan(0);
  });

  test("hovering a dot shows its skill and community card", async ({ page }) => {
    await openIntro(page);
    const point = await freeNodePoint(page);
    expect(point, "a dot outside the panels").not.toBeNull();
    const cid = data.commOf[point.id];
    const community = data.comms.find((c) => c.id === cid);

    await page.mouse.move(point.x, point.y);
    await expect(page.locator("#hovercard")).toBeVisible();
    await expect(page.locator("#hc-title")).toHaveText(nameOf(data.nodes[point.id]));
    await expect(page.locator("#hc-meta")).toContainText(community.label);
    await expect(page.locator("#hc-cta")).toHaveAttribute(
      "href",
      `./index.html?community=${cid}`
    );

    await page.mouse.move(5, 5);
    await expect(page.locator("#hovercard")).toBeHidden();
  });

  test("choosing a community focuses it and links into the workspace", async ({ page }) => {
    await openIntro(page);
    const target = data.comms.slice().sort((a, b) => b.size - a.size)[0];
    const item = page.locator(`#crowd-list .crowd__item[data-comm="${target.id}"]`);
    await item.click();

    await expect(page.locator("body")).toHaveAttribute("data-community", String(target.id));
    await expect(page.locator("#hovercard")).toBeVisible();
    await expect(page.locator("#hc-title")).toHaveText(target.label);
    await expect(page.locator("#hc-cta")).toHaveAttribute(
      "href",
      `./index.html?community=${target.id}`
    );
    const hidden = Number(await page.locator("body").getAttribute("data-hidden"));
    expect(hidden).toBe(data.nodes.length - target.size);
  });

  test("clicking a dot opens the workspace in that community", async ({ page }) => {
    await openIntro(page);
    const point = await freeNodePoint(page);
    expect(point, "a dot outside the panels").not.toBeNull();
    const cid = data.commOf[point.id];
    const community = data.comms.find((c) => c.id === cid);

    await page.mouse.click(point.x, point.y);
    await page.waitForURL(new RegExp(`index\\.html\\?community=${cid}$`));
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "community");
    await expect(page.locator("#gcommunity")).toHaveValue(String(cid));
    await expect(page.locator("#workspace-title")).toHaveText(community.label);
  });

  test("an unknown community deeplink falls back to the overview", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/index.html?community=999999");
    await expect(page.locator("#top")).toHaveAttribute("data-mode", "overview");
    expect(errors).toEqual([]);
  });

  test("a tap shows the card on touch and keeps the link tappable", async ({ page, isMobile }) => {
    test.skip(!isMobile, "touch only");
    await openIntro(page);
    const point = await freeNodePoint(page);
    expect(point, "a dot outside the panels").not.toBeNull();

    await page.touchscreen.tap(point.x, point.y);
    await expect(page.locator("#hovercard")).toBeVisible();
    await expect(page.locator("body")).toHaveClass(/is-touch/);
    const cid = data.commOf[point.id];
    await expect(page.locator("#hc-cta")).toHaveAttribute(
      "href",
      `./index.html?community=${cid}`
    );
  });

  test("zooming in stops drawing sparse communities", async ({ page }) => {
    await openIntro(page);
    const focusScale = Number(await page.locator("body").getAttribute("data-focus-scale"));
    await page.evaluate((scale) => {
      window.__intro.network.moveTo({ scale, animation: { duration: 250 } });
    }, focusScale * 1.6);
    await expect(page.locator("body")).toHaveAttribute("data-scale", /^[0-9.]+$/);
    await waitForCameraSettled(page);

    expect(Number(await page.locator("body").getAttribute("data-scale"))).toBeGreaterThanOrEqual(
      focusScale
    );
    await expect(page.locator("body")).toHaveAttribute("data-hidden", String(smallCommunityNodes));

    await page.evaluate(() => {
      window.__intro.network.moveTo({ scale: 0.05, animation: { duration: 250 } });
    });
    await waitForCameraSettled(page);
    await expect(page.locator("body")).toHaveAttribute("data-hidden", "0");
  });
});
