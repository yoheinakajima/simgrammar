// node render.js states.json outdir figdir grid.json [v]
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const [ , , statesFile, outDir, figDir, gridFile, vert] = process.argv;
  const states = JSON.parse(fs.readFileSync(statesFile, 'utf8'));
  fs.mkdirSync(outDir, { recursive: true });
  const b = await chromium.launch();
  const W = vert ? 1080 : 1920, H = vert ? 1920 : 1080;
  const p = await b.newPage({ viewport: { width: W, height: H } });
  await p.goto('file://' + path.resolve(__dirname, 'render.html'), { waitUntil: 'networkidle' });
  await p.evaluate(([v, dir, vis, sized]) => { if (v) document.body.classList.add('v'); FIGDIR = dir; VISDIR = vis; SIZEDIR = sized; },
    [!!vert, path.resolve(figDir), path.resolve(figDir, '..', '..', 'visual'), path.resolve(path.dirname(gridFile), 'visual', 'icons')]);
  await p.evaluate(() => document.fonts.ready);
  // the fonts are vendored (media/fonts); stop rather than render in a fallback face
  const faces = ['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"', '400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'];
  await p.evaluate(fs => Promise.all(fs.map(f => document.fonts.load(f))), faces);
  const missing = await p.evaluate(fs => fs.filter(f => !document.fonts.check(f) || ![...document.fonts].some(x => x.status === 'loaded' && f.includes(x.family.replace(/"/g, '')))), faces);
  if (missing.length) throw new Error('fonts not loaded: ' + missing.join(', '));
  // site frames (templates.js T.site): screenshot the project's own site as this build renders it (dist/web), served
  // under its real address with no network, at a desktop size for 16:9 and a phone size for 9:16
  const webDir = path.resolve(figDir, '..', '..', 'web'), shots = new Map();
  for (const s of states) {
    if (!s.frame || s.frame.t !== 'site') continue;
    const key = `${s.frame.page}|${s.frame.scroll}`;
    if (!shots.has(key)) {
      const [vw, vh, dpr] = vert ? [460, 900, 3] : [1120, 630, 2];
      const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: dpr });
      const host = 'https://' + s.frame.url.split('/')[0], missing = [];
      await ctx.route('**/*', async route => {
        const u = new URL(route.request().url());
        if (u.origin !== host) return route.abort();
        let rel = decodeURIComponent(u.pathname); if (rel.endsWith('/')) rel += 'index.html';
        const f = path.join(webDir, rel);
        if (!f.startsWith(webDir) || !fs.existsSync(f)) { missing.push(rel); return route.fulfill({ status: 404, body: '' }); }
        return route.fulfill({ path: f });
      });
      const sp = await ctx.newPage();
      await sp.goto(host + s.frame.page, { waitUntil: 'networkidle' });
      await sp.evaluate(() => document.fonts.ready);
      if (s.frame.scroll) { await sp.evaluate(y => window.scrollTo(0, y), s.frame.scroll); await sp.waitForTimeout(300); }
      // the pictures in view have loaded (a lazy one below the fold or inside a closed block never starts)
      await sp.waitForFunction(() => [...document.images].filter(im => { const r = im.getBoundingClientRect(); return r.height > 0 && r.top < innerHeight && r.bottom > 0; }).every(im => im.complete));
      if (missing.length) throw new Error(`site page ${s.frame.page}: not in the build: ${missing.slice(0, 4).join(', ')} (posters: python scripts/video/fetch_published.py dist/web --from video-out/publish)`);
      const f = path.join(outDir, `site-${shots.size}.png`);
      await sp.screenshot({ path: f });
      await ctx.close();
      shots.set(key, { shot: 'file://' + f, vw, vh });
    }
    Object.assign(s.frame, shots.get(key));
  }
  const grid = JSON.parse(fs.readFileSync(gridFile, 'utf8'));
  await p.evaluate(g => { GRID = g; NCOL = g.ncol; NGAME = g.rows.length; MAXN = g.maxn; }, grid);
  // Motion (ADR-0006): a new frame builds in, a changed frame or a moved highlight cross-dissolves. The steps are 1/30 s
  // stills taken out of the start of the state's own duration, so the cut points and the total length do not move.
  const STEP = 1 / 30, MOTION = !process.env.SIMGRAMMAR_NO_MOTION;   // SIMGRAMMAR_NO_MOTION=1: final stills only, for previews
  let prev = null, prevState = null, n = 0; const list = [];
  const shot = async (dur, exact = true) => {
    await p.waitForFunction(() => [...document.images].every(im => im.complete));
    const broken = await p.evaluate(() => [...document.images].filter(im => !im.naturalWidth).map(im => im.src));
    if (broken.length) throw new Error('missing images: ' + broken.slice(0, 3).join(', '));
    const f = path.join(outDir, `s${String(n).padStart(5, '0')}.png`);
    await p.screenshot({ path: f }); list.push({ f, dur, exact, state: merged_i }); n++;
  };
  const merged = []; let merged_i = 0;
  for (const s of states) {
    const sig = JSON.stringify({ ...s, dur: 0 });
    if (merged.length && sig === merged[merged.length - 1].sig) { merged[merged.length - 1].s.dur += s.dur; continue; }
    merged.push({ sig, s: { ...s } });
  }
  // A build that does not fit in its first state carries on into the next states that show the same frame (only the
  // caption, chip, or highlight changes), each taking its steps out of its own duration.
  let steps = 0, pend = null;
  for (const [mi, { s }] of merged.entries()) {
    merged_i = mi;
    let mode = null;
    const sig = s.frame ? JSON.stringify(s.frame) : null;
    if (s.frame) {
      const pf = prevState && prevState.frame;
      if (pend && pend.sig === sig) mode = 'continue';
      else if (!pf) mode = 'build';
      else if (JSON.stringify(pf) !== sig) mode = pf.t === s.frame.t ? 'xfade' : 'build';
      else if (JSON.stringify(prevState.current) !== JSON.stringify(s.current)) mode = 'xfade';
    }
    if (mode !== 'continue') pend = null;
    if (mode === 'xfade') await p.evaluate(() => keepOld());
    await p.evaluate(x => show(x), s);
    let K = 0, hold = false;
    if (MOTION && (mode === 'build' || mode === 'continue')) {
      await p.waitForFunction(() => [...document.images].every(im => im.complete));
      const total = await p.evaluate(() => transPrep('build', 1e9));
      const k0 = mode === 'continue' ? pend.k : 0;
      const n = Math.max(0, Math.min(total - k0, Math.floor(s.dur / STEP) - 1));
      for (let k = k0; k < k0 + n; k++) { await p.evaluate(k => transStep(k), k); await shot(STEP); }
      K = n;
      if (k0 + n < total) { pend = { sig, k: k0 + n }; hold = true; if (!n) await p.evaluate(k => transStep(k), Math.max(k0 - 1, -1)); }
      else pend = null;
    } else if (MOTION && mode === 'xfade') {
      const maxK = Math.floor((s.dur - 0.25) / STEP);
      if (maxK >= 3) {
        await p.waitForFunction(() => [...document.images].every(im => im.complete));
        K = await p.evaluate(([m, k]) => transPrep(m, k), [mode, maxK]);
        for (let k = 0; k < K; k++) { await p.evaluate(k => transStep(k), k); await shot(STEP); }
      }
    }
    if (!hold) await p.evaluate(() => transEnd());
    // the state's final still: its duration is exact when motion steps came out of it
    await shot(K ? s.dur - K * STEP : s.dur, !!K);
    list[list.length - 1].final = true;
    if (hold) await p.evaluate(() => { const o = document.getElementById("frame-old"); if (o) o.remove(); });
    steps += K; prevState = s;
  }
  let txt = ''; for (const x of list) txt += `file '${x.f}'\nduration ${(x.exact ? x.dur : Math.max(x.dur, 0.04)).toFixed(6)}\n`;
  fs.writeFileSync(path.join(outDir, 'stills.json'), JSON.stringify(list.map(x => ({ f: path.basename(x.f), dur: +x.dur.toFixed(6), state: x.state, final: !!x.final }))));
  txt += `file '${list[list.length - 1].f}'\n`;
  fs.writeFileSync(path.join(outDir, 'concat.txt'), txt);
  console.log('stills', n, 'motion steps', steps, 'seconds', list.reduce((a, x) => a + x.dur, 0).toFixed(1));
  await b.close();
})();
