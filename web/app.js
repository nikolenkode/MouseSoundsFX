/* =====================================================================
   Mouse Sound FX — фронтенд.

   Ничего не решает самостоятельно: каждое пользовательское действие
   уходит в window.pywebview.api.*, а всё, что видно на экране, рисуется
   заново из state, который вернул Python. Здесь нет ни одной переменной,
   которая бы дублировала или подменяла состояние из backend/api.py —
   только DOM да временные UI-флаги (какой попап открыт, какой файл
   сейчас выбирается для кастомного звука и т.п.).
   ===================================================================== */

(() => {
  "use strict";

  const els = {
    logoDot: document.getElementById("logoDot"),
    logoFx: document.getElementById("logoFx"),

    themeBtn: document.getElementById("themeBtn"),
    volumeBtn: document.getElementById("volumeBtn"),
    volumeWaves: document.getElementById("volumeWaves"),
    minimizeBtn: document.getElementById("minimizeBtn"),
    closeBtn: document.getElementById("closeBtn"),

    stagePatternLayer: document.getElementById("stagePatternLayer"),
    panelPatternLayer: document.getElementById("panelPatternLayer"),

    powerBtn: document.getElementById("powerBtn"),
    powerInner: document.getElementById("powerInner"),

    partLeft: document.getElementById("partLeft"),
    partRight: document.getElementById("partRight"),
    partMiddle: document.getElementById("partMiddle"),

    releaseToggle: document.getElementById("releaseToggle"),
    stageDivider: document.getElementById("stageDivider"),

    tabs: document.getElementById("tabs"),
    panelTitle: document.getElementById("panelTitle"),
    enableToggle: document.getElementById("enableToggle"),

    soundDropdown: document.getElementById("soundDropdown"),
    soundDropdownBtn: document.getElementById("soundDropdownBtn"),
    soundLabel: document.getElementById("soundLabel"),
    soundDropdownList: document.getElementById("soundDropdownList"),
    playBtn: document.getElementById("playBtn"),

    statusBar: document.getElementById("statusBar"),

    volumePopover: document.getElementById("volumePopover"),
    volumeValue: document.getElementById("volumeValue"),
    volumeSlider: document.getElementById("volumeSlider"),

    themePopover: document.getElementById("themePopover"),
    targetSegmented: document.getElementById("targetSegmented"),
    presetGrid: document.getElementById("presetGrid"),
    patternSection: document.getElementById("patternSection"),
    patternGrid: document.getElementById("patternGrid"),
    hueStrip: document.getElementById("hueStrip"),
    hueMarker: document.getElementById("hueMarker"),
    svSquare: document.getElementById("svSquare"),
    svSafeZone: document.getElementById("svSafeZone"),
    svMarker: document.getElementById("svMarker"),
    hexSwatch: document.getElementById("hexSwatch"),
    hexInput: document.getElementById("hexInput"),
    hexOkBtn: document.getElementById("hexOkBtn"),

    nameModalOverlay: document.getElementById("nameModalOverlay"),
    nameInput: document.getElementById("nameInput"),
    nameError: document.getElementById("nameError"),
    nameCancelBtn: document.getElementById("nameCancelBtn"),
    nameSaveBtn: document.getElementById("nameSaveBtn"),

    confirmModalOverlay: document.getElementById("confirmModalOverlay"),
    confirmMessage: document.getElementById("confirmMessage"),
    confirmCancelBtn: document.getElementById("confirmCancelBtn"),
    confirmOkBtn: document.getElementById("confirmOkBtn"),
  };

  const PATTERN_SVG = {
    honeycomb: '<rect width="100%" height="100%" fill="url(#pat-honeycomb)"/>',
    waves: '<rect width="100%" height="100%" fill="url(#pat-waves)"/>',
    diamond: '<rect width="100%" height="100%" fill="url(#pat-diamond)"/>',
    dots: '<rect width="100%" height="100%" fill="url(#pat-dots)"/>',
    grid: '<rect width="100%" height="100%" fill="url(#pat-grid)"/>',
    stripes: '<rect width="100%" height="100%" fill="url(#pat-stripes)"/>',
    none: "",
  };

  let state = null;
  // Имя, которое пользователь только что подтвердил в модалке названия
  // звука — нужно, если сервер ответит "такое имя уже занято" и придётся
  // показать модалку подтверждения замены.
  let pendingConfirmName = null;

  // ============================== ВЫЗОВЫ API ==============================

  async function api(method, ...args) {
    return window.pywebview.api[method](...args);
  }

  /** Для методов, которые возвращают {state, ...} — перерисовывает UI и
   *  отдаёт результат вызывающему коду для проверки ok/reason. */
  async function act(method, ...args) {
    const result = await api(method, ...args);
    if (result && result.state) render(result.state);
    return result;
  }

  // ============================== РЕНДЕР ==============================

  function render(s) {
    state = s;

    applyColors(s.colors);
    renderMaster(s);
    renderVolume(s);
    renderButtons(s);
    renderSound(s);
    renderStatus(s);
    renderPatternLayers(s);
    renderThemePopoverContent(s);
  }

  function applyColors(c) {
    const root = document.documentElement.style;
    root.setProperty("--color-accent", c.accent);
    root.setProperty("--color-background", c.background);
    root.setProperty("--color-body", c.body);
    root.setProperty("--color-outline", c.outline);
    root.setProperty("--color-pattern", c.pattern);
    root.setProperty("--color-stage", c.stage);
    root.setProperty("--color-stage-outline", c.stage_outline);
    root.setProperty("--color-stage-pattern", c.stage_pattern);
  }

  function renderMaster(s) {
    els.powerInner.classList.toggle("is-on", s.master);
  }

  function renderVolume(s) {
    els.volumeSlider.value = Math.round(s.volume * 100);
    els.volumeValue.textContent = `${Math.round(s.volume * 100)}%`;

    const muted = !s.master || s.volume <= 0.02;
    if (muted) {
      els.volumeWaves.innerHTML =
        '<line x1="20" y1="11" x2="26" y2="23"></line>' +
        '<line x1="26" y1="11" x2="20" y2="23"></line>';
    } else {
      let paths = "";
      if (s.volume > 0.03) paths += '<path d="M20 13 Q24.5 17 20 21" fill="none"></path>';
      if (s.volume > 0.4) paths += '<path d="M22.5 9.5 Q29.5 17 22.5 24.5" fill="none"></path>';
      els.volumeWaves.innerHTML = paths;
    }
  }

  function renderButtons(s) {
    const cur = s.current_button;

    for (const [name, el] of [["left", els.partLeft], ["right", els.partRight], ["middle", els.partMiddle]]) {
      el.classList.toggle("is-selected", name === cur);
    }

    els.tabs.querySelectorAll(".tab").forEach((tab) => {
      tab.classList.toggle("is-active", tab.dataset.btn === cur);
    });

    els.panelTitle.textContent = `Настройки для: ${s.buttons[cur].title}`;
    els.enableToggle.checked = s.buttons[cur].enabled;
    els.releaseToggle.checked = s.release_sound;
  }

  function renderSound(s) {
    const cur = s.buttons[s.current_button];
    els.soundLabel.textContent = cur.sound_label;

    const items = [];
    for (const pack of s.sound_catalog.builtin) {
      items.push(
        `<div class="dropdown-item${pack.id === cur.sound_id && cur.sound_kind === "builtin" ? " is-active" : ""}" data-kind="builtin" data-id="${escapeAttr(pack.id)}">${escapeHtml(pack.label)}</div>`
      );
    }
    if (s.sound_catalog.custom.length) {
      items.push('<div class="dropdown-separator"></div>');
      for (const name of s.sound_catalog.custom) {
        items.push(
          `<div class="dropdown-item${name === cur.sound_id && cur.sound_kind === "custom" ? " is-active" : ""}" data-kind="custom" data-id="${escapeAttr(name)}">${escapeHtml(name)}</div>`
        );
      }
    }
    items.push('<div class="dropdown-separator"></div>');
    items.push('<div class="dropdown-item dropdown-item--add" data-action="add-custom">➕ Добавить свой...</div>');

    els.soundDropdownList.innerHTML = items.join("");
  }

  function renderStatus(s) {
    els.statusBar.textContent = s.status || "";
  }

  function renderPatternLayers(s) {
    // Обе колонки показывают ОДИН и тот же выбранный узор — просто с
    // разным оттенком (stage_pattern чуть теплее/акцентнее, pattern —
    // нейтральный). currentColor внутри <pattern> берёт цвет отсюда.
    const svgContent = PATTERN_SVG[s.bg_pattern] || "";
    els.stagePatternLayer.innerHTML = svgContent;
    els.stagePatternLayer.style.color = "var(--color-stage-pattern)";
    els.panelPatternLayer.innerHTML = svgContent;
    els.panelPatternLayer.style.color = "var(--color-pattern)";
  }

  // ============================== ОКНО (без рамки — своя шапка) ==============================

  els.minimizeBtn.addEventListener("click", () => api("minimize_window"));
  els.closeBtn.addEventListener("click", () => api("close_window"));

  // ============================== ГЛАВНЫЙ ВЫКЛЮЧАТЕЛЬ / ГРОМКОСТЬ ==============================

  els.powerBtn.addEventListener("click", () => act("toggle_master"));

  els.releaseToggle.addEventListener("change", () => act("toggle_release_sound"));

  let volumeRaf = null;
  els.volumeSlider.addEventListener("input", () => {
    const value = Number(els.volumeSlider.value) / 100;
    els.volumeValue.textContent = `${Math.round(value * 100)}%`;
    if (volumeRaf) return;
    volumeRaf = requestAnimationFrame(async () => {
      volumeRaf = null;
      await act("set_volume", value);
    });
  });

  // ============================== КНОПКИ МЫШИ / ВКЛАДКИ ==============================

  function wireButtonSelectors() {
    for (const el of [els.partLeft, els.partRight, els.partMiddle]) {
      el.addEventListener("click", () => act("select_button", el.dataset.btn));
    }
    els.tabs.addEventListener("click", (e) => {
      const tab = e.target.closest(".tab");
      if (tab) act("select_button", tab.dataset.btn);
    });
  }

  els.enableToggle.addEventListener("change", () => act("set_button_enabled", els.enableToggle.checked));

  // ============================== ВЫБОР ЗВУКА ==============================

  function toggleDropdown(open) {
    const willOpen = open ?? !els.soundDropdownList.classList.contains("is-open");
    els.soundDropdownList.classList.toggle("is-open", willOpen);
    els.soundDropdownBtn.setAttribute("aria-expanded", String(willOpen));
  }

  els.soundDropdownBtn.addEventListener("click", () => toggleDropdown());

  els.soundDropdownList.addEventListener("click", async (e) => {
    const item = e.target.closest(".dropdown-item");
    if (!item) return;
    toggleDropdown(false);

    if (item.dataset.action === "add-custom") {
      await startAddCustomSound();
      return;
    }
    await act("select_sound", item.dataset.kind, item.dataset.id);
  });

  els.playBtn.addEventListener("click", async () => {
    els.playBtn.classList.remove("is-flashing");
    // reflow, чтобы анимацию можно было перезапустить кликом подряд
    void els.playBtn.offsetWidth;
    els.playBtn.classList.add("is-flashing");
    await act("preview_sound");
  });

  // ---- добавление своего звука ----

  async function startAddCustomSound() {
    const picked = await api("pick_custom_sound_file");
    if (!picked || !picked.ok) {
      if (picked && picked.error) showTransientStatus(`Не удалось воспроизвести файл: ${picked.error}`);
      return;
    }
    openNameModal(picked.suggested_name || "");
  }

  function openNameModal(prefill) {
    els.nameError.textContent = "";
    els.nameInput.value = prefill;
    els.nameInput.classList.remove("is-invalid");
    els.nameModalOverlay.classList.add("is-open");
    els.nameInput.focus();
    els.nameInput.select();
  }

  function closeNameModal() {
    els.nameModalOverlay.classList.remove("is-open");
  }

  async function trySaveCustomName(overwrite) {
    const name = els.nameInput.value.trim();
    if (!name) {
      els.nameInput.classList.add("is-invalid");
      els.nameError.textContent = "Введите название";
      return;
    }
    const result = await act("confirm_custom_sound_name", name, overwrite);
    if (result.ok) {
      closeNameModal();
      return;
    }
    if (result.reason === "reserved") {
      els.nameInput.classList.add("is-invalid");
      els.nameError.textContent = "Это имя занято, выберите другое";
    } else if (result.reason === "exists") {
      pendingConfirmName = name;
      els.confirmMessage.textContent = `Звук «${name}» уже есть. Заменить его?`;
      els.confirmModalOverlay.classList.add("is-open");
    } else if (result.reason === "error") {
      els.nameError.textContent = result.message || "Не удалось сохранить файл";
    }
  }

  els.nameCancelBtn.addEventListener("click", async () => {
    closeNameModal();
    await api("cancel_custom_sound");
  });
  els.nameSaveBtn.addEventListener("click", () => trySaveCustomName(false));
  els.nameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") trySaveCustomName(false);
    if (e.key === "Escape") els.nameCancelBtn.click();
  });
  els.nameInput.addEventListener("input", () => {
    els.nameInput.classList.remove("is-invalid");
    els.nameError.textContent = "";
  });

  els.confirmCancelBtn.addEventListener("click", () => {
    // Как и в оригинале: отказ от замены не отменяет добавление звука
    // целиком, а возвращает к вводу другого имени.
    els.confirmModalOverlay.classList.remove("is-open");
    openNameModal(pendingConfirmName || "");
  });
  els.confirmOkBtn.addEventListener("click", async () => {
    els.confirmModalOverlay.classList.remove("is-open");
    await trySaveCustomName(true);
  });

  function showTransientStatus(msg) {
    els.statusBar.textContent = msg;
    setTimeout(() => {
      if (state) els.statusBar.textContent = state.status || "";
    }, 4000);
  }

  // ============================== ГРОМКОСТЬ / ТЕМА — ПОПАПЫ ==============================

  function openPopover(el) {
    closeAllPopovers();
    el.classList.add("is-open");
  }
  function closeAllPopovers() {
    els.volumePopover.classList.remove("is-open");
    els.themePopover.classList.remove("is-open");
  }

  els.volumeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = !els.volumePopover.classList.contains("is-open");
    closeAllPopovers();
    if (willOpen) els.volumePopover.classList.add("is-open");
  });

  els.themeBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const willOpen = !els.themePopover.classList.contains("is-open");
    closeAllPopovers();
    if (willOpen) {
      await act("open_theme_popover");
      els.themePopover.classList.add("is-open");
    }
  });

  document.addEventListener("pointerdown", (e) => {
    if (
      els.volumePopover.classList.contains("is-open") &&
      !els.volumePopover.contains(e.target) &&
      !els.volumeBtn.contains(e.target)
    ) {
      els.volumePopover.classList.remove("is-open");
    }
    if (
      els.themePopover.classList.contains("is-open") &&
      !els.themePopover.contains(e.target) &&
      !els.themeBtn.contains(e.target)
    ) {
      els.themePopover.classList.remove("is-open");
    }
    if (
      els.soundDropdownList.classList.contains("is-open") &&
      !els.soundDropdown.contains(e.target)
    ) {
      toggleDropdown(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (els.confirmModalOverlay.classList.contains("is-open")) {
      els.confirmCancelBtn.click();
      return;
    }
    if (els.nameModalOverlay.classList.contains("is-open")) {
      els.nameCancelBtn.click();
      return;
    }
    closeAllPopovers();
    toggleDropdown(false);
  });

  // ============================== ТЕМА: СЕГМЕНТ / ПРЕСЕТЫ / УЗОРЫ ==============================

  function renderThemePopoverContent(s) {
    // Сегментированный переключатель Акцент/Фон
    els.targetSegmented.querySelectorAll(".segmented-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.target === s.theme_target);
    });

    const activeHex = s.theme_target === "accent" ? s.colors.accent : s.colors.background;

    // Пресеты (свои для акцента и для фона)
    const presets = s.theme_target === "accent" ? s.theme_presets : s.bg_presets;
    els.presetGrid.innerHTML = presets
      .map(
        (p) => `
      <button type="button" class="preset-cell${p.hex.toLowerCase() === activeHex.toLowerCase() ? " is-active" : ""}" data-hex="${escapeAttr(p.hex)}">
        <span class="preset-swatch" style="background:${escapeAttr(p.hex)}"></span>
        <span class="preset-name">${escapeHtml(p.name)}</span>
      </button>`
      )
      .join("");

    // Узор фона — показываем только на вкладке "Фон"
    els.patternSection.style.display = s.theme_target === "background" ? "" : "none";
    if (s.theme_target === "background") {
      els.patternGrid.innerHTML = s.pattern_options
        .map(
          (p) => `
        <button type="button" class="pattern-cell${p.id === s.bg_pattern ? " is-active" : ""}" data-pattern="${escapeAttr(p.id)}">
          <span class="pattern-thumb">${patternThumbSvg(p.id)}</span>
          <span class="pattern-name">${escapeHtml(p.label)}</span>
        </button>`
        )
        .join("");
    }

    // Свой цвет: полоса оттенка, квадрат sat/val, hex
    els.hueMarker.style.left = `${s.picker.hue * 100}%`;
    els.svMarker.style.left = `${s.picker.sat * 100}%`;
    els.svMarker.style.top = `${(1 - s.picker.val) * 100}%`;
    document.documentElement.style.setProperty("--picker-hue-deg", `${s.picker.hue * 360}deg`);

    if (s.theme_target === "accent") {
      const [sLo, sHi] = s.accent_range.sat;
      const [vLo, vHi] = s.accent_range.val;
      els.svSafeZone.style.display = "";
      els.svSafeZone.style.left = `${sLo * 100}%`;
      els.svSafeZone.style.width = `${(sHi - sLo) * 100}%`;
      els.svSafeZone.style.top = `${(1 - vHi) * 100}%`;
      els.svSafeZone.style.height = `${(vHi - vLo) * 100}%`;
    } else {
      els.svSafeZone.style.display = "none";
    }

    els.hexSwatch.style.background = activeHex;
    if (document.activeElement !== els.hexInput) {
      els.hexInput.value = activeHex.toUpperCase();
    }
  }

  function patternThumbSvg(id) {
    if (id === "none") {
      return '<svg viewBox="0 0 44 28" width="100%" height="100%"><line x1="15" y1="10" x2="29" y2="18" stroke="currentColor" stroke-width="1.5"/><line x1="29" y1="10" x2="15" y2="18" stroke="currentColor" stroke-width="1.5"/></svg>';
    }
    const fill = { honeycomb: "pat-honeycomb", waves: "pat-waves", diamond: "pat-diamond", dots: "pat-dots", grid: "pat-grid", stripes: "pat-stripes" }[id];
    return `<svg viewBox="0 0 44 28" width="100%" height="100%"><rect width="100%" height="100%" fill="url(#${fill})" transform="scale(0.5)"/></svg>`;
  }

  els.targetSegmented.addEventListener("click", (e) => {
    const btn = e.target.closest(".segmented-btn");
    if (btn) act("set_theme_target", btn.dataset.target);
  });

  els.presetGrid.addEventListener("click", (e) => {
    const cell = e.target.closest(".preset-cell");
    if (cell) act("apply_preset", cell.dataset.hex);
  });

  els.patternGrid.addEventListener("click", (e) => {
    const cell = e.target.closest(".pattern-cell");
    if (cell) act("set_bg_pattern", cell.dataset.pattern);
  });

  // ---- Полоса оттенка и квадрат насыщенность/яркость ----

  function dragTrack(el, onMove) {
    let dragging = false;
    let raf = null;
    let pending = null;

    function handle(clientX, clientY) {
      const rect = el.getBoundingClientRect();
      const relX = clamp01((clientX - rect.left) / rect.width);
      const relY = clamp01((clientY - rect.top) / rect.height);
      pending = [relX, relY];
      if (raf) return;
      raf = requestAnimationFrame(async () => {
        raf = null;
        const [x, y] = pending;
        await onMove(x, y);
      });
    }

    el.addEventListener("pointerdown", (e) => {
      dragging = true;
      el.setPointerCapture(e.pointerId);
      handle(e.clientX, e.clientY);
    });
    el.addEventListener("pointermove", (e) => {
      if (dragging) handle(e.clientX, e.clientY);
    });
    el.addEventListener("pointerup", (e) => {
      dragging = false;
      try { el.releasePointerCapture(e.pointerId); } catch (_) { /* noop */ }
    });
  }

  dragTrack(els.hueStrip, (x) => act("pick_hue", x));
  dragTrack(els.svSquare, (x, y) => act("pick_sv", x, y));

  els.hexOkBtn.addEventListener("click", () => applyHexInput());
  els.hexInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") applyHexInput();
  });
  els.hexInput.addEventListener("input", () => els.hexInput.classList.remove("is-invalid"));

  async function applyHexInput() {
    const result = await act("apply_hex", els.hexInput.value);
    els.hexInput.classList.toggle("is-invalid", !result.ok);
  }

  // ============================== УТИЛИТЫ ==============================

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
  function escapeAttr(str) {
    return String(str).replace(/"/g, "&quot;");
  }

  // ============================== СТАРТ ==============================

  function boot() {
    wireButtonSelectors();
    api("get_state").then(render);
  }

  if (window.pywebview && window.pywebview.api) {
    boot();
  } else {
    window.addEventListener("pywebviewready", boot);
  }
})();
