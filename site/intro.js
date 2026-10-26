(function () {
  "use strict";

  var SK = window.SKILLDATA || {};
  var nodesRaw = SK.nodes || [];
  var edgesRaw = SK.edges || [];
  var catDomain = SK.catDomain || {};
  var domains = SK.domains || {};
  var domainIds = Object.keys(domains);
  var comms = SK.comms || [];
  var commOf = SK.commOf || [];
  var PALETTE = ["#00e5ff", "#ff2ea6", "#8a63ff", "#ffd166",
                 "#3ddc97", "#ff8c5a", "#5aa9ff", "#9dff5c"];
  var MIN_DOTS = 3;

  var netEl = document.getElementById("net");
  var heroEl = document.getElementById("hero");
  var crowdEl = document.getElementById("crowd");
  var crowdTitle = document.getElementById("crowd-title");
  var crowdHint = document.getElementById("crowd-hint");
  var crowdList = document.getElementById("crowd-list");
  var cardEl = document.getElementById("hovercard");
  var cardKicker = document.getElementById("hc-kicker");
  var cardTitle = document.getElementById("hc-title");
  var cardMeta = document.getElementById("hc-meta");
  var cardCta = document.getElementById("hc-cta");

  function domainOf(key) {
    var parts = key.split("~~");
    var cat = parts.length > 1 ? parts[0] : key.split("/")[0];
    return catDomain[cat] || "";
  }
  function domainLabel(id) {
    return (domains[id] || id || "unfiled").toString();
  }
  function domainColor(id) {
    var i = domainIds.indexOf(id);
    return PALETTE[(i < 0 ? 0 : i) % PALETTE.length];
  }
  function skillName(key) { return key.split("~~").pop(); }
  function skillCategory(key) {
    var parts = key.split("~~");
    return parts.length > 1 ? parts[0] : key.split("/")[0];
  }

  var degree = {};
  edgesRaw.forEach(function (e) {
    degree[e[0]] = (degree[e[0]] || 0) + 1;
    degree[e[1]] = (degree[e[1]] || 0) + 1;
  });

  var commById = {};
  comms.forEach(function (c) { commById[c.id] = c; });
  var membersOf = {};
  for (var i = 0; i < nodesRaw.length; i++) {
    var cid = commOf[i];
    (membersOf[cid] = membersOf[cid] || []).push(i);
  }
  var topDomain = {};
  Object.keys(membersOf).forEach(function (cid) {
    var counts = {};
    membersOf[cid].forEach(function (n) {
      var d = domainOf(nodesRaw[n]);
      counts[d] = (counts[d] || 0) + 1;
    });
    var best = "";
    Object.keys(counts).sort().forEach(function (d) {
      if (!best || counts[d] > counts[best]) best = d;
    });
    topDomain[cid] = best;
  });

  var nodes = new vis.DataSet();
  var edges = new vis.DataSet();
  nodesRaw.forEach(function (key, id) {
    var dom = domainOf(key);
    var color = domainColor(dom);
    var d = degree[id] || 0;
    var hub = d >= 12;
    nodes.add({
      id: id,
      label: hub ? skillName(key) : "",
      size: hub ? 16 + Math.min(10, d * 0.5) : 4 + Math.min(4, d * 0.3),
      color: { background: "#05070d", border: color },
      borderWidth: hub ? 3 : 1.2,
      font: { color: "#e8f0ff", size: 11, face: "ui-monospace, Menlo, monospace" },
      shadow: hub ? { enabled: true, color: color, size: 18 } : { enabled: false }
    });
  });
  edgesRaw.forEach(function (e, id) {
    edges.add({ id: "e" + id, from: e[0], to: e[1], color: { color: "#1a2334" }, width: 0.6 });
  });

  var network = new vis.Network(netEl, { nodes: nodes, edges: edges }, {
    autoResize: true,
    interaction: { hover: false, dragNodes: false, dragView: true, zoomView: true },
    layout: { improvedLayout: false, randomSeed: 7 },
    physics: {
      solver: "barnesHut",
      barnesHut: { gravitationalConstant: -2600, centralGravity: 0.35, springLength: 90,
                   springConstant: 0.05, damping: 0.4, avoidOverlap: 0.15 },
      stabilization: { iterations: 200, fit: true }
    },
    nodes: { shape: "dot" },
    edges: { selectionWidth: 0, hoverWidth: 1 }
  });
  window.__intro = { network: network, nodes: nodes, eligible: eligibleIds };

  var reduceMotion = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
  var state = { domain: "", community: null, hovered: null, scale: 1 };
  var focusScale = 0.5;
  var hidden = nodesRaw.map(function () { return false; });

  function visible(id) {
    if (state.community !== null) return commOf[id] === state.community;
    if (state.domain) return domainOf(nodesRaw[id]) === state.domain;
    return !(state.scale >= focusScale && membersOf[commOf[id]].length < MIN_DOTS);
  }

  var scheduled = false;
  function applyVisibility() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      var updates = [];
      var count = 0;
      for (var id = 0; id < nodesRaw.length; id++) {
        var want = !visible(id);
        if (want !== hidden[id]) {
          hidden[id] = want;
          updates.push({ id: id, hidden: want });
        }
        if (want) count++;
      }
      if (updates.length) nodes.update(updates);
      if (state.hovered !== null && hidden[state.hovered]) hideCard();
      document.body.dataset.hidden = String(count);
      document.body.dataset.domain = state.domain;
      document.body.dataset.community = state.community === null ? "" : String(state.community);
    });
  }

  function eligibleIds() {
    var ids = [];
    for (var id = 0; id < nodesRaw.length; id++) if (visible(id)) ids.push(id);
    return ids;
  }

  function refit() {
    var ids = eligibleIds();
    if (!ids.length) return;
    network.fit({ nodes: ids, animation: false });
    network.moveTo({ scale: network.getScale() * 0.9,
                     animation: reduceMotion ? false
                       : { duration: 500, easingFunction: "easeInOutQuad" } });
  }

  var cardPinned = false;
  function showCard(kicker, title, meta, href, pinned) {
    cardPinned = !!pinned;
    cardEl.classList.toggle("is-pinned", cardPinned);
    cardKicker.textContent = kicker;
    cardTitle.textContent = title;
    cardMeta.textContent = meta;
    cardCta.setAttribute("href", href);
    cardEl.hidden = false;
  }
  function hideCard() {
    cardPinned = false;
    cardEl.classList.remove("is-pinned");
    cardEl.hidden = true;
    state.hovered = null;
  }
  function openCommunity(cid) {
    location.href = "./index.html?community=" + encodeURIComponent(cid);
  }

  function showSkill(id) {
    var key = nodesRaw[id];
    var cid = commOf[id];
    var comm = commById[cid];
    var label = comm ? comm.label : "community " + cid;
    var size = membersOf[cid] ? membersOf[cid].length : 0;
    showCard(
      domainLabel(domainOf(key)),
      skillName(key),
      skillCategory(key) + " · " + label + " (" + size + " skills) · " +
        (degree[id] || 0) + " relationships",
      "./index.html?community=" + encodeURIComponent(cid),
      false
    );
    document.body.dataset.hover = key;
  }

  function showCommunity(cid) {
    var comm = commById[cid];
    var size = membersOf[cid] ? membersOf[cid].length : 0;
    showCard(
      "Detected community",
      comm ? comm.label : "community " + cid,
      size + " skills · mostly " + domainLabel(topDomain[cid]) +
        " · hub " + (comm ? comm.hub : "—"),
      "./index.html?community=" + encodeURIComponent(cid),
      true
    );
    document.body.dataset.hover = "comm:" + cid;
  }

  function renderDomains() {
    var box = document.getElementById("domains");
    domainIds.forEach(function (id) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.setAttribute("aria-pressed", "false");
      chip.dataset.domain = id;
      var swatch = document.createElement("i");
      swatch.className = "domain-swatch domain-swatch--" + (domainIds.indexOf(id) % PALETTE.length);
      chip.appendChild(swatch);
      chip.appendChild(document.createTextNode(domainLabel(id)));
      chip.addEventListener("click", function () { selectDomain(id); });
      box.appendChild(chip);
    });
  }

  function selectDomain(id) {
    var next = state.domain === id ? "" : id;
    state.domain = next;
    state.community = null;
    hideCard();
    Array.prototype.forEach.call(
      document.querySelectorAll("#domains .chip"),
      function (chip) {
        chip.setAttribute("aria-pressed", String(chip.dataset.domain === next));
      }
    );
    crowdTitle.textContent = next ? domainLabel(next) : "All communities";
    crowdHint.textContent = next
      ? "Communities holding skills for this kind of work. Choose one to open it."
      : "Pick a kind of problem above, or choose a community.";
    applyVisibility();
    renderCrowd();
    refit();
  }

  function communitiesFor(domain) {
    return comms.filter(function (c) {
      if (!domain) return true;
      var members = membersOf[c.id] || [];
      return members.some(function (n) { return domainOf(nodesRaw[n]) === domain; });
    }).sort(function (a, b) {
      if (domain) {
        var na = (membersOf[a.id] || []).filter(function (n) {
          return domainOf(nodesRaw[n]) === domain;
        }).length;
        var nb = (membersOf[b.id] || []).filter(function (n) {
          return domainOf(nodesRaw[n]) === domain;
        }).length;
        if (na !== nb) return nb - na;
      }
      return b.size - a.size || String(a.label).localeCompare(String(b.label));
    });
  }

  function renderCrowd() {
    crowdList.textContent = "";
    var list = communitiesFor(state.domain);
    if (!list.length) {
      var empty = document.createElement("p");
      empty.className = "crowd__hint";
      empty.textContent = "No community in this kind of work.";
      crowdList.appendChild(empty);
      return;
    }
    list.forEach(function (c) {
      var members = membersOf[c.id] || [];
      var matching = state.domain
        ? members.filter(function (n) { return domainOf(nodesRaw[n]) === state.domain; })
        : members.slice();
      var item = document.createElement("button");
      item.type = "button";
      item.className = "crowd__item";
      item.dataset.comm = String(c.id);
      item.setAttribute("aria-current", String(state.community === c.id));
      var swatch = document.createElement("i");
      swatch.className = "domain-swatch domain-swatch--" +
        (domainIds.indexOf(topDomain[c.id]) % PALETTE.length);
      var name = document.createElement("span");
      name.className = "crowd__name";
      name.textContent = c.label;
      var why = document.createElement("span");
      why.className = "crowd__why";
      why.textContent = matching.slice(0, 3).map(function (n) {
        return skillName(nodesRaw[n]);
      }).join(", ");
      name.appendChild(why);
      var count = document.createElement("span");
      count.className = "crowd__n";
      count.textContent = state.domain
        ? matching.length + " of " + c.size
        : c.size + " skills";
      item.appendChild(swatch);
      item.appendChild(name);
      item.appendChild(count);
      item.addEventListener("click", function () { selectCommunity(c.id); });
      crowdList.appendChild(item);
    });
  }

  function selectCommunity(cid) {
    if (state.community === cid) {
      state.community = null;
      hideCard();
    } else {
      state.community = cid;
      showCommunity(cid);
    }
    applyVisibility();
    updateCrowdSelection();
    updateCrowdHint();
    refit();
  }

  function updateCrowdSelection() {
    Array.prototype.forEach.call(
      document.querySelectorAll("#crowd-list .crowd__item"),
      function (item) {
        item.setAttribute("aria-current", String(Number(item.dataset.comm) === state.community));
      }
    );
  }

  function updateCrowdHint() {
    var focused = state.community === null ? null : commById[state.community];
    crowdHint.textContent = focused
      ? "Focused: " + focused.label + ". Choose another community, or pick a kind of problem."
      : (state.domain
          ? "Communities holding skills for this kind of work. Choose one to open it."
          : "Pick a kind of problem above, or choose a community.");
  }

  var lastPointerType = "mouse";
  var downPoint = null;
  netEl.addEventListener("pointerdown", function (event) {
    lastPointerType = event.pointerType || "mouse";
    if (lastPointerType === "touch") document.body.classList.add("is-touch");
    downPoint = { x: event.clientX, y: event.clientY };
  });

  function nearest(event) {
    var positions = network.getPositions();
    var rect = netEl.getBoundingClientRect();
    var x = event.clientX - rect.left;
    var y = event.clientY - rect.top;
    var best = null;
    var bestDistance = 16;
    for (var id = 0; id < nodesRaw.length; id++) {
      if (hidden[id] || !positions[id]) continue;
      var point = network.canvasToDOM(positions[id]);
      var dx = point.x - x;
      var dy = point.y - y;
      var distance = Math.sqrt(dx * dx + dy * dy);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = id;
      }
    }
    return best;
  }

  netEl.addEventListener("pointermove", function (event) {
    if (event.pointerType === "touch" || cardPinned) return;
    var id = nearest(event);
    if (id === state.hovered) return;
    state.hovered = id;
    if (id === null) hideCard();
    else showSkill(id);
  });
  netEl.addEventListener("pointerleave", function () {
    if (lastPointerType !== "touch" && !cardPinned) hideCard();
  });

  netEl.addEventListener("pointerup", function (event) {
    if (!downPoint) return;
    var dx = event.clientX - downPoint.x;
    var dy = event.clientY - downPoint.y;
    downPoint = null;
    if (Math.sqrt(dx * dx + dy * dy) > 6) return;
    var id = nearest(event);
    if (id === null) {
      if (cardPinned) hideCard();
      return;
    }
    if (lastPointerType === "touch") {
      state.hovered = id;
      showSkill(id);
      return;
    }
    openCommunity(commOf[id]);
  });

  function onZoom() {
    state.scale = network.getScale();
    document.body.dataset.scale = state.scale.toFixed(3);
    applyVisibility();
  }
  network.on("zoom", onZoom);
  network.on("animationFinished", onZoom);

  var booted = false;
  function boot() {
    if (booted) return;
    booted = true;
    var loading = document.getElementById("loading");
    if (loading) loading.remove();
    state.scale = network.getScale();
    focusScale = Math.max(0.35, state.scale * 2.5);
    document.body.dataset.scale = state.scale.toFixed(3);
    document.body.dataset.fitScale = state.scale.toFixed(3);
    document.body.dataset.focusScale = focusScale.toFixed(3);
    document.body.dataset.ready = "true";
    renderDomains();
    renderCrowd();
    applyVisibility();
    network.moveTo({ scale: state.scale * 0.9,
                     animation: reduceMotion ? false
                       : { duration: 700, easingFunction: "easeInOutQuad" } });
  }

  network.once("stabilized", boot);
  setTimeout(function () {
    if (document.body.dataset.ready !== "true") boot();
  }, 4000);

  document.getElementById("stat-line").textContent =
    (SK.total || nodesRaw.length) + " skills · " +
    edgesRaw.length.toLocaleString() + " relationships · " +
    comms.length + " communities · " + (SK.solutions || 0) + " solutions";
})();
