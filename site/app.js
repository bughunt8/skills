/* Static graph workspace. Context changes only through deliberate user actions.
 * The build owns identity, evidence, communities and the complete text library.
 * Geometry and screen-space labels have independent transforms. No motion layer.
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
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
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

  function applyViewport(layoutPass = 0) {
    const {x, y, k} = state.viewport;
    vp.setAttribute("transform", `translate(${x} ${y}) scale(${k})`);
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

  function render({frame = true} = {}) {
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
    render();
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
    render();
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
    render();
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
  function zoom(factor) {
    const old = state.viewport.k, next = Math.max(.08, Math.min(30, old * factor));
    state.viewport.x = size.w / 2 - (size.w / 2 - state.viewport.x) * next / old;
    state.viewport.y = size.h / 2 - (size.h / 2 - state.viewport.y) * next / old;
    state.viewport.k = next;
    applyViewport();
  }
  $("gzoom-in").addEventListener("click", () => zoom(1.3));
  $("gzoom-out").addEventListener("click", () => zoom(1 / 1.3));
  $("gfit").addEventListener("click", () => { fit(); applyViewport(); });
  svg.addEventListener("keydown", (event) => {
    const moves = {ArrowLeft: [48, 0], ArrowRight: [-48, 0], ArrowUp: [0, 48], ArrowDown: [0, -48]};
    if (moves[event.key]) {
      event.preventDefault(); state.viewport.x += moves[event.key][0]; state.viewport.y += moves[event.key][1]; applyViewport();
    } else if (["+", "=", "-"].includes(event.key)) {
      event.preventDefault(); zoom(event.key === "-" ? 1 / 1.3 : 1.3);
    } else if (event.key === "Home") {
      event.preventDefault(); fit(); applyViewport();
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
      applyViewport();
    } else {
      render();
      root.dataset.ready = "true";
    }
  }
  resize();
  new ResizeObserver(resize).observe($("graph-canvas"));
  if (document.fonts) document.fonts.ready.then(drawLabels);
  openHash();
})();
