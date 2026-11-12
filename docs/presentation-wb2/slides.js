/* Team 4 · Team Meeting 2 (Workbook 2) deck content.
   Each slide: arc (story section 0-5), num + kicker + title (on-slide headline), rubric tag,
   speaker, secs (target), html (slide body on a 1920x1080 canvas), say (spoken word for word;
   lines starting "CUE:" are stage directions, not spoken), qa ([question, answer] pairs).
   Every number here is from Workbook 2 (T4.A6), CONTEXT.md or the committed data files. */
(function () {
  /* ---------- icons (24px grid, stroked) ---------- */
  const P = {
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5"/><circle cx="17" cy="7" r="2.8"/><path d="M17 12.5c2.6 0 4.5 2.2 4.5 5"/>',
    bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 3.5V8M9 13h.01M15 13h.01M9.5 16.5h5"/>',
    download: '<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/>',
    filter: '<path d="M3 4h18l-7 9v6l-4 2v-8z"/>',
    shuffle: '<path d="M4 7h12l-3-3M20 17H8l3 3"/>',
    split: '<path d="M3 12h6M9 12l5-6h7M9 12l5 6h7"/>',
    chart: '<path d="M4 20V4M4 20h16M8.5 16v-5M13 16V8M17.5 16v-3"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    db: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 018 0V11"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    merge: '<circle cx="6" cy="5" r="2.2"/><circle cx="6" cy="19" r="2.2"/><circle cx="18" cy="12" r="2.2"/><path d="M6 7.2v9.6M6 8c0 3.5 4 4 9.8 4"/>',
    route: '<circle cx="5" cy="12" r="2.2"/><circle cx="19" cy="5" r="2.2"/><circle cx="19" cy="19" r="2.2"/><path d="M7.2 12H11l6-5.6M11 12l6 5.6"/>',
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15H17"/>',
    spark: '<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
    link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
    gauge: '<path d="M4 17a8 8 0 1116 0"/><path d="M12 17l4-5"/>',
    alert: '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4.5M12 17.5h.01"/>',
    play: '<path d="M8 5l11 7-11 7z"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    flag: '<path d="M5 21V4M5 4h12l-2.5 4L17 12H5"/>',
    doc: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>'
  };
  const I = (n, s = 28, w = 1.9) => `<svg class="ic" viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${P[n]}</svg>`;
  const arrow = (s = 34) => `<span class="arrow-r"><svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h15M13 6l6 6-6 6"/></svg></span>`;

  /* ---------- tiny JSON highlighter for code samples ---------- */
  const hl = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(
    /(\/\/.*$)|("(?:[^"\\]|\\.)*")(\s*:)?|\b(\d+(?:\.\d+)?)\b/gm,
    (m, com, str, colon, num) => com ? `<span class="c">${com}</span>`
      : str ? (colon ? `<span class="k">${str}</span>${colon}` : `<span class="s">${str}</span>`)
      : `<span class="n">${num}</span>`);
  const code = (t, style = "") => `<div class="code" style="${style}">${hl(t.trim())}</div>`;

  /* ---------- timeline (9 Sep to 8 Dec), reused on slides 1, 2 ---------- */
  const X = (pct) => 3 + pct * 0.94; // keep end labels inside the track
  function timeline(top, focus, inset = 120) {
    const nodes = [
      { p: 0, d: "9 Sep", w: "Semester starts", c: "past" },
      { p: 31.1, d: "7 Oct", w: "Workbook 1", c: "past" },
      { p: 71.1, d: "12 Nov", w: "Today · Workbook 2", c: "now" },
      { p: 100, d: "7–8 Dec", w: "Final report", c: "next" }
    ];
    const seg = focus === "since"
      ? `<div class="seg" style="left:${X(0)}%;width:${X(31.1) - X(0)}%;background:#9a9ca3"></div>
         <div class="seg" style="left:${X(31.1)}%;width:${X(71.1) - X(31.1)}%;background:var(--blue);height:10px;top:-2px"></div>`
      : `<div class="seg" style="left:${X(0)}%;width:${X(31.1) - X(0)}%;background:var(--ink);height:10px;top:-2px"></div>
         <div class="seg" style="left:${X(31.1)}%;width:${X(71.1) - X(31.1)}%;background:#9a9ca3"></div>`;
    const dash = `<div class="seg" style="left:${X(71.1)}%;width:${X(100) - X(71.1)}%;background:repeating-linear-gradient(90deg,var(--amber) 0 14px,transparent 14px 26px)"></div>`;
    return `<div class="tl" style="top:${top}px;left:${inset}px;right:${inset}px"><div class="track" style="left:${X(0)}%;right:${100 - X(100)}%"></div>${seg}${dash}
      ${nodes.map((n) => `<div class="node${n.c === "next" ? " dim" : ""}" style="left:${X(n.p)}%">
        <div class="pw"><div class="pin ${n.c}"></div></div><div class="date">${n.d}</div><div class="what">${n.w}</div></div>`).join("")}</div>`;
  }

  /* ---------- charts drawn from the committed data ---------- */
  // Reference-summary length, % of rows per 20-word bin (data/splits/m1_v1/*.jsonl)
  const HIST = {
    Train: [0.9, 14.4, 25.7, 25.9, 16.9, 8.7, 3.7, 2.5, 0.8, 0.2, 0.2, 0.1],
    Validation: [0.7, 11.0, 28.7, 27.6, 18.0, 8.5, 2.6, 2.2, 0.4, 0.4, 0, 0],
    Test: [1.4, 17.8, 31.3, 23.1, 13.2, 7.5, 3.2, 2.1, 0, 0.4, 0, 0]
  };
  function histSVG() {
    const x0 = 64, x1 = 470, y0 = 300, y1 = 24, bw = (x1 - x0) / 12, ys = (v) => y0 - (v / 35) * (y0 - y1);
    const col = { Train: "#15171d", Validation: "#2d4bf0", Test: "#e3962b" };
    const step = (a) => { let d = `M${x0},${y0}`; a.forEach((v, i) => { d += ` L${x0 + i * bw},${ys(v)} L${x0 + (i + 1) * bw},${ys(v)}`; }); return d + ` L${x1},${y0}`; };
    const grid = [0, 10, 20, 30].map((v) => `<line x1="${x0}" x2="${x1}" y1="${ys(v)}" y2="${ys(v)}" stroke="#ece9e2"/><text x="${x0 - 12}" y="${ys(v) + 6}" text-anchor="end">${v}%</text>`).join("");
    const xt = [0, 60, 120, 180, 240].map((w) => `<text x="${x0 + (w / 20) * bw}" y="${y0 + 30}" text-anchor="middle">${w}</text>`).join("");
    const mx = x0 + (65 / 20) * bw;
    return `<svg viewBox="0 0 500 360" width="440" height="317" font-family="Instrument Sans" font-size="17" fill="#767a85">
      ${grid}${xt}<text x="${(x0 + x1) / 2}" y="${y0 + 56}" text-anchor="middle" fill="#3a3e48" font-weight="600">reference summary length (words)</text>
      <path d="${step(HIST.Train)}" fill="rgba(21,23,29,0.07)" stroke="${col.Train}" stroke-width="2.5"/>
      <path d="${step(HIST.Validation)}" fill="none" stroke="${col.Validation}" stroke-width="2.5"/>
      <path d="${step(HIST.Test)}" fill="none" stroke="${col.Test}" stroke-width="2.5"/>
      <line x1="${mx}" x2="${mx}" y1="${y1}" y2="${y0}" stroke="#15171d" stroke-dasharray="5 5" stroke-width="1.6"/>
      <text x="${mx + 10}" y="${y1 + 14}" fill="#15171d" font-weight="700">median ≈ 65</text>
      ${Object.keys(col).map((k, i) => `<rect x="${300}" y="${88 + i * 28}" width="22" height="5" fill="${col[k]}"/><text x="330" y="${95 + i * 28}" fill="#3a3e48">${k}</text>`).join("")}
    </svg>`;
  }
  // MAST label prevalence on 1,638 scorable traces (data/mast/EDA_SUMMARY.json)
  const MODES = [["1.3", "Step repetition", 664], ["3.3", "No or wrong verification", 658], ["2.6", "Reasoning–action mismatch", 610],
    ["3.2", "Weak verification", 608], ["1.1", "Disobey task spec", 591], ["1.5", "Unaware of termination", 436],
    ["2.5", "Ignored other agent", 370], ["2.3", "Task derailment", 353], ["3.1", "Premature termination", 274],
    ["2.2", "Fail to ask for clarification", 265], ["1.4", "Loss of history", 117], ["1.2", "Disobey role spec", 91],
    ["2.1", "Conversation reset", 80], ["2.4", "Information withholding", 24]];
  function barsSVG() {
    const lx = 300, bx = 312, bmax = 250, rh = 27.5, top = 8;
    const rows = MODES.map(([c, n, v], i) => {
      const pct = (v / 1638) * 100, w = (pct / 45) * bmax, y = top + i * rh;
      const fill = i === 0 ? "#2d4bf0" : i === MODES.length - 1 ? "#e3962b" : "#b9c4ff";
      const strong = i === 0 || i === MODES.length - 1;
      return `<text x="${lx}" y="${y + 18}" text-anchor="end" fill="${strong ? "#15171d" : "#3a3e48"}" font-weight="${strong ? 700 : 500}"><tspan font-family="JetBrains Mono" font-size="15" fill="#767a85">${c}</tspan>  ${n}</text>
        <rect x="${bx}" y="${y + 4}" width="${Math.max(w, 3)}" height="${rh - 9}" rx="4" fill="${fill}"/>
        <text x="${bx + Math.max(w, 3) + 8}" y="${y + 18}" fill="${strong ? "#15171d" : "#767a85"}" font-weight="${strong ? 700 : 500}">${pct.toFixed(1)}%</text>`;
    }).join("");
    return `<svg viewBox="0 0 640 400" width="560" height="350" font-family="Instrument Sans" font-size="17">${rows}</svg>`;
  }
  // Phi correlation between the 14 MAST labels (computed from MAD_full_dataset.json, 1,638 scorable)
  const CODES = ["1.1", "1.2", "1.3", "1.4", "1.5", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "3.1", "3.2", "3.3"];
  const PHI = [[1, .19, .22, .21, .29, .22, .19, .49, .08, .2, .32, .17, .24, .31], [.19, 1, .16, .44, .25, .44, .05, .28, .04, .26, .17, .09, .15, .15], [.22, .16, 1, .32, .66, .26, .22, .35, .09, .37, .22, .14, .27, .25], [.21, .44, .32, 1, .4, .62, .21, .41, .18, .34, .22, .19, .23, .26], [.29, .25, .66, .4, 1, .32, .22, .42, .13, .29, .24, .14, .24, .24], [.22, .44, .26, .62, .32, 1, .15, .38, .14, .28, .25, .13, .24, .23], [.19, .05, .22, .21, .22, .15, 1, .31, .22, .25, .33, .25, .23, .29], [.49, .28, .35, .41, .42, .38, .31, 1, .18, .31, .35, .22, .3, .27], [.08, .04, .09, .18, .13, .14, .22, .18, 1, .14, .13, .12, .13, .13], [.2, .26, .37, .34, .29, .28, .25, .31, .14, 1, .22, .15, .34, .3], [.32, .17, .22, .22, .24, .25, .33, .35, .13, .22, 1, .23, .4, .48], [.17, .09, .14, .19, .14, .13, .25, .22, .12, .15, .23, 1, .23, .39], [.24, .15, .27, .23, .24, .24, .23, .3, .13, .34, .4, .23, 1, .35], [.31, .15, .25, .26, .24, .23, .29, .27, .13, .3, .48, .39, .35, 1]];
  function heatSVG() {
    const c = 23, ox = 50, oy = 8;
    const mix = (v) => { const t = Math.min(v / 0.66, 1); const a = [243, 241, 236], b = [45, 75, 240]; return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(",")})`; };
    let cells = "";
    PHI.forEach((r, i) => r.forEach((v, j) => {
      const fill = i === j ? "#15171d" : mix(v);
      cells += `<rect x="${ox + j * c}" y="${oy + i * c}" width="${c - 2}" height="${c - 2}" rx="3" fill="${fill}"/>`;
    }));
    const hi = (i, j) => `<rect x="${ox + j * c - 2}" y="${oy + i * c - 2}" width="${c + 2}" height="${c + 2}" rx="4" fill="none" stroke="#e3962b" stroke-width="3"/>`;
    const lab = CODES.map((k, i) => `<text x="${ox - 8}" y="${oy + i * c + 16}" text-anchor="end">${k}</text>`).join("");
    const scale = `<defs><linearGradient id="phig"><stop offset="0" stop-color="rgb(243,241,236)"/><stop offset="1" stop-color="#2d4bf0"/></linearGradient></defs>
      <rect x="${ox}" y="${oy + 14 * c + 16}" width="200" height="12" rx="6" fill="url(#phig)"/>
      <text x="${ox}" y="${oy + 14 * c + 50}" font-family="Instrument Sans" font-size="16">0</text>
      <text x="${ox + 200}" y="${oy + 14 * c + 50}" text-anchor="end" font-family="Instrument Sans" font-size="16">0.66</text>`;
    return `<svg viewBox="0 0 380 400" width="320" height="337" font-family="JetBrains Mono" font-size="14" fill="#767a85">${cells}${hi(2, 4)}${hi(4, 2)}${lab}${scale}</svg>`;
  }

  /* ---------- 4.2 platform diagram ---------- */
  function platformSVG() {
    const box = (x, y, w, h, t, s, k = "b") => {
      const st = { b: ["#ffffff", "#d6d2c8", "#15171d"], blue: ["#e9edff", "#c8d0ff", "#1a2fb0"], ink: ["#15171d", "#15171d", "#ffffff"], plan: ["#ffffff", "#e3962b", "#8a5208"] }[k];
      return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="${st[0]}" stroke="${st[1]}" stroke-width="2" ${k === "plan" ? 'stroke-dasharray="8 6"' : ""}/>
        <text x="${x + w / 2}" y="${y + h / 2 - (s ? 4 : -8)}" text-anchor="middle" font-size="23" font-weight="650" fill="${st[2]}">${t}</text>
        ${s ? `<text x="${x + w / 2}" y="${y + h / 2 + 24}" text-anchor="middle" font-size="18" fill="${k === "ink" ? "#b8bcc7" : "#767a85"}">${s}</text>` : ""}`;
    };
    const ln = (d, c = "#9a9ca3", dash = "") => `<path d="${d}" fill="none" stroke="${c}" stroke-width="2.5" ${dash ? `stroke-dasharray="${dash}"` : ""} marker-end="url(#ah${c === "#2d4bf0" ? "b" : c === "#e3962b" ? "a" : ""})"/>`;
    const tag = (x, y, t, c = "#767a85") => `<text x="${x}" y="${y}" text-anchor="middle" font-size="17" fill="${c}" font-weight="600">${t}</text>`;
    const band = (y, h, t) => `<rect x="0" y="${y}" width="1430" height="${h}" rx="20" fill="rgba(255,255,255,0.55)" stroke="#e2ded5" stroke-width="1.5"/>
      <text x="24" y="${y + 34}" font-size="16" font-weight="700" letter-spacing="2.2" fill="#767a85">${t}</text>`;
    return `<svg viewBox="0 0 1680 700" width="1680" height="700" font-family="Instrument Sans">
      <defs>${["", "b", "a"].map((s) => `<marker id="ah${s}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${s === "b" ? "#2d4bf0" : s === "a" ? "#e3962b" : "#9a9ca3"}"/></marker>`).join("")}</defs>
      ${band(0, 200, "SESSION PLANE")}
      ${box(24, 64, 290, 104, "Browser client", "React · editor · presence")}
      ${box(390, 64, 270, 104, "CRDT server", "Yjs: edits converge")}
      ${box(736, 64, 300, 104, "Session service", "FastAPI · roles · order")}
      ${box(1112, 64, 290, 104, "Event log", "PostgreSQL · Redis fan-out", "blue")}
      ${ln("M314,116 L382,116")}${ln("M660,116 L728,116")}${ln("M1036,116 L1104,116")}
      ${tag(348, 104, "edits")}${tag(694, 104, "events")}${tag(1070, 104, "append")}
      ${band(222, 200, "EXECUTION AND SERVING")}
      ${box(24, 286, 360, 104, "Agent runtime", "LangGraph · plan, act, observe")}
      <rect x="736" y="276" width="666" height="124" rx="16" fill="#f5f3ee" stroke="#d6d2c8" stroke-width="2"/>
      <text x="756" y="304" font-size="17" font-weight="700" fill="#3a3e48">Serving: one predict endpoint per model</text><text x="1382" y="304" text-anchor="end" font-size="16" font-weight="700" fill="#8a5208">interface frozen · ready for each winner</text>
      ${["M1", "M2", "M3", "M4"].map((m, i) => box(756 + i * 160, 318, 146, 66, m, "", i === 0 ? "blue" : "b")).join("")}
      ${ln("M886,168 L886,268")}${tag(946, 226, "on join")}
      ${ln("M384,338 C 560,338 640,150 728,140")}${tag(470, 300, "agent steps")}
      ${band(444, 256, "DATA AND MODELS · ML FLOW")}
      ${box(24, 508, 210, 80, "Public data", "pinned", "b")}
      ${box(24, 600, 210, 80, "Sessions", "planned export", "plan")}
      ${box(300, 540, 230, 112, "Warehouse", "DuckDB · 19 checks")}
      ${box(596, 540, 220, 112, "Frozen splits", "hashed manifests", "blue")}
      <rect x="882" y="520" width="290" height="152" rx="14" fill="#15171d"/>
      <text x="1027" y="572" text-anchor="middle" font-size="23" font-weight="650" fill="#fff">Training</text>
      <text x="1027" y="608" text-anchor="middle" font-size="18" fill="#b8bcc7">1 RTX 5080 Laptop GPU</text>
      <text x="1027" y="634" text-anchor="middle" font-size="18" fill="#b8bcc7">16 GB · PyTorch, PEFT · $0</text>
      ${box(1238, 540, 164, 112, "Eval", "1 harness", "blue")}
      ${ln("M234,552 L292,580")}${ln("M234,640 L292,612", "#e3962b", "7 6")}
      ${ln("M530,596 L588,596", "#2d4bf0")}${ln("M816,596 L874,596", "#2d4bf0")}${ln("M1172,596 L1230,596", "#2d4bf0")}
      ${ln("M1320,540 L1320,408", "#2d4bf0")}<text x="1336" y="480" font-size="17" font-weight="700" fill="#2d4bf0">winner only</text>
      
      <rect x="1460" y="0" width="220" height="700" rx="20" fill="#15171d"/>
      <text x="1570" y="46" text-anchor="middle" font-size="16" font-weight="700" letter-spacing="2" fill="#9aa0ac">FOR ALL PARTS</text>
      ${[["GitHub Actions", "CI on every PR"], ["Docker Compose", "one local stack"], ["Pinned lock", "same versions"], ["ADR-001 to 005", "frozen contracts"]].map(([a, b], i) =>
        `<text x="1570" y="${140 + i * 140}" text-anchor="middle" font-size="22" font-weight="650" fill="#fff">${a}</text><text x="1570" y="${170 + i * 140}" text-anchor="middle" font-size="18" fill="#9aa0ac">${b}</text>`).join("")}
    </svg>`;
  }

  /* ---------- title-slide illustration: people and agents around one ordered log ---------- */
  const titleArt = `<svg viewBox="0 0 600 520" width="600" height="520" font-family="JetBrains Mono">
    ${[[60, 120, "#2d4bf0", 150], [60, 260, "#e3962b", 266], [60, 400, "#13936a", 382]].map(([x, y, c, ty]) => `
      <path d="M${x + 44},${y} C 150,${y} 160,${ty} 214,${ty}" fill="none" stroke="${c}" stroke-width="2.5" opacity="0.55"/>
      <circle cx="${x}" cy="${y}" r="44" fill="${c}" opacity="0.12"/><circle cx="${x}" cy="${y - 9}" r="12" fill="${c}"/>
      <path d="M${x - 20},${y + 24} a20,18 0 0 1 40,0" fill="${c}"/>`).join("")}
    ${[[540, 196, 208], [540, 352, 324]].map(([x, y, ty]) => `
      <path d="M${x - 40},${y} C 450,${y} 440,${ty} 388,${ty}" fill="none" stroke="#15171d" stroke-width="2.5" opacity="0.4"/>
      <rect x="${x - 38}" y="${y - 38}" width="76" height="76" rx="20" fill="#15171d"/>
      <circle cx="${x - 13}" cy="${y - 4}" r="6" fill="#fff"/><circle cx="${x + 13}" cy="${y - 4}" r="6" fill="#fff"/>
      <rect x="${x - 14}" y="${y + 14}" width="28" height="4" rx="2" fill="#fff" opacity="0.7"/>`).join("")}
    <rect x="214" y="40" width="174" height="440" rx="26" fill="#fff" stroke="#e2ded5" stroke-width="2"/>
    <text x="301" y="80" text-anchor="middle" font-size="15" font-weight="700" fill="#767a85" letter-spacing="2">ONE LOG</text>
    ${[["#2d4bf0", 88], ["#e3962b", 70], ["#2d4bf0", 100], ["#15171d", 80], ["#e3962b", 94], ["#13936a", 62], ["#15171d", 90]].map(([c, w], i) => `
      <text x="236" y="${126 + i * 50}" font-size="15" fill="#a3a6ae">${i + 1}</text>
      <rect x="258" y="${112 + i * 50}" width="${w}" height="18" rx="9" fill="${c}" opacity="${i === 6 ? 0.35 : 0.9}"/>`).join("")}
  </svg>`;

  const tile = (ic, h, p, cls = "") => `<div class="card tile"><div class="icwrap ${cls}">${I(ic, 32)}</div><h3>${h}</h3><p>${p}</p></div>`;
  const ok = (t) => `<span class="chip green">${I("check", 20, 2.6)}${t}</span>`;

  window.DECK = [
    /* ================= 0 · Title and recap ================= */
    {
      arc: 0, bare: true, rubric: "Opening · recap", speaker: "Manav", secs: 35,
      title: "Multiplayer Agents · where we were at Workbook 1",
      html: `
        <div class="t-title">
          <div class="kicker">DATA 298A · Team 4 · Team Meeting 2 · 12 Nov 2026</div>
          <div class="hero">Multiplayer<br><em>Agents</em></div>
          <p class="sub">One live session where several people and several agents work together. Today: the data and the models.</p>
          <div class="names">${["Ayush Gawai", "Naman Chheda", "Manav Patel", "Shriram Dundigalla", "Pramod Dindukurthi"].map((n) => `<span class="chip ghost">${n}</span>`).join("")}</div>
        </div>
        <div class="t-art">${titleArt}</div>
        ${timeline(760, "then")}
        <div style="position:absolute;left:120px;top:880px;display:flex;gap:12px;align-items:center">
          <span class="label" style="margin-right:6px">At Workbook 1</span>
          <span class="chip">Plan · requirements · schedule</span>
          <span class="chip">Platform contracts frozen</span>
          <span class="chip">MAST data downloaded</span>
        </div>`,
      say: [
        "Good afternoon. We're Team 4, and our project is Multiplayer Agents: one live workspace where several people and several AI agents work on the same task together.",
        "At our last presentation, on October 7th, we had the plan, the requirements and the schedule, the platform's interfaces were frozen, and the MAST data was downloaded.",
        "Today: what we built since, then the data and the models."
      ],
      qa: [
        ["Why no results yet?", "The template leaves 4.5 and 4.6 for the final report on 7 December. The Model 1 contract (ADR-005) also forbids a selection run until the annotated product-session split is frozen, and that split does not exist yet."],
        ["What changed since Workbook 1?", "Two things, both in the carry-forward table. The Model 1 candidates are now BM25, ModernBERT, Phi-4-mini and Qwen3.5-4B (Gemma was replaced, and a parameter-free floor added). And Model 1 is selected on critical-fact recall behind safety gates, not on ROUGE-L alone. QMSum is also corrected from 1,808 to 1,810 pairs."]
      ]
    },

    /* ================= 1 · Built since Workbook 1 ================= */
    {
      arc: 1, num: "", kicker: "Since 7 October", rubric: "Progress since Workbook 1", speaker: "Manav", secs: 30,
      title: "Six things built since Workbook 1",
      html: `
        ${timeline(10, "since", 0)}
        <div style="position:absolute;left:0;right:0;top:128px;display:grid;grid-template-columns:repeat(3,1fr);gap:22px">
          ${tile("download", "QMSum collected, splits frozen", "1,810 pairs · 1,257 / 272 / 281 · commit 330603f")}
          ${tile("users", "Prototype: shared editing and rollback", "client, CRDT server and presence on main")}
          ${tile("filter", "MAST cleaned", "1,638 of 1,642 traces scorable")}
          ${tile("shield", "Model 1 contract frozen", "4 candidates, gates and metrics · ADR-005")}
          ${tile("bot", "Agent runtime on main", "LangGraph plan, act, observe loop")}
          ${tile("db", "Source-to-warehouse pipeline", "19 data checks and run history · on main (PR #33)")}
        </div>
        <div class="strip amber" style="position:absolute;left:0;right:0;bottom:0">${I("flag", 30)}Next: record our own sessions, then train and compare the four Model 1 candidates</div>`,
      say: [
        "Since then we finished six things. QMSum, which trains our first model, is collected and split. The prototype runs. MAST is cleaned. The Model 1 contract is written, so all candidates are judged the same way. The agent runtime is merged. And one command loads both datasets into a warehouse, which Shriram will run live.",
        "Next up, at the bottom: recording our own sessions and training the Model 1 candidates."
      ],
      qa: [
        ["Has any GPU work happened?", "Feasibility only. ModernBERT passed a 40-step smoke run on the lab GPU with checkpoint and resume. Phi-4-mini failed after 2 of 15 steps, not yet diagnosed (probably memory at 4,096 tokens). Qwen3.5-4B has not run. An earlier Qwen3-1.7B infrastructure run checked QLoRA, checkpointing and resume. None of this is a result."],
        ["Why no product sessions yet?", "Sessions need the end-to-end integration gate, which has not been passed. The Workbook 1 risk trigger (fewer than five sessions by late October) fired, so the documented fallback is in effect: internal sessions plus 18 scripted smoke examples (DAT-53). First sessions are due by 2 December."],
        ["Where is the harness?", "PR #25 (DAT-61), in review. Review found the comparison step applying gates to the three-seed mean, which ADR-005 forbids. It is being fixed before merge; target 18 November."]
      ]
    },

    /* ================= 2 · Prototype ================= */
    {
      arc: 1, num: "", kicker: "Working prototype", rubric: "Progress · prototype", speaker: "Manav", secs: 30,
      title: "Two people, one document, one ordered log",
      html: `
        <div style="position:absolute;left:44px;top:0;width:900px;opacity:0.9">
          <div class="win"><div class="bar"><i></i><i></i><i></i><b>Ben</b><span class="role">reviewer · second tab</span></div><div style="height:420px;background:#f7f7f8"></div></div>
        </div>
        <div style="position:absolute;left:0;top:44px;width:900px">
          <div class="win"><div class="bar"><i></i><i></i><i></i><b>Ada</b><span class="role">author · first tab</span><span class="chip green" style="margin-left:auto;font-size:15px;padding:3px 10px">REAL API</span></div><img src="figures/proto_ada.png" alt="Ada's tab: the shared document and the event log"></div>
          <div class="callout" style="position:absolute;left:-18px;top:88px">1</div>
          <div class="callout" style="position:absolute;left:-18px;top:300px">2</div>
        </div>
        <div class="card" style="position:absolute;left:1000px;top:0;right:0">
          <div style="display:flex;align-items:center;gap:14px;padding:22px 26px 6px"><div class="callout">3</div><span style="font:700 26px var(--display)">Roll back to seq 2</span></div>
          <div class="elog">
            ${[["1", "#2d4bf0", "Ada", "join", "joined as author", ""], ["2", "#e3962b", "Ben", "join", "joined as reviewer", ""],
               ["3", "#2d4bf0", "Ada", "instruction", "Draft the intro paragraph", "gone"], ["4", "#e3962b", "Ben", "instruction", "Make it shorter", "gone"]].map(([q, c, a, t, x, g]) =>
              `<div class="erow ${g}"><span class="sq">${q}</span><span style="display:flex;align-items:center;gap:8px"><span class="dot" style="background:${g ? "#cfccc4" : c}"></span>${a}</span><span class="ty">${t}</span><span>${x}</span></div>`).join("")}
            <div style="display:flex;align-items:center;gap:10px;margin-top:18px;font:600 21px var(--sans);color:#0b6b4c">${I("check", 24, 2.6)}“Rolled back to seq 2; removed 2 events.”</div>
            <div class="muted" style="font:500 17px var(--sans);margin-top:8px">redrawn from the client's before and after screenshots</div>
          </div>
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px">
          ${[["1", "Edits merge", "A Yjs CRDT merges both people's typing"], ["2", "Every action is an event", "One ordered log, shared by the session"], ["3", "Rollback for everyone", "The two instructions are removed"]].map(([n, h, p]) =>
            `<div style="display:flex;gap:16px;align-items:flex-start"><div class="callout">${n}</div><div><div style="font:650 27px var(--display)">${h}</div><div class="muted" style="font:500 20px var(--sans);margin-top:4px">${p}</div></div></div>`).join("")}
        </div>`,
      say: [
        "This is our client on the real session service. Ada and Ben type in the same document at once, and a CRDT merges their edits, so nothing is lost.",
        "Every action is also an ordered event in one shared log, on the right. Roll back to event two, and both instructions disappear for everyone.",
        "That log is where our own data will come from. Over to Naman."
      ],
      qa: [
        ["Is any model output shown in the client?", "No. The client does not call or display any model yet. The serving adapters are stubs behind a frozen interface until a bake-off winner is locked."],
        ["Why about 30 sessions?", "That is the Workbook 1 pilot target. The first sessions come from the five of us, so the population is narrow; every result will state it."],
        ["Is it deployed in the cloud?", "Not yet. It runs locally with Docker Compose: PostgreSQL, Redis, the session service and serving. Cloud deployment is deferred to the 298B study, when people outside the team need access."],
        ["Why a CRDT and an event log, both?", "The CRDT (Yjs) makes concurrent text edits converge. It cannot order agent commands or undo them. The event log gives total order, audit, interruption and rollback."],
        ["Can we see it live?", "Only if asked: three terminals (session-service with uvicorn on port 8000, crdt-server npm run dev, client npm run dev), two tabs in one session, type in both, roll back to seq 2."]
      ]
    },

    /* ================= 3 · 3.1 Data process ================= */
    {
      arc: 2, num: "3.1", kicker: "Data process", rubric: "3.1 Data Process · 3.6 stage summary", speaker: "Naman", secs: 25,
      title: "Three sources, one five-step process",
      html: `
        <div class="lanes">
          <div></div>
          ${[["download", "Collect"], ["filter", "Clean"], ["shuffle", "Transform"], ["split", "Prepare"], ["chart", "Describe"]].map(([ic, h], i) => `<div class="h">${I(ic, 26)}<span class="n">${i + 1}</span>${h}</div>`).join("")}
          <div class="h">${I("flag", 26)}Used for</div>

          <div class="src"><b>MAST</b><span>published failure traces</span></div>
          <div class="cell"><b>Pinned download</b><span>1,642 traces</span></div>
          <div class="cell"><b>Validate labels</b><span>4 removed</span></div>
          <div class="cell"><b>Flat table</b><span>1,638 × 26</span></div>
          <div class="cell"><b>Eval manifest</b><span>frozen v1.0.0</span></div>
          <div class="cell last"><b>Stats, charts</b><span>imbalance</span></div>
          <div class="use"><b>Baseline</b><span>reproduce the judge</span></div>

          <div class="src"><b>QMSum</b><span>meeting summaries</span></div>
          <div class="cell"><b>Pinned download</b><span>232 meetings</span></div>
          <div class="cell"><b>Check fields</b><span>0 removed</span></div>
          <div class="cell"><b>Events with ids</b><span>1,810 examples</span></div>
          <div class="cell"><b>Train / val / test</b><span>1,257·272·281</span></div>
          <div class="cell last"><b>Stats, charts</b><span>lengths</span></div>
          <div class="use"><b>Model 1</b><span>training only</span></div>

          <div class="src"><b>Our sessions</b><span>our own event log</span></div>
          <div class="cell plan"><b>Export log</b><span>planned</span></div>
          <div class="cell plan"><b>Pseudonymise</b><span>planned</span></div>
          <div class="cell plan"><b>Annotate facts</b><span>planned</span></div>
          <div class="cell plan"><b>Split by session</b><span>rules frozen</span></div>
          <div class="cell plan last"><b>Stats, charts</b><span>planned</span></div>
          <div class="use plan"><b>Picks winners</b><span>for every model</span></div>
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;display:flex;gap:16px;align-items:center">
          <span class="chip blue"><span class="dot" style="background:var(--blue)"></span>built, on main</span>
          <span class="chip amber"><span class="dot" style="background:var(--amber)"></span>planned</span>
          <span class="chip ghost">${I("lock", 20)}test split read once</span>
          <span class="chip ghost">${I("eye", 20)}nothing dropped silently</span>
          <span class="chip ghost" style="margin-left:auto">${I("db", 20)}built stages also run as one pipeline · live demo</span>
        </div>`,
      say: [
        "Section three, the data. Three sources, each with one job. MAST backs the baseline we reproduce. QMSum trains Model 1. Our own sessions will pick the winners, because only they look like our real task.",
        "Each row runs the same five steps: collect, clean, transform, prepare, describe. Blue is built. Amber is our sessions, still planned."
      ],
      qa: [
        ["Why is the session row amber?", "No session has been recorded, because the end-to-end integration gate has not been passed. The fallback from Workbook 1 is in effect: internal sessions plus 18 scripted smoke examples. Its split rules are already frozen in ADR-005: split by session_id, freeze before the first comparative run, synthetic examples in training only."],
        ["Why keep the three paths separate?", "MAST has two label sources, judge labels on 1,642 traces and human labels on 19. Mixing paths is how a baseline number gets scored against the wrong labels."],
        ["Where is MAST's train split?", "There is none on purpose. The baseline is an inference-only judge, so MAST is evaluation only: the frozen manifest (v1.0.0) fixes 1,638 scorable records and the 4 human-labelled traces that use the current taxonomy (the other 15 of the 19 use older taxonomies)."],
        ["Design rules?", "Public data is never committed; it is rebuilt from pinned revisions and checked by digest. Nothing is dropped silently. The test split is opened only for the final frozen comparison (ADR-005 rule 4)."]
      ]
    },

    /* ================= 4 · 3.2 Data collection ================= */
    {
      arc: 2, num: "3.2", kicker: "Data collection", rubric: "3.2 Data Collection", speaker: "Naman", secs: 25,
      title: "Collected in full: the counts match the papers",
      html: `
        <div style="display:grid;grid-template-columns:1fr 1fr 0.72fr;gap:22px;height:350px">
          <div class="card tile" style="gap:14px">
            <div class="label">MAST · failure traces</div>
            <div style="display:flex;align-items:baseline;gap:18px"><div class="big" style="color:var(--blue)">1,642</div><span class="chip green">${I("check", 20, 2.6)}= paper</span></div>
            <div style="display:flex;flex-wrap:wrap;gap:8px"><span class="chip">199.6 MB</span><span class="chip">14 failure labels</span><span class="chip">7 frameworks</span><span class="chip">5 LLMs</span><span class="chip">8 benchmarks</span><span class="chip">+19 human-labelled</span></div>
            <p class="mono" style="font-size:17px;margin-top:auto">Hugging Face mcemri/MAD @ 95118ac9 · CC-BY-4.0</p>
          </div>
          <div class="card tile" style="gap:14px">
            <div class="label">QMSum · meeting summaries</div>
            <div style="display:flex;align-items:baseline;gap:18px"><div class="big">1,810</div><span class="muted" style="font:600 22px var(--sans)">question–summary pairs</span></div>
            <div style="display:flex;flex-wrap:wrap;gap:8px"><span class="chip">232 meetings</span><span class="chip">129,177 turns</span><span class="chip">1,576 specific</span><span class="chip">234 general</span></div>
            <p class="mono" style="font-size:17px;margin-top:auto">Yale-LILY/QMSum official release · MIT</p>
          </div>
          <div class="card tile" style="gap:14px;border:2px dashed var(--amber)">
            <div class="label" style="color:var(--amber-ink)">Our sessions</div>
            <div class="big" style="color:var(--amber)">~30</div>
            <p style="color:var(--amber-ink);font-weight:600">sessions planned · schema ready</p>
            <div style="display:flex;flex-wrap:wrap;gap:6px">${["event_id", "seq", "type", "actor", "payload"].map((f) => `<span class="chip amber mono" style="font-size:15px;padding:4px 10px">${f}</span>`).join("")}</div>
            <p class="mono" style="font-size:17px;margin-top:auto">PostgreSQL event log</p>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px">
          <div><div class="label" style="margin-bottom:10px">Raw sample · MAST record 400</div>${code(`
"mas_name": "AG2",  "llm_name": "Claude",
"benchmark_name": "GSM",  "trace_id": 190,
"trace": { "key": "AG2_GSM_Plus_Claude",
           "trajectory": "Let's use Python to solve…" },
"mast_annotation": { "1.1": 0, "1.2": 0, … "2.6": 1,
                     "3.1": 0, "3.2": 1, "3.3": 1 }`)}</div>
          <div><div class="label" style="margin-bottom:10px">Raw sample · QMSum, first training meeting</div>${code(`
"meeting_transcripts": [{ "speaker": "Project Manager",
    "content": "Yep . Soon as I get this . Okay . …" }],
"specific_query_list": [{
    "query": "How Did Project Manager and User
              Interface introduce the prototype …?",
    "answer": "Project Manager introduced that …" }]`)}</div>
        </div>`,
      say: [
        "Collection is a script: it downloads a pinned version and checks every file with a SHA-256 checksum, so anyone gets exactly the same data.",
        "We got all 1,642 MAST traces, exactly the paper's number, and 1,810 question-and-summary pairs from 232 QMSum meetings.",
        "Below are two raw records: a MAST trace with its fourteen failure labels, and a QMSum meeting with its questions and summaries."
      ],
      qa: [
        ["Workbook 1 said 1,808 QMSum pairs.", "That is the paper's figure. The pinned release yields 1,810: 1,576 specific and 234 general queries. It is corrected in the carry-forward table."],
        ["Is that enough data?", "For the public sources, yes: MAST is the complete corpus of the paper we reproduce and QMSum is the complete benchmark. The source that is not yet sufficient is our own sessions, and Workbook 2 says so plainly."],
        ["What is in MAST?", "Seven multi-agent frameworks, five underlying language models and eight benchmarks; three frameworks contribute only 30 traces each. Trajectories run from 1,262 to over 2 million characters."],
        ["What about the smoke fixtures?", "18 scripted examples from 12 sessions (DAT-53), in the product schema with critical facts and evidence ids. They test the pipeline only and are barred from ever being an evaluation split."],
        ["Which scripts?", "data/scripts/download_mast.py and download_qmsum.py. They are idempotent and refuse to continue if a count or a hash differs from the pinned value. Digests are in the two STATS.md files."]
      ]
    },

    /* ================= 5 · 3.3 Pre-processing ================= */
    {
      arc: 2, num: "3.3", kicker: "Data pre-processing", rubric: "3.3 Data Pre-processing", speaker: "Naman", secs: 30,
      title: "Every cleaning rule is code, and reports what it removed",
      html: `
        <div class="card" style="position:absolute;left:0;top:0;width:1060px;padding:8px 30px">
          <div class="ledger">
            ${[["MAST", "Checksum and record count equal the pinned values", "download_mast.py", ok("0 removed")],
               ["MAST", "Required fields present; key (trace.key, trace_id) unique", "eda_mast.py", ok("0 removed")],
               ["MAST", "Each label is exactly 0, 1 or null", "eda_mast.py · 22,988 cells", ok("0 invalid")],
               ["MAST", "A missing label stays missing, never 0", "eda_mast.py", `<span class="chip blue">56 cells kept</span>`, "key"],
               ["MAST", "All 14 labels missing: exclude from scoring", "named in EDA_SUMMARY.json", `<span class="chip amber">4 removed</span>`],
               ["QMSum", "Checksums and counts; turns rendered as Speaker: text", "download_qmsum.py · make_splits.py", ok("0 removed")],
               ["QMSum", "Query, context, summary non-empty; ids unique", "t4a6_data_facts.py · pytest", ok("0 of 1,810")]
              ].map(([d, r, t, res, k]) => `<div class="lrow ${k || ""}"><div class="ds">${d}</div><div class="rule">${r}<small>${t}</small></div><div class="res">${res}</div></div>`).join("")}
          </div>
        </div>
        <div style="position:absolute;left:1092px;right:0;top:0;bottom:0;display:flex;flex-direction:column;gap:22px">
          <div class="card tile" style="padding:26px 30px">
            <div class="label">MAST traces</div>
            <div style="display:flex;align-items:center;gap:16px"><span class="mid muted">1,642</span>${arrow(40)}<span class="mid" style="color:var(--blue)">1,638</span></div>
            <p><b style="color:var(--amber-ink)">4 removed, 0.24%</b> · traces 4, 72, 73, 81 of one ChatDev run</p>
          </div>
          <div style="flex:1;display:flex;flex-direction:column;gap:10px">
            <div class="label">Before → after</div>
            ${code(`// ChatDev_ProgramDev-v2_CodeLlama, 4
{ "1.1": null, "1.2": null, … "3.3": null }`, "font-size:17px;padding:16px 20px")}
            <div style="display:flex;gap:10px;align-items:center;font:600 21px var(--sans);color:var(--amber-ink)">${arrow(26)}excluded, labels stay null</div>
            ${code(`// AG2_GSM_Plus_Claude, 190
{ "1.1": 0, … "2.6": 1, "3.2": 1, "3.3": 1 }`, "font-size:17px;padding:16px 20px")}
            <div style="display:flex;gap:10px;align-items:center;font:600 21px var(--sans);color:#0b6b4c">${arrow(26)}kept: 14 valid labels, 3 positive</div>
          </div>
        </div>`,
      say: [
        "Every cleaning rule is code, and each one reports what it removed. Most removed nothing, because these are curated datasets. One removed four MAST traces whose fourteen labels were all missing; one is shown on the right.",
        "The key rule is in blue: a missing label stays missing. We never turn it into a zero, because 'not judged' isn't 'no failure'. Shriram takes it from here."
      ],
      qa: [
        ["Only four rows removed. Did you really clean the data?", "Yes. Both are curated research releases, so the value is the guarantee, not the volume: unique record keys, label domain 0, 1 or null over 22,988 cells, and ten quality gates that pass. The four excluded traces are named in the committed summary."],
        ["Why not strip the disfluency markers like {vocalsound}?", "They are part of the published benchmark text and the reference summaries were written against them. Stripping them would make our QMSum numbers incomparable with published figures."],
        ["Is pre-processing deterministic?", "Yes. Two consecutive runs produce byte-identical summary files, which we use as a regression check. The gate ends with QUALITY GATE: all checks passed."],
        ["22,988 cells here but 22,932 label rows in the warehouse?", "22,988 is 1,642 raw traces × 14 labels. After excluding the 4 all-null traces, 1,638 × 14 = 22,932. The 56 null cells are exactly the 4 excluded traces × 14."],
        ["Why is trace_id not the key?", "trace_id alone has only 206 distinct values and restarts in every source run. The key is (trace.key, trace_id): 1,642 unique."]
      ]
    },

    /* ================= 6 · 3.4 Transformation ================= */
    {
      arc: 2, num: "3.4", kicker: "Data transformation", rubric: "3.4 Data Transformation", speaker: "Shriram", secs: 30,
      title: "Same facts, reshaped for the model",
      html: `
        ${[["MAST", "eda_mast.py", code(`"mast_annotation": {
  "1.1": 0, "1.2": 0, … "2.5": 0,
  "2.6": 1, "3.1": 0,
  "3.2": 1, "3.3": 1 }`, "height:212px"),
            `<div class="card" style="height:212px;padding:8px 10px;display:flex;flex-direction:column;justify-content:center">
              <table class="mini"><tr><th>trace_key</th><th>n_failures</th><th>failure_codes</th><th>spec·mis·ver</th></tr>
              <tr><td>AG2_GSM_Plus_Claude</td><td>3</td><td>2.6|3.2|3.3</td><td>0 · 1 · 2</td></tr></table>
              <div style="display:flex;gap:10px;padding:14px 14px 4px"><span class="chip blue">1,638 rows × 26 columns</span><span class="chip">142 KB, not 199.6 MB</span></div></div>`,
            "Countable, plottable, comparable with the paper"],
           ["QMSum", "eval/contracts/ m1.py", code(`{ "speaker": "Grad B",
  "content":
    "And they wouldn't look
     pretty . So ." }`, "height:212px"),
            code(`{ "event_id": "qmsum_test_9_s3:span:0000",
  "sequence": 0,
  "event_type": "doc_update",
  "text": "Grad B: And they wouldn't look…" }`, "height:212px"),
            "One example per question, shaped like a live session: claims cite event ids"]
          ].map(([ds, tool, before, after, why], i) => `
          <div style="position:absolute;left:0;right:0;top:${50 + i * 262}px;display:grid;grid-template-columns:110px 420px 130px 720px 1fr;gap:18px;align-items:center">
            <div style="font:700 30px var(--display)">${ds}</div>
            <div>${before}</div>
            <div style="display:flex;flex-direction:column;align-items:center;gap:6px">${arrow(46)}<span class="mono muted" style="font-size:15px;text-align:center;word-break:break-all">${tool}</span></div>
            <div>${after}</div>
            <div style="font:600 22px/1.3 var(--sans);color:var(--ink2);border-left:4px solid var(--blue);padding-left:18px">${why}</div>
          </div>`).join("")}
        <div style="position:absolute;left:128px;top:0;display:grid;grid-template-columns:420px 130px 720px;gap:18px"><span class="label">Before</span><span></span><span class="label">After</span></div>
        <div class="strip ink" style="position:absolute;left:0;right:0;bottom:0">${I("lock", 30)}The reference summary stays outside the input, so the answer cannot leak.</div>`,
      say: [
        "Transformation changes the shape, not the facts. Top row: MAST's nested labels become one flat table, 1,638 rows by 26 columns, that we can count and compare with the paper.",
        "Bottom row: each QMSum question becomes one example, and each piece of transcript becomes an event with an id. That's the shape of a live session, so the model can cite its evidence. The answer stays out of the input, so it can't leak."
      ],
      qa: [
        ["Why turn meeting transcripts into events?", "All four Model 1 candidates must consume one input contract, m1-input-v1, which is also what live sessions produce. One adapter in the evaluation layer does the mapping, so no candidate invents its own (ADR-005)."],
        ["Why drop the trajectory text from the MAST table?", "The analysis table is 142 KB instead of 199.6 MB. The full text is read from the pinned file when the judge needs it; the table keeps its length as trace_chars."],
        ["What other columns are derived?", "n_failures, n_null_labels, the pipe-joined failure_codes, and the paper's three category roll-ups (specification, inter-agent misalignment, task verification), because the paper reports at category level."],
        ["How do live sessions map?", "SessionEvent to M1Event: seq to sequence, type to event_type, actor.id to actor_id, payload.text to text. Ids are deterministic (qmsum_<split>_<meeting>_<s|g><n>) so predictions trace back to inputs across seeds."]
      ]
    },

    /* ================= 7 · 3.5 Data preparation ================= */
    {
      arc: 2, num: "3.5", kicker: "Data preparation", rubric: "3.5 Data Preparation", speaker: "Shriram", secs: 25,
      title: "Frozen splits, and no meeting crosses a split",
      html: `
        <div style="display:flex;flex-direction:column;justify-content:space-between;height:100%">
        <div class="split" style="height:150px">
          <div style="flex:69.4;background:var(--ink)"><b>Train 1,257</b><span>69.4% · 162 meetings</span></div>
          <div style="flex:15;background:var(--blue)"><b>Val 272</b><span>15.0% · 35 meetings</span></div>
          <div style="flex:15.5;background:var(--amber)"><b>Test 281</b><span>15.5% · 35</span></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px">
          ${[["var(--ink)", "Train sample", "qmsum_train_145_s1", "Did the Professor agree with Grad G on cross-lingual data?", "17 spans"],
             ["var(--blue)", "Validation sample", "qmsum_val_4_s0", "Summarize the presentations on working design, technical functions, functional requirements.", "260 spans"],
             ["var(--amber)", "Test sample", "qmsum_test_9_s3", "How would the middle layer work?", "8 spans"]].map(([c, l, id, q, n]) =>
            `<div class="card" style="padding:24px 28px;min-height:200px;border-top:6px solid ${c}"><div class="label">${l}</div><div style="font:600 24px/1.3 var(--sans);margin:10px 0">“${q}”</div><div class="mono muted" style="font-size:16px">${id} · ${n}</div></div>`).join("")}
        </div>
        <div style="display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:22px">
          <div class="card" style="padding:24px 28px;background:var(--green-soft);border-color:#bfe5d4">
            <div class="label" style="color:#0b6b4c">Leakage check</div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px">
              ${["meetings", "example ids", "contexts", "query + ref"].map((t) => `<div><div class="mid" style="color:var(--green)">0</div><div style="font:600 18px var(--sans);color:#0b6b4c;margin-top:6px">${t}</div></div>`).join("")}
            </div>
            <div style="font:600 18px var(--sans);color:#0b6b4c;margin-top:10px">shared across splits</div>
          </div>
          <div class="card" style="padding:24px 28px;background:var(--amber-soft);border-color:#f2d6a8">
            <div class="label" style="color:var(--amber-ink)">What it found</div>
            <div style="display:flex;align-items:baseline;gap:12px;margin-top:10px"><div class="mid" style="color:var(--amber)">4</div><div style="font:600 21px/1.3 var(--sans);color:var(--amber-ink)">rows share 2 upstream summaries · disclosed</div></div>
          </div>
          <div class="card" style="padding:24px 28px">
            <div class="label">Fixed and versioned</div>
            <div style="font:600 22px/1.45 var(--sans);margin-top:10px">SHA-256 per file · MANIFEST.json</div>
            <div style="font:600 19px var(--sans);color:var(--blue-ink)">validation tunes · test is read once</div>
            <div class="mono muted" style="font-size:17px">commit 330603f · seed 13 · unchanged since</div>
          </div>
        </div></div>`,
      say: [
        "The splits are fixed: 1,257 training rows, 272 validation and 281 test, each file stored with a checksum.",
        "We split by whole meeting, and the green box is the leakage check: nothing is shared across splits. It did find two repeated summaries in the original release, four rows, which we report. Validation is for tuning; test is read once, at the end."
      ],
      qa: [
        ["Did you stratify?", "No. We inherit the official QMSum partition by meeting, which keeps our numbers comparable with the literature. Because we did not stratify, we checked that the three splits have the same distributions, and they do (next slide)."],
        ["Why split by meeting?", "About eight queries share one transcript. A row-level split would put the same meeting on both sides."],
        ["Why leave the duplicate summaries in?", "They are upstream duplicates attached to different queries and transcripts (qmsum_train_69_g0 and qmsum_val_6_g0; qmsum_val_6_s2 and qmsum_test_30_s2). Removing them would change the published partition. They are 0.22% of rows and are disclosed."],
        ["Where is the split that picks the winner?", "data/splits/m1_session_v1/ is not prepared, because no sessions exist. Its rules are frozen in ADR-005: split by session_id, freeze files, facts, evidence links and hashes before the first comparative run."]
      ]
    },

    /* ================= 8 · 3.6 Data statistics ================= */
    {
      arc: 2, num: "3.6", kicker: "Data statistics", rubric: "3.6 Data Statistics", speaker: "Shriram", secs: 30,
      title: "Short summaries and skewed labels shaped our metrics",
      html: `
        <div class="card" style="display:grid;grid-template-columns:130px repeat(4,1fr);row-gap:4px;column-gap:16px;padding:12px 26px;margin-bottom:16px;font:600 20px var(--sans);align-items:baseline">
          <span></span>${["Raw", "Cleaned", "Transformed", "Prepared"].map((t, i) => `<span class="label" style="font-size:15px">${i ? "→ " : ""}${t}</span>`).join("")}
          <b style="font-weight:700">MAST</b><span>1,642 traces</span><span>1,638</span><span>1,638 × 26</span><span>1,638 + 4 human, eval only</span>
          <b style="font-weight:700">QMSum</b><span>232 meetings</span><span>232 · 0 removed</span><span>1,810 examples</span><span>1,257 / 272 / 281</span>
        </div>
        <div style="display:grid;grid-template-columns:520px 1fr 410px;gap:22px;height:468px">
          <div class="card" style="padding:22px 18px 0 22px"><div style="font:650 26px var(--display);margin:0 0 4px 6px">Summaries are short</div><div class="muted" style="font:500 18px var(--sans);margin:0 0 8px 6px">QMSum, % of rows · splits overlap</div>${histSVG()}</div>
          <div class="card" style="padding:22px 22px 0 26px"><div style="font:650 26px var(--display);margin-bottom:4px">Labels are imbalanced, about 28 : 1</div><div class="muted" style="font:500 18px var(--sans);margin-bottom:10px">MAST, share of 1,638 traces labelled positive</div>${barsSVG()}</div>
          <div class="card" style="padding:22px 18px 0 22px"><div style="font:650 26px var(--display);margin-bottom:4px">Labels co-occur</div><div class="muted" style="font:500 18px var(--sans);margin-bottom:10px">phi, all 91 pairs positive</div>${heatSVG()}</div>
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;display:flex;gap:12px;align-items:center">
          <span class="label" style="margin-right:8px">Coverage gaps</span>
          <span class="chip amber">English meetings only → other languages</span>
          <span class="chip amber">Agents only, no humans steering → our target users</span>
          <span class="chip amber">4 usable human traces → wide intervals</span>
        </div>`,
      say: [
        "The top strip summarizes all four stages. Three statistics shaped our metrics: summaries are short, about 65 words, so one missing fact matters; MAST labels range from 40 percent down to 1.5, so accuracy alone misleads; and failures come together.",
        "The bottom line shows the gaps: QMSum is English only, and MAST has no humans steering agents. So QMSum trains, but never picks the winner. Now, live."
      ],
      qa: [
        ["Who is disadvantaged by these gaps?", "Teams working in other languages, and teams whose sessions are terse tool calls and code. Users of under-represented MAST frameworks. And exactly our target teams, several humans steering agents, which MAST does not contain. That is why our own sessions, not QMSum, select the winner, and why results will state the population."],
        ["Correlation details?", "Phi from 0.04 to 0.66. Strongest: step repetition with unawareness of termination (1.3 and 1.5, 0.66), loss of history with conversation reset (1.4 and 2.1, 0.62). Trace length and failure count have Spearman 0.54, an association, not a cause."],
        ["Why does context length matter?", "Context is right-skewed: median about 660 words, 95th percentile over 10,000, because general queries take the whole meeting. A 4,096-token input truncates the tail, so 'truncated' is a failure code and latency is committed at p95 too."],
        ["Summary of the stages?", "Raw: MAST 1,642, QMSum 232 meetings. Pre-processed: 1,638 and 232. Transformed: 1,638 × 26 and 1,810 examples. Prepared: MAST 1,638 judge-labelled + 4 human-labelled, evaluation only; QMSum 1,257 / 272 / 281; smoke 12 / 3 / 3."],
        ["How do the charts relate to the workbook?", "They are drawn from the same committed files as Workbook Figures 6, 7 and 9: data/splits/m1_v1 and the MAST release."]
      ]
    },

    /* ================= 13 · 4.5 Pipeline demo ================= */
    {
      arc: 3, num: "4.5", kicker: "Data pipeline · live demo", rubric: "4.5 Data Pipeline Demo", speaker: "Shriram", secs: 25,
      title: "From source to warehouse, live, in about six seconds",
      html: `
        <div style="display:grid;grid-template-columns:230px 44px repeat(4, 1fr);gap:0 14px;align-items:stretch;height:330px">
          <div class="col" style="gap:14px">
            <div class="card" style="flex:1;padding:18px 20px;display:flex;flex-direction:column;justify-content:center"><div class="label">Source</div><div style="font:700 26px var(--display)">MAST</div><div class="mono muted" style="font-size:15px">pinned, SHA-256</div></div>
            <div class="card" style="flex:1;padding:18px 20px;display:flex;flex-direction:column;justify-content:center"><div class="label">Source</div><div style="font:700 26px var(--display)">QMSum</div><div class="mono muted" style="font-size:15px">pinned, SHA-256</div></div>
          </div>
          <div style="display:grid;place-items:center">${arrow(40)}</div>
          ${[["1", "download", "Ingest", "raw", "1,642 + 1,810 rows", "checksums verified, stored raw"], ["2", "filter", "Clean and validate", "staging", "1,638 traces · 22,932 labels", "a bad label stops the run"], ["3", "shuffle", "Transform", "marts", "3 fact + 4 dimension tables", "a star schema for analysis"], ["4", "shield", "Quality gates", "meta", "19 of 19 data checks pass", "expected vs actual, every run"]].map(([n, ic, h, layer, rows, what], i) =>
            `<div class="card" style="padding:24px 24px;display:flex;flex-direction:column;gap:12px;${i === 3 ? "background:var(--green-soft);border-color:#bfe5d4" : ""}">
              <div style="display:flex;align-items:center;gap:12px"><span class="callout" style="width:42px;height:42px;font-size:22px;${i === 3 ? "background:var(--green);box-shadow:none" : ""}">${n}</span><span style="color:${i === 3 ? "var(--green)" : "var(--blue)"}">${I(ic, 30)}</span></div>
              <div style="font:700 29px/1.1 var(--display)">${h}</div>
              <span class="chip ${i === 3 ? "green" : "blue"}" style="align-self:flex-start;font-family:var(--mono);font-size:17px">${layer}</span>
              <div style="font:500 19px/1.35 var(--sans);color:var(--mute)">${what}</div>
              <div style="margin-top:auto;font:600 20px/1.35 var(--sans);color:var(--ink2)">${rows}</div></div>`).join("")}
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;display:grid;grid-template-columns:1fr 1fr;gap:22px;height:290px">
          <div class="code" style="font-size:21px;line-height:1.6;display:flex;flex-direction:column;justify-content:center;padding:24px 32px">
            <span><span class="c">$</span> python infra/warehouse/pipeline.py</span>
            <span><span class="c">stage</span> ingest: <span class="n">success</span>    rows_out=3452</span>
            <span><span class="c">stage</span> clean: <span class="n">success</span>     rows_out=3448</span>
            <span><span class="c">stage</span> transform: <span class="n">success</span></span>
            <span><span class="n">[PASS]</span> × 19 data checks</span>
            <span><span class="c">run …</span> <span class="n">SUCCESS</span> in about 6 s</span>
            <span><span class="c">$</span> python infra/warehouse/pipeline.py --report</span>
          </div>
          <div class="card" style="padding:26px 30px;display:flex;flex-direction:column;gap:14px">
            <div style="display:flex;align-items:center;gap:12px">${I("gauge", 30)}<span style="font:700 28px var(--display)">Monitoring and management</span></div>
            <div style="font:600 21px/1.4 var(--sans)"><span class="mono" style="color:var(--blue)">meta.pipeline_runs</span> · every stage, every run: duration, rows in and out, status, git commit</div>
            <div style="font:600 21px/1.4 var(--sans)"><span class="mono" style="color:var(--blue)">meta.quality_checks</span> · expected vs actual for each gate</div>
            <div class="muted" style="font:600 19px var(--sans);margin-top:auto">Stops at the first failure · reruns rebuild the same warehouse</div>
          </div>
        </div>`,
      say: [
        "One command runs the whole pipeline: it ingests both datasets and verifies checksums, cleans and validates, builds a star schema in a local DuckDB warehouse, and runs nineteen quality checks.",
        "CUE: SWITCH TO THE TERMINAL. Run: python infra/warehouse/pipeline.py (about 6 seconds).",
        "Four stages, and all nineteen checks pass, in about six seconds.",
        "CUE: Run: python infra/warehouse/pipeline.py --report",
        "And this is our monitoring: every run, every stage, with duration, rows in and out, status and git commit. Over to Ayush.",
        "CUE: If it fails live, open infra/warehouse/SAMPLE_RUN.md and walk through the saved output. Do not debug in front of the room."
      ],
      qa: [
        ["What if a stage fails?", "The run stops at that stage, the failure is written to the run history with the error, and the exit code is non-zero. Tables are replaced on each run, so a rerun after a fix gives the same warehouse as a clean run."],
        ["What is in the warehouse?", "Raw: 1,642 traces and 1,810 examples. Staging: 1,638 clean traces, 22,932 label rows, 1,810 clean examples. Marts: fact_trace 1,638, fact_trace_failure 5,141, fact_m1_example 1,810, and four dimensions (failure mode 14, framework 7, LLM 5, benchmark 8)."],
        ["Does your own session data flow into it?", "Not yet. No session has been recorded, so the export from the PostgreSQL event log is the one ingestion path that does not exist. It is in the carry-forward table."],
        ["Why no Airflow or cloud warehouse? (talk only)", "Static pinned data, four stages in a line, about 220 MB, about 6 seconds on a laptop. A scheduler would be idle; a cloud warehouse adds cost, credentials and latency and no capability, and makes the pipeline unverifiable without our accounts. First step up when ingestion becomes recurring: a scheduled GitHub Actions job."],
        ["Is this rubric 4.5 the same as report section 4.5?", "No. The live pipeline demo is the meeting's 4.5. In the report template, 4.5 First Model Implementation and 4.6 Baseline Reproduction are intentionally empty until the final report, because no model is trained and the judge has not been run."],
        ["Are the 19 checks model metrics?", "No. They are data-quality gates (counts, keys, label domains, reconciliation between layers). No model is involved in the pipeline."],
        ["Before the meeting", "On the demo laptop: git pull, pip install -r requirements.txt, python data/scripts/download_mast.py once (about 200 MB), run the pipeline once so the demo shows two runs, terminal font large."]
      ]
    },

    /* ================= 9 · 4.1 Model proposals ================= */
    {
      arc: 4, num: "4.1", kicker: "Model proposals", rubric: "4.1 Model Proposals", flag: "Plan, committed before training", speaker: "Ayush", secs: 35,
      title: "Four models, sixteen candidates, one reproduced baseline",
      html: `
        <div class="card" style="position:absolute;left:0;top:0;width:800px;bottom:0;padding:32px 36px;display:flex;flex-direction:column;gap:16px;border:2px solid #c8d0ff">
          <div style="display:flex;align-items:center;gap:16px"><div class="icwrap">${I("clock", 34)}</div><div><div class="label">Model 1 · this semester</div><div style="font:700 40px var(--display)">Catch-up for a late joiner</div></div></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            ${[["BM25", "lexical ranker · no training", true], ["ModernBERT", "149M encoder · picks events", false], ["Phi-4-mini", "3.8B decoder · 4-bit QLoRA", false], ["Qwen3.5-4B", "4B · 4-bit QLoRA", false]].map(([n, d, c]) =>
              `<div style="border-radius:12px;padding:10px 14px;${c ? "background:var(--ink);color:#fff" : "background:#f0eee8"}"><div style="font:700 21px var(--sans)">${n}</div><div style="font:500 16px var(--sans);opacity:0.7">${d}</div></div>`).join("")}
          </div>
          <div style="flex:1;background:var(--paper);border-radius:18px;padding:20px 24px;display:flex;flex-direction:column;justify-content:center;gap:12px;position:relative">
            <span class="chip amber" style="position:absolute;right:16px;top:14px;font-size:15px;padding:4px 10px">example of the output format</span>
            <div style="display:flex;gap:10px;align-items:center;font:600 21px var(--sans)">${I("user", 24)}“Catch me up on what happened while I was away.”</div>
            <div class="card" style="padding:16px 20px;display:flex;gap:14px;align-items:center;border-color:#c8d0ff">
              <span class="chip red" style="font-size:16px">BLOCKED</span><span style="font:600 21px var(--sans)">test_large_payload is blocked on the archive fixture</span>
            </div>
            <div style="display:flex;gap:10px;align-items:center;color:var(--blue);font:600 19px var(--sans);padding-left:8px">${I("link", 22)}cites events <span class="pill on" style="font-family:var(--mono)">e011</span><span class="pill on" style="font-family:var(--mono)">e012</span></div>
            <div class="mono" style="font-size:16px;line-height:1.7;color:var(--ink2);padding-left:8px">
              <div><b style="color:var(--blue)">e011</b> tool_result · 4 passed, 1 failed: test_large_payload…</div>
              <div><b style="color:var(--blue)">e012</b> agent_step · needs the archive fixture, only Omar…</div>
            </div>
            
          </div>
          <div class="strip blue" style="font-size:22px;padding:16px 22px">${I("spark", 28)}New: every claim must cite its events. No evidence, no claim.</div>
        </div>
        <div style="position:absolute;left:830px;right:0;top:0;bottom:0;display:flex;flex-direction:column;justify-content:space-between">
          ${[["target", "Model 2 · Who is it for?", "Instruction, mentions, roles → a score per participant", ["TF-IDF", "DeBERTaV3", "ModernBERT", "Qwen head"]],
             ["merge", "Model 3 · Arbitration", "Two conflicting instructions → accept A, B, merge or escalate", ["Last writer wins", "ModernBERT", "Qwen LoRA", "Few-shot Qwen"]],
             ["route", "Model 4 · Decompose and route", "Task, skills, workload → a task graph, each part assigned", ["Rules", "Planner + router", "Planner", "Single prompt"]]].map(([ic, h, p, c]) =>
            `<div class="card" style="padding:20px 24px;display:flex;gap:18px;align-items:flex-start">
              <div class="icwrap" style="background:#f0eee8;color:var(--ink2)">${I(ic, 30)}</div>
              <div style="flex:1"><div style="display:flex;align-items:baseline;gap:12px"><span style="font:700 27px var(--display)">${h}</span><span class="label" style="margin-left:auto">298B · next term</span></div>
              <div class="muted" style="font:500 19px var(--sans);margin:4px 0 10px">${p}</div>
              <div style="display:flex;gap:6px;flex-wrap:wrap">${c.map((x, k) => `<span class="pill${k === 0 ? " ctl" : ""}">${x}</span>`).join("")}</div></div></div>`).join("")}
          <div class="card" style="padding:22px 24px;border:2px dashed #9a9ca3;background:transparent;display:flex;gap:18px;align-items:center">
            <div class="icwrap ink">${I("eye", 30)}</div>
            <div><div style="font:700 25px var(--display)">Baseline · MAST LLM judge, reproduced</div>
            <div class="muted" style="font:500 19px var(--sans);margin-top:4px">Paper (o1, few-shot): accuracy 0.94 · F1 0.80 · kappa 0.77. Not one of the four.</div></div>
          </div>
          <div style="display:flex;gap:10px;align-items:center"><span class="pill ctl">dark</span><span class="muted" style="font:500 18px var(--sans)">= the simple control each model must beat</span></div>
        </div>`,
      say: [
        "Section four, the models. Four models, one per coordination problem. Model 1, this semester, catches up someone who joins late. Model 2 finds who an instruction is for. Model 3 handles two people redirecting one agent. Model 4 splits and routes a task.",
        "Each is a bake-off of four candidates, starting from a simple control. The MAST judge is our separate baseline.",
        "What's new: every Model 1 claim must cite the events that prove it, like the blocked test shown here."
      ],
      qa: [
        ["Which model is innovative, and why?", "Model 1. Three things: evidence-cited output by construction (a claim without a valid event id is invalid, not low-scoring); selection that is safety-gated before it is quality-ranked; and approved memory that can change how it writes but can never be used as evidence."],
        ["Architectures, briefly?", "m1-a Okapi BM25 ranks events and fills a template, no parameters, CPU. m1-b ModernBERT-base, 149M-parameter encoder with 8,192-token context, fine-tuned as a relevance scorer, same template. m1-c Phi-4-mini, 3.8B decoder, 4-bit NF4 QLoRA, writes the JSON directly. m1-d Qwen3.5-4B, 4-bit NF4, LoRA r 16, alpha 32."],
        ["Why QLoRA and small models?", "One 16 GB GPU in the university lab, at zero cost. 4-bit quantisation with adapters fits, and adapter-only checkpoints survive an interrupted session."],
        ["Has any candidate been trained?", "No. ModernBERT ran a 40-step feasibility smoke on the GPU with checkpoint and resume. That is not a result and is not in the workbook as one."],
        ["Why is the baseline separate?", "It is the external reference that tells us whether our prompt, parser, batch runner and metric code can recover a published number. None of our models claims to improve on it. Prompt mast-judge-v1, parser mast-parser-v1.1, batch runner, provenance and metrics are on main; the judge has not been run."],
        ["Why pairwise for Model 2?", "The roster changes from session to session; scoring one (instruction, participant) pair at a time works for any roster."],
        ["Models 2 to 4 in more detail?", "M2: instruction text, explicit mentions, each participant's role and recent activity; TF-IDF with a linear classifier vs DeBERTaV3 and ModernBERT cross-encoders vs a Qwen classification head. M3: both instructions, authors, roles, timing, document state; last-writer-wins vs ModernBERT pairwise cross-encoder vs Qwen3.5-4B LoRA with a four-way head vs few-shot Qwen; escalation is a first-class output. M4: task text, skills, workload, cost; rules-only vs LLM planner with a LightGBM router vs planner alone vs single prompt; an invalid task graph is rejected before any metric. M3 configs are committed (eval/configs/m3-a to m3-d); M2 and M4 configs come at the start of 298B."]
      ]
    },

    /* ================= 10 · 4.2 Model supports ================= */
    {
      arc: 4, num: "4.2", kicker: "Model supports", rubric: "4.2 Model Supports", flag: "Plan, committed before training", speaker: "Ayush", secs: 25,
      title: "One local stack, one lab GPU, frozen interfaces",
      html: platformSVG(),
      say: [
        "This is the platform. Top: the session layer from the prototype, ending in the event log. Middle: the agent runtime, and one prediction endpoint per model, ready to serve each winner once it is chosen.",
        "Bottom: the ML flow. Data into the warehouse, frozen splits, training on one 16-gigabyte lab GPU, and one shared evaluation harness. All local, all free, every change through CI."
      ],
      qa: [
        ["Why not AWS or Airflow? (talk only, not on slides)", "We evaluated both and chose not to adopt them in 298A. Our two datasets are static and pinned, so nothing is scheduled. The pipeline is four steps in a straight line and runs in about six seconds on a laptop, about 220 MB raw. Training is free on the university GPU. We adopt them when the workload asks: when sessions are recorded more often than weekly (a nightly export becomes a real schedule) and when people outside the team join the 298B study. Details: docs/reports/T4-TA-aws-airflow-justification.md."],
        ["Then how do you monitor the pipeline?", "Every run writes 19 quality checks and a per-stage run history (start, duration, rows in and out, status, git commit) into the warehouse. Pipeline tests run in CI on every pull request, so a broken stage is a red check and an email to its author."],
        ["Why not at least run Airflow locally?", "It needs a metadata database, a scheduler and a web server to run four functions on data that never changes. Each stage is a plain function, so wrapping it in an Airflow task later is mechanical. The first step up will be a scheduled GitHub Actions job."],
        ["How would it map to AWS later?", "Raw files to S3, stage functions to Airflow tasks, DuckDB schemas to Redshift or Athena. The checkpoint utility already accepts remote URIs such as s3:// (PR #32)."],
        ["Environment and tools per model?", "Python 3.11; PyTorch with CUDA, Transformers, PEFT, bitsandbytes 4-bit NF4; scikit-learn for the TF-IDF control; LangGraph and LightGBM for Model 4; the MAST baseline needs no GPU (API inference). Checkpoints every 200 steps through one shared utility."],
        ["Is DuckDB really a data warehouse?", "It is a columnar analytical database. We use it with raw, staging and marts layers and a star schema: four dimensions and three fact tables."],
        ["Why frozen interfaces?", "Components owned by different people talk only through a network call or a committed file format, never shared memory, so five people build in parallel. Interface changes need an ADR first."]
      ]
    },

    /* ================= 11 · 4.3 Comparison ================= */
    {
      arc: 4, num: "4.3", kicker: "Model comparison and justification", rubric: "4.3 Comparison and Justification", flag: "Plan, committed before training", speaker: "Ayush", secs: 30,
      title: "Each Model 1 candidate tests one idea",
      html: `
        <div style="position:absolute;left:0;top:0;width:1110px;bottom:0;display:grid;grid-template-columns:repeat(4,1fr);gap:16px;align-items:end">
          ${[["Statistics", "BM25", "the floor", "CPU · no training", false, 470, "explainable, no GPU", "misses paraphrase"],
             ["Deep learning · extractive", "ModernBERT", "+ learned relevance", "149M · fine-tuned", false, 530, "matches meaning, not just words", "weak labels, cannot summarise"],
             ["Deep learning · generative", "Phi-4-mini", "+ generation", "3.8B · 4-bit QLoRA", true, 600, "concise state, low memory", "may emit invalid JSON"],
             ["Deep learning · generative", "Qwen3.5-4B", "+ capacity", "4B · 4-bit QLoRA", true, 668, "most capacity for recall", "slowest, largest"]].map(([fam, name, adds, hw, gen, h, plus, minus], i) =>
            `<div class="card" style="height:${h}px;padding:22px 20px;display:flex;flex-direction:column;gap:10px;${i ? "" : "background:var(--ink);color:#fff;border-color:var(--ink)"}">
              <span class="chip ${i ? "blue" : ""}" style="align-self:flex-start;font-size:18px;${i ? "" : "background:#2a2d36;color:#fff"}">${adds}</span>
              <div style="font:700 34px/1.05 var(--display);margin-top:6px">${name}</div>
              <div style="font:600 17px var(--sans);letter-spacing:0.06em;text-transform:uppercase;opacity:0.6">${fam}</div>
              <div class="mono" style="font-size:17px;opacity:0.75">${hw}</div>
              <div style="margin-top:14px;font:500 19px/1.35 var(--sans);opacity:0.85"><b style="color:${i ? "var(--green)" : "#7fe0b8"}">+</b> ${plus}</div>
              <div style="font:500 19px/1.35 var(--sans);opacity:0.85"><b style="color:${i ? "var(--red)" : "#ff9e86"}">−</b> ${minus}</div>
              <div style="margin-top:auto;display:flex;flex-direction:column;gap:8px;font:600 19px var(--sans)">
                <div style="display:flex;align-items:center;gap:8px;color:${gen ? "var(--red)" : i ? "var(--green)" : "#7fe0b8"}">${I(gen ? "alert" : "check", 22, 2.4)}${gen ? "can invent a claim" : "cannot invent"}</div>
                <div style="display:flex;align-items:center;gap:8px;color:${gen ? "var(--green)" : i ? "var(--mute)" : "#9aa0ac"}">${I(gen ? "check" : "x", 22, 2.4)}${gen ? "merges events" : "copies events"}</div>
              </div></div>`).join("")}
        </div>
        <div style="position:absolute;left:1140px;right:0;top:0;bottom:0;display:flex;flex-direction:column;gap:18px">
          <div class="card" style="padding:26px 28px;background:var(--ink);color:#fff;border-color:var(--ink)">
            <div class="label" style="color:#9aa0ac">Preference, stated before any result</div>
            <div style="font:700 32px/1.15 var(--display);margin:8px 0 6px">A generative model</div>
            <div style="font:500 19px/1.4 var(--sans);color:#c9ccd4">A catch-up must merge events and give each a status.</div>
          </div>
          <div class="card" style="padding:24px 28px;flex:1">
            <div class="label" style="color:var(--red)">It loses if, on the session test split</div>
            ${["It invents a claim on any one seed", "It only ties BM25 on recall: the faster model wins", "Too few sessions to learn the status labels", "Nothing passes: BM25 stays in service"].map((t) =>
              `<div style="display:flex;gap:12px;align-items:flex-start;margin-top:16px;font:600 22px/1.3 var(--sans)"><span style="color:var(--red);margin-top:2px">${I("x", 24, 2.6)}</span>${t}</div>`).join("")}
          </div>
          <div class="card" style="padding:20px 24px">
            <div class="label">Models 2 to 4 must beat a control</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px"><span class="pill ctl">TF-IDF + linear</span><span class="pill ctl">Last writer wins</span><span class="pill ctl">Rules router</span></div>
          </div>
        </div>`,
      say: [
        "Each Model 1 candidate tests one idea. BM25 is the floor, no training. ModernBERT adds learned relevance. Phi-4-mini adds writing. Qwen adds capacity. The first two only copy events, so they can't invent; the last two can merge events, but can also invent.",
        "We prefer a generative model, and we've written down when it loses: if it invents a claim on any seed, or only ties BM25. Pramod has the rules."
      ],
      qa: [
        ["Why this matrix?", "Each neighbouring pair isolates one question. m1-a to m1-b holds the template fixed and changes only the ranker. m1-b to m1-c moves from copying to writing: the value and the risk of generation. m1-c to m1-d holds the method fixed and changes capacity. Unrelated models would tell us which scored highest, not why."],
        ["Strengths and limitations?", "BM25: cannot invent a claim, no GPU, fully explainable; misses paraphrase. ModernBERT: better relevance when wording differs; weak labels from QMSum, cannot summarise across events. Phi-4-mini: concise state at low memory; may emit invalid JSON or unsupported claims. Qwen3.5-4B: most capacity; slowest, same generative risks."],
        ["Approaches across all models?", "Statistics (BM25, rules, last writer wins), classical ML (TF-IDF with a linear classifier, gradient-boosted router), and deep learning (encoders, QLoRA and LoRA generators, few-shot prompting). Each learned arm is only interesting if it beats its control."],
        ["Phi-4-mini or Qwen?", "No preference. Qwen loses to Phi-4-mini whenever recall is within the margin, because the smaller model is faster."],
        ["What if nothing passes?", "ADR-005 requires us to report that no model is promotable and keep the extractive control in service while failures are corrected."],
        ["Models 2 to 4: strengths and limits?", "M2: cheap per-event inference, per-class F1 exposes weak classes; bounded by annotator agreement. M3: can escalate instead of guessing, rule control is easy to audit; conflicts are rare, so data is scarce and partly synthetic. M4: the DAG-validity gate stops malformed plans early; plans are costly to label and planner quality is prompt-sensitive. Baseline: a published target, inference only; only 4 human-labelled traces use the current taxonomy, which limits the precision of any agreement figure."],
        ["What is the tie margin?", "Critical-fact recall within 0.01. The tie passes to BERTScore-F1 and ROUGE-L, then latency at p95 and peak memory, where BM25 on a CPU wins."]
      ]
    },

    /* ================= 12 · 4.4 Evaluation ================= */
    {
      arc: 4, num: "4.4", kicker: "Model evaluation methods", rubric: "4.4 Evaluation Methods", flag2: "Committed 22 Oct · ADR-005", speaker: "Pramod", secs: 30,
      title: "Safety first, then quality, committed before any result",
      html: `
        <div style="display:grid;grid-template-columns:230px 40px 230px 40px 560px 40px 1fr;align-items:stretch;height:450px">
          <div class="card tile" style="justify-content:center"><div class="mid">4 × 3</div><h3 style="font-size:24px">candidates × seeds</h3><p>seeds 13, 29, 47</p></div>
          <div style="display:grid;place-items:center">${arrow(34)}</div>
          <div class="card tile" style="justify-content:center"><div class="icwrap">${I("check", 32, 2.4)}</div><h3 style="font-size:24px">All 3 seeds finish</h3><p>otherwise out</p></div>
          <div style="display:grid;place-items:center">${arrow(34)}</div>
          <div class="card" style="padding:24px 28px;background:var(--amber-soft);border-color:#f2d6a8">
            <div style="display:flex;align-items:center;gap:12px;color:var(--amber-ink)">${I("shield", 30)}<span style="font:700 26px var(--display)">Safety gates, on every seed</span></div>
            ${[["≤ 2%", "unsupported claims, and no worse than BM25"], ["≥ 95%", "claims cite the right event"], ["≥ 95%", "status is right (blocked is not done)"], ["≥ 98%", "outputs are valid JSON"]].map(([v, t]) =>
              `<div style="display:flex;align-items:baseline;gap:16px;margin-top:20px"><span style="font:700 44px var(--display);color:var(--amber-ink);min-width:128px">${v}</span><span style="font:600 20px var(--sans);color:var(--ink2)">${t}</span></div>`).join("")}
          </div>
          <div style="display:grid;place-items:center">${arrow(34)}</div>
          <div class="card" style="padding:24px 28px;display:flex;flex-direction:column;gap:12px">
            <div class="label">Then rank</div>
            ${["Critical-fact recall", "BERTScore-F1", "ROUGE-L"].map((t, i) => `<div style="display:flex;align-items:center;gap:12px"><span class="callout" style="width:38px;height:38px;font-size:20px;${i ? "background:#9aa0ac;box-shadow:none" : ""}">${i + 1}</span><span style="font:${i ? 600 : 700} ${i ? 21 : 24}px var(--sans)">${t}</span></div>`).join("")}
            <div style="margin-top:auto;font:600 19px/1.35 var(--sans);color:var(--mute)">Blind human review of the top two. Nothing passes → nothing promoted.</div>
          </div>
        </div>
        <div class="label" style="position:absolute;left:0;bottom:142px">Every other model has its metric fixed too</div>
        <div style="position:absolute;left:0;right:0;bottom:0;display:grid;grid-template-columns:repeat(4,1fr);gap:18px">
          ${[["Model 2", "macro-F1, per-class F1"], ["Model 3", "macro-F1 · harmful-merge rate · escalation P/R"], ["Model 4", "valid plan (gate) → routing accuracy, cost"], ["Baseline", "accuracy · P · R · F1 · kappa, 95% CI"]].map(([m, t]) =>
            `<div class="card" style="padding:20px 24px"><div class="label">${m}</div><div style="font:600 21px/1.35 var(--sans);margin-top:8px">${t}</div></div>`).join("")}
        </div>
        `,
      say: [
        "These rules were committed on October 22nd, before any result. Each candidate runs three seeds and must pass every safety gate on every seed: at most two percent unsupported claims, 95 percent right evidence and status, 98 percent valid output.",
        "Only then do we rank: critical-fact recall, then BERTScore, then ROUGE. If nothing passes, nothing is promoted. Models 2 to 4 have their metrics fixed too."
      ],
      qa: [
        ["Why is ROUGE-L not the primary metric?", "Summaries are about 65 words. A summary can score well on overlap and still omit the one blocker, or assign an action to the wrong person. ROUGE-L is still reported (on QMSum test against the 28.2 reference floor) and still breaks ties, after the gates."],
        ["Why three seeds, and why per seed?", "Seeds 13, 29 and 47. We report each seed, the mean and a 95% interval, never pooled. Gates apply per seed so one unsafe run cannot hide behind two good ones."],
        ["Metrics for the other models?", "M2: macro-F1 with per-class F1. M3: macro-F1, harmful-merge rate, escalation precision and recall, against last writer wins. M4: DAG validity as a gate, then routing accuracy, completion, latency and cost. Baseline: accuracy, precision, recall, F1 and Cohen's kappa against the 4 human-labelled traces in the current taxonomy, with sample size and 95% interval; agreement with released judge labels on 1,638 traces is a pipeline check, never reported as a reproduction."],
        ["Is the harness finished?", "No. It is in review (DAT-61, PR #25). Review found the comparison step applying gates to the three-seed mean, which the contract forbids, so it is being fixed before merge; target 18 November."],
        ["How does the human review work?", "The top two candidates that pass the gates get a blinded review; the metric is human edit rate, the token edits a reviewer needs to make an output acceptable (committed in ADR-005)."],
        ["What does a candidate with zero claims score?", "It fails recall, and its attribution accuracy is recorded as zero by contract convention, so silence cannot win the safety gates."],
        ["What else is evaluated?", "An ablation over context budget (512, 1,024, 2,048 tokens) and memory on or off, and every failure gets one of seven frozen failure codes for the failure analysis."]
      ]
    },

    /* ================= 14 · Next ================= */
    {
      arc: 5, num: "", kicker: "What we do next", rubric: "Next steps · carry-forward", speaker: "Pramod", secs: 25,
      title: "Next: our own sessions, then the Model 1 bake-off",
      html: `
        <div class="tl" style="left:0;right:0;top:20px">
          <div class="track" style="left:4%;right:4%"></div>
          <div class="seg" style="left:4%;width:92%;background:repeating-linear-gradient(90deg,var(--amber) 0 14px,transparent 14px 26px)"></div>
          ${[[4, "12 Nov", "Today", "", "now"], [68, "2 Dec", "First sessions · MAST judge runs", "Naman · Ayush, Shriram", "next"], [96, "7–8 Dec", "Final report, presentation", "Ayush", "next"]].map(([p, d, w, o, c]) =>
            `<div class="node${p > 90 ? " end" : ""}" style="left:${p}%"><div class="pw"><div class="pin ${c}"></div></div><div class="date">${d}</div><div class="what">${w}</div><div class="muted" style="font:500 19px var(--sans);margin-top:2px">${o}</div></div>`).join("")}
        </div>
        <div style="position:absolute;left:0;right:0;top:250px">
          <div class="label" style="margin-bottom:14px;color:var(--blue)">Path to the Model 1 winner</div>
          <div style="display:flex;align-items:center;gap:12px">
            ${["Record sessions", "Annotate facts", "Freeze session split", "Bake-off, 3 seeds", "Pick the winner"].map((t, i) =>
              `<div class="card" style="flex:1;padding:30px 24px;min-height:150px;${i === 4 ? "background:var(--ink);color:#fff;border-color:var(--ink)" : ""}"><div style="font:700 25px/1.15 var(--display)">${t}</div></div>${i < 4 ? arrow(30) : ""}`).join("")}
          </div>
        </div>
        <div style="position:absolute;left:0;bottom:0;display:flex;gap:12px;align-items:center">
          <span class="label" style="margin-right:6px">298B</span><span class="chip">Models 2 to 4</span><span class="chip">Cloud deployment</span><span class="chip">Controlled study</span>
        </div>
        <div style="position:absolute;right:0;bottom:-10px;text-align:right"><div style="font:720 104px/1 var(--display);letter-spacing:-0.035em">Thank you<span style="color:var(--blue)">.</span></div><div class="muted" style="font:600 26px var(--sans);margin-top:8px">Questions welcome</div></div>`,
      say: [
        "Next: the evaluation harness was merged yesterday. Now we record and annotate our own sessions, run the MAST judge, and run the Model 1 bake-off.",
        "Our own sessions are the next big step, because they decide every winner. Our target for the final report on December 7th is the Model 1 bake-off and the MAST reproduction. Thank you. Questions?"
      ],
      qa: [
        ["What is your biggest risk?", "The session corpus. Sessions need the end-to-end integration gate, annotation needs sessions, splits need annotation. If it slips, we shorten collection, not the freeze date."],
        ["What if the MAST baseline does not reproduce?", "Check the prompt and scoring code before the model. The paper's zero-shot figure is 0.89, so few-shot matters. MultiAgentBench is the documented fallback. If the gap stays, we report it."],
        ["Who does what?", "Ayush: platform, serving, Model 1. Naman: data, Model 2. Manav: client, Model 3. Shriram: agent runtime, Model 4. Pramod: evaluation and the MAST baseline."],
        ["What else is open?", "GPU feasibility for Phi-4-mini (failed at step 2 of 15, likely memory at 4,096 tokens) and Qwen3.5-4B (not run); branch protection on main (DAT-10, target 18 Nov); Model 2 and 4 config files at the start of 298B."],
        ["Will outside participants be recruited?", "The first sessions come from the five of us. We widen recruitment only after the IRB question is answered, and every result states its population."]
      ]
    }
  ];
})();
