/*
 * Behaviour layer for the skill library.
 *
 * This script attaches to markup build.py has already prerendered. It never
 * creates a node, a card or a rail link: the page must be complete for a crawler
 * and usable with JavaScript disabled, so the DOM is the source of truth and this
 * file is an enhancement over it.
 *
 * Two distinct layers, deliberately separated:
 *
 *   Graph interaction — hover, focus, search, provenance filters. This is
 *   FUNCTION, not decoration, so it runs everywhere: on mobile, under
 *   prefers-reduced-motion, and with GSAP missing. Withholding search from
 *   someone because they asked for less animation would be absurd.
 *
 *   Scroll traversal — pinning the stage and stepping the highlight from one
 *   Solution to the next. This is motion, so it is the part that bails out.
 *
 * Nothing here counts a number up from zero. The headline states the size of the
 * library, and a headline's resting state should not be a false statement.
 */
(function () {
  "use strict";

  // Matches the stylesheet's stacking breakpoint. Below it the stage is a single
  // column with its own height, so there is nothing to pin: pinning a stage taller
  // than the viewport hides its own controls for the length of the pin.
  var MOBILE = 1000;
  // The pin also needs vertical room, and must agree exactly with the media query
  // in styles.css that stacks the stage. If these two disagree, one of them
  // pins a layout the other has already reflowed.
  var SHORT = 720;

  function wide() {
    return window.innerWidth > MOBILE && window.innerHeight > SHORT;
  }
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var DATA = window.SKILLDATA || {};

  var stage = document.getElementById("top");
  var svg = document.getElementById("gsvg");
  var panel = {
    tier: document.getElementById("paneltier"),
    name: document.getElementById("panelname"),
    desc: document.getElementById("paneldesc"),
    chain: document.getElementById("panelchain"),
    ev: document.getElementById("panelev")
  };
  var search = document.getElementById("gsearch");
  var chips = document.getElementById("gchips");
  // How many of the drawn relationships the repository states outright, rather than
  // this page having derived them. Reported rather than assumed.
  var STATED_COUNT = (DATA.edges || []).filter(function (e) {
    return e[3] === 0;
  }).length;
  var resetBtn = document.getElementById("greset");
  var beats = document.getElementById("beats");
  var bar = document.getElementById("bar");
  var rail = document.getElementById("rail");
  var cue = document.getElementById("cue");

  if (!stage || !svg) return;

  /* --------------------------------------------------------------- the graph
   * 490 skills, 1,868 relationships, communities detected rather than declared.
   *
   * Everything is prerendered and positioned by the build. What happens here is
   * reading: which nodes neighbour this one, which community is this, how do these two
   * connect, and what is the evidence for each edge.
   */

  var nodes = Array.prototype.slice.call(svg.querySelectorAll(".g-node"));
  var edges = Array.prototype.slice.call(svg.querySelectorAll(".g-edge"));
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var sols = Array.prototype.slice.call(document.querySelectorAll(".sol"));
  var viewport = document.getElementById("vp");

  var nodeByKey = {};
  nodes.forEach(function (n) {
    nodeByKey[n.getAttribute("data-key")] = n;
  });

  // Labels live in their own layer so they paint above every node and edge — SVG has no
  // z-index — so they are keyed and toggled alongside the node they belong to.
  var labelByKey = {};
  Array.prototype.slice.call(svg.querySelectorAll(".g-nlabel")).forEach(function (el) {
    labelByKey[el.getAttribute("data-key")] = el;
  });
  var commLabels = Array.prototype.slice.call(svg.querySelectorAll(".g-clabel"));

  // How many names to reveal at once. Every skill has a label element, but 50 of them
  // drawn at their node positions overlap into a grey wash — the fault the first version
  // of this graph shipped with. Ten is about what fits without collisions at the zoom
  // the camera settles on.
  var NAME_CAP = 10;

  /* The adjacency, rebuilt once from the integers in data.js.
   *
   * The DOM knows which two nodes an edge joins, but answering "what are this node's
   * neighbours" from the DOM means walking 1,868 elements per hover, and answering "how
   * do these two connect" means a search over them. The graph is small; an index is
   * cheap and makes both immediate.
   */
  var GKEYS = DATA.nodes || [];
  var GEDGES = DATA.edges || [];
  // Why each relationship is drawn, in the same order as the edges. Shown in the panel
  // beside each connection: "led by Idea to shipped code", "siblings in stitch", 'names
  // share "cro"'. This was emitted and never read for one build — 52 KB of the 103 KB data
  // file was an explanation the page had no way to show, while a comment claimed it said
  // what an edge is when you select it.
  var GWHY = DATA.why || [];
  var adj = {};
  var edgeByPair = {};
  GKEYS.forEach(function (k) {
    adj[k] = [];
  });
  GEDGES.forEach(function (e, i) {
    var a = GKEYS[e[0]];
    var b = GKEYS[e[1]];
    if (a === undefined || b === undefined) return;
    adj[a].push({ to: b, w: e[2], kind: e[3], i: i });
    adj[b].push({ to: a, w: e[2], kind: e[3], i: i });
    edgeByPair[a + "|" + b] = i;
    edgeByPair[b + "|" + a] = i;
  });
  var edgeEl = {};
  edges.forEach(function (el) {
    edgeEl[el.getAttribute("data-i")] = el;
  });

  var beatItems = beats
    ? Array.prototype.slice.call(beats.querySelectorAll(".beat"))
    : [];

  var solByKey = {};
  sols.forEach(function (el) {
    var key = el.getAttribute("data-sol");
    if (!key) return;
    solByKey[key] = {
      el: el,
      tier: el.getAttribute("data-tier") || "",
      label: (el.querySelector("h3") || {}).textContent || key,
      problem: (el.querySelector(".sol__problem") || {}).textContent || ""
    };
  });
  var cardByKey = {};
  cards.forEach(function (c) {
    cardByKey[c.getAttribute("data-id")] = c;
  });
  var commByIdMeta = {};
  (DATA.comms || []).forEach(function (c) {
    commByIdMeta[c.id] = c;
  });

  /* ------------------------------------------------------------------ the camera
   * A previous version of this page had no camera on purpose, because the first one
   * caused three faults: labels grew with the zoom until they collided, a node sliding
   * under a stationary cursor fired mouseenter and stole the selection the reader had
   * just clicked, and anything outside the frame became unreachable.
   *
   * All three are fixable and worth fixing — 490 nodes in one frame is an overview, and
   * an overview you cannot go into is a picture. So: labels divide their size by the
   * zoom factor in CSS, hover is ignored while the camera is moving, and Escape, the
   * Reset button and a click on the background all pull back out.
   */

  // Read from the graph itself rather than restated here. The two disagreed once —
  // the layout used 620 where the viewBox declared 560 — and twenty-nine skills were
  // positioned in a band the browser clips away: highlighted, labelled, counted in the
  // panel, and invisible.
  var VB = { w: 1400, h: 560 };
  if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) {
    VB = { w: svg.viewBox.baseVal.width, h: svg.viewBox.baseVal.height };
  }
  /* The part of the frame nothing is sitting on top of.
   *
   * The stage carries five overlays — the headline, the panel, the category rail, the
   * search row and the community chips — and the graph is sized to sit clear of all of
   * them, so this is a margin rather than a cut-out. It exists because framing a
   * community into the exact middle of the frame put its outermost nodes half off the
   * edge, where they were highlighted, labelled, and unclickable.
   */
  var SAFE = {
    x0: VB.w * 0.03,
    y0: VB.h * 0.05,
    x1: VB.w * 0.97,
    y1: VB.h * 0.94
  };
  SAFE.w = SAFE.x1 - SAFE.x0;
  SAFE.h = SAFE.y1 - SAFE.y0;
  SAFE.cx = (SAFE.x0 + SAFE.x1) / 2;
  SAFE.cy = (SAFE.y0 + SAFE.y1) / 2;
  var cam = { k: 1, x: 0, y: 0 };
  var camMoving = false;
  var camTimer = null;

  function applyCam() {
    if (!viewport) return;
    viewport.style.transform =
      "translate(" + cam.x + "px," + cam.y + "px) scale(" + cam.k + ")";
    // Everything measured in user units — the labels — divides by this.
    viewport.style.setProperty("--k", String(cam.k));
    stage.classList.toggle("is-zoomed", cam.k > 1.02);
  }

  function moveCam(k, cx, cy) {
    k = Math.max(1, Math.min(6, k));
    cam.k = k;
    // Clamped so the content cannot be dragged off the edge of its own frame.
    var maxX = VB.w * (k - 1);
    var maxY = VB.h * (k - 1);
    cam.x = Math.max(-maxX, Math.min(0, SAFE.cx - cx * k));
    cam.y = Math.max(-maxY, Math.min(0, SAFE.cy - cy * k));
    applyCam();

    // Hover is suppressed until the move finishes. This is the fix for the fault that
    // killed the first camera: while the transform eases, nodes slide under a cursor
    // that has not moved, each firing mouseenter, and the selection the reader clicked
    // is replaced by whatever happened to pass beneath the pointer.
    camMoving = true;
    clearTimeout(camTimer);
    camTimer = setTimeout(function () {
      camMoving = false;
    }, reduced ? 0 : 660);
  }

  function frameNodes(list, pad) {
    if (!list.length) {
      moveCam(1, VB.w / 2, VB.h / 2);
      return;
    }
    var x0 = Infinity;
    var y0 = Infinity;
    var x1 = -Infinity;
    var y1 = -Infinity;
    list.forEach(function (n) {
      var x = +n.getAttribute("data-x");
      var y = +n.getAttribute("data-y");
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    });
    pad = pad === undefined ? 46 : pad;
    var w = Math.max(60, x1 - x0) + pad * 2;
    var h = Math.max(60, y1 - y0) + pad * 2;
    moveCam(Math.min(SAFE.w / w, SAFE.h / h), (x0 + x1) / 2, (y0 + y1) / 2);
  }

  function resetCam() {
    moveCam(1, VB.w / 2, VB.h / 2);
  }

  // Clicking the empty background pulls back out, which is the gesture people try
  // first and the answer to "anything outside the frame is unreachable".
  svg.addEventListener("click", function (e) {
    if (e.target.closest(".g-node") || e.target.closest(".g-clabel")) return;
    if (cam.k > 1.02) resetCam();
  });

  /* ------------------------------------------------------------------- panel */

  function setChain(items) {
    if (!panel.chain) return;
    // Rebuilt element by element rather than assigned as innerHTML: these strings come
    // from skill frontmatter, and textContent cannot be talked into becoming markup.
    while (panel.chain.firstChild) panel.chain.removeChild(panel.chain.firstChild);
    items.forEach(function (text) {
      var li = document.createElement("li");
      li.textContent = text;
      panel.chain.appendChild(li);
    });
  }

  function nameOf(key) {
    var n = nodeByKey[key];
    return n ? n.getAttribute("data-name") : key;
  }

  function explainNode(key) {
    var node = nodeByKey[key];
    if (!node) return;
    var card = cardByKey[key];
    var desc = card ? card.querySelector("p") : null;
    var cid = +node.getAttribute("data-comm");
    var meta = commByIdMeta[cid];
    var neighbours = (adj[key] || []).slice().sort(function (a, b) {
      if (b.w !== a.w) return b.w - a.w;
      return nameOf(a.to) < nameOf(b.to) ? -1 : 1;
    });
    var stated = neighbours.filter(function (e) {
      return e.kind === 0;
    }).length;

    if (panel.tier) {
      panel.tier.textContent = meta ? "in " + meta.label : "unconnected";
    }
    if (panel.name) panel.name.textContent = node.getAttribute("data-name");
    if (panel.desc) panel.desc.textContent = desc ? desc.textContent : "";
    // Each connection with the evidence for it, because "connected" on its own is a claim
    // the reader cannot check. An inferred edge says which words the two names share, which
    // is also the honest way to show how weak that kind of edge is.
    setChain(
      neighbours.slice(0, 12).map(function (e) {
        var why = GWHY[e.i] && GWHY[e.i].length ? GWHY[e.i][0] : "";
        var other = nameOf(e.to);
        // A Solution named after its own lead otherwise reads "automate-me \u2014 led by
        // automate-me", which is a sentence that tells the reader nothing twice.
        if (why === "led by " + other) why = "leads it";
        return other + (why ? " \u2014 " + why : "");
      })
    );
    if (panel.ev) {
      var domain = (DATA.domains || {})[(DATA.catDomain || {})[node.getAttribute("data-dom")]];
      panel.ev.textContent =
        neighbours.length +
        " connections, " +
        stated +
        " stated" +
        (domain ? " · filed under " + domain : "");
    }
  }

  function explainCommunity(cid) {
    var meta = commByIdMeta[cid];
    if (!meta) return;
    var members = nodes.filter(function (n) {
      return +n.getAttribute("data-comm") === cid;
    });
    if (panel.tier) panel.tier.textContent = "community";
    if (panel.name) panel.name.textContent = meta.label;
    if (panel.desc) {
      panel.desc.textContent =
        meta.size +
        " skills grouped by what their names and their Solutions say they have in " +
        "common, not by where they are filed. " +
        // "Most connected", which is what degree measures. This said "everything here runs
        // through X", which claims betweenness or an articulation point and was not
        // computed: in the largest community the top node has six in-community neighbours
        // and removing it leaves the rest in one piece. The prerendered copy of this
        // sentence in build.py was corrected and this one was missed, so the live page said
        // both things depending on whether you had clicked anything.
        "Its most connected member is " +
        meta.hub +
        ".";
    }
    setChain(
      members
        .slice()
        .sort(function (a, b) {
          return +b.getAttribute("data-deg") - +a.getAttribute("data-deg");
        })
        .slice(0, 12)
        .map(function (n) {
          return n.getAttribute("data-name");
        })
    );
    if (panel.ev) {
      var doms = {};
      members.forEach(function (n) {
        doms[(DATA.catDomain || {})[n.getAttribute("data-dom")]] = true;
      });
      var spread = Object.keys(doms).length;
      panel.ev.textContent =
        meta.size +
        " skills · most connected: " +
        meta.hub +
        (spread > 1 ? " · spans " + spread + " declared domains" : "");
    }
  }

  /* Placing the names that are revealed on demand.
   *
   * The build places the 26 default names so none of them collide, but it cannot place
   * the other 464: which ones appear depends on what the reader selects. Ten names
   * revealed at their nodes' own offsets inside one dense community landed on top of
   * each other — six overlapping words where six readable ones were intended.
   *
   * So the same greedy placement the build does, done here for the handful being
   * revealed: four candidate positions per name, first one that clears the names already
   * placed wins, and a name with nowhere to go is not shown. Every measurement is divided
   * by the zoom factor, because that is what the labels' own font size is divided by.
   */

  var labelHome = {};
  Object.keys(labelByKey).forEach(function (k) {
    var el = labelByKey[k];
    labelHome[k] = {
      x: el.getAttribute("x"),
      y: el.getAttribute("y"),
      a: el.getAttribute("text-anchor") || "start"
    };
  });

  // Only a fallback: getComputedTextLength below measures the real advance width. Kept
  // deliberately generous so that if it were ever used it over-reserves rather than under.
  var CHAR_W = DATA.charw || {};
  var CHAR_W_FALLBACK = DATA.charwFallback || 0.62;
  var LABEL_FONT = DATA.labelFont || 9.5;
  var LABEL_H = DATA.labelHeight || 12.4;

  // The width a name will occupy, computed rather than measured.
  //
  // getComputedTextLength is exact but reads the current layout, and the camera has just
  // changed the zoom factor that these labels' font size divides by. In the same tick the
  // browser could still answer from the layout before that recalculation, which is why one
  // pair of names overlapped at 1280 wide and not at 1440. Arithmetic on the table the build
  // uses has no such dependence, and gives the same answer to within 0.01%.
  function textWidth(text, font) {
    var w = 0;
    for (var i = 0; i < text.length; i++) {
      var c = CHAR_W[text.charAt(i)];
      w += c === undefined ? CHAR_W_FALLBACK : c;
    }
    return w * font;
  }
  // Labels must clear each other, not merely fail to intersect. Two names a fifth of a
  // unit apart read as one word.
  var LABEL_GAP = 1.8;

  function homeLabels() {
    Object.keys(labelByKey).forEach(function (k) {
      var el = labelByKey[k];
      var h = labelHome[k];
      el.setAttribute("x", h.x);
      el.setAttribute("y", h.y);
      el.setAttribute("text-anchor", h.a);
      // Both classes come off here. Moving a label back to where the build put it while
      // leaving it lit is how a previous search kept its names on screen underneath the
      // next one's: searching "review" then "agent" left eleven overlapping names, none
      // of which matched the query being typed.
      el.classList.remove("is-on", "is-hit");
    });
  }

  function light(keys, cls) {
    homeLabels();
    var k = cam.k || 1;
    var boxes = [];
    // The community names stay on screen while a selection is up, dimmed but legible, so
    // they are reserved before any skill name is offered a position.
    // The community names stay on screen while a selection is up, dimmed but legible, so
    // they are reserved before any skill name is offered a position. Their boxes come from
    // the same arithmetic and their own font size, which is larger than a skill name's.
    var commFont = (DATA.communityFont || 11.5) / k;
    commLabels.forEach(function (cl) {
      if (getComputedStyle(cl).opacity === "0") return;
      var cw = textWidth(cl.textContent, commFont);
      var ch = (LABEL_H * (DATA.communityFont || 11.5)) / LABEL_FONT / k;
      var cxx = +cl.getAttribute("x");
      var cyy = +cl.getAttribute("y");
      boxes.push([cxx - cw / 2, cyy - ch * 0.78, cxx + cw / 2, cyy + ch * 0.22]);
    });
    keys.forEach(function (key) {
      var el = labelByKey[key];
      var node = nodeByKey[key];
      if (!el || !node) return;
      var x = +node.getAttribute("data-x");
      var y = +node.getAttribute("data-y");
      var dot = node.querySelector(".g-dot");
      var r = dot ? +dot.getAttribute("r") : 3;
      var w = textWidth(el.textContent, LABEL_FONT / k);
      var h = LABEL_H / k;
      var options = [
        [x + r + 4 / k, y + (3.2 / k), "start"],
        [x - r - 4 / k, y + (3.2 / k), "end"],
        [x, y - r - 5 / k, "middle"],
        [x, y + r + h, "middle"]
      ];
      for (var i = 0; i < options.length; i++) {
        var ox = options[i][0];
        var oy = options[i][1];
        var anchor = options[i][2];
        var x0 = anchor === "start" ? ox : anchor === "end" ? ox - w : ox - w / 2;
        var box = [x0, oy - h * 0.78, x0 + w, oy + h * 0.22];
        // Inside the frame the browser will actually draw. The build-time placer tests this
        // and this one did not, so selecting a node near the right edge pushed its name out
        // to x=1503 in a 1400-wide viewBox: no overlap, because the label was not on screen
        // at all. Four nodes did it on selection and ten ordinary searches reproduced it.
        if (box[0] < 2 || box[2] > VB.w - 2 || box[1] < 2 || box[3] > VB.h - 2) continue;
        var clash = false;
        for (var j = 0; j < boxes.length; j++) {
          var o = boxes[j];
          if (
            box[0] < o[2] + LABEL_GAP &&
            o[0] < box[2] + LABEL_GAP &&
            box[1] < o[3] + LABEL_GAP &&
            o[1] < box[3] + LABEL_GAP
          ) {
            clash = true;
            break;
          }
        }
        if (clash) continue;
        el.setAttribute("x", ox);
        el.setAttribute("y", oy);
        el.setAttribute("text-anchor", anchor);
        el.classList.add(cls);
        boxes.push(box);
        return;
      }
    });
  }

  /* ------------------------------------------------------------------ reading */

  var focused = null;
  var pinned = null;
  var openComm = null;
  var pathEnds = [];

  function mark() {
    stage.setAttribute("data-pinned", pinned || "");
    stage.setAttribute("data-focused", focused || "");
    stage.setAttribute("data-comm", openComm === null ? "" : String(openComm));
    stage.setAttribute("data-path", pathEnds.join(" "));
  }

  function clearClasses() {
    nodes.forEach(function (n) {
      n.classList.remove("is-on", "is-self", "is-hit", "is-path", "is-path-end");
    });
    edges.forEach(function (e) {
      e.classList.remove("is-on", "is-path");
    });
    Object.keys(labelByKey).forEach(function (k) {
      labelByKey[k].classList.remove("is-on", "is-hit");
    });
    commLabels.forEach(function (l) {
      l.classList.remove("is-on");
    });
  }

  function focus(key, opts) {
    opts = opts || {};
    if (!nodeByKey[key]) return;
    if (opts.pin) pinned = key;
    focused = key;
    pathEnds = [];

    clearClasses();
    stage.classList.remove("is-dim", "is-path");
    stage.classList.add("is-focus");

    var self = nodeByKey[key];
    self.classList.add("is-on", "is-self");
    var cid = self.getAttribute("data-comm");
    commLabels.forEach(function (l) {
      l.classList.toggle("is-on", l.getAttribute("data-comm") === cid);
    });

    // Every neighbour is highlighted; only the strongest few are named. A hub has 23
    // neighbours, and 23 names at their node positions overlap into a smudge.
    var nb_sorted = (adj[key] || []).slice().sort(function (x, y) {
      if (y.w !== x.w) return y.w - x.w;
      return x.to < y.to ? -1 : 1;
    });
    nb_sorted.forEach(function (e) {
      var nb = nodeByKey[e.to];
      if (nb) nb.classList.add("is-on");
      var el = edgeEl[e.i];
      if (el) el.classList.add("is-on");
    });
    // The selection first, so its own name is never the one that fails to fit.
    light(
      [key].concat(
        nb_sorted.slice(0, NAME_CAP).map(function (e) {
          return e.to;
        })
      ),
      "is-on"
    );

    sols.forEach(function (s) {
      s.classList.toggle("is-on", s.getAttribute("data-sol") === key);
    });
    cards.forEach(function (c) {
      c.classList.toggle("is-on", c.getAttribute("data-id") === key);
    });

    explainNode(key);
    mark();
  }

  function showCommunity(cid, opts) {
    opts = opts || {};
    openComm = cid;
    pinned = null;
    focused = null;
    pathEnds = [];
    clearClasses();
    stage.classList.remove("is-dim", "is-path");
    stage.classList.add("is-focus");

    var mine = nodes.filter(function (n) {
      return +n.getAttribute("data-comm") === cid;
    });
    nodes.forEach(function (n) {
      n.classList.toggle("is-on", mine.indexOf(n) > -1);
    });
    // The strongest handful get named. The rest are readable by hovering them, which is
    // the trade that keeps the names legible instead of a wash of overlapping text.
    var named = mine
      .slice()
      .sort(function (a, b) {
        return +b.getAttribute("data-deg") - +a.getAttribute("data-deg");
      })
      .slice(0, NAME_CAP)
      .map(function (n) {
        return n.getAttribute("data-key");
      });
    // The camera moves first. Label positions and widths are both measured at the
    // current zoom — the offsets are divided by it and the font size is divided by it —
    // so placing names and then zooming means every measurement was taken against the
    // wrong scale, which is where the last few collisions came from.
    // Framing is what selecting does, not what arriving does. The page's opening image is
    // the whole library with its largest community named — zooming straight in on one
    // cluster hides the thing the page is trying to show, and makes every node outside
    // that cluster unclickable before the reader has done anything.
    if (opts.frame !== false) frameNodes(mine);
    light(named, "is-on");
    edges.forEach(function (e) {
      var a = nodeByKey[e.getAttribute("data-a")];
      var b = nodeByKey[e.getAttribute("data-b")];
      e.classList.toggle(
        "is-on",
        !!a && !!b &&
          +a.getAttribute("data-comm") === cid &&
          +b.getAttribute("data-comm") === cid
      );
    });
    commLabels.forEach(function (l) {
      l.classList.toggle("is-on", +l.getAttribute("data-comm") === cid);
    });
    beatItems.forEach(function (b) {
      b.classList.toggle("is-on", +b.getAttribute("data-comm") === cid);
    });
    explainCommunity(cid);
    mark();
  }

  /* --------------------------------------------------------------------- path
   * Graphify traces how any two things connect; this does the same over the skill
   * graph. Breadth-first and unweighted, because "how many steps from here to there"
   * is the question, and a strong edge is not a shorter one.
   */

  function shortestPath(a, b) {
    if (a === b) return [a];
    var prev = {};
    prev[a] = null;
    var queue = [a];
    var head = 0;
    while (head < queue.length) {
      var cur = queue[head++];
      var out = (adj[cur] || []).slice().sort(function (x, y) {
        return x.to < y.to ? -1 : 1;
      });
      for (var i = 0; i < out.length; i++) {
        var nb = out[i].to;
        if (nb in prev) continue;
        prev[nb] = cur;
        if (nb === b) {
          var path = [nb];
          while (prev[path[path.length - 1]] !== null) {
            path.push(prev[path[path.length - 1]]);
          }
          return path.reverse();
        }
        queue.push(nb);
      }
    }
    return [];
  }

  function showPath(a, b) {
    var path = shortestPath(a, b);
    clearClasses();
    stage.classList.remove("is-focus", "is-dim");
    focused = null;
    pinned = null;

    if (!path.length) {
      stage.classList.remove("is-path");
      if (panel.tier) panel.tier.textContent = "no path";
      if (panel.name) panel.name.textContent = nameOf(a) + " → " + nameOf(b);
      if (panel.desc) {
        panel.desc.textContent =
          "Nothing in the library connects these two, directly or through anything " +
          "else. One of them is on the frontier: 34 skills belong to no Solution and " +
          "share a subject with nothing.";
      }
      setChain([]);
      if (panel.ev) panel.ev.textContent = "not connected";
      pathEnds = [a, b];
      mark();
      return;
    }

    stage.classList.add("is-path");
    // Framing the route is the whole reason the camera exists here: two ends five hops
    // apart can sit in opposite corners of the frame.
    frameNodes(
      path
        .map(function (k) {
          return nodeByKey[k];
        })
        .filter(Boolean),
      64
    );
    light(path, "is-on");
    path.forEach(function (k, i) {
      var n = nodeByKey[k];
      if (n) n.classList.add("is-path");
      if (i === 0 || i === path.length - 1) {
        if (n) n.classList.add("is-path-end");
      }
      if (i > 0) {
        var el = edgeEl[edgeByPair[path[i - 1] + "|" + k]];
        if (el) el.classList.add("is-path");
      }
    });

    if (panel.tier) panel.tier.textContent = path.length - 1 + " hops";
    if (panel.name) panel.name.textContent = nameOf(a) + " → " + nameOf(b);
    if (panel.desc) {
      panel.desc.textContent =
        "The shortest route between them in the library, one relationship per step.";
    }
    setChain(
      path.map(function (k) {
        return nameOf(k);
      })
    );
    if (panel.ev) {
      var stated = 0;
      for (var i = 1; i < path.length; i++) {
        var idx = edgeByPair[path[i - 1] + "|" + path[i]];
        if (GEDGES[idx] && GEDGES[idx][3] === 0) stated++;
      }
      panel.ev.textContent =
        path.length - 1 + " steps, " + stated + " of them stated by the repository";
    }
    pathEnds = [a, b];
    mark();
  }

  function clearFocus() {
    focused = null;
    pinned = null;
    pathEnds = [];
    clearClasses();
    stage.classList.remove("is-focus", "is-dim", "is-path");
    sols.forEach(function (s) {
      s.classList.remove("is-on");
    });
    cards.forEach(function (c) {
      c.classList.remove("is-hit", "is-on");
    });
    beatItems.forEach(function (b) {
      b.classList.remove("is-on");
    });
    if (openComm !== null) {
      explainCommunity(openComm);
    }
    mark();
  }

  /* ------------------------------------------------------------- node events */

  var pathMode = false;
  var pathBtn = document.getElementById("gpath");

  function setPathMode(on) {
    pathMode = on;
    pathEnds = [];
    if (on) {
      // Back to the whole library, and nothing dimmed. Picking two skills means both
      // have to be clickable, and while the camera was framing one community every node
      // outside it was off the edge of the view: the second pick was impossible.
      openComm = null;
      clearClasses();
      stage.classList.remove("is-focus", "is-dim", "is-path");
      resetCam();
    }
    if (pathBtn) pathBtn.setAttribute("aria-pressed", on ? "true" : "false");
    if (stage) stage.classList.toggle("is-picking", on);
    // Also on the document element: the category rail sits outside the stage, so a
    // stage-scoped rule cannot reach it.
    document.documentElement.classList.toggle("is-picking", on);
    if (on && panel.tier) {
      panel.tier.textContent = "trace";
      if (panel.name) panel.name.textContent = "Pick two skills";
      if (panel.desc) {
        panel.desc.textContent =
          "Click one node, then another, and the shortest route between them lights up.";
      }
      setChain([]);
      if (panel.ev) panel.ev.textContent = "waiting for the first";
    }
    mark();
  }

  /* One tab stop for the graph, not 490.
   *
   * Every node is a real link, which is what makes the graph a table of contents with
   * JavaScript off. With JavaScript on that same fact put 490 sequential stops in the tab
   * order — an independent review counted 1,025 focusables on the page — so reaching the
   * Solutions section below meant pressing Tab several hundred times. The links stay in the
   * document and stay real; they are taken out of the sequential order and the graph is
   * entered once, then walked with the arrow keys.
   *
   * On a narrow screen they come out of the tab order entirely: the click target scales
   * with the viewport and is under three pixels on a phone, so the search box and the text
   * list below are the interface there, and offering a keyboard path into targets nobody
   * can hit is worse than not offering one.
   */
  var roving = 0;

  function setRoving(i, focusIt) {
    if (!nodes.length) return;
    roving = Math.max(0, Math.min(nodes.length - 1, i));
    nodes.forEach(function (n, j) {
      n.setAttribute("tabindex", j === roving && wide() ? "0" : "-1");
    });
    if (focusIt) nodes[roving].focus();
  }

  // Reading order for the arrow keys: by community, then by how connected each skill is,
  // so walking the graph with a keyboard follows the same structure the colours show
  // rather than the document order, which is smallest-degree-first for painting reasons.
  var walkOrder = nodes
    .slice()
    .sort(function (a, b) {
      var ca = +a.getAttribute("data-comm");
      var cb = +b.getAttribute("data-comm");
      if (ca !== cb) return ca - cb;
      return +b.getAttribute("data-deg") - +a.getAttribute("data-deg");
    })
    .map(function (n) {
      return nodes.indexOf(n);
    });
  var walkAt = {};
  walkOrder.forEach(function (idx, at) {
    walkAt[idx] = at;
  });

  function step(delta) {
    var at = walkAt[roving] === undefined ? 0 : walkAt[roving];
    var next = walkOrder[(at + delta + walkOrder.length) % walkOrder.length];
    setRoving(next, true);
  }

  setRoving(0, false);

  // Re-applied on resize, because whether the graph has a tab stop at all depends on the
  // viewport. The traversal's own resize handler reloads when crossing the breakpoint, but
  // it is only registered on desktop: growing a narrow window would otherwise leave all 490
  // nodes at tabindex="-1" and the graph unreachable by keyboard.
  var rovingTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(rovingTimer);
    rovingTimer = setTimeout(function () {
      setRoving(roving, false);
    }, 200);
  });

  nodes.forEach(function (n) {
    var key = n.getAttribute("data-key");
    n.addEventListener("mouseenter", function () {
      if (pinned || pathMode || camMoving) return;
      focus(key);
    });
    n.addEventListener("focus", function () {
      // Focus moves the roving stop with it, so tabbing away and back returns to the node
      // the reader was last on rather than to the first one.
      var at = nodes.indexOf(n);
      if (at > -1 && at !== roving) setRoving(at, false);
      if (pathMode) return;
      focus(key, { pin: true });
    });
    // Every node is a real link to its own card in the library, so the graph is a table
    // of contents when this script does not run. When it does run, activation means
    // "read this here" and the jump is suppressed: following the link would scroll away
    // from the graph being used.
    n.addEventListener("click", function (e) {
      if (wide()) e.preventDefault();
      if (pathMode) {
        pathEnds.push(key);
        if (pathEnds.length === 1) {
          clearClasses();
          n.classList.add("is-path", "is-path-end");
          if (panel.ev) panel.ev.textContent = "from " + nameOf(key) + ", now pick another";
          mark();
        } else {
          var a = pathEnds[0];
          showPath(a, key);
          setPathModeOff();
        }
        return;
      }
      focus(key, { pin: true });
    });
    n.addEventListener("keydown", function (e) {
      // Arrow keys walk the graph; Home and End jump to its ends. This is the composite
      // widget half of the roving tabindex: one stop to enter, then movement inside.
      var moves = {
        ArrowRight: 1,
        ArrowDown: 1,
        ArrowLeft: -1,
        ArrowUp: -1
      };
      if (moves[e.key] !== undefined) {
        e.preventDefault();
        step(moves[e.key]);
        return;
      }
      if (e.key === "Home" || e.key === "End") {
        e.preventDefault();
        setRoving(walkOrder[e.key === "Home" ? 0 : walkOrder.length - 1], true);
        return;
      }
      if (e.key === "Enter" || e.key === " ") {
        if (wide() || e.key === " ") e.preventDefault();
        if (pathMode) {
          n.dispatchEvent(new MouseEvent("click", { bubbles: true }));
          return;
        }
        focus(key, { pin: true });
      }
    });
  });

  function setPathModeOff() {
    pathMode = false;
    if (pathBtn) pathBtn.setAttribute("aria-pressed", "false");
    if (stage) stage.classList.remove("is-picking");
    document.documentElement.classList.remove("is-picking");
  }

  if (pathBtn) {
    pathBtn.addEventListener("click", function () {
      setPathMode(pathBtn.getAttribute("aria-pressed") !== "true");
    });
  }

  /* The community names are labels, not controls.
   *
   * They were clickable for one build, and that cost more than it gave. A name's text box
   * is wide, and SVG has no z-index, so twelve labels covered the centres of six nodes
   * underneath them: those skills were drawn, coloured, sized and completely unclickable.
   * Worse, making them clickable meant setting pointer-events as an inline style, which the
   * page's own Content-Security-Policy drops without a word — the same class of failure
   * that left the hero counter frozen at zero on the live site.
   *
   * The chip row below the graph selects communities, and it is one obvious control rather
   * than two half-discoverable ones.
   */

  beatItems.forEach(function (b) {
    b.addEventListener("click", function (e) {
      e.preventDefault();
      // Works at every width. On a phone the graph takes no pointer input — the targets are
      // three pixels wide — so these chips ARE the way into it, and they used to fall through
      // to a plain jump down the page. The camera stays put there: framing a cluster is no
      // help when nothing in it can be tapped, but naming it and lighting it up is.
      showCommunity(+b.getAttribute("data-comm"), { frame: wide() });
    });
  });

  // Hovering a Solution card lights its lead in the graph, so the two halves of the
  // page are visibly the same information.
  sols.forEach(function (s) {
    s.addEventListener("mouseenter", function () {
      if (pinned || pathMode || camMoving) return;
      focus(s.getAttribute("data-sol"));
    });
  });
  cards.forEach(function (c) {
    c.addEventListener("mouseenter", function () {
      if (pinned || pathMode || camMoving) return;
      focus(c.getAttribute("data-id"));
    });
  });

  /* ----------------------------------------------------------------- search */

  function runSearch(q) {
    q = (q || "").trim().toLowerCase();
    if (!q) {
      stage.classList.remove("is-dim");
      nodes.forEach(function (n) {
        n.classList.remove("is-hit");
      });
      // Back to where the build placed them. Clearing the class without restoring the
      // position left the default 26 names wherever the last search had moved them to,
      // and two of them overlapped in the page's own opening state.
      homeLabels();
      cards.forEach(function (c) {
        c.classList.remove("is-hit");
      });
      return;
    }
    stage.classList.remove("is-focus", "is-path");
    stage.classList.add("is-dim");
    // A search is a question about the whole library, so it pulls the camera back out.
    // Leaving it framed on one community showed a match count that included nodes off
    // the edge of the view.
    resetCam();

    // Matches on the name a reader can see, not on the identity key, which carries the
    // category and bundle and would make "engineering" match all 105 skills in it.
    var hits = [];
    nodes.forEach(function (n) {
      var hit = (n.getAttribute("data-name") || "").toLowerCase().indexOf(q) > -1;
      n.classList.toggle("is-hit", hit);
      if (hit) hits.push(n.getAttribute("data-key"));
    });
    // Strongest first, so when a query matches more names than can be drawn without
    // collisions the ones that survive are the ones worth reading.
    hits.sort(function (a, b) {
      return (
        +nodeByKey[b].getAttribute("data-deg") - +nodeByKey[a].getAttribute("data-deg")
      );
    });
    light(hits.slice(0, 24), "is-hit");
    cards.forEach(function (c) {
      c.classList.toggle(
        "is-hit",
        (c.getAttribute("data-name") || "").toLowerCase().indexOf(q) > -1
      );
    });
    mark();
  }

  // A hit inside a closed category is a hit nobody can see, so searching opens
  // the categories it found something in, and closes them again when cleared.
  function revealHits(anyQuery) {
    Array.prototype.slice
      .call(document.querySelectorAll(".lib__cat"))
      .forEach(function (d) {
        if (!anyQuery) {
          d.removeAttribute("open");
        } else if (d.querySelector(".card.is-hit")) {
          d.setAttribute("open", "");
        } else {
          d.removeAttribute("open");
        }
      });
  }

  if (search) {
    search.addEventListener("input", function () {
      runSearch(search.value);
      revealHits(!!search.value.trim());
    });
  }

  /* Back to the opening state, from any of them: a search, a pinned node, a traced
   * path, an evidence filter, a community. One key, one button, and it has to release
   * every mode — a reset that leaves a chip pressed or a path lit is the fault this
   * page has already had once. */
  function resetAll() {
    if (search) search.value = "";
    runSearch("");
    revealHits(false);
    setPathModeOff();
    if (statedBtn) statedBtn.setAttribute("aria-pressed", "false");
    stage.classList.remove("is-extracted-only", "is-picking");
    document.documentElement.classList.remove("is-picking");
    openComm = null;
    clearFocus();
    resetCam();
    if (featured.length) showCommunity(featured[0], { frame: false });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") resetAll();
  });

  // Following a rail link into a closed category should open it, otherwise the
  // link lands on a heading and appears to do nothing.
  function openTarget(hash) {
    if (!hash || hash.charAt(0) !== "#") return;
    var el = document.getElementById(hash.slice(1));
    if (el && el.tagName === "DETAILS") el.setAttribute("open", "");
  }
  if (rail) {
    rail.addEventListener("click", function (e) {
      var a = e.target.closest("a");
      if (a) openTarget(a.getAttribute("href"));
    });
  }
  window.addEventListener("hashchange", function () {
    openTarget(window.location.hash);
  });
  openTarget(window.location.hash);
  /* --------------------------------------------------------- what is asserted
   * The graph draws two kinds of relationship and says which is which. This lets a
   * reader throw away the weaker kind and see what is left: 357 relationships the
   * repository states outright, out of 1,868 drawn.
   */

  var statedBtn = document.getElementById("gstated");
  if (statedBtn) {
    statedBtn.addEventListener("click", function () {
      var on = statedBtn.getAttribute("aria-pressed") !== "true";
      statedBtn.setAttribute("aria-pressed", on ? "true" : "false");
      stage.classList.toggle("is-extracted-only", on);
      if (on && panel.tier) {
        panel.tier.textContent = "stated only";
        if (panel.name) panel.name.textContent = "Evidence filter";
        if (panel.desc) {
          panel.desc.textContent =
            "Showing only relationships the repository states: a Solution leading a " +
            "skill, or two skills packaged in the same bundle. The rest were inferred " +
            "from names sharing a subject.";
        }
        setChain([]);
        if (panel.ev) {
          panel.ev.textContent = STATED_COUNT + " stated of " + GEDGES.length + " drawn";
        }
      } else if (openComm !== null) {
        explainCommunity(openComm);
      }
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      resetAll();
    });
  }


  /* --------------------------------------------------- note on the camera's history
   * There used to be a comment here saying this page had no camera, on purpose. It stayed
   * for a build after the camera was implemented above, which is the kind of comment that
   * is worse than none: a reviewer found it and was right to.
   *
   * The history it recorded is still true and still the reason the camera is built the way
   * it is. A first attempt eased the SVG viewBox and caused three faults: labels are
   * measured in user units so they grew with the zoom until they collided; a node sliding
   * under a stationary cursor fired mouseenter and replaced the selection the reader had
   * just clicked; and anything outside the frame became unclickable with no way back.
   *
   * All three are handled where the camera is defined — labels divide their size and their
   * halo by the zoom factor in CSS, hover is ignored while `camMoving` is set, and Escape,
   * the Reset button and a click on the background all pull back out. The page also opens
   * unzoomed, so every one of the 490 nodes is clickable before the reader does anything.
   */

  /* ------------------------------------------------ the page opens on a Solution
   * The panel and the graph should be showing something the moment the page is
   * readable, rather than waiting for a hover that never arrives on a touch
   * screen.
   */
  // DATA.featured holds the largest communities, in size order. The first is opened
  // immediately: the panel and the graph should be showing something the moment the page
  // is readable, rather than waiting for a hover that never arrives on a touch screen.
  var featured = (DATA.featured || []).filter(function (id) {
    return commByIdMeta[id] !== undefined;
  });
  if (featured.length) showCommunity(featured[0], { frame: false });

  /* -------------------------------------------------------------- traversal */

  var enhanced =
    !reduced &&
    wide() &&
    typeof window.gsap !== "undefined" &&
    typeof window.ScrollTrigger !== "undefined";

  if (!enhanced) {
    if (bar) bar.classList.add("is-full");
    document.documentElement.classList.add("is-static");
    return;
  }

  gsap.registerPlugin(ScrollTrigger);
  document.documentElement.classList.add("is-enhanced");

  var lenis = null;
  if (typeof window.Lenis !== "undefined") {
    lenis = new Lenis({ duration: 0.9, smoothWheel: true });
    gsap.ticker.add(function (time) {
      lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);
    lenis.on("scroll", ScrollTrigger.update);
  }

  if (rail) {
    rail.addEventListener("click", function (e) {
      var a = e.target.closest("a");
      if (!a) return;
      var target = document.querySelector(a.getAttribute("href"));
      if (!target) return;
      e.preventDefault();
      if (lenis) lenis.scrollTo(target, { offset: -70 });
      else target.scrollIntoView({ behavior: "smooth" });
    });
  }

  // Page-wide progress. It means "how far down the page you are" and nothing
  // else; the previous bar meant two different things in two different sections.
  ScrollTrigger.create({
    start: 0,
    end: "max",
    onUpdate: function (self) {
      if (bar) gsap.set(bar, { scaleX: Math.max(0.02, self.progress) });
    }
  });

  /* The opening: pin the stage and open each domain in turn.
   *
   * Seven beats, one per domain, where there used to be eight per Solution — and
   * before that 24 chapters over 76,000 pixels, where scrolling was the whole
   * interface and reaching a named skill meant travelling past hundreds of others.
   *
   * Scrolling now demonstrates the top layer and nothing more. Depth is reached by
   * clicking, which is faster than scrolling for a tree and does not make the
   * visitor pay in page height for structure they may not want.
   */
  if (featured.length) {
    var PER_BEAT = 260;
    gsap.timeline({
      scrollTrigger: {
        trigger: stage,
        start: "top top",
        end: "+=" + featured.length * PER_BEAT,
        scrub: 0.5,
        pin: true,
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate: function (self) {
          // A dead zone at the very start, so the page's opening image is the whole
          // library rather than one cluster already singled out.
          //
          // It must not clear a selection the reader made. This trigger updates on
          // every tick, so while sitting at the top of the page it was calling
          // clearFocus() immediately after any click, which released the pin and let
          // the next hover take over: clicking a Solution appeared to work and then
          // silently stopped holding.
          if (self.progress < 0.06) {
            if (openComm !== featured[0]) {
              showCommunity(featured[0], { frame: false });
            }
            return;
          }
          var i = Math.min(
            featured.length - 1,
            Math.floor(((self.progress - 0.06) / 0.94) * featured.length)
          );
          if (featured[i] !== openComm) {
            showCommunity(featured[i]);
          }
        },
        onLeaveBack: function () {
          if (featured.length) showCommunity(featured[0], { frame: false });
        }
      }
    }).to(cue, { opacity: 0, duration: 0.3 }, 0);
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      ScrollTrigger.refresh();
    });
  }

  var wasDesktop = wide();
  var t;
  window.addEventListener("resize", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var isDesktop = wide();
      if (isDesktop !== wasDesktop) window.location.reload();
      else ScrollTrigger.refresh();
    }, 250);
  });
})();
