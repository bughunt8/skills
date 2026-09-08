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

  var leads = Array.prototype.slice.call(svg.querySelectorAll(".g-lead"));
  // Labels are a separate layer so they paint above every node, so they are
  // keyed by lead and toggled alongside it.
  var labelBy = {};
  Array.prototype.slice.call(svg.querySelectorAll(".g-label")).forEach(function (el) {
    labelBy[el.getAttribute("data-id")] = el;
  });
  function setLabel(id, cls, on) {
    var el = labelBy[id];
    if (el) el.classList.toggle(cls, on);
  }
  var nodes = Array.prototype.slice.call(svg.querySelectorAll(".g-node"));
  var edges = Array.prototype.slice.call(svg.querySelectorAll(".g-edge"));
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var sols = Array.prototype.slice.call(document.querySelectorAll(".sol"));
  // data-sol holds every Solution that leads this skill, space separated, so
  // membership is a token test rather than an equality test.
  function owns(el, id) {
    var v = el.getAttribute("data-sol") || "";
    return (" " + v + " ").indexOf(" " + id + " ") > -1;
  }

  var beatItems = beats
    ? Array.prototype.slice.call(beats.querySelectorAll(".beat"))
    : [];

  // Index the Solutions section by lead, so the panel reads its text from the
  // rendered page instead of from a duplicate copy in JavaScript. One source of
  // truth means the panel cannot disagree with the card it describes.
  var solByLead = {};
  sols.forEach(function (el) {
    var id = el.getAttribute("data-sol");
    if (!id) return;
    solByLead[id] = {
      el: el,
      tier: el.getAttribute("data-tier") || "",
      label: (el.querySelector("h3") || {}).textContent || id,
      problem: (el.querySelector(".sol__problem") || {}).textContent || "",
      evidence: (el.querySelector(".sol__ev") || {}).textContent || "",
      members: Array.prototype.slice
        .call(el.querySelectorAll(".sol__step"))
        .map(function (s) {
          return s.textContent;
        })
    };
  });

  /* ------------------------------------------------------------------ panel */

  function fillPanel(id) {
    var s = solByLead[id];
    if (!s) return;
    if (panel.tier) panel.tier.textContent = s.tier;
    if (panel.name) panel.name.textContent = s.label;
    if (panel.desc) panel.desc.textContent = s.problem;
    if (panel.ev) panel.ev.textContent = s.evidence;
    if (panel.chain) {
      // Rebuilt rather than innerHTML-assigned: these strings come from skill
      // frontmatter, and textContent cannot be talked into becoming markup.
      while (panel.chain.firstChild) panel.chain.removeChild(panel.chain.firstChild);
      s.members.forEach(function (m) {
        var li = document.createElement("li");
        li.textContent = m;
        panel.chain.appendChild(li);
      });
    }
  }

  /* ------------------------------------------------------------------ focus */

  var focused = null;
  // An explicit choice is sticky: hover previews, clicking commits. Without this,
  // moving the pointer off a clicked node onto any neighbour silently replaced the
  // selection, so the panel described a Solution the reader had not chosen.
  var pinned = null;

  // Reflected onto the stage so the selection model is inspectable rather than
  // trapped in a closure: "is this Solution pinned or merely hovered" is exactly
  // the distinction that broke twice, and a test cannot assert it otherwise.
  function mark() {
    stage.setAttribute("data-pinned", pinned || "");
    stage.setAttribute("data-focused", focused || "");
  }

  function focus(id, opts) {
    opts = opts || {};
    if (opts.pin) pinned = id;
    focused = id;
    mark();
    stage.classList.add("is-focus");
    stage.classList.remove("is-dim");

    leads.forEach(function (l) {
      var lid = l.getAttribute("data-id");
      l.classList.toggle("is-on", lid === id);
      setLabel(lid, "is-on", lid === id);
    });
    nodes.forEach(function (n) {
      if (n.classList.contains("g-node--member")) {
        n.classList.toggle("is-on", owns(n, id));
      }
    });
    edges.forEach(function (e) {
      e.classList.toggle("is-on", owns(e, id));
    });
    beatItems.forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-sol") === id);
    });
    sols.forEach(function (s) {
      s.classList.toggle("is-on", s.getAttribute("data-sol") === id);
    });

    fillPanel(id);
  }

  function clearFocus() {
    focused = null;
    pinned = null;
    mark();
    stage.classList.remove("is-focus", "is-dim");
    leads.concat(nodes, edges).forEach(function (el) {
      el.classList.remove("is-on", "is-hit");
    });
    Object.keys(labelBy).forEach(function (id) {
      labelBy[id].classList.remove("is-on", "is-hit");
    });
    beatItems.forEach(function (b) {
      b.classList.remove("is-on");
    });
    sols.forEach(function (s) {
      s.classList.remove("is-on");
    });
    cards.forEach(function (c) {
      c.classList.remove("is-hit");
    });
  }

  leads.forEach(function (l) {
    var id = l.getAttribute("data-id");
    // Hover focuses rather than only previewing. When hover merely filled the
    // panel, the panel could describe one Solution while the graph highlighted
    // another, which is worse than either behaviour on its own.
    l.addEventListener("mouseenter", function () {
      if (pinned) return;
      focus(id);
    });
    l.addEventListener("focus", function () {
      focus(id, { pin: true });
    });
    l.addEventListener("click", function () {
      focus(id, { pin: true });
    });
    l.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        focus(id, { pin: true });
      }
    });
  });

  // Hovering a Solution card lights its cluster in the graph, so the two halves
  // of the page are visibly the same information.
  sols.forEach(function (s) {
    var id = s.getAttribute("data-sol");
    s.addEventListener("mouseenter", function () {
      if (pinned) return;
      focus(id);
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
      leads.forEach(function (l) {
        l.classList.remove("is-hit");
        setLabel(l.getAttribute("data-id"), "is-hit", false);
      });
      cards.forEach(function (c) {
        c.classList.remove("is-hit");
      });
      return;
    }
    stage.classList.remove("is-focus");
    stage.classList.add("is-dim");

    var hits = 0;
    nodes.forEach(function (n) {
      var id = (n.getAttribute("data-id") || "").toLowerCase();
      var dom = (n.getAttribute("data-dom") || "").toLowerCase();
      var hit = id.indexOf(q) > -1 || dom.indexOf(q) > -1;
      n.classList.toggle("is-hit", hit);
      if (hit) hits++;
    });
    leads.forEach(function (l) {
      var raw = l.getAttribute("data-id") || "";
      var hit = raw.toLowerCase().indexOf(q) > -1;
      l.classList.toggle("is-hit", hit);
      setLabel(raw, "is-hit", hit);
    });
    cards.forEach(function (c) {
      var id = (c.getAttribute("data-id") || "").toLowerCase();
      c.classList.toggle("is-hit", id.indexOf(q) > -1);
    });
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
      leads.forEach(function (l) {
        var hit = active.indexOf(l.getAttribute("data-tier")) > -1;
        l.classList.toggle("is-hit", hit);
        setLabel(l.getAttribute("data-id"), "is-hit", hit);
      });
      nodes.forEach(function (n) {
        if (!n.classList.contains("g-node--member")) return;
        var hit = (n.getAttribute("data-sol") || "").split(" ").some(function (o) {
          var s = solByLead[o];
          return !!s && active.indexOf(s.tier) > -1;
        });
        n.classList.toggle("is-hit", hit);
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
  var featured = (DATA.featured || []).filter(function (id) {
    return !!solByLead[id];
  });
  if (featured.length) fillPanel(featured[0]);

  /* -------------------------------------------------------------- traversal */

  var enhanced =
    !reduced &&
    window.innerWidth > MOBILE &&
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

  /* The opening: pin the stage and step the highlight through the featured
   * Solutions. The budget is deliberately small. The previous page pinned 24
   * chapters and ran to 76,000 pixels; scrolling was the whole interface, and
   * getting to a named skill meant travelling past hundreds of others. Eight
   * beats teach the interaction, and everything else is reachable by search or
   * by clicking a node.
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
          if (featured[i] !== focused) {
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

  var wasDesktop = window.innerWidth > MOBILE;
  var t;
  window.addEventListener("resize", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var isDesktop = window.innerWidth > MOBILE;
      if (isDesktop !== wasDesktop) window.location.reload();
      else ScrollTrigger.refresh();
    }, 250);
  });
})();
