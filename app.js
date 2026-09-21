const NETWORKS = [
  {
    id: "telegram",
    name: "Telegram",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 7.7 13.4 3.4c.5-.2 1 .3.8.8l-2.3 8.2c-.1.5-.7.7-1.1.4l-2.6-2-1.3 1.3c-.2.2-.5.1-.6-.2l-.4-2.2 5.2-4.7-6.4 4.1L2.6 8.5c-.5-.2-.5-.8 0-.8Z" fill="currentColor"/></svg>',
  },
  {
    id: "youtube",
    name: "YouTube",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1.5" y="3.5" width="13" height="9" rx="2.2" stroke="currentColor" stroke-width="1.3"/><path d="M7 6.2v3.6l3-1.8-3-1.8Z" fill="currentColor"/></svg>',
  },
  {
    id: "vk",
    name: "ВКонтакте",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 4.2h2.1c.1 2.1 1.1 3.3 1.9 3.8V4.2h2v2.3c.8-.4 1.6-1.6 1.9-2.3h2c-.4 1.2-1.5 2.6-2.3 3.3.9.5 2.1 1.7 2.6 3.2h-2.2c-.4-1-1.2-1.9-2-2.3v2.3H6.2V9.1C4.6 8.7 2.8 6.9 2.2 4.2Z" fill="currentColor"/></svg>',
  },
  {
    id: "tiktok",
    name: "TikTok",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M9.2 2.2h1.7c.2 1.3 1 2.3 2.3 2.6v1.7c-.9 0-1.7-.3-2.3-.8v4.1a3.6 3.6 0 1 1-3.6-3.6c.2 0 .4 0 .6.1v1.8a1.8 1.8 0 1 0 1.3 1.7V2.2Z" fill="currentColor"/></svg>',
  },
  {
    id: "dzen",
    name: "Дзен",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.6c.2 2.4.7 3.8 1.8 4.6 1.1.8 2.6 1.1 4.6 1.2-2 .2-3.5.5-4.6 1.3-1.1.8-1.6 2.2-1.8 4.7-.2-2.5-.7-3.9-1.8-4.7C5 8.9 3.5 8.6 1.6 8.4c2-.1 3.5-.4 4.6-1.2C7.3 6.4 7.8 5 8 1.6Z" fill="currentColor"/></svg>',
  },
  {
    id: "max",
    name: "Макс",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 3.4h11.6v7.4c0 .9-.7 1.6-1.6 1.6H6.2L3.4 14.2V12.4H3.8c-.9 0-1.6-.7-1.6-1.6V3.4Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
  },
];

const format = new Intl.NumberFormat("ru-RU");
const grid = document.getElementById("grid");
const totalEl = document.getElementById("total");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function mountCards() {
  grid.innerHTML = NETWORKS.map((network, index) => `
    <article class="card" style="animation-delay:${index * 60}ms" data-id="${network.id}">
      <div class="card-top">
        <span class="mark">${network.icon}</span>
        <span class="name">${network.name}</span>
      </div>
      <div class="count">—</div>
      <div class="delta"></div>
      <svg class="spark empty" viewBox="0 0 160 36" preserveAspectRatio="none" aria-hidden="true">
        <path d=""></path>
      </svg>
    </article>
  `).join("");
}

function linePath(series) {
  const width = 160;
  const height = 36;
  if (!series.length) {
    return `M 0 ${height / 2} L ${width} ${height / 2}`;
  }
  if (series.length === 1) {
    return `M 0 ${height / 2} L ${width} ${height / 2}`;
  }
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  return series.map((value, index) => {
    const x = (index / (series.length - 1)) * width;
    const y = height - 3 - ((value - min) / span) * (height - 6);
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function paintNumber(element, value) {
  if (value == null) {
    element.textContent = "—";
    element.dataset.value = "";
    return;
  }
  const from = element.dataset.value === "" || element.dataset.value == null
    ? value
    : Number(element.dataset.value);
  element.dataset.value = String(value);
  if (reduceMotion || from === value || Number.isNaN(from)) {
    element.textContent = format.format(value);
    return;
  }
  const start = performance.now();
  const duration = 700;
  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(from + (value - from) * eased);
    element.textContent = format.format(current);
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function paintDelta(element, delta) {
  element.classList.remove("up", "down");
  if (delta == null) {
    element.textContent = "";
    return;
  }
  if (delta > 0) {
    element.classList.add("up");
    element.textContent = `+${format.format(delta)} за сутки`;
    return;
  }
  if (delta < 0) {
    element.classList.add("down");
    element.textContent = `−${format.format(Math.abs(delta))} за сутки`;
    return;
  }
  element.textContent = "0 за сутки";
}

function paintCard(network) {
  const card = grid.querySelector(`[data-id="${network.id}"]`);
  if (!card) return;
  paintNumber(card.querySelector(".count"), network.count);
  paintDelta(card.querySelector(".delta"), network.delta);
  const spark = card.querySelector(".spark");
  spark.classList.toggle("empty", network.count == null);
  spark.querySelector("path").setAttribute("d", linePath(network.series || []));
}

function apply(data) {
  const known = (data.networks || []).filter((item) => item.count != null);
  const total = known.reduce((sum, item) => sum + item.count, 0);
  paintNumber(totalEl, known.length ? total : null);
  for (const network of data.networks || []) paintCard(network);
}

async function refresh() {
  const response = await fetch(`stats.json?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) return;
  apply(await response.json());
}

mountCards();
refresh();
setInterval(refresh, 20000);
