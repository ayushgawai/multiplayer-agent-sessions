/* Keeps the audience window and the presenter window on the same slide. */
(function () {
  const KEY = "t4-wb2-slide";
  const CH = "t4-wb2";
  const deck = window.DECK;
  let index = Number(localStorage.getItem(KEY) || 0);
  if (!Number.isFinite(index) || index < 0 || index >= deck.length) index = 0;

  const channel = ("BroadcastChannel" in window) ? new BroadcastChannel(CH) : null;
  const isPresenter = document.body.classList.contains("presenter");

  function show(i, broadcast) {
    index = (i + deck.length) % deck.length;
    localStorage.setItem(KEY, String(index));
    const slide = deck[index];
    if (isPresenter) {
      document.getElementById("notes").innerHTML = slide.notes.map((p) => `<p>${p}</p>`).join("");
      document.getElementById("meta").textContent = `${index + 1} / ${deck.length}  ·  ${slide.rubric}`;
      document.getElementById("next").textContent = deck[(index + 1) % deck.length].title;
      const preview = document.getElementById("preview");
      preview.innerHTML = `<div class="stage">${slide.html}</div>`;
    } else {
      document.getElementById("stage").innerHTML = slide.html;
    }
    if (broadcast && channel) channel.postMessage({ index });
  }

  if (channel) {
    channel.onmessage = (event) => {
      if (event.data && typeof event.data.index === "number") show(event.data.index, false);
    };
  }
  window.addEventListener("storage", (event) => {
    if (event.key === KEY && event.newValue != null) show(Number(event.newValue), false);
  });

  document.addEventListener("keydown", (event) => {
    if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) {
      event.preventDefault();
      show(index + 1, true);
    } else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(event.key)) {
      event.preventDefault();
      show(index - 1, true);
    } else if (event.key === "Home") {
      show(0, true);
    } else if (event.key === "End") {
      show(deck.length - 1, true);
    }
  });

  const openBtn = document.getElementById("open-audience");
  if (openBtn) {
    openBtn.addEventListener("click", () => {
      window.open("audience.html", "t4-wb2-audience", "noopener");
      show(index, true);
    });
  }

  let started = Date.now();
  const timer = document.getElementById("timer");
  if (timer) {
    setInterval(() => {
      const s = Math.floor((Date.now() - started) / 1000);
      const m = String(Math.floor(s / 60)).padStart(2, "0");
      const r = String(s % 60).padStart(2, "0");
      timer.textContent = `${m}:${r}`;
    }, 1000);
  }

  show(index, false);
  window.T4 = { show: (i) => show(i, true), deck };
})();
