import { test, expect } from "@playwright/test";
import { assertNoRuntimeErrors, saveEvidence } from "../scripts/workspace-test-helpers.mjs";
import {
  openMotionWorkspace, openMotionPage, expectMotionIdle, resetProbe, readProbe,
  motionEpisodes, sampleMotionFrame, motionSnapshot, comparableSnapshot,
  resultKeys, resultFor, tapOrClick, ensureVisible, sampleCamera, cameraDisplacement
} from "../scripts/motion-test-helpers.mjs";

// Acceptance for `site/MOTION.md`. One rule is under test everywhere here:
// state commits synchronously and only pixels interpolate. Every wait is on
// `#top[data-motion="idle"]` or on an explicit attribute, never on a fixed sleep
// chosen to be "long enough" — the settled frame is observable, so waiting for it
// is deterministic. Page evaluation only reads state and geometry; all input is
// real click/tap/mouse.

test.afterEach(async ({ page }) => {
  try { await assertNoRuntimeErrors(page); }
  finally { await page.unrouteAll({ behavior: "wait" }); }
});

async function firstResults(page, count = 3) {
  const keys = await resultKeys(page);
  expect(keys.length, "the default context must list real members to interact with")
    .toBeGreaterThanOrEqual(count);
  return keys.slice(0, count);
}

async function newReducedContext(page, testInfo) {
  const use = testInfo.project.use;
  return page.context().browser().newContext({
    viewport: page.viewportSize(),
    userAgent: use.userAgent,
    deviceScaleFactor: use.deviceScaleFactor,
    isMobile: use.isMobile,
    hasTouch: use.hasTouch,
    reducedMotion: "reduce"
  });
}

// The exact same interaction burst, replayed in two contexts. Interruption is the
// point: nothing here waits for a tween to finish.
async function interruptBurst(page, testInfo, keys) {
  await tapOrClick(resultFor(page, keys[0]), testInfo);
  await page.waitForTimeout(60);
  await tapOrClick(await ensureVisible(page, "#gzoom-in"), testInfo);
  await page.waitForTimeout(40);
  await tapOrClick(resultFor(page, keys[1]), testInfo);
  await page.waitForTimeout(50);
  await tapOrClick(await ensureVisible(page, "#gzoom-out"), testInfo);
  await page.waitForTimeout(30);
  await tapOrClick(resultFor(page, keys[2]), testInfo);
}

async function beatSequence(page, testInfo, keys) {
  await tapOrClick(resultFor(page, keys[0]), testInfo);
  await expectMotionIdle(page);
  await tapOrClick(await ensureVisible(page, "#gzoom-in"), testInfo);
  await expectMotionIdle(page);
  await page.locator("#gsearch").click();
  await page.locator("#gsearch").fill("");
  await page.locator("#gsearch").pressSequentially("NDA", { delay: 65 });
  await expect(page.locator("#top")).toHaveAttribute("data-query", "NDA");
  await expectMotionIdle(page);
  await tapOrClick(page.locator("#goverview"), testInfo);
  await expectMotionIdle(page);
  await tapOrClick(page.locator("#gback"), testInfo);
  await expectMotionIdle(page);
  await tapOrClick(page.locator("#greset"), testInfo);
  await expectMotionIdle(page);
}

test.describe("graph motion acceptance", () => {
  test.beforeEach(async ({ page }) => { await openMotionWorkspace(page); });

  test("MOTION_COMMIT_SYNC datasets and label sizes are correct immediately after a click", async ({ page }, testInfo) => {
    const [key] = await firstResults(page, 1);
    const expectedName = await page.locator(`.g-node[data-key="${key.replace(/["\\]/g, "\\$&")}"]`)
      .evaluate((el) => el.dataset.name);
    expect(expectedName, "the clicked member must have a real name").toBeTruthy();
    await resetProbe(page);
    await tapOrClick(resultFor(page, key), testInfo);
    // Zero wait: the very next round trip reads the committed truth.
    const immediate = await sampleMotionFrame(page);
    const immediateSnapshot = await motionSnapshot(page);
    expect(immediate.selected, "MOTION_COMMIT_SYNC: selection is committed before any tween").toBe(key);
    expect(immediate.mode, "MOTION_COMMIT_SYNC: mode is committed before any tween").toBe("node");
    expect(immediate.query, "MOTION_COMMIT_SYNC: query is untouched by a selection").toBe("");
    expect(immediate.title, "MOTION_COMMIT_SYNC: the title names the new context immediately")
      .toContain(expectedName);
    expect(Number(immediateSnapshot.top.matchingCount),
      "MOTION_COMMIT_SYNC: counts are committed immediately").toBeGreaterThan(0);
    expect(Number(immediateSnapshot.top.visibleCount),
      "MOTION_COMMIT_SYNC: counts are committed immediately").toBeGreaterThan(0);
    expect(immediate.labelCount,
      "MOTION_COMMIT_SYNC: labels for the final layout exist on the committing frame").toBeGreaterThan(0);
    expect(immediate.tiny,
      "MOTION_COMMIT_SYNC: every visible label is >=16 CSS px (font size x screen CTM) with no wait").toEqual([]);
    await expectMotionIdle(page);
    const settled = await motionSnapshot(page);
    expect(settled.top, "MOTION_COMMIT_SYNC: the settled datasets equal the immediate ones")
      .toEqual(immediateSnapshot.top);
    expect(settled.title).toEqual(immediateSnapshot.title);
    const probe = await readProbe(page);
    expect(motionEpisodes(probe.motionLog).length,
      "non-vacuity: this beat must actually have animated, otherwise nothing was raced")
      .toBeGreaterThan(0);
    await saveEvidence(page, testInfo, "motion-commit-sync",
      { key, immediate, immediateSnapshot, settled, motionLog: probe.motionLog });
  });

  test("MOTION_LABEL_FLOOR labels never drop below 16 CSS px across a whole transition", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    await tapOrClick(page.locator("#goverview"), testInfo);
    await expectMotionIdle(page);
    const [key] = await firstResults(page, 1);
    await resetProbe(page);
    await tapOrClick(resultFor(page, key), testInfo);
    const samples = [];
    const deadline = Date.now() + 4000;
    let sawRunning = false, settledSamples = 0;
    while (Date.now() < deadline) {
      const sample = await sampleMotionFrame(page);
      samples.push(sample);
      if (sample.motion === "running") sawRunning = true;
      if (sample.motion === "idle" && sawRunning) settledSamples++;
      if (settledSamples >= 2) break;
    }
    const during = samples.filter((s) => s.motion === "running");
    expect(sawRunning,
      "non-vacuity: a context change must animate, otherwise nothing was sampled mid-flight").toBe(true);
    expect(during.length,
      "non-vacuity: the sampler must catch several in-flight frames").toBeGreaterThanOrEqual(3);
    expect(samples.every((s) => s.labelCount > 0),
      "non-vacuity: labels must be placed throughout the transition").toBe(true);
    const tiny = samples.flatMap((s) => s.tiny.map((label) =>
      ({ ...label, at: s.t, motion: s.motion })));
    expect(tiny,
      "MOTION_LABEL_FLOOR: no label may drop below 16 CSS px at any point in a transition").toEqual([]);
    // A 16px computed font size on an invisible label proves nothing. Labels must
    // be effectively visible (no display/visibility loss and no ancestor opacity
    // at or below 0.05) on every sampled in-flight frame, and the smallest of
    // those actually-visible labels must still measure at least 16 CSS px.
    const blankFrames = during.filter((s) => s.paintedLabelCount === 0)
      .map((s) => ({ at: s.t, revealed: s.revealed, placed: s.labelCount }));
    expect(blankFrames,
      "MOTION_LABEL_FLOOR: the label layer must stay visible during the flight, not blank out").toEqual([]);
    const tinyPainted = during.flatMap((s) => s.tinyPainted.map((label) =>
      ({ ...label, at: s.t })));
    expect(tinyPainted,
      "MOTION_LABEL_FLOOR: every visible label stays at or above 16 CSS px in flight").toEqual([]);
    await saveEvidence(page, testInfo, "motion-label-floor", { key, sampleCount: samples.length,
      inFlightSamples: during.length, minCssPx: Math.min(...samples.map((s) => s.minCssPx ?? Infinity)),
      minPaintedInFlight: Math.min(...during.map((s) => s.minPaintedCssPx ?? Infinity)),
      minPaintedCountInFlight: Math.min(...during.map((s) => s.paintedLabelCount)), samples });
  });

  test("MOTION_CAMERA_TRAVEL the camera actually travels and lands on the committed view", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    // View state may move per frame; semantic state may not. This watches the
    // pixels: successive in-flight readings of the viewport's screen CTM must
    // differ by more than a pixel of real displacement (or a real scale change),
    // and the last reading must equal the committed camera on `#vp`.
    const [key] = await firstResults(page, 1);
    await resetProbe(page);
    await tapOrClick(resultFor(page, key), testInfo);
    const samples = [];
    const deadline = Date.now() + 5000;
    let sawRunning = false, settled = 0;
    while (Date.now() < deadline) {
      const sample = await sampleCamera(page);
      samples.push(sample);
      if (sample.motion === "running") sawRunning = true;
      if (sample.motion === "idle" && sawRunning) settled++;
      if (settled >= 2) break;
    }
    const during = samples.filter((s) => s.motion === "running");
    expect(sawRunning, "non-vacuity: the context change must animate").toBe(true);
    expect(during.length,
      "non-vacuity: the sampler must catch several in-flight camera frames").toBeGreaterThanOrEqual(3);
    const steps = during.slice(1).map((sample, index) => ({
      at: sample.t, ...cameraDisplacement(during[index], sample) }));
    const moved = steps.filter((step) => step.distance > 1 || Math.abs(step.dScale) > 0.002);
    expect(moved.length,
      "MOTION_CAMERA_TRAVEL: successive in-flight camera readings must differ by real displacement")
      .toBeGreaterThan(0);
    const travel = cameraDisplacement(during[0], during[during.length - 1]);
    expect(travel.distance > 1 || Math.abs(travel.dScale) > 0.002,
      "MOTION_CAMERA_TRAVEL: the camera must visibly move across the flight, not jump instantly").toBe(true);
    await expectMotionIdle(page);
    const end = await sampleCamera(page);
    const expected = `translate(${end.target.x} ${end.target.y}) scale(${end.target.scale})`;
    expect(end.transform,
      "MOTION_CAMERA_TRAVEL: the settled camera must equal the committed target exactly").toBe(expected);
    const drift = cameraDisplacement(during[during.length - 1], end);
    await saveEvidence(page, testInfo, "motion-camera-travel", { key, samples: samples.length,
      inFlight: during.length, steps, travel, drift, end });
  });

  test("MOTION_EDGE_CONTINUITY the network never disappears mid-transition", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    // Pick a member that actually has relationships, or there is no network to
    // lose. The in-flight stand-in path counts as structure; nothing does not.
    const keys = await resultKeys(page);
    const connected = await page.evaluate((candidates) => candidates.find((key) => {
      const node = document.querySelector(`.g-node[data-key="${CSS.escape(key)}"]`);
      return node && Number(node.dataset.deg) > 0;
    }) ?? null, keys);
    expect(connected, "non-vacuity: the context must contain a connected member").toBeTruthy();
    const settledBefore = await sampleMotionFrame(page);
    expect(settledBefore.edges.structure,
      "non-vacuity: the settled scene must show edge structure before the transition").toBe(true);
    await resetProbe(page);
    await tapOrClick(resultFor(page, connected), testInfo);
    const samples = [];
    const deadline = Date.now() + 4000;
    let sawRunning = false, settledSamples = 0;
    while (Date.now() < deadline) {
      const sample = await sampleMotionFrame(page);
      samples.push(sample);
      if (sample.motion === "running") sawRunning = true;
      if (sample.motion === "idle" && sawRunning) settledSamples++;
      if (settledSamples >= 2) break;
    }
    const during = samples.filter((s) => s.motion === "running");
    expect(sawRunning, "non-vacuity: the transition must actually animate").toBe(true);
    expect(during.length,
      "non-vacuity: the sampler must catch several in-flight frames").toBeGreaterThanOrEqual(3);
    const blank = during.filter((s) => !s.edges.structure)
      .map((s) => ({ at: s.t, drawn: s.edges.drawn, flight: s.edges.flight }));
    expect(blank,
      "MOTION_EDGE_CONTINUITY: visible edge structure must exist on every in-flight frame").toEqual([]);
    const settledAfter = samples[samples.length - 1];
    expect(settledAfter.edges.structure,
      "MOTION_EDGE_CONTINUITY: the settled scene must show its edges again").toBe(true);
    await saveEvidence(page, testInfo, "motion-edge-continuity", { key: connected,
      settledBefore: settledBefore.edges, inFlight: during.map((s) => ({ at: s.t, edges: s.edges })),
      settledAfter: settledAfter.edges });
  });

  test("MOTION_POINTER_IMMUNITY a pointer sweep during a transition cannot move selection", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    const keys = await firstResults(page, 2);
    await tapOrClick(resultFor(page, keys[0]), testInfo);
    await expectMotionIdle(page);
    await resetProbe(page);
    await tapOrClick(resultFor(page, keys[1]), testInfo);
    const before = await sampleMotionFrame(page);
    expect(before.selected).toBe(keys[1]);
    const graph = await page.locator("#gsvg").boundingBox();
    const targets = await page.locator(".g-node").evaluateAll((nodes, selected) => nodes.flatMap((n) => {
      const box = n.getBoundingClientRect(), style = getComputedStyle(n);
      if (n.dataset.key === selected || n.dataset.visible !== "true" || !box.width || !box.height ||
        style.display === "none" || style.visibility === "hidden") return [];
      return [{ key: n.dataset.key, x: box.x + box.width / 2, y: box.y + box.height / 2 }];
    }), keys[1]);
    const reachable = targets.filter((p) => p.x > graph.x && p.x < graph.x + graph.width &&
      p.y > graph.y && p.y < graph.y + graph.height).slice(0, 8);
    expect(reachable.length,
      "non-vacuity: the sweep must cross actual other painted dots").toBeGreaterThan(0);
    const sweepSamples = [];
    for (const point of reachable) {
      await page.mouse.move(point.x, point.y, { steps: 5 });
      sweepSamples.push(await sampleMotionFrame(page));
    }
    expect(sweepSamples.some((s) => s.motion === "running"),
      "non-vacuity: the pointer must have crossed dots while a tween was in flight").toBe(true);
    await expectMotionIdle(page);
    const after = await sampleMotionFrame(page);
    for (const sample of [...sweepSamples, after]) {
      expect(sample.selected,
        "MOTION_POINTER_IMMUNITY: pointer travel during a transition must not change selection").toBe(before.selected);
      expect(sample.query,
        "MOTION_POINTER_IMMUNITY: pointer travel during a transition must not change the query").toBe(before.query);
      expect(sample.title,
        "MOTION_POINTER_IMMUNITY: pointer travel during a transition must not change the title").toBe(before.title);
      expect(sample.mode,
        "MOTION_POINTER_IMMUNITY: pointer travel during a transition must not change the mode").toBe(before.mode);
    }
    await saveEvidence(page, testInfo, "motion-pointer-immunity",
      { before, after, crossed: reachable.map((p) => p.key), sweepSamples });
  });

  test("MOTION_INTERRUPTIBLE rapid interrupting interactions land on the instant result", async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const keys = await firstResults(page, 3);
    const origin = new URL(page.url()).origin;
    await resetProbe(page);
    await interruptBurst(page, testInfo, keys);
    await expectMotionIdle(page);
    const animated = await motionSnapshot(page);
    const probe = await readProbe(page);
    expect(motionEpisodes(probe.motionLog).length,
      "non-vacuity: the interrupted burst must actually have animated").toBeGreaterThan(0);

    const context = await newReducedContext(page, testInfo);
    let reduced;
    try {
      const reducedPage = await openMotionPage(context, origin);
      const reducedKeys = await resultKeys(reducedPage);
      expect(reducedKeys.slice(0, 3),
        "the reduced-motion reference must start from the same context").toEqual(keys);
      await interruptBurst(reducedPage, testInfo, keys);
      await expectMotionIdle(reducedPage);
      reduced = await motionSnapshot(reducedPage);
    } finally { await context.close(); }

    expect(comparableSnapshot(animated).vp,
      "MOTION_INTERRUPTIBLE: the settled #vp transform must equal the instant result").toEqual(reduced.vp);
    expect(comparableSnapshot(animated).nodes,
      "MOTION_INTERRUPTIBLE: settled dot positions must equal the instant result").toEqual(reduced.nodes);
    expect(comparableSnapshot(animated).top,
      "MOTION_INTERRUPTIBLE: settled #top datasets must equal the instant result").toEqual(reduced.top);
    expect(animated.title,
      "MOTION_INTERRUPTIBLE: the settled title must equal the instant result").toEqual(reduced.title);
    await saveEvidence(page, testInfo, "motion-interruptible", { keys, animated, reduced });
  });

  test("MOTION_REDUCED_MOTION no animation frames run and the end state matches", async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const keys = await firstResults(page, 3);
    const origin = new URL(page.url()).origin;
    await resetProbe(page);
    await beatSequence(page, testInfo, keys);
    const animatedEnd = await motionSnapshot(page);
    const animatedProbe = await readProbe(page);
    expect(animatedProbe.rafSince,
      "non-vacuity: with motion allowed the workspace must actually run animation frames").toBeGreaterThan(0);
    expect(animatedProbe.motionLog.some((entry) => entry.value === "running"),
      "non-vacuity: with motion allowed data-motion must go running").toBe(true);

    const context = await newReducedContext(page, testInfo);
    let reducedEnd, reducedProbe, ambientWhileSelected;
    try {
      const reducedPage = await openMotionPage(context, origin);
      await resetProbe(reducedPage);
      await beatSequence(reducedPage, testInfo, keys);
      reducedEnd = await motionSnapshot(reducedPage);
      reducedProbe = await readProbe(reducedPage);
      await tapOrClick(resultFor(reducedPage, keys[0]), testInfo);
      await expectMotionIdle(reducedPage);
      ambientWhileSelected = await reducedPage.locator("[data-ambient]").count();
    } finally { await context.close(); }

    expect(reducedProbe.rafSince,
      "MOTION_REDUCED_MOTION: no animation frame may run under prefers-reduced-motion").toBe(0);
    expect(reducedProbe.motionLog.filter((entry) => entry.value === "running"),
      "MOTION_REDUCED_MOTION: data-motion must stay idle under prefers-reduced-motion").toEqual([]);
    expect(ambientWhileSelected,
      "MOTION_REDUCED_MOTION: the ambient breath never runs under reduced motion").toBe(0);
    expect(comparableSnapshot(reducedEnd),
      "MOTION_REDUCED_MOTION: the instant end state must equal the animated end state")
      .toEqual(comparableSnapshot(animatedEnd));
    await saveEvidence(page, testInfo, "motion-reduced", { animatedEnd, reducedEnd,
      animatedFrames: animatedProbe.rafSince, reducedFrames: reducedProbe.rafSince,
      reducedMotionLog: reducedProbe.motionLog });
  });

  test("MOTION_IDLE_RETURN data-motion returns to idle within 900ms of every beat", async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    const keys = await firstResults(page, 2);
    await resetProbe(page);
    const beats = [];
    async function beat(name, action) {
      await resetProbe(page);
      await action();
      await expectMotionIdle(page, 5000);
      const probe = await readProbe(page);
      const episodes = motionEpisodes(probe.motionLog);
      // A beat that is re-triggered (each committed keystroke of a query is its
      // own beat) restarts the clock. The bound is "within 900ms of a beat", so
      // measure from the last beat this action committed to the settling idle.
      const beatWrites = probe.motionLog.filter((e) => e.attr === "data-motion-beat");
      const lastBeatAt = beatWrites.length ? beatWrites[beatWrites.length - 1].t
        : (episodes.length ? episodes[episodes.length - 1].start : null);
      const idleWrites = probe.motionLog.filter((e) => e.attr === "data-motion" && e.value === "idle");
      const settledAt = idleWrites.length ? idleWrites[idleWrites.length - 1].t : null;
      beats.push({ name, episodes, beatNames: beatWrites.map((e) => e.value),
        settleAfterLastBeatMs: lastBeatAt !== null && settledAt !== null && settledAt >= lastBeatAt
          ? settledAt - lastBeatAt : null });
    }
    await beat("context-select", () => tapOrClick(resultFor(page, keys[0]), testInfo));
    await beat("camera-zoom", async () => tapOrClick(await ensureVisible(page, "#gzoom-in"), testInfo));
    await beat("search", async () => {
      await page.locator("#gsearch").click();
      await page.locator("#gsearch").fill("");
      await page.locator("#gsearch").pressSequentially("NDA", { delay: 65 });
      await expect(page.locator("#top")).toHaveAttribute("data-query", "NDA");
    });
    await beat("overview", () => tapOrClick(page.locator("#goverview"), testInfo));
    await beat("back", () => tapOrClick(page.locator("#gback"), testInfo));
    await beat("reset", () => tapOrClick(page.locator("#greset"), testInfo));
    const animated = beats.filter((b) => b.episodes.length > 0);
    expect(animated.length,
      "non-vacuity: most beats must actually animate for this bound to mean anything")
      .toBeGreaterThanOrEqual(4);
    expect(animated.every((b) => b.settleAfterLastBeatMs !== null),
      "every animated beat must actually settle back to idle").toBe(true);
    const slow = animated
      .filter((b) => !(b.settleAfterLastBeatMs <= 900))
      .map((b) => ({ beat: b.name, settleAfterLastBeatMs: b.settleAfterLastBeatMs }));
    expect(slow,
      "MOTION_IDLE_RETURN: data-motion must return to idle within 900ms of every beat").toEqual([]);
    await saveEvidence(page, testInfo, "motion-idle-return", { beats });
  });

  test("MOTION_LONG_TASK no long task exceeds 120ms during a community to node transition", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    await tapOrClick(page.locator("#goverview"), testInfo);
    await expectMotionIdle(page);
    const overview = await motionSnapshot(page);
    expect(Number(overview.top.visibleCount),
      "non-vacuity: the overview transition must move a heavy scene").toBeGreaterThan(100);
    const [key] = await firstResults(page, 1);
    await resetProbe(page);
    await tapOrClick(resultFor(page, key), testInfo);
    // One cheap read while the beat is in flight: real motion primitives must be
    // running on real graph geometry. An attribute flip with nothing animating,
    // or frames that paint nothing, cannot satisfy this.
    const inFlight = await page.evaluate(() => ({
      motion: document.getElementById("top").dataset.motion ?? null,
      running: document.getAnimations()
        .filter((animation) => animation.playState === "running")
        .map((animation) => {
          const target = animation.effect?.target;
          return { kind: animation.constructor.name,
            property: animation.transitionProperty ?? animation.animationName ?? null,
            target: target ? `${target.tagName}.${target.getAttribute("class") || target.id || ""}` : null };
        })
    }));
    await expectMotionIdle(page);
    const probe = await readProbe(page);
    expect(probe.longTaskSupported,
      "non-vacuity: the long task observer must be available, or this proves nothing").toBe(true);
    // Non-vacuity without prescribing a technique: this beat must really have
    // animated. A CSS-transition beat runs no rAF callbacks at all, so the
    // observable is `data-motion` going running, with frames reported as
    // evidence rather than required.
    const episodes = motionEpisodes(probe.motionLog);
    expect(episodes.length,
      "non-vacuity: the measured window must contain a real animation").toBeGreaterThan(0);
    expect(inFlight.motion,
      "non-vacuity: the beat must still have been in flight when it was sampled").toBe("running");
    expect(probe.rafSince > 0 || inFlight.running.length > 0,
      "non-vacuity: real animations (frames or running CSS transitions) must be in flight").toBe(true);
    // Attribute each long task: one that contains the synchronous commit is the
    // render, one that lands later is the tween. Both are contract violations,
    // but the diagnosis belongs in the evidence.
    const commitAt = probe.motionLog.find((entry) => entry.value === "running")?.t ?? null;
    const long = probe.longTasks.filter((task) => task.duration > 120).map((task) => ({
      ...task, containsCommit: commitAt !== null && task.start <= commitAt && commitAt <= task.start + task.duration }));
    expect(long,
      "MOTION_LONG_TASK: no long task over 120ms during a community to node transition").toEqual([]);
    await saveEvidence(page, testInfo, "motion-long-task", { key, longTasks: probe.longTasks,
      frames: probe.rafSince, episodes, inFlight, commitAt, overviewVisible: overview.top.visibleCount });
  });

  test("MOTION_AMBIENT_SINGLETON exactly one ambient element while a skill is selected", async ({ page }, testInfo) => {
    test.setTimeout(60_000);
    await expect(page.locator("[data-ambient]"),
      "MOTION_AMBIENT_SINGLETON: nothing is selected, so nothing may breathe").toHaveCount(0);
    const [key] = await firstResults(page, 1);
    await tapOrClick(resultFor(page, key), testInfo);
    await expectMotionIdle(page);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", key);
    await expect(page.locator("[data-ambient]"),
      "MOTION_AMBIENT_SINGLETON: exactly one ambient element animates for the selected dot").toHaveCount(1);
    const ambient = await page.locator("[data-ambient]").evaluate((el) => {
      const owner = el.closest(".g-node") || el;
      return { key: owner.dataset.key ?? null,
        animations: el.getAnimations({ subtree: true }).length,
        transform: getComputedStyle(el).transform, opacity: getComputedStyle(el).opacity };
    });
    expect(ambient.key,
      "MOTION_AMBIENT_SINGLETON: the ambient element belongs to the selected dot").toBe(key);
    const later = await page.locator("[data-ambient]").evaluate((el) =>
      new Promise((resolve) => setTimeout(() => resolve({
        transform: getComputedStyle(el).transform, opacity: getComputedStyle(el).opacity }), 320)));
    expect(ambient.animations > 0 || later.transform !== ambient.transform || later.opacity !== ambient.opacity,
      "MOTION_AMBIENT_SINGLETON: the single ambient element must actually animate").toBe(true);
    await tapOrClick(page.locator("#greset"), testInfo);
    await expectMotionIdle(page);
    await expect(page.locator("#top")).toHaveAttribute("data-selected-key", "");
    await expect(page.locator("[data-ambient]"),
      "MOTION_AMBIENT_SINGLETON: the breath stops when nothing is selected").toHaveCount(0);
    await saveEvidence(page, testInfo, "motion-ambient", { key, ambient, later });
  });
});
