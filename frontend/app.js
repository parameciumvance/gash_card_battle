/* 金色のガッシュベル!! THE CARD BATTLE — 前端
 * 模式:本機(local, 全視角雙 token)/ 線上(online, 單 token + WS)/ 觀戰(spectator)。
 * 規則裁決與資訊過濾全在後端;前端渲染視角化快照、送指令、渲染事件 log。 */

"use strict";

let DICT = {};        // i18n 字典
let CARDS = {};       // 卡片數值資料(decks.js 的驗證也依賴)
let ZH = {};          // 卡片中文文本
let LEVEL1 = [];      // level1 預組頁序(構築器複製起手用)
let S = null;         // 最新遊戲狀態快照(視角化)
let R = null;         // 房間 meta {code, mode, you, deadline, ...}
let SESSION = null;   // {code, mode, viewer, tokens:{playerIndex→token} 或 {me:token}}
let ws = null;
let wsWanted = false;
let logSeq = 0;
let clockDrift = 0;   // Date.now()/1000 - server_time

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

// ---------------------------------------------------------------- session / 身分

function myViewer() { return SESSION ? SESSION.viewer : null; }   // 0|1|"all"|"spectator"
function isLocal() { return SESSION && SESSION.mode === "local"; }
function iControl(p) {
  const v = myViewer();
  return v === "all" || v === p;
}

function tokenFor(command) {
  if (isLocal()) return SESSION.tokens[command.player];
  return SESSION.tokens.me;
}

function saveSession() {
  localStorage.setItem(`gash-room-${SESSION.code}`, JSON.stringify(SESSION));
}

function loadSession(code) {
  const raw = localStorage.getItem(`gash-room-${code}`);
  return raw ? JSON.parse(raw) : null;
}

// ---------------------------------------------------------------- API

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const body = await res.json();
  if (!res.ok) {
    const msg = body.detail && body.detail.message ? body.detail.message : JSON.stringify(body);
    const err = new Error(msg);
    err.code = body.detail && body.detail.code;
    throw err;
  }
  return body;
}

async function send(command) {
  try {
    const body = await api(`/api/rooms/${SESSION.code}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Player-Token": tokenFor(command) },
      body: JSON.stringify({ command }),
    });
    applyPayload(body);
  } catch (err) {
    toast(t("ui.error", { msg: err.message }));
  }
}

function applyPayload(body) {
  const prevS = S;
  if (body.state) S = body.state;
  if (body.room) { R = body.room; clockDrift = Date.now() / 1000 - R.server_time; }
  if (body.events) appendLog(body.events);
  if (R && R.started && SESSION && S) show("layout");  // 對手加入 → 離開等待畫面
  // 統一動畫管線:量測 → 阻塞演出 → 重繪 → 疊加特效(reduced-motion 直接重繪)
  Anim.apply(body.events || [], prevS, render);
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2600);
}

// ---------------------------------------------------------------- WebSocket

function wsToken() {
  return isLocal() ? Object.values(SESSION.tokens)[0] : SESSION.tokens.me;
}

function openWS() {
  wsWanted = true;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/api/rooms/${SESSION.code}/ws?token=${wsToken()}`);
  ws.onopen = () => setConn(true);
  ws.onmessage = (msg) => {
    const body = JSON.parse(msg.data);
    if (body.type === "welcome") {
      applyPayload(body);       // 全量狀態;log 以 seq 去重補齊
      fetchMissedEvents();
    } else if (body.type === "update") {
      applyPayload(body);
    }
  };
  ws.onclose = () => {
    setConn(false);
    if (wsWanted) setTimeout(openWS, 1500);
  };
  ws.onerror = () => ws.close();
}

async function fetchMissedEvents() {
  try {
    const body = await api(`/api/rooms/${SESSION.code}/events?since=${logSeq}`,
      { headers: { "X-Player-Token": wsToken() } });
    appendLog(body.events);
  } catch (_) { /* 房間可能未開局 */ }
}

function setConn(ok) {
  const el = document.getElementById("conn-status");
  if (!SESSION || SESSION.mode === "local") { el.textContent = ""; return; }
  el.textContent = ok ? t("ui.conn.online") : t("ui.conn.reconnecting");
  el.className = ok ? "ok" : "bad";
}

// ---------------------------------------------------------------- 入口流程

function show(sectionId) {
  for (const id of ["landing", "waiting", "layout", "builder"]) {
    document.getElementById(id).classList.toggle("hidden", id !== sectionId);
  }
}

// ---------------------------------------------------------------- 牌組選單與 payload

function deckOptions(sel) {
  sel.innerHTML = "";
  const preset = document.createElement("option");
  preset.value = "preset";
  preset.textContent = t("ui.deck.preset_level1");
  sel.appendChild(preset);
  for (const d of DeckStore.list()) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = d.name + (d.valid ? "" : t("ui.deck.invalid_suffix"));
    opt.disabled = !d.valid;  // 不合法牌組不可選入對戰
    sel.appendChild(opt);
  }
}

function deckPayload(selectId) {
  const value = document.getElementById(selectId).value;
  if (value === "preset") return { preset: "level1" };
  const deck = DeckStore.get(value);
  return deck ? { pages: deck.pages } : { preset: "level1" };
}

async function startLocal() {
  const body = await api("/api/rooms", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "local",
      decks: [deckPayload("deck-local-0"), deckPayload("deck-local-1")] }),
  });
  SESSION = { code: body.code, mode: "local", viewer: "all",
              tokens: { 0: body.player_tokens[0], 1: body.player_tokens[1] } };
  saveSession();
  history.replaceState(null, "", `/?room=${body.code}`);
  resetLog();
  applyPayload(body);
  show("layout");
}

async function createRoom() {
  const timer = document.getElementById("timer-select").value;
  const body = await api("/api/rooms", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "online", timer_seconds: timer ? Number(timer) : null,
      deck: deckPayload("deck-create") }),
  });
  SESSION = { code: body.code, mode: "online", viewer: 0,
              tokens: { me: body.player_token } };
  saveSession();
  history.replaceState(null, "", `/?room=${body.code}`);
  R = body.room;
  showWaiting(body);
  openWS();  // 對手加入時會收到 update → 進入對局
}

function showWaiting(body) {
  show("waiting");
  document.getElementById("waiting-title").textContent = t("ui.waiting_opponent");
  document.getElementById("waiting-code").textContent = SESSION.code;
  const joinUrl = `${location.origin}/?join=${SESSION.code}`;
  const specUrl = `${location.origin}${body.spectate_url || R.spectate_url || ""}`;
  document.getElementById("share-join").value = joinUrl;
  document.getElementById("share-spec").value = specUrl;
}

async function joinRoom(code) {
  try {
    const body = await api(`/api/rooms/${code}/join`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deck: deckPayload("deck-join") }),
    });
    SESSION = { code: code.toUpperCase(), mode: "online", viewer: 1,
                tokens: { me: body.player_token } };
    saveSession();
    history.replaceState(null, "", `/?room=${SESSION.code}`);
    resetLog();
    applyPayload(body);
    show("layout");
    openWS();
  } catch (err) {
    toast(t("ui.error", { msg: err.message }));
    show("landing");
  }
}

function enterSpectate(code, token) {
  SESSION = { code: code.toUpperCase(), mode: "spectate", viewer: "spectator",
              tokens: { me: token } };
  history.replaceState(null, "", `/?room=${SESSION.code}`);
  resetLog();
  show("layout");
  openWS();
}

async function resumeRoom(code) {
  const saved = loadSession(code);
  if (!saved) { show("landing"); return; }
  SESSION = saved;
  resetLog();
  try {
    const body = await api(`/api/rooms/${code}/state`,
      { headers: { "X-Player-Token": wsToken() } });
    R = body.room;
    if (SESSION.mode === "local") {
      applyPayload(body);
      await fetchMissedEvents();
      show("layout");
    } else if (!R.started) {
      showWaiting(body);
      openWS();
    } else {
      show("layout");
      openWS();
    }
  } catch (err) {
    localStorage.removeItem(`gash-room-${code}`);
    toast(t("ui.error.room_gone"));
    history.replaceState(null, "", "/");
    show("landing");
  }
}

function leaveRoom() {
  wsWanted = false;
  if (ws) ws.close();
  SESSION = null; S = null; R = null;
  history.replaceState(null, "", "/");
  show("landing");
  renderTopbar();
}

function resetLog() {
  logSeq = 0;
  document.getElementById("log").innerHTML = "";
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
  art.onerror = () => art.remove();
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

function cardBackEl(page, consumed = false) {
  const el = document.createElement("div");
  el.className = "card back" + (consumed ? " consumed" : "");
  const label = document.createElement("div");
  label.className = "backlabel";
  label.textContent = t("ui.hidden_page", { n: page });
  el.appendChild(label);
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
  if (!iControl(p)) return false;
  if (S.pending) return false;
  if (S.battle_in) return p === 1 - S.battle_in.attacker;
  if (S.battle) return false;
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

function topPlayerIndex() {
  const v = myViewer();
  if (v === 0) return 1;
  if (v === 1) return 0;
  return 1;  // 本機/觀戰:玩家2在上
}

function render() {
  renderTopbar();
  if (!S) return;
  renderPlayerZone(document.getElementById("zone-top"), topPlayerIndex(), true);
  renderPlayerZone(document.getElementById("zone-bottom"), 1 - topPlayerIndex(), false);
  renderBattleStage();
  renderActionBar();
  renderPendingDialog();
}

function renderTopbar() {
  document.getElementById("title").textContent = t("app.title");
  document.getElementById("log-title").textContent = t("ui.log");
  const leave = document.getElementById("leave-room");
  leave.textContent = t("ui.leave");
  leave.classList.toggle("hidden", !SESSION);
  const idEl = document.getElementById("identity");
  const v = myViewer();
  idEl.textContent = !SESSION ? "" :
    v === "spectator" ? t("ui.spectating") :
    v === "all" ? "" : t("ui.you_are", { player: pname(v) });
  if (!S) {
    document.getElementById("turn-info").textContent = "";
    document.getElementById("phase-info").textContent = "";
    document.getElementById("acting-info").textContent = "";
    return;
  }
  document.getElementById("turn-info").textContent =
    t("ui.turn", { n: S.turn_no }) + "|" + pname(S.turn_player);
  document.getElementById("phase-info").textContent =
    t(`ui.phase.${S.phase === "game_over" ? "game_over" : S.phase}`);

  const acting = document.getElementById("acting-info");
  if (S.phase === "game_over") {
    acting.textContent = t("ui.winner", { player: pname(S.winner) }) +
      "(" + t(`ui.reason.${S.end_reason}`) + ")";
  } else if (S.pending) {
    acting.textContent = iControl(S.pending.player)
      ? t("ui.waiting_choice", { player: pname(S.pending.player) })
      : t("ui.opponent_choosing");
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
}

/* 鏡像牌桌:上方(對手)由上而下=魔本→搭檔→魔物;下方(我方)=魔物→搭檔→魔本。
 * 搭檔槽固定在該魔物的魔本側(對手在上、我方在下),由 mamodo-column 內的排列方向實現。 */
function renderPlayerZone(zone, p, isTop) {
  zone.innerHTML = "";
  zone.dataset.player = p;
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
    `<span class="pname">${pname(p)}${iControl(p) && myViewer() !== "all" ? "(你)" : ""}</span>` +
    `<span class="mp">${t("ui.mp")} ${ps.mp}</span>` +
    `<span class="book-progress">${t("ui.book")} ${t("ui.book_progress", { pos: ps.pos, size: ps.book_size })}</span>` +
    `<span class="discard-btn">${t("ui.discard", { n: ps.discard.length })}</span>`;
  head.querySelector(".discard-btn").onclick = () => showDiscard(p);
  zone.appendChild(head);

  // 場區(魔物列+搭檔列)置中;魔本區靠外角:對手右上、我方左下(對角相對)
  const body = document.createElement("div");
  body.className = "zone-body";
  const sideL = document.createElement("div");
  sideL.className = "zone-side";
  const sideR = document.createElement("div");
  sideR.className = "zone-side";
  const book = renderBookBlock(p, ps);
  (isTop ? sideR : sideL).classList.add("book-side");
  (isTop ? sideR : sideL).appendChild(book);
  body.appendChild(sideL);
  body.appendChild(renderFieldBlock(p, ps, isTop));
  body.appendChild(sideR);
  zone.appendChild(body);
}

const FIELD_COLUMNS = 3;

// 魔物列與搭檔列:各固定 3 欄同寬,垂直配對靠同索引對齊;搭檔朝己方外側
function renderFieldBlock(p, ps, isTop) {
  const block = document.createElement("div");
  block.className = "field-block";
  const mamodoRow = document.createElement("div");
  mamodoRow.className = "field-row mamodo-row";
  const partnerRow = document.createElement("div");
  partnerRow.className = "field-row partner-row";
  for (let i = 0; i < Math.max(FIELD_COLUMNS, ps.slots.length); i++) {
    const slot = ps.slots[i];
    const mamodoCell = document.createElement("div");
    mamodoCell.className = "mcell mamodo-cell";
    const partnerCell = document.createElement("div");
    partnerCell.className = "mcell partner-cell";
    if (slot) {
      const m = slotEl(p, slot);
      m.dataset.slotUid = slot.uid;
      m.dataset.zoneKind = "mamodo";
      if (slot.stack && slot.stack.length > 1) {
        const st = document.createElement("span");
        st.className = "stack-badge";
        st.textContent = `×${slot.stack.length}`;
        m.appendChild(st);
      }
      mamodoCell.appendChild(m);
      if (slot.partner) {
        const pt = partnerEl(p, slot);
        pt.dataset.slotUid = slot.uid;
        pt.dataset.zoneKind = "partner";
        partnerCell.appendChild(pt);
      } else {
        partnerCell.appendChild(emptyFrame(t("ui.slot.empty_partner"), true));
      }
    } else {
      mamodoCell.appendChild(emptyFrame(t("ui.slot.empty_mamodo"), false));
      partnerCell.appendChild(emptyFrame(t("ui.slot.empty_partner"), true));
    }
    mamodoRow.appendChild(mamodoCell);
    partnerRow.appendChild(partnerCell);
  }
  if (isTop) { block.appendChild(partnerRow); block.appendChild(mamodoRow); }
  else { block.appendChild(mamodoRow); block.appendChild(partnerRow); }
  return block;
}

function emptyFrame(label, small) {
  const el = document.createElement("div");
  el.className = "empty-frame" + (small ? " small" : "");
  el.textContent = label;
  return el;
}

// 魔本區:對頁固定兩個頁位(pos, pos+1)。卡片仍在=卡面(對手視角=卡背+頁碼);
// 卡片已離開頁面(上場/使用)=卡背圖;超出書末=空位,尺寸不變
function renderBookBlock(p, ps) {
  const block = document.createElement("div");
  block.className = "book-block";
  const cover = document.createElement("div");
  cover.className = "book-cover";
  cover.dataset.book = p;
  const spine = document.createElement("div");
  spine.className = "book-spine";
  const pages = document.createElement("div");
  pages.className = "book-pages";
  const byPage = Object.fromEntries(ps.open_pages.map((e) => [e.page, e]));
  for (const pg of [ps.pos, ps.pos + 1]) {
    let el;
    if (pg < 1 || pg > ps.book_size) {
      el = document.createElement("div");
      el.className = "page-void";
    } else if (byPage[pg]) {
      const entry = byPage[pg];
      el = entry.card ? openPageEl(p, entry) : cardBackEl(entry.page);
      el.dataset.page = entry.page;
      if (entry.card) el.dataset.card = entry.card;
    } else {
      el = cardBackEl(pg, true);  // 卡片已被拿出的頁位
      el.dataset.page = pg;
    }
    pages.appendChild(el);
  }
  cover.appendChild(spine);
  cover.appendChild(pages);
  block.appendChild(cover);
  block.appendChild(mpTrayEl(p, ps.mp));
  return block;
}

// MP token 托盤:1 顆=1 MP、每排 8 顆;超過 16 顆折疊為「●×N」;數字保底
function mpTrayEl(p, mp) {
  const tray = document.createElement("div");
  tray.className = "mp-tray";
  tray.dataset.mpTray = p;
  tray.title = `${t("ui.mp")} ${mp}`;
  const tokens = document.createElement("div");
  tokens.className = "mp-tokens";
  if (mp > 16) {
    tray.classList.add("folded");
    const big = document.createElement("span");
    big.className = "mp-token big";
    tokens.appendChild(big);
    const n = document.createElement("span");
    n.className = "mp-fold-count";
    n.textContent = `×${mp}`;
    tokens.appendChild(n);
  } else {
    for (let i = 0; i < mp; i++) {
      const tk = document.createElement("span");
      tk.className = "mp-token";
      tokens.appendChild(tk);
    }
  }
  const num = document.createElement("span");
  num.className = "mp-count";
  num.textContent = `${t("ui.mp")} ${mp}`;
  tray.appendChild(tokens);
  tray.appendChild(num);
  return tray;
}

function slotEl(p, slot) {
  const buttons = [];
  const ab = slot.ability;
  if (ab && iControl(p)) {
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
  if (ab && iControl(p)) {
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

  if (!S.pending && S.battle && S.battle.step === "defense"
      && p === 1 - S.battle.attacker && iControl(p)) {
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

// 對決舞台:非戰鬥時收為發光細線,battle_in/battle 時展開承載攻防資訊與合計魔力
function renderBattleStage() {
  const stage = document.getElementById("battle-stage");
  const content = document.getElementById("stage-content");
  content.innerHTML = "";
  const open = !!(S.battle || S.battle_in);
  stage.classList.toggle("open", open);
  if (!open) return;
  if (S.battle_in) {
    content.innerHTML = `<span class="stage-hint">${t("ui.battle_in_hint", {
      player: pname(S.battle_in.attacker), spell: cname(S.battle_in.spell) })}</span>`;
    return;
  }
  const b = S.battle;
  const att = document.createElement("div");
  att.className = "stage-side attack";
  att.innerHTML =
    `<span class="side-label">${t("ui.battle_attack", { player: pname(b.attacker), spell: cname(b.attack_spell) })}` +
    (b.attack_negated ? `(${t("ui.negated")})` : "") +
    (b.attack_undefendable ? `(${t("ui.undefendable")})` : "") + `</span>` +
    `<span class="side-total" id="stage-att-total">${b.attacker_total}</span>`;
  const mid = document.createElement("div");
  mid.className = "stage-vs";
  mid.textContent = t("ui.battle");
  const def = document.createElement("div");
  def.className = "stage-side defense";
  def.innerHTML =
    (b.defense_spell
      ? `<span class="side-label">${t("ui.battle_defense", { player: pname(1 - b.attacker), spell: cname(b.defense_spell) })}` +
        (b.defense_negated ? `(${t("ui.negated")})` : "") + `</span>`
      : `<span class="side-label">${t("ui.battle_no_defense_yet")}</span>`) +
    `<span class="side-total" id="stage-def-total">${b.defender_total}</span>`;
  content.appendChild(att);
  content.appendChild(mid);
  content.appendChild(def);
  if (b.step === "effects") {
    const hint = document.createElement("div");
    hint.className = "stage-hint";
    hint.textContent = t("ui.battle_effects_hint", { player: pname(b.effect_turn) });
    content.appendChild(hint);
  }
}

function renderActionBar() {
  const bar = document.getElementById("action-bar");
  bar.innerHTML = "";
  if (!S || S.phase === "game_over" || S.pending) return;

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
  const waitHint = () => hint(t("ui.opponent_thinking"));

  if (S.phase === "start") {
    const tp = S.turn_player;
    if (!iControl(tp)) { waitHint(); return; }
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
    if (!iControl(dp)) { waitHint(); return; }
    hint(pname(dp));
    addBtn(t("ui.allow_battle"),
      () => send({ type: "battle_in_response", player: dp, allow: true }), true);
    return;
  }

  if (S.battle) {
    const b = S.battle;
    if (b.step === "defense") {
      const dp = 1 - b.attacker;
      if (!iControl(dp)) { waitHint(); return; }
      hint(pname(dp));
      addBtn(t("ui.no_defense"), () => send({ type: "no_defense", player: dp }));
    } else {
      if (!iControl(b.effect_turn)) { waitHint(); return; }
      hint(pname(b.effect_turn));
      addBtn(t("ui.pass"), () => send({ type: "pass", player: b.effect_turn }));
    }
    return;
  }

  if (S.action_player !== null) {
    if (!iControl(S.action_player)) { waitHint(); return; }
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
  if (!S || !S.pending || !S.pending.options || !iControl(S.pending.player)) {
    overlay.classList.add("hidden");
    return;
  }
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
    logSeq = ev.seq + 1;
    let line = logLine(ev);
    if (!line) continue;
    if (ev.timeout) line += t("ui.timeout_mark");
    const el = document.createElement("div");
    el.className = "ev";
    if (ev.type === "turn_started") el.classList.add("turn");
    if (["battle_started", "showdown", "game_ended", "attack_negated"].includes(ev.type)) {
      el.classList.add("important");
    }
    el.textContent = line;
    holder.appendChild(el);
  }
  holder.scrollTop = holder.scrollHeight;
}

// ---------------------------------------------------------------- 倒數計時

setInterval(() => {
  const el = document.getElementById("countdown");
  if (!R || !R.timer_seconds || !R.deadline || !S || S.phase === "game_over") {
    el.textContent = "";
    return;
  }
  const remain = Math.max(0, Math.round(R.deadline - (Date.now() / 1000 - clockDrift)));
  el.textContent = t("ui.countdown", { n: remain });
}, 500);

// ---------------------------------------------------------------- 牌組構築器

let B = null;  // {deck:{id,name,pages[32]}, selected: 頁index|null, ftype, fmamodo, fproduct}

function showBuilder() {
  const draft = DeckStore.loadDraft();
  const deck = draft && Array.isArray(draft.pages) && draft.pages.length === 32
    ? draft
    : { id: null, name: t("builder.new"), pages: Array(32).fill(null) };
  B = { deck, selected: null, ftype: "", fmamodo: "", fproduct: "" };
  show("builder");
  renderBuilderAll();
}

function builderMutated() {
  DeckStore.saveDraft(B.deck);
  renderBook();
  renderValidation();
}

function loadDeckIntoBuilder(deck) {
  B.deck = { id: deck.id, name: deck.name, pages: [...deck.pages] };
  B.selected = null;
  DeckStore.saveDraft(B.deck);
  renderBuilderAll();
}

// --- 頁位互動:選中→點另一頁=移動/互換;點選中的有卡頁=移除 ---
function togglePage(i) {
  const pages = B.deck.pages;
  if (B.selected === i) {
    if (pages[i]) pages[i] = null;       // 再點選中的有卡頁 → 移除
    else B.selected = null;
  } else if (B.selected !== null && pages[B.selected]) {
    [pages[B.selected], pages[i]] = [pages[i], pages[B.selected]];  // 移動/互換
    B.selected = null;
  } else {
    B.selected = i;
  }
  builderMutated();
}

function placeCard(num) {
  const pages = B.deck.pages;
  let target = B.selected;
  if (target === null) target = pages.indexOf(null);
  if (target === -1 || target === null) return;
  pages[target] = num;
  if (B.selected === null || pages.indexOf(null) !== -1) {
    B.selected = null;
  }
  builderMutated();
}

function swapPages(i, j) {
  const pages = B.deck.pages;
  [pages[i], pages[j]] = [pages[j], pages[i]];
  B.selected = null;
  builderMutated();
}

// --- 渲染 ---

function renderBuilderAll() {
  const head = document.getElementById("builder-head");
  document.getElementById("builder-back").textContent = t("builder.back");
  document.getElementById("builder-back").onclick = () => {
    history.replaceState(null, "", "/");
    renderLanding();  // 牌組清單可能已變,刷新選單
    show("landing");
  };
  document.getElementById("builder-save").textContent = t("builder.save");
  document.getElementById("builder-save").onclick = () => {
    B.deck = DeckStore.save({ ...B.deck, pages: [...B.deck.pages] });
    DeckStore.saveDraft(B.deck);
    renderDeckList();
    toast(t("builder.saved"));
  };
  document.getElementById("builder-delete").textContent = t("builder.delete");
  document.getElementById("builder-delete").onclick = () => {
    if (B.deck.id) DeckStore.remove(B.deck.id);
    loadDeckIntoBuilder({ id: null, name: t("builder.new"), pages: Array(32).fill(null) });
  };
  document.getElementById("builder-export").textContent = t("builder.export");
  document.getElementById("builder-export").onclick = () =>
    showIO(t("builder.io_title.export"), exportDeckCode(B.deck.pages), true);
  document.getElementById("builder-import").textContent = t("builder.import");
  document.getElementById("builder-import").onclick = () =>
    showIO(t("builder.io_title.import"), "", false, (text) => {
      const result = importDeckCode(text);
      if (result.error) {
        toast(t(result.error.key, result.error.params));
        return false;
      }
      const deck = DeckStore.create(t("builder.new"), result.pages);
      loadDeckIntoBuilder(deck);
      toast(t("builder.import_ok"));
      return true;
    });

  const nameInput = document.getElementById("builder-name");
  nameInput.placeholder = t("builder.deck_name");
  nameInput.value = B.deck.name;
  nameInput.onchange = () => {
    B.deck.name = nameInput.value || t("builder.new");
    DeckStore.saveDraft(B.deck);
  };

  renderDeckList();
  renderNewSelect();
  renderPoolFilters();
  renderPool();
  renderBook();
  renderValidation();
  document.getElementById("book-hint").textContent = t("builder.book");
}

function renderDeckList() {
  const sel = document.getElementById("builder-deck-list");
  sel.innerHTML = "";
  const head = document.createElement("option");
  head.value = "";
  head.textContent = t("builder.my_decks");
  sel.appendChild(head);
  for (const d of DeckStore.list()) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = d.name + (d.valid ? "" : t("ui.deck.invalid_suffix"));
    if (d.id === B.deck.id) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.onchange = () => {
    const deck = DeckStore.get(sel.value);
    if (deck) loadDeckIntoBuilder(deck);
  };
}

function renderNewSelect() {
  const sel = document.getElementById("builder-new");
  sel.innerHTML = "";
  const head = document.createElement("option");
  head.value = "";
  head.textContent = t("builder.new") + "…";
  sel.appendChild(head);
  const opts = [["blank", t("builder.new_blank")],
                ["level1", t("builder.new_from_level1")]];
  for (const d of DeckStore.list()) {
    opts.push(["copy:" + d.id, t("builder.new_from_deck", { name: d.name })]);
  }
  for (const [value, label] of opts) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  sel.onchange = () => {
    const v = sel.value;
    sel.value = "";
    if (!v) return;
    let pages = Array(32).fill(null);
    if (v === "level1") pages = [...LEVEL1];
    if (v.startsWith("copy:")) {
      const src = DeckStore.get(v.slice(5));
      if (src) pages = [...src.pages];
    }
    loadDeckIntoBuilder({ id: null, name: t("builder.new"), pages });
  };
}

function renderPoolFilters() {
  const holder = document.getElementById("pool-filters");
  holder.innerHTML = "";
  const typeSel = document.createElement("select");
  typeSel.innerHTML = `<option value="">${t("builder.filter.type")}:${t("builder.filter.all")}</option>`;
  for (const ty of ["mamodo", "partner", "spell", "event"]) {
    typeSel.innerHTML += `<option value="${ty}">${t("builder.type." + ty)}</option>`;
  }
  typeSel.value = B.ftype;
  typeSel.onchange = () => { B.ftype = typeSel.value; renderPool(); };
  holder.appendChild(typeSel);

  const mamodoSel = document.createElement("select");
  const names = [...new Set(Object.values(CARDS)
    .map((c) => c.related_mamodo).filter((m) => m && m !== "Command: All"))].sort();
  mamodoSel.innerHTML = `<option value="">${t("builder.filter.mamodo")}:${t("builder.filter.all")}</option>`;
  for (const name of names) {
    const numAny = Object.values(CARDS).find(
      (c) => c.type === "mamodo" && c.related_mamodo === name);
    const zh = numAny && ZH[numAny.number] ? ZH[numAny.number].name : name;
    mamodoSel.innerHTML += `<option value="${name}">${zh}</option>`;
  }
  mamodoSel.value = B.fmamodo;
  mamodoSel.onchange = () => { B.fmamodo = mamodoSel.value; renderPool(); };
  holder.appendChild(mamodoSel);

  // 產品(彈數)篩選:同一張卡可屬多個產品
  const productSel = document.createElement("select");
  const products = [...new Set(Object.values(CARDS).flatMap((c) => c.sets || []))].sort();
  productSel.innerHTML = `<option value="">${t("builder.filter.product")}:${t("builder.filter.all")}</option>`;
  for (const tag of products) {
    productSel.innerHTML += `<option value="${tag}">${tag}</option>`;
  }
  productSel.value = B.fproduct;
  productSel.onchange = () => { B.fproduct = productSel.value; renderPool(); };
  holder.appendChild(productSel);
}

function renderPool() {
  const grid = document.getElementById("pool-grid");
  grid.innerHTML = "";
  const numbers = Object.keys(CARDS).sort();
  for (const num of numbers) {
    const def = CARDS[num];
    if (B.ftype && def.type !== B.ftype) continue;
    if (B.fmamodo && def.related_mamodo !== B.fmamodo) continue;
    if (B.fproduct && !(def.sets || []).includes(B.fproduct)) continue;
    const el = cardEl(num, { small: true });
    el.onclick = () => placeCard(num);
    grid.appendChild(el);
  }
}

function pageSlotEl(i) {
  const slot = document.createElement("div");
  slot.className = "page-slot" + (B.selected === i ? " selected" : "")
    + (B.deck.pages[i] ? " filled" : "");
  const pno = document.createElement("span");
  pno.className = "pno";
  pno.textContent = i === 0 ? t("builder.page_first")
    : i === 31 ? t("builder.page_last") : `P${i + 1}`;
  slot.appendChild(pno);
  const num = B.deck.pages[i];
  if (num) {
    const card = cardEl(num, { small: true });
    card.onclick = (ev) => { ev.stopPropagation(); togglePage(i); };
    slot.appendChild(card);
    slot.draggable = true;
    slot.ondragstart = (ev) => ev.dataTransfer.setData("text/plain", String(i));
  } else {
    const label = document.createElement("span");
    label.className = "empty-label";
    label.textContent = t("builder.empty_page", { n: i + 1 });
    slot.appendChild(label);
  }
  slot.onclick = () => togglePage(i);
  slot.ondragover = (ev) => { ev.preventDefault(); slot.classList.add("dragover"); };
  slot.ondragleave = () => slot.classList.remove("dragover");
  slot.ondrop = (ev) => {
    ev.preventDefault();
    const from = Number(ev.dataTransfer.getData("text/plain"));
    if (!Number.isNaN(from) && from !== i) swapPages(from, i);
  };
  return slot;
}

function renderBook() {
  const grid = document.getElementById("book-grid");
  grid.innerHTML = "";
  const spread = (indices, single) => {
    const el = document.createElement("div");
    el.className = "spread" + (single ? " single" : "");
    for (const i of indices) el.appendChild(pageSlotEl(i));
    grid.appendChild(el);
  };
  spread([0], true);                       // P1 首頁
  for (let i = 1; i < 31; i += 2) spread([i, i + 1], false);  // P2-3 ... P30-31
  spread([31], true);                      // P32 末頁
}

function renderValidation() {
  const bar = document.getElementById("builder-validation");
  bar.innerHTML = "";
  const errors = validateDeckPages(B.deck.pages);
  if (errors.length === 0) {
    const ok = document.createElement("span");
    ok.className = "ok";
    ok.textContent = t("builder.valid");
    bar.appendChild(ok);
  } else {
    for (const e of errors) {
      const el = document.createElement("span");
      el.className = "err";
      el.textContent = t(e.key, e.params);
      bar.appendChild(el);
    }
  }
  const mamodo = B.deck.pages.filter((c) => c && CARDS[c].type === "mamodo").length;
  const stat = document.createElement("span");
  stat.className = "stat";
  stat.textContent = t("builder.mamodo_count", { n: mamodo });
  bar.appendChild(stat);
}

function showIO(title, text, readonly, onConfirm) {
  const overlay = document.getElementById("io-overlay");
  document.getElementById("io-title").textContent = title;
  const ta = document.getElementById("io-text");
  ta.value = text;
  ta.readOnly = readonly;
  const actions = document.getElementById("io-actions");
  actions.innerHTML = "";
  if (readonly) {
    const copy = document.createElement("button");
    copy.textContent = t("ui.copy");
    copy.onclick = () => {
      navigator.clipboard.writeText(ta.value);
      copy.textContent = t("ui.copied");
    };
    actions.appendChild(copy);
  } else {
    const confirm = document.createElement("button");
    confirm.textContent = t("builder.confirm_import");
    confirm.onclick = () => {
      if (onConfirm(ta.value) !== false) overlay.classList.add("hidden");
    };
    actions.appendChild(confirm);
    ta.placeholder = t("builder.import_placeholder");
  }
  const close = document.createElement("button");
  close.textContent = t("ui.close");
  close.onclick = () => overlay.classList.add("hidden");
  actions.appendChild(close);
  overlay.classList.remove("hidden");
}

// ---------------------------------------------------------------- 入口頁渲染與啟動

function renderLanding() {
  document.getElementById("landing-title").textContent = t("app.title");
  const local = document.getElementById("entry-local");
  local.querySelector("h2").textContent = t("ui.landing.local");
  local.querySelector("p").textContent = t("ui.landing.local_desc");
  local.querySelector("button").textContent = t("ui.landing.go");
  local.querySelector("button").onclick = startLocal;

  const create = document.getElementById("entry-create");
  create.querySelector("h2").textContent = t("ui.landing.create");
  create.querySelector("p").textContent = t("ui.landing.create_desc");
  document.getElementById("timer-label").textContent = t("ui.landing.timer");
  const sel = document.getElementById("timer-select");
  sel.innerHTML = "";
  for (const [value, label] of [["", t("ui.timer.off")],
      ["30", t("ui.timer.n", { n: 30 })], ["60", t("ui.timer.n", { n: 60 })],
      ["120", t("ui.timer.n", { n: 120 })]]) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  create.querySelector("button").textContent = t("ui.landing.go");
  create.querySelector("button").onclick = createRoom;

  const join = document.getElementById("entry-join");
  join.querySelector("h2").textContent = t("ui.landing.join");
  join.querySelector("p").textContent = t("ui.landing.join_desc");
  join.querySelector("button").textContent = t("ui.landing.go");
  join.querySelector("button").onclick = () => {
    const code = document.getElementById("join-code").value.trim();
    if (code) joinRoom(code);
  };

  const builderEntry = document.getElementById("entry-builder");
  builderEntry.querySelector("h2").textContent = t("ui.landing.builder");
  builderEntry.querySelector("p").textContent = t("ui.landing.builder_desc");
  builderEntry.querySelector("button").textContent = t("ui.landing.go");
  builderEntry.querySelector("button").onclick = () => {
    history.replaceState(null, "", "/?builder=1");
    showBuilder();
  };

  // 牌組選單(本機×2 / 建房 / 加入)
  document.getElementById("deck-local-0-label").textContent = t("ui.deck.p1");
  document.getElementById("deck-local-1-label").textContent = t("ui.deck.p2");
  document.getElementById("deck-create-label").textContent = t("ui.deck.select");
  document.getElementById("deck-join-label").textContent = t("ui.deck.select");
  for (const id of ["deck-local-0", "deck-local-1", "deck-create", "deck-join"]) {
    deckOptions(document.getElementById(id));
  }

  document.getElementById("share-join-label").textContent = t("ui.share.join");
  document.getElementById("share-spec-label").textContent = t("ui.share.spectate");
  for (const btn of document.querySelectorAll("[data-copy]")) {
    btn.textContent = t("ui.copy");
    btn.onclick = () => {
      navigator.clipboard.writeText(document.getElementById(btn.dataset.copy).value);
      btn.textContent = t("ui.copied");
      setTimeout(() => { btn.textContent = t("ui.copy"); }, 1500);
    };
  }
  document.getElementById("leave-room").onclick = leaveRoom;
}

async function boot() {
  [DICT, CARDS, ZH, LEVEL1] = await Promise.all([
    fetch("/static/i18n/zh-TW.json").then((r) => r.json()),
    fetch("/data/cards.json").then((r) => r.json()).then((list) =>
      Object.fromEntries(list.map((c) => [c.number, c]))),
    fetch("/data/cards.zh-TW.json").then((r) => r.json()),
    fetch("/data/decks/level1.json").then((r) => r.json()).then((d) => d.pages),
  ]);
  renderLanding();
  renderTopbar();

  const params = new URLSearchParams(location.search);
  if (params.has("join")) {
    // 停在入口頁預填房號,讓加入者先選牌組再加入
    document.getElementById("join-code").value = params.get("join").toUpperCase();
    show("landing");
  } else if (params.has("spectate")) {
    enterSpectate(params.get("spectate"), params.get("token") || "");
  } else if (params.has("room")) {
    await resumeRoom(params.get("room"));
  } else if (params.has("builder")) {
    showBuilder();
  } else {
    show("landing");
  }
}

boot();
