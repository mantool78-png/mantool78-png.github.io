const NETWORKS = [
  {
    id: "telegram",
    name: "Telegram",
    url: "https://t.me/acrotim",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 7.7 13.4 3.4c.5-.2 1 .3.8.8l-2.3 8.2c-.1.5-.7.7-1.1.4l-2.6-2-1.3 1.3c-.2.2-.5.1-.6-.2l-.4-2.2 5.2-4.7-6.4 4.1L2.6 8.5c-.5-.2-.5-.8 0-.8Z" fill="currentColor"/></svg>',
  },
  {
    id: "youtube",
    name: "YouTube",
    url: "https://www.youtube.com/channel/UCBG6Fg2flgYnhQGiBZkyK7Q",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1.5" y="3.5" width="13" height="9" rx="2.2" stroke="currentColor" stroke-width="1.3"/><path d="M7 6.2v3.6l3-1.8-3-1.8Z" fill="currentColor"/></svg>',
  },
  {
    id: "vk",
    name: "ВКонтакте",
    url: "https://vk.ru/club225676956",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 4.2h2.1c.1 2.1 1.1 3.3 1.9 3.8V4.2h2v2.3c.8-.4 1.6-1.6 1.9-2.3h2c-.4 1.2-1.5 2.6-2.3 3.3.9.5 2.1 1.7 2.6 3.2h-2.2c-.4-1-1.2-1.9-2-2.3v2.3H6.2V9.1C4.6 8.7 2.8 6.9 2.2 4.2Z" fill="currentColor"/></svg>',
  },
  {
    id: "tiktok",
    name: "TikTok",
    url: "https://www.tiktok.com/@slovoacrobata",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M9.2 2.2h1.7c.2 1.3 1 2.3 2.3 2.6v1.7c-.9 0-1.7-.3-2.3-.8v4.1a3.6 3.6 0 1 1-3.6-3.6c.2 0 .4 0 .6.1v1.8a1.8 1.8 0 1 0 1.3 1.7V2.2Z" fill="currentColor"/></svg>',
  },
  {
    id: "dzen",
    name: "Дзен",
    url: "https://dzen.ru/gymacro.ru",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.6c.2 2.4.7 3.8 1.8 4.6 1.1.8 2.6 1.1 4.6 1.2-2 .2-3.5.5-4.6 1.3-1.1.8-1.6 2.2-1.8 4.7-.2-2.5-.7-3.9-1.8-4.7C5 8.9 3.5 8.6 1.6 8.4c2-.1 3.5-.4 4.6-1.2C7.3 6.4 7.8 5 8 1.6Z" fill="currentColor"/></svg>',
  },
  {
    id: "max",
    name: "Макс",
    url: "https://max.ru/se14052651_biz",
    icon: '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.2 3.4h11.6v7.4c0 .9-.7 1.6-1.6 1.6H6.2L3.4 14.2V12.4H3.8c-.9 0-1.6-.7-1.6-1.6V3.4Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
  },
];

const format = new Intl.NumberFormat("ru-RU");
const grid = document.getElementById("grid");
const totalEl = document.getElementById("total");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const shown = new Map();

function mountCards() {
  grid.innerHTML = NETWORKS.map((network, index) => `
    <article class="card" data-id="${network.id}" style="animation-delay:${index * 60}ms">
    <a class="card-link" href="${network.url}" aria-label="${network.name}">
      <div class="card-top">
        <span class="mark">${network.icon}</span>
        <span class="name">${network.name}</span>
      </div>
      <div class="count">—</div>
      <div class="delta"></div>
      <p class="reach" hidden></p>
      <svg class="spark empty" viewBox="0 0 160 36" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="spark-grad-up-${network.id}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--up)" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="var(--up)" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="spark-grad-down-${network.id}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--down)" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="var(--down)" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="spark-grad-neutral-${network.id}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.20"/>
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <path class="spark-area" fill="url(#spark-grad-neutral-${network.id})" d=""></path>
        <path class="spark-line" d=""></path>
        <circle class="spark-dot" r="2.5" cx="-10" cy="-10"></circle>
      </svg>
    </a>
    <a class="best" hidden rel="noopener noreferrer"></a>
    </article>
  `).join("");
}

let lastOpen = 0;

function openCard(link) {
  const now = Date.now();
  if (now - lastOpen < 700) return;
  lastOpen = now;
  const url = link.href;
  const phone = window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
  if (phone) {
    window.location.assign(url);
    return;
  }
  const popup = window.open(url, "_blank", "noopener,noreferrer");
  if (!popup) window.location.assign(url);
}

function cardFromEvent(event) {
  const node = event.target && event.target.closest ? event.target : event.target && event.target.parentElement;
  return node && node.closest ? node.closest("a.best, a.card-link") : null;
}

grid.addEventListener("click", (event) => {
  const link = cardFromEvent(event);
  if (!link) return;
  event.preventDefault();
  openCard(link);
});

grid.addEventListener("touchend", (event) => {
  const link = cardFromEvent(event);
  if (!link) return;
  event.preventDefault();
  openCard(link);
}, { passive: false });

function sparkPaths(series) {
  const width = 160;
  const height = 36;
  if (!series.length) {
    const y = height / 2;
    return {
      line: `M 0 ${y} L ${width} ${y}`,
      area: `M 0 ${y} L ${width} ${y} L ${width} ${height} L 0 ${height} Z`,
      dot: { x: width, y, visible: false },
    };
  }
  if (series.length === 1) {
    const y = height / 2;
    return {
      line: `M 0 ${y} L ${width} ${y}`,
      area: `M 0 ${y} L ${width} ${y} L ${width} ${height} L 0 ${height} Z`,
      dot: { x: width, y, visible: true },
    };
  }
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const points = series.map((value, index) => {
    const x = (index / (series.length - 1)) * width;
    const y = height - 4 - ((value - min) / span) * (height - 8);
    return { x, y };
  });
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  const area = `${line} L ${width} ${height} L 0 ${height} Z`;
  return {
    line,
    area,
    dot: { x: last.x, y: last.y, visible: true },
  };
}

function isRoundHundred(value) {
  return typeof value === "number" && value >= 100 && value % 100 === 0;
}

function markRound(element, value, key) {
  const round = isRoundHundred(value);
  element.classList.toggle("round", round);
  if (!round || !key) return;
  const mark = `acro-salute:${key}:${value}`;
  try {
    if (sessionStorage.getItem(mark)) return;
    sessionStorage.setItem(mark, "1");
  } catch {
    return;
  }
  launchSalute();
}

let saluteCanvas = null;

function launchSalute() {
  if (reduceMotion || saluteCanvas) return;
  const canvas = document.createElement("canvas");
  canvas.className = "salute";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  saluteCanvas = canvas;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rockets = [];
  const sparks = [];
  const width = () => window.innerWidth;
  const height = () => window.innerHeight;

  function resize() {
    canvas.width = Math.round(width() * dpr);
    canvas.height = Math.round(height() * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();

  function burst(x, y, color) {
    const count = 72;
    for (let i = 0; i < count; i += 1) {
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.2;
      const speed = 2.2 + Math.random() * 5.2;
      sparks.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        color: i % 4 === 0 ? "#fff4d2" : color,
        radius: 2.2 + Math.random() * 2.4,
      });
    }
  }

  const plan = [
    { at: 80, x: 0.22, y: 0.34, color: "#ffd56a" },
    { at: 360, x: 0.72, y: 0.3, color: "#3ee0a0" },
    { at: 640, x: 0.48, y: 0.24, color: "#fff4d2" },
    { at: 920, x: 0.3, y: 0.46, color: "#9be7ff" },
    { at: 1160, x: 0.66, y: 0.42, color: "#ffd56a" },
  ];
  plan.forEach((shot) => {
    rockets.push({
      x: shot.x * width(),
      y: height() + 8,
      tx: shot.x * width(),
      ty: shot.y * height(),
      color: shot.color,
      born: performance.now() + shot.at,
      done: false,
    });
  });

  const started = performance.now();
  function frame(now) {
    if (!canvas.isConnected) return;
    ctx.clearRect(0, 0, width(), height());
    for (const rocket of rockets) {
      if (rocket.done || now < rocket.born) continue;
      const t = Math.min(1, (now - rocket.born) / 520);
      const eased = 1 - Math.pow(1 - t, 3);
      const y = rocket.y + (rocket.ty - rocket.y) * eased;
      ctx.globalAlpha = 0.85;
      ctx.fillStyle = rocket.color;
      ctx.beginPath();
      ctx.arc(rocket.tx, y, 2.2, 0, Math.PI * 2);
      ctx.fill();
      if (t >= 1) {
        rocket.done = true;
        burst(rocket.tx, rocket.ty, rocket.color);
      }
    }
    for (let i = sparks.length - 1; i >= 0; i -= 1) {
      const spark = sparks[i];
      spark.vy += 0.026;
      spark.x += spark.vx;
      spark.y += spark.vy;
      spark.vx *= 0.988;
      spark.life -= 0.0045;
      if (spark.life <= 0) {
        sparks.splice(i, 1);
        continue;
      }
      ctx.globalAlpha = Math.max(0, spark.life);
      ctx.fillStyle = spark.color;
      ctx.shadowBlur = 16;
      ctx.shadowColor = spark.color;
      ctx.beginPath();
      ctx.arc(spark.x, spark.y, spark.radius * (0.45 + spark.life), 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    ctx.globalAlpha = 1;
    if (now - started < 5600) requestAnimationFrame(frame);
    else {
      canvas.remove();
      if (saluteCanvas === canvas) saluteCanvas = null;
    }
  }
  requestAnimationFrame(frame);
}

function paintNumber(element, value, key) {
  if (value == null) {
    element.textContent = "—";
    element.dataset.value = "";
    element.classList.remove("round");
    return;
  }
  const from = element.dataset.value === "" || element.dataset.value == null
    ? value
    : Number(element.dataset.value);
  element.dataset.value = String(value);
  markRound(element, value, key);

  if (from != null && from !== value && !Number.isNaN(from)) {
    element.classList.remove("pulse-up", "pulse-down");
    void element.offsetWidth;
    element.classList.add(value > from ? "pulse-up" : "pulse-down");
  }

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

const PERIODS = ["week", "month", "all"];
let period = "week";
try {
  const savedPeriod = localStorage.getItem("acro-period");
  if (PERIODS.includes(savedPeriod)) period = savedPeriod;
} catch {
  period = "week";
}

const periodBar = document.getElementById("periods");
const periodButtons = [...periodBar.querySelectorAll(".period")];
const forecastEl = document.getElementById("forecast");
const updatedEl = document.getElementById("updated");
let latest = null;
let generatedAt = "";

function plural(value, one, few, many) {
  const abs = Math.abs(value) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

function syncPeriods() {
  for (const button of periodButtons) {
    const active = button.dataset.period === period;
    button.setAttribute("aria-checked", active ? "true" : "false");
    button.tabIndex = active ? 0 : -1;
  }
}

function selectPeriod(next) {
  if (!PERIODS.includes(next) || next === period) return;
  period = next;
  try {
    localStorage.setItem("acro-period", period);
  } catch {
    /* private mode */
  }
  syncPeriods();
  if (latest) apply(latest);
}

periodButtons.forEach((button) => {
  button.addEventListener("click", () => selectPeriod(button.dataset.period));
});

periodBar.addEventListener("keydown", (event) => {
  const index = PERIODS.indexOf(period);
  let next = index;
  if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % PERIODS.length;
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + PERIODS.length - 1) % PERIODS.length;
  else return;
  event.preventDefault();
  selectPeriod(PERIODS[next]);
  periodButtons[next].focus();
});
syncPeriods();

function sortedHistory(network) {
  return (Array.isArray(network.history) ? network.history : [])
    .filter((point) => point && typeof point.count === "number" && typeof point.date === "string")
    .slice()
    .sort((left, right) => (left.date < right.date ? -1 : left.date > right.date ? 1 : 0));
}

function seriesFor(network) {
  if (period === "week") return network.series || [];
  const points = sortedHistory(network);
  if (!points.length) return network.series || [];
  if (period === "month") return points.slice(-30).map((point) => point.count);
  return points.map((point) => point.count);
}

function nextMilestone(total) {
  if (total < 1000) {
    for (const mark of [100, 250, 500, 1000]) {
      if (total < mark) return mark;
    }
    return 1000;
  }
  if (total < 10000) return Math.floor(total / 1000) * 1000 + 1000;
  return Math.floor(total / 5000) * 5000 + 5000;
}

function dailyTotals(networks) {
  const histories = networks.map(sortedHistory).filter((points) => points.length);
  if (!histories.length) return [];
  const dates = new Set();
  for (const points of histories) {
    for (const point of points) dates.add(point.date);
  }
  const totals = [];
  for (const date of [...dates].sort()) {
    let sum = 0;
    let ready = 0;
    for (const points of histories) {
      let value = null;
      for (const point of points) {
        if (point.date <= date) value = point.count;
        else break;
      }
      if (value == null) continue;
      sum += value;
      ready += 1;
    }
    if (ready === histories.length) totals.push({ date, total: sum });
  }
  return totals;
}

function forecastText(networks, total) {
  if (typeof total !== "number" || total <= 0) return "";
  const recent = dailyTotals(networks).slice(-8);
  if (recent.length < 3) return "";
  const first = recent[0];
  const last = recent[recent.length - 1];
  const span = (Date.parse(last.date) - Date.parse(first.date)) / 86400000;
  if (!(span >= 2)) return "";
  const rate = (last.total - first.total) / span;
  if (!(rate > 0)) return "";
  const goal = nextMilestone(total);
  const left = goal - total;
  if (!(left > 0)) return "";
  const days = Math.max(1, Math.round(left / rate));
  const pace = days > 400
    ? "больше года при текущем темпе"
    : `≈${format.format(days)} ${plural(days, "день", "дня", "дней")} при текущем темпе`;
  return `до ${format.format(goal)} осталось ${format.format(left)} · ${pace}`;
}

function paintForecast(text) {
  if (!text) {
    forecastEl.hidden = true;
    forecastEl.textContent = "";
    return;
  }
  forecastEl.hidden = false;
  if (forecastEl.textContent !== text) forecastEl.textContent = text;
}

function updatedLabel(iso) {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "";
  const delta = Date.now() - then;
  if (delta < 60000) return "обновлено только что";
  const minutes = Math.floor(delta / 60000);
  if (minutes < 60) {
    return `обновлено ${minutes} ${plural(minutes, "минуту", "минуты", "минут")} назад`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `обновлено ${hours} ${plural(hours, "час", "часа", "часов")} назад`;
  }
  const days = Math.floor(hours / 24);
  return `обновлено ${days} ${plural(days, "день", "дня", "дней")} назад`;
}

function paintUpdated() {
  const label = generatedAt ? updatedLabel(generatedAt) : "";
  if (!label) {
    updatedEl.hidden = true;
    updatedEl.textContent = "";
    updatedEl.removeAttribute("datetime");
    return;
  }
  updatedEl.hidden = false;
  updatedEl.dateTime = generatedAt;
  updatedEl.textContent = label;
}

function safePostUrl(url) {
  return typeof url === "string" && /^https:\/\/(t\.me|vk\.ru|vk\.com)\//.test(url);
}

function paintReach(card, network) {
  const reach = card.querySelector(".reach");
  if (!reach) return;
  if (typeof network.reach !== "number") {
    reach.hidden = true;
    reach.textContent = "";
    reach.removeAttribute("title");
    return;
  }
  reach.hidden = false;
  reach.textContent = `охват ${format.format(network.reach)}`;
  reach.title = "Средние просмотры поста за 7 дней";
}

function paintBest(card, network) {
  const best = card ? card.querySelector(".best") : null;
  const post = network.best_post;
  const visible = best && card && post && safePostUrl(post.url) && typeof post.views === "number";
  if (!visible) {
    if (best) {
      best.hidden = true;
      best.removeAttribute("href");
      best.textContent = "";
    }
    if (card) card.classList.remove("has-best");
    return;
  }
  best.hidden = false;
  best.href = post.url;
  best.textContent = `Лучший пост · ${format.format(post.views)}`;
  const title = typeof post.title === "string" ? post.title : "";
  best.title = title || "Лучший пост за неделю";
  best.setAttribute(
    "aria-label",
    `${title ? `${title}. ` : ""}${format.format(post.views)} просмотров`,
  );
  card.classList.add("has-best");
}

function paintCard(network) {
  const card = grid.querySelector(`[data-id="${network.id}"]`);
  if (!card) return;
  paintNumber(card.querySelector(".count"), network.count, network.id);
  paintDelta(card.querySelector(".delta"), network.delta);
  paintReach(card, network);
  paintBest(card, network);

  card.classList.remove("trend-up", "trend-down", "trend-neutral");
  let trend = "neutral";
  if (network.delta > 0) trend = "up";
  else if (network.delta < 0) trend = "down";
  card.classList.add(`trend-${trend}`);

  const spark = card.querySelector(".spark");
  const isEmpty = network.count == null;
  spark.classList.toggle("empty", isEmpty);
  const paths = sparkPaths(seriesFor(network));
  const lineEl = spark.querySelector(".spark-line");
  const areaEl = spark.querySelector(".spark-area");
  const dotEl = spark.querySelector(".spark-dot");
  if (lineEl) lineEl.setAttribute("d", paths.line);
  if (areaEl) {
    areaEl.setAttribute("d", paths.area);
    areaEl.setAttribute("fill", `url(#spark-grad-${trend}-${network.id})`);
  }
  if (dotEl) {
    dotEl.setAttribute("cx", paths.dot.x.toFixed(1));
    dotEl.setAttribute("cy", paths.dot.y.toFixed(1));
    dotEl.style.display = paths.dot.visible && !isEmpty ? "" : "none";
  }
}

function apply(data) {
  latest = data;
  generatedAt = typeof data.generated_at === "string" ? data.generated_at : "";
  paintUpdated();
  const networks = data.networks || [];
  const known = networks.filter((item) => item.count != null);
  const total = known.reduce((sum, item) => sum + item.count, 0);
  paintNumber(totalEl, known.length ? total : null, "total");
  paintForecast(known.length ? forecastText(known, total) : "");
  for (const network of networks) paintCard(network);
}

function networksHaveHistory(data) {
  return (data.networks || []).some((network) => Array.isArray(network.history) && network.history.length);
}

function attachArchive(data, archive) {
  const days = archive && archive.days;
  if (!days || typeof days !== "object") return;
  const dates = Object.keys(days).filter((date) => days[date] && typeof days[date] === "object").sort();
  for (const network of data.networks || []) {
    if (Array.isArray(network.history) && network.history.length) continue;
    const points = [];
    for (const date of dates) {
      const value = days[date][network.id];
      if (typeof value === "number") points.push({ date, count: value });
    }
    if (points.length) network.history = points;
  }
}

async function refresh() {
  const response = await fetch(`stats.json?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) return;
  const data = await response.json();
  if (typeof data.generated_at !== "string") {
    const lastModified = response.headers.get("last-modified");
    if (lastModified) data.generated_at = lastModified;
  }
  if (!networksHaveHistory(data)) {
    try {
      const archive = await fetch(`data/history.json?t=${Date.now()}`, { cache: "no-store" });
      if (archive.ok) attachArchive(data, await archive.json());
    } catch {
      /* series in stats.json is enough for the week view */
    }
  }
  apply(data);
}

mountCards();
refresh();
setInterval(refresh, 20000);
setInterval(paintUpdated, 30000);
