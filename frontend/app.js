/* 金色のガッシュベル!! THE CARD BATTLE — hotseat 前端
 * 職責:渲染後端狀態快照、送出指令、以 i18n 模板渲染事件 log。
 * 規則裁決全在後端;前端只做合法操作的預過濾(後端仍是最終權威)。 */

"use strict";

let DICT = {};        // i18n 字典
let CARDS = {};       // 卡片數值資料(卡號 → def)
let ZH = {};          // 卡片中文文本(卡號 → {name, name_ja, attr, effect})
let gameId = null;
let S = null;         // 最新狀態快照
let logSeq = 0;       // 已渲染事件序號

// ---------------------------------------------------------------- i18n

function t(key, params = {}) {
  let s = DICT[key];
  if (s === undefined) return key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (params[k] !== undefined ? params[k] : `{${k}}`));
}

function pname(p) { return t("ui.player", { n: p + 1 }); }

function cname(num) {
  const z = ZH[num];
  if (!z) return num;
  return z.attr && CARDS[num] && CARDS[num].type === "mamodo" ? `${z.name}《${z.attr}》` : z.name;
}

// ---------------------------------------------------------------- API

async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json();
  if (!res.ok) {
    const msg = body.detail && body.detail.message ? body.detail.message : JSON.stringify(body);
    throw new Error(msg);
  }
  return body;
}

async function newGame() {
  const body = await api("/api/games", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
  });
  gameId = body.game_id;
  S = body.state;
  logSeq = 0;
  document.getElementById("log").innerHTML = "";
  appendLog(body.events);
  render();
}

async function send(command) {
  try {
    const body = await api(`/api/games/${gameId}/commands`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });
    S = body.state;
    appendLog(body.events);
    render();
  } catch (err) {
    toast(t("ui.error", { msg: err.message }));
  }
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2600);
}

// ---------------------------------------------------------------- 卡片元件

function cardEl(num, opts = {}) {
  const def = CARDS[num] || {};
  const z = ZH[num] || { name: num };
  const el = document.createElement("div");
  el.className = `card type-${def.type || "mamodo"}` + (opts.small ? " small" : "") +
    (opts.injured ? " injured" : "");

  const art = document.createElement("img");
  art.className = "art";
  art.src = `/static/assets/cards/${num}.jpg`;
  art.onerror = () => art.remove();      // 卡圖缺失 → 純文字卡面
  el.appendChild(art);

  const cn = document.createElement("div");
  cn.className = "cname";
  cn.textContent = z.name + (def.type === "mamodo" && z.attr ? `《${z.attr}》` : "");
  el.appendChild(cn);

  const ja = document.createElement("div");
  ja.className = "cname-ja";
  ja.textContent = z.name_ja || "";
  el.appendChild(ja);

  const meta = document.createElement("div");
  meta.className = "cmeta";
  const bits = [];
  if (def.cost !== null && def.cost !== undefined) bits.push(t("ui.cost", { n: opts.cost !== undefined ? opts.cost : def.cost }));
  if (def.power) {
    if (def.power.base !== undefined) bits.push(t("ui.power", { n: opts.power !== undefined ? opts.power : def.power.base }));
    if (def.power.bonus !== undefined) bits.push(t("ui.power_bonus", { n: def.power.bonus }));
    if (def.power.special) bits.push(t("ui.power_special"));
  }
  if (def.damage) bits.push(t("ui.damage", { n: def.damage }));
  if (def.ad) bits.push(def.ad);
  meta.textContent = bits.join("・");
  el.appendChild(meta);

  const eff = document.createElement("div");
  eff.className = "ceffect";
  eff.textContent = z.effect || "";
  el.appendChild(eff);

  const numEl = document.createElement("div");
  numEl.className = "cnum";
  numEl.textContent = num;
  el.appendChild(numEl);

  if (opts.badges) {
    for (const b of opts.badges) {
      const bd = document.createElement("span");
      bd.className = `badge ${b.cls}`;
      bd.textContent = b.text;
      el.appendChild(bd);
    }
  }

  if (opts.buttons && opts.buttons.length) {
    const btns = document.createElement("div");
    btns.className = "btns";
    for (const b of opts.buttons) {
      const btn = document.createElement("button");
      btn.textContent = b.label;
      if (b.primary) btn.classList.add("primary");
      if (b.disabled) { btn.disabled = true; if (b.reason) btn.title = b.reason; }
      else btn.onclick = (ev) => { ev.stopPropagation(); b.onclick(); };
      btns.appendChild(btn);
    }
    el.appendChild(btns);
  }

  el.onclick = () => zoom(num);
  return el;
}

function zoom(num) {
  const overlay = document.getElementById("zoom-overlay");
  const holder = document.getElementById("zoom-card");
  holder.innerHTML = "";
  holder.appendChild(cardEl(num, {}));
  overlay.classList.remove("hidden");
}
document.getElementById("zoom-overlay").onclick = () =>
  document.getElementById("zoom-overlay").classList.add("hidden");

// ---------------------------------------------------------------- 合法操作判斷

function inNonBattle() { return S.phase === "battle" && !S.battle && !S.battle_in && !S.pending; }

function canActNow(p) {
  if (S.pending) return false;
  if (S.battle_in) return p === 1 - S.battle_in.attacker;      // 確認中:防方可插入行動
  if (S.battle) return false;                                   // 戰鬥中另行處理
  return S.phase === "battle" && S.action_player === p;
}

function mamodoInPlay(p, related) {
  return S.players[p].slots.find((s) => CARDS[s.top].related_mamodo === related);
}

function spellUsable(p, entry, forAttack) {
  const def = CARDS[entry.card];
  const ps = S.players[p];
  if (def.type !== "spell") return { ok: false };
  const icon = forAttack ? ["A", "AD"] : ["D", "AD"];
  if (!icon.includes(def.ad)) return { ok: false };
  if (ps.used_spell_pages.includes(entry.page)) return { ok: false, reason: t("ui.used") };
  if (ps.mp < entry.cost) return { ok: false, reason: `MP ${ps.mp} < ${entry.cost}` };
  const isCommand = def.related_mamodo === "Command: All";
  if (!isCommand && !mamodoInPlay(p, def.related_mamodo)) return { ok: false };
  if (isCommand && ps.slots.length === 0) return { ok: false };
  return { ok: true, isCommand };
}

function pickSlotThen(p, isCommand, cb) {
  const slots = S.players[p].slots;
  if (!isCommand || slots.length === 1) { cb(isCommand ? slots[0].uid : undefined); return; }
  showDialog(t("choice.title.e009_pick"), slots.map((s) => ({
    cardNum: s.top, onpick: () => cb(s.uid),
  })));
}

// ---------------------------------------------------------------- 渲染

function render() {
  document.getElementById("title").textContent = t("app.title");
  document.getElementById("log-title").textContent = t("ui.log");
  document.getElementById("new-game").textContent = t("ui.new_game");
  document.getElementById("turn-info").textContent = t("ui.turn", { n: S.turn_no }) +
    "|" + pname(S.turn_player);
  document.getElementById("phase-info").textContent =
    t(`ui.phase.${S.phase === "game_over" ? "game_over" : S.phase}`);

  const acting = document.getElementById("acting-info");
  if (S.phase === "game_over") {
    acting.textContent = t("ui.winner", { player: pname(S.winner) }) +
      "(" + t(`ui.reason.${S.end_reason}`) + ")";
  } else if (S.pending) {
    acting.textContent = t("ui.waiting_choice", { player: pname(S.pending.player) });
  } else if (S.battle) {
    acting.textContent = S.battle.step === "defense"
      ? t("ui.battle_no_defense_yet")
      : t("ui.acting", { player: pname(S.battle.effect_turn) });
  } else if (S.battle_in) {
    acting.textContent = t("ui.acting", { player: pname(1 - S.battle_in.attacker) });
  } else if (S.phase === "start") {
    acting.textContent = t("ui.acting", { player: pname(S.turn_player) });
  } else {
    acting.textContent = S.action_player !== null ? t("ui.acting", { player: pname(S.action_player) }) : "";
  }

  renderPlayer(1);
  renderPlayer(0);
  renderBattleStrip();
  renderActionBar();
  renderPendingDialog();
}

function renderPlayer(p) {
  const zone = document.getElementById(`player-${p}`);
  zone.innerHTML = "";
  const ps = S.players[p];
  const active =
    (S.phase === "start" && S.turn_player === p) ||
    (S.pending && S.pending.player === p) ||
    (!S.pending && S.battle && S.battle.step === "defense" && p === 1 - S.battle.attacker) ||
    (!S.pending && S.battle && S.battle.step === "effects" && p === S.battle.effect_turn) ||
    (!S.pending && !S.battle && S.battle_in && p === 1 - S.battle_in.attacker) ||
    (!S.pending && inNonBattle() && S.action_player === p);
  zone.classList.toggle("active", !!active);

  const head = document.createElement("div");
  head.className = "pz-head";
  head.innerHTML =
    `<span class="pname">${pname(p)}</span>` +
    `<span class="mp">${t("ui.mp")} ${ps.mp}</span>` +
    `<span class="book-progress">${t("ui.book")} ${t("ui.book_progress", { pos: ps.pos, size: ps.book_size })}</span>` +
    `<span class="discard-btn">${t("ui.discard", { n: ps.discard.length })}</span>`;
  head.querySelector(".discard-btn").onclick = () => showDiscard(p);
  zone.appendChild(head);

  // 場上魔物
  const fieldLabel = document.createElement("div");
  fieldLabel.className = "row-label";
  fieldLabel.textContent = t("ui.field");
  zone.appendChild(fieldLabel);
  const field = document.createElement("div");
  field.className = "card-row";
  for (const slot of ps.slots) {
    field.appendChild(slotEl(p, slot));
    if (slot.partner) field.appendChild(partnerEl(p, slot));
  }
  zone.appendChild(field);

  // 魔本翻開對頁
  const pagesLabel = document.createElement("div");
  pagesLabel.className = "row-label";
  pagesLabel.textContent = t("ui.open_pages");
  zone.appendChild(pagesLabel);
  const row = document.createElement("div");
  row.className = "card-row";
  for (const entry of ps.open_pages) row.appendChild(openPageEl(p, entry));
  zone.appendChild(row);
}

function slotEl(p, slot) {
  const buttons = [];
  const ab = slot.ability;
  if (ab) {
    const label = ab.mode === "mp" ? t("ui.ability_mp", { n: ab.mp_cost }) : t("ui.ability");
    const usable = abilityUsableNow(p, ab);
    buttons.push({
      label, disabled: !usable.ok, reason: usable.reason,
      onclick: () => send({ type: "use_field_ability", player: p, zone: "mamodo", slot_uid: slot.uid }),
    });
  }
  return cardEl(slot.top, {
    injured: slot.injured,
    power: slot.power,
    badges: [{ cls: slot.injured ? "injured-mark" : "partner-mark",
               text: slot.injured ? t("ui.injured") : t("ui.healthy") }],
    buttons,
  });
}

function partnerEl(p, slot) {
  const buttons = [];
  const ab = slot.partner_ability;
  if (ab) {
    const label = ab.mode === "discard" ? t("ui.ability_discard")
      : ab.mode === "mp" ? t("ui.ability_mp", { n: ab.mp_cost }) : t("ui.ability");
    const usable = abilityUsableNow(p, ab);
    buttons.push({
      label, disabled: !usable.ok, reason: usable.reason,
      onclick: () => send({ type: "use_field_ability", player: p, zone: "partner", slot_uid: slot.uid }),
    });
  }
  return cardEl(slot.partner, { small: true, buttons });
}

function abilityUsableNow(p, ab) {
  if (S.pending || S.phase !== "battle") return { ok: false };
  if (S.battle) {
    if (ab.timing === "nonbattle") return { ok: false };
    if (S.battle.step !== "effects" || S.battle.effect_turn !== p) return { ok: false };
  } else {
    if (ab.timing === "battle") return { ok: false };
    if (S.battle_in ? p !== 1 - S.battle_in.attacker : S.action_player !== p) return { ok: false };
  }
  if (ab.mp_cost > S.players[p].mp) return { ok: false, reason: `MP < ${ab.mp_cost}` };
  return { ok: true };
}

function openPageEl(p, entry) {
  const def = CARDS[entry.card];
  const buttons = [];
  const pageBadge = [{ cls: "partner-mark", text: t("ui.page_n", { n: entry.page }) }];

  if (canActNow(p)) {
    if (def.type === "mamodo" || def.type === "partner") {
      buttons.push({
        label: t("ui.play"), primary: true,
        onclick: () => send({ type: "play_card", player: p, page: entry.page }),
      });
    } else if (def.type === "event") {
      const ps = S.players[p];
      const blocked = ps.used_event_this_turn ? t("ui.used")
        : (def.cost || 0) > ps.mp ? `MP < ${def.cost}`
        : (def.ad === "A" && p !== S.turn_player) ? t("ui.error", { msg: "" }) : null;
      buttons.push({
        label: t("ui.use_event"), primary: true, disabled: !!blocked, reason: blocked,
        onclick: () => send({ type: "use_book_card", player: p, page: entry.page }),
      });
    }
    if (def.type === "spell" && p === S.turn_player && !S.battle_in) {
      const u = spellUsable(p, entry, true);
      if (["A", "AD"].includes(def.ad)) {
        buttons.push({
          label: t("ui.attack"), primary: true, disabled: !u.ok, reason: u.reason,
          onclick: () => pickSlotThen(p, u.isCommand, (uid) => {
            const cmd = { type: "declare_attack", player: p, page: entry.page };
            if (uid !== undefined) cmd.slot_uid = uid;
            send(cmd);
          }),
        });
      }
    }
  }

  // 戰鬥防禦宣告
  if (!S.pending && S.battle && S.battle.step === "defense" && p === 1 - S.battle.attacker) {
    const u = spellUsable(p, entry, false);
    if (["D", "AD"].includes(def.ad) && def.type === "spell") {
      const blocked = S.battle.attack_undefendable ? t("ui.undefendable") : (u.ok ? null : u.reason);
      buttons.push({
        label: t("ui.defend"), primary: true,
        disabled: S.battle.attack_undefendable || !u.ok, reason: blocked,
        onclick: () => pickSlotThen(p, u.isCommand, (uid) => {
          const cmd = { type: "declare_defense", player: p, page: entry.page };
          if (uid !== undefined) cmd.slot_uid = uid;
          send(cmd);
        }),
      });
    }
  }

  return cardEl(entry.card, { cost: entry.cost, badges: pageBadge, buttons });
}

function renderBattleStrip() {
  const strip = document.getElementById("battle-strip");
  strip.innerHTML = "";
  if (S.battle_in) {
    strip.innerHTML = `<span>${t("ui.battle_in_hint", {
      player: pname(S.battle_in.attacker), spell: cname(S.battle_in.spell) })}</span>`;
    return;
  }
  if (!S.battle) return;
  const b = S.battle;
  const parts = [];
  parts.push(`<span class="vs">${t("ui.battle")}</span>`);
  parts.push(`<span>${t("ui.battle_attack", { player: pname(b.attacker), spell: cname(b.attack_spell) })}` +
    (b.attack_negated ? `(${t("ui.negated")})` : "") +
    (b.attack_undefendable ? `(${t("ui.undefendable")})` : "") + `</span>`);
  if (b.defense_spell) {
    parts.push(`<span>${t("ui.battle_defense", { player: pname(1 - b.attacker), spell: cname(b.defense_spell) })}` +
      (b.defense_negated ? `(${t("ui.negated")})` : "") + `</span>`);
  }
  parts.push(`<span>${t("ui.battle_totals", { att: b.attacker_total, def: b.defender_total })}</span>`);
  if (b.step === "effects") {
    parts.push(`<span>${t("ui.battle_effects_hint", { player: pname(b.effect_turn) })}</span>`);
  }
  strip.innerHTML = parts.join(" ");
}

function renderActionBar() {
  const bar = document.getElementById("action-bar");
  bar.innerHTML = "";
  if (S.phase === "game_over" || S.pending) return;

  const addBtn = (label, onclick, primary) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (primary) btn.classList.add("primary");
    btn.onclick = onclick;
    bar.appendChild(btn);
  };
  const hint = (msg) => {
    const el = document.createElement("span");
    el.className = "hint";
    el.textContent = msg;
    bar.appendChild(el);
  };

  if (S.phase === "start") {
    const tp = S.turn_player;
    hint(pname(tp) + "・" + t("ui.phase.start"));
    const maxFlip = Math.min(3, Math.floor((32 - S.players[tp].pos) / 2));
    for (let n = 0; n <= maxFlip; n++) {
      addBtn(n === 0 ? t("ui.flip_0") : t("ui.flip_n", { n, mp: 2 * n }),
        () => send({ type: "flip_pages", player: tp, count: n }), n === maxFlip);
    }
    return;
  }

  if (S.battle_in) {
    const dp = 1 - S.battle_in.attacker;
    hint(pname(dp));
    addBtn(t("ui.allow_battle"),
      () => send({ type: "battle_in_response", player: dp, allow: true }), true);
    return;
  }

  if (S.battle) {
    const b = S.battle;
    if (b.step === "defense") {
      const dp = 1 - b.attacker;
      hint(pname(dp));
      addBtn(t("ui.no_defense"), () => send({ type: "no_defense", player: dp }));
    } else {
      hint(pname(b.effect_turn));
      addBtn(t("ui.pass"), () => send({ type: "pass", player: b.effect_turn }));
    }
    return;
  }

  if (S.action_player !== null) {
    hint(pname(S.action_player));
    addBtn(t("ui.pass"), () => send({ type: "pass", player: S.action_player }));
  }
}

// ---------------------------------------------------------------- 決策對話框

function showDialog(title, options) {
  const overlay = document.getElementById("dialog-overlay");
  document.getElementById("dialog-title").textContent = title;
  const holder = document.getElementById("dialog-options");
  holder.innerHTML = "";
  for (const opt of options) {
    if (opt.cardNum) {
      const el = cardEl(opt.cardNum, { small: true });
      el.onclick = () => { overlay.classList.add("hidden"); opt.onpick(); };
      holder.appendChild(el);
    } else {
      const btn = document.createElement("button");
      btn.textContent = opt.label;
      btn.onclick = () => { overlay.classList.add("hidden"); opt.onpick(); };
      holder.appendChild(btn);
    }
  }
  overlay.classList.remove("hidden");
}

function renderPendingDialog() {
  const overlay = document.getElementById("dialog-overlay");
  if (!S.pending) { overlay.classList.add("hidden"); return; }
  const pd = S.pending;
  const p = pd.player;
  const titleKey = `choice.title.${pd.kind}`;
  const title = pname(p) + ":" + (DICT[titleKey] ? t(titleKey) : pd.kind);
  const choose = (value) => send({ type: "choose", player: p, value });

  const options = pd.options.map((opt) => {
    if (opt.label === "no_protect") return { label: t("choice.no_protect"), onpick: () => choose(null) };
    if (opt.label === "keep") return { label: t("choice.keep"), onpick: () => choose(null) };
    if (opt.label === "reflip") return { label: t("choice.reflip", { n: opt.value + 1 }), onpick: () => choose(opt.value) };
    if (opt.label === "pay_reflip") return { label: t("choice.pay_reflip"), onpick: () => choose(true) };
    if (opt.label === "stop") return { label: t("choice.stop"), onpick: () => choose(false) };
    if (opt.card) {
      const value = opt.value !== undefined ? opt.value : opt.page;
      return { cardNum: opt.card, onpick: () => choose(value) };
    }
    if (opt.page !== undefined) return { label: t("ui.page_n", { n: opt.page }), onpick: () => choose(opt.page) };
    if (opt.index !== undefined) return { label: `#${opt.index}`, onpick: () => choose(opt.index) };
    return { label: String(opt.value), onpick: () => choose(opt.value) };
  });
  showDialog(title, options);
}

function showDiscard(p) {
  const ps = S.players[p];
  showDialog(pname(p) + "・" + t("ui.discard", { n: ps.discard.length }),
    ps.discard.length
      ? ps.discard.map((num) => ({ cardNum: num, onpick: () => zoom(num) }))
      : [{ label: t("ui.close"), onpick: () => {} }]);
}

// ---------------------------------------------------------------- 行動記錄

function logLine(ev) {
  const P = { player: ev.player !== undefined ? pname(ev.player) : "" };
  switch (ev.type) {
    case "game_started": return t("log.game_started");
    case "turn_started": return t("log.turn_started", { turn: ev.turn, player: pname(ev.player) });
    case "turn_ended": return t("log.turn_ended");
    case "phase_changed": return t("log.phase_changed", { phase: t(`ui.phase.${ev.phase}`) });
    case "pages_flipped":
      return ev.mp_gained ? t("log.pages_flipped", { ...P, count: ev.count, mp: ev.mp_gained })
                          : t("log.pages_flipped_forced", { ...P, count: ev.count });
    case "pages_turned": return t("log.pages_turned", { ...P, count: Math.abs(ev.count), source: cname(ev.source) || ev.source });
    case "mp_changed":
      return ev.delta >= 0 ? t("log.mp_changed_gain", { ...P, delta: ev.delta, mp: ev.mp })
                           : t("log.mp_changed_pay", { ...P, delta: -ev.delta, mp: ev.mp });
    case "card_played":
      if (ev.stacked) return t("log.card_played_stacked", { ...P, card: cname(ev.card) });
      if (ev.forced) return t("log.card_played_forced", { ...P, card: cname(ev.card) });
      return t("log.card_played", { ...P, card: cname(ev.card) });
    case "book_card_used": return t("log.book_card_used", { ...P, card: cname(ev.card) });
    case "ability_used": return t("log.ability_used", { ...P, card: cname(ev.card) });
    case "passed": return t("log.passed", P);
    case "battle_in_check": return t("log.battle_in_check", { player: pname(ev.attacker), spell: cname(ev.spell) });
    case "battle_in_voided": return t("log.battle_in_voided");
    case "battle_started": return t("log.battle_started", { player: pname(ev.attacker), spell: cname(ev.spell) });
    case "defense_declared": return t("log.defense_declared", { ...P, spell: cname(ev.spell) });
    case "no_defense": return t("log.no_defense", P);
    case "battle_effects_step": return t("log.battle_effects_step");
    case "coin_flipped":
      if (ev.source === "setup") return t("log.coin_first", { player: pname(ev.player) });
      return t(`log.coin_flipped.${ev.result}`, { ...P, source: cname(ev.source) || ev.source });
    case "showdown":
      return t("log.showdown", { att: ev.attacker_total, def: ev.defender_total,
        winner: t(`log.showdown.${ev.winner}`) });
    case "attack_negated": return t("log.attack_negated", { source: cname(ev.source) || ev.source || "" });
    case "defense_negated": return t("log.defense_negated", { source: cname(ev.source) || ev.source || "" });
    case "damage_dealt": return t("log.damage_dealt.book", { ...P, amount: ev.amount });
    case "damage_prevented": return t("log.damage_prevented", P);
    case "damage_negated": return t("log.damage_negated", { card: cname(ev.card) });
    case "protected": return t("log.protected", { ...P, card: cname(ev.card) });
    case "mamodo_injured": return t("log.mamodo_injured", { ...P, card: cname(ev.card) });
    case "mamodo_discarded": return t("log.mamodo_discarded", { ...P, card: cname(ev.cards[ev.cards.length - 1]) });
    case "mamodo_healed": return t("log.mamodo_healed", { ...P, card: cname(ev.card) });
    case "card_discarded": return t("log.card_discarded", { ...P, card: cname(ev.card) });
    case "standby_set": return t("log.standby_set", { player: pname(ev.owner), card: cname(ev.source) });
    case "standby_resolved": return t("log.standby_resolved", { card: cname(ev.card) });
    case "modifier_added": return t("log.modifier_added", { card: cname(ev.source) || ev.source });
    case "effect_applied": return t("log.effect_applied", { source: cname(ev.source) || ev.source });
    case "battle_ended": return t("log.battle_ended");
    case "choice_required": return t("log.choice_required", P);
    case "book_revealed": return t("log.book_revealed", P);
    case "pages_peeked": return t("log.pages_peeked", P);
    case "game_ended": return t("log.game_ended", { player: pname(ev.winner), reason: t(`ui.reason.${ev.reason}`) });
    default: return null;
  }
}

function appendLog(events) {
  const holder = document.getElementById("log");
  for (const ev of events) {
    if (ev.seq < logSeq) continue;
    const line = logLine(ev);
    if (!line) continue;
    const el = document.createElement("div");
    el.className = "ev";
    if (ev.type === "turn_started") el.classList.add("turn");
    if (["battle_started", "showdown", "game_ended", "attack_negated"].includes(ev.type)) {
      el.classList.add("important");
    }
    el.textContent = line;
    holder.appendChild(el);
    logSeq = ev.seq + 1;
  }
  holder.scrollTop = holder.scrollHeight;
}

// ---------------------------------------------------------------- 啟動

async function boot() {
  [DICT, CARDS, ZH] = await Promise.all([
    fetch("/static/i18n/zh-TW.json").then((r) => r.json()),
    fetch("/data/cards.json").then((r) => r.json()).then((list) =>
      Object.fromEntries(list.map((c) => [c.number, c]))),
    fetch("/data/cards.zh-TW.json").then((r) => r.json()),
  ]);
  document.getElementById("new-game").onclick = newGame;
  await newGame();
}

boot();
