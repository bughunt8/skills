/* Static graph workspace. Context changes only through deliberate user actions.
 * The build owns identity, evidence, communities and the complete text library.
 * Geometry and screen-space labels have independent transforms.
 * The motion layer interpolates pixels only: state commits synchronously before
 * the first animation frame runs. See MOTION.md for the binding contract.
 */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const data = window.SKILLDATA;
  if (!data || !data.nodes || !$("top")) return;
  const root = $("top"), svg = $("gsvg"), vp = $("vp");
  const search = $("gsearch"), results = $("gresults");
  const ns = "http://www.w3.org/2000/svg";
  const nodes = new Map(), cards = new Map(), solutions = new Map();
  const communities = new Map(data.comms.map((c) => [String(c.id), c]));
  const labels = new Map();
  const edgeElements = [...svg.querySelectorAll(".g-edge")];
  const communityLabels = [...svg.querySelectorAll(".g-clabel")];
  document.querySelectorAll(".card").forEach((el) => cards.set(el.dataset.id, el));
  document.querySelectorAll(".sol").forEach((el) => solutions.set(el.dataset.sol, {
    label: el.querySelector("h3").textContent,
    tier: el.dataset.tier,
    evidence: el.querySelector(".sol__ev").textContent,
    members: [...el.querySelectorAll(".sol__step")].map((s) => s.dataset.id),
  }));
  svg.querySelectorAll(".g-nlabel").forEach((el) => labels.set(el.dataset.key, el));
  svg.querySelectorAll(".g-node").forEach((el) => {
    const key = el.dataset.key, card = cards.get(key);
    const description = card.querySelector("p").textContent;
    nodes.set(key, {
      key, el, card, name: el.dataset.name, description,
      text: `${el.dataset.name} ${description}`.toLocaleLowerCase(),
      words: `${el.dataset.name} ${description}`.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [],
      community: el.dataset.comm, category: el.dataset.dom,
      degree: Number(el.dataset.deg), x: Number(el.dataset.x), y: Number(el.dataset.y),
      dot: el.querySelector(".g-dot"), hit: el.querySelector(".g-hit"),
      radius: Number(el.querySelector(".g-dot").getAttribute("r")),
      source: card.querySelector("footer a").href,
      repo: card.querySelector("footer a").textContent,
      licence: card.querySelector(".lic").textContent,
    });
    // The native member buttons are the keyboard/touch interface, not microscopic dots.
    el.setAttribute("tabindex", "-1");
  });
  const adjacency = new Map(data.nodes.map((key) => [key, []]));
  const edges = data.edges.map((e, i) => {
    const item = {a: data.nodes[e[0]], b: data.nodes[e[1]], kind: e[3], index: i};
    adjacency.get(item.a).push({to: item.b, edge: item});
    adjacency.get(item.b).push({to: item.a, edge: item});
    return item;
  });
  adjacency.forEach((items) => items.sort((a, b) => a.to.localeCompare(b.to)));
  const initial = () => ({
    mode: "community", selected: "", query: "", community: String(data.comms[0].id),
    listKind: "community", filters: {community: "", category: "", solution: "", stated: false},
    viewport: {k: 1, x: 0, y: 0}, pathStart: "", pathEnd: "", path: [], pathPending: false,
    searchOrigin: null,
  });
  let state = initial(), history = [], size = {w: 1, h: 1};
  let scene = new Map(), sceneKeys = [], listKeys = [], activeEdges = [];
  let listSignature = "", suppressClick = false;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const text = (id, value) => { $(id).textContent = value; };
  const allowedEdge = (edge) => !state.filters.stated || edge.kind === 0;
  const neighbors = (key) => adjacency.get(key).filter((entry) => allowedEdge(entry.edge));
  const save = () => {
    history.push(clone(state));
    if (history.length > 40) history.shift();
  };
  const ranked = (keys) => [...keys].sort((a, b) =>
    nodes.get(b).degree - nodes.get(a).degree || nodes.get(a).name.localeCompare(nodes.get(b).name) ||
    a.localeCompare(b));

  function matches(node) {
    const f = state.filters;
    if (f.community && node.community !== f.community) return false;
    if (f.category && node.category !== f.category) return false;
    if (f.solution) {
      const solution = solutions.get(f.solution);
      if (!solution.members.includes(node.key) && node.key !== f.solution) return false;
    }
    const terms = state.query.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
    return terms.every((term) => {
      // Short queries use word starts: NDA must not match staNDArds or ageNDAs.
      if (term === "nda" && /non[\s-]?disclosure/.test(node.text)) return true;
      return term.length <= 3 ? node.words.some((word) => word.startsWith(term)) : node.text.includes(term);
    });
  }

  function getListKeys() {
    let keys = [...nodes.keys()].filter((key) => matches(nodes.get(key)));
    if (!state.query.trim() && state.listKind === "community") {
      keys = keys.filter((key) => nodes.get(key).community === state.community);
    }
    if (state.query.trim()) {
      const query = state.query.trim().toLocaleLowerCase();
      const score = (key) => {
        const name = nodes.get(key).name.toLocaleLowerCase();
        return name === query ? 0 : name.startsWith(query) ? 1 : name.includes(query) ? 2 : 3;
      };
      return keys.sort((a, b) => score(a) - score(b) || nodes.get(a).name.localeCompare(nodes.get(b).name) ||
        a.localeCompare(b));
    }
    return ranked(keys);
  }

  function shortestPath(start, end) {
    if (!nodes.has(start) || !nodes.has(end)) return [];
    const queue = [start], previous = new Map([[start, null]]);
    for (let i = 0; i < queue.length; i++) {
      const key = queue[i];
      if (key === end) {
        const path = [];
        for (let at = end; at !== null; at = previous.get(at)) path.push(at);
        return path.reverse();
      }
      for (const item of neighbors(key)) {
        if (previous.has(item.to)) continue;
        previous.set(item.to, key);
        queue.push(item.to);
      }
    }
    return [];
  }

  function prepareScene() {
    listKeys = getListKeys();
    let keys = listKeys;
    if (state.mode === "node" && state.selected) {
      keys = [state.selected, ...neighbors(state.selected).map((item) => item.to)];
    } else if (state.mode === "path") {
      keys = state.path.length ? state.path : [state.pathStart, state.pathEnd].filter(Boolean);
    }
    sceneKeys = [...new Set(keys)];
    const included = new Set(sceneKeys);
    scene = new Map(sceneKeys.map((key) => [key, {x: nodes.get(key).x, y: nodes.get(key).y}]));
    // A local neighborhood is a fresh deterministic radial layout, not a capped zoom
    // into distant clusters. Original identity and edge evidence are untouched.
    if (state.mode === "node") {
      scene.set(state.selected, {x: 0, y: 0});
      const others = ranked(sceneKeys.filter((key) => key !== state.selected));
      others.forEach((key, i) => {
        const ring = Math.floor(i / 12), count = Math.min(12, others.length - ring * 12);
        const angle = -Math.PI / 2 + (i % 12) * Math.PI * 2 / count + ring * 0.16;
        const radius = 115 + ring * 105;
        scene.set(key, {x: Math.cos(angle) * radius, y: Math.sin(angle) * radius});
      });
    }
    if (state.mode === "path" && state.path.length) {
      state.path.forEach((key, i) => scene.set(key, {x: i * 130, y: (i % 2) * 65}));
    }
    const pathPairs = new Set(state.path.slice(1).map((key, i) =>
      [state.path[i], key].sort().join("|")));
    activeEdges = edges.filter((edge) =>
      included.has(edge.a) && included.has(edge.b) && allowedEdge(edge) &&
      (state.mode !== "path" || pathPairs.has([edge.a, edge.b].sort().join("|"))));
    const edgeIds = new Set(activeEdges.map((edge) => edge.index));
    edgeElements.forEach((el) => { el.style.display = edgeIds.has(Number(el.dataset.i)) ? "" : "none"; });
    activeEdges.forEach((edge) => {
      const a = scene.get(edge.a), b = scene.get(edge.b);
      const mx = (a.x + b.x) / 2 + (b.y - a.y) * .075;
      const my = (a.y + b.y) / 2 - (b.x - a.x) * .075;
      edgeElements[edge.index].setAttribute("d", `M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`);
    });
    nodes.forEach((node, key) => {
      const show = included.has(key);
      node.el.style.display = show ? "" : "none";
      node.el.dataset.inContext = String(show);
      node.el.classList.toggle("is-selected", key === state.selected);
      if (!show) return;
      const point = scene.get(key);
      [node.dot, node.hit].forEach((el) => {
        el.setAttribute("cx", point.x);
        el.setAttribute("cy", point.y);
      });
      node.el.dataset.renderX = point.x;
      node.el.dataset.renderY = point.y;
    });
    $("graph-empty").hidden = sceneKeys.length > 0;
  }

  function fit() {
    if (!sceneKeys.length) {
      state.viewport = {k: 1, x: size.w / 2, y: size.h / 2};
      return;
    }
    const points = [...scene.values()];
    const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
    const left = Math.min(...xs), right = Math.max(...xs);
    const top = Math.min(...ys), bottom = Math.max(...ys);
    const padX = Math.min(72, size.w * .14), padY = Math.min(72, size.h * .18);
    const k = Math.max(.08, Math.min(30,
      (size.w - padX * 2) / Math.max(80, right - left),
      (size.h - padY * 2) / Math.max(80, bottom - top)));
    state.viewport = {k, x: size.w / 2 - (left + right) / 2 * k,
      y: size.h / 2 - (top + bottom) / 2 * k};
  }

  const measure = document.createElement("canvas").getContext("2d");
  function labelLines(name, maxWidth, fontSize, weight = 500) {
    measure.font = `${weight} ${fontSize}px Inter, sans-serif`;
    if (measure.measureText(name).width <= maxWidth) return [name];
    // Prefer the skill's own hyphens/spaces, retaining every character. Break a
    // word only when it cannot fit on a line by itself; never truncate a name.
    const lines = []; let line = "";
    for (const word of name.match(/[^-\s]+[-\s]*|[-\s]+/g) || [name]) {
      if (line && measure.measureText(line + word).width > maxWidth) {
        lines.push(line); line = "";
      }
      for (const character of word) {
        if (line && measure.measureText(line + character).width > maxWidth) {
          lines.push(line); line = "";
        }
        line += character;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const selectedLeader = document.createElementNS(ns, "path");
  selectedLeader.id = "selected-label-leader";
  $("graph-labels").prepend(selectedLeader);

  function drawLabels() {
    labels.forEach((label) => { label.style.display = "none"; });
    communityLabels.forEach((label) => { label.style.display = "none"; });
    $("graph-labels").querySelectorAll(".g-label-leader").forEach((line) => line.remove());
    selectedLeader.style.display = "none";
    const reserved = [], k = state.viewport.k;
    const dots = sceneKeys.map((key) => {
      const point = scene.get(key), node = nodes.get(key);
      const x = point.x * k + state.viewport.x, y = point.y * k + state.viewport.y;
      const radius = Number(node.dot.getAttribute("r")) * k;
      return {key, x: x - radius, y: y - radius, w: radius * 2, h: radius * 2};
    }).filter((box) => box.x + box.w >= 0 && box.x <= size.w && box.y + box.h >= 0 && box.y <= size.h);
    const intersects = (a, b) => a.x < b.x + b.w + 8 && a.x + a.w + 8 > b.x &&
      a.y < b.y + b.h + 6 && a.y + a.h + 6 > b.y;
    function place(label, name, px, py, selected = false, community = false) {
      const font = selected ? 18 : 16;
      let lines = labelLines(name, Math.max(90, Math.min(selected ? 340 : 250, size.w - 32)),
        font, selected ? 650 : 500);
      let width = Math.max(...lines.map((line) => measure.measureText(line).width));
      let height = lines.length * (font + 4);
      const positions = community ?
        [[px - width / 2, py - height / 2], [px - width / 2, py - height - 18]] :
        [[px + 26, py - height / 2], [px - width - 26, py - height / 2],
          [px - width / 2, py + 26], [px - width / 2, py - height - 26]];
      // Try progressively offset callouts rather than painting a name over a
      // different skill's dot. Priority comes from graph degree, not a hard cap.
      for (const distance of [64, 112, 176, 248]) {
        positions.push([px + distance, py - height / 2], [px - width - distance, py - height / 2],
          [px - width / 2, py + distance], [px - width / 2, py - height - distance]);
      }
      let box = positions.map(([x, y]) => ({x, y, w: width, h: height}))
        .find((candidate) => candidate.x >= 12 && candidate.y >= 10 &&
          candidate.x + candidate.w <= size.w - 12 && candidate.y + candidate.h <= size.h - 10 &&
          !reserved.some((other) => intersects(candidate, other)) &&
          !dots.some((dot) => intersects(candidate, dot)));
      if (!box && selected) {
        // Search the whole canvas at obstacle boundaries, including the outer
        // gutters. Coarse rows can miss a valid strip just above/below the dots.
        // Try narrower wrapping too, without shrinking type or losing text.
        let best = null;
        for (const limit of [...new Set([Math.min(340, size.w - 32), 240, 180, 120, 90])]) {
          const wrapped = labelLines(name, Math.min(limit, size.w - 16), font, 650);
          const w = Math.max(...wrapped.map((line) => measure.measureText(line).width));
          const h = wrapped.length * (font + 4);
          if (w > size.w - 16 || h > size.h - 12) continue;
          const xs = [...new Set([8, size.w - w - 8, px - w / 2,
            ...dots.flatMap((dot) => [dot.x - w - 9, dot.x + dot.w + 9])]
            .map((x) => clamp(x, 8, size.w - w - 8)))];
          const ys = [...new Set([6, size.h - h - 6, py - h / 2,
            ...dots.flatMap((dot) => [dot.y - h - 7, dot.y + dot.h + 7])]
            .map((y) => clamp(y, 6, size.h - h - 6)))];
          for (const y of ys) {
            for (const x of xs) {
              const candidate = {x, y, w, h};
              if (dots.some((dot) => intersects(candidate, dot)) ||
                  reserved.some((other) => intersects(candidate, other))) continue;
              const distance = Math.hypot(px - clamp(px, x, x + w), py - clamp(py, y, y + h));
              if (!best || distance < best.distance) best = {box: candidate, lines: wrapped, distance};
            }
          }
        }
        if (best) {
          box = best.box; lines = best.lines; width = box.w; height = box.h;
        }
      }
      if (!box) return false;
      label.replaceChildren();
      label.setAttribute("x", box.x);
      label.setAttribute("y", box.y + font);
      label.setAttribute("text-anchor", "start");
      label.style.fontSize = `${font}px`;
      label.style.display = "";
      label.classList.toggle("is-selected", selected);
      lines.forEach((line, i) => {
        const span = document.createElementNS(ns, "tspan");
        span.setAttribute("x", box.x);
        span.setAttribute("dy", i ? font + 4 : 0);
        span.textContent = line;
        label.appendChild(span);
      });
      reserved.push(box);
      // The scene-space anchor and the placed box let the motion layer carry this
      // label with its own dot in flight without ever rescaling the text.
      const anchorScene = {x: (px - state.viewport.x) / k, y: (py - state.viewport.y) / k};
      Object.assign(label.dataset, {sceneX: String(anchorScene.x), sceneY: String(anchorScene.y),
        boxX: String(box.x), boxY: String(box.y), boxW: String(width), boxH: String(height)});
      if (!community) {
        const offscreen = px < 0 || px > size.w || py < 0 || py > size.h;
        Object.assign(label.dataset, {anchorX: String(px), anchorY: String(py), offscreen: String(offscreen)});
        let sx = clamp(px, 5, size.w - 5), sy = clamp(py, 5, size.h - 5);
        const tx = clamp(sx, box.x, box.x + width), ty = clamp(sy, box.y, box.y + height);
        const node = nodes.get(label.dataset.key), distance = Math.hypot(tx - sx, ty - sy);
        if (!offscreen && distance && node) {
          const radius = Number(node.dot.getAttribute("r")) * k;
          sx += (tx - sx) / distance * radius; sy += (ty - sy) / distance * radius;
        }
        const leader = selected ? selectedLeader : document.createElementNS(ns, "path");
        if (!selected) {
          leader.setAttribute("class", "g-label-leader");
          $("graph-labels").prepend(leader);
        }
        leader.setAttribute("d", `M ${sx} ${sy} L ${tx} ${ty}`);
        leader.style.display = "";
        leader.dataset.offscreen = String(offscreen);
        // The leader travels with the same delta as its label and its dot, so the
        // three stay rigidly attached for every frame of the flight.
        Object.assign(leader.dataset, {sceneX: String(anchorScene.x), sceneY: String(anchorScene.y),
          key: label.dataset.key || ""});
      }
      return true;
    }
    // Anchor the full selected name to its dot. If panned offscreen, keep a
    // clamped callout connected to the relevant edge and report that in status.
    if (state.selected && labels.has(state.selected)) {
      const point = scene.get(state.selected);
      if (point) place(labels.get(state.selected), nodes.get(state.selected).name,
        point.x * k + state.viewport.x, point.y * k + state.viewport.y, true);
    }
    if (state.mode === "overview") {
      for (const c of data.comms) {
        const keys = sceneKeys.filter((key) => nodes.get(key).community === String(c.id));
        if (!keys.length) continue;
        let label = communityLabels.find((el) => el.dataset.comm === String(c.id));
        if (!label) {
          label = document.createElementNS(ns, "text");
          label.setAttribute("class", "g-clabel");
          label.style.display = "none";
          label.dataset.comm = c.id;
          $("graph-labels").appendChild(label);
          communityLabels.push(label);
        }
        const x = keys.reduce((sum, key) => sum + scene.get(key).x, 0) / keys.length;
        const y = keys.reduce((sum, key) => sum + scene.get(key).y, 0) / keys.length;
        place(label, c.label, x * k + state.viewport.x, y * k + state.viewport.y, false, true);
      }
    } else {
      for (const key of ranked(sceneKeys)) {
        if (key === state.selected) continue;
        const point = scene.get(key), px = point.x * k + state.viewport.x, py = point.y * k + state.viewport.y;
        if (px < 0 || px > size.w || py < 0 || py > size.h) continue;
        place(labels.get(key), nodes.get(key).name, px, py);
      }
    }
  }

  function contextTitle() {
    if (state.mode === "path") return state.pathEnd ?
      `${nodes.get(state.pathStart).name} → ${nodes.get(state.pathEnd).name}` : "Trace a path";
    if (state.selected) return nodes.get(state.selected).name;
    if (state.mode === "search") return `Search: ${state.query}`;
    if (state.mode === "community") return communities.get(state.community).label;
    if (state.mode === "category") return $("gcategory").selectedOptions[0].textContent.replace(/ \(\d+\)$/, "");
    if (state.mode === "solution") return solutions.get(state.filters.solution).label;
    return "All communities";
  }

  const cameraTransform = (v) => `translate(${v.x} ${v.y}) scale(${v.k})`;

  function applyViewport(layoutPass = 0) {
    const {x, y, k} = state.viewport;
    vp.setAttribute("transform", cameraTransform(state.viewport));
    Object.assign(vp.dataset, {x: String(x), y: String(y), scale: String(k)});
    let visible = 0;
    nodes.forEach((node, key) => {
      const point = scene.get(key);
      const onScreen = !!point && point.x * k + x >= 0 && point.x * k + x <= size.w &&
        point.y * k + y >= 0 && point.y * k + y <= size.h;
      node.el.dataset.visible = String(onScreen);
      if (!point) return;
      if (onScreen) visible++;
      // Nodes are readable marks, while the companion list guarantees 44px targets.
      node.dot.setAttribute("r", Math.max(5, Math.min(15, node.radius * k)) / k);
      node.hit.setAttribute("r", 22 / k);
    });
    drawLabels();
    placeHalo();
    root.dataset.visibleCount = String(visible);
    root.dataset.renderedCount = String(sceneKeys.length);
    text("status-counts", `${visible} visible / ${sceneKeys.length} in view · ${listKeys.length} matching`);
    text("status-zoom", `${Math.round(k * 100)}% zoom`);
    text("status-context", state.mode === "node" ?
      `Node · ${communities.get(nodes.get(state.selected).community).label}` :
      state.mode === "community" ? `Community · ${communities.get(state.community).label}` :
        state.mode === "path" ? `Path · ${state.path.length ? state.path.length - 1 : 0} steps` : contextTitle());
    const offscreen = state.selected && nodes.get(state.selected).el.dataset.visible !== "true";
    text("status-selected", state.selected ? `Selected: ${nodes.get(state.selected).name}${offscreen ? " · offscreen — Fit to return" : ""}` : "No node selected");
    root.dataset.selectedOffscreen = String(!!offscreen);
    const stated = activeEdges.filter((edge) => edge.kind === 0).length;
    text("status-evidence", `${stated} stated · ${activeEdges.length - stated} inferred`);
    $("gzoom-in").disabled = k >= 30;
    $("gzoom-out").disabled = k <= .08;
    // A long title or status can wrap during this explicit render. Settle the
    // canvas now, not one observer frame later, so counts/callouts are truthful
    // immediately after a click. Keep the same world point at the center.
    const rect = $("graph-canvas").getBoundingClientRect();
    if (layoutPass < 3 && rect.width && rect.height &&
        (Math.abs(rect.width - size.w) > .01 || Math.abs(rect.height - size.h) > .01)) {
      state.viewport.x += (rect.width - size.w) / 2;
      state.viewport.y += (rect.height - size.h) / 2;
      size = {w: rect.width, h: rect.height};
      applyViewport(layoutPass + 1);
    }
  }

  // -------------------------------------------------------------- motion layer
  // Nothing below writes state, selection, query, mode, counts or label text.
  // Only transform, opacity and stroke-dashoffset move. One rAF loop, self-stopping.
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const MOTION = {quick: 160, standard: 260, slow: 420, ceiling: 600,
    wave: 200, step: 30, buckets: 10, pulse: 640, hop: 120, draw: 380, roles: 60, labels: 240,
    // The camera entry of a context change, as a fraction of the shorter canvas
    // edge. Bounded on purpose: it reads as arriving, not as a fly-through.
    entry: .06,
    // Bounds. Exits are decoration and the in-flight label core is what a moving
    // scale can carry without re-spacing names, so both are capped by count.
    core: 6, exits: 40};
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    return (p) => {
      if (p <= 0) return 0;
      if (p >= 1) return 1;
      let t = p;
      for (let i = 0; i < 8; i++) {
        const error = ((ax * t + bx) * t + cx) * t - p;
        if (Math.abs(error) < 1e-5) break;
        const slope = (3 * ax * t + 2 * bx) * t + cx;
        if (Math.abs(slope) < 1e-6) break;
        t -= error / slope;
      }
      t = Math.max(0, Math.min(1, t));
      return ((ay * t + by) * t + cy) * t;
    };
  }
  const EASE = {standard: bezier(.2, 0, 0, 1), enter: bezier(.05, .7, .1, 1), exit: bezier(.3, 0, 1, 1)};
  const halo = document.createElementNS(ns, "circle");
  halo.setAttribute("class", "g-halo");
  let flight = null, raf = 0, settleTimer = 0, idleTimer = 0, drawTimer = 0;
  let opening = false;
  const roleNodes = [], exitNodes = [];
  // Nothing ghosts the network any more. The scene layout is fixed for the whole
  // flight, so the real curved edges move with their dots through the one parent
  // transform and stay drawn: there is no geometry to rebuild and nothing to hide.
  // Receding dots are decoration, not nodes: they are drawn in their own layer so
  // they never masquerade as a node in context, carry a label or take a click.
  const exitLayer = document.createElementNS(ns, "g");
  exitLayer.setAttribute("id", "flight-exits");
  exitLayer.setAttribute("class", "g-flight-exits");
  exitLayer.setAttribute("aria-hidden", "true");
  (svg.querySelector(".g-edges") || vp).after(exitLayer);

  // The one ambient element: a halo on the selected dot, never under reduced motion.
  function placeHalo() {
    const key = state.selected, node = key ? nodes.get(key) : null;
    const point = node ? scene.get(key) : null;
    nodes.forEach((other) => {
      if (other.el.dataset.ambient && other.key !== key) delete other.el.dataset.ambient;
    });
    if (reducedMotion.matches || !node || !point) {
      if (halo.parentNode) halo.parentNode.removeChild(halo);
      if (node) delete node.el.dataset.ambient;
      return;
    }
    halo.setAttribute("cx", point.x);
    halo.setAttribute("cy", point.y);
    halo.setAttribute("r", 18 / state.viewport.k);
    // Re-inserting restarts the scale-in, so only move it when the target changes.
    if (halo.parentNode !== node.el) node.el.insertBefore(halo, node.dot);
    node.el.dataset.ambient = "true";
  }

  // Labels are always revealed. The flag stays as a readable marker, but there is
  // no code path and no rule left that can hide the whole layer: a global label
  // blackout is now structurally impossible rather than merely unused.
  function revealLabels() { $("graph-labels").dataset.revealed = "true"; }

  // Every label and leader on screen, with its scene anchor and the box the settled
  // layout gave it. Read once per beat, never per frame: cached metrics are what
  // makes a per-frame projection cheap, and a projection never touches font size.
  function liveLabels(coreOnly) {
    const layer = $("graph-labels"), all = [];
    const read = (el) => {
      if (el.style.display === "none") return;
      const sx = Number(el.dataset.sceneX), sy = Number(el.dataset.sceneY);
      if (!Number.isFinite(sx) || !Number.isFinite(sy)) return;
      // The selected leader is identified by identity, not by class: it is the one
      // leader in the layer without `.g-label-leader`, and treating it as a label
      // is what left its path stale while its name moved.
      const leader = el === selectedLeader || el.classList.contains("g-label-leader");
      all.push({el, sx, sy, leader, dx: 0, dy: 0, hidden: false,
        key: el.dataset.key || (leader && el === selectedLeader ? state.selected || "" : ""),
        box: leader ? null : {x: Number(el.dataset.boxX), y: Number(el.dataset.boxY),
          w: Number(el.dataset.boxW), h: Number(el.dataset.boxH)}});
    };
    layer.querySelectorAll(".g-nlabel, .g-clabel, .g-label-leader").forEach(read);
    if (selectedLeader.parentNode) read(selectedLeader);
    // The selected name first, then the names of the best-connected dots: if a
    // frame can only carry a few labels, these are the few worth carrying.
    const weight = (item) => item.key && item.key === state.selected ? 1e9 :
      item.key && nodes.has(item.key) ? Number(nodes.get(item.key).el.dataset.deg) || 0 : 0;
    all.sort((a, b) => weight(b) - weight(a));
    // The selected name is the one label the reader is following, so it is marked
    // once and never culled. Its leader's settled endpoint is recorded relative to
    // the box, because that offset is what keeps the leader attached to its dot
    // after the box has been clamped or nudged away from the dot's own delta.
    const chosen = state.selected || "";
    const anchor = chosen ? all.find((item) => !item.leader && item.key === chosen) : null;
    if (anchor) {
      anchor.anchor = true;
      anchor.lead = all.find((item) => item.leader && item.key === chosen) || null;
      if (anchor.lead) {
        anchor.lead.anchor = true;
        const end = (anchor.lead.el.getAttribute("d") || "").match(/L\s*(-?[\d.]+)[\s,]+(-?[\d.]+)/);
        anchor.lead.end = end
          ? {x: Number(end[1]) - anchor.box.x, y: Number(end[2]) - anchor.box.y}
          : {x: anchor.box.w / 2, y: anchor.box.h / 2};
      }
    }
    if (!coreOnly) return all.slice(0, MOTION.labels);
    // A moving scale re-spaces the labels while their text keeps one fixed size, so
    // only a small core rides a zoom: the selected name with its leader plus the few
    // best-connected names, each re-checked for collision on every frame. The rest
    // step aside for the flight and the full settled layout returns at idle.
    const keep = new Set();
    for (const item of all) {
      if (item.leader || keep.size >= MOTION.core + 1) continue;
      if (item.key) keep.add(item.key);
    }
    for (const item of all) {
      if (item.anchor) continue;
      if (!item.key || !keep.has(item.key)) {
        item.hidden = true;
        item.el.dataset.flown = "out";
        item.el.style.visibility = "hidden";
      }
    }
    return all;
  }

  function clearLabelFlight(items) {
    items.forEach((item) => {
      item.el.removeAttribute("transform");
      if (item.el.dataset.flown) delete item.el.dataset.flown;
      item.el.style.removeProperty("visibility");
    });
  }

  // Capture what the eye currently sees, including a tween in flight, so an
  // interruption continues from the visible position instead of snapping.
  function liveScene() {
    const points = new Map();
    nodes.forEach((node, key) => {
      if (node.el.dataset.inContext !== "true") return;
      const x = Number(node.el.dataset.renderX), y = Number(node.el.dataset.renderY);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      points.set(key, {x, y});
    });
    return {points, viewport: flight ? {...flight.live} : {...state.viewport}};
  }

  function clearTimers() {
    if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; }
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = 0; }
    if (drawTimer) { clearTimeout(drawTimer); drawTimer = 0; }
  }

  function clearDraw() {
    edgeElements.forEach((el) => {
      if (!el.dataset.draw) return;
      delete el.dataset.draw;
      el.style.removeProperty("stroke-dasharray");
      el.style.removeProperty("stroke-dashoffset");
      el.style.removeProperty("transition");
    });
  }

  // Pixels return to the committed geometry exactly: the tween only ever added
  // a group transform, so removing it leaves an instant render.
  function clearFlight() {
    if (raf) { cancelAnimationFrame(raf); raf = 0; }
    if (!flight) return;
    clearLabelFlight(flight.labels);
    flight = null;
    root.style.removeProperty("--dot-counter-scale");
    // The flight only ever added a parent transform and view measurements, so one
    // committed render puts every pixel and every count back on the settled truth.
    applyViewport();
  }

  // Only the nodes that were actually given a role are touched: sweeping all 490
  // on every render cost more frame budget than the roles themselves.
  // Exits are the only place motion re-shows a dot render() had hidden. It is
  // presentational: they carry no label, no hit target and no context.
  function clearExits() {
    if (exitLayer.firstChild) exitLayer.replaceChildren();
    exitNodes.length = 0;
  }

  function clearRoles() {
    clearExits();
    roleNodes.forEach((el) => {
      if (el.dataset.entering) delete el.dataset.entering;
      if (el.dataset.leaving) delete el.dataset.leaving;
      el.style.removeProperty("--enter-delay");
    });
    roleNodes.length = 0;
    delete root.dataset.pulse;
  }

  function cancelMotion() {
    clearTimers();
    clearDraw();
    clearFlight();
    clearRoles();
    revealLabels();
    root.dataset.motion = "idle";
  }

  // One parent transform per frame carries the whole fixed scene: dots, real edges
  // and the halo move together, and nothing rebuilds a path.
  function paint(f, progress) {
    const eased = f.ease(progress);
    const k = f.from.k * Math.pow(f.to.k / f.from.k, eased);
    const x = f.from.x + (f.to.x - f.from.x) * eased;
    const y = f.from.y + (f.to.y - f.from.y) * eased;
    f.live = {x, y, k};
    vp.setAttribute("transform", cameraTransform(f.live));
    // r is committed for the settled camera, so a moving scale would paint dots at
    // the wrong size. One custom property holds them at the size the layout
    // reserved for them, instead of 490 attribute writes per frame.
    root.style.setProperty("--dot-counter-scale", String(f.to.k / k));
    // View measurements describe the frame on screen, not the destination. Semantic
    // fields are never touched here; at idle these equal the instant render.
    Object.assign(vp.dataset, {x: String(x), y: String(y), scale: String(k)});
    let visible = 0;
    for (let i = 0; i < f.sample.length; i++) {
      const point = f.sample[i];
      const px = point.x * k + x, py = point.y * k + y;
      if (px >= 0 && px <= size.w && py >= 0 && py <= size.h) visible++;
      // One projection pass serves the count and every clearance test on this frame.
      const slot = f.proj[i];
      slot.x = px; slot.y = py;
    }
    if (visible !== f.visible) {
      f.visible = visible;
      root.dataset.visibleCount = String(visible);
      text("status-counts", `${visible} visible / ${sceneKeys.length} in view · ${listKeys.length} matching`);
    }
    const zoomPercent = Math.round(k * 100);
    if (zoomPercent !== f.zoomPercent) { f.zoomPercent = zoomPercent; text("status-zoom", `${zoomPercent}% zoom`); }
    if (!f.labels.length) return;
    // The selected callout is placed before anything else, so every other label is
    // culled around it rather than the other way round.
    const reserved = placeCallout(f, k, x, y);
    // A label is projected from its own scene anchor, so the same delta moves the
    // label, its leader and the dot underneath: the leader stays attached by
    // construction, and a translate can never change a font size.
    for (const item of f.labels) {
      if (item.hidden || item.anchor) continue;
      item.dx = (item.sx * k + x) - (item.sx * f.to.k + f.to.x);
      item.dy = (item.sy * k + y) - (item.sy * f.to.k + f.to.y);
      item.el.setAttribute("transform", `translate(${item.dx.toFixed(2)} ${item.dy.toFixed(2)})`);
    }
    cullLabels(f, k, x, y, reserved);
  }

  // The selected name is never hidden and never clipped: it is projected with the
  // camera, clamped whole into the canvas, and moved off a dot only as far as it
  // must go to stay legible. Its leader is redrawn to the dot's actual interpolated
  // rim, and the offscreen cue describes this frame rather than the destination.
  function placeCallout(f, k, x, y) {
    const item = f.anchor;
    if (!item) return null;
    const box = item.box;
    const projected = {x: box.x + (item.sx * k + x) - (item.sx * f.to.k + f.to.x),
      y: box.y + (item.sy * k + y) - (item.sy * f.to.k + f.to.y)};
    const dot = f.dot ? {x: f.dot.x * k + x, y: f.dot.y * k + y, r: f.dot.r} : null;
    const spot = calloutSpot(f, projected, box, dot);
    f.spot = spot;
    item.dx = spot.x - box.x; item.dy = spot.y - box.y;
    item.el.setAttribute("transform", `translate(${item.dx.toFixed(2)} ${item.dy.toFixed(2)})`);
    if (item.el.dataset.flown) delete item.el.dataset.flown;
    item.el.style.removeProperty("visibility");
    if (spot.fallback) item.el.dataset.calloutFallback = "1";
    else if (item.el.dataset.calloutFallback) delete item.el.dataset.calloutFallback;
    // View state, not semantic state: whether the dot is on screen on this frame.
    const off = !dot || dot.x < 0 || dot.x > size.w || dot.y < 0 || dot.y > size.h;
    if (off !== f.off) {
      f.off = off;
      root.dataset.selectedOffscreen = String(off);
      text("status-selected", state.selected ?
        `Selected: ${nodes.get(state.selected).name}${off ? " · offscreen — Fit to return" : ""}` :
        "No node selected");
    }
    const lead = item.lead;
    if (lead) {
      const tx = spot.x + lead.end.x, ty = spot.y + lead.end.y;
      let sx = tx, sy = ty;
      if (dot) {
        sx = clamp(dot.x, 5, size.w - 5); sy = clamp(dot.y, 5, size.h - 5);
        const distance = Math.hypot(tx - sx, ty - sy);
        if (!off && distance) { sx += (tx - sx) / distance * dot.r; sy += (ty - sy) / distance * dot.r; }
      }
      lead.el.removeAttribute("transform");
      lead.el.setAttribute("d", `M ${sx.toFixed(2)} ${sy.toFixed(2)} L ${tx.toFixed(2)} ${ty.toFixed(2)}`);
      lead.el.dataset.offscreen = String(off);
      lead.el.style.removeProperty("visibility");
      if (lead.el.dataset.flown) delete lead.el.dataset.flown;
    }
    return {x: spot.x, y: spot.y, w: box.w, h: box.h};
  }

  // Where the selected callout can sit on this frame: the position it held last
  // frame if it is still clear, then the projected position, then eight positions
  // around the dot, then a bounded coarse scan ordered by distance from the dot.
  // Hysteresis first is what stops the callout jittering between equally valid
  // spots on consecutive frames.
  function calloutSpot(f, projected, box, dot) {
    const lo = 6, hiX = size.w - 6 - box.w, hiY = size.h - 6 - box.h;
    const fit = (spot) => ({x: hiX < lo ? lo : clamp(spot.x, lo, hiX),
      y: hiY < lo ? lo : clamp(spot.y, lo, hiY)});
    const clear = (spot) => !dotUnder(f, spot, box, 5);
    const tries = [];
    if (f.spot) tries.push({x: f.spot.x, y: f.spot.y});
    tries.push(projected);
    if (dot) {
      const reach = Math.max(dot.r + 10,
        Math.hypot(projected.x + box.w / 2 - dot.x, projected.y + box.h / 2 - dot.y));
      for (let i = 0; i < 8; i++) {
        const angle = Math.PI / 4 * i;
        tries.push({x: dot.x + Math.cos(angle) * reach - box.w / 2,
          y: dot.y + Math.sin(angle) * reach - box.h / 2});
      }
    }
    for (const candidate of tries) {
      const spot = fit(candidate);
      if (clear(spot)) return spot;
    }
    const near = dot || {x: projected.x + box.w / 2, y: projected.y + box.h / 2};
    // A fixed candidate count spread over the whole canvas, so the scan cannot run
    // out of budget in one corner and report that no clear position exists.
    const cols = 24, rows = 24, grid = [];
    const stepX = Math.max(8, (Math.max(lo, hiX) - lo) / (cols - 1));
    const stepY = Math.max(8, (Math.max(lo, hiY) - lo) / (rows - 1));
    for (let cx = 0; cx < cols; cx++) {
      for (let cy = 0; cy < rows; cy++) {
        const gx = Math.min(Math.max(lo, hiX), lo + cx * stepX);
        const gy = Math.min(Math.max(lo, hiY), lo + cy * stepY);
        grid.push({x: gx, y: gy});
      }
    }
    grid.sort((a, b) => Math.hypot(a.x + box.w / 2 - near.x, a.y + box.h / 2 - near.y) -
      Math.hypot(b.x + box.w / 2 - near.x, b.y + box.h / 2 - near.y));
    // Clear positions can sit at the periphery while the dot is in a crowded middle,
    // so the scan is allowed to reach them. The budget is spent per frame against the
    // dots actually on screen, which keeps a dense overview cheap and a sparse
    // close-up thorough.
    const budget = Math.max(120, Math.min(grid.length, Math.floor(30000 / Math.max(1, f.proj.length))));
    let best = null, least = Infinity;
    for (let i = 0; i < grid.length && i < budget; i++) {
      const candidate = grid[i];
      const overlap = dotOverlap(f, candidate, box, 5, false);
      if (overlap === 0) return candidate;
      if (overlap < least) { least = overlap; best = candidate; }
    }
    // Documented last resort: no position on this frame is completely clear, so the
    // name takes the least-obstructed one it found instead of silently sitting on a
    // dot. It stays whole, inside the canvas and readable, and says so in the DOM.
    return {...fit(best || projected), fallback: true};
  }

  function dotUnder(f, spot, box, margin) {
    return dotOverlap(f, spot, box, margin, true) > 0;
  }

  // How much of a box the painted dots cover. `first` stops at the first hit for the
  // cheap yes/no question; the full count ranks candidates when none is clear.
  function dotOverlap(f, spot, box, margin, first) {
    let total = 0;
    for (const point of f.proj) {
      // The painted dot is its radius plus a stroke, so the callout keeps a wider
      // margin than a plain label: clearance has to hold for painted pixels.
      const pad = point.r + (margin || 2);
      const w = Math.min(point.x + pad, spot.x + box.w) - Math.max(point.x - pad, spot.x);
      const h = Math.min(point.y + pad, spot.y + box.h) - Math.max(point.y - pad, spot.y);
      if (w > 0 && h > 0) {
        total += w * h;
        if (first) return total;
      }
    }
    return total;
  }

  // What the eye must not see: a name outside the canvas, a name over another name,
  // or a name over a dot. Checked on the frame, for the labels actually riding it.
  function cullLabels(f, k, x, y, reserved) {
    const placed = reserved ? [reserved] : [];
    for (const item of f.labels) {
      if (item.hidden || item.anchor || !item.box) continue;
      // The 6px allowance is the label's own halo stroke, which paints outside the
      // measured text box.
      const bx = item.box.x + item.dx, by = item.box.y + item.dy;
      let out = bx < 6 || by < 6 || bx + item.box.w > size.w - 6 || by + item.box.h > size.h - 6;
      if (!out && f.cull) {
        for (const other of placed) {
          if (bx < other.x + other.w && bx + item.box.w > other.x &&
              by < other.y + other.h && by + item.box.h > other.y) { out = true; break; }
        }
        if (!out && dotUnder(f, {x: bx, y: by}, item.box)) out = true;
      }
      if (!out) placed.push({x: bx, y: by, w: item.box.w, h: item.box.h});
      if (out === (item.el.dataset.flown === "out")) continue;
      // visibility, not opacity: an entering label's own fade-in animation would
      // otherwise override an opacity rule and paint it in the wrong place anyway.
      if (out) { item.el.dataset.flown = "out"; item.el.style.visibility = "hidden"; }
      else { delete item.el.dataset.flown; item.el.style.removeProperty("visibility"); }
    }
  }

  function step(now) {
    const f = flight;
    if (!f) { raf = 0; return; }
    const progress = Math.min(1, (now - f.start) / f.duration);
    paint(f, progress);
    if (progress >= 1) { raf = 0; clearFlight(); return; }
    raf = requestAnimationFrame(step);
  }

  // The path hops draw in sequence. Edge geometry is already final; only the
  // dash offset moves, so no path is ever rebuilt while it animates.
  function startDraw(budget) {
    const hops = state.path.length - 1;
    if (hops < 1) return 0;
    const per = Math.max(40, Math.min(MOTION.hop, Math.floor(budget / hops)));
    let drawn = 0;
    state.path.slice(1).forEach((key, i) => {
      const previous = state.path[i];
      const edge = activeEdges.find((item) =>
        (item.a === previous && item.b === key) || (item.a === key && item.b === previous));
      if (!edge) return;
      const el = edgeElements[edge.index];
      let length = 0;
      try { length = el.getTotalLength(); } catch (_) { length = 0; }
      if (!length) return;
      el.dataset.draw = "true";
      el.style.transition = "none";
      el.style.strokeDasharray = String(length);
      el.style.strokeDashoffset = String(length);
      void el.getBoundingClientRect();
      el.style.transition = `stroke-dashoffset ${per}ms cubic-bezier(0.2, 0, 0, 1) ${i * per}ms`;
      el.style.strokeDashoffset = "0";
      drawn = Math.max(drawn, (i + 1) * per);
    });
    if (drawn) drawTimer = setTimeout(() => { drawTimer = 0; clearDraw(); }, drawn + 60);
    return drawn;
  }

  function waveDelays(entering) {
    const anchorKey = state.selected && scene.has(state.selected) ? state.selected :
      ranked(sceneKeys)[0];
    const anchor = anchorKey ? scene.get(anchorKey) : {x: 0, y: 0};
    const order = entering.slice().sort((a, b) => {
      const pa = scene.get(a.key), pb = scene.get(b.key);
      return Math.hypot(pa.x - anchor.x, pa.y - anchor.y) - Math.hypot(pb.x - anchor.x, pb.y - anchor.y);
    });
    const perBucket = Math.max(1, Math.ceil(order.length / MOTION.buckets));
    let longest = 0;
    order.forEach((node, i) => {
      const delay = Math.min(MOTION.buckets - 1, Math.floor(i / perBucket)) * MOTION.step;
      node.el.style.setProperty("--enter-delay", `${delay}ms`);
      longest = Math.max(longest, delay);
    });
    return longest;
  }

  // The settled screen box of the selected name, so an entry can be clamped to keep
  // the one label the reader is looking for inside the frame.
  function selectedBox() {
    if (!state.selected) return null;
    const el = labels.get(state.selected);
    if (el && el.style.display !== "none" && Number.isFinite(Number(el.dataset.boxX))) {
      return {x: Number(el.dataset.boxX), y: Number(el.dataset.boxY),
        w: Number(el.dataset.boxW), h: Number(el.dataset.boxH)};
    }
    const point = scene.get(state.selected);
    if (!point) return null;
    const {x, y, k} = state.viewport;
    return {x: point.x * k + x - 14, y: point.y * k + y - 14, w: 28, h: 28};
  }

  // A context change commits its destination layout, then the camera arrives into
  // it: the offset points back the way the anchor moved on screen, so the eye is
  // carried from where it last saw the subject. Bounded to MOTION.entry of the
  // shorter canvas edge, and clamped so the selected name never starts outside.
  function entryOffset(previous) {
    const to = state.viewport, limit = Math.min(size.w, size.h) * MOTION.entry;
    const key = state.selected && scene.has(state.selected) ? state.selected : ranked(sceneKeys)[0];
    const now = key ? scene.get(key) : null, was = key ? previous.points.get(key) : null;
    let dx = 0, dy = 0;
    if (now && was) {
      dx = (was.x * previous.viewport.k + previous.viewport.x) - (now.x * to.k + to.x);
      dy = (was.y * previous.viewport.k + previous.viewport.y) - (now.y * to.k + to.y);
    } else {
      dx = previous.viewport.x - to.x;
      dy = previous.viewport.y - to.y;
    }
    const span = Math.hypot(dx, dy);
    // No direction to borrow: the scene settles down into place rather than snapping.
    if (span < .001) { dx = 0; dy = -limit * .55; }
    else { dx = dx / span * limit; dy = dy / span * limit; }
    const box = selectedBox();
    if (box) {
      const clamp = (value, low, high) => low > high ? 0 : Math.max(low, Math.min(high, value));
      dx = clamp(dx, 6 - box.x, size.w - 6 - box.x - box.w);
      dy = clamp(dy, 6 - box.y, size.h - 6 - box.y - box.h);
    }
    return {dx, dy};
  }

  function beginMotion(previous, beat) {
    clearTimers();
    clearDraw();
    const entering = [], leaving = [];
    sceneKeys.forEach((key) => {
      if (!previous.points.has(key)) entering.push(nodes.get(key));
    });
    previous.points.forEach((_point, key) => {
      if (!scene.has(key) && nodes.has(key)) leaving.push(nodes.get(key));
    });
    const wave = beat === "first-paint";
    // The scene layout is never interpolated: dot positions and the destination
    // camera commit at once. What moves is the camera, and it moves for real.
    // A zoom or Fit interpolates the committed camera from where the eye last saw
    // it; a context change interpolates a bounded entry offset into its committed
    // camera. Both are one uniform transform over a fixed scene, so every spatial
    // relationship the layout resolved survives every frame of the flight.
    let from = {...previous.viewport}, to = {...state.viewport}, camera = false;
    if (!wave && beat === "camera") {
      camera = Math.abs(from.x - to.x) > .5 || Math.abs(from.y - to.y) > .5 ||
        Math.abs(Math.log((to.k || 1) / (from.k || 1))) > .001;
    } else if (!wave && beat === "context") {
      const entry = entryOffset(previous);
      if (Math.hypot(entry.dx, entry.dy) > .5) {
        from = {k: to.k, x: to.x + entry.dx, y: to.y + entry.dy};
        camera = true;
      }
    }
    const zooming = Math.abs(Math.log((to.k || 1) / (from.k || 1))) > .001;
    const regime = entering.length > 0;
    if (beat === "context" && !camera && !entering.length && !leaving.length) {
      beat = "selection";
    }
    root.dataset.motionBeat = beat;
    clearFlight();
    clearRoles();
    if (reducedMotion.matches) {
      revealLabels();
      root.dataset.motion = "idle";
      return;
    }
    // A zoom or Fit is a control the hand is holding, so it answers at 260ms. A
    // context change is a new place to read, so it settles at 420ms. Neither is
    // stretched by distance, because the entry itself is bounded.
    const duration = Math.min(MOTION.ceiling,
      beat === "camera" || beat === "selection" ? MOTION.standard : MOTION.slow);
    // Roles are capped: a node-to-overview change enters hundreds of dots at once,
    // and one CSS animation per dot costs more frame budget than the beat is worth.
    const entered = entering.slice(0, MOTION.roles);
    entered.forEach((node) => { node.el.dataset.entering = "true"; roleNodes.push(node.el); });
    // Leaving dots recede instead of blinking out. render() already committed them
    // hidden, so motion re-shows only the ones that were actually on screen, capped
    // at MOTION.exits: re-showing all 466 of them on an overview-to-node change is
    // what blew the frame budget, and each one still carries no label and no target.
    const exiting = [];
    for (const node of leaving) {
      if (exiting.length >= MOTION.exits) break;
      const point = previous.points.get(node.key);
      const sx = point.x * previous.viewport.k + previous.viewport.x;
      const sy = point.y * previous.viewport.k + previous.viewport.y;
      if (sx < 0 || sx > size.w || sy < 0 || sy > size.h) continue;
      exiting.push(node);
    }
    exiting.forEach((node) => {
      const point = previous.points.get(node.key);
      const dot = document.createElementNS(ns, "circle");
      const hue = [...node.el.classList].find((name) => /^h(\d+|x)$/.test(name)) || "hx";
      dot.setAttribute("class", `g-exit-dot ${hue}`);
      dot.setAttribute("cx", point.x);
      dot.setAttribute("cy", point.y);
      dot.setAttribute("r", node.dot.getAttribute("r") || 6);
      exitLayer.appendChild(dot);
      node.el.dataset.leaving = "true";
      roleNodes.push(node.el);
      exitNodes.push(dot);
    });
    leaving.slice(0, MOTION.roles).forEach((node) => {
      if (node.el.dataset.leaving) return;
      node.el.dataset.leaving = "true";
      roleNodes.push(node.el);
    });
    const waveLongest = (wave || regime) && entered.length ? waveDelays(entered) : 0;
    const moving = camera;
    let settleAt = wave ? waveLongest + MOTION.wave : moving || entering.length || leaving.length ?
      Math.max(duration, waveLongest + MOTION.wave) : beat === "selection" ? MOTION.standard : 0;
    if (beat === "search") settleAt = Math.max(settleAt, MOTION.standard);
    if (!settleAt && beat !== "search") {
      revealLabels();
      root.dataset.motion = "idle";
      return;
    }
    root.dataset.motion = "running";
    opening = wave;
    if (beat === "search") {
      // Restart the matched-dot pulse even when the attribute was already present.
      delete root.dataset.pulse;
      void root.getBoundingClientRect();
      root.dataset.pulse = "1";
    }
    // Nothing readable is ever withheld, on any beat including the opening. The
    // layout is committed before the first frame, so the names and the network are
    // correct immediately; the dot wave is decoration laid over a readable graph,
    // not a curtain in front of one.
    revealLabels();
    if (moving) {
      const labelling = liveLabels(zooming);
      const anchor = labelling.find((item) => item.anchor && !item.leader) || null;
      const selectedPoint = state.selected ? scene.get(state.selected) : null;
      flight = {start: performance.now(), duration, ease: beat === "context" ? EASE.enter : EASE.standard,
        from: {...from}, to: {...to}, live: {...from}, cull: zooming, visible: -1, zoomPercent: -1,
        anchor, spot: null, off: null,
        // The selected dot keeps one screen radius for the whole flight, because the
        // committed r is counter-scaled per frame, so the leader's rim is exact.
        dot: selectedPoint ? {x: selectedPoint.x, y: selectedPoint.y,
          r: Math.max(5, Math.min(15, (nodes.get(state.selected).radius || 6) * to.k))} : null,
        // The scene is fixed, so one projected sample of it answers both the live
        // visible count and the per-frame label clearance check. A dot keeps its
        // screen radius through the flight, so the radius is sampled once too.
        sample: sceneKeys.map((key) => {
          const point = scene.get(key);
          if (!point) return null;
          return {x: point.x, y: point.y,
            r: Math.max(5, Math.min(15, (nodes.get(key).radius || 6) * to.k))};
        }).filter(Boolean),
        labels: labelling};
      // Reused per frame so a projection pass allocates nothing.
      flight.proj = flight.sample.map((point) => ({x: 0, y: 0, r: point.r}));
      paint(flight, 0);
      raf = requestAnimationFrame(step);
    }
    let total = settleAt;
    if (beat === "search") total = Math.max(total, MOTION.pulse);
    const drawBudget = beat === "path" ? Math.max(0, Math.min(MOTION.draw, 880 - settleAt)) : 0;
    settleTimer = setTimeout(() => {
      settleTimer = 0;
      clearFlight();
      clearRoles();
      revealLabels();
      if (drawBudget) {
        const drawn = startDraw(drawBudget);
        if (drawn) {
          if (idleTimer) clearTimeout(idleTimer);
          idleTimer = setTimeout(() => { idleTimer = 0; root.dataset.motion = "idle"; }, drawn);
        }
      }
    }, settleAt);
    // The only frame loop is the one that paints the camera. CSS-only beats end on
    // a cancellable timer, and an interruption cancels both, so a frame counter is
    // never mistaken for evidence that pixels moved.
    idleTimer = setTimeout(() => {
      idleTimer = 0; opening = false; root.dataset.motion = "idle";
    }, total);
  }

  function renderList() {
    const signature = JSON.stringify([listKeys, state.query, state.listKind]);
    if (signature !== listSignature) {
      const fragment = document.createDocumentFragment();
      for (const key of listKeys) {
        const node = nodes.get(key), li = document.createElement("li"), button = document.createElement("button");
        button.type = "button";
        button.dataset.key = key;
        const name = document.createElement("strong"), description = document.createElement("span");
        name.textContent = node.name;
        const q = state.query.trim().toLocaleLowerCase();
        const found = q ? node.description.toLocaleLowerCase().indexOf(q) : -1;
        const start = Math.max(0, found - 40);
        description.textContent = (start ? "…" : "") + node.description.slice(start, start + 145) +
          (node.description.length > start + 145 ? "…" : "");
        button.append(name, description);
        const qualifier = node.card.querySelector(".qual");
        if (qualifier) {
          const detail = document.createElement("span");
          detail.className = "result-qualifier";
          detail.textContent = `${node.category} / ${qualifier.textContent}`;
          button.append(detail);
        }
        button.setAttribute("aria-label", `${node.name}, ${node.category}${qualifier ? ", " + qualifier.textContent : ""}`);
        li.appendChild(button);
        fragment.appendChild(li);
      }
      if (!listKeys.length) {
        const li = document.createElement("li");
        li.className = "empty-result";
        li.textContent = "No matching skills. Try another word or clear a filter.";
        fragment.appendChild(li);
      }
      results.replaceChildren(fragment);
      results.scrollTop = 0;
      listSignature = signature;
    }
    results.querySelectorAll("button").forEach((button) =>
      button.setAttribute("aria-pressed", String(button.dataset.key === state.selected)));
    text("results-title", state.query.trim() ? "Search results" :
      state.listKind === "community" ? "Community members" : "Matching skills");
    text("results-count", String(listKeys.length));
    text("results-hint", state.pathPending ?
      (state.pathStart ? `Choose the end. Start: ${nodes.get(state.pathStart).name}` : "Choose a start, then an end.") :
      state.selected ? "Selection stays put. Choose another result to compare." : "Select a skill to inspect it.");
  }

  function evidenceText(edge) {
    const reasons = data.why[edge.index] || [];
    return `${edge.kind === 0 ? "Stated" : "Inferred"}: ${reasons.join("; ") || "No detail supplied"}`;
  }

  function renderPanel() {
    text("paneltier", state.mode === "node" ? "Selected skill" : state.mode);
    text("panelname", contextTitle());
    $("panelchain").replaceChildren();
    $("panelsource").hidden = !state.selected;
    text("panelmeta", "");
    if (state.mode === "path") {
      const count = Math.max(0, state.path.length - 1);
      text("paneldesc", !state.pathEnd ? "Choose an end skill from the result list. Search remains available." :
        state.path.length ? `${count} ${count === 1 ? "edge" : "edges"} in the shortest path.` :
          "No path exists with the active evidence filter. Try all evidence or choose another end.");
      state.path.forEach((key, i) => {
        const li = document.createElement("li");
        li.textContent = nodes.get(key).name;
        if (i) {
          const edge = adjacency.get(state.path[i - 1]).find((item) => item.to === key).edge;
          const detail = document.createElement("p");
          detail.textContent = evidenceText(edge);
          li.appendChild(detail);
        }
        $("panelchain").appendChild(li);
      });
      text("panelev", "Breadth-first search. Every edge costs one step. Filters do not invent missing connections.");
    } else if (state.selected) {
      const node = nodes.get(state.selected), linked = neighbors(state.selected);
      text("paneldesc", node.description);
      $("panelsource").href = node.source;
      text("panelmeta", `${node.repo} · ${node.licence}`);
      linked.forEach((item) => {
        const li = document.createElement("li"), button = document.createElement("button"), detail = document.createElement("span");
        button.type = "button"; button.dataset.key = item.to;
        button.textContent = nodes.get(item.to).name;
        detail.textContent = evidenceText(item.edge);
        li.append(button, detail);
        $("panelchain").appendChild(li);
      });
      text("panelev", `${linked.length} connections in the active evidence graph. Solid = stated. Dashed = inferred.`);
    } else {
      const solution = solutions.get(state.filters.solution);
      text("paneldesc", state.mode === "search" ?
        `${listKeys.length} matches in skill names and full descriptions. Select a result; your search stays here.` :
        state.mode === "community" ?
          `${listKeys.length} skills in this detected community. Select any member below to expand its neighborhood.` :
          state.mode === "solution" ? `${solution.tier} Solution. ${solution.evidence}` :
            `${listKeys.length} skills available. Select a member or narrow the top filters.`);
      text("panelev", state.mode === "overview" ?
        "Labels name detected communities. All communities, including single skills, are available in the dropdown." :
        "Solid edges are stated in the repository. Dashed edges are inferred from names.");
    }
    if (state.selected) $("panelsource").href = nodes.get(state.selected).source;
  }

  function render({frame = true, beat = "context"} = {}) {
    // The previous rendered pixels, captured before any recompute overwrites them.
    const previous = liveScene();
    clearTimers();
    clearDraw();
    clearFlight();
    clearRoles();
    search.value = state.query;
    $("gcommunity").value = state.filters.community || (state.mode === "community" ? state.community : "");
    $("gcategory").value = state.filters.category;
    $("gsolution").value = state.filters.solution;
    $("gstated").setAttribute("aria-pressed", String(state.filters.stated));
    text("gstated", state.filters.stated ? "Stated only" : "All evidence");
    $("gpath").setAttribute("aria-pressed", String(state.pathPending || state.mode === "path"));
    text("gpath", state.pathPending ? "Cancel path" : "Trace path");
    $("gback").disabled = !history.length;
    $("gclear").disabled = !state.query;
    Object.assign(root.dataset, {mode: state.mode, query: state.query, selectedKey: state.selected,
      community: state.community, category: state.filters.category, solution: state.filters.solution,
      evidence: state.filters.stated ? "stated" : "all", path: JSON.stringify(state.path)});
    text("workspace-title", contextTitle());
    text("context-kind", `Skill library / ${state.mode === "node" ? "Selected skill" : state.mode}`);
    text("graph-caption", state.mode === "node" ? "Selected skill + direct connections" :
      state.mode === "path" ? "Shortest path · active evidence" : "Drag to pan · select a skill to explore");
    prepareScene();
    root.dataset.matchingCount = String(listKeys.length);
    renderList();
    renderPanel();
    if (frame) fit();
    applyViewport();
    // Every truthful write above is committed. Only pixels move from here.
    beginMotion(previous, beat);
  }

  function selectNode(key) {
    if (!nodes.has(key)) return;
    save();
    state.selected = key;
    if (state.pathPending) {
      if (!state.pathStart) {
        state.pathStart = key; state.mode = "path";
      } else {
        state.pathEnd = key; state.path = shortestPath(state.pathStart, key);
        state.pathPending = false; state.mode = "path";
      }
    } else {
      state.mode = "node";
    }
    render({beat: state.mode === "path" && state.path.length > 1 ? "path" : "context"});
    $("panel").scrollTop = 0;
  }

  function baseMode() {
    if (state.query.trim()) return "search";
    if (state.filters.solution) return "solution";
    if (state.filters.category) return "category";
    if (state.filters.community) return "community";
    return "overview";
  }
  function changeSearch() {
    if (search.value === state.query) return;
    if (!search.value && state.query) { clearSearch(); return; }
    // One history entry per search session, not one per keystroke.
    if (!state.query || state.mode === "node") save();
    if (!state.query && !state.searchOrigin) state.searchOrigin = clone(state);
    state.query = search.value;
    if (state.pathPending) {
      state.mode = "path";
    } else {
      state.selected = ""; state.path = []; state.pathStart = ""; state.pathEnd = "";
      state.mode = baseMode();
    }
    state.listKind = "search";
    render({beat: "search"});
  }
  search.addEventListener("input", changeSearch);
  $("gform").addEventListener("submit", (event) => {
    event.preventDefault();
    if (listKeys.length) selectNode(listKeys[0]);
  });
  function clearSearch() {
    const origin = state.searchOrigin, filters = clone(state.filters);
    save();
    if (origin && ["community", "category", "solution"].every((key) => origin.filters[key] === filters[key])) {
      state = clone(origin); state.searchOrigin = null; state.filters.stated = filters.stated;
      render({frame: false});
    } else {
      state.query = ""; state.selected = ""; state.pathPending = false; state.path = [];
      state.pathStart = ""; state.pathEnd = ""; state.mode = baseMode(); state.searchOrigin = null;
      state.listKind = state.mode; render();
    }
    search.focus();
  }
  $("gclear").addEventListener("click", clearSearch);
  for (const [id, filter] of [["gcommunity", "community"], ["gcategory", "category"], ["gsolution", "solution"]]) {
    $(id).addEventListener("change", () => {
      save(); state.filters[filter] = $(id).value;
      if (filter === "community") state.community = $(id).value;
      state.selected = ""; state.path = []; state.pathPending = false;
      state.pathStart = ""; state.pathEnd = "";
      state.mode = baseMode(); state.listKind = state.mode; render();
    });
  }
  $("gstated").addEventListener("click", () => {
    save(); state.filters.stated = !state.filters.stated;
    if (state.pathStart && state.pathEnd) state.path = shortestPath(state.pathStart, state.pathEnd);
    render({beat: state.path.length > 1 ? "path" : "context"});
  });
  function resetWorkspace() {
    save(); state = initial(); render();
  }
  $("greset").addEventListener("click", resetWorkspace);
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      // An explicit Reset shortcut, not the browser's partial search-input clear.
      event.preventDefault(); resetWorkspace();
    }
  });
  $("goverview").addEventListener("click", () => {
    save(); state = initial(); state.mode = "overview"; state.listKind = "overview"; state.community = ""; render();
  });
  $("gback").addEventListener("click", () => {
    if (!history.length) return;
    state = history.pop(); render({frame: false});
  });
  $("gpath").addEventListener("click", () => {
    save();
    if (state.pathPending) {
      state.pathPending = false; state.path = []; state.pathStart = ""; state.pathEnd = "";
      state.mode = state.selected ? "node" : baseMode();
    } else {
      state.pathPending = true; state.pathStart = state.selected;
      state.pathEnd = ""; state.path = []; state.mode = "path";
    }
    render();
  });
  [results, $("panelchain")].forEach((list) => list.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-key]");
    if (button) selectNode(button.dataset.key);
  }));
  svg.addEventListener("click", (event) => {
    const node = event.target.closest(".g-node");
    if (node) event.preventDefault();
    if (suppressClick) { suppressClick = false; return; }
    if (node) selectNode(node.dataset.key);
  });
  // A camera-only beat: the world is unchanged, so only #vp interpolates and the
  // labels are re-placed for the settled camera before the tween starts.
  function cameraBeat(change) {
    const previous = liveScene();
    change();
    applyViewport();
    beginMotion(previous, "camera");
  }
  function zoom(factor) {
    cameraBeat(() => {
      const old = state.viewport.k, next = Math.max(.08, Math.min(30, old * factor));
      state.viewport.x = size.w / 2 - (size.w / 2 - state.viewport.x) * next / old;
      state.viewport.y = size.h / 2 - (size.h / 2 - state.viewport.y) * next / old;
      state.viewport.k = next;
    });
  }
  $("gzoom-in").addEventListener("click", () => zoom(1.3));
  $("gzoom-out").addEventListener("click", () => zoom(1 / 1.3));
  $("gfit").addEventListener("click", () => cameraBeat(fit));
  svg.addEventListener("keydown", (event) => {
    const moves = {ArrowLeft: [48, 0], ArrowRight: [-48, 0], ArrowUp: [0, 48], ArrowDown: [0, -48]};
    if (moves[event.key]) {
      // A held arrow key is a direct manipulation: it tracks the key, never lags.
      event.preventDefault(); cancelMotion();
      state.viewport.x += moves[event.key][0]; state.viewport.y += moves[event.key][1]; applyViewport();
    } else if (["+", "=", "-"].includes(event.key)) {
      event.preventDefault(); zoom(event.key === "-" ? 1 / 1.3 : 1.3);
    } else if (event.key === "Home") {
      event.preventDefault(); cameraBeat(fit);
    }
  });
  let drag = null;
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    suppressClick = false;
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY,
      startX: state.viewport.x, startY: state.viewport.y, moved: false};
  });
  svg.addEventListener("pointermove", (event) => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) < 5) return;
    drag.moved = true;
    // A drag is direct manipulation: cancel any tween and follow the pointer.
    if (flight || raf) cancelMotion();
    svg.setPointerCapture(event.pointerId);
    svg.classList.add("is-dragging");
    state.viewport.x = drag.startX + dx; state.viewport.y = drag.startY + dy;
    applyViewport();
  });
  function endDrag() {
    if (!drag) return;
    suppressClick = drag.moved;
    if (svg.hasPointerCapture(drag.id)) svg.releasePointerCapture(drag.id);
    drag = null; svg.classList.remove("is-dragging");
  }
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  function openReference(id) {
    const target = $(id);
    if (!target) return;
    let parent = target;
    while (parent) {
      if (parent.tagName === "DETAILS") parent.open = true;
      parent = parent.parentElement;
    }
    target.scrollIntoView({behavior: "instant", block: "start"});
  }
  document.querySelectorAll("[data-open]").forEach((link) => link.addEventListener("click", (event) => {
    event.preventDefault(); openReference(link.dataset.open);
    historyReplace(link.getAttribute("href"));
  }));
  function historyReplace(hash) {
    try { window.history.replaceState(null, "", hash); } catch (_) { /* opaque previews */ }
  }
  function openHash() {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id) openReference(id);
  }
  window.addEventListener("hashchange", openHash);
  if (window.matchMedia("(max-width: 767px)").matches) $("gfilters").open = false;
  document.documentElement.classList.add("js");
  function resize() {
    const rect = $("graph-canvas").getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const old = size;
    size = {w: rect.width, h: rect.height};
    // With no root viewBox, SVG user units are CSS pixels even during the frame
    // before ResizeObserver runs. Header wrapping can never briefly shrink type.
    svg.removeAttribute("viewBox");
    if (root.dataset.ready === "true") {
      // Preserve zoom and the world point at viewport center, not just the title.
      state.viewport.x += (size.w - old.w) / 2;
      state.viewport.y += (size.h - old.h) / 2;
      // A genuine resize invalidates a tween's target; an observer echo does not.
      const resized = Math.abs(size.w - old.w) > .01 || Math.abs(size.h - old.h) > .01;
      if (resized) cancelMotion();
      applyViewport();
      // A layout echo right after load used to cancel the opening wave, which is why
      // it was never observable. The geometry it was cancelled for is now committed,
      // so the opening simply starts again against it.
      if (resized && opening) beginMotion({points: new Map(), viewport: {...state.viewport}}, "first-paint");
    } else {
      render({beat: "first-paint"});
      root.dataset.ready = "true";
    }
  }
  resize();
  new ResizeObserver(resize).observe($("graph-canvas"));
  if (document.fonts) document.fonts.ready.then(drawLabels);
  openHash();
})();
