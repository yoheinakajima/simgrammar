/* simgrammar.js: progressive enhancement for the SimGrammar site.
   Every page is complete without this file. It adds: contents highlighting, sortable and
   filterable tables and index groups, view switches, part highlighting on the games index,
   click-to-play shorts and episodes, an episode's scene list, hover cards on the home mosaic and contributors' names,
   and the hover, toggle, and readout layer of the paper's figures.
   Figures are fully laid out by scripts/viz.py; this file only toggles, highlights, and reads out.
   Labels come from the dataset and are inserted with textContent, never innerHTML. */
(function () {
  "use strict";
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function svgPoint(svg, evt) {
    var p = svg.createSVGPoint();
    p.x = evt.clientX; p.y = evt.clientY;
    var m = svg.getScreenCTM();
    return m ? p.matrixTransform(m.inverse()) : { x: 0, y: 0 };
  }
  function link(type, id, text) {
    var a = el("a", { href: type + "/" + id + "/", "data-internal": "" }, text);
    return a;
  }
  // readout: a list of parts; strings become text nodes, nodes are appended as is
  function readout(fig, parts) {
    var r = $("[data-readout]", fig);
    if (!r) return;
    r.textContent = "";
    var line = el("span");  // one flex item, so the line wraps like a sentence on narrow screens
    parts.forEach(function (p, i) {
      if (i) line.appendChild(document.createTextNode(" · "));
      if (typeof p === "string") line.appendChild(document.createTextNode(p));
      else line.appendChild(p);
    });
    r.appendChild(line);
  }
  function bold(s) { return el("b", null, s); }
  function pressed(group, value) {
    $$("button", group).forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-value") === value ? "true" : "false"); });
  }

  /* ---------------------------------------------------------------- contents */
  function toc() {
    var links = $$(".toc a[href^='#']");
    if (!links.length || !("IntersectionObserver" in window)) return;
    var map = {};
    links.forEach(function (a) { var t = document.getElementById(a.getAttribute("href").slice(1)); if (t) map[t.id] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting && map[e.target.id]) {
          links.forEach(function (a) { a.removeAttribute("aria-current"); });
          map[e.target.id].setAttribute("aria-current", "true");
        }
      });
    }, { rootMargin: "0px 0px -70% 0px" });
    Object.keys(map).forEach(function (id) { obs.observe(document.getElementById(id)); });
  }

  /* ---------------------------------------------------------------- tables */
  function tables() {
    $$("table[data-sortable]").forEach(function (table) {
      var ths = $$("thead th", table);
      ths.forEach(function (th, col) {
        th.setAttribute("tabindex", "0");
        th.style.cursor = "pointer";
        th.setAttribute("aria-sort", "none");
        var sort = function () {
          var asc = th.getAttribute("aria-sort") !== "ascending";
          ths.forEach(function (o) { o.setAttribute("aria-sort", "none"); });
          th.setAttribute("aria-sort", asc ? "ascending" : "descending");
          var body = table.tBodies[0];
          var rows = Array.prototype.slice.call(body.rows);
          var num = th.classList.contains("num");
          rows.sort(function (a, b) {
            var x = a.cells[col] ? a.cells[col].textContent.trim() : "";
            var y = b.cells[col] ? b.cells[col].textContent.trim() : "";
            if (num) { x = parseFloat(x); y = parseFloat(y); x = isNaN(x) ? -Infinity : x; y = isNaN(y) ? -Infinity : y; return asc ? x - y : y - x; }
            return asc ? x.localeCompare(y) : y.localeCompare(x);
          });
          rows.forEach(function (r) { body.appendChild(r); });
        };
        th.addEventListener("click", sort);
        th.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } });
      });
    });
    $$("[data-filter-controls]").forEach(function (c) {
      c.hidden = false;
      var input = $("[data-filter]", c);
      var table = $("table[data-filterable]");
      var scope = $("[data-filter-scope]");
      if (!input || (!table && !scope)) return;
      input.addEventListener("input", function () {
        var q = input.value.trim().toLowerCase();
        if (table) Array.prototype.forEach.call(table.tBodies[0].rows, function (r) { r.hidden = q && r.textContent.toLowerCase().indexOf(q) < 0; });
        if (!scope) return;
        $$("[data-q]", scope).forEach(function (n) { n.hidden = !!q && n.getAttribute("data-q").indexOf(q) < 0; });
        $$("[data-group]", scope).forEach(function (g) { g.hidden = !!q && !$("[data-q]:not([hidden])", g); });
      });
      var start = /[?&]q=([^&]*)/.exec(location.search);   // find/?q=word starts filtered
      if (start) { input.value = decodeURIComponent(start[1].replace(/\+/g, " ")); input.dispatchEvent(new Event("input")); }
    });
  }

  /* ---------------------------------------------------------------- index views and parts */
  function views() {
    $$("[data-views]").forEach(function (seg) {
      $$("button", seg).forEach(function (b) {
        b.addEventListener("click", function () {
          var v = b.getAttribute("data-value");
          pressed(seg, v);
          $$("[data-view]").forEach(function (n) { n.hidden = n.getAttribute("data-view") !== v; });
        });
      });
    });
  }

  function parts() {
    $$("[data-parts-scope]").forEach(function (scope) {
      var clear = function () {
        scope.removeAttribute("data-hl");
        $$("[data-on]", scope).forEach(function (n) { n.removeAttribute("data-on"); });
      };
      scope.addEventListener("mouseover", function (e) {
        var a = e.target.closest("[data-m]");
        if (!a) return;
        clear();
        scope.setAttribute("data-hl", "");
        $$("[data-m=\"" + a.getAttribute("data-m") + "\"]", scope).forEach(function (n) { n.setAttribute("data-on", ""); });
      });
      scope.addEventListener("mouseleave", clear);
      scope.addEventListener("mouseout", function (e) { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest("[data-m]")) clear(); });
    });
  }

  /* a poster becomes its video; without script the poster links the file */
  function video(a) {
    var img = $("img", a);
    var v = el("video", { "class": a.className, src: a.getAttribute("href"), poster: img ? img.getAttribute("src") : "", controls: "", playsinline: "", preload: "auto" });
    if (img) { v.setAttribute("width", img.getAttribute("width")); v.setAttribute("height", img.getAttribute("height")); }
    a.parentNode.replaceChild(v, a);
    return v;
  }
  function shorts() {
    $$('a[data-play]:not([data-play="episode"])').forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); video(a).play(); });
    });
  }

  /* an episode page: the poster plays from the start, or from the #t= in the page address; each scene time plays from
     that moment, and the scene list follows the video. Without script each time links the file at that second (#t=). */
  function episode() {
    var scope = $("[data-episode]"), a = scope && $('a[data-play="episode"]', scope);
    if (!a) return;
    var v = null, start = 0;
    var nav = $$("[data-kind=scenes] .row[data-seek]", scope), rows = $$("[data-kind=script] .row[data-start]", scope);
    function mark(t) {
      [[nav, "data-seek"], [rows, "data-start"]].forEach(function (g) {
        var cur = null;
        g[0].forEach(function (r) { if (parseFloat(r.getAttribute(g[1])) <= t + 0.25) cur = r; });
        g[0].forEach(function (r) { if (r === cur) r.setAttribute("aria-current", "true"); else r.removeAttribute("aria-current"); });
      });
    }
    function play(t) {
      if (!v) { v = video(a); v.addEventListener("timeupdate", function () { mark(v.currentTime); }); }
      var go = function () { v.currentTime = t; v.play(); };
      if (v.readyState >= 1) go(); else v.addEventListener("loadedmetadata", go, { once: true });
      mark(t);
      var r = v.getBoundingClientRect();
      if (r.top < 0 || r.bottom > window.innerHeight) v.scrollIntoView({ block: "center" });
    }
    a.addEventListener("click", function (e) { e.preventDefault(); play(start); });
    $$("a[data-seek]", scope).forEach(function (l) {
      l.addEventListener("click", function (e) { e.preventDefault(); play(parseFloat(l.getAttribute("data-seek"))); });
    });
    var m = /^#t=([\d.]+)$/.exec(location.hash);
    if (m) {
      start = parseFloat(m[1]);
      var plate = $(".plate", a), s = Math.round(start);
      if (plate) plate.textContent = "play from " + Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2);
      mark(start);
    }
  }

  /* a card beside the link under the pointer or keyboard focus, on screens with a mouse. Touch screens keep the plain
     link, which opens the card's twin. `attr` names the links' key into `cards`; `fill` writes the card for one entry;
     `kind`, when set, marks a card whose own links take the pointer, so it stays open while the pointer is on it. */
  function hovercard(scope, cards, id, attr, fill, kind) {
    var card = el("div", { "class": "panel", "data-style": "peek", role: "tooltip", id: id, hidden: "" });
    if (kind) card.setAttribute("data-kind", kind);
    document.body.appendChild(card);
    var cur = null, timer = 0, sel = "a[" + attr + "]";
    $$(sel + "[title]", scope).forEach(function (a) { a.removeAttribute("title"); });  // the card replaces the native tooltip
    function place(a) {
      var r = a.getBoundingClientRect(), w = card.offsetWidth, h = card.offsetHeight, gap = 8, edge = 16;
      var x = Math.max(edge, Math.min(r.left - 16, window.innerWidth - w - edge));
      var y = r.bottom + gap;
      if (y + h > window.innerHeight - edge) y = Math.max(edge, r.top - gap - h);
      card.style.left = x + "px";
      card.style.top = y + "px";
    }
    function show(a) {
      var c = cards[a.getAttribute(attr)];
      if (!c) return;
      if (cur) { cur.removeAttribute("data-on"); cur.removeAttribute("aria-describedby"); }
      cur = a;
      a.setAttribute("data-on", "");
      a.setAttribute("aria-describedby", card.id);
      card.textContent = "";
      fill(card, a, c);
      card.hidden = false;
      place(a);
    }
    function hide() {
      clearTimeout(timer);
      card.hidden = true;
      if (cur) { cur.removeAttribute("data-on"); cur.removeAttribute("aria-describedby"); }
      cur = null;
    }
    function later() { clearTimeout(timer); timer = setTimeout(hide, 120); }
    scope.addEventListener("mouseover", function (e) {
      var a = e.target.closest(sel);
      if (!a || card.contains(a)) return;
      clearTimeout(timer);
      if (a === cur) return;
      if (card.hidden) timer = setTimeout(function () { show(a); }, 120); else show(a);   // a short wait on entry, none between links
    });
    scope.addEventListener("mouseout", function (e) {
      var t = e.relatedTarget, to = t && t.closest ? t.closest(sel) : null;
      if ((to && scope.contains(to) && !card.contains(to)) || (kind && t && card.contains(t))) return;
      later();
    });
    if (kind) {
      card.addEventListener("mouseenter", function () { clearTimeout(timer); });
      card.addEventListener("mouseleave", function (e) { if (!(e.relatedTarget && cur && cur.contains(e.relatedTarget))) later(); });
    }
    scope.addEventListener("focusin", function (e) { var a = e.target.closest(sel); if (a && !card.contains(a)) { clearTimeout(timer); show(a); } });
    scope.addEventListener("focusout", function (e) { if (!(kind && e.relatedTarget && card.contains(e.relatedTarget))) hide(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
    window.addEventListener("scroll", hide, { passive: true });
  }
  function canHover() { return window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches; }
  function json(id) { var n = document.getElementById(id); try { return n ? JSON.parse(n.textContent) : null; } catch (err) { return null; } }

  /* the home mosaic: a mechanic's card beside its icon. Its fields are all on the record page the icon opens. */
  function peek() {
    if (!canHover()) return;
    $$("[data-cards]").forEach(function (scope) {
      var id = scope.getAttribute("data-cards"), cards = json(id);
      if (!cards) return;
      hovercard(scope, cards, "peek-" + id, "data-card", function (card, a, c) {
        var img = $("img", a), eb = el("p", { "class": "eyebrow" }), dl = el("dl", { "class": "receipt", "data-style": "bare" });
        card.appendChild(el("img", { "data-icon": "", src: img ? img.getAttribute("src") : "", width: "48", height: "48", alt: "" }));
        eb.appendChild(el("span", { "class": "id" }, a.getAttribute("data-card")));
        eb.appendChild(el("span", null, c[1]));
        card.appendChild(eb);
        card.appendChild(el("h3", null, c[0]));
        if (c[2]) card.appendChild(el("p", null, c[2]));
        [["used by", c[3] ? c[3] + (c[3] === 1 ? " game" : " games") + (c[4] ? " · core in " + c[4] : "") : "no catalogued game yet"],
         ["first seen", c[5] ? c[5] + (c[6] ? " · " + c[6] : "") : null],
         ["techniques", c[7] ? c[7] + (c[7] === 1 ? " affects it" : " affect it") : null]].forEach(function (r) {
          if (r[1] == null) return;
          dl.appendChild(el("dt", null, r[0]));
          dl.appendChild(el("dd", null, r[1]));
        });
        card.appendChild(dl);
      });
    });
  }

  /* contributors: a person's card beside their name in a byline or the contributors table, with their links.
     Its twin is the contributors table (paper appendix D), which the byline names link to. */
  function people() {
    var cards = json("people");
    if (!cards || !canHover()) return;
    function n(k, one, many) { return k + " " + (k === 1 ? one : many); }
    hovercard(document.body, cards, "peek-people", "data-person", function (card, a, c) {
      var eb = el("p", { "class": "eyebrow" }), dl = el("dl", { "class": "receipt", "data-style": "bare" }), dd = el("dd");
      eb.appendChild(el("span", { "class": "id" }, a.getAttribute("data-person")));
      eb.appendChild(el("span", null, "since " + c.since));
      card.appendChild(eb);
      card.appendChild(el("h3", null, c.name));
      [["runs", String(c.runs)],
       ["created", [c.records ? n(c.records, "record", "records") : "", c.sources ? n(c.sources, "source", "sources") : ""].filter(Boolean).join(" · ") || null],
       ["verified", c.verified ? n(c.verified, "record", "records") : null],
       ["rated", c.rated ? n(c.rated, "score", "scores") : null]].forEach(function (r) {
        if (r[1] == null) return;
        dl.appendChild(el("dt", null, r[0]));
        dl.appendChild(el("dd", null, r[1]));
      });
      c.links.forEach(function (l, i) {
        if (i) dd.appendChild(document.createTextNode(" · "));
        dd.appendChild(el("a", { href: l[1], rel: "noopener" }, l[0]));
      });
      dl.appendChild(el("dt", null, "links"));
      dl.appendChild(dd);
      card.appendChild(dl);
    }, "person");
  }

  /* ---------------------------------------------------------------- figure: matrix */
  function matrix(fig, data, svg) {
    var mode = { rows: "cluster", cols: "family" };
    var cellRole = {};
    data.cells.forEach(function (c) { cellRole[c[0] * 1000 + c[1]] = c[2]; });
    var hlRow = $("[data-hl=row]", svg), hlCol = $("[data-hl=col]", svg);
    var rects = $$("rect[data-r]", svg);
    var pinned = false;
    function find(arr, v) {
      for (var i = 0; i < arr.length; i++) if (v >= arr[i] - 0.5 && v < arr[i] + data.pitch - 0.5) return i;
      return -1;
    }
    function apply() {
      rects.forEach(function (r) {
        r.setAttribute("x", data.colX[mode.cols][+r.getAttribute("data-c")]);
        r.setAttribute("y", data.rowY[mode.rows][+r.getAttribute("data-r")]);
      });
      ["cluster", "year"].forEach(function (m) { var g = $("[data-layer=rows-" + m + "]", svg); if (g) g.setAttribute("display", m === mode.rows ? "inline" : "none"); });
      ["family", "first"].forEach(function (m) { var g = $("[data-layer=cols-" + m + "]", svg); if (g) g.setAttribute("display", m === mode.cols ? "inline" : "none"); });
    }
    function show(r, c) {
      hlRow.setAttribute("display", r >= 0 ? "inline" : "none");
      hlCol.setAttribute("display", c >= 0 ? "inline" : "none");
      if (r >= 0) hlRow.setAttribute("y", data.rowY[mode.rows][r] - 0.5);
      if (c >= 0) hlCol.setAttribute("x", data.colX[mode.cols][c] - 0.5);
      if (r < 0 && c < 0) return;
      var parts = [];
      if (r >= 0) { var g = data.rows[r]; parts.push(link("game", g.id, g.name)); parts.push(String(g.year)); parts.push("cluster " + (g.cluster || "").toLowerCase()); }
      if (c >= 0) { var m = data.cols[c]; parts.push(link("mechanic", m.id, m.name)); parts.push(m.family.toLowerCase()); }
      if (r >= 0 && c >= 0) { var role = cellRole[r * 1000 + c]; parts.push(bold(role === 2 ? "core use" : role === 1 ? "supporting use" : "not used")); }
      readout(fig, parts);
    }
    svg.addEventListener("pointermove", function (e) {
      if (pinned) return;
      var p = svgPoint(svg, e);
      show(find(data.rowY[mode.rows], p.y), find(data.colX[mode.cols], p.x));
    });
    svg.addEventListener("click", function (e) {
      var p = svgPoint(svg, e);
      if (e.target.closest && e.target.closest("a")) return;
      pinned = false;
      show(find(data.rowY[mode.rows], p.y), find(data.colX[mode.cols], p.x));
      pinned = true;  // a tap or click pins the cell; the next one moves the pin
    });
    $$("[data-controls=matrix] .segmented", fig).forEach(function (g) {
      g.addEventListener("click", function (e) {
        var b = e.target.closest("button"); if (!b) return;
        mode[b.getAttribute("data-set")] = b.getAttribute("data-value");
        pressed(g, b.getAttribute("data-value"));
        apply();
      });
    });
    readout(fig, ["hover or tap a square to read it; a click or tap pins it"]);
  }

  /* ---------------------------------------------------------------- figure: strata */
  function strata(fig, data, svg) {
    var line = $("[data-hl=year]", svg);
    var range = $("[data-set=year]", fig);
    var span = data.right - data.left, n = data.y1 - data.y0 + 1;
    var activeLayer = null;
    function xOf(y) { return data.left + (y - data.y0) / n * span; }
    function setYear(y) {
      y = Math.max(data.y0, Math.min(data.y1, y));
      line.setAttribute("display", "inline");
      line.setAttribute("x1", xOf(y) + 1); line.setAttribute("x2", xOf(y) + 1);
      if (range) range.value = y;
      var total = data.total[data.years.indexOf(y)];
      var added = data.added[String(y)] || [];
      var parts = [bold(String(y)), total + " mechanics seen"];
      if (activeLayer) parts.unshift(activeLayer.getAttribute("data-label").toLowerCase() + ": " + activeLayer.getAttribute("data-count") + " mechanics, first in " + activeLayer.getAttribute("data-first"));
      if (added.length) {
        var games = {};
        added.forEach(function (a) { games[a[3]] = a[4]; });
        parts.push("+" + added.length + " new: " + added.slice(0, 6).map(function (a) { return a[1].toLowerCase(); }).join(", ") + (added.length > 6 ? ", …" : ""));
        var gs = Object.keys(games);
        parts.push(gs.length === 1 ? link("game", gs[0], games[gs[0]]) : "from " + gs.length + " games");
      } else parts.push("no new mechanics this year");
      readout(fig, parts);
    }
    svg.addEventListener("pointermove", function (e) {
      var p = svgPoint(svg, e);
      if (p.x < data.left || p.x > data.right) return;
      setYear(data.y0 + Math.floor((p.x - data.left) / span * n));
    });
    $$("path[data-family]", svg).forEach(function (pth) {
      pth.addEventListener("pointerenter", function () { activeLayer = pth; pth.setAttribute("data-fo", pth.getAttribute("fill-opacity")); pth.setAttribute("fill-opacity", "0.32"); });
      pth.addEventListener("pointerleave", function () { pth.setAttribute("fill-opacity", pth.getAttribute("data-fo")); activeLayer = null; });
    });
    $$("line[data-game]", svg).forEach(function (t) {
      t.style.cursor = "pointer";
      t.addEventListener("pointerenter", function () { var g = data.games[t.getAttribute("data-game")]; readout(fig, [link("game", t.getAttribute("data-game"), g[0]), String(g[1])]); });
    });
    if (range) range.addEventListener("input", function () { setYear(+range.value); });
    svg.addEventListener("click", function (e) {
      var p = svgPoint(svg, e);
      if (p.x >= data.left && p.x <= data.right) setYear(data.y0 + Math.floor((p.x - data.left) / span * n));
    });
    readout(fig, ["hover or tap the layers, or drag the year, to read what each year added"]);
  }

  /* ---------------------------------------------------------------- figure: design map */
  function designMap(fig, data, svg) {
    var nodes = data.nodes;
    var rects = $$("rect[data-i]", svg);
    var hl = $("[data-hl=node]", svg);
    var links = $("[data-layer=links]", svg);
    var subLabel = {};
    data.subgenres.forEach(function (s) { subLabel[s[0]] = s[1]; });
    var pinned = false, current = -1, selected = "";
    function nearest(p, r) {
      var best = -1, bd = (r || 22) * (r || 22);
      for (var i = 0; i < nodes.length; i++) {
        var dx = nodes[i].x - p.x, dy = nodes[i].y - p.y, d = dx * dx + dy * dy;
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    }
    function show(i) {
      current = i;
      while (links.firstChild) links.removeChild(links.firstChild);
      if (i < 0) { hl.setAttribute("display", "none"); if (!selected) readout(fig, ["hover or tap a game to see its nearest neighbours"]); return; }
      var n = nodes[i];
      hl.setAttribute("display", "inline"); hl.setAttribute("x", n.x - 6); hl.setAttribute("y", n.y - 6);
      n.n.forEach(function (j) { links.appendChild(svgEl("line", { x1: n.x, y1: n.y, x2: nodes[j].x, y2: nodes[j].y })); });
      var nb = el("span", null, "nearest: ");
      n.n.forEach(function (j, k) { if (k) nb.appendChild(document.createTextNode(", ")); nb.appendChild(link("game", nodes[j].id, nodes[j].name)); });
      readout(fig, [link("game", n.id, n.name), String(n.year), (subLabel[n.sub] || n.sub).toLowerCase(), (n.cluster || "").toLowerCase() + " " + (data.clusters[n.cluster] || "").toLowerCase(), nb]);
    }
    svg.addEventListener("pointermove", function (e) { if (!pinned) show(nearest(svgPoint(svg, e))); });
    svg.addEventListener("pointerleave", function () { if (!pinned) show(-1); });
    svg.addEventListener("click", function (e) { var i = nearest(svgPoint(svg, e), 40); pinned = i >= 0 && !(pinned && i === current); show(i); });
    var sel = $("[data-set=subgenre]", fig);
    if (sel) sel.addEventListener("change", function () {
      selected = sel.value;
      var counts = {};
      rects.forEach(function (r) {
        var n = nodes[+r.getAttribute("data-i")];
        var on = !selected || n.sub === selected;
        r.style.fill = selected && on ? "var(--accent)" : "";
        r.setAttribute("fill-opacity", on ? "1" : "0.18");
        if (selected && on) counts[n.cluster] = (counts[n.cluster] || 0) + 1;
      });
      if (!selected) { readout(fig, ["hover or tap a game to see its nearest neighbours"]); return; }
      var ks = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a] || (a < b ? -1 : 1); });
      var total = ks.reduce(function (s, k) { return s + counts[k]; }, 0);
      readout(fig, [bold((subLabel[selected] || selected).toLowerCase()), total + " games across " + ks.length + (ks.length === 1 ? " island" : " islands"),
        ks.map(function (k) { return k.toLowerCase() + " " + counts[k]; }).join(", ")]);
    });
    $$("[data-key]", fig).forEach(function (g) {
      var island = $("path[data-cluster='" + g.getAttribute("data-key") + "']", svg);
      var on = function () { if (island) { island.style.stroke = "var(--accent)"; island.style.strokeWidth = "2"; } };
      var off = function () { if (island) { island.style.stroke = ""; island.style.strokeWidth = ""; } };
      g.addEventListener("pointerenter", on); g.addEventListener("pointerleave", off);
      g.addEventListener("click", function () { on(); setTimeout(off, 1600); });
    });
    readout(fig, ["hover or tap a game to see its nearest neighbours"]);
  }

  /* ---------------------------------------------------------------- figure: vacant lots */
  function vacantLots(fig, data, svg) {
    var hl = $("[data-hl=lot]", svg);
    var lots = $$("[data-k]", svg);
    var pinned = false;
    function show(k) {
      if (!k) { hl.setAttribute("display", "none"); return; }
      var ij = k.split("-"), i = +ij[0], j = +ij[1], v = data.pairs[k];
      hl.setAttribute("display", "inline");
      hl.setAttribute("x", data.left + data.pos[j] - 2); hl.setAttribute("y", data.top + data.pos[i] - 2);
      var a = data.m[i], b = data.m[j];
      var status = v[3] ? "vacant, white-space rank " + v[4] : v[5] ? "in design tension" : v[2] >= 2 ? "built well above chance" : v[2] >= 1 ? "built about as often as chance" : "built less than chance";
      readout(fig, [link("mechanic", a[0], a[1]), link("mechanic", b[0], b[1]), "together in " + v[0] + " of " + data.N + " games", v[1] + " expected", "lift " + v[2], bold(status)]);
    }
    svg.addEventListener("pointermove", function (e) {
      if (pinned) return;
      var t = e.target.closest ? e.target.closest("[data-k]") : null;
      show(t ? t.getAttribute("data-k") : null);
    });
    svg.addEventListener("click", function (e) { var t = e.target.closest("[data-k]"); pinned = !!t && !pinned; show(t ? t.getAttribute("data-k") : null); });
    $$("[data-controls=vacant-lots] .segmented", fig).forEach(function (g) {
      g.addEventListener("click", function (e) {
        var b = e.target.closest("button"); if (!b) return;
        var only = b.getAttribute("data-value") === "vacant";
        pressed(g, b.getAttribute("data-value"));
        lots.forEach(function (r) { var v = data.pairs[r.getAttribute("data-k")]; r.style.opacity = only && !v[3] ? "0.12" : ""; });
      });
    });
    readout(fig, ["hover or tap a lot to read the pair"]);
  }

  /* ---------------------------------------------------------------- figure: technique flows */
  function flows(fig, data, svg) {
    var ribbons = $$("path[data-t]", svg);
    var mode = "edges";
    ribbons.forEach(function (r) { r.setAttribute("data-d1", r.getAttribute("d")); r.setAttribute("data-fo", r.getAttribute("fill-opacity")); });
    $$("[data-node]", svg).forEach(function (n) {
      if (n.hasAttribute("y")) n.setAttribute("data-y1", n.getAttribute("y"));
      if (n.hasAttribute("height")) n.setAttribute("data-h1", n.getAttribute("height"));
    });
    function match(r, key) {
      if (!key) return true;
      var kv = key.split(":"), k = kv[0], v = kv.slice(1).join(":");
      return r.getAttribute("data-" + k) === v;
    }
    function highlight(key, single) {
      ribbons.forEach(function (r) {
        var on = single ? r === single : match(r, key);
        r.setAttribute("fill-opacity", key || single ? (on ? "0.85" : "0.04") : r.getAttribute("data-fo"));
      });
    }
    function nodeReadout(key) {
      var kv = key.split(":"), k = kv[0], v = kv.slice(1).join(":"), info = data[k][v];
      var i = mode === "edges" ? 0 : 1;
      if (k === "t") readout(fig, [link("technique", v, info[0]), info[1].toLowerCase(), mode === "edges" ? info[2] + " affects edges" : "exposure " + info[3]]);
      else readout(fig, [bold(info[0].toLowerCase()), mode === "edges" ? info[1] + " affects edges" : "exposure " + info[2]]);
    }
    svg.addEventListener("pointerover", function (e) {
      var n = e.target.closest ? e.target.closest("[data-node]") : null;
      if (n) { highlight(n.getAttribute("data-node")); nodeReadout(n.getAttribute("data-node")); return; }
      var r = e.target.closest ? e.target.closest("path[data-t]") : null;
      if (r) {
        highlight(null, r);
        var t = r.getAttribute("data-t"), ef = r.getAttribute("data-e"), f = r.getAttribute("data-f");
        readout(fig, [link("technique", t, data.t[t][0]), data.e[ef][0].toLowerCase(), data.f[f][0].toLowerCase(),
          mode === "edges" ? r.getAttribute("data-v") + " edges" : "exposure " + r.getAttribute("data-v2")]);
      }
    });
    svg.addEventListener("pointerleave", function () { highlight(null); readout(fig, ["hover or tap a technique, an effect, or a family"]); });
    $$("[data-controls=technique-flows] .segmented", fig).forEach(function (g) {
      g.addEventListener("click", function (e) {
        var b = e.target.closest("button"); if (!b) return;
        mode = b.getAttribute("data-value");
        pressed(g, mode);
        var two = mode === "exposure";
        ribbons.forEach(function (r) { r.setAttribute("d", r.getAttribute(two ? "data-d2" : "data-d1")); });
        $$("[data-node]", svg).forEach(function (n) {
          if (n.hasAttribute("data-y2")) n.setAttribute("y", n.getAttribute(two ? "data-y2" : "data-y1"));
          if (n.hasAttribute("data-h2")) n.setAttribute("height", n.getAttribute(two ? "data-h2" : "data-h1"));
          if (n.hasAttribute("data-v")) { var ts = n.querySelector("tspan"); if (ts) ts.textContent = n.getAttribute(two ? "data-v2" : "data-v"); }
        });
      });
    });
    readout(fig, ["hover or tap a technique, an effect, or a family"]);
  }

  var FIGS = { "matrix": matrix, "strata": strata, "design-map": designMap, "vacant-lots": vacantLots, "technique-flows": flows };

  function figures() {
    $$("figure[data-viz]").forEach(function (fig) {
      var name = fig.getAttribute("data-viz");
      var script = document.getElementById("viz-data-" + name);
      var svg = $("svg", fig);
      if (!script || !svg || !FIGS[name]) return;
      var data;
      try { data = JSON.parse(script.textContent); } catch (err) { return; }
      $$("[data-viz-controls], [data-readout]", fig).forEach(function (n) { n.hidden = false; });
      try { FIGS[name](fig, data, svg); } catch (err) { if (window.console) console.error("simgrammar figure " + name, err); }
    });
  }

  function init() { toc(); tables(); views(); parts(); shorts(); episode(); peek(); people(); figures(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
