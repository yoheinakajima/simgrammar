// Frame templates for render.html (ADR-0006). Each takes the frame resolved by framedata.py, the ids that are current,
// and the stage size, and returns HTML. Pictures are pre-dithered icons at 3 px per dither pixel (16:9) or 4 px (9:16):
// the icon's own size comes from dist/visual, larger draws (72 to 144 dpx, redrawn from the vector) from the render's
// icon cache. Text stays vector. Nothing here computes a number: framedata.py read them from the dataset.
//
// Layout units carry class f-u: render.html snaps each unit so its first icon sits on the 8-dpx grid (the Bayer pattern
// repeats every 8 dpx, so neighbouring sprites line up), and builds units in document order (motion, render.js).
let VISDIR = "", SIZEDIR = "";
const VERT = () => document.body.classList.contains("v");
const PX = () => (VERT() ? 4 : 3);
const G = () => 8 * PX();
const ic = (e, on, dpx, cls = "") => {
  if (!e || !e.icon) return tile(e, on, dpx, cls);
  const n = dpx || e.size, acc = on ? ".accent" : "";
  const src = n === e.size ? `${VISDIR}/icons/${e.icon}${acc}@${PX()}x.png` : `${SIZEDIR}/${e.icon}${acc}.${n}@${PX()}x.png`;
  return `<img class="f-ic ${cls}" src="${src}" width="${n * PX()}" height="${n * PX()}" alt="">`;
};
// an element with no icon yet is a type tile of the same size, never a broken picture
const tile = (e, on, dpx, cls = "") => {
  const n = (dpx || 48) * PX();
  return `<div class="f-ic f-tic ${cls}${on ? " on" : ""}" style="width:${n}px;height:${n}px"></div>`;
};
const isOn = (cur, id) => (cur || []).includes(id);
const bar = (n, N, on) => `<span class="f-bar${on ? " on" : ""}"><i data-w="${Math.max(2, 100 * n / N).toFixed(1)}" style="width:${Math.max(2, 100 * n / N).toFixed(1)}%"></i></span>`;
const cnt = (n) => `<span class="f-cnt" data-n="${n}">${n}</span>`;
const games = (n, N) => `${cnt(n)} of ${N} games`;
// draw size for n items in a row of width w: the largest of 144..48 dpx that leaves room for labels
const fit = (n, w, opts = {}) => {
  const max = opts.max || 96, min = opts.min || 48, pad = opts.pad || 0.72;
  for (const d of [144, 120, 96, 72, 48]) if (d <= max && d >= min && n * d * PX() <= w * pad) return d;
  return min;
};

// the first option whose layout fits, else the last
const pick = (opts, fits) => opts.find(fits) || opts[opts.length - 1];

const T = {};

T.anatomy = (f, cur, W, H) => {
  const n = f.parts.length, v = VERT();
  const yr = p => f.dates && p.year ? `<div class="f-mono${p.first === f.name ? " acc" : ""}">${p.year} · ${p.first === f.name ? "first here" : esc(p.first)}</div>` : `<div class="f-mono">${f.firsts ? "now in " : ""}${games(p.n, f.N)}</div>`;
  if (!v && n > 8) {   // many parts: the subject on the left, the parts as an inventory on the right
    const d = n <= 12 ? 48 : 42, cols = n <= 12 ? 3 : 4;
    const parts = f.parts.map(p => `<div class="f-prow f-u">${ic(p, isOn(cur, p.id), d)}<div><div class="f-lab sm${isOn(cur, p.id) ? " acc" : ""}">${esc(p.label)}</div>${yr(p)}</div></div>`).join("");
    return `<div class="f-anat f-inv"><div class="f-invs f-u">${ic((f.subject || { label: f.name }), false, 120)}<div class="f-name">${esc(f.name)}</div><div class="f-mono">${esc(f.meta)}</div><div class="f-mono ink">${esc(f.counts)}</div></div><div class="f-invp" style="grid-template-columns:repeat(${cols},1fr)">${parts}</div></div>`;
  }
  if (v && n > 6) {   // 9:16 with many parts: a compact grid of icons with short labels
    const cols = n > 8 ? 4 : 3, d = 42;
    const parts = f.parts.map(p => `<div class="f-vcell f-u">${ic(p, isOn(cur, p.id), d)}<div class="f-lab sm${isOn(cur, p.id) ? " acc" : ""}">${esc(p.label)}</div>${yr(p)}</div>`).join("");
    return `<div class="f-anat v"><div class="f-subjrow f-u">${ic(f.subject || { label: f.name }, false, 48)}<div><div class="f-name">${esc(f.name)}</div><div class="f-mono">${esc(f.meta)}</div><div class="f-mono ink">${esc(f.counts)}</div></div></div><div class="f-vgrid" style="grid-template-columns:repeat(${cols},1fr)">${parts}</div></div>`;
  }
  if (v) {
    const P = PX();
    const [d, sd] = pick([[72, 96], [72, 72], [48, 96], [48, 72], [42, 72], [42, 48]].filter(([d]) => d < 72 || n <= 4), ([d, sd]) => {
      const rows = d >= 72 ? n : Math.ceil(n / 2);
      return sd * P + 40 + rows * d * P + (rows - 1) * (d >= 72 ? 28 : 34) <= H;
    });
    const parts = f.parts.map(p => `<div class="f-prow f-u">${ic(p, isOn(cur, p.id), d)}<div><div class="f-lab${isOn(cur, p.id) ? " acc" : ""}">${esc(p.label)}</div>${yr(p)}${f.dates ? "" : bar(p.n, f.N, isOn(cur, p.id))}</div></div>`).join("");
    return `<div class="f-anat v${d >= 72 ? " one" : ""}"><div class="f-subjrow f-u">${ic((f.subject || { label: f.name }), false, sd)}<div><div class="f-name">${esc(f.name)}</div><div class="f-mono">${esc(f.meta)}</div><div class="f-mono ink">${esc(f.counts)}</div></div></div><div class="f-pgrid">${parts}</div></div>`;
  }
  const d = n <= 8 ? 72 : 48;
  const parts = f.parts.map(p => `<div class="f-part f-u">${ic(p, isOn(cur, p.id), d)}<div class="f-lab${isOn(cur, p.id) ? " acc" : ""}">${esc(p.label)}</div>${yr(p)}${f.dates ? "" : bar(p.n, f.N, isOn(cur, p.id))}<div class="f-tick${isOn(cur, p.id) ? " on" : ""}"></div></div>`).join("");
  return `<div class="f-anat${d === 72 ? " f-big" : ""}"><div class="f-parts">${parts}</div><div class="f-bus" style="left:${50 / n}%;right:${50 / n}%"></div><div class="f-stem"></div>
  <div class="f-subj"><div class="f-u">${ic((f.subject || { label: f.name }), false, 96)}</div><div class="f-subjtext f-u"><div class="f-name">${esc(f.name)}</div><div class="f-mono">${esc(f.meta)}</div><div class="f-mono ink">${esc(f.counts)}</div></div>
  <div class="f-key f-mono">${f.dates ? "year: first catalog game to use the part" : `core: a different game without it<br>bar: share of the ${f.N} catalog games`}</div></div></div>`;
};

T.hub = (f, cur, W, H) => {
  const v = VERT(), d = f.spokes.length > 2 && !v ? 48 : 72, S = PX() * d;
  const two = f.spokes.length <= 2;
  const cx = W / 2, cy = H * (two ? (v ? 0.68 : 0.64) : 0.5);
  const pos = two
    ? (v ? [[0.25, 0.2], [0.75, 0.2]] : [[0.2, 0.28], [0.8, 0.28]])
    : (v ? [[0.24, 0.18], [0.76, 0.18], [0.24, 0.84], [0.76, 0.84]] : [[0.17, 0.2], [0.83, 0.2], [0.17, 0.8], [0.83, 0.8]]);
  const maxw = Math.max(...f.spokes.map(s => s.w));
  let lines = "", items = "";
  f.spokes.forEach((s, k) => {
    const [px, py] = pos[k % pos.length]; const x = px * W, y = py * H;
    const dx = x - cx, dy = y - cy, dd = Math.hypot(dx, dy), ux = dx / dd, uy = dy / dd;
    const on = isOn(cur, s.id), w = 3 + 15 * (s.w / maxw) ** 2;
    lines += `<line class="f-draw" x1="${(cx + ux * S * 0.72).toFixed(1)}" y1="${(cy + uy * S * 0.72).toFixed(1)}" x2="${(x - ux * S * 0.7).toFixed(1)}" y2="${(y - uy * S * 0.7).toFixed(1)}" stroke="${on ? "#0550ae" : "#3d3d38"}" stroke-width="${w.toFixed(1)}" stroke-linecap="round"/>`;
    const up = py < 0.5;
    const txt = `<div class="f-lab${on ? " acc" : ""}">${esc(s.label)}</div><div class="f-mono${on ? " acc" : ""}">advertises ${esc(s.need)}</div>`;
    const th = v ? 112 : 96;
    items += `<div class="f-spoke f-u" style="left:${x - 200}px;top:${up ? y - S / 2 - th : y - S / 2}px">${up ? txt : ""}${ic(s, on, d)}${up ? "" : txt}</div>`;
  });
  return `<div class="f-hub" style="width:${W}px;height:${H}px"><svg width="${W}" height="${H}">${lines}</svg>${items}
  <div class="f-hubc f-u" style="left:${cx - S / 2}px;top:${cy - S / 2}px">${ic(f.hub, false, d)}</div>
  ${f.weights ? `<div class="f-mono faint f-wnote" style="left:${cx - 200}px;top:${cy + S / 2 + 18}px">${esc(f.weights)}</div>` : ""}</div>`;
};

T.blank = (f, cur, W, H) => {
  const v = VERT(), d = v ? 48 : 72;
  if (v) {
    const slots = Array.from({ length: f.slots }, () => `<div class="f-prow f-u"><div class="f-slot" style="width:${d * PX()}px;height:${d * PX()}px"></div><div><div class="f-lab faint">a part</div><div class="f-mono faint">core or supporting · games using it</div></div></div>`).join("");
    return `<div class="f-anat v"><div class="f-subjrow f-u"><div class="f-slot" style="width:${96 * PX()}px;height:${72 * PX()}px"></div><div><div class="f-name faint">${esc(f.label)}</div><div class="f-mono">list its parts · mark the core ones · count the games</div></div></div><div class="f-pgrid">${slots}</div></div>`;
  }
  const slots = Array.from({ length: f.slots }, () => `<div class="f-part f-u"><div class="f-slot" style="width:${d * PX()}px;height:${d * PX()}px"></div><div class="f-lab faint">a part</div><div class="f-mono faint">${f.dates ? "first catalog game<br>and its year" : "core or supporting<br>games using it"}</div><div class="f-tick"></div></div>`).join("");
  return `<div class="f-anat f-big"><div class="f-parts">${slots}</div><div class="f-bus" style="left:${50 / f.slots}%;right:${50 / f.slots}%"></div><div class="f-stem"></div>
  <div class="f-subj"><div class="f-slot f-u" style="width:${96 * PX()}px;height:${72 * PX()}px"></div><div class="f-subjtext f-u"><div class="f-name faint">${esc(f.label)}</div><div class="f-mono">list its parts · mark the core ones · count the games</div></div></div></div>`;
};

const arrow = (len, on, vert) => {   // len = 0: stretch to fill the link
  const c = on ? " on" : "";
  return vert ? `<div class="f-arr v${c}" style="${len ? `height:${len}px` : ""}"><i></i><b></b></div>` : `<div class="f-arr${c}" style="${len ? `width:${len}px` : ""}"><i></i><b></b></div>`;
};

T.chain = (f, cur, W, H) => {
  if (f.fan) return T.fan(f, cur, W, H);
  const v = VERT();
  const strip = f.strip && f.strip.length ? `<div class="f-strip">${f.strip.map(x => `<span class="${x.on ? "acc" : "faint"}">${esc(x.text)}</span>`).join('<span class="f-dot"> · </span>')}</div>` : "";
  const title = f.title ? `<div class="f-mono ink f-title">${esc(f.title)}</div>` : "";
  const two = f.rows.length > 1;
  const most = Math.max(...f.rows.map(r => r.nodes.length));
  const nn = f.rows.reduce((a, r) => a + r.nodes.length, 0);
  const avail = H - (strip ? 80 : 0) - (title ? 44 : 0) - (f.rows.some(r => r.links.some(l => l.sign)) ? 56 : 0) - f.rows.filter(r => r.loop).length * 60;
  const [d, lh] = v ? pick([[72, 96], [48, 96], [48, 72], [42, 64], [42, 52]], ([d, lh]) => nn * d * PX() + (nn - f.rows.length) * lh <= avail) : [two || most > 4 ? 48 : 72, 0];
  const node = (nd) => {
    const on = isOn(cur, nd.id);
    return `<div class="f-node f-u${two ? " sm" : ""}">${ic(nd, on, d)}<div class="f-ntext"><div class="f-lab${on ? " acc" : ""}">${esc(nd.label)}</div>${nd.note && !two && !(v && d < 72 && nn > 3) ? `<div class="f-mono f-note">${esc(nd.note)}</div>` : ""}${nd.n != null ? `<div class="f-mono ink">${nd.mname ? esc(nd.mname.toLowerCase()) + " · " : ""}in ${cnt(nd.n)} of ${f.N} games</div>` : ""}</div></div>`;
  };
  const link = (lk, on) => `<div class="f-link"${v ? ` style="height:${lh}px;padding-left:${d * PX() / 2 - 12}px"` : ""}>${lk.verb ? `<div class="f-mono${on ? " acc" : ""} f-verb">${esc(lk.verb)}</div>` : ""}<div class="f-arrow">${arrow(v ? lh - 24 : 0, on, v)}${lk.sign ? `<span class="f-sign${on ? " on" : ""}">${esc(lk.sign)}</span>` : ""}</div></div>`;
  const rows = f.rows.map(r => {
    let h = "";
    r.nodes.forEach((nd, k) => {
      h += node(nd);
      if (k < r.nodes.length - 1) h += link(r.links[k], isOn(cur, r.nodes[k + 1].id));
    });
    const lp = r.loop ? `<div class="f-loop f-u"><div class="f-loopline"></div><div class="f-mono ink">${r.loop === "R" ? "reinforcing loop" : "balancing loop"}${r.links[r.nodes.length - 1] && r.links[r.nodes.length - 1].sign ? ` <span class="f-sign sm">${esc(r.links[r.nodes.length - 1].sign)}</span>` : ""}${r.links[r.nodes.length - 1] && r.links[r.nodes.length - 1].verb ? ` · ${esc(r.links[r.nodes.length - 1].verb)}` : ""}</div></div>` : "";
    return `<div class="f-crow">${h}</div>${lp}`;
  }).join("");
  return `<div class="f-chain${v ? " v" : ""}${two ? " two" : ""}${d > 48 ? " f-big" : ""}">${strip}${title}<div class="f-rows">${rows}</div>${f.rows.some(r => r.links.some(l => l.sign)) ? `<div class="f-mono faint f-legend">signs: + same direction · − opposite direction</div>` : ""}</div>`;
};

// a fan: the first node feeds every other node
T.fan = (f, cur, W, H) => {
  const v = VERT(), r = f.rows[0], root = r.nodes[0], leaves = r.nodes.slice(1), n = leaves.length;
  const d = v ? 48 : (n <= 4 ? 72 : 48);
  const leaf = (nd, k) => { const on = isOn(cur, nd.id), lk = r.links[k] || {};
    return `<div class="f-leaf f-u">${ic(nd, on, d)}<div class="f-lab${on ? " acc" : ""}">${esc(nd.label)}</div>${lk.verb ? `<div class="f-mono${on ? " acc" : ""}">${esc(lk.verb)}</div>` : ""}</div>`; };
  const rootOn = isOn(cur, root.id);
  return `<div class="f-fan${v ? " v" : ""}">${f.title ? `<div class="f-mono ink f-title">${esc(f.title)}</div>` : ""}<div class="f-froot f-u">${ic(root, rootOn, v ? 72 : 96)}<div class="f-lab${rootOn ? " acc" : ""}">${esc(root.label)}</div></div>
  <div class="f-fanarr">${leaves.map((nd, k) => `<div class="f-fslot">${arrow(v ? 56 : 64, isOn(cur, nd.id), true)}</div>`).join("")}</div>
  <div class="f-leaves">${leaves.map(leaf).join("")}</div></div>`;
};

T.compare = (f, cur, W, H) => {
  const v = VERT();
  const most = Math.max(f.a.items.length, f.b.items.length);
  const d = v ? (most <= 3 ? 72 : 48) : (most <= 2 ? 96 : most <= 3 ? 72 : 48);
  const col = (c) => `<div class="f-col"><div class="f-ctitle f-u">${esc(c.title)}</div><div class="f-citems">${c.items.map(e => `<div class="f-citem f-u">${ic(e, isOn(cur, e.id), d)}<div class="f-lab${isOn(cur, e.id) ? " acc" : ""}">${esc(e.label)}</div></div>`).join("")}</div></div>`;
  return `<div class="f-compare${v ? " v" : ""}"><div class="f-cols">${col(f.a)}<div class="f-vrule"></div>${col(f.b)}</div>${f.note ? `<div class="f-mono f-cnote f-u">record: ${esc(f.note)}</div>` : ""}</div>`;
};

T.bars = (f, cur, W, H) => {
  const v = VERT(), d = v ? pick([72, 48, 42], d => f.items.length * (d * PX() + 20) <= H) : (f.items.length <= 4 ? 72 : 48);
  const items = f.items.map(e => {
    const on = isOn(cur, e.id);
    return `<div class="f-bitem f-u">${f.rank ? `<div class="f-rank${on ? " acc" : ""}">${e.rank}</div>` : ""}${ic(e, on, d)}<div class="f-btext"><div class="f-lab${on ? " acc" : ""}">${esc(e.label)}</div><div class="f-num${on ? " acc" : ""}">${cnt(e.n)}<small> of ${f.N} ${esc(f.of || "games")}</small></div>${bar(e.n, f.N, on)}${e.games && e.games.length ? `<div class="f-mono f-bgames${on ? " acc" : ""}">${e.games.map(esc).join(" · ")}</div>` : ""}</div></div>`;
  }).join("");
  return `<div class="f-bars${v ? " v" : ""}${f.items.length <= 4 ? " few" : ""}">${items}</div>`;
};

T.tiles = (f, cur, W, H) => `<div class="f-tiles${VERT() ? " v" : ""}"><div class="f-thead f-u">${ic({ icon: f.icon, size: 48, label: f.family }, false, 72)}<div><div class="f-name">${esc(f.family)}</div><div class="f-mono ink">${esc(f.summary)}</div></div></div>
  <div class="f-tgrid">${f.tiles.map(t => `<div class="f-tile f-u${t.lit ? " lit" : ""}"><div class="f-tl">${esc(t.label)}</div><div class="f-mono">${f.lits === false ? "" : (t.lit ? "a technique points here" : "none") + " · "}${t.n} games${t.year ? " · first " + t.year : ""}</div></div>`).join("")}</div></div>`;

T.roles = (f, cur, W, H) => {
  const max = Math.max(...f.hist.core, ...f.hist.supporting), hh = VERT() ? 380 : 420;
  const hist = (k, title) => `<div class="f-hist f-u"><div class="f-lab">${title}</div><div class="f-mono">${f.uses[k]} uses · median ${f.med[k]} games</div><div class="f-hbars" style="height:${hh}px">${f.hist[k].map((c, i) => `<div class="f-hcol"><div class="f-mono ink">${cnt(c)}</div><div class="f-hbar${k === "core" ? " on" : ""}" style="height:${(hh * 0.8 * c / max).toFixed(0)}px"></div><div class="f-mono">${f.bins[i]}</div></div>`).join("")}</div><div class="f-mono faint">games using the mechanic</div></div>`;
  return `<div class="f-roles${VERT() ? " v" : ""}">${hist("core", "Core parts")}${hist("supporting", "Supporting parts")}</div>`;
};

T.timeline = (f, cur, W, H) => {
  const v = VERT();
  const groups = [];
  [...f.items].sort((a, b) => a.year - b.year).forEach(e => { const g = groups.find(g => g.year === e.year); g ? g.items.push(e) : groups.push({ year: e.year, items: [e] }); });
  const firsts = g => [...new Set(g.items.map(e => e.first).filter(Boolean))].join(", ");
  if (v) {   // 9:16: a vertical axis, oldest at the top
    const d = f.items.length <= 5 ? 72 : 48;
    const rows = groups.map(g => {
      const on = g.items.some(e => isOn(cur, e.id));
      return `<div class="f-vtrow f-u"><div class="f-vty${on ? " acc" : ""}">${g.year}</div><div class="f-vtdot${on ? " on" : ""}"></div><div class="f-vtitems">${g.items.map(e => `<div class="f-vti">${ic(e, isOn(cur, e.id), d)}<div class="f-lab${isOn(cur, e.id) ? " acc" : ""}">${esc(e.label)}</div></div>`).join("")}${firsts(g) ? `<div class="f-mono">${esc(firsts(g))}</div>` : ""}</div></div>`;
    }).join("");
    return `<div class="f-vtimeline"><div class="f-vtaxis"></div>${rows}<div class="f-mono faint f-tcap2">${esc(f.cap || "first catalog game to use each part")}</div></div>`;
  }
  const x = y => 120 + (W - 240) * (y - f.lo) / (f.hi - f.lo);
  const d = f.items.length <= 5 && groups.length >= f.items.length - 1 ? 72 : 48, iw = d === 72 ? 240 : 200;
  let ticks = "";
  for (let y = f.lo; y <= f.hi; y += f.step || 10) ticks += `<div class="f-ttick" style="left:${x(y)}px"><span class="f-mono">${y}</span></div>`;
  const ends = [], laneH = Math.min(d === 72 ? 330 : 260, (H - 170) / 2);
  const html = groups.map(g => {
    const w = g.items.length * iw, left = Math.min(Math.max(x(g.year) - w / 2, 0), W - w);
    let lane = 0; while (ends[lane] !== undefined && left < ends[lane] + 20) lane++;
    ends[lane] = left + w;
    const on = g.items.some(e => isOn(cur, e.id));
    return `<div class="f-tgroup f-u" style="left:${left}px;width:${w}px;bottom:${150 + lane * laneH}px;z-index:${10 - lane}"><div class="f-tgi">${g.items.map(e => `<div class="f-titem" style="width:${iw}px">${ic(e, isOn(cur, e.id), d)}<div class="f-lab sm${isOn(cur, e.id) ? " acc" : ""}">${esc(e.label)}</div></div>`).join("")}</div>
      <div class="f-mono${on ? " acc" : " ink"}">${g.year}${firsts(g) ? " · " + esc(firsts(g)) : ""}</div><div class="f-tpin${on ? " on" : ""}" style="left:${x(g.year) - left}px;height:${lane * laneH + 40}px"></div></div>`;
  }).join("");
  return `<div class="f-timeline" style="width:${W}px;height:${H}px"><div class="f-axis" style="left:120px;width:${W - 240}px"></div>${ticks}${html}<div class="f-mono faint f-tcap">${esc(f.cap || "first catalog game to use each part")}</div></div>`;
};

T.formula = (f, cur, W, H) => {
  const v = VERT(), n = f.terms.length + 1 + (f.terms.some(x => x.open) ? 1 : 0), d = v ? (n <= 3 ? 72 : 48) : (n <= 4 ? 96 : n <= 5 ? 72 : 48), lh = `style="line-height:${d * PX()}px"`;
  const term = (x) => x.const ? `<div class="f-fterm f-u"><div class="f-const" ${lh}>${esc(x.const)}</div>${x.unit ? `<div class="f-lab">${esc(x.unit)}</div>` : ""}</div>`
    : `<div class="f-fterm f-u">${ic(x, isOn(cur, x.id), d)}<div class="f-lab${isOn(cur, x.id) ? " acc" : ""}">${esc(x.label)}${x.pow != null ? `<sup class="f-pow">${x.pow}</sup>` : ""}</div></div>`;
  const op = (t) => `<div class="f-op" ${lh}>${esc(t)}</div>`;
  const parts = f.terms.map((x, k) => `${k || x.op.replace(/[()]/g, "") ? op(x.op.replace(/[()]/g, "") || "+") : ""}${x.open ? `<div class="f-paren" ${lh}>(</div>` : ""}${term(x)}${x.close ? `<div class="f-paren" ${lh}>)</div>` : ""}`).join("");
  return `<div class="f-formula${v ? " v" : ""}"><div class="f-frow">${term(f.result)}${op("=")}${parts}</div>${f.note ? `<div class="f-mono f-cnote f-u">record: ${esc(f.note)}</div>` : ""}</div>`;
};

T.scale = (f, cur, W, H) => {
  const v = VERT();
  return `<div class="f-scale${v ? " v" : ""}"><div class="f-thead f-u">${ic(f.mech, true, 72)}<div><div class="f-name">${esc(f.mech.label)}</div><div class="f-mono ink">${esc(f.field)}: ${f.value} of ${f.levels.length}</div><div class="f-mono">${esc(f.question)}</div></div></div>
  <div class="f-ruler"><div class="f-rail"></div>${f.levels.map(l => `<div class="f-level f-u${l.n === f.value ? " on" : ""}"><div class="f-ln">${l.n}</div><div class="f-lt">${esc(l.text)}</div></div>`).join("")}</div></div>`;
};

T.record = (f, cur, W, H) => `<div class="f-record${VERT() ? " v" : ""}"><div class="f-thead f-u">${ic(f.mech, true, 72)}<div><div class="f-mono">${esc(f.kicker || "mechanic · " + f.family)}</div><div class="f-name">${esc(f.mech.label)}</div></div></div>
  <div class="f-rrows${f.cols ? " cols" : ""}">${f.rows.slice(0, VERT() ? 6 : 9).map(([k, vals]) => `<div class="f-rrow f-u"><div class="f-mono f-rk">${esc(k)}</div><div class="f-rv">${vals.slice(0, 3).map(x => `<div>${esc(x)}</div>`).join("")}</div></div>`).join("")}</div>
  ${f.stamps.length ? `<div class="f-stamps">${f.stamps.map(s => `<div class="f-stamp f-u">${esc(s.toLowerCase())}</div>`).join("")}</div>` : ""}</div>`;

T.moment = (f, cur, W, H) => {
  const v = VERT(), n = f.panels.length, most = Math.max(...f.panels.map(p => p.icons.length));
  const d = v ? pick(most > 1 ? [72, 48, 42] : [96, 72, 48, 42], d => (most > 1 && d * PX() * most + 16 * (most - 1) > W * 0.55 ? false : true) && n * d * PX() + (n - 1) * 72 <= H - 50)
    : (most > 1 ? (n <= 3 ? 72 : 48) : (n <= 3 ? 120 : 96));
  return `<div class="f-moment${v ? " v" : ""}"><div class="f-mono faint f-mlabel">${esc(f.label)}</div><div class="f-panels">${f.panels.map((p, k) => `<div class="f-panel f-u"><div class="f-mono f-pk">${k + 1}</div><div class="f-pics">${p.icons.map(e => ic(e, isOn(cur, e.id), d)).join("")}</div><div class="f-pcap">${esc(p.caption)}</div></div>`).join('<div class="f-pnext">' + arrow(v ? 48 : 64, false, v) + "</div>")}</div></div>`;
};

T.toysim = (f, cur, W, H) => `<div class="f-toysim${VERT() ? " v" : ""}"><div class="f-thead f-u">${ic(f.mech, true, 72)}<div><div class="f-mono faint">${esc(f.label)}</div><div class="f-name">${esc(f.mech.label)}</div><div class="f-mono f-note3">record: ${esc(f.note)}</div></div></div>
  <div class="f-plates">${f.plates.map((p, j) => [p, j]).filter(([p, j]) => !(VERT() && f.plates.length * (f.h * PX() + 50) + 330 > H && j > 0 && j < f.plates.length - 1)).map(([p, j]) => `<div class="f-plate f-u"><img class="f-ic" src="${p}@${PX()}x.png" width="${f.w * PX()}" height="${f.h * PX()}" alt=""><div class="f-mono">${esc(f.caps[j] || "")}</div></div>`).join("")}</div></div>`;

// two games: their families, the parts they share, or the core parts each has alone
T.games = (f, cur, W, H) => {
  const v = VERT();
  const side = (g) => `<div class="f-gside f-u">${ic(g.emblem || { label: g.name }, false, v ? (f.show === "family" ? 72 : 48) : [96, 72, 48][f.fit || 0])}<div class="f-gname">${esc(g.name)}</div><div class="f-mono">${esc(g.meta)}</div><div class="f-mono ink f-gfam">family: ${esc(g.family.toLowerCase())}</div></div>`;
  const plist = (ps, max) => ps.slice(0, max).map(p => `<div class="f-pt f-u">${ic(p, isOn(cur, p.id), 42)}<div><div class="f-lab sm${isOn(cur, p.id) ? " acc" : ""}">${esc(p.label)}</div><div class="f-mono">${games(p.n, f.N)}</div></div></div>`).join("") + (ps.length > max ? `<div class="f-mono">and ${ps.length - max} more</div>` : "") + (ps.length ? "" : `<div class="f-mono">none</div>`);
  const rel = `<div class="f-grel${f.same ? " same" : ""}">${f.same ? "same family" : "different families"}</div>`;
  if (f.show === "shared") {
    const max = v ? 4 : 6;
    return `<div class="f-games sh${v ? " v" : ""}"><div class="f-gtop">${side(f.a)}<div class="f-gmid">${rel}<div class="f-mono ink">${f.nshared} parts in both</div></div>${side(f.b)}</div><div class="f-glist">${plist(f.shared, max)}</div></div>`;
  }
  if (f.show === "own") {
    const max = v ? 2 : 4;
    return `<div class="f-games own${v ? " v" : ""}"><div class="f-gcol">${side(f.a)}<div class="f-mono ink f-ghead">core parts ${esc(f.b.name)} lacks</div><div class="f-olist">${plist(f.a.own, max)}</div></div><div class="f-vrule"></div><div class="f-gcol">${side(f.b)}<div class="f-mono ink f-ghead">core parts ${esc(f.a.name)} lacks</div><div class="f-olist">${plist(f.b.own, max)}</div></div></div>`;
  }
  return `<div class="f-games fam${v ? " v" : ""}">${side(f.a)}${rel}${side(f.b)}</div>`;
};

T.venn = (f, cur, W, H) => {
  const v = VERT(), max = Math.max(f.a.n, f.b.n);
  const R = n => Math.round(Math.min(v ? 300 : 300, (H - (v ? 720 : 150)) / 2) * Math.sqrt(n / max));
  const ra = R(f.a.n), rb = R(f.b.n), ov = f.nboth ? Math.min(ra, rb) * 0.45 : -40;
  const circ = (e, r, on) => `<div class="f-vc${on ? " on" : ""}" style="width:${2 * r}px;height:${2 * r}px"></div>`;
  const lab = (e) => { const on = isOn(cur, e.id); return `<div class="f-vlab f-u">${ic(e, on, v ? 48 : 72)}<div class="f-lab${on ? " acc" : ""}">${esc(e.label)}</div><div class="f-num${on ? " acc" : ""}">${cnt(e.n)}<small> of ${f.N} games</small></div></div>`; };
  return `<div class="f-venn${v ? " v" : ""}"><div class="f-vrow">${lab(f.a)}<div class="f-vpair" style="--ov:${ov}px">${circ(f.a, ra, isOn(cur, f.a.id))}${circ(f.b, rb, isOn(cur, f.b.id))}</div>${lab(f.b)}</div>
  <div class="f-vboth f-u"><span class="f-num">${cnt(f.nboth)}</span><span class="f-lab">${f.nboth === 1 ? "game has both" : "games have both"}${f.both.length ? ": " + f.both.slice(0, 3).map(esc).join(", ") : ""}</span></div></div>`;
};

T.set = (f, cur, W, H) => {
  const v = VERT(), n = Math.max(...f.rows.map(r => r.length)), tot = f.rows.reduce((a, r) => a + r.length, 0);
  const d0 = v ? (tot <= 3 ? 72 : tot <= 6 ? 48 : 42) : (n <= 3 && f.rows.length === 1 ? 96 : n <= 4 && f.rows.length <= 2 ? 72 : 48);
  const d = f.fit ? [96, 72, 48, 42][Math.min(3, [96, 72, 48, 42].indexOf(d0) + f.fit)] : d0;   // f.fit: render.html found it taller than the stage
  const item = e => { const on = isOn(cur, e.id); return `<div class="f-si f-u">${ic(e, on, d)}<div><div class="f-lab${on ? " acc" : ""}">${esc(e.label)}</div>${f.dates && e.year ? `<div class="f-mono${on ? " acc" : ""}">${e.year}${e.first ? " · " + esc(e.first) : ""}</div>` : ""}</div></div>`; };
  return `<div class="f-set${v ? " v" : ""}${f.rows.length > 1 ? " grp" : ""}${v && tot > 5 ? " two" : ""}${f.fit ? " tight" : ""}">${f.rows.map((r, k) => `<div class="f-srow">${f.groups[k] ? `<div class="f-mono ink f-sg">${esc(f.groups[k])}</div>` : ""}<div class="f-sitems">${r.map(item).join("")}</div></div>`).join("")}</div>`;
};

T.units = (f, cur, W, H) => {
  const v = VERT(), cols = v ? 5 : Math.min(f.total, Math.ceil(Math.sqrt(f.total * 3))), d = v ? 42 : (f.total > 12 ? 42 : 48);
  const cells = Array.from({ length: f.total }, (_, k) => `<div class="f-unit f-u${k < (f.also || 0) ? " also" : ""}">${ic(f.unit, k < f.on, d)}</div>`).join("");
  return `<div class="f-units${v ? " v" : ""}"><div class="f-ugrid" style="grid-template-columns:repeat(${cols},auto)">${cells}</div>
  <div class="f-ukey"><div class="f-num acc">${cnt(f.on)}<small> of ${f.total}${f.labels[0] ? " " + esc(f.labels[0]) : ""}</small></div>${f.also != null ? `<div class="f-num">${cnt(f.also)}<small>${f.labels[1] ? " " + esc(f.labels[1]) : ""}</small></div>` : ""}</div></div>`;
};

T.figures = (f, cur, W, H) => {
  const v = VERT(), num = x => parseFloat(String(x).replace(/[^0-9.]/g, ""));
  const max = Math.max(100, ...f.rows.flatMap(r => r.vals.map(num)));
  return `<div class="f-figs${v ? " v" : ""}">${f.rows.map(r => `<div class="f-figrow f-u"><div class="f-lab">${esc(r.label)}</div><div class="f-figbars">${r.vals.map((x, k) => `<div class="f-figbar"><div class="f-mono">${esc(f.cols[k] || "")}</div><div class="f-fb${k === r.vals.length - 1 ? " on" : ""}"><i data-w="${(100 * num(x) / max).toFixed(1)}" style="width:${(100 * num(x) / max).toFixed(1)}%"></i></div><div class="f-num sm${k === r.vals.length - 1 ? " acc" : ""}">${esc(x)}</div></div>`).join("")}</div></div>`).join("")}</div>`;
};

T.tally = (f, cur, W, H) => {
  const v = VERT(), max = Math.max(...f.items.map(x => x.n), 1), many = f.items.length > 6;
  const items = (f.ordered ? [...f.items].sort((a, b) => b.n - a.n) : f.items);
  const nm = f.items.some(x => x.names && x.names.length);
  const d = many ? 0 : pick((nm ? [48, 42] : (v ? [72, 48, 42] : [72, 48, 42])).concat([0]), d => f.items.length * (Math.max(d * PX(), nm ? 90 : 50) + 18) + 50 <= H);
  return `<div class="f-tally${v ? " v" : ""}${many ? " many" : ""}"><div class="f-mono ink f-tof">${f.N} ${esc(f.of)}</div>${items.map(x => { const on = isOn(cur, x.id);
    return `<div class="f-trow f-u">${d ? ic(x, on, d) : ""}<div class="f-tlab"><div class="f-lab${on ? " acc" : ""}">${esc(x.label)}</div>${x.names && x.names.length ? `<div class="f-mono f-tnames">${x.names.slice(0, v ? 2 : 3).map(esc).join(" · ")}${x.names.length > (v ? 2 : 3) ? ` · and ${x.names.length - (v ? 2 : 3)} more` : ""}</div>` : ""}</div><div class="f-tbar${on ? " on" : ""}"><i data-w="${(100 * x.n / max).toFixed(1)}" style="width:${(100 * x.n / max).toFixed(1)}%"></i></div><div class="f-num sm${on ? " acc" : ""}">${cnt(x.n)}</div></div>`; }).join("")}</div>`;
};

T.piles = (f, cur, W, H) => {
  const v = VERT();
  const pile = (p) => `<div class="f-pile"><div class="f-ctitle f-u">${esc(p.title)}</div><div class="f-mono ink">${p.items.length} techniques</div><div class="f-pcards">${p.items.map(e => { const on = isOn(cur, e.id); return `<div class="f-pcard f-u${on ? " on" : ""}">${v || f.fit > 1 ? "" : ic(e, on, 42)}<div><div class="f-lab sm${on ? " acc" : ""}">${esc(e.label)}</div><div class="f-mono">${esc(e.mat)}</div></div></div>`; }).join("")}</div></div>`;
  return `<div class="f-piles${v ? " v" : ""}${f.fit ? " tight" : ""}${f.fit > 1 ? " three" : ""}">${pile(f.a)}<div class="f-vrule"></div>${pile(f.b)}</div>`;
};

T.spread = (f, cur, W, H) => {
  const v = VERT(), y0 = Math.min(...f.years), y1 = Math.max(new Date().getFullYear(), ...f.years) + 1;
  const pw = v ? W - 40 : W - 300, ph = v ? 520 : 420, x = y => 40 + pw * (y - y0) / (y1 - y0), y = n => ph - (ph - 30) * n / f.n;
  let path = `M${x(y0)},${y(0)}`, k = 0;
  f.years.forEach(yy => { k++; path += ` H${x(yy).toFixed(1)} V${y(k).toFixed(1)}`; });
  path += ` H${x(y1).toFixed(1)}`;
  const fifth = f.fifth ? `<line x1="${x(f.fifth)}" y1="${y(5)}" x2="${x(f.fifth)}" y2="${ph}" stroke="#0550ae" stroke-width="3" stroke-dasharray="6 6"/><circle cx="${x(f.fifth)}" cy="${y(5)}" r="9" fill="#0550ae"/>` : "";
  const ticks = []; for (let yy = Math.ceil(y0 / 5) * 5; yy < y1; yy += 5) ticks.push(`<text x="${x(yy)}" y="${ph + 34}" text-anchor="middle">${yy}</text>`);
  return `<div class="f-spread${v ? " v" : ""}"><div class="f-thead f-u">${ic(f.mech, true, 72)}<div><div class="f-name">${esc(f.mech.label)}</div><div class="f-mono ink">catalog games using it, by release year</div></div></div>
  <div class="f-u"><svg width="${pw + 120}" height="${ph + 50}" class="f-ssvg"><line x1="40" y1="${ph}" x2="${pw + 40}" y2="${ph}" stroke="#171717" stroke-width="2"/><path class="f-draw" d="${path}" fill="none" stroke="#171717" stroke-width="5"/>${fifth}${ticks.join("")}
  ${f.fifth ? `<text class="acc" x="${x(f.fifth) + 16}" y="${y(5) - 14}">5th game: ${f.fifth}</text>` : ""}<text x="${x(y1) - 10}" y="${y(f.n) - 16}" text-anchor="end" class="big">${f.n} games today</text></svg></div></div>`;
};

T.stat = (f, cur, W, H) => `<div class="f-stat f-u"><div class="f-sval">${esc(f.value)}</div><div class="f-slab">${esc(f.label)}</div></div>`;

T.ranked = (f, cur, W, H) => `<div class="f-ranked${VERT() ? " v" : ""}"><div class="f-rnkh f-mono"><span>rank</span><span>bet</span><span>priority</span><span>outcome</span></div>${f.rows.map(r => { const on = isOn(cur, r.id);
  return `<div class="f-rnk f-u${on ? " on" : ""}"><span class="f-rnkn">${r.rank}</span><span class="f-lab${on ? " acc" : ""}">${esc(r.name)}<div class="f-mono">${esc(r.horizon)}</div></span><span class="f-mono ink">${r.priority}</span><span class="f-rnko">${esc(r.outcome)}</span></div>`; }).join("")}<div class="f-mono faint">of ${f.N} bets</div></div>`;

T.packages = (f, cur, W, H) => `<div class="f-packs${VERT() ? " v" : ""}">${f.rows.map(r => `<div class="f-pack f-u"><div class="f-pkitems">${r.items.map(e => `<div class="f-pki">${ic(e, isOn(cur, e.id), VERT() ? 42 : 48)}<div class="f-lab sm${isOn(cur, e.id) ? " acc" : ""}">${esc(e.label)}</div></div>`).join('<div class="f-plus">+</div>')}</div><div class="f-mono ink">together in ${cnt(r.n)} ${r.n === 1 ? "game" : "games"}</div></div>`).join("")}</div>`;

T.gap = (f, cur, W, H) => {
  const v = VERT(), lw = v ? 0 : 480, pw = W - lw - (v ? 20 : 60), x = y => pw * (y - f.lo) / (f.hi - f.lo);
  const ticks = []; for (let y = f.lo; y <= f.hi; y += 10) ticks.push(`<div class="f-gtick" style="left:${x(y)}px"><span class="f-mono">${y}</span></div>`);
  return `<div class="f-gap${v ? " v" : ""}">${f.rows.map(r => { const on = isOn(cur, r.id);
    return `<div class="f-grow f-u"><div class="f-glab" style="${v ? "" : `width:${lw}px`}">${ic(r, on, 48)}<div class="f-lab${on ? " acc" : ""}">${esc(r.label)}</div></div><div class="f-gline" style="height:${v ? 120 : 110}px">
      <div class="f-gbar${on ? " on" : ""}" style="left:${x(r.y1)}px;width:${Math.max(4, x(r.y2 || r.y1) - x(r.y1))}px"></div>
      <div class="f-gend" style="left:${x(r.y1)}px"><b>${r.y1}</b> ${esc(r.g1)}</div>${r.y2 ? `<div class="f-gend r" style="left:${x(r.y2)}px"><b>${r.y2}</b> ${esc(r.g2)}</div><div class="f-gyrs${on ? " acc" : ""}" style="left:${x(r.y1)}px">${r.y2 - r.y1} years</div>` : ""}</div></div>`; }).join("")}
    <div class="f-gaxis" style="margin-left:${lw}px">${ticks.join("")}</div><div class="f-mono faint">first and second catalog game to use each part</div></div>`;
};

T.due = (f, cur, W, H) => {
  const v = VERT(), [dd, mm, yy] = f.date.split(" ");
  return `<div class="f-due${v ? " v" : ""}"><div class="f-cal f-u"><div class="f-calm">${esc(mm)} ${esc(yy)}</div><div class="f-cald">${esc(dd)}</div></div>
  <div class="f-dcards"><div class="f-mono ink">${cnt(f.n)} predictions due</div>${f.cards.map(c => { const on = isOn(cur, c.id);
    return `<div class="f-dcard f-u${on ? " on" : ""}"><span class="f-mono">#${c.rank}</span> <span class="f-lab sm${on ? " acc" : ""}">${esc(c.name)}</span>${on ? `<div class="f-dpred">${esc(c.pred)}</div>` : ""}</div>`; }).join("")}</div></div>`;
};

T.dueyears = (f, cur, W, H) => {
  const v = VERT(), max = Math.max(...f.rows.map(r => r.n));
  return `<div class="f-dy${v ? " v" : ""}">${f.rows.map(r => `<div class="f-dyc f-u"><div class="f-mono ink">${cnt(r.n)} due</div><div class="f-dyb" style="height:${(v ? 520 : 380) * r.n / max}px"></div><div class="f-dyy">${r.year}</div><div class="f-mono">${r.cum} of ${f.N} by the end of ${r.year}</div></div>`).join("")}<div class="f-mono faint f-dylast">last: ${esc(f.last)}</div></div>`;
};

T.techyears = (f, cur, W, H) => {
  const v = VERT(), sq = v ? 30 : 34;
  const cols = f.years.map(y => `<div class="f-tyc f-u"><div class="f-tys">${f.by[y].map(t => `<i class="${isOn(cur, t.cat) ? "on" : ""}" style="width:${sq}px;height:${sq}px" title=""></i>`).join("")}</div><div class="f-mono">${y}</div></div>`).join("");
  const onCat = (cur || []).find(c => f.cats[c]);
  return `<div class="f-ty${v ? " v" : ""}"><div class="f-tycols">${cols}</div><div class="f-mono ink">${cnt(f.recent)} of ${f.N} techniques dated 2023 or later${onCat ? ` · <span class="acc">blue: ${esc(f.cats[onCat].toLowerCase())}</span>` : ""}</div></div>`;
};

T.rulers = (f, cur, W, H) => {
  const v = VERT(), rw = v ? W - 60 : W - 200, nr = f.rulers.length;
  const th = Math.max(150, Math.min(v ? 300 : 200, (H - nr * 150) / nr));
  const x = (val, n) => 30 + rw * (val - 1) / (n - 1);
  return `<div class="f-rulers${v ? " v" : ""}">${f.rulers.map(r => `<div class="f-rl f-u"><div class="f-lab">${esc(r.field)}</div><div class="f-mono">${esc(r.question)}</div>
    <div class="f-rtrack" style="width:${rw + 60}px;height:${th}px">${Array.from({ length: r.n }, (_, k) => `<div class="f-rt" style="left:${x(k + 1, r.n)}px"><span>${k + 1}</span></div>`).join("")}
    ${(() => { const at = {}; return r.marks.map(m => { const on = isOn(cur, m.id), o = (at[m.v] = (at[m.v] || 0) + 1) - 1;
      return `<div class="f-rm${on ? " on" : ""}" style="left:${x(m.v, r.n)}px;top:${-o * (PX() * 42 + 54)}px">${ic(m, on, 42)}<div class="f-mono${on ? " acc" : ""}">${esc(m.label)}</div></div>`; }).join(""); })()}</div>
    <div class="f-rends f-mono" style="width:${rw + 60}px"><span>1: ${esc(r.lo)}</span><span>${r.n}: ${esc(r.hi)}</span></div></div>`).join("")}</div>`;
};

T.cards = (f, cur, W, H) => `<div class="f-bcards${VERT() ? " v" : f.cards.length === 3 ? " three" : ""}">${f.cards.map(c => { const on = isOn(cur, c.id);
  return `<div class="f-bcard f-u${on ? " on" : ""}"><div class="f-lab">${esc(c.name)}</div><div class="f-bp">${esc(c.pred)}</div>${VERT() ? "" : c.crit.map(x => `<div class="f-mono">${esc(x)}</div>`).join("")}<div class="f-mono ink">resolves ${esc(c.due)}</div></div>`; }).join("")}</div>`;

T.source = (f, cur, W, H) => `<div class="f-src${VERT() ? " v" : ""}"><div class="f-mono faint">${esc(f.file)}</div><div class="f-srcl f-u">${f.parts.map(p => p.tok ? `<span class="f-tok">${esc(p.text)}</span>` : esc(p.text)).join("")}</div><div class="f-mono ink">blue: tokens the build fills in and checks</div></div>`;

T.card = (f, cur, W, H) => `<div class="f-card2${VERT() ? " v" : ""}">${f.title ? `<div class="f-ctitle f-u">${esc(f.title)}</div>` : ""}<div class="f-clines">${f.lines.map((l, k) => `<div class="f-cl f-u">${f.numbered ? `<span class="f-cln">${k + 1}</span>` : ""}<span>${esc(l)}</span></div>`).join("")}</div></div>`;

T.mockup = (f, cur, W, H) => {
  const v = VERT();
  const items = f.items.length ? `<div class="f-mitems">${f.items.map(e => { const on = isOn(cur, e.id); return `<div class="f-mi">${ic(e, on, v ? 48 : 72)}<div class="f-lab sm${on ? " acc" : ""}">${esc(e.label)}</div></div>`; }).join("")}</div>` : "";
  let chart = "";
  if (f.chart === "fan") {   // a fan of futures: deterministic curves from one present
    const w = v ? W - 120 : 900, h = v ? 300 : 260; let ls = "";
    for (let k = 0; k < 24; k++) { const s = (k - 11.5) / 11.5; let d = `M10,${h / 2}`; for (let x = 1; x <= 12; x++) d += ` L${10 + (w - 20) * x / 12},${(h / 2 - s * h * 0.42 * Math.pow(x / 12, 1.3) + Math.sin(k * 1.7 + x) * 4).toFixed(1)}`; ls += `<path d="${d}" fill="none" stroke="${k === 3 || k === 20 ? "#0550ae" : "#8c8c86"}" stroke-width="${k === 3 || k === 20 ? 4 : 2}"/>`; }
    chart = `<svg class="f-mchart" width="${w}" height="${h}"><line x1="10" y1="${h / 2}" x2="10" y2="${h / 2}" stroke="#171717"/>${ls}<circle cx="10" cy="${h / 2}" r="7" fill="#171717"/></svg>`;
  }
  if (f.chart === "timer") chart = `<div class="f-mtimer">${esc(f.lines[0] || "")}</div>`;
  const lines = (f.chart === "timer" ? f.lines.slice(1) : f.lines);
  const body = f.kind === "terminal"
    ? `<div class="f-term">${lines.map(l => `<div class="${/^(E[0-9]{3}|FAIL|error)/.test(l) ? "err" : /^\+/.test(l) ? "add" : /^\$/.test(l) ? "cmd" : ""}">${esc(l)}</div>`).join("")}</div>`
    : f.kind === "doc" ? `<div class="f-doc">${lines.map(l => `<div>${esc(l).replace(/“([^”]+)”|"([^"]+)"/g, (m, a, b) => `<span class="f-circ">${a || b}</span>`)}</div>`).join("")}</div>`
    : f.kind === "standin" ? `<div class="f-stand"><div class="f-standpic">${f.subject ? `<div class="f-standsub">${esc(f.subject)}</div>` : ""}${chart}</div>${lines.map(l => `<div class="f-mline">${esc(l)}</div>`).join("")}</div>`
    : `${items}${chart}<div class="f-mlines">${lines.map((l, k) => `<div class="f-mline${k === 0 && lines.length > 1 ? " head" : ""}">${esc(l)}</div>`).join("")}</div>${f.button ? `<div class="f-mbtn">${esc(f.button)}</div>` : ""}`;
  return `<div class="f-mock${v ? " v" : ""} k-${f.kind}"><div class="f-mtag f-mono">${esc(f.label)}</div><div class="f-win f-u"><div class="f-wbar"><i></i><i></i><i></i><span>${esc(f.title)}</span></div><div class="f-wbody">${body}</div></div></div>`;
};

// the catalog in four numbers: games, mechanics, techniques, predictions; the one the narration has reached is in the accent
T.totals = (f, cur, W, H) => `<div class="f-totals${VERT() ? " v" : ""}">${f.cells.map(c => { const on = isOn(cur, c.id);
  return `<div class="f-tot f-u${on ? " on" : ""}"><div class="f-totn${on ? " acc" : ""}">${cnt(c.n)}</div><div class="f-totl">${esc(c.label)}</div><div class="f-mono">${esc(c.sub)}</div></div>`; }).join("")}</div>`;

// every catalog game as one square on its release year, stacked; the named games are pinned with their names
T.gameyears = (f, cur, W, H) => {
  const v = VERT(), span = f.hi - f.lo + 1, by = {};
  f.games.forEach(g => (by[g.year] = by[g.year] || []).push(g));
  const most = Math.max(...Object.values(by).map(a => a.length));
  const named = new Map(f.named.map(x => [x.id, x]));
  const lab = x => { const on = isOn(cur, x.id); return `<div class="f-gyl f-u${on ? " on" : ""}"><span class="f-lab sm${on ? " acc" : ""}">${esc(x.label)}</span><span class="f-mono${on ? " acc" : ""}">${x.year}</span></div>`; };
  const LH = v ? 40 : 34;   // one label line: the name, then the year
  const ticks = []; for (let y = Math.ceil(f.lo / 10) * 10; y <= f.hi; y += 10) ticks.push(y);
  if (v) {   // 9:16: years run down the page, the stacks grow right, the names sit right of the stacks
    const top = 40, bot = 90, step = (H - top - bot) / span, sq = Math.max(6, Math.min(step - 3, 22)), axisX = 110;
    const yOf = y => top + (y - f.lo) * step;
    let sqs = "", pins = "", labs = "", ty = -1e9;
    for (const [y, gs] of Object.entries(by)) gs.forEach((g, k) => {
      const on = g.on && isOn(cur, g.g);
      sqs += `<div class="f-gys f-u${g.on ? " named" : ""}${on ? " on" : ""}" style="left:${axisX + 12 + k * (sq + 3)}px;top:${yOf(+y)}px;width:${sq}px;height:${sq}px"></div>`;
    });
    const lx = axisX + 12 + most * (sq + 3) + 70;
    f.named.forEach(x => {
      const k = by[x.year].findIndex(g => g.g === x.id), sy = yOf(x.year) + sq / 2, ly = Math.max(sy - LH / 2, ty + LH + 10); ty = ly;
      const sx = axisX + 12 + k * (sq + 3) + sq;
      pins += `<line class="f-draw" x1="${sx + 4}" y1="${sy}" x2="${lx - 10}" y2="${ly + LH / 2}" stroke="${isOn(cur, x.id) ? "#0550ae" : "#a3a39a"}" stroke-width="2"/>`;
      labs += `<div class="f-gyw" style="left:${lx}px;top:${ly}px">${lab(x)}</div>`;
    });
    const tk = ticks.map(y => `<div class="f-mono f-gyt" style="left:0;top:${yOf(y) - 6}px;width:${axisX - 14}px;text-align:right">${y}</div>`).join("");
    return `<div class="f-gyears v" style="width:${W}px;height:${H}px"><div class="f-gyaxis" style="left:${axisX}px;top:${top}px;height:${H - top - bot}px"></div>${tk}${sqs}<svg width="${W}" height="${H}">${pins}</svg>${labs}
      <div class="f-mono ink f-gycap">${f.N} games, ${f.lo} to ${f.hi}, one square each</div></div>`;
  }
  const left = 60, right = 60, bot = 110, step = (W - left - right) / span, sq = Math.max(6, Math.min(step - 3, 24));
  const xOf = y => left + (y - f.lo) * step;
  const base = H - bot, stackH = most * (sq + 3);
  let sqs = "";
  for (const [y, gs] of Object.entries(by)) gs.forEach((g, k) => {
    const on = g.on && isOn(cur, g.g);
    sqs += `<div class="f-gys f-u${g.on ? " named" : ""}${on ? " on" : ""}" style="left:${xOf(+y)}px;top:${base - (k + 1) * (sq + 3)}px;width:${sq}px;height:${sq}px"></div>`;
  });
  // names in lanes above the stacks, each pinned to its square: a lane is free when no name in it overlaps this one, no
  // deeper name sits across this pin, and no shallower pin runs down through this name
  const laneH = LH + 22, lw = x => 76 + 13.2 * x.label.length, placed = [];
  let pins = "", labs = "";
  f.named.forEach(x => {
    const w = lw(x), cx = xOf(x.year) + sq / 2, lx = Math.min(Math.max(cx - 14, 0), W - w);
    let lane = 0;
    const free = L => placed.every(p => (p.lane !== L || lx >= p.r + 24 || lx + w + 24 <= p.l) && (p.lane <= L || cx < p.l - 8 || cx > p.r + 8) && (p.lane >= L || p.cx < lx - 8 || p.cx > lx + w + 8));
    while (!free(lane)) lane++;
    placed.push({ lane, l: lx, r: lx + w, cx, x, w });
  });
  const nl = Math.max(...placed.map(p => p.lane)) + 1, top0 = Math.max(10, base - stackH - 40 - nl * laneH);
  placed.forEach(({ lane, l: lx, cx, x }) => {
    const ly = top0 + lane * laneH, k = by[x.year].findIndex(g => g.g === x.id), sy = base - (k + 1) * (sq + 3);
    pins += `<line class="f-draw" x1="${cx}" y1="${ly + LH + 4}" x2="${cx}" y2="${sy - 4}" stroke="${isOn(cur, x.id) ? "#0550ae" : "#a3a39a"}" stroke-width="2"/>`;
    labs += `<div class="f-gyw" style="left:${lx}px;top:${ly}px">${lab(x)}</div>`;
  });
  const tk = ticks.map(y => `<div class="f-mono f-gyt" style="left:${xOf(y) - 40}px;top:${base + 16}px;width:${80 + sq}px;text-align:center">${y}</div>`).join("");
  return `<div class="f-gyears" style="width:${W}px;height:${H}px"><div class="f-gyaxis h" style="left:${left - 10}px;top:${base + 4}px;width:${W - left - right + 20}px"></div>${tk}${sqs}<svg width="${W}" height="${H}">${pins}</svg>${labs}
    <div class="f-mono ink f-gycap">${f.N} games, ${f.lo} to ${f.hi}, one square each</div></div>`;
};

// every icon the project has drawn, in one grid; the groups the narration names light up in the accent
T.iconmap = (f, cur, W, H) => {
  const v = VERT(), capH = v ? 120 : 64, n = f.icons.length;
  let best = null;
  for (let cols = 6; cols <= n; cols++) {
    const rows = Math.ceil(n / cols), cell = Math.min(W / cols, (H - capH) / rows);
    if (!best || cell > best.cell) best = { cols, rows, cell };
  }
  const d = Math.floor(best.cell * 0.84);
  const cells = f.icons.map(e => { const on = isOn(cur, e.group);
    const src = `${VISDIR}/icons/${e.ic}${on ? ".accent" : ""}@${PX()}x.png`;
    return `<div class="f-imc f-u" style="width:${best.cell}px;height:${best.cell}px"><img class="f-imi" src="${src}" width="${d}" height="${d}" alt=""></div>`; }).join("");
  return `<div class="f-iconmap${v ? " v" : ""}"><div class="f-imgrid" style="grid-template-columns:repeat(${best.cols},${best.cell}px)">${cells}</div>
    <div class="f-imcap"><span class="f-num sm">${cnt(f.N)}</span><span class="f-mono ink">icons · ${f.counts.map(esc).join(" · ")}</span></div></div>`;
};

// the project's own site, as this build renders it: render.js takes the screenshot (f.shot) before the frames are drawn
T.site = (f, cur, W, H) => {
  const bh = H - 48, w = Math.min(W, Math.round(bh * f.vw / f.vh));
  return `<div class="f-site"><div class="f-win f-u" style="width:${w}px"><div class="f-wbar"><i></i><i></i><i></i><span class="f-url">${esc(f.url)}</span></div><div class="f-wbody f-shot"><img src="${f.shot}" width="${w - 4}" height="${Math.round((w - 4) * f.vh / f.vw)}" alt=""></div></div></div>`;
};

function frameHTML(f, cur, W, H) { return (T[f.t] || (() => `<div class="f-mono">no template ${esc(f.t)}</div>`))(f, cur, W, H); }
