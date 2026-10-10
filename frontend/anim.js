/* 事件驅動動畫層 — 統一管線:量測 → 時間軸(聚焦展示與阻塞演出依事件順序)→ 重繪 → 疊加特效。
 * 疊加式(翻頁/飛卡/MP token/負傷棄牌)不阻塞盤面更新;
 * 阻塞式(coin_flipped 約 800ms、showdown 對峙演出 2.5 / 1.2 秒)延後重繪,帶硬性逾時保底。
 * 聚焦展示:對手行動(與對自己不利的結果)在畫面中央停留,整批播完才重繪;點擊跳過。
 * 動畫開關依演出設定(未設定時依 prefers-reduced-motion);聚焦不屬於動畫,只看聚焦設定。
 * 音效(sound.js)跟著畫面:聚焦格出現時、阻塞演出時,其餘在重繪時;重繪後輪到自己時提示。
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
    "passed", "no_defense", "damage_dealt", "protected", "mamodo_injured",
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

  // 阻塞演出的保底上限:依演出長度(對峙;能量加上保護者橫置與回原位)再留 1 秒
  function blockingLimit(ev) {
    if (ev.type === "showdown") return faceoffMs() + 1000;
    if (damageHit(ev)) return energyMs() + 2 * guardMs() + 1000;
    if (ev.type === "protected") return 2 * guardMs() + 1000;
    return HARD_TIMEOUT;
  }

  // 造成傷害的事件:魔書受傷、魔物因傷害負傷或送墓
  function damageHit(ev) {
    return ev.type === "damage_dealt" || ev.type === "mamodo_injured"
      || (ev.type === "mamodo_discarded" && ev.reason === "damage");
  }

  function blocking(ev) {
    return BLOCKING.has(ev.type) && !(ev.type === "coin_flipped" && ev.source === "setup");
  }

  // 依事件順序組成時間軸:卡片格 / 文字格 / 回合開始橫幅 / 阻塞演出;阻塞演出與橫幅之後的文字另起一格。
  // skip:排隊過多時跳過這批的聚焦(含橫幅)
  function timeline(events, actor, motion, skip) {
    const me = selfPlayer();                      // 0 / 1;本機與觀戰為 null(雙方都聚焦)
    const enabled = !skip && spotlightMode() !== "off" && !document.hidden;
    const spot = enabled && actor !== null && actor !== undefined;
    const others = me === null || actor !== me;
    const steps = [];
    let cur = null;
    for (const ev of events) {
      if (blocking(ev)) {
        if (motion) steps.push({ kind: "anim", ev, events: [ev] });
        cur = null;
        continue;
      }
      const hit = motion && (damageHit(ev) || ev.type === "protected");
      if (hit) {                                  // 保護 / 傷害:保護者移到傷害對象前、能量衝向承受者,之後的文字另起一格
        steps.push({ kind: "anim", ev, events: [ev] });
        cur = null;
      }
      if (ev.type === "turn_started") {           // 回合開始橫幅:每回合都顯示,不論行動者
        if (enabled) {
          const text = me !== null && ev.player === me ? t("ui.turn_banner.mine")
            : t("ui.turn_banner.named", { player: pname(ev.player) });
          steps.push({ kind: "text", caption: null, lines: [text], pass: true, banner: true, events: [] });
        }
        cur = null;
        continue;
      }
      if (!spot) continue;
      const card = CARD_EVENTS[ev.type] && others ? CARD_EVENTS[ev.type](ev) : null;
      if (card) {
        cur = { kind: "card", card, caption: logLine(ev), lines: [], pass: false, events: [ev] };
        steps.push(cur);
      } else if (textWorthy(ev, others, me)) {
        const line = logLine(ev);
        if (!line) continue;
        if (!cur) {
          cur = { kind: "text", caption: null, lines: [], pass: true, events: [] };
          steps.push(cur);
        }
        cur.lines.push(line);
        if (!hit) cur.events.push(ev);            // 傷害的音效已在能量命中時播放
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
      .catch(() => {
        try { renderFn(); } catch (_) { /* 保底 */ }
        clearGuardLeftovers();                    // 保護演出中斷時復原
      })
      .finally(() => { pending -= 1; });
    return queue;
  }

  async function run(events, prevState, renderFn, actor) {
    clearGuardLeftovers();                        // 上一批逾時後才回到原位的保護演出殘留
    if (!events.length || !boardVisible() || !overlay()) {
      renderFn();
      return;
    }
    const motion = !motionOff();
    const marks = motion ? measure(events) : null;
    // 追趕:排隊太多批時跳過這批的聚焦(最後一批仍會播)
    const steps = timeline(events, actor, motion, pending >= 5);
    // 音效:開局、金手指、重連(actor 為 null)不播
    const me = selfPlayer();
    const sound = actor !== null && actor !== undefined;
    for (const step of steps) {
      if (sound) Sfx.play(Sfx.pick(step.events, me));
      if (step.kind === "anim") {
        await withTimeout(playBlocking(step.ev, prevState), blockingLimit(step.ev));
      }
      else await spotlight(step, motion);
    }
    await guardReturn();                          // 保護者沒有承受能量(傷害被防止等)時回到原位
    renderFn();
    clearGuardLeftovers();
    if (motion) playOverlays(events, marks);
    if (!sound) return;
    const used = new Set(steps.flatMap((step) => step.events));
    const rest = Sfx.play(Sfx.pick(events.filter((ev) => !used.has(ev)), me));
    // 輪到你:等待輸入的玩家從別人變成自己(本機與觀戰沒有自己)
    if (me !== null && prevState && S && awaitedPlayer(prevState) !== me && awaitedPlayer(S) === me) {
      Sfx.play("your_turn", rest ? 350 : 0);
    }
  }

  // ---------------------------------------------------------------- 聚焦展示

  function spotlightMs(step) {
    const fast = spotlightMode() === "fast" || pending >= 2;   // 落後時自動加快
    const base = fast ? 1000 : 2000;          // 標準 2 秒、快 1 秒
    return step.pass ? base / 2 : base;
  }

  function spotlight(step, motion) {
    const el = document.getElementById("spotlight");
    if (!el) return Promise.resolve();
    const ms = spotlightMs(step);
    const panel = document.createElement("div");
    panel.className = "spot-panel" + (step.kind === "card" ? " with-card" : "") + (step.banner ? " banner" : "");
    if (step.kind === "card") {
      const art = document.createElement("img");
      art.className = "spot-art";
      art.src = artUrl(step.card);
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
      effect.textContent = (TEXT[step.card] && TEXT[step.card].effect) || "";
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

  // 翻頁:書頁翻轉片覆蓋於該方魔書右半,rotateY 過渡;翻 N 頁錯開演 N 次(上限 4);
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

  // 出卡:FLIP — 來源=魔書頁位(重繪前量測),目標=場上欄位(重繪後)
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

  // MP 增減:token 在魔書與托盤之間飛行(增=書→盤、減=盤→書並淡出)
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
    if (ev.type === "showdown") return showdown(ev);
    if (damageHit(ev)) return energyShot(ev);
    if (ev.type === "protected") return guardMove(ev);
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

  // 魔力對決:中央上下對峙(各組自己那一側滑入)→ 合計滾動 → 勝方衝撞 → 結果大字。
  // 總長標準 2.5 秒、快(或落後)1.2 秒,點擊跳過;各時段依總長比例。
  function faceoffMs() { return spotlightMode() === "fast" || pending >= 2 ? 1200 : 2500; }

  function faceoffGroup(side, ev) {
    const attack = side === "attack";
    const player = attack ? ev.attacker : 1 - ev.attacker;
    const g = document.createElement("div");
    g.className = `fo-group ${side} ${topPlayerIndex() === player ? "top" : "bottom"}`;
    const label = document.createElement("div");
    label.className = "fo-label";
    label.textContent = `${t(attack ? "anim.showdown.att" : "anim.showdown.def")} ${pname(player)}`;
    const cards = document.createElement("div");
    cards.className = "fo-cards";
    const slot = (num, emptyKey) => {
      const cell = document.createElement("div");
      cell.className = "fo-card";
      if (num) {
        cell.dataset.card = num;
        cell.appendChild(cardEl(num));
      } else {
        const empty = document.createElement("div");
        empty.className = "fo-empty";
        empty.textContent = emptyKey ? t(emptyKey) : "";
        cell.appendChild(empty);
      }
      cards.appendChild(cell);
    };
    const mamodo = attack ? ev.attack_mamodo : ev.defense_mamodo;
    let spell = attack ? ev.attack_spell : ev.defense_spell;
    if (attack && !spell) {                         // 無戰術攻擊:固定魔力的來源卡
      const fixed = (ev.attacker_breakdown || []).find((i) => i.kind === "fixed");
      spell = fixed && fixed.source && fixed.source !== mamodo ? fixed.source : null;
    }
    if (attack || spell) {
      slot(mamodo, null);
      slot(spell, "anim.showdown.no_spell");
    } else {
      slot(null, "anim.showdown.no_defense");      // 不防禦:沒有特定的魔物,只放「不防禦」
    }
    const total = document.createElement("div");
    total.className = "fo-total";
    total.dataset.final = attack ? ev.attacker_total : ev.defender_total;
    total.textContent = "0";
    g.append(label, cards, total);
    return g;
  }

  async function showdown(ev) {
    const T = faceoffMs();
    const wrap = document.createElement("div");
    wrap.className = "fx-faceoff";
    wrap.style.setProperty("--fo-ms", `${T}ms`);
    const att = faceoffGroup("attack", ev);
    const def = faceoffGroup("defense", ev);
    const vs = document.createElement("div");
    vs.className = "fo-vs";
    vs.textContent = t("anim.showdown.vs");
    const stage = document.createElement("div");
    stage.className = "fo-stage";
    const [upper, lower] = att.classList.contains("top") ? [att, def] : [def, att];
    stage.append(upper, vs, lower);
    wrap.appendChild(stage);
    let skipped = false;
    let skip = null;
    const skipP = new Promise((res) => { skip = res; });
    wrap.style.pointerEvents = "auto";
    wrap.onclick = () => { skipped = true; skip(); };
    overlay().appendChild(wrap);
    const phase = (k) => Promise.race([wait(T * k), skipP]);
    try {
      await phase(0.2);                                                 // 滑入
      if (skipped) return;
      const rollMs = T * 0.3;
      const start = performance.now();
      const nums = [att, def].map((g) => g.querySelector(".fo-total"));
      await Promise.race([skipP, new Promise((done) => {
        (function tick(now) {
          const k = Math.min(1, (now - start) / rollMs);
          for (const el of nums) el.textContent = Math.round(Number(el.dataset.final) * k);
          if (k < 1 && !skipped) requestAnimationFrame(tick);
          else done();
        })(start);
      })]);
      if (skipped) return;
      for (const [g, negated] of [[att, ev.attack_negated], [def, (ev.defender_breakdown || []).some((i) => i.kind === "negated")]]) {
        if (!negated) continue;
        const stamp = document.createElement("div");
        stamp.className = "fo-stamp";
        stamp.textContent = t("anim.showdown.negated");
        g.querySelector(".fo-cards").appendChild(stamp);
      }
      const [win, lose] = ev.winner === "attacker" ? [att, def] : [def, att];
      win.classList.add("clash");                                       // 勝方朝敗方衝撞
      lose.classList.add("shake");
      await phase(0.12);
      if (skipped) return;
      win.classList.add("win");
      lose.classList.add("lose");
      const result = document.createElement("div");
      result.className = "fo-result";
      const main = document.createElement("div");
      main.className = "fo-result-main";
      const tie = ev.winner !== "attacker" && !ev.attack_negated && ev.attacker_total === ev.defender_total;
      main.textContent = t(ev.winner === "attacker" ? "anim.showdown.attack_success"
        : ev.attack_negated ? "anim.showdown.attack_negated" : "anim.showdown.defense_success");
      result.appendChild(main);
      if (tie) {
        const sub = document.createElement("div");
        sub.className = "fo-result-sub";
        sub.textContent = t("anim.showdown.tie");
        result.appendChild(sub);
      }
      vs.replaceWith(result);
      await phase(0.38);
    } finally {
      wrap.remove();
    }
  }

  // 傷害能量:自畫面中央(對峙演出與聚焦展示的位置)飛向承受傷害的魔書或魔物,命中時爆光。
  // 盤面尚未重繪,目標仍在原位(送墓的魔物也還在)。標準約 650ms、快約 380ms。
  function energyMs() { return spotlightMode() === "fast" || pending >= 2 ? 380 : 650; }

  function damageTarget(ev) {
    const zone = zoneOf(ev.player);
    if (!zone) return null;
    const el = ev.type === "damage_dealt" ? zone.querySelector(".book-cover")
      : zone.querySelector(`[data-slot-uid="${ev.slot}"][data-zone-kind="mamodo"]`);
    return el && el.getBoundingClientRect();
  }

  async function energyShot(ev) {
    const guarding = guard && ev.type !== "damage_dealt" && guard.player === ev.player && guard.slot === ev.slot;
    const rect = guarding ? guard.el.getBoundingClientRect() : damageTarget(ev);
    if (!rect) return;
    const T = energyMs();
    const fly = T * 0.7;
    const orb = document.createElement("div");
    orb.className = "fx-energy";
    orb.dataset.target = ev.type === "damage_dealt" ? `book-${ev.player}` : `slot-${ev.slot}`;
    const x0 = window.innerWidth / 2;
    const y0 = window.innerHeight / 2;
    const x1 = rect.left + rect.width / 2;
    const y1 = rect.top + rect.height / 2;
    Object.assign(orb.style, { left: `${x0}px`, top: `${y0}px`, "--fly-ms": `${fly}ms` });
    const angle = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
    orb.style.setProperty("--angle", `${angle}deg`);
    overlay().appendChild(orb);
    orb.getBoundingClientRect();
    Object.assign(orb.style, { left: `${x1}px`, top: `${y1}px` });
    await wait(fly);
    orb.remove();
    const burst = document.createElement("div");
    burst.className = "fx-impact";
    Object.assign(burst.style, {
      left: `${x1}px`, top: `${y1}px`, "--impact-ms": `${T - fly}ms`,
      width: `${Math.max(rect.width, rect.height) * 1.3}px`, height: `${Math.max(rect.width, rect.height) * 1.3}px`,
    });
    overlay().appendChild(burst);
    await wait(T - fly);
    burst.remove();
    if (guarding) await guardAfterHit(ev);
  }

  // 保護:保護的魔物(複製的卡)自原位移到原本傷害對象(魔書或魔物)前方,承受接著的能量後回到原位。
  // 保護後傷害被防止等沒有能量時,在重繪前回到原位。標準約 450ms、快約 250ms。
  let guard = null;   // {player, slot, el, home}
  function guardMs() { return spotlightMode() === "fast" || pending >= 2 ? 250 : 450; }

  async function guardMove(ev) {
    const zone = zoneOf(ev.player);
    const src = zone && zone.querySelector(`[data-slot-uid="${ev.slot}"][data-zone-kind="mamodo"]`);
    const target = zone && (ev.target === "book" ? zone.querySelector(".book-cover")
      : zone.querySelector(`[data-slot-uid="${ev.target_slot}"][data-zone-kind="mamodo"]`));
    if (!src || !target) return;
    if (guard) await guardReturn();
    const ms = guardMs();
    const box = src.getBoundingClientRect();
    const home = { x: box.left + box.width / 2, y: box.top + box.height / 2 };
    const to = target.getBoundingClientRect();
    // 外框只負責移動(以中心定位);裡面的卡保留自己的樣式(負傷的卡維持橫置)
    const wrap = document.createElement("div");
    wrap.className = "fx-guard-wrap";
    wrap.dataset.guardFor = ev.target === "book" ? `book-${ev.player}` : `slot-${ev.target_slot}`;
    Object.assign(wrap.style, { left: `${home.x}px`, top: `${home.y}px`, "--guard-ms": `${ms}ms` });
    const card = src.cloneNode(true);
    card.classList.add("fx-guard");
    wrap.appendChild(card);
    overlay().appendChild(wrap);
    src.style.visibility = "hidden";
    guard = { player: ev.player, slot: ev.slot, el: wrap, card, home, src };
    wrap.getBoundingClientRect();
    // 對象正前方:中心對齊對象,朝畫面中央(傷害來的方向)偏一些,對象仍露出一部分
    const dy = Math.sign(window.innerHeight / 2 - (to.top + to.height / 2)) * Math.min(28, to.height * 0.25);
    Object.assign(wrap.style, { left: `${to.left + to.width / 2}px`, top: `${to.top + to.height / 2 + dy}px` });
    card.classList.add("guarding");
    await wait(ms);
  }

  // 保護者承受能量後:負傷 → 在原地轉成橫置再回到原位;送墓 → 在原地淡出(盤面重繪時移除)
  async function guardAfterHit(ev) {
    const g = guard;
    if (!g) return;
    if (ev.type === "mamodo_discarded") {
      guard = null;
      g.card.classList.add("guard-gone");
      await wait(guardMs());
      g.el.remove();
      return;                                     // 原元素維持隱藏,重繪後即不存在
    }
    if (ev.type === "mamodo_injured") {
      g.card.classList.add("injured");
      await wait(guardMs());
    }
    await guardReturn();
  }

  // 回到原位後複製品留在原位,等盤面重繪後才移除(clearGuardLeftovers):
  // 重繪前盤面上的還是舊樣子(例如尚未負傷的直放卡),提早換回會閃一下
  const guardLeftovers = [];
  async function guardReturn() {
    const g = guard;
    if (!g) return;
    guard = null;
    Object.assign(g.el.style, { left: `${g.home.x}px`, top: `${g.home.y}px` });
    g.card.classList.remove("guarding");
    await wait(guardMs());
    guardLeftovers.push(g);
  }

  function clearGuardLeftovers() {
    if (guard) guardLeftovers.push(guard);
    guard = null;
    for (const g of guardLeftovers.splice(0)) {
      g.el.remove();
      g.src.style.visibility = "";                // 重繪後原元素通常已被取代;保險起見恢復
    }
  }

  // idle:目前排隊中的播放全部結束時完成(測試與需要等畫面追上的流程使用)
  return { apply, idle: () => queue };
})();
