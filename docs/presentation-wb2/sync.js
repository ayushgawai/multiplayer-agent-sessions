/* Deck runtime, shared by audience.html, presenter.html and render.html.
   - draws each slide on a fixed 1920x1080 stage and scales it to fit (letterboxed)
   - keeps the audience and presenter windows on the same slide
     (BroadcastChannel, with localStorage "storage" events as a fallback)
   - keys: right/space/PageDown next, left/PageUp back, Home/End, F fullscreen; click advances */
(function () {
  const W = 1920, H = 1080;
  const KEY = "t4-wb2-slide", CH = "t4-wb2";
  const ARC = ["Recap", "Built", "Data", "Demo", "Models", "Next"];
  const deck = window.DECK, N = deck.length;
  const mode = document.body.dataset.mode; // audience | presenter | render

  function frame(s, i) {
    const arc = ARC.map((a, k) => `<span class="${k === s.arc ? "on" : k < s.arc ? "done" : ""}">${a}</span>`).join("");
    const head = s.bare ? "" :
      `<header class="hd"><div class="kicker">${s.num ? `<span class="num">${s.num}</span>` : ""}<span class="kicker-text">${s.kicker}</span>${s.flag ? `<span class="flag">${s.flag}</span>` : ""}${s.flag2 ? `<span class="flag ink">${s.flag2}</span>` : ""}</div><h1>${s.title}</h1></header>`;
    return `<div class="slide">${head}${s.bare ? s.html : `<div class="body">${s.html}</div>`}
      <footer class="ft"><div class="arc">${arc}</div><div class="rub">${s.rubric}</div>
      <div class="spk">${s.speaker}</div><div class="ctr">${String(i + 1).padStart(2, "0")} / ${N}</div></footer></div>`;
  }

  function fit(stage, box) {
    const w = box.clientWidth, h = box.clientHeight, k = Math.min(w / W, h / H);
    stage.style.transform = `translate(${(w - W * k) / 2}px, ${(h - H * k) / 2}px) scale(${k})`;
  }

  function paint(stage, i, animate) {
    stage.innerHTML = frame(deck[i], i);
    if (animate) { stage.classList.remove("fade"); void stage.offsetWidth; stage.classList.add("fade"); }
  }

  /* ---- render.html: one slide, no chrome, no motion ---- */
  if (mode === "render") {
    const i = Math.max(0, Math.min(N - 1, Number(new URLSearchParams(location.search).get("i") || 0)));
    const stage = document.getElementById("stage"), vp = document.getElementById("vp");
    paint(stage, i, false); fit(stage, vp);
    addEventListener("resize", () => fit(stage, vp));
    return;
  }

  let index = Number(localStorage.getItem(KEY) || 0);
  if (!Number.isInteger(index) || index < 0 || index >= N) index = 0;
  const channel = "BroadcastChannel" in window ? new BroadcastChannel(CH) : null;
  const boxes = []; // [stage, container] pairs to refit on resize
  const refit = () => boxes.forEach(([s, b]) => fit(s, b));
  addEventListener("resize", refit);

  let slideStart = Date.now();

  function show(i, broadcast) {
    const prev = index;
    index = Math.max(0, Math.min(N - 1, i));
    if (index !== prev || !show.done) slideStart = Date.now();
    try { localStorage.setItem(KEY, String(index)); } catch (e) { /* private window: channel still works */ }
    const s = deck[index];
    if (mode === "audience") {
      paint(document.getElementById("stage"), index, show.done && index !== prev);
    } else {
      paint(document.getElementById("cur"), index, false);
      const nx = deck[index + 1];
      if (nx) paint(document.getElementById("nxt"), index + 1, false);
      else document.getElementById("nxt").innerHTML = "";
      document.getElementById("nxt-title").textContent = nx ? nx.title.replace(/<[^>]+>/g, "") : "End of deck";
      document.getElementById("nxt-who").textContent = nx ? `${nx.speaker} · about ${nx.secs} s` : "";
      document.getElementById("meta").textContent = `Slide ${index + 1} / ${N}`;
      document.getElementById("rubric").textContent = s.rubric;
      document.getElementById("who").textContent = `${s.speaker.toUpperCase()} · about ${s.secs} s`;
      document.getElementById("say").innerHTML = s.say.map((p) =>
        p.startsWith("CUE:") ? `<div class="cue">${p.slice(4).trim()}</div>` : `<p>${p}</p>`).join("");
      document.getElementById("qa").innerHTML = s.qa.map(([q, a]) =>
        `<div class="qa"><b>If asked: ${q}</b><span>${a}</span></div>`).join("");
      document.getElementById("notes").scrollTop = 0;
      refit();
    }
    show.done = true;
    if (broadcast && channel) channel.postMessage({ index });
  }

  if (channel) channel.onmessage = (e) => { if (e.data && Number.isInteger(e.data.index)) show(e.data.index, false); };
  addEventListener("storage", (e) => { if (e.key === KEY && e.newValue != null) show(Number(e.newValue), false); });

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => {});
  }

  document.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) { e.preventDefault(); show(index + 1, true); }
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) { e.preventDefault(); show(index - 1, true); }
    else if (k === "Home") show(0, true);
    else if (k === "End") show(N - 1, true);
    else if (k === "f" || k === "F") toggleFullscreen();
  });

  if (mode === "audience") {
    const stage = document.getElementById("stage"), vp = document.getElementById("vp");
    boxes.push([stage, vp]);
    vp.addEventListener("click", () => show(index + 1, true));
    vp.addEventListener("contextmenu", (e) => { e.preventDefault(); show(index - 1, true); });
    document.addEventListener("fullscreenchange", refit);
    // hide the cursor and the key hint when idle
    const hint = document.getElementById("hint");
    let idle;
    const wake = () => {
      document.body.classList.remove("idle"); hint.classList.add("show");
      clearTimeout(idle); idle = setTimeout(() => { document.body.classList.add("idle"); hint.classList.remove("show"); }, 2200);
    };
    addEventListener("mousemove", wake); wake();
  } else {
    boxes.push([document.getElementById("cur"), document.getElementById("cur-box")]);
    boxes.push([document.getElementById("nxt"), document.getElementById("nxt-box")]);
    document.getElementById("open-audience").addEventListener("click", () => {
      window.open("audience.html", "t4-wb2-audience");
      setTimeout(() => show(index, true), 600);
    });
    document.getElementById("btn-prev").addEventListener("click", () => show(index - 1, true));
    document.getElementById("btn-next").addEventListener("click", () => show(index + 1, true));
    let started = Date.now();
    document.getElementById("reset").addEventListener("click", () => { started = Date.now(); slideStart = Date.now(); });
    const mmss = (ms) => { const s = Math.floor(ms / 1000); return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
    setInterval(() => {
      document.getElementById("timer").textContent = mmss(Date.now() - started);
      const on = Date.now() - slideStart, el = document.getElementById("slide-timer");
      el.textContent = `this slide ${mmss(on)} of ~${deck[index].secs}s`;
      el.classList.toggle("over", on / 1000 > deck[index].secs + 5);
    }, 500);
  }

  show(index, false);
  refit();
  window.T4 = { show: (i) => show(i, true), deck, frame, get index() { return index; } };
})();
