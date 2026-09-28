/* 事件驅動動畫層 — 統一管線:量測 → 時間軸(聚焦展示與阻塞演出依事件順序)→ 重繪 → 疊加特效。
 * 疊加式(翻頁/飛卡/MP token/負傷棄牌)不阻塞盤面更新;
 * 阻塞式(coin_flipped、showdown)短暫延後重繪(500-800ms),帶 1.5s 硬性逾時保底。
 * 聚焦展示:對手行動(與對自己不利的結果)在畫面中央停留,整批播完才重繪;點擊跳過。
 * 動畫開關依演出設定(未設定時依 prefers-reduced-motion);聚焦不屬於動畫,只看聚焦設定。
 * 裁決在伺服器,動畫與聚焦不影響指令與計時。 */

"use strict";

const Anim = (() => {
  const HARD_TIMEOUT = 1500;
  const BLOCKING = new Set(["coin_flipped", "showdown"]);
  let queue = Promise.resolve();
  let pending = 0;   // 排隊中的批數(含播放中),用於追趕

  // ---------------------------------------------------------------- 聚焦展示的事件分類
  // 卡片聚焦:事件 → 要展示的卡號
  const CARD_EVENTS = {
    card_played: (ev) => ev.card,
    book_card_used: (ev) => ev.card,
    ability_used: (ev) => ev.card,
    battle_in_check: (ev) => ev.spell || ev.mamodo,
    defense_declared: (ev) => ev.spell,
    effect_negated: (ev) => ev.source,
  };
  // 文字聚焦(跟在卡片之後時併為結果行)
  const TEXT_EVENTS = new Set([
    "turn_started", "passed", "no_defense", "damage_dealt", "protected", "mamodo_injured",
    "mamodo_discarded", "mamodo_healed", "card_discarded", "pages_turned", "mp_changed",
    "attack_negated", "defense_negated", "game_ended",
  ]);
  const CARD_NO = /^[EMPS]-\d{3}$/;
  // MP 增減只在「效果造成」時列出(reason 為卡號);支付費用(spell:… 等)不列
  function mpByEffect(ev) { return typeof ev.reason === "string" && CARD_NO.test(ev.reason); }

  // 自己發起的這批事件中,只聚焦對自己不利的結果
  function unfavorable(ev, me) {
    switch (ev.type) {
      case "damage_dealt":
      case "mamodo_injured":
      case "mamodo_discarded": return ev.player === me;
      case "pages_turned": return ev.player === me && ev.count > 0;
      case "card_discarded": return ev.player === me && ev.reason !== "cost";
      case "mp_changed": return ev.player === me && ev.delta < 0 && mpByEffect(ev);
      case "attack_negated":
      case "defense_negated": return ev.player !== me;
      case "game_ended": return true;
      default: return false;
    }
  }

  function textWorthy(ev, others, me) {
    if (!TEXT_EVENTS.has(ev.type)) return false;
    if (ev.type === "mp_changed" && !mpByEffect(ev)) return false;
    return others || unfavorable(ev, me);
  }

  function blocking(ev) {
    return BLOCKING.has(ev.type) && !(ev.type === "coin_flipped" && ev.source === "setup");
  }

  // 依事件順序組成時間軸:卡片格 / 文字格 / 阻塞演出;阻塞演出之後的文字另起一格
  function timeline(events, actor, motion) {
    const me = selfPlayer();                      // 0 / 1;本機與觀戰為 null(雙方都聚焦)
    const spot = actor !== null && actor !== undefined && spotlightMode() !== "off" && !document.hidden;
    const others = me === null || actor !== me;
    const steps = [];
    let cur = null;
    for (const ev of events) {
      if (blocking(ev)) {
        if (motion) steps.push({ kind: "anim", ev });
        cur = null;
        continue;
      }
      if (!spot) continue;
      const card = CARD_EVENTS[ev.type] && others ? CARD_EVENTS[ev.type](ev) : null;
      if (card) {
        cur = { kind: "card", card, caption: logLine(ev), lines: [], pass: false };
        steps.push(cur);
      } else if (textWorthy(ev, others, me)) {
        const line = logLine(ev);
        if (!line) continue;
        if (!cur) {
          cur = { kind: "text", caption: null, lines: [], pass: true };
          steps.push(cur);
        }
        cur.lines.push(line);
        cur.pass = cur.pass && ev.type === "passed";
      }
    }
    return steps;
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

  // 進入點:批次排隊,確保前一批演完才處理下一批(全域 S 永遠渲染最新)。
  // actor:發起這批事件的玩家(伺服器推送 / 回應標明;金手指、開局等為 null → 不聚焦)
  function apply(events, prevState, renderFn, actor = null) {
    pending += 1;
    queue = queue
      .then(() => run(events, prevState, renderFn, actor))
      .catch(() => { try { renderFn(); } catch (_) { /* 保底 */ } })
      .finally(() => { pending -= 1; });
    return queue;
  }

  async function run(events, prevState, renderFn, actor) {
    if (!events.length || !boardVisible() || !overlay()) {
      renderFn();
      return;
    }
    const motion = !motionOff();
    const marks = motion ? measure(events) : null;
    // 追趕:排隊太多批時跳過這批的聚焦(最後一批仍會播)
    const steps = timeline(events, pending >= 5 ? null : actor, motion);
    for (const step of steps) {
      if (step.kind === "anim") await withTimeout(playBlocking(step.ev, prevState), HARD_TIMEOUT);
      else await spotlight(step, motion);
    }
    renderFn();
    if (motion) playOverlays(events, marks);
  }

  // ---------------------------------------------------------------- 聚焦展示

  function spotlightMs(step) {
    const fast = spotlightMode() === "fast" || pending >= 2;   // 落後時自動加快
    const base = fast ? 500 : 1000;
    return step.pass ? base / 2 : base;
  }

  function spotlight(step, motion) {
    const el = document.getElementById("spotlight");
    if (!el) return Promise.resolve();
    const ms = spotlightMs(step);
    const panel = document.createElement("div");
    panel.className = "spot-panel" + (step.kind === "card" ? " with-card" : "");
    if (step.kind === "card") {
      const art = document.createElement("img");
      art.className = "spot-art";
      art.src = `/static/assets/cards/${step.card}.jpg`;
      art.onerror = () => { art.onerror = null; art.src = "/static/back.jpg"; };
      const info = document.createElement("div");
      info.className = "spot-info";
      const caption = document.createElement("div");
      caption.className = "spot-caption";
      caption.textContent = step.caption || "";
      const name = document.createElement("div");
      name.className = "spot-name";
      name.textContent = cname(step.card);
      const effect = document.createElement("div");
      effect.className = "spot-effect";
      effect.textContent = (ZH[step.card] && ZH[step.card].effect) || "";
      info.append(caption, name, effect);
      panel.append(art, info);
    }
    if (step.lines.length) {
      const list = document.createElement("div");
      list.className = "spot-lines";
      for (const line of step.lines) {
        const row = document.createElement("div");
        row.textContent = (step.kind === "card" ? "→ " : "") + line;
        list.appendChild(row);
      }
      panel.appendChild(list);
    }
    el.replaceChildren(panel);
    el.dataset.ms = String(ms);
    el.classList.toggle("no-motion", !motion);
    el.classList.remove("hidden");
    return new Promise((done) => {
      let timer = null;
      const finish = () => {
        clearTimeout(timer);
        el.onclick = null;
        el.classList.add("hidden");
        el.replaceChildren();
        done();
      };
      el.onclick = finish;                         // 點擊跳過
      timer = setTimeout(finish, ms);
    });
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
