/* ============================================================
   我们的小时光 — 交互脚本（原生 JS，零依赖）
   数据来自 data/content.js，本地修改存在 localStorage。
   ============================================================ */
(function () {
  "use strict";

  const DATA = window.LOVE_DATA || {};
  const LS_SETTINGS = "ours.settings.v1";
  const LS_WISHES = "ours.wishes.v1";
  const LS_NOTES = "ours.notes.v1";
  const LS_HIDDEN_NOTES = "ours.hiddenNotes.v1";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const FALLBACK_IMG =
    "data:image/svg+xml," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">' +
        '<rect width="400" height="400" fill="#f4ede2"/>' +
        '<path d="M200 268c-46-32-84-62-84-100 0-27 21-46 45-46 18 0 32 10 39 25 7-15 21-25 39-25 24 0 45 19 45 46 0 38-38 68-84 100z" fill="none" stroke="#c9bcaa" stroke-width="6" stroke-linecap="round"/>' +
        '<text x="200" y="316" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#a4968a">把照片放进来</text>' +
        "</svg>"
    );

  /* ---------------- 小工具 ---------------- */
  const pad2 = (n) => String(n).padStart(2, "0");

  function parseDate(str) {
    if (!str) return null;
    const m = String(str).match(/(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }

  // 用 UTC 的「日」来算整天数，避开夏令时和时区误差
  const dayNumber = (d) => Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);

  function startOfToday() {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  function formatCN(date) {
    return date.getFullYear() + "." + pad2(date.getMonth() + 1) + "." + pad2(date.getDate());
  }

  function formatShort(date) {
    return date.getFullYear() + "-" + pad2(date.getMonth() + 1) + "-" + pad2(date.getDate());
  }

  // 日历意义上的「几年几个月几天」
  function calendarDiff(from, to) {
    let years = to.getFullYear() - from.getFullYear();
    let months = to.getMonth() - from.getMonth();
    let days = to.getDate() - from.getDate();
    if (days < 0) {
      months -= 1;
      const prevMonth = new Date(to.getFullYear(), to.getMonth(), 0);
      days += prevMonth.getDate();
    }
    if (months < 0) {
      years -= 1;
      months += 12;
    }
    return { years, months, days };
  }

  function nextOccurrence(monthDay) {
    const [mm, dd] = String(monthDay).split("-").map(Number);
    const today = startOfToday();
    let target = new Date(today.getFullYear(), mm - 1, dd);
    if (dayNumber(target) < dayNumber(today)) target = new Date(today.getFullYear() + 1, mm - 1, dd);
    return target;
  }

  function escapeHTML(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);
  }

  function readLS(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function writeLS(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      return false;
    }
  }

  /* ---------------- 状态 ---------------- */
  const baseCouple = Object.assign({}, DATA.couple || {});
  const savedCouple = readLS(LS_SETTINGS, null);
  const couple = Object.assign({}, baseCouple, savedCouple || {});

  function currentData() {
    return Object.assign({}, DATA, { couple: couple });
  }

  /* ---------------- 绑定静态文案 ---------------- */
  function getPath(obj, path) {
    return path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);
  }

  function applyBindings() {
    const ctx = currentData();
    $$("[data-bind]").forEach((el) => {
      const value = getPath(ctx, el.getAttribute("data-bind"));
      if (typeof value === "string" && value.trim()) el.textContent = value;
    });

    const start = parseDate(couple.startDate);
    const since = $('[data-bind="couple.since"]');
    if (since) since.textContent = "SINCE " + (start ? formatCN(start) : "----.--.--");

    document.title = (DATA.meta && DATA.meta.title ? DATA.meta.title + " · " : "") + couple.nameA + " & " + couple.nameB;

    const heroArt = $("#heroArt");
    if (heroArt) {
      heroArt.src = couple.art || "assets/art/hero.jpg";
      heroArt.alt = couple.nameA + " 和 " + couple.nameB + " 的涂鸦";
      heroArt.onerror = () => { heroArt.onerror = null; heroArt.src = FALLBACK_IMG; };
    }
  }

  /* ---------------- 计时与倒计时 ---------------- */
  function renderCounters() {
    const start = parseDate(couple.startDate);
    const today = startOfToday();
    const daysEl = $("#daysTogether");
    const detailEl = $("#togetherDetail");
    const clockEl = $("#liveClock");
    const nextEl = $("#nextDate");

    if (!start) {
      if (daysEl) daysEl.textContent = "—";
      return;
    }

    const totalDays = Math.max(0, dayNumber(today) - dayNumber(start) + 1);
    if (daysEl) daysEl.textContent = totalDays.toLocaleString("en-US");

    const diff = calendarDiff(start, today);
    if (detailEl) {
      const bits = [];
      if (diff.years) bits.push(diff.years + " 年");
      bits.push(diff.months + " 个月");
      bits.push(diff.days + " 天");
      detailEl.textContent = "也就是 " + bits.join(" ") + "，还在继续";
    }

    if (clockEl) {
      const tick = () => {
        const now = new Date();
        clockEl.textContent = pad2(now.getHours()) + ":" + pad2(now.getMinutes()) + ":" + pad2(now.getSeconds());
      };
      tick();
      setInterval(tick, 1000);
    }

    const list = DATA.anniversaries || [];
    if (nextEl && list.length) {
      const upcoming = list
        .map((a) => ({ a, when: nextOccurrence(a.date) }))
        .sort((x, y) => x.when - y.when)[0];
      const gap = dayNumber(upcoming.when) - dayNumber(today);
      const label = gap === 0 ? "就是今天 🎉" : "还有 <em>" + gap + "</em> 天";
      nextEl.innerHTML = escapeHTML(upcoming.a.name) + " · " + label;
    } else if (nextEl) {
      nextEl.textContent = "还没写纪念日";
    }
  }

  /* ---------------- 数字条 ---------------- */
  function renderStats() {
    const wrap = $("#statStrip");
    if (!wrap) return;
    const start = parseDate(couple.startDate);
    const days = start ? Math.max(0, dayNumber(startOfToday()) - dayNumber(start) + 1) : 0;

    const auto = [
      { label: "在一起的日子", value: days.toLocaleString("en-US"), unit: "天" },
      { label: "记录下来的故事", value: (DATA.timeline || []).length, unit: "件" },
      { label: "相册里的照片", value: (DATA.photos || []).length, unit: "张" },
    ].concat(DATA.stats || []);

    wrap.innerHTML = auto
      .map(
        (s) =>
          '<li class="reveal"><span class="stat__value">' +
          escapeHTML(s.value) +
          (s.unit ? "<small>" + escapeHTML(s.unit) + "</small>" : "") +
          '</span><span class="stat__label">' +
          escapeHTML(s.label) +
          "</span></li>"
      )
      .join("");
  }

  /* ---------------- 时光轴 ---------------- */
  function renderTimeline() {
    const wrap = $("#timelineList");
    if (!wrap) return;
    const items = (DATA.timeline || []).slice().sort((a, b) => new Date(a.date) - new Date(b.date));

    wrap.innerHTML = items
      .map((item) => {
        const d = parseDate(item.date);
        const label = d ? d.getFullYear() + " 年 " + (d.getMonth() + 1) + " 月 " + d.getDate() + " 日" : escapeHTML(item.date);
        return (
          '<article class="tl-item" role="listitem">' +
            '<div class="tl-card reveal">' +
              '<div class="tl-card__top">' +
                '<span class="tl-date">' + label + "</span>" +
                (item.tag ? '<span class="tl-tag">' + escapeHTML(item.tag) + "</span>" : "") +
              "</div>" +
              '<h3 class="tl-title">' + escapeHTML(item.title) + "</h3>" +
              '<p class="tl-text">' + escapeHTML(item.text) + "</p>" +
              (item.image
                ? '<div class="tl-img"><img src="' + escapeHTML(item.image) + '" alt="' + escapeHTML(item.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + FALLBACK_IMG + '\';" /></div>'
                : "") +
            "</div>" +
          "</article>"
        );
      })
      .join("");
  }

  /* ---------------- 相册 ---------------- */
  let photos = [];
  let samples = [];

  function renderGallery() {
    const wrap = $("#gallery");
    if (!wrap) return;
    photos = DATA.photos || [];

    wrap.innerHTML = photos
      .map((p, i) => {
        const d = parseDate(p.date);
        return (
          '<button class="gallery__item reveal" type="button" data-index="' + i + '" aria-label="查看大图：' + escapeHTML(p.title) + '">' +
            '<span class="gallery__thumb"><img src="' + escapeHTML(p.src) + '" alt="' + escapeHTML(p.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + FALLBACK_IMG + '\';" /></span>' +
            '<span class="gallery__meta">' +
              '<span class="gallery__title">' + escapeHTML(p.title) + "</span>" +
              '<span class="gallery__date">' + (d ? formatCN(d) : escapeHTML(p.date || "")) + "</span>" +
            "</span>" +
          "</button>"
        );
      })
      .join("");

    if (!wrap.dataset.bound) {
      wrap.dataset.bound = "1";
      wrap.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-index]");
        if (btn) openLightbox(Number(btn.getAttribute("data-index")), photos);
      });
    }
  }

  /* ---------------- 画风样张 ---------------- */
  function renderSamples() {
    const wrap = $("#sampleWall");
    if (!wrap) return;
    samples = DATA.samples || [];

    wrap.innerHTML = samples
      .map(
        (s, i) =>
          '<button class="sample" type="button" data-sample="' + i + '" aria-label="查看大图：' + escapeHTML(s.title) + '">' +
            '<img src="' + escapeHTML(s.src) + '" alt="' + escapeHTML(s.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + FALLBACK_IMG + '\';" />' +
            '<span class="sample__title">' + escapeHTML(s.title) + "</span>" +
          "</button>"
      )
      .join("");

    if (!wrap.dataset.bound) {
      wrap.dataset.bound = "1";
      wrap.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-sample]");
        if (btn) openLightbox(Number(btn.getAttribute("data-sample")), samples);
      });
    }
  }

  /* ---------------- 纪念日 ---------------- */
  function renderDates() {
    const wrap = $("#dateGrid");
    if (!wrap) return;
    const today = startOfToday();

    wrap.innerHTML = (DATA.anniversaries || [])
      .map((a) => {
        const when = nextOccurrence(a.date);
        const gap = dayNumber(when) - dayNumber(today);
        const isToday = gap === 0;
        const [mm, dd] = String(a.date).split("-");
        return (
          '<article class="date-card reveal' + (isToday ? " is-today" : "") + '">' +
            '<div class="date-card__emoji" aria-hidden="true">' + escapeHTML(a.emoji || "♥") + "</div>" +
            '<h3 class="date-card__name">' + escapeHTML(a.name) + "</h3>" +
            '<p class="date-card__when">每年 ' + escapeHTML(mm) + " 月 " + escapeHTML(dd) + " 日 · " + when.getFullYear() + "</p>" +
            '<p class="date-card__count">' + gap + "<small>天后</small></p>" +
            (a.note ? '<p class="date-card__note">' + escapeHTML(a.note) + "</p>" : "") +
          "</article>"
        );
      })
      .join("");
  }

  /* ---------------- 清单 ---------------- */
  function wishState() {
    const seed = {};
    (DATA.wishes || []).forEach((w) => { seed[w.text] = !!w.done; });
    return Object.assign(seed, readLS(LS_WISHES, {}));
  }

  function renderWishes() {
    const list = $("#wishList");
    if (!list) return;
    const state = wishState();
    const items = DATA.wishes || [];

    list.innerHTML = items
      .map((w, i) => {
        const id = "wish-" + i;
        const checked = state[w.text] ? " checked" : "";
        return (
          '<li class="wish__item">' +
            '<label class="wish__label" for="' + id + '">' +
              '<input type="checkbox" id="' + id + '" data-wish="' + escapeHTML(w.text) + '"' + checked + " />" +
              '<span class="wish__box" aria-hidden="true"></span>' +
              '<span class="wish__text">' + escapeHTML(w.text) + "</span>" +
            "</label>" +
          "</li>"
        );
      })
      .join("");

    updateWishProgress();

    if (!list.dataset.bound) {
      list.dataset.bound = "1";
      list.addEventListener("change", (e) => {
        const input = e.target.closest("[data-wish]");
        if (!input) return;
        const saved = readLS(LS_WISHES, {});
        saved[input.getAttribute("data-wish")] = input.checked;
        writeLS(LS_WISHES, saved);
        updateWishProgress();
        if (input.checked) burstFrom(e.target.closest(".wish__label"));
      });
    }
  }

  function updateWishProgress() {
    const boxes = $$("#wishList [data-wish]");
    const done = boxes.filter((b) => b.checked).length;
    const total = boxes.length;
    const bar = $("#wishBar");
    if (bar) bar.style.width = total ? Math.round((done / total) * 100) + "%" : "0%";
    if ($("#wishDone")) $("#wishDone").textContent = done;
    if ($("#wishTotal")) $("#wishTotal").textContent = total;
  }

  /* ---------------- 小纸条 ---------------- */
  function defaultNotes() {
    return (DATA.notes || []).map((n, i) => ({
      id: "seed-" + i,
      from: n.from,
      text: n.text,
      date: n.date || "",
      seed: true,
    }));
  }

  function allNotes() {
    const hidden = readLS(LS_HIDDEN_NOTES, []);
    const local = readLS(LS_NOTES, []);
    return defaultNotes()
      .concat(local)
      .filter((n) => hidden.indexOf(n.id) === -1)
      .sort((a, b) => String(b.date).localeCompare(String(a.date)));
  }

  function renderNotes() {
    const wall = $("#notesWall");
    if (!wall) return;

    const notes = allNotes();
    wall.innerHTML = notes.length
      ? notes
          .map(
            (n) =>
              '<article class="note reveal" data-note-id="' + escapeHTML(n.id) + '">' +
                '<p class="note__text">' + escapeHTML(n.text) + "</p>" +
                '<div class="note__meta"><span class="note__from">—— ' + escapeHTML(n.from) + "</span>" +
                  "<span>" + escapeHTML(n.date || "") +
                    '<button class="note__del" type="button" data-del="' + escapeHTML(n.id) + '" title="撕掉这张纸条" aria-label="撕掉这张纸条">×</button>' +
                  "</span>" +
                "</div>" +
              "</article>"
          )
          .join("")
      : '<p class="gallery__hint">还没有小纸条，写第一张吧。</p>';

    $$(".reveal", wall).forEach((el) => el.classList.add("in"));
    observeReveals();
  }

  function refreshNoteOptions() {
    const fromSel = $("#noteFrom");
    if (!fromSel) return;
    const current = fromSel.value;
    fromSel.innerHTML = "";
    [couple.nameA, couple.nameB].filter(Boolean).forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      fromSel.appendChild(opt);
    });
    if (current) {
      const hit = Array.from(fromSel.options).find((o) => o.value === current);
      if (hit) fromSel.value = current;
    }
  }

  function setupNoteForm() {
    const form = $("#noteForm");
    const fromSel = $("#noteFrom");
    if (!form || !fromSel) return;

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = $("#noteText").value.trim();
      if (!text) return;
      const local = readLS(LS_NOTES, []);
      local.push({
        id: "local-" + Date.now(),
        from: fromSel.value || couple.nameA || "我",
        text: text,
        date: formatShort(new Date()),
      });
      writeLS(LS_NOTES, local);
      $("#noteText").value = "";
      renderNotes();
      burstFrom(form);
    });

    const wall = $("#notesWall");
    if (wall) {
      wall.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-del]");
        if (!btn) return;
        const id = btn.getAttribute("data-del");
        if (id.indexOf("seed-") === 0) {
          const hidden = readLS(LS_HIDDEN_NOTES, []);
          hidden.push(id);
          writeLS(LS_HIDDEN_NOTES, hidden);
        } else {
          writeLS(LS_NOTES, readLS(LS_NOTES, []).filter((n) => n.id !== id));
        }
        renderNotes();
      });
    }
  }

  /* ---------------- 每日一句 ---------------- */
  function renderQuote() {
    const el = $("#dailyQuote");
    if (!el) return;
    const quotes = DATA.quotes || [];
    if (!quotes.length) { el.textContent = "日子还长，故事还在写。"; return; }
    const dayIndex = dayNumber(startOfToday());
    el.textContent = quotes[dayIndex % quotes.length];
  }

  /* ---------------- 灯箱 ---------------- */
  let lbIndex = 0;
  let lbItems = [];
  let lastFocused = null;

  function openLightbox(index, list) {
    const box = $("#lightbox");
    lbItems = list && list.length ? list : photos;
    if (!box || !lbItems.length) return;
    lbIndex = (index + lbItems.length) % lbItems.length;
    lastFocused = document.activeElement;
    paintLightbox();
    box.classList.add("is-open");
    box.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    $("#lbClose").focus();
  }

  function paintLightbox() {
    const p = lbItems[lbIndex];
    if (!p) return;
    const img = $("#lbImage");
    img.src = p.src;
    img.alt = p.title || "";
    img.onerror = () => { img.onerror = null; img.src = FALLBACK_IMG; };
    $("#lbCaption").textContent = [p.title, p.note].filter(Boolean).join(" · ");
  }

  function closeLightbox() {
    const box = $("#lightbox");
    if (!box) return;
    box.classList.remove("is-open");
    box.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }

  function stepLightbox(dir) {
    if (!lbItems.length) return;
    lbIndex = (lbIndex + dir + lbItems.length) % lbItems.length;
    paintLightbox();
  }

  function setupLightbox() {
    const box = $("#lightbox");
    if (!box) return;
    $("#lbClose").addEventListener("click", closeLightbox);
    $("#lbPrev").addEventListener("click", () => stepLightbox(-1));
    $("#lbNext").addEventListener("click", () => stepLightbox(1));
    box.addEventListener("click", (e) => { if (e.target === box) closeLightbox(); });

    document.addEventListener("keydown", (e) => {
      if (box.classList.contains("is-open")) {
        if (e.key === "Escape") closeLightbox();
        if (e.key === "ArrowLeft") stepLightbox(-1);
        if (e.key === "ArrowRight") stepLightbox(1);
      }
    });
  }

  /* ---------------- 设置抽屉 ---------------- */
  function fillSettings() {
    const map = {
      fNameA: couple.nameA || "",
      fNameB: couple.nameB || "",
      fStartDate: couple.startDate || "",
      fLocation: couple.location || "",
      fTagline: couple.tagline || "",
      fIntro: couple.intro || "",
      fArt: couple.art || "",
    };
    Object.keys(map).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = map[id];
    });
  }

  function openDrawer() {
    fillSettings();
    const drawer = $("#drawer");
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    setTimeout(() => document.getElementById("fNameA").focus(), 260);
  }

  function closeDrawer() {
    const drawer = $("#drawer");
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function setupDrawer() {
    $("#openSettings").addEventListener("click", openDrawer);
    $$("[data-close-drawer]").forEach((el) => el.addEventListener("click", closeDrawer));

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && $("#drawer").classList.contains("is-open")) closeDrawer();
    });

    $("#saveSettings").addEventListener("click", () => {
      couple.nameA = $("#fNameA").value.trim() || baseCouple.nameA;
      couple.nameB = $("#fNameB").value.trim() || baseCouple.nameB;
      couple.startDate = $("#fStartDate").value || baseCouple.startDate;
      couple.location = $("#fLocation").value.trim();
      couple.tagline = $("#fTagline").value.trim();
      couple.intro = $("#fIntro").value.trim();
      couple.art = $("#fArt").value.trim() || baseCouple.art;

      if (!writeLS(LS_SETTINGS, {
        nameA: couple.nameA, nameB: couple.nameB, startDate: couple.startDate,
        location: couple.location, tagline: couple.tagline, intro: couple.intro, art: couple.art,
      })) {
        setStatus("浏览器不让存（可能是隐私模式），导出 content.js 也能用。", true);
        return;
      }
      setStatus("已保存到这台设备。");
      refreshAll();
    });

    $("#exportData").addEventListener("click", () => {
      const data = currentData();
      const text = "/* 由「我们的小时光」导出 · " + formatShort(new Date()) + " */\nwindow.LOVE_DATA = " + JSON.stringify(data, null, 2) + ";\n";
      const blob = new Blob([text], { type: "text/javascript;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "content.js";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      setStatus("已导出 content.js，替换 data/content.js 后重新部署即可。");
    });

    $("#resetSettings").addEventListener("click", () => {
      try { localStorage.removeItem(LS_SETTINGS); } catch (e) {}
      Object.keys(baseCouple).forEach((k) => { couple[k] = baseCouple[k]; });
      fillSettings();
      refreshAll();
      setStatus("已恢复默认内容。");
    });
  }

  function setStatus(msg, isError) {
    const el = $("#drawerStatus");
    if (!el) return;
    el.textContent = msg;
    el.classList.toggle("is-error", !!isError);
    clearTimeout(setStatus._t);
    setStatus._t = setTimeout(() => { el.textContent = ""; }, 6000);
  }

  /* ---------------- 分享 ---------------- */
  function setupShare() {
    const btn = $("#shareBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      const url = location.href;
      try {
        if (navigator.share) {
          await navigator.share({ title: document.title, url: url });
          return;
        }
        await navigator.clipboard.writeText(url);
        toast("链接已经复制好啦");
      } catch (e) {
        toast("复制失败，手动复制地址栏吧");
      }
    });
  }

  function toast(msg) {
    let el = $("#toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.className = "toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("is-on");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("is-on"), 2400);
  }

  /* ---------------- 爱心纸屑 ---------------- */
  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function burstFrom(sourceEl, amount) {
    if (prefersReducedMotion()) return;
    const layer = $("#confettiLayer");
    if (!layer) return;
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    if (sourceEl && sourceEl.getBoundingClientRect) {
      const r = sourceEl.getBoundingClientRect();
      x = r.left + r.width / 2;
      y = r.top + Math.min(r.height / 2, 80);
    }
    const n = amount || 10;
    const glyphs = ["♥", "♡", "✦", "♥"];
    for (let i = 0; i < n; i++) {
      const s = document.createElement("span");
      s.className = "confetti";
      s.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
      s.style.left = x + "px";
      s.style.top = y + "px";
      s.style.color = ["#e4573d", "#f2c14e", "#a9c3d9", "#e4573d"][Math.floor(Math.random() * 4)];
      s.style.setProperty("--dx", (Math.random() * 200 - 100).toFixed(0) + "px");
      s.style.setProperty("--rot", (Math.random() * 160 - 80).toFixed(0) + "deg");
      s.style.animationDelay = (i * 28) + "ms";
      s.style.fontSize = (13 + Math.random() * 12).toFixed(0) + "px";
      layer.appendChild(s);
      setTimeout(() => s.remove(), 1900 + i * 30);
    }
  }

  /* ---------------- 滚动出现 / 导航高亮 ---------------- */
  let revealObserver = null;

  function observeReveals() {
    if (!("IntersectionObserver" in window)) {
      $$(".reveal").forEach((el) => el.classList.add("in"));
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("in");
              revealObserver.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.06 }
      );
    }
    $$(".reveal").forEach((el) => {
      if (!el.classList.contains("in")) revealObserver.observe(el);
    });
  }

  function setupNavHighlight() {
    const links = $$(".nav a");
    const sections = links
      .map((a) => document.querySelector(a.getAttribute("href")))
      .filter(Boolean);
    if (!sections.length || !("IntersectionObserver" in window)) return;

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + entry.target.id));
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach((s) => io.observe(s));

    const topbar = $("#topbar");
    const onScroll = () => topbar.classList.toggle("is-stuck", window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------------- 初始化 ---------------- */
  function refreshAll() {
    applyBindings();
    refreshNoteOptions();
    renderCounters();
    renderStats();
    renderTimeline();
    renderGallery();
    renderSamples();
    renderDates();
    renderWishes();
    renderNotes();
    renderQuote();
    observeReveals();
  }

  function init() {
    refreshAll();
    setupNoteForm();
    setupLightbox();
    setupDrawer();
    setupShare();
    setupNavHighlight();

    // 点首页插画撒爱心
    const art = $(".hero__art");
    if (art) art.addEventListener("click", () => burstFrom(art, 14));
    const primary = $(".btn--primary");
    if (primary) primary.addEventListener("click", () => burstFrom(primary, 8));

    // 点任意位置的 ♥ 也可以
    document.addEventListener("click", (e) => {
      const heart = e.target.closest(".brand__heart");
      if (heart) burstFrom(heart, 8);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
