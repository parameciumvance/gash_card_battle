/* 事件驅動動畫層 — 統一管線:量測 → 阻塞演出 → 重繪 → 疊加特效。
 * 疊加式(翻頁/飛卡/MP token/負傷棄牌)不阻塞盤面更新;
 * 阻塞式(coin_flipped、showdown)短暫延後重繪(500-800ms),帶 1.5s 硬性逾時保底。
 * prefers-reduced-motion 時全部跳過直接重繪。裁決在伺服器,動畫不影響指令與計時。 */

"use strict";

const Anim = (() => {
  const HARD_TIMEOUT = 1500;
  const BLOCKING = new Set(["coin_flipped", "showdown"]);
  let queue = Promise.resolve();

  function reduced() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function overlay() { return document.getElementById("anim-overlay"); }

  function boardVisible() {
    const layout = document.getElementById("layout");
    return layout && !layout.classList.contains("hidden");
  }

  function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise((res) => setTimeout(res, ms))]);
  }

  function wait(ms) { return new Promise((res) => setTimeout(res, ms)); }

  // 進入點:批次排隊,確保前一批演完才處理下一批(全域 S 永遠渲染最新)
  function apply(events, prevState, renderFn) {
    queue = queue
      .then(() => run(events, prevState, renderFn))
      .catch(() => { try { renderFn(); } catch (_) { /* 保底 */ } });
    return queue;
  }

  async function run(events, prevState, renderFn) {
    if (reduced() || !events.length || !boardVisible() || !overlay()) {
      renderFn();
      return;
    }
    const marks = measure(events);
    const blocking = events.filter((ev) =>
      BLOCKING.has(ev.type) && !(ev.type === "coin_flipped" && ev.source === "setup"));
    for (const ev of blocking) {
      await withTimeout(playBlocking(ev, prevState), HARD_TIMEOUT);
    }
    renderFn();
    playOverlays(events, marks);
  }

  // ---------------------------------------------------------------- 量測(重繪前)

  function zoneOf(p) {
    return document.querySelector(`.player-zone[data-player="${p}"]`);
  }

  function measure(events) {
    const marks = { bookRect: {}, trayRect: {}, cardSrc: {}, slotRect: {} };
    for (const p of [0, 1]) {
      const zone = zoneOf(p);
      if (!zone) continue;
      const cover = zone.querySelector(".book-cover");
      const tray = zone.querySelector(".mp-tray");
      if (cover) marks.bookRect[p] = cover.getBoundingClientRect();
      if (tray) marks.trayRect[p] = tray.getBoundingClientRect();
    }
    for (const ev of events) {
      if (ev.type === "card_played") {
        const zone = zoneOf(ev.player);
        const el = zone && zone.querySelector(`.book-pages [data-card="${ev.card}"]`);
        marks.cardSrc[ev.seq] = (el || null) && el.getBoundingClientRect();
      }
      if (ev.type === "mamodo_discarded" || ev.type === "mamodo_injured") {
        const zone = zoneOf(ev.player);
        const el = zone && zone.querySelector(`[data-slot-uid="${ev.slot}"][data-zone-kind="mamodo"]`);
        if (el) marks.slotRect[ev.seq] = el.getBoundingClientRect();
      }
    }
    return marks;
  }

  // ---------------------------------------------------------------- 疊加式(重繪後)

  function playOverlays(events, marks) {
    const damagedPlayers = new Set(
      events.filter((e) => e.type === "damage_dealt").map((e) => e.player));
    for (const ev of events) {
      try { playOverlay(ev, marks, damagedPlayers); } catch (_) { /* 單一特效失敗不影響盤面 */ }
    }
  }

  function playOverlay(ev, marks, damagedPlayers) {
    switch (ev.type) {
      case "pages_flipped":
      case "pages_turned":
        return pageFlip(ev.player, damagedPlayers.has(ev.player), Math.abs(ev.count) || 1);
      case "card_played":
        return flyCard(ev, marks);
      case "mp_changed":
        return mpTokens(ev, marks);
      case "mamodo_injured":
        return hitFlash(ev);
      case "mamodo_discarded":
        return discardFade(ev, marks);
    }
  }

  // 翻頁:書頁翻轉片覆蓋於該方魔本右半,rotateY 過渡;翻 N 頁錯開演 N 次(上限 4);
  // 傷害翻頁帶紅閃
  function pageFlip(p, damage, count = 1) {
    const n = Math.min(count, 4);
    for (let i = 0; i < n; i++) {
      setTimeout(() => spawnFlap(p, damage), i * 170);
    }
  }

  function spawnFlap(p, damage) {
    const zone = zoneOf(p);
    const cover = zone && zone.querySelector(".book-cover");
    if (!cover) return;
    const rect = cover.getBoundingClientRect();
    const flap = document.createElement("div");
    flap.className = "fx-page-flap" + (damage ? " damage" : "");
    Object.assign(flap.style, {
      left: `${rect.left + rect.width / 2}px`, top: `${rect.top}px`,
      width: `${rect.width / 2}px`, height: `${rect.height}px`,
    });
    overlay().appendChild(flap);
    flap.addEventListener("animationend", () => flap.remove());
    setTimeout(() => flap.remove(), 900);
    if (damage) {
      cover.classList.add("fx-damage-glow");
      setTimeout(() => cover.classList.remove("fx-damage-glow"), 700);
    }
  }

  // 出卡:FLIP — 來源=魔本頁位(重繪前量測),目標=場上欄位(重繪後)
  function flyCard(ev, marks) {
    const zone = zoneOf(ev.player);
    const target = zone && zone.querySelector(
      `[data-slot-uid="${ev.slot}"][data-zone-kind="${ev.zone}"]`);
    if (!target) return;
    const from = marks.cardSrc[ev.seq] || marks.bookRect[ev.player];
    if (!from) return;
    const to = target.getBoundingClientRect();
    const ghost = target.cloneNode(true);
    ghost.className = target.className + " fx-fly-card";
    Object.assign(ghost.style, {
      left: `${from.left}px`, top: `${from.top}px`,
      width: `${from.width}px`, height: `${from.height}px`,
    });
    overlay().appendChild(ghost);
    target.classList.add("fx-arriving");
    // 強制 reflow 後過渡到目標位置
    ghost.getBoundingClientRect();
    Object.assign(ghost.style, {
      left: `${to.left}px`, top: `${to.top}px`,
      width: `${to.width}px`, height: `${to.height}px`,
    });
    setTimeout(() => {
      ghost.remove();
      target.classList.remove("fx-arriving");
    }, 480);
  }

  // MP 增減:token 在魔本與托盤之間飛行(增=書→盤、減=盤→書並淡出)
  function mpTokens(ev, marks) {
    const p = ev.player;
    const zone = zoneOf(p);
    const tray = zone && zone.querySelector(".mp-tray");
    const book = marks.bookRect[p];
    if (!tray || !book) return;
    const trayRect = tray.getBoundingClientRect();
    const gain = ev.delta > 0;
    const n = Math.min(Math.abs(ev.delta), 6);
    for (let i = 0; i < n; i++) {
      const tk = document.createElement("span");
      tk.className = "fx-mp-token" + (gain ? "" : " spend");
      const from = gain ? book : trayRect;
      const to = gain ? trayRect : book;
      Object.assign(tk.style, {
        left: `${from.left + from.width / 2}px`,
        top: `${from.top + from.height / 2}px`,
      });
      overlay().appendChild(tk);
      setTimeout(() => {
        Object.assign(tk.style, {
          left: `${to.left + to.width / 2 + (i - n / 2) * 10}px`,
          top: `${to.top + to.height / 2}px`,
          opacity: gain ? "1" : "0",
        });
      }, 40 + i * 60);
      setTimeout(() => tk.remove(), 700 + i * 60);
    }
  }

  // 負傷:紅閃(橫倒由重繪後的 .injured 樣式呈現)
  function hitFlash(ev) {
    const zone = zoneOf(ev.player);
    const el = zone && zone.querySelector(
      `[data-slot-uid="${ev.slot}"][data-zone-kind="mamodo"]`);
    if (!el) return;
    el.classList.add("fx-hit");
    el.addEventListener("animationend", () => el.classList.remove("fx-hit"), { once: true });
  }

  // 魔物送墓:原位灰化縮小淡出
  function discardFade(ev, marks) {
    const rect = marks.slotRect[ev.seq];
    if (!rect) return;
    const ghost = document.createElement("div");
    ghost.className = "fx-discard";
    Object.assign(ghost.style, {
      left: `${rect.left}px`, top: `${rect.top}px`,
      width: `${rect.width}px`, height: `${rect.height}px`,
    });
    overlay().appendChild(ghost);
    ghost.getBoundingClientRect();
    ghost.classList.add("gone");
    setTimeout(() => ghost.remove(), 800);
  }

  // ---------------------------------------------------------------- 阻塞式

  function playBlocking(ev, prevState) {
    if (ev.type === "coin_flipped") return coinFlip(ev);
    if (ev.type === "showdown") return showdown(ev, prevState);
    return Promise.resolve();
  }

  // 3D 硬幣:中央 rotateX 旋轉,結果面朝前落定,停留一拍(合計約 800ms)
  async function coinFlip(ev) {
    const wrap = document.createElement("div");
    wrap.className = "fx-coin-wrap";
    const coin = document.createElement("div");
    coin.className = `fx-coin land-${ev.result}`;
    coin.innerHTML =
      `<div class="face heads">${t("anim.coin.heads")}</div>` +
      `<div class="face tails">${t("anim.coin.tails")}</div>`;
    wrap.appendChild(coin);
    overlay().appendChild(wrap);
    await wait(800);
    wrap.remove();
  }

  // 魔力對決:中央橫幅,攻防數字滾動至合計,勝方金光/敗方黯淡(合計約 800ms)
  async function showdown(ev, prevState) {
    const wrap = document.createElement("div");
    wrap.className = "fx-showdown";
    wrap.innerHTML =
      `<div class="sd-side attack"><span class="sd-label">${t("anim.showdown.att")}</span>` +
      `<span class="sd-num" data-final="${ev.attacker_total}">0</span></div>` +
      `<div class="sd-vs">VS</div>` +
      `<div class="sd-side defense"><span class="sd-label">${t("anim.showdown.def")}</span>` +
      `<span class="sd-num" data-final="${ev.defender_total}">0</span></div>`;
    overlay().appendChild(wrap);
    const rollMs = 380;
    const start = performance.now();
    const nums = wrap.querySelectorAll(".sd-num");
    await new Promise((done) => {
      (function tick(now) {
        const k = Math.min(1, (now - start) / rollMs);
        for (const el of nums) {
          el.textContent = Math.round(Number(el.dataset.final) * k);
        }
        if (k < 1) requestAnimationFrame(tick);
        else done();
      })(start);
    });
    const winSide = ev.winner === "attacker" ? ".attack" : ".defense";
    const loseSide = ev.winner === "attacker" ? ".defense" : ".attack";
    wrap.querySelector(winSide).classList.add("win");
    wrap.querySelector(loseSide).classList.add("lose");
    await wait(420);
    wrap.remove();
  }

  return { apply };
})();
