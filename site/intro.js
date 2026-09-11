(function () {
  "use strict";
  var SK = window.SKILLDATA || {};
  var nodesRaw = SK.nodes || [], edgesRaw = SK.edges || [];
  var catDomain = SK.catDomain || {}, domains = Object.keys(SK.domains || {});
  var comms = SK.comms || [];
  var PALETTE = ["#00e5ff","#ff2ea6","#8a63ff","#ffd166","#3ddc97","#ff8c5a","#5aa9ff"];

  // degrees
  var deg = {};
  edgesRaw.forEach(function (e) { deg[e[0]] = (deg[e[0]] || 0) + 1; deg[e[1]] = (deg[e[1]] || 0) + 1; });

  var nodes = new vis.DataSet();
  var edges = new vis.DataSet();
  var byLabel = {};
  nodesRaw.forEach(function (nid, i) {
    var parts = nid.split("~~");
    var cat = parts.length > 1 ? parts[0] : nid.split("/")[0];
    var name = parts[parts.length - 1];
    var dom = catDomain[cat] || "other";
    var color = PALETTE[domains.indexOf(dom) % PALETTE.length] || "#8492b0";
    var d = deg[i] || 0;
    var god = d >= 12;
    nodes.add({
      id: i, label: name,
      size: god ? 16 + Math.min(10, d * 0.5) : 4 + Math.min(4, d * 0.3),
      color: { background: "#05070d", border: color },
      borderWidth: god ? 3 : 1.2,
      font: god ? { color: "#e8f0ff", size: 11, face: "ui-monospace, Menlo, monospace" }
                : { color: "#5a6684", size: 8, face: "ui-monospace, Menlo, monospace" },
      shadow: god ? { enabled: true, color: color, size: 18 } : { enabled: false }
    });
    byLabel[name] = i;
  });
  edgesRaw.forEach(function (e, i) {
    edges.add({ id: "e" + i, from: e[0], to: e[1], color: { color: "#1a2334" }, width: 0.6 });
  });

  var network = new vis.Network(document.getElementById("net"), { nodes: nodes, edges: edges }, {
    autoResize: true,
    interaction: { hover: true, dragNodes: true, dragView: true, zoomView: true },
    layout: { improvedLayout: false },
    physics: {
      solver: "barnesHut",
      barnesHut: { gravitationalConstant: -2600, centralGravity: 0.35, springLength: 90,
                   springConstant: 0.05, damping: 0.4, avoidOverlap: 0.15 },
      stabilization: { iterations: 200, fit: true }
    },
    nodes: { shape: "dot" },
    edges: { selectionWidth: 0, hoverWidth: 1 }
  });

  // insert community beats before the zoomout section, from the real comms
  var main = document.getElementById("main");
  var zoom = document.getElementById("enter");
  var top = comms.slice().sort(function (a, b) { return b.size - a.size; }).slice(0, 4);
  top.forEach(function (c, idx) {
    var sec = document.createElement("section");
    sec.setAttribute("data-view", "comm:" + c.hub);
    var card = document.createElement("div");
    card.className = "card" + (idx % 2 ? " right" : "");
    card.innerHTML = '<div class="kicker">community · ' + c.size + ' skills</div>' +
      '<h2>' + c.label + '</h2>' +
      '<p class="lede">Its hub is <b>' + c.hub + '</b> — the skill the rest of this community connects through. Scroll on.</p>';
    sec.appendChild(card);
    main.insertBefore(sec, zoom);
  });
  document.getElementById("stat-line").innerHTML =
    "<b>" + (SK.total || nodesRaw.length) + "</b> skills · <b>" + edgesRaw.length.toLocaleString() +
    "</b> relationships · <b>" + comms.length + "</b> communities · <b>" + (SK.solutions || 50) + "</b> solutions";

  // domain legend
  var lg = document.getElementById("domlegend");
  domains.forEach(function (d, i) {
    lg.innerHTML += '<div><i style="background:' + PALETTE[i % PALETTE.length] + '"></i>' + d + "</div>";
  });

  // scroll-driven camera
  var beats = Array.prototype.slice.call(document.querySelectorAll("section[data-view]"));
  var views = { sea: { scale: 0.26, pos: { x: 0, y: 0 } }, zoomout: { scale: 0.42, pos: { x: 0, y: 0 } } };
  var cur = -1;
  function activeIdx() {
    for (var i = beats.length - 1; i >= 0; i--) {
      if (beats[i].getBoundingClientRect().top <= window.innerHeight * 0.5) return i;
    }
    return 0;
  }
  function setBeat(i) {
    if (i === cur) return; cur = i;
    var v = beats[i].getAttribute("data-view");
    if (views[v]) {
      network.moveTo({ position: views[v].pos, scale: views[v].scale,
        animation: { duration: 900, easingFunction: "easeInOutQuad" } });
    } else if (v.indexOf("comm:") === 0) {
      var id = byLabel[v.slice(5)];
      if (id !== undefined) network.focus(id, { scale: 1.05,
        animation: { duration: 950, easingFunction: "easeInOutQuad" } });
    }
  }
  window.addEventListener("scroll", function () { setBeat(activeIdx()); }, { passive: true });
  function hideLoading() { var el = document.getElementById("loading"); if (el) el.remove(); }
  network.once("stabilized", function () { hideLoading(); setBeat(0); });
  setTimeout(hideLoading, 3500);
  setTimeout(function () { setBeat(0); }, 3600);
})();
