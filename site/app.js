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
  var resetBtn = document.getElementById("greset");
  var beats = document.getElementById("beats");
  var bar = document.getElementById("bar");
  var rail = document.getElementById("rail");
  var cue = document.getElementById("cue");

  if (!stage || !svg) return;

  /* ---------------------------------------------------------------- the tree
   * Four layers: domain, group, Solution, skill. Everything is prerendered; the two
   * deeper layers are held closed because 490 leaves at once is a speckle, and 50
   * Solutions in one column sit 9 units apart. Opening a branch is what gives it
   * room, and only one branch of each layer is ever open.
   */

  var nodes = Array.prototype.slice.call(svg.querySelectorAll(".g-node"));
  var edges = Array.prototype.slice.call(svg.querySelectorAll(".g-edge"));
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var sols = Array.prototype.slice.call(document.querySelectorAll(".sol"));

  var nodeById = {};
  nodes.forEach(function (n) {
    nodeById[n.getAttribute("data-id")] = n;
  });

  // Labels live in their own layer so they paint above every node — SVG has no
  // z-index — so they are keyed by node id and toggled alongside it.
  var labelBy = {};
  Array.prototype.slice.call(svg.querySelectorAll(".g-label")).forEach(function (el) {
    labelBy[el.getAttribute("data-id")] = el;
  });
  function label(id) {
    return labelBy[id];
  }
  function setLabel(id, cls, on) {
    var el = labelBy[id];
    if (el) el.classList.toggle(cls, on);
  }

  function layerOf(id) {
    var n = nodeById[id];
    return n ? n.getAttribute("data-layer") : "";
  }
  function parentOf(id) {
    var n = nodeById[id];
    return n ? n.getAttribute("data-parent") : null;
  }
  // Every ancestor of a node, itself included. The whole path lights up, so a
  // selected skill shows which Solution, group and domain it belongs to.
  function pathOf(id) {
    var out = [];
    var cur = id;
    while (cur) {
      out.push(cur);
      cur = parentOf(cur);
    }
    return out;
  }

  var beatItems = beats
    ? Array.prototype.slice.call(beats.querySelectorAll(".beat"))
    : [];

  // The panel reads its text from the rendered page rather than from a second copy
  // in JavaScript, so it cannot disagree with the card it describes.
  var solByKey = {};
  sols.forEach(function (el) {
    var key = el.getAttribute("data-sol");
    if (!key) return;
    solByKey[key] = {
      el: el,
      tier: el.getAttribute("data-tier") || "",
      label: (el.querySelector("h3") || {}).textContent || key,
      problem: (el.querySelector(".sol__problem") || {}).textContent || "",
      evidence: (el.querySelector(".sol__ev") || {}).textContent || "",
      members: Array.prototype.slice
        .call(el.querySelectorAll(".sol__step"))
        .map(function (s) {
          return s.textContent;
        })
    };
  });
  var cardByKey = {};
  cards.forEach(function (c) {
    cardByKey[c.getAttribute("data-id")] = c;
  });

  /* ------------------------------------------------------------------ opening */

  var openDomain = null;
  var openBranch = null;

  function showDomain(domId) {
    openDomain = domId;
    // Opening a domain closes whatever branch was open inside the previous one:
    // leaving it open left a column of skills belonging to a Solution no longer on
    // screen, which read as a second, unexplained group of dots.
    showBranch(null);
    nodes.forEach(function (n) {
      var layer = n.getAttribute("data-layer");
      if (layer === "domain" || layer === "skill") return;
      // Groups and Solutions belong to exactly one domain and are only ever drawn
      // while that domain is the one being read, which is what lets whichever branch
      // is open use the full height of the drawing.
      var mine = n.getAttribute("data-dom") === domId;
      n.classList.toggle("is-open", mine);
      setLabel(n.getAttribute("data-id"), "is-open", mine);
    });
    edges.forEach(function (e) {
      if (e.classList.contains("g-edge--leaf") || e.classList.contains("g-edge--cross")) {
        return;
      }
      e.classList.toggle("is-open", e.getAttribute("data-dom") === domId);
    });
    beatItems.forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-dom") === domId);
    });
  }

  function showBranch(parentId) {
    openBranch = parentId;
    // A skill can be led by two Solutions — code-review is led by both
    // idea-to-shipped-code and hard-to-find-bug — and a tree can only hold one of
    // those, so the second is a cross-link. Opening the second Solution has to reveal
    // that skill too, or its card lists three steps while the graph shows two.
    var alsoOpen = {};
    if (parentId) {
      edges.forEach(function (e) {
        if (e.classList.contains("g-edge--cross") && e.getAttribute("data-sol") === parentId) {
          alsoOpen[e.getAttribute("data-to")] = true;
        }
      });
    }
    nodes.forEach(function (n) {
      if (n.getAttribute("data-layer") !== "skill") return;
      var id = n.getAttribute("data-id");
      var on = (!!parentId && n.getAttribute("data-parent") === parentId) || !!alsoOpen[id];
      n.classList.toggle("is-open", on);
      setLabel(id, "is-open", on);
    });
    edges.forEach(function (e) {
      if (e.classList.contains("g-edge--leaf")) {
        e.classList.toggle("is-open", !!parentId && e.getAttribute("data-branch") === parentId);
      } else if (e.classList.contains("g-edge--cross")) {
        e.classList.toggle("is-open", !!parentId && e.getAttribute("data-sol") === parentId);
      }
    });
  }

  /* ------------------------------------------------------------------- panel */

  function setChain(items) {
    if (!panel.chain) return;
    // Rebuilt element by element rather than assigned as innerHTML: these strings
    // come from skill frontmatter, and textContent cannot be talked into markup.
    while (panel.chain.firstChild) panel.chain.removeChild(panel.chain.firstChild);
    items.forEach(function (text) {
      var li = document.createElement("li");
      li.textContent = text;
      panel.chain.appendChild(li);
    });
  }

  function fillPanel(id) {
    var node = nodeById[id];
    if (!node) return;
    var layer = node.getAttribute("data-layer");
    var name = node.getAttribute("data-name") || id;

    if (panel.tier) panel.tier.textContent = layer === "practice" ? "group" : layer;
    if (panel.name) panel.name.textContent = name;

    if (layer === "solution") {
      var s = solByKey[node.getAttribute("data-key")];
      if (panel.desc) panel.desc.textContent = s ? s.problem : "";
      setChain(s ? s.members : []);
      if (panel.ev) panel.ev.textContent = s ? s.evidence : "";
      return;
    }

    if (layer === "skill") {
      var card = cardByKey[node.getAttribute("data-key")];
      var desc = card ? card.querySelector("p") : null;
      if (panel.desc) panel.desc.textContent = desc ? desc.textContent : "";
      var owner = parentOf(id);
      setChain(
        owner && layerOf(owner) === "solution"
          ? ["led by " + (nodeById[owner].getAttribute("data-name") || "")]
          : ["no Solution leads this skill yet"]
      );
      if (panel.ev) {
        panel.ev.textContent = card ? card.getAttribute("data-name") || "" : "";
        var meta = card ? card.querySelector(".card__meta") : null;
        if (meta) panel.ev.textContent = meta.textContent;
      }
      return;
    }

    // A domain or a group: describe what it contains, since that is the only claim
    // either of them makes.
    var kids = nodes.filter(function (n) {
      return n.getAttribute("data-parent") === id;
    });
    if (panel.desc) panel.desc.textContent = node.getAttribute("data-blurb") || "";
    setChain(
      kids.slice(0, 24).map(function (k) {
        return k.getAttribute("data-name") || "";
      })
    );
    var skillCount = +node.getAttribute("data-skills") || 0;
    var solCount = +node.getAttribute("data-sols") || 0;
    if (panel.ev) {
      panel.ev.textContent =
        kids.length +
        (layer === "domain" ? " groups, " : " Solutions, ") +
        (layer === "domain" ? solCount + " Solutions, " : "") +
        skillCount +
        " skills";
    }
  }

  /* ------------------------------------------------------------------ focus */

  var focused = null;
  // An explicit choice is sticky: hover previews, clicking commits. Without this,
  // moving the pointer off a clicked node onto any neighbour silently replaced the
  // selection, so the panel described something the reader had not chosen.
  var pinned = null;

  // Reflected onto the stage so the selection model is inspectable rather than
  // trapped in a closure: "pinned or merely hovered" is exactly the distinction
  // that broke twice, and a test cannot assert it otherwise.
  function mark() {
    stage.setAttribute("data-pinned", pinned || "");
    stage.setAttribute("data-focused", focused || "");
    stage.setAttribute("data-domain", openDomain || "");
    stage.setAttribute("data-branch", openBranch || "");
  }

  function focus(id, opts) {
    opts = opts || {};
    if (!nodeById[id]) return;
    if (opts.pin) pinned = id;
    focused = id;

    var path = pathOf(id);
    var domId = path[path.length - 1];
    var layer = layerOf(id);

    if (domId !== openDomain) showDomain(domId);
    // Selecting a Solution or a group opens it; selecting a skill keeps its own
    // parent open so the skill you picked stays on screen.
    if (layer === "solution" || layer === "practice") {
      showBranch(id);
    } else if (layer === "skill") {
      showBranch(parentOf(id));
    } else {
      showBranch(null);
    }

    stage.classList.add("is-focus");
    stage.classList.remove("is-dim");
    mark();

    nodes.forEach(function (n) {
      var nid = n.getAttribute("data-id");
      var on = path.indexOf(nid) > -1 || parentOf(nid) === id;
      n.classList.toggle("is-on", on);
      setLabel(nid, "is-on", on);
    });
    edges.forEach(function (e) {
      var from = e.getAttribute("data-from");
      var to = e.getAttribute("data-to");
      // On the path from the root to the selection, or hanging directly off it.
      var on =
        (path.indexOf(from) > -1 && path.indexOf(to) > -1) || from === id;
      e.classList.toggle("is-on", on);
    });
    sols.forEach(function (s) {
      s.classList.toggle("is-on", "s:" + s.getAttribute("data-sol") === id);
    });
    cards.forEach(function (c) {
      c.classList.toggle("is-on", "k:" + c.getAttribute("data-id") === id);
    });

    fillPanel(id);
  }

  function clearFocus() {
    focused = null;
    pinned = null;
    stage.classList.remove("is-focus", "is-dim");
    nodes.concat(edges).forEach(function (el) {
      el.classList.remove("is-on", "is-hit");
    });
    Object.keys(labelBy).forEach(function (id) {
      labelBy[id].classList.remove("is-on", "is-hit");
    });
    sols.forEach(function (s) {
      s.classList.remove("is-on");
    });
    cards.forEach(function (c) {
      c.classList.remove("is-hit", "is-on");
    });
    if (openDomain) fillPanel(openDomain);
    mark();
  }

  nodes.forEach(function (n) {
    var id = n.getAttribute("data-id");
    n.addEventListener("mouseenter", function () {
      if (pinned) return;
      focus(id);
    });
    n.addEventListener("focus", function () {
      focus(id, { pin: true });
    });
    // Every node is a real link to the part of the page that describes it, so the
    // tree is a table of contents when this script does not run. When it does run,
    // the same activation means "show me this here" instead, and the jump is
    // suppressed: following the link would scroll away from the tree being used.
    n.addEventListener("click", function (e) {
      if (wide()) e.preventDefault();
      focus(id, { pin: true });
    });
    n.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        // Space does not activate a link by default, and here it should: the visitor
        // is operating a graph, not reading prose.
        if (wide() || e.key === " ") e.preventDefault();
        focus(id, { pin: true });
      }
    });
  });

  // Hovering a Solution card lights its branch in the tree, so the two halves of the
  // page are visibly the same information.
  sols.forEach(function (s) {
    s.addEventListener("mouseenter", function () {
      if (pinned) return;
      focus("s:" + s.getAttribute("data-sol"));
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (search) search.value = "";
      clearFocus();
    }
  });

  /* ----------------------------------------------------------------- search */

  function runSearch(q) {
    q = (q || "").trim().toLowerCase();
    if (!q) {
      stage.classList.remove("is-dim");
      nodes.forEach(function (n) {
        n.classList.remove("is-hit");
      });
      Object.keys(labelBy).forEach(function (id) {
        labelBy[id].classList.remove("is-hit");
      });
      cards.forEach(function (c) {
        c.classList.remove("is-hit");
      });
      return;
    }
    stage.classList.remove("is-focus");
    stage.classList.add("is-dim");

    // Search reads data-name, the label, not data-id, which is an identity key of
    // the form category~bundle~name. Searching the key would make "engineering"
    // match all 105 skills in that category through their ids as well as their
    // names, which is not what someone typing a skill name means.
    //
    // A hit deeper than the open branch is a hit nobody can see, so any domain
    // holding one is opened, and so is any Solution holding one.
    var hitDomains = {};
    var hitBranches = {};
    nodes.forEach(function (n) {
      var name = (n.getAttribute("data-name") || "").toLowerCase();
      var hit = name.indexOf(q) > -1;
      n.classList.toggle("is-hit", hit);
      setLabel(n.getAttribute("data-id"), "is-hit", hit);
      if (hit) {
        hitDomains[n.getAttribute("data-dom")] = true;
        var parent = n.getAttribute("data-parent");
        if (parent && n.getAttribute("data-layer") === "skill") hitBranches[parent] = true;
      }
    });
    cards.forEach(function (c) {
      var name = (c.getAttribute("data-name") || "").toLowerCase();
      c.classList.toggle("is-hit", name.indexOf(q) > -1);
    });

    var domainKeys = Object.keys(hitDomains);
    if (domainKeys.length) {
      // One domain can be open at a time, so the first match wins and the rest stay
      // visible as dimmed hits at their own layer.
      if (domainKeys.indexOf(openDomain) < 0) showDomain(domainKeys[0]);
      var branchKeys = Object.keys(hitBranches).filter(function (b) {
        var n = nodeById[b];
        return n && n.getAttribute("data-dom") === openDomain;
      });
      showBranch(branchKeys.length ? branchKeys[0] : null);
      // Re-mark, because opening a branch does not know about the query.
      nodes.forEach(function (n) {
        var name = (n.getAttribute("data-name") || "").toLowerCase();
        var hit = name.indexOf(q) > -1;
        n.classList.toggle("is-hit", hit);
        setLabel(n.getAttribute("data-id"), "is-hit", hit);
      });
    }
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

  /* ------------------------------------------------------ provenance filters */

  if (chips) {
    chips.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      if (btn === resetBtn) {
        if (search) search.value = "";
        chips.querySelectorAll(".chip[data-tier]").forEach(function (c) {
          c.setAttribute("aria-pressed", "false");
        });
        clearFocus();
        return;
      }
      var tier = btn.getAttribute("data-tier");
      if (!tier) return;
      var on = btn.getAttribute("aria-pressed") !== "true";
      btn.setAttribute("aria-pressed", on ? "true" : "false");

      var active = Array.prototype.slice
        .call(chips.querySelectorAll('.chip[aria-pressed="true"]'))
        .map(function (c) {
          return c.getAttribute("data-tier");
        });

      if (!active.length) {
        clearFocus();
        return;
      }
      stage.classList.remove("is-focus");
      stage.classList.add("is-dim");
      // The filter is about Solutions, so it lights Solution nodes and the skills
      // hanging off them. A Solution node carries its own tier, so this no longer
      // has to look the tier up through a member's owner list.
      var lit = {};
      nodes.forEach(function (n) {
        if (n.getAttribute("data-layer") !== "solution") return;
        var hit = active.indexOf(n.getAttribute("data-tier")) > -1;
        n.classList.toggle("is-hit", hit);
        setLabel(n.getAttribute("data-id"), "is-hit", hit);
        if (hit) lit[n.getAttribute("data-id")] = true;
      });
      nodes.forEach(function (n) {
        if (n.getAttribute("data-layer") !== "skill") return;
        n.classList.toggle("is-hit", !!lit[n.getAttribute("data-parent")]);
      });
      sols.forEach(function (s) {
        s.classList.toggle(
          "is-on",
          active.indexOf(s.getAttribute("data-tier")) > -1
        );
      });
    });
  }

  /* ------------------------------------------------------------------ camera
   * There isn't one, and that is deliberate.
   *
   * The first version eased the SVG viewBox to frame the focused Solution. It
   * looked good for one beat and then caused three separate faults: SVG text is
   * measured in user units so every label scaled with the zoom and the labels
   * collided; a node sliding under a stationary cursor fired mouseenter and hover
   * replaced the selection the reader had just clicked; and worst, once zoomed in,
   * every Solution outside the frame became unclickable, so the graph's own
   * navigation broke unless the reader knew to press Escape.
   *
   * Highlighting instead of moving keeps all 54 Solutions reachable at all times,
   * keeps labels at the size they were designed at, and makes the focused cluster
   * clearer than a zoom did, because the contrast is against the rest of the
   * library rather than against empty space.
   */

  /* ------------------------------------------------ the page opens on a Solution
   * The panel and the graph should be showing something the moment the page is
   * readable, rather than waiting for a hover that never arrives on a touch
   * screen.
   */
  // DATA.featured holds the domain ids, in the order the tree presents them. The
  // first one is opened immediately: the panel and the graph should be showing
  // something the moment the page is readable, rather than waiting for a hover that
  // never arrives on a touch screen.
  var featured = (DATA.featured || []).filter(function (id) {
    return !!nodeById[id];
  });
  if (featured.length) {
    showDomain(featured[0]);
    fillPanel(featured[0]);
    mark();
  }

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
            if (focused && !pinned) clearFocus();
            return;
          }
          var i = Math.min(
            featured.length - 1,
            Math.floor(((self.progress - 0.06) / 0.94) * featured.length)
          );
          if (featured[i] !== openDomain) {
            pinned = null;
            focus(featured[i]);
          }
        },
        onLeaveBack: function () {
          clearFocus();
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
