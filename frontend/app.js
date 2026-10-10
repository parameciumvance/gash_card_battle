/* Gash Card Battle Online — 前端
 * 模式:本機(local, 全視角雙 token)/ 線上(online, 單 token + WS)/ NPC 對戰(npc, 同線上,對手由伺服器驅動)
 * / 觀戰(spectator)。
 * 規則裁決與資訊過濾全在後端;前端渲染視角化快照、送指令、渲染事件 log。 */

"use strict";

let DICT = {};        // i18n 字典(目前語言)
let CARDS = {};       // 卡片數值資料(decks.js 的驗證也依賴)
let TEXT = {};        // 卡片文字(目前語言的 data/cards.<lang>.json)
let PRESETS = [];     // 探索得到的預組清單 [{id, name}]
let META = { assets: null, version: null };  // /api/meta:卡圖安裝狀態、版本號
let RULES = null;     // 規則頁內容(i18n/rules.<lang>.json)
let RELEASES = null;  // 更新內容(i18n/releases.<lang>.json 的 releases,最新的在前);載入失敗為 null

// 窄螢幕(手機直向)偵測:佈局由 CSS 切換,JS 僅供 log 抽屜等行為分支
const NARROW_MQ = window.matchMedia("(max-width: 700px)");
function isNarrow() { return NARROW_MQ.matches; }
NARROW_MQ.addEventListener("change", () => {
  document.getElementById("log-panel").classList.remove("open");
  if (S) render();
});
const DEFAULT_PRESET = "level1";  // 缺省預組 id(與後端一致)
// 意見回報管道。formUrl 空白時只顯示 GitHub;contextEntry 是表單「環境資訊」欄位的 entry id(預填用)
const FEEDBACK = {
  formUrl: "https://docs.google.com/forms/d/e/1FAIpQLSdPa_q5eS3ONbpkIF30uVFrR_AZblxFrdF4pGOLnU-chfkfGQ/viewform",
  contextEntry: "entry.1381931511",
  issuesUrl: "https://github.com/parameciumvance/gash_card_battle/issues/new/choose",
};
let S = null;         // 最新遊戲狀態快照(視角化)
let R = null;         // 房間 meta {code, mode, you, deadline, ...}
let SESSION = null;   // {code, mode, viewer, tokens:{playerIndex→token} 或 {me:token}}
let ws = null;
let wsWanted = false;
let logSeq = 0;
let animSeq = 0;      // 動畫事件游標:HTTP 回應與 WS 推送重複投遞同批事件時只演一次
let clockDrift = 0;   // Date.now()/1000 - server_time

// ---------------------------------------------------------------- i18n

function t(key, params = {}) {
  let s = DICT[key];
  if (s === undefined) return key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (params[k] !== undefined ? params[k] : `{${k}}`));
}

// 語言:清單在 i18n/languages.json(順序即選單順序);選擇記在 localStorage,切換時重新載入頁面
const LANG_KEY = "gash-lang";
const FALLBACK_LANG = "zh-TW";
let LANGS = [{ code: FALLBACK_LANG, name: "繁體中文" }];
let LANG = FALLBACK_LANG;

// 簡體中文的瀏覽器語言;其他 zh(含只有 zh)依主語言落在清單中排在前面的繁中
function isSimplifiedChinese(pref) {
  const tag = pref.toLowerCase();
  return ["zh-cn", "zh-sg", "zh-my"].includes(tag) || tag.startsWith("zh-hans");
}

// 玩家選過的語言優先;未選過時依瀏覽器偏好語言,取第一個能對應(簡中別名,或主語言相同)者,都不符合為英文
function detectLang() {
  const codes = LANGS.map((l) => l.code);
  let saved = null;
  try { saved = localStorage.getItem(LANG_KEY); } catch (_) { /* 無法存取時依瀏覽器 */ }
  if (codes.includes(saved)) return saved;
  const primary = (code) => code.toLowerCase().split("-")[0];
  for (const pref of navigator.languages || [navigator.language || ""]) {
    if (isSimplifiedChinese(pref) && codes.includes("zh-CN")) return "zh-CN";
    const hit = codes.find((c) => primary(c) === primary(pref));
    if (hit) return hit;
  }
  return codes.includes("en") ? "en" : FALLBACK_LANG;
}

function setLang(code) {
  try { localStorage.setItem(LANG_KEY, code); } catch (_) { /* 只在本次生效 */ }
  location.reload();   // 走既有的接回路徑:對局、觀戰、構築器、加入連結都回到原處,行動記錄以新語言重建
}

function renderLangInfo() {
  const row = document.createElement("div");
  row.className = "prefs-options";
  for (const l of LANGS) {
    const btn = document.createElement("button");
    btn.textContent = l.name;
    btn.lang = l.code;
    btn.dataset.lang = l.code;
    btn.setAttribute("aria-pressed", String(l.code === LANG));
    btn.onclick = () => { if (l.code === LANG) closeInfo(); else setLang(l.code); };
    row.appendChild(btn);
  }
  showInfo("lang", t("ui.lang.title"), [row]);
}

function pname(p) {
  if (R && R.npc && R.npc.seat === p) return t(`ui.npc.name.${R.npc.level}`);
  const custom = R && R.names && R.names[p];
  return custom || t("ui.player", { n: p + 1 });
}

// 預組名稱:name_key 依目前語言解析,字典沒有時用伺服器給的 name
function presetName(p) {
  return p.name_key && DICT[p.name_key] !== undefined ? t(p.name_key) : p.name;
}

// NPC 使用的牌組(對局結束後才由房間 meta 公開):預組名稱 / 本機儲存牌組名稱 / 「自訂牌組」
function npcDeckName(deck) {
  if (deck.preset) {
    const preset = PRESETS.find((p) => p.id === deck.preset);
    return preset ? presetName(preset) : deck.preset;
  }
  const key = JSON.stringify(deck.pages);
  const saved = DeckStore.list().find((d) => JSON.stringify(d.pages) === key);
  return saved ? saved.name : t("ui.npc.custom_deck");
}

// 暱稱記憶(localStorage);清理與後端一致(去空白、限長 16)
function loadNick() { return localStorage.getItem("gash-nick") || ""; }
function saveNick(v) {
  const clean = (v || "").trim().slice(0, 16);
  if (clean) localStorage.setItem("gash-nick", clean);
  return clean || null;
}

// 卡名:同名魔物以效果名區分(格式依語言,ui.card_with_attr)
function cname(num) {
  const z = TEXT[num];
  if (!z) return num;
  return z.attr && CARDS[num] && CARDS[num].type === "mamodo"
    ? t("ui.card_with_attr", { name: z.name, attr: z.attr }) : z.name;
}

// ---------------------------------------------------------------- 演出設定(存於瀏覽器)

const PREFS = { spotlight: ["normal", "fast", "off"], motion: ["on", "off", "system"], sound: ["on", "off"] };

function pref(name) {
  let value = null;
  try { value = localStorage.getItem(`gash-${name}`); } catch (_) { /* 無法存取時用缺省 */ }
  return PREFS[name].includes(value) ? value : PREFS[name][name === "motion" ? 2 : 0];
}

function setPref(name, value) {
  try { localStorage.setItem(`gash-${name}`, value); } catch (_) { /* 仍於本次生效 */ }
}

function spotlightMode() { return pref("spotlight"); }   // normal | fast | off

// 動畫關閉:玩家設定優先,未設定(跟隨系統)時依 prefers-reduced-motion
function motionOff() {
  const m = pref("motion");
  if (m !== "system") return m === "off";
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function applyMotionClass() {
  document.documentElement.classList.toggle("motion-off", motionOff());
}
window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", applyMotionClass);

function renderPrefsInfo() {
  const group = (name) => {
    const sec = document.createElement("div");
    sec.className = "info-section";
    const h = document.createElement("h4");
    h.textContent = t(`ui.prefs.${name}`);
    const row = document.createElement("div");
    row.className = "prefs-options";
    for (const value of PREFS[name]) {
      const btn = document.createElement("button");
      btn.textContent = t(`ui.prefs.${name}.${value}`);
      btn.setAttribute("aria-pressed", String(pref(name) === value));
      btn.onclick = () => { setPref(name, value); applyMotionClass(); renderPrefsInfo(); };
      row.appendChild(btn);
    }
    sec.append(h, row);
    return sec;
  };
  showInfo("prefs", t("ui.prefs.title"), [group("spotlight"), group("motion"), group("sound")]);
}

// ---------------------------------------------------------------- session / 身分

function myViewer() { return SESSION ? SESSION.viewer : null; }   // 0|1|"all"|"spectator"
// 聚焦展示用的「自己」:本機(全視角)與觀戰沒有自己的一方 → null(雙方都聚焦)
function selfPlayer() { const v = myViewer(); return v === 0 || v === 1 ? v : null; }
function isLocal() { return SESSION && SESSION.mode === "local"; }
function isNpc() { return SESSION && SESSION.mode === "npc"; }
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
    // 依錯誤碼以目前語言顯示;字典沒有該錯誤碼時用伺服器原文
    const code = body.detail && body.detail.code;
    const msg = code && DICT[`error.${code}`] !== undefined ? t(`error.${code}`)
      : body.detail && body.detail.message ? body.detail.message : JSON.stringify(body);
    const err = new Error(msg);
    err.code = code;
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
  if (body.state) { S = body.state; LOCAL_PICK = null; }   // 新快照:前端的場上選擇作廢
  if (body.room) { R = body.room; clockDrift = Date.now() / 1000 - R.server_time; }
  if (body.events) appendLog(body.events);
  if (R && R.started && SESSION && S) show("layout");  // 對手加入 → 離開等待畫面
  // 統一動畫管線:量測 → 阻塞演出 → 重繪 → 疊加特效(reduced-motion 直接重繪)
  // 同批事件經 HTTP 回應與 WS 推送各到一次,以 seq 游標去重,只演第一次
  const fresh = (body.events || []).filter((ev) => ev.seq >= animSeq);
  for (const ev of fresh) animSeq = Math.max(animSeq, ev.seq + 1);
  // 翻閱中的魔書被翻動:先以前一個快照把魔書區畫回目前頁,翻頁動畫才從正確的位置開始
  const flipped = fresh.filter((ev) => (ev.type === "pages_flipped" || ev.type === "pages_turned")
    && ev.count && BOOK_BROWSE[ev.player]);
  if (flipped.length && prevS) {
    for (const ev of flipped) delete BOOK_BROWSE[ev.player];
    const next = S;
    S = prevS;
    render();
    S = next;
  }
  const played = Anim.apply(fresh, prevS, render, body.actor);
  // 檢視對手頁面(E-014 / M-018):只對即時批次(有行動者)在演出結束後跳出;
  // 伺服器已依視角過濾,帶 cards 的就是自己檢視的
  const live = body.actor !== null && body.actor !== undefined;
  const peeks = live ? fresh.filter((ev) => ev.type === "pages_peeked" && ev.cards) : [];
  if (peeks.length) played.then(() => showPeek(peeks));
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
  if (sectionId !== "layout") closeCheat();
  for (const id of ["landing", "setup", "waiting", "layout", "builder"]) {
    document.getElementById(id).classList.toggle("hidden", id !== sectionId);
  }
  if (sectionId === "landing") maybeShowRelease();
  else if (INFO && INFO.kind.startsWith("release")) closeInfo();   // 更新內容只在首頁顯示
  syncOnline();   // 對戰中人數:進入首頁時抓取,離開時停止
}

// ---------------------------------------------------------------- 牌組選單與 payload

function deckOptions(sel) {
  sel.innerHTML = "";
  for (const p of PRESETS) {                 // 探索得到的預組(value 帶 preset: 前綴)
    const opt = document.createElement("option");
    opt.value = `preset:${p.id}`;
    opt.textContent = presetName(p);
    sel.appendChild(opt);
  }
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
  if (value.startsWith("preset:")) return { preset: value.slice(7) };
  const deck = DeckStore.get(value);
  return deck ? { pages: deck.pages } : { preset: DEFAULT_PRESET };
}

function nameVal(id) {
  const v = document.getElementById(id).value.trim().slice(0, 16);
  return v || null;
}

async function startLocal() {
  const body = await api("/api/rooms", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "local",
      decks: [deckPayload("deck-local-0"), deckPayload("deck-local-1")],
      names: [nameVal("name-local-0"), nameVal("name-local-1")] }),
  });
  SESSION = { code: body.code, mode: "local", viewer: "all",
              tokens: { 0: body.player_tokens[0], 1: body.player_tokens[1] } };
  saveSession();
  history.replaceState(null, "", `/?room=${body.code}`);
  resetLog();
  applyPayload(body);
  show("layout");
}

const NPC_RANDOM_DECK = "npc:random";

// 「隨機」:所有預組與本機儲存的合法牌組都是候選
function npcDeckCandidates() {
  return PRESETS.map((p) => ({ preset: p.id }))
    .concat(DeckStore.validList().map((d) => ({ pages: d.pages })));
}

async function startNpc() {
  const payload = { mode: "npc", deck: deckPayload("deck-npc"),
    npc_level: document.getElementById("npc-level").value,
    name: saveNick(document.getElementById("name-npc").value) };
  if (document.getElementById("deck-npc-opp").value === NPC_RANDOM_DECK) {
    payload.npc_decks = npcDeckCandidates();
  } else {
    payload.npc_deck = deckPayload("deck-npc-opp");
  }
  try {
    const body = await api("/api/rooms", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    SESSION = { code: body.code, mode: "npc", viewer: 0, tokens: { me: body.player_token } };
    saveSession();
    history.replaceState(null, "", `/?room=${body.code}`);
    resetLog();
    applyPayload(body);
    show("layout");
    openWS();   // NPC 的行動經 WS 推送
  } catch (err) {
    toast(t("ui.error", { msg: err.message }));
  }
}

async function createRoom() {
  const timer = document.getElementById("timer-select").value;
  const body = await api("/api/rooms", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "online", timer_seconds: timer ? Number(timer) : null,
      deck: deckPayload("deck-friend"), name: saveNick(document.getElementById("name-friend").value) }),
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
      body: JSON.stringify({ deck: deckPayload("deck-friend"),
                             name: saveNick(document.getElementById("name-friend").value) }),
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
    toast(t("ui.error", { msg: err.message }));   // 留在設定頁,可修正房號再加入
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
  closeCheat();
  closeInfo();
  wsWanted = false;
  if (ws) ws.close();
  SESSION = null; S = null; R = null;
  history.replaceState(null, "", "/");
  show("landing");
  renderTopbar();
}

function resetLog() {
  logSeq = 0;
  animSeq = 0;
  document.getElementById("log").innerHTML = "";
}

// ---------------------------------------------------------------- 卡片元件

// 卡圖一律是 WebP;卡片元件、聚焦展示(anim.js)、規則頁共用
function artUrl(num) { return `/static/assets/cards/${num}.webp`; }

function cardEl(num, opts = {}) {
  const def = CARDS[num] || {};
  const z = TEXT[num] || { name: num };
  const el = document.createElement("div");
  el.className = `card type-${def.type || "mamodo"}` + (opts.small ? " small" : "") +
    (opts.injured ? " injured" : "");

  const art = document.createElement("img");
  art.className = "art";
  art.src = artUrl(num);
  art.onerror = () => {  // 缺圖以卡背佔位(onerror 先清空避免佔位圖也缺時迴圈)
    art.onerror = () => art.remove();
    art.classList.add("placeholder");
    art.src = "/static/back.jpg";
  };
  el.appendChild(art);

  const cn = document.createElement("div");
  cn.className = "cname";
  cn.textContent = opts.fullName ? cname(num) : z.name;   // 放大檢視以效果名區分同名魔物
  el.appendChild(cn);

  if (LANG !== "ja") {   // 日文原名小字;日文時與卡名重複,不顯示
    const ja = document.createElement("div");
    ja.className = "cname-ja";
    ja.lang = "ja";
    ja.textContent = z.name_ja || "";
    el.appendChild(ja);
  }

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
  meta.textContent = bits.join(t("ui.sep.meta"));
  if (def.class === "intermediate" || def.class === "superior") {   // 中級 / 上級:限制可放的頁數
    const cls = document.createElement("span");
    cls.className = `cclass cclass-${def.class}`;
    cls.textContent = t(`card.class.${def.class}`);
    meta.appendChild(cls);
  }
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

  if (opts.detail) {   // 牌組編輯器:詳情按鈕開純展示放大檢視,不觸發放卡 / 選取 / 拖拉
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "card-detail";
    btn.textContent = "i";
    btn.title = t("builder.detail");
    btn.setAttribute("aria-label", t("builder.detail"));
    btn.draggable = false;
    btn.onclick = (ev) => { ev.stopPropagation(); zoom(num); };
    btn.onkeydown = (ev) => ev.stopPropagation();   // Enter / Space 只觸發按鈕,不傳到卡片或頁位
    btn.onmousedown = (ev) => ev.stopPropagation();
    el.appendChild(btn);
  }

  el.onclick = () => zoom(num, opts.zoomCtx);
  return el;
}

// 把元素內文字中出現的卡名包成可點 span(開純展示檢視)。
// 以 splitText 做 DOM 分割,不拼 HTML;找不到片段即跳過(退回純文字)。
function linkCardNames(root, nums) {
  for (const num of nums) {
    const name = cname(num);
    if (!name) continue;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement.closest(".card-ref")) continue;
      const idx = node.data.indexOf(name);
      if (idx < 0) continue;
      const target = node.splitText(idx);
      target.splitText(name.length);
      const span = document.createElement("span");
      span.className = "card-ref";
      span.textContent = name;
      span.onclick = (ev) => { ev.stopPropagation(); zoom(num); };
      target.replaceWith(span);
      break;  // 每卡只包首次出現
    }
  }
}

// 事件中引用的卡號(值符合卡號格式且存在於卡片庫者)
function cardRefs(ev) {
  const out = new Set();
  for (const v of Object.values(ev)) {
    if (typeof v === "string" && /^[EMPS]-\d{3}$/.test(v) && CARDS[v]) out.add(v);
  }
  return [...out];
}

function cardBackEl(page, consumed = false) {
  const el = document.createElement("div");
  el.className = "card back" + (consumed ? " consumed" : "");
  return el;
}

// 放大檢視 = 卡片實例面板:完整資訊 + 該實例此刻可用的行動按鈕(統一操作入口)
let ZOOM = null;  // {num, ctx};ctx 無值 = 純展示(卡池/記錄/檢閱等)

function zoom(num, ctx) {
  ZOOM = { num, ctx: ctx || null };
  renderZoom();
}

function closeZoom() {
  ZOOM = null;
  document.getElementById("zoom-overlay").classList.add("hidden");
}

// 依實例上下文自當前快照取行動按鈕;實例已不存在 → {gone: true}
function zoomActions(ctx) {
  const ps = S && S.players[ctx.p];
  if (!ps) return { gone: true };
  if (ctx.kind === "slot") {
    const slot = ps.slots.find((s) => s.uid === ctx.uid);
    return slot ? { buttons: slotButtons(ctx.p, slot) } : { gone: true };
  }
  if (ctx.kind === "partner") {
    const slot = ps.slots.find((s) => s.uid === ctx.uid);
    return slot && slot.partner ? { buttons: partnerButtons(ctx.p, slot) } : { gone: true };
  }
  if (ctx.kind === "any_page") {
    const entry = (ps.any_page_spells || []).find((e) => e.page === ctx.page);
    return entry ? { buttons: anyPageButtons(ctx.p, entry) } : { gone: true };
  }
  if (ctx.kind === "borrowed") {
    const borrow = borrowedEffect(ctx.p);
    return borrow ? { buttons: borrowedButtons(ctx.p, borrow) } : { gone: true };
  }
  if (ctx.kind === "page") {
    const entry = ps.open_pages.find((e) => e.page === ctx.page && e.card);
    return entry ? { buttons: pageButtons(ctx.p, entry) } : { gone: true };
  }
  if (ctx.kind === "pick") return pickValue(ctx) !== undefined ? { buttons: [] } : { gone: true };   // 魔書網格、棄牌區中的目標
  return { buttons: [] };
}

function renderZoom() {
  if (!ZOOM) return;
  const overlay = document.getElementById("zoom-overlay");
  const holder = document.getElementById("zoom-card");
  const actions = document.getElementById("zoom-actions");
  holder.innerHTML = "";
  actions.innerHTML = "";

  const opts = {};
  let buttons = [];
  if (ZOOM.ctx) {
    const r = zoomActions(ZOOM.ctx);
    if (r.gone) { closeZoom(); return; }  // 卡片已離場(狀態更新)→ 自動關閉
    buttons = PICK && PICK.local ? pickButtons(ZOOM.ctx) : [...pickButtons(ZOOM.ctx), ...r.buttons];
    if (ZOOM.ctx.kind === "page") {
      const entry = S.players[ZOOM.ctx.p].open_pages.find((e) => e.page === ZOOM.ctx.page);
      if (entry) opts.cost = entry.cost;
    }
  }

  opts.fullName = true;
  const card = cardEl(ZOOM.num, opts);
  card.onclick = (ev) => ev.stopPropagation();  // 點卡面不關閉、不重開
  holder.appendChild(card);

  for (const b of buttons) {
    const row = document.createElement("div");
    row.className = "zoom-action";
    row.onclick = (ev) => ev.stopPropagation();
    const btn = document.createElement("button");
    btn.textContent = b.label;
    if (b.primary) btn.classList.add("primary");
    if (b.disabled) {
      btn.disabled = true;
      if (b.reason) {  // 禁用原因直接呈現(觸控無 hover title)
        const why = document.createElement("span");
        why.className = "zoom-reason";
        why.textContent = b.reason;
        row.appendChild(why);
      }
    } else {
      btn.onclick = (ev) => { ev.stopPropagation(); closeZoom(); b.onclick(); };
    }
    row.prepend(btn);
    actions.appendChild(row);
  }
  overlay.classList.remove("hidden");
}

document.getElementById("zoom-overlay").onclick = closeZoom;

// ---------------------------------------------------------------- 合法操作判斷

function inNonBattle() { return S.phase === "battle" && !S.battle && !S.battle_in && !S.pending; }

// 目前的時機(時機指示、行動欄摘要與提示共用):start / nonbattle / battle_in / defense / effects / end / over。
// 結束階段沒有自己的 phase 值,只在魔物消失處理等待選頁時停下
function currentTiming() {
  if (S.phase === "game_over") return "over";
  if (S.pending && S.pending.kind === "deploy_page") return "end";
  if (S.phase === "start") return "start";
  if (S.battle_in) return "battle_in";
  if (S.battle) return S.battle.step === "defense" ? "defense" : "effects";
  return "nonbattle";
}

// 目前等待輸入的玩家(與伺服器的 awaited_player 相同規則,由快照推得;預設為目前快照)
function awaitedPlayer(st = S) {
  if (st.phase === "game_over") return null;
  if (st.pending) return st.pending.player;
  if (st.phase === "start") return st.turn_player;
  if (st.battle) return st.battle.step === "defense" ? 1 - st.battle.attacker : st.battle.effect_turn;
  if (st.battle_in) return 1 - st.battle_in.attacker;
  return st.action_player;
}

function canActNow(p) {
  if (!iControl(p)) return false;
  if (S.pending) return false;
  if (S.battle_in) return p === 1 - S.battle_in.attacker;
  if (S.battle) return false;
  return S.phase === "battle" && S.action_player === p;
}

const COMMAND_MAMODO = "コマンド";
function isCommandSpell(def) { return def.type === "spell" && def.related_mamodo === COMMAND_MAMODO; }

// 與引擎 _spell_usable_by 的家族及 M-023/M-029 相容性保持一致。
// 可使用此戰術的魔物:以快照的 users 為準(引擎的相容判定),前端不自行判斷相容規則。
// selectable = 未被 E-024 封鎖且 MP 足以支付該魔物使用時的費用
function spellUsers(p, entry) {
  const mp = S.players[p].mp;
  return (entry.users || []).map((u) => {
    const reason = u.locked ? t("ui.spell.locked") : u.cost > mp ? t("ui.spell.mp", { mp, cost: u.cost }) : null;
    return { ...u, selectable: !reason, reason };
  });
}

// 至少一隻可選才可用;沒有可使用的魔物、或都不可選時回傳第一個原因
function spellUsersCheck(p, entry) {
  const users = spellUsers(p, entry);
  if (!users.length) return { ok: false, reason: t("ui.spell.no_mamodo") };
  if (!users.some((u) => u.selectable)) return { ok: false, reason: users[0].reason };
  return { ok: true };
}

function nonbattleSpellUsable(p, entry) {
  const def = CARDS[entry.card];
  const ps = S.players[p];
  if ((def.ad === "A" && p !== S.turn_player) || (def.ad === "D" && p === S.turn_player)) {
    return { ok: false, reason: t(def.ad === "A" ? "ui.spell.own_turn" : "ui.spell.other_turn") };
  }
  if ((ps.used_nonbattle_spells || []).includes(entry.card)) return { ok: false, reason: t("ui.used") };
  return spellUsersCheck(p, entry);
}

function spellUsable(p, entry, forAttack) {
  const def = CARDS[entry.card];
  const ps = S.players[p];
  if (def.type !== "spell" || def.effect_icon === "nonbattle") return { ok: false };
  const icon = forAttack ? ["A", "AD"] : ["D", "AD"];
  if (!icon.includes(def.ad)) return { ok: false };
  if ((ps.used_spell_pages || []).includes(entry.page)) return { ok: false, reason: t("ui.used") };
  return { ...spellUsersCheck(p, entry), isCommand: isCommandSpell(def) };
}

// 選擇戰術的使用魔物(攻防、非戰鬥相同):可選的只有一隻 → 直接;兩隻以上 → 場上選擇。一律送出 slot_uid
function pickSpellUser(p, entry, cb) {
  const users = spellUsers(p, entry);
  const ok = users.filter((u) => u.selectable);
  if (!ok.length) return;
  if (ok.length === 1) { cb(ok[0].slot_uid); return; }
  const title = isCommandSpell(CARDS[entry.card]) ? t("ui.pick_command_user") : t("ui.pick_spell_user");
  startLocalPick({
    player: p, title, source: entry.card, onpick: cb,
    options: new Map(users.map((u) => [u.slot_uid,
      { selectable: u.selectable, note: t("ui.cost", { n: u.cost }), reason: u.reason }])),
  });
}

// 搭檔卡的裝備對象:對應(頂層魔物的對應魔物相同)且尚未裝搭檔的自己魔物
function partnerTargets(p, def) {
  const matching = S.players[p].slots.filter((s) => CARDS[s.top].related_mamodo === def.related_mamodo);
  return { matching, free: matching.filter((s) => !s.partner) };
}

function pickPartnerTarget(p, def, cb) {
  const { free } = partnerTargets(p, def);
  if (free.length <= 1) { if (free.length) cb(free[0].uid); return; }
  startLocalPick({
    player: p, title: t("choice.title.pick_mamodo_for_partner"), source: def.number, onpick: cb,
    options: new Map(free.map((s) => [s.uid, { selectable: true }])),
  });
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
  PICK = pickState();
  renderPlayerZone(document.getElementById("zone-top"), topPlayerIndex(), true);
  renderPlayerZone(document.getElementById("zone-bottom"), 1 - topPlayerIndex(), false);
  renderTimingTrack();
  renderBattleStage();
  renderActionBar();
  if (BOOK_VIEW !== null) showBookReview(BOOK_VIEW);   // 開啟中的魔書網格依新狀態重繪(決策結束時不再可選)
  if (ZOOM) renderZoom();  // 開啟中的檢視隨狀態刷新(實例消失則自動關閉)
}

// log 抽屜頁籤(窄螢幕):點擊展開/收合;收合時由 CSS 只顯示最新 4 條
function updateLogTab() {
  document.getElementById("log-title").textContent = t("ui.log");
}
document.getElementById("log-title").onclick = () => {
  if (!isNarrow()) return;
  const panel = document.getElementById("log-panel");
  panel.classList.toggle("open");
  if (panel.classList.contains("open")) {
    const holder = document.getElementById("log");
    holder.scrollTop = holder.scrollHeight;
  }
  updateLogTab();
};

// ---------------------------------------------------------------- 金手指(本機測試模式與 NPC 對戰)

let CHEAT = null;
let cheatGeneration = 0;

function canCheat() { return (isLocal() || isNpc()) && ["all", 0, 1].includes(myViewer()); }
function cheatCurrent(editor) { return CHEAT === editor && SESSION === editor.session && canCheat(); }
function cheatEditable() { return CHEAT && CHEAT.players && !CHEAT.busy && cheatCurrent(CHEAT); }

function showCheatError(msg) {
  const el = document.getElementById("cheat-error");
  el.textContent = msg;
  el.classList.toggle("hidden", !msg);
}

function closeCheat() {
  CHEAT = null;
  const panel = document.getElementById("cheat-panel");
  if (panel.open) panel.close();
}

function openCheat() {
  if (!canCheat() || CHEAT) return;
  CHEAT = { session: SESSION, generation: ++cheatGeneration, players: null,
    active: 0, selected: [null, null], ftype: "", fmamodo: "", fproduct: "", busy: false, applied: false };
  showCheatError("");
  document.getElementById("cheat-panel").showModal();
  renderCheatFields();
  cheatRefresh();
}

function renderCheatFields() {
  const editor = CHEAT;
  if (!editor) return;
  const holder = document.getElementById("cheat-players");
  holder.replaceChildren();
  for (let i = 0; i < 2; i++) {
    const button = document.createElement("button");
    button.textContent = pname(i);
    button.setAttribute("aria-pressed", String(editor.active === i));
    button.onclick = () => {
      if (!cheatEditable()) return;
      editor.active = i;
      renderCheatFields();
    };
    holder.appendChild(button);
  }
  const mp = document.getElementById("cheat-mp");
  document.getElementById("cheat-mp-label").textContent = t("ui.cheat.mp_label", { player: pname(editor.active) });
  mp.value = editor.players ? editor.players[editor.active].mp : "";
  mp.oninput = () => {
    if (cheatEditable()) {
      editor.players[editor.active].mp = mp.value;
      cheatMutated();
    }
  };
  renderCardPoolFilters(document.getElementById("cheat-filters"), editor, renderCheatPool);
  renderCheatPool();
  renderCheatBook();
  setCheatBusy(editor.busy);
}

function renderCheatPool() {
  if (!CHEAT) return;
  renderCardPool(document.getElementById("cheat-pool-grid"), CHEAT, (num) => {
    if (!cheatEditable()) return;
    const i = CHEAT.selected[CHEAT.active];
    if (i === null) { showCheatError(t("ui.cheat.select_page")); return; }
    CHEAT.players[CHEAT.active].book[i] = num;
    cheatMutated();
    renderCheatBook();
  });
}

function renderCheatBook() {
  const editor = CHEAT;
  const grid = document.getElementById("cheat-book-grid");
  const selected = editor.selected[editor.active];
  document.getElementById("cheat-selection").textContent = selected === null
    ? t("ui.cheat.select_page") : t("ui.cheat.selected_page", { n: selected + 1 });
  if (!editor.players) { grid.replaceChildren(); return; }
  const player = editor.active;
  const pages = editor.players[player].book;
  renderBookGrid(grid, (i) => bookPageSlotEl(i, pages, selected, {
    scope: `cheat-${editor.generation}-${player}`,
    enabled: () => cheatEditable() && CHEAT === editor && editor.active === player,
    select: (index) => {
      editor.selected[player] = editor.selected[player] === index ? null : index;
      showCheatError("");
      renderCheatBook();
    },
    swap: (from, to) => {
      [pages[from], pages[to]] = [pages[to], pages[from]];
      editor.selected[player] = null;
      cheatMutated();
      renderCheatBook();
    },
  }));
}

function cheatMutated() {
  CHEAT.applied = false;
  showCheatError("");
  document.getElementById("cheat-status").textContent = "";
}

function setCheatBusy(busy) {
  if (!CHEAT) return;
  CHEAT.busy = busy;
  const disabled = busy || !CHEAT.players;
  document.getElementById("cheat-editor").disabled = disabled;
  document.getElementById("cheat-editor").inert = disabled;
  document.getElementById("cheat-apply").disabled = disabled;
  document.getElementById("cheat-refresh").disabled = busy;
  document.getElementById("cheat-status").textContent = busy ? t("ui.cheat.loading")
    : CHEAT.applied ? t("ui.cheat.applied") : "";
}

async function cheatRefresh() {
  const editor = CHEAT;
  if (!editor || editor.busy || !cheatCurrent(editor)) return;
  editor.applied = false;
  setCheatBusy(true);
  showCheatError("");
  try {
    const data = await api(`/api/rooms/${editor.session.code}/debug-state`, {
      headers: { "X-Player-Token": Object.values(editor.session.tokens)[0] },
    });
    if (!cheatCurrent(editor)) return;
    editor.players = data.players.map((p) => ({ book: [...p.book], mp: p.mp }));
    editor.selected = [null, null];
    renderCheatFields();
  } catch (err) {
    if (cheatCurrent(editor)) showCheatError(err.message);
  } finally {
    if (cheatCurrent(editor)) setCheatBusy(false);
  }
}

async function cheatApply() {
  if (!cheatEditable()) return;
  const editor = CHEAT;
  for (let i = 0; i < 2; i++) {
    const book = editor.players[i].book;
    if (!Array.isArray(book) || book.length !== BOOK_SIZE || book.some((num) => !CARDS[num])) {
      showCheatError(t("ui.cheat.bad_book", { player: pname(i) }));
      return;
    }
  }
  const players = editor.players.map((p) => ({ book: [...p.book], mp: parseInt(p.mp, 10) || 0 }));
  const headers = { "X-Player-Token": Object.values(editor.session.tokens)[0] };
  const base = `/api/rooms/${editor.session.code}`;
  editor.applied = false;
  setCheatBusy(true);
  showCheatError("");
  try {
    const data = await api(`${base}/debug-state`, {
      method: "POST", headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ players }),
    });
    if (cheatCurrent(editor)) {
      editor.players = data.players.map((p) => ({ book: [...p.book], mp: p.mp }));
      editor.applied = true;
      renderCheatFields();
    }
    // 本機模式沒有持續 WS，明確讀回盤面及事件；關閉編輯器也仍同步同一房間。
    if (SESSION !== editor.session) return;
    try {
      const [state, events] = await Promise.all([
        api(`${base}/state`, { headers }),
        api(`${base}/events?since=${logSeq}`, { headers }),
      ]);
      if (SESSION === editor.session) applyPayload({ ...state, events: events.events });
    } catch (err) {
      if (cheatCurrent(editor)) showCheatError(t("ui.cheat.sync_failed", { msg: err.message }));
    }
  } catch (err) {
    if (cheatCurrent(editor)) showCheatError(err.message);
  } finally {
    if (cheatCurrent(editor)) setCheatBusy(false);
  }
}

document.getElementById("cheat-toggle").onclick = openCheat;
document.getElementById("cheat-refresh").onclick = cheatRefresh;
document.getElementById("cheat-apply").onclick = cheatApply;
document.getElementById("cheat-cancel").onclick = closeCheat;
document.getElementById("cheat-close").onclick = closeCheat;
document.getElementById("cheat-panel").addEventListener("cancel", (ev) => {
  ev.preventDefault();
  closeCheat();
});

function renderTopbar() {
  document.getElementById("title").setAttribute("aria-label", t("app.title"));
  updateLogTab();
  const leave = document.getElementById("leave-room");
  leave.textContent = t("ui.leave");
  leave.classList.toggle("hidden", !SESSION);
  document.getElementById("rules-toggle").textContent = t("ui.rules.toggle");
  document.getElementById("feedback-toggle").textContent = t("ui.feedback.toggle");
  const current = LANGS.find((l) => l.code === LANG);
  document.getElementById("lang-toggle").textContent = `🌐 ${current ? current.name : LANG}`;
  document.getElementById("lang-toggle").title = t("ui.lang.title");
  const prefsToggle = document.getElementById("prefs-toggle");
  prefsToggle.textContent = t("ui.prefs.toggle");
  const effectsToggle = document.getElementById("effects-toggle");
  effectsToggle.classList.toggle("hidden", !(SESSION && S));
  effectsToggle.textContent = t("ui.effects.toggle", { n: S && S.effects ? S.effects.length : 0 });
  if (INFO && INFO.kind === "effects") renderEffectsInfo();   // 開啟中的清單隨狀態刷新
  const cheatToggle = document.getElementById("cheat-toggle");
  cheatToggle.textContent = t("ui.cheat.toggle");
  cheatToggle.classList.toggle("hidden", !canCheat());
  if (CHEAT && !cheatCurrent(CHEAT)) closeCheat();
  for (const key of ["cancel", "close", "help", "pool_title", "book_title"]) {
    document.getElementById("cheat-" + key.replace("_", "-")).textContent = t("ui.cheat." + key);
  }
  document.getElementById("cheat-title").textContent = t("ui.cheat.title");
  document.getElementById("cheat-refresh").textContent = t("ui.cheat.refresh");
  document.getElementById("cheat-apply").textContent = t("ui.cheat.apply");
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
    t("ui.turn", { n: S.turn_no }) + t("ui.sep.bar") + pname(S.turn_player);
  document.getElementById("phase-info").textContent =
    t(`ui.phase.${S.phase === "game_over" ? "game_over" : S.phase}`);

  const acting = document.getElementById("acting-info");
  if (S.phase === "game_over") {
    acting.textContent = t("ui.winner", { player: pname(S.winner) }) +
      t("ui.paren", { text: t(`ui.reason.${S.end_reason}`) }) +
      (R && R.npc && R.npc.deck ? t("ui.sep.bar") + t("ui.npc.deck_reveal", { deck: npcDeckName(R.npc.deck) }) : "");
  } else if (S.pending) {
    const results = (S.pending.info && S.pending.info.results) || [];
    acting.textContent = (iControl(S.pending.player)
      ? t("ui.waiting_choice", { player: pname(S.pending.player) })
      : t("ui.opponent_choosing")) + (results.length ? t("ui.sep.bar") + coinResultsText(results) : "");
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

/* 鏡像牌桌:上方(對手)由上而下=魔書→搭檔→魔物;下方(我方)=魔物→搭檔→魔書。
 * 搭檔槽固定在該魔物的魔書側(對手在上、我方在下),由 mamodo-column 內的排列方向實現。 */
function renderPlayerZone(zone, p, isTop) {
  zone.innerHTML = "";
  zone.dataset.player = p;
  const ps = S.players[p];
  const active = awaitedPlayer() === p;               // 行動權:等待輸入的一方
  zone.classList.toggle("active", active);

  const head = document.createElement("div");
  head.className = "pz-head";
  const nameSpan = document.createElement("span");   // 暱稱以 textContent 呈現(防注入)
  nameSpan.className = "pname";
  nameSpan.textContent = pname(p) + (iControl(p) && myViewer() !== "all" ? t("ui.you_suffix") : "");
  head.appendChild(nameSpan);
  const badge = (cls, key) => {
    const el = document.createElement("span");
    el.className = cls;
    el.textContent = t(key);
    head.appendChild(el);
  };
  if (S.phase !== "game_over" && S.turn_player === p) badge("turn-marker", "ui.turn_marker");   // 整個回合都在
  if (active) badge("acting-label", "ui.acting_label");
  const rest = document.createElement("span");
  rest.className = "pz-head-rest";
  rest.innerHTML =
    `<span class="mp">${t("ui.mp")} ${ps.mp}</span>` +
    `<span class="book-progress">${t("ui.book")} ${t("ui.book_progress", { pos: ps.pos, size: ps.book_size })}</span>` +
    (ps.book ? `<span class="review-btn">${t("ui.review_book")}</span>` : "") +
    `<span class="discard-btn">${t("ui.discard", { n: ps.discard.length })}</span>`;
  rest.querySelector(".discard-btn").onclick = () => showDiscard(p);
  if (ps.book) rest.querySelector(".review-btn").onclick = () => showBookReview(p);
  head.appendChild(rest);
  zone.appendChild(head);

  // 場區(魔物列+搭檔列)置中;魔書區靠外角:對手右上、我方左下(對角相對)
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
      if (slot.injured) {                      // 虛線直框在下、橫卡在上,交叉成十字
        const frame = document.createElement("div");
        frame.className = "injured-frame";
        mamodoCell.appendChild(frame);
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

// ---------------------------------------------------------------- 場上魔書翻閱
// 玩家 → {start, pos}:start 為正在檢視的對頁起點(0 = 只有第 1 頁、32 = 只有第 32 頁),
// pos 為開始翻閱時的目前頁;沒有項目 = 在目前頁。只存在前端,重新整理後回到目前頁
const BOOK_BROWSE = {};

// 只有快照含持有者完整魔書的一方可翻閱(自己的魔書;本機模式雙方)
function bookBrowsable(p) { return !!(S && S.players[p] && S.players[p].book); }

// 正在檢視的對頁起點;在目前頁時 null。自己的魔書被翻動(目前頁改變)時自動回到目前頁
function browseStart(p) {
  const b = BOOK_BROWSE[p];
  if (b && b.pos !== S.players[p].pos) delete BOOK_BROWSE[p];
  return BOOK_BROWSE[p] ? BOOK_BROWSE[p].start : null;
}

// delta:+1 / -1 切換一個對頁;0 回到目前頁
function browseBook(p, delta) {
  if (!bookBrowsable(p)) return;
  const ps = S.players[p];
  if (delta === 0) {
    delete BOOK_BROWSE[p];
  } else {
    const cur = browseStart(p) ?? Math.min(ps.pos, 32);
    const start = Math.max(0, Math.min(32, cur + 2 * delta));
    if (start === ps.pos) delete BOOK_BROWSE[p];
    else BOOK_BROWSE[p] = { start, pos: ps.pos };
  }
  render();
}

// 鍵盤:← → 切換對頁、Home / Esc 回到目前頁。線上 / NPC 對戰控制自己的魔書,本機模式控制行動中的一方;
// 打字中或任何視窗開著時不處理(Esc 照舊由視窗處理)
const BOOK_KEYS = { ArrowLeft: -1, ArrowRight: 1, Home: 0, Escape: 0 };
const BLOCKING_OVERLAYS = ["zoom-overlay", "dialog-overlay", "info-overlay", "book-review-overlay",
  "rules-overlay", "io-overlay"];
document.addEventListener("keydown", (ev) => {
  if (!(ev.key in BOOK_KEYS) || ev.defaultPrevented || ev.ctrlKey || ev.altKey || ev.metaKey) return;
  const el = document.activeElement;
  if (el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))) return;
  if (!S || document.getElementById("layout").classList.contains("hidden")) return;
  if (BLOCKING_OVERLAYS.some((id) => !document.getElementById(id).classList.contains("hidden"))) return;
  if (document.getElementById("cheat-panel").open) return;
  const target = selfPlayer() ?? (isLocal() ? awaitedPlayer() : null);
  if (target === null || !bookBrowsable(target)) return;
  ev.preventDefault();
  browseBook(target, BOOK_KEYS[ev.key]);
});

// 翻閱中的頁:唯讀卡面(點擊只開純展示放大檢視);已離開魔書的頁為卡背
// 例外:待命允許從魔書任意頁使用的戰術頁(P-015)發光,放大檢視提供「攻擊」
function browsedPageEl(p, ps, pg) {
  if ((ps.consumed_pages || []).includes(pg)) return cardBackEl(pg, true);
  const usable = (ps.any_page_spells || []).some((e) => e.page === pg);
  const el = cardEl(ps.book[pg - 1], { zoomCtx: usable ? { kind: "any_page", p, page: pg } : undefined });
  if (usable) el.classList.add("pickable");
  el.dataset.card = ps.book[pg - 1];
  return el;
}

function bookNavButton(cls, label, text, disabled, onclick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `book-nav ${cls}`;
  btn.textContent = text;
  btn.title = label;
  btn.setAttribute("aria-label", label);
  btn.disabled = disabled;
  btn.onclick = (ev) => { ev.stopPropagation(); onclick(); };
  return btn;
}

// 魔書區:對頁兩個頁位(目前頁 pos, pos+1,或翻閱中的對頁)。卡片仍在=卡面(對手視角=卡背+頁碼);
// 卡片已離開頁面(上場/使用)=卡背圖;超出書末=空位,尺寸不變
function renderBookBlock(p, ps) {
  const block = document.createElement("div");
  block.className = "book-block";
  block.dataset.bookBlock = p;
  const cover = document.createElement("div");
  cover.className = "book-cover";
  cover.dataset.book = p;
  const spine = document.createElement("div");
  spine.className = "book-spine";
  const pages = document.createElement("div");
  pages.className = "book-pages";
  const byPage = Object.fromEntries(ps.open_pages.map((e) => [e.page, e]));
  const browse = bookBrowsable(p) ? browseStart(p) : null;
  const first = browse ?? ps.pos;
  for (const pg of [first, first + 1]) {
    const col = document.createElement("div");
    col.className = "page-col";
    let el;
    if (pg < 1 || pg > ps.book_size) {
      el = document.createElement("div");
      el.className = "page-void";
      col.appendChild(el);
    } else {
      if (browse !== null) {
        el = browsedPageEl(p, ps, pg);
      } else if (byPage[pg]) {
        const entry = byPage[pg];
        el = entry.card ? openPageEl(p, entry) : cardBackEl(entry.page);
        if (entry.card) el.dataset.card = entry.card;
      } else {
        el = cardBackEl(pg, true);  // 卡片已被拿出的頁位
      }
      el.dataset.page = pg;
      col.appendChild(el);
      const no = document.createElement("span");  // 頁碼印在書皮上、卡片之外
      no.className = "page-no";
      no.textContent = t("ui.hidden_page", { n: pg });
      col.appendChild(no);
    }
    pages.appendChild(col);
  }
  cover.appendChild(spine);
  cover.appendChild(pages);
  if (bookBrowsable(p)) {   // 左右鍵在書皮兩緣;「回到目前頁」在上緣,不在目前頁時變亮
    const at = browse ?? Math.min(ps.pos, 32);
    cover.classList.toggle("browsing", browse !== null);
    cover.appendChild(bookNavButton("book-prev", t("ui.book.prev"), "‹", at <= 0, () => browseBook(p, -1)));
    cover.appendChild(bookNavButton("book-next", t("ui.book.next"), "›", at >= 32, () => browseBook(p, 1)));
    cover.appendChild(bookNavButton("book-current", t("ui.book.current"), t("ui.book.current"),
      browse === null, () => browseBook(p, 0)));
  }
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

// 卡片實例的行動按鈕生成器:不再渲染於卡面,由放大檢視(zoom)依實例上下文即時取得
function slotButtons(p, slot) {
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
  // 無戰術攻擊(M-027 バルトロ〈裝甲〉):回合玩家、非戰鬥、非決策時可宣告
  if (slot.mamodo_attack && iControl(p) && p === S.turn_player && canActNow(p)) {
    const spec = slot.mamodo_attack;
    const blocked = S.players[p].mp < spec.mp_cost ? `MP < ${spec.mp_cost}` : null;
    buttons.push({
      label: t("ui.mamodo_attack", { power: spec.power, dam: spec.damage }),
      primary: true, disabled: !!blocked, reason: blocked,
      onclick: () => send({ type: "declare_attack", player: p, mode: "mamodo", slot_uid: slot.uid }),
    });
  }
  return buttons;
}

function slotEl(p, slot) {
  const ctx = { kind: "slot", p, uid: slot.uid };
  return markPickable(markUsable(cardEl(slot.top, {
    injured: slot.injured,
    power: slot.power,
    zoomCtx: ctx,
  }), ctx), ctx);
}

// 可用卡發光:可操作的一方的卡片,放大檢視中有任一啟用的行動按鈕(同一套判斷)
function markUsable(el, ctx) {
  if (iControl(ctx.p) && (zoomActions(ctx).buttons || []).some((b) => !b.disabled)) {
    el.classList.add("usable");
  }
  return el;
}

function partnerButtons(p, slot) {
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
  return buttons;
}

function partnerEl(p, slot) {
  const ctx = { kind: "partner", p, uid: slot.uid };
  return markPickable(markUsable(cardEl(slot.partner, { small: true, zoomCtx: ctx }), ctx), ctx);
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
  if (ab.own_turn && S.turn_player !== p) return { ok: false, reason: t("ui.ability.own_turn_only") };
  if (ab.mp_cost > S.players[p].mp) return { ok: false, reason: `MP < ${ab.mp_cost}` };
  return { ok: true };
}

// P-015:從魔書任意頁宣告攻擊(條件與翻開頁的攻擊按鈕相同,使用魔物的選擇也相同)
function anyPageButtons(p, entry) {
  if (!iControl(p) || p !== S.turn_player || S.battle || S.battle_in || !canActNow(p)) return [];
  const u = spellUsable(p, entry, true);
  return [{
    label: t("ui.attack"), primary: true, disabled: !u.ok, reason: u.reason,
    onclick: () => {
      closeBookReview();   // 網格在選擇視窗之上:先關閉,使用魔物的選擇才看得到
      pickSpellUser(p, entry,
        (uid) => send({ type: "declare_attack", player: p, page: entry.page, slot_uid: uid }));
    },
  }];
}

// E-010:玩家 p 本回合借用且尚未使用的搭檔效果(作用中效果中的 borrow_partner);沒有則 null
function borrowedEffect(p) {
  return (S.effects || []).find((e) => e.kind === "borrow_partner" && e.owner === p && !e.used) || null;
}

function borrowedButtons(p, borrow) {
  if (!iControl(p) || !borrow.ability) return [];
  const restricted = (S.effects || []).some((e) => e.kind === "restriction"
    && e.flag === "no_partner_effects" && e.target_player === p);
  let usable = abilityUsableNow(p, borrow.ability);
  if (!usable.ok && !usable.reason && !S.pending && S.phase === "battle") {
    usable = { ok: false, reason: t("error.ability.timing") };   // 時機不符(戰鬥中 / 非戰鬥)
  }
  if (usable.ok && restricted) usable = { ok: false, reason: t("error.ability.partner_restricted") };
  return [{
    label: t("ui.use_borrowed"), primary: true, disabled: !usable.ok, reason: usable.reason,
    onclick: () => send({ type: "use_borrowed_effect", player: p }),
  }];
}

function pageButtons(p, entry) {
  const def = CARDS[entry.card];
  const buttons = [];

  if (canActNow(p)) {
    if (def.type === "mamodo" || def.type === "partner") {
      // 搭檔卡:對應且未裝搭檔的魔物為裝備對象,兩隻以上時由玩家選(魔物卡可能疊放,前端不判斷場上是否已滿)
      const targets = def.type === "partner" ? partnerTargets(p, def) : null;
      const blocked = !targets ? null
        : !targets.matching.length ? t("ui.play.no_mamodo") : !targets.free.length ? t("ui.play.partner_exists") : null;
      buttons.push({
        label: t("ui.play"), primary: true, disabled: !!blocked, reason: blocked,
        onclick: () => (def.type === "partner"
          ? pickPartnerTarget(p, def, (uid) => send({ type: "play_card", player: p, page: entry.page, slot_uid: uid }))
          : send({ type: "play_card", player: p, page: entry.page })),
      });
    } else if (def.type === "event") {
      const ps = S.players[p];
      const blocked = ps.used_event_this_turn ? t("ui.used")
        : (def.cost || 0) > ps.mp ? `MP < ${def.cost}`
        : (def.ad === "A" && p !== S.turn_player) ? t("ui.spell.own_turn")
        : (def.ad === "D" && p === S.turn_player) ? t("ui.spell.other_turn") : null;
      buttons.push({
        label: t("ui.use_event"), primary: true, disabled: !!blocked, reason: blocked,
        onclick: () => send({ type: "use_book_card", player: p, page: entry.page }),
      });
    }
    if (def.type === "spell" && def.effect_icon === "nonbattle" && inNonBattle()) {
      const u = nonbattleSpellUsable(p, entry);
      buttons.push({
        label: t("ui.use_event"), primary: true, disabled: !u.ok, reason: u.reason,
        onclick: () => pickSpellUser(p, entry,
          (uid) => send({ type: "use_book_card", player: p, page: entry.page, slot_uid: uid })),
      });
    }
    if (def.type === "spell" && def.effect_icon !== "nonbattle" && p === S.turn_player && !S.battle_in) {
      const u = spellUsable(p, entry, true);
      if (["A", "AD"].includes(def.ad)) {
        buttons.push({
          label: t("ui.attack"), primary: true, disabled: !u.ok, reason: u.reason,
          onclick: () => pickSpellUser(p, entry,
            (uid) => send({ type: "declare_attack", player: p, page: entry.page, slot_uid: uid })),
        });
      }
    }
  }

  if (!S.pending && S.battle && S.battle.step === "defense"
      && p === 1 - S.battle.attacker && iControl(p)) {
    const u = spellUsable(p, entry, false);
    if (["D", "AD"].includes(def.ad) && def.type === "spell" && def.effect_icon !== "nonbattle") {
      const blocked = S.battle.attack_undefendable ? t("ui.undefendable") : (u.ok ? null : u.reason);
      buttons.push({
        label: t("ui.defend"), primary: true,
        disabled: S.battle.attack_undefendable || !u.ok, reason: blocked,
        onclick: () => pickSpellUser(p, entry,
          (uid) => send({ type: "declare_defense", player: p, page: entry.page, slot_uid: uid })),
      });
    }
  }

  return buttons;
}

function openPageEl(p, entry) {
  const ctx = { kind: "page", p, page: entry.page };
  const el = markPickable(markUsable(cardEl(entry.card, { cost: entry.cost, zoomCtx: ctx }), ctx), ctx);
  if (entry.in_use) el.classList.add("in-use");  // 宣告中的攻防戰術:發光標示
  return el;
}

// 以攻擊魔物槽 uid 取其卡名(無戰術攻擊顯示用)
function attackerName(player, slotUid) {
  const slot = S.players[player].slots.find((s) => s.uid === slotUid);
  return slot ? cname(slot.top) : "";
}

// 對決舞台:非戰鬥時收為發光細線,battle_in/battle 時展開承載攻防資訊與合計魔力
// 時機指示(中線):開始 › 戰鬥階段〔非戰鬥中 ⇄ 戰鬥中:開始確認 → 防禦 → 效果〕 › 結束
const IN_BATTLE_STEPS = ["battle_in", "defense", "effects"];

function renderTimingTrack() {
  const track = document.getElementById("timing-track");
  const timing = currentTiming();
  track.replaceChildren();
  track.classList.toggle("hidden", timing === "over");
  if (timing === "over") return;
  const span = (cls, text) => {
    const el = document.createElement("span");
    el.className = cls;
    el.textContent = text;
    return el;
  };
  const step = (key) => {
    const el = span("step" + (key === timing ? " current" : ""), t(`track.${key}`));
    el.dataset.step = key;
    el.onclick = () => openRules(RULE_LINKS[`timing.${key}`]);   // 連到規則頁的說明
    return el;
  };
  // 窄螢幕只顯示當下所在的一層:不在戰鬥中收起戰鬥中的子步驟,在戰鬥中收起外層(開始、戰鬥階段、結束)
  const battling = IN_BATTLE_STEPS.includes(timing);
  track.classList.toggle("in-battle", battling);
  const inBattle = span("seg-battle" + (battling ? "" : " collapsed"), "");
  inBattle.appendChild(span("seg-label", t("track.in_battle")));
  IN_BATTLE_STEPS.forEach((key, i) => {
    if (i) inBattle.appendChild(span("sep", "→"));
    inBattle.appendChild(step(key));
  });
  const phase = span("seg-phase", "");
  phase.append(span("seg-label", t("track.battle")), span("sep outer", "〔"), step("nonbattle"),
    span("sep", "⇄"), inBattle, span("sep outer", "〕"));
  track.append(step("start"), span("sep", "›"), phase, span("sep", "›"), step("end"));
}

function renderBattleStage() {
  const stage = document.getElementById("battle-stage");
  const content = document.getElementById("stage-content");
  content.innerHTML = "";
  const open = !!(S.battle || S.battle_in);
  stage.classList.toggle("open", open);
  if (!open) return;
  // 標籤一律 DOM 建構(textContent + 卡名包可點 span):暱稱不進 innerHTML
  const mkLabel = (cls, text, nums) => {
    const span = document.createElement("span");
    span.className = cls;
    span.textContent = text;
    linkCardNames(span, nums || []);
    return span;
  };
  if (S.battle_in) {
    const bi = S.battle_in;
    const label = bi.spell
      ? t("ui.battle_in_hint", { player: pname(bi.attacker), spell: cname(bi.spell) })
      : t("ui.battle_in_hint_mamodo", { player: pname(bi.attacker),
          mamodo: attackerName(bi.attacker, bi.slot) });
    content.appendChild(mkLabel("stage-hint", label, bi.spell ? [bi.spell] : []));
    return;
  }
  const b = S.battle;
  // 無戰術攻擊:攻方以魔物名代替戰術名呈現
  const attackLabel = b.attack_spell
    ? t("ui.battle_attack", { player: pname(b.attacker), spell: cname(b.attack_spell) })
    : t("ui.battle_attack_mamodo", { player: pname(b.attacker),
        mamodo: attackerName(b.attacker, b.attack_slot) });
  const att = document.createElement("div");
  att.className = "stage-side attack";
  att.appendChild(mkLabel("side-label",
    attackLabel +
    (b.attack_negated ? `(${t("ui.negated")})` : "") +
    (b.attack_undefendable ? `(${t("ui.undefendable")})` : ""),
    b.attack_spell ? [b.attack_spell] : []));
  const attTotal = document.createElement("span");
  attTotal.className = "side-total";
  attTotal.id = "stage-att-total";
  attTotal.textContent = b.attacker_total;
  attTotal.onclick = () => showBreakdown({ ...b, live: true });
  att.appendChild(attTotal);
  const mid = document.createElement("div");
  mid.className = "stage-vs";
  mid.textContent = t("ui.battle");
  const def = document.createElement("div");
  def.className = "stage-side defense";
  def.appendChild(b.defense_spell
    ? mkLabel("side-label",
        t("ui.battle_defense", { player: pname(1 - b.attacker), spell: cname(b.defense_spell) }) +
        (b.defense_negated ? `(${t("ui.negated")})` : ""),
        [b.defense_spell])
    : mkLabel("side-label", t("ui.battle_no_defense_yet")));
  const defTotal = document.createElement("span");
  defTotal.className = "side-total";
  defTotal.id = "stage-def-total";
  defTotal.textContent = b.defender_total;
  defTotal.onclick = () => showBreakdown({ ...b, live: true });
  def.appendChild(defTotal);
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

// 行動欄摘要:輪到誰、誰的回合、目前的時機。可操作的一方以「你」稱呼(本機與觀戰以名稱)
function actionSummary(awaited, timing) {
  const me = selfPlayer();
  const turn = me === null ? t("ui.turn_of.named", { player: pname(S.turn_player) })
    : t(S.turn_player === me ? "ui.turn_of.mine" : "ui.turn_of.opp");
  const params = { turn, timing: t(`timing.${timing}`), player: pname(awaited) };
  if (me !== null && awaited === me) return t("ui.summary.mine", params);
  if (me !== null) return t("ui.summary.wait", params);
  return t("ui.summary.named", params);
}

// 詳細提示:依時機與是否回合玩家,對應規則書「戰鬥階段可做的事」
function actionHints(awaited, timing) {
  if (S.pending && timing !== "end") return ["hint.pending"];
  if (timing === "nonbattle") return awaited === S.turn_player ? HINTS.nonbattle_turn : HINTS.nonbattle_other;
  return HINTS[timing] || [];
}
const HINTS = {
  start: ["hint.start"],
  nonbattle_turn: ["hint.play", "hint.field_effect", "hint.own_turn_cards", "hint.attack", "hint.pass_end"],
  nonbattle_other: ["hint.play", "hint.field_effect", "hint.opp_turn_cards", "hint.pass_end"],
  battle_in: ["hint.allow_battle", "hint.insert_action"],
  defense: ["hint.defend", "hint.no_defense"],
  effects: ["hint.battle_effects", "hint.pass_showdown"],
  end: ["hint.deploy"],
};

function hintsShown() {
  try { return localStorage.getItem("gash-action-hints") === "shown"; } catch (_) { return false; }
}

function renderActionBar() {
  const bar = document.getElementById("action-bar");
  bar.innerHTML = "";
  bar.classList.remove("mine");
  if (!S || S.phase === "game_over") return;
  const timing = currentTiming();
  const awaited = awaitedPlayer();
  const mine = awaited !== null && iControl(awaited);
  bar.classList.toggle("mine", mine);                // 輪到自己:行動欄醒目

  const summary = document.createElement("span");
  summary.className = "summary";
  summary.textContent = actionSummary(awaited, timing);
  bar.appendChild(summary);
  let details = null;
  if (mine && PICK) {                                  // 決策:行動欄顯示決策區塊,目標在原位置選
    bar.appendChild(PICK.local ? localPromptEl() : choicePromptEl());
    return;
  }
  if (mine) {                                          // 詳細提示只對可操作的一方
    const toggle = document.createElement("button");
    toggle.className = "hint-toggle";
    toggle.textContent = t(hintsShown() ? "ui.hints.hide" : "ui.hints.show");
    toggle.onclick = () => {
      try { localStorage.setItem("gash-action-hints", hintsShown() ? "hidden" : "shown"); } catch (_) { /* 本次不記 */ }
      renderActionBar();
    };
    bar.appendChild(toggle);
    if (hintsShown()) {
      details = document.createElement("ul");
      details.className = "hint-details";
      for (const key of actionHints(awaited, timing)) {
        const li = document.createElement("li");
        li.textContent = t(key);
        if (RULE_LINKS[key]) {                         // 連到規則頁的對應段落
          const link = document.createElement("button");
          link.className = "rule-link";
          link.textContent = "?";
          link.title = t("ui.rules.link");
          link.onclick = () => openRules(RULE_LINKS[key]);
          li.appendChild(link);
        }
        details.appendChild(li);
      }
    }
  }
  const addBtn = (label, onclick, primary) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (primary) btn.classList.add("primary");
    btn.onclick = onclick;
    bar.appendChild(btn);
  };

  if (mine && !S.pending) {
    if (timing === "start") {
      const tp = S.turn_player;
      const maxFlip = Math.min(3, Math.floor((32 - S.players[tp].pos) / 2));
      for (let n = 0; n <= maxFlip; n++) {
        addBtn(n === 0 ? t("ui.flip_0") : t("ui.flip_n", { n, mp: 2 * n }),
          () => send({ type: "flip_pages", player: tp, count: n }), n === maxFlip);
      }
    } else if (timing === "battle_in") {
      addBtn(t("ui.allow_battle"),
        () => send({ type: "battle_in_response", player: awaited, allow: true }), true);
    } else if (timing === "defense") {
      addBtn(t("ui.no_defense"), () => send({ type: "no_defense", player: awaited }));
    } else {
      addBtn(t("ui.pass"), () => send({ type: "pass", player: awaited }));
      const borrow = borrowedEffect(awaited);        // E-010:借來的搭檔效果(該搭檔離場也在)
      if (borrow) {
        addBtn(t("ui.borrowed_effect", { card: cname(borrow.card) }),
          () => zoom(borrow.card, { kind: "borrowed", p: awaited }));
      }
      // P-015:待命允許從魔書任意頁使用的戰術,在可宣告攻擊時從魔書網格使用
      const anyPage = S.players[awaited].any_page_spells || [];
      if (anyPage.length && awaited === S.turn_player && !S.battle && !S.battle_in) {
        addBtn(t("ui.any_page_spell", { card: cname(anyPage[0].card) }), () => showBookReview(awaited));
      }
    }
  }
  if (details) bar.appendChild(details);
}

// ---------------------------------------------------------------- 決策對話框

function showDialog(title, options, sourceNum = null, notes = []) {
  const overlay = document.getElementById("dialog-overlay");
  document.getElementById("dialog-title").textContent = title;
  const notesEl = document.getElementById("dialog-notes");   // 決策的公開脈絡(如目前擲幣結果)
  notesEl.replaceChildren(...notes.map((text) => {
    const line = document.createElement("div");
    line.textContent = text;
    return line;
  }));
  notesEl.classList.toggle("hidden", !notes.length);
  // 來源卡:通用標題之外,以來源卡的名稱與效果文提供脈絡(效果文為中譯,只供閱讀)
  const source = document.getElementById("dialog-source");
  source.innerHTML = "";
  const z = sourceNum ? TEXT[sourceNum] : null;
  if (z) {
    const name = document.createElement("div");
    name.className = "src-name";
    name.textContent = t("ui.choice_source", { card: cname(sourceNum) });
    const effect = document.createElement("div");
    effect.className = "src-effect";
    effect.textContent = z.effect || "";
    source.append(name, effect);
  }
  source.classList.toggle("hidden", !z);
  const holder = document.getElementById("dialog-options");
  holder.innerHTML = "";
  for (const opt of options) {
    if (opt.cardNum) {
      const el = cardEl(opt.cardNum, { small: true });
      if (opt.pickable) el.classList.add("pickable");
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

// ---------------------------------------------------------------- 決策:在原位置選擇

// 目前決策的選項(只對決策者):目標依選項的 zone 對應到畫面位置,其餘為按鈕或直接列出的卡
//   slot:    "玩家:uid:mamodo|partner" → value       book: "玩家:頁碼" → {value, card}
//   discard: "玩家:索引" → value                     buttons / cards:提示區的按鈕與退回列出的卡
let PICK = null;

// 前端的場上選擇(使用戰術的魔物、搭檔的裝備對象):候選在場上發光,點開放大檢視按「選擇」。
// {player, title, source, options: Map(slot uid → {selectable, note, reason}), onpick};收到新快照時清除
let LOCAL_PICK = null;

function startLocalPick(pick) {
  closeZoom();
  LOCAL_PICK = pick;
  render();
}

function cancelLocalPick() {
  LOCAL_PICK = null;
  render();
}

function pickState() {
  if (S && !S.pending && LOCAL_PICK) {
    const pick = { player: LOCAL_PICK.player, slot: new Map(), book: new Map(), discard: new Map(),
                   buttons: [], cards: [], books: new Set(), discards: new Set(), local: true };
    for (const [uid, opt] of LOCAL_PICK.options) {
      if (opt.selectable) pick.slot.set(`${LOCAL_PICK.player}:${uid}:mamodo`, uid);
    }
    return pick;
  }
  if (!S || !S.pending || !S.pending.options || !iControl(S.pending.player)) return null;
  const pd = S.pending;
  const results = (pd.info && pd.info.results) || [];
  const pick = { player: pd.player, slot: new Map(), book: new Map(), discard: new Map(),
                 buttons: [], cards: [], books: new Set(), discards: new Set() };
  for (const opt of pd.options) {
    const value = opt.index !== undefined ? opt.index : opt.value !== undefined ? opt.value : opt.page;
    const label = choiceLabel(opt, results);
    if (label !== null) { pick.buttons.push({ label, value }); continue; }
    if (opt.zone === "slot") {
      const slot = S.players[opt.player]?.slots.find((x) => x.uid === opt.slot);
      const part = slot && opt.card && opt.card === slot.partner && opt.card !== slot.top ? "partner" : "mamodo";
      if (slot) { pick.slot.set(`${opt.player}:${opt.slot}:${part}`, value); continue; }
    } else if (opt.zone === "book") {
      pick.book.set(`${opt.player}:${opt.page}`, { value, card: opt.card });
      pick.books.add(opt.player);
      continue;
    } else if (opt.zone === "discard") {
      pick.discard.set(`${opt.player}:${opt.index}`, value);
      pick.discards.add(opt.player);
      continue;
    }
    if (opt.card) pick.cards.push({ card: opt.card, value });            // 對應不到位置:直接列出
    else if (opt.page !== undefined) pick.buttons.push({ label: t("ui.page_n", { n: opt.page }), value });
    else pick.buttons.push({ label: String(value), value });
  }
  return pick;
}

// 純選項的按鈕文字;不是純選項時回傳 null
function choiceLabel(opt, results) {
  switch (opt.label) {
    case "no_protect": return t("choice.no_protect");
    case "keep": return t("choice.keep");
    case "reflip": {
      const face = results[opt.value] ? t(`ui.coin_face.${results[opt.value]}`) : "";
      return t("choice.reflip", { n: opt.value + 1, face });
    }
    case "pay_reflip": return t("choice.pay_reflip");
    case "stop": return t("choice.stop");
    case "skip": return t("choice.skip");
    case "jammer_use": return t("choice.jammer_use", { card: cname(opt.card) });
    case "spell_discount_use": return t("choice.spell_discount_use");
    case "s043_fuse": return t("choice.s043_fuse");
    case "s043_split": return t("choice.s043_split");
    case "heal_injured": return t("choice.heal_injured");
    case "gain_mp_2": return t("choice.gain_mp_2");
  }
  if (opt.item && opt.item.kind === "book") return pname(opt.item.player) + t("ui.book");   // 受傷順序的魔書項
  return null;
}

function choosePick(value) {
  if (BOOK_VIEW !== null) closeBookReview();   // 從魔書網格選完就關閉,回到場面
  if (PICK && PICK.local) {                    // 前端的場上選擇:交給發起者,不送 choose
    const onpick = LOCAL_PICK.onpick;
    LOCAL_PICK = null;
    render();
    onpick(value);
    return;
  }
  send({ type: "choose", player: PICK.player, value });
}

// 實例是否為可選目標:回傳選項值,不是時 undefined
function pickValue(ctx) {
  if (!PICK || !ctx) return undefined;
  if (ctx.kind === "slot") return PICK.slot.get(`${ctx.p}:${ctx.uid}:mamodo`);
  if (ctx.kind === "partner") return PICK.slot.get(`${ctx.p}:${ctx.uid}:partner`);
  if (ctx.kind === "page" || (ctx.kind === "pick" && ctx.zone === "book")) return PICK.book.get(`${ctx.p}:${ctx.page}`)?.value;
  if (ctx.kind === "pick" && ctx.zone === "discard") return PICK.discard.get(`${ctx.p}:${ctx.index}`);
  return undefined;
}

function markPickable(el, ctx) {
  if (pickValue(ctx) !== undefined) el.classList.add("pickable");
  return el;
}

// 放大檢視的「選擇」按鈕
function pickButtons(ctx) {
  if (PICK && PICK.local) {                    // 前端的場上選擇:附費用;不可選者停用並顯示原因
    const opt = ctx && ctx.kind === "slot" && ctx.p === PICK.player ? LOCAL_PICK.options.get(ctx.uid) : null;
    if (!opt) return [];
    const label = opt.note ? `${t("ui.pick")}(${opt.note})` : t("ui.pick");
    return [{ label, primary: true, disabled: !opt.selectable, reason: opt.reason, onclick: () => choosePick(ctx.uid) }];
  }
  const value = pickValue(ctx);
  if (value === undefined) return [];
  return [{ label: t("ui.pick"), primary: true, onclick: () => choosePick(value) }];
}

// 前端場上選擇的提示:標題、來源卡、「在場上選擇」提示與「取消」
function localPromptEl() {
  const box = document.createElement("div");
  box.className = "choice-prompt";
  const title = document.createElement("div");
  title.className = "choice-title";
  title.textContent = LOCAL_PICK.title;
  box.appendChild(title);
  const z = LOCAL_PICK.source ? TEXT[LOCAL_PICK.source] : null;
  if (z) {
    const source = document.createElement("div");
    source.className = "choice-source";
    const name = document.createElement("div");
    name.className = "src-name";
    name.textContent = t("ui.choice_source", { card: cname(LOCAL_PICK.source) });
    source.appendChild(name);
    box.appendChild(source);
  }
  const hint = document.createElement("div");
  hint.className = "choice-hint";
  hint.textContent = t("ui.pick_hint.slot");
  box.appendChild(hint);
  const opts = document.createElement("div");
  opts.className = "choice-options";
  const cancel = document.createElement("button");
  cancel.textContent = t("ui.cancel");
  cancel.onclick = cancelLocalPick;
  opts.appendChild(cancel);
  box.appendChild(opts);
  return box;
}

// 行動欄的決策區塊:標題、來源卡、公開脈絡、提示、按鈕;對應不到位置的卡直接列出
function choicePromptEl() {
  const pd = S.pending;
  const box = document.createElement("div");
  box.className = "choice-prompt";
  const titleKey = `choice.title.${pd.kind}`;
  const title = document.createElement("div");
  title.className = "choice-title";
  title.textContent = t("ui.choice_title", { player: pname(pd.player), title: DICT[titleKey] ? t(titleKey) : pd.kind });
  box.appendChild(title);
  const z = pd.source ? TEXT[pd.source] : null;
  if (z) {                     // 來源卡:名稱與效果文(效果文為譯文,只供閱讀)
    const source = document.createElement("div");
    source.className = "choice-source";
    const name = document.createElement("div");
    name.className = "src-name";
    name.textContent = t("ui.choice_source", { card: cname(pd.source) });
    const effect = document.createElement("div");
    effect.className = "src-effect";
    effect.textContent = z.effect || "";
    source.append(name, effect);
    box.appendChild(source);
  }
  const results = (pd.info && pd.info.results) || [];
  if (results.length) {
    const notes = document.createElement("div");
    notes.className = "choice-notes";
    notes.textContent = coinResultsText(results);
    box.appendChild(notes);
  }
  const hints = [];
  if (PICK.slot.size) hints.push(t("ui.pick_hint.slot"));
  if (PICK.books.size) hints.push(t("ui.pick_hint.book"));
  if (PICK.discards.size) hints.push(t("ui.pick_hint.discard"));
  if (hints.length) {
    const hint = document.createElement("div");
    hint.className = "choice-hint";
    hint.textContent = hints.join(t("ui.sep.list"));
    box.appendChild(hint);
  }
  const row = document.createElement("div");
  row.className = "choice-options";
  const addBtn = (label, onclick, primary) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (primary) btn.classList.add("primary");
    btn.onclick = onclick;
    row.appendChild(btn);
  };
  for (const q of PICK.books) {
    addBtn(PICK.books.size > 1 || q !== PICK.player ? t("ui.pick_open_book_of", { player: pname(q) }) : t("ui.pick_open_book"),
      () => showBookReview(q), true);
  }
  for (const q of PICK.discards) {
    addBtn(PICK.discards.size > 1 || q !== PICK.player ? t("ui.pick_open_discard_of", { player: pname(q) }) : t("ui.pick_open_discard"),
      () => showDiscard(q), true);
  }
  for (const b of PICK.buttons) addBtn(b.label, () => choosePick(b.value));
  box.appendChild(row);
  if (PICK.cards.length) {
    const cards = document.createElement("div");
    cards.className = "choice-cards";
    for (const c of PICK.cards) {
      const el = cardEl(c.card, { small: true });
      el.onclick = () => choosePick(c.value);
      cards.appendChild(el);
    }
    box.appendChild(cards);
  }
  return box;
}

// 目前擲幣結果:「第 1 枚:正面、第 2 枚:反面」
function coinResultsText(results) {
  return t("ui.coin_results", { list: results.map((r, i) =>
    t("ui.coin_n", { n: i + 1, face: t(`ui.coin_face.${r}`) })).join(t("ui.sep.list")) });
}

// ---------------------------------------------------------------- 純展示資訊(魔力明細、作用中效果)

let INFO = null;   // 開啟中的資訊對話框 {kind}

// ---------------------------------------------------------------- 更新內容
// 進入首頁時,最新一版還沒按過「確認」就跳出該版;確認才記在 gash-release-seen,同一次載入只跳一次
const RELEASE_SEEN_KEY = "gash-release-seen";
let releasePopped = false;

function releaseBlock(r) {
  const sec = document.createElement("div");
  sec.className = "info-section release";
  const h = document.createElement("h4");
  const ver = document.createElement("span");
  ver.textContent = r.version + (r.title ? ` ${r.title}` : "");
  const date = document.createElement("span");
  date.className = "release-date";
  date.textContent = r.date;
  h.append(ver, date);
  sec.appendChild(h);
  if (r.items.length) {
    const ul = document.createElement("ul");
    for (const item of r.items) {
      const li = document.createElement("li");
      li.textContent = t("release.item", { kind: t(`release.kind.${item.kind}`), text: item.text });
      ul.appendChild(li);
    }
    sec.appendChild(ul);
  }
  return sec;
}

function maybeShowRelease() {
  if (!RELEASES || releasePopped) return;
  const latest = RELEASES[0];
  let seen = null;
  try { seen = localStorage.getItem(RELEASE_SEEN_KEY); } catch (_) { /* 無法存取:視為未確認 */ }
  if (seen === latest.version) return;
  releasePopped = true;
  showInfo("release-latest", t("ui.release.latest", { version: latest.version }), [releaseBlock(latest)]);
  const confirm = document.getElementById("info-close");
  confirm.textContent = t("ui.release.confirm");
  confirm.onclick = () => {
    try { localStorage.setItem(RELEASE_SEEN_KEY, latest.version); } catch (_) { /* 本次載入不再跳出 */ }
    closeInfo();
  };
}

function showReleaseHistory() {
  showInfo("release-history", t("ui.release.title"), RELEASES.map(releaseBlock));
}

function showInfo(kind, title, body) {
  INFO = { kind };
  document.getElementById("info-title").textContent = title;
  const close = document.getElementById("info-close");
  close.textContent = t("ui.close");
  close.onclick = closeInfo;
  document.getElementById("info-body").replaceChildren(...body);
  document.getElementById("info-overlay").classList.remove("hidden");
}

// 檢視對手翻開的頁:依頁碼列出卡片(可點開放大檢視),按「確定」關閉;不是決策,對局照常
function showPeek(peeks) {
  const body = peeks.map((ev) => {
    const sec = document.createElement("div");
    sec.className = "info-section peek";
    for (const { page, card } of [...ev.cards].sort((a, b) => a.page - b.page)) {
      const item = document.createElement("div");
      item.className = "peek-item";
      const no = document.createElement("div");
      no.className = "peek-page-no";
      no.textContent = t("ui.page_n", { n: page });
      item.append(no, cardEl(card, { small: true }));
      sec.appendChild(item);
    }
    return sec;
  });
  showInfo("peek", t("ui.peek.title"), body);
  document.getElementById("info-close").textContent = t("ui.ok");
}

function closeInfo() {
  INFO = null;
  document.getElementById("info-overlay").classList.add("hidden");
}
document.getElementById("info-overlay").onclick = (e) => {
  if (e.target.id === "info-overlay") closeInfo();
};

function signed(n) { return n > 0 ? `+${n}` : String(n); }

// 一列:說明(卡名可點)+ 右側數值或時效
function infoRow(text, nums, right, rightCls) {
  const row = document.createElement("div");
  row.className = "info-row";
  const label = document.createElement("span");
  label.textContent = text;
  linkCardNames(label, nums);
  const value = document.createElement("span");
  value.className = rightCls;
  value.textContent = right;
  row.append(label, value);
  return row;
}

function infoSection(title, rows, emptyText) {
  const sec = document.createElement("div");
  sec.className = "info-section";
  const h = document.createElement("h4");
  h.textContent = title;
  sec.appendChild(h);
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "info-empty";
    empty.textContent = emptyText;
    sec.appendChild(empty);
  }
  sec.append(...rows);
  return sec;
}

const BREAKDOWN_BASE = new Set(["mamodo", "spell", "fixed"]);   // 基礎值不帶正負號

// 魔力勝負明細:ev 為 showdown 事件或快照的 battle(live=true 為即時明細)
function showBreakdown(ev) {
  const side = (who, total, items) => infoSection(
    t(who === "attack" ? "ui.breakdown.attack" : "ui.breakdown.defense",
      { player: pname(who === "attack" ? ev.attacker : 1 - ev.attacker), total }),
    items.map((i) => infoRow(
      t(`breakdown.${i.kind}`, { card: i.source ? cname(i.source) : "" }),
      i.source ? [i.source] : [],
      BREAKDOWN_BASE.has(i.kind) ? String(i.amount) : signed(i.amount), "info-amount")),
    t("ui.breakdown.no_defense"));
  const body = [side("attack", ev.attacker_total, ev.attacker_breakdown),
                side("defense", ev.defender_total, ev.defender_breakdown)];
  if (!ev.live) {
    const result = document.createElement("div");
    result.className = "info-result";
    result.textContent = t(`log.showdown.${ev.winner}`);
    body.push(result);
  }
  showInfo("breakdown", t(ev.live ? "ui.breakdown.live_title" : "ui.breakdown.title"), body);
}

// 作用中效果:依擁有者分組;說明依種類取 i18n,沒有專屬文字時退回來源卡效果文
function renderEffectsInfo() {
  const effects = (S && S.effects) || [];
  const body = [0, 1].map((p) => infoSection(pname(p),
    effects.filter((e) => e.owner === p).map((e) =>
      infoRow(t("ui.effects.item", { card: cname(e.source), text: effectText(e) }), [e.source],
              effectWhen(e), "info-when")),
    t("ui.effects.none")));
  showInfo("effects", t("ui.effects.title"), body);
}

function mamodoName(family) {
  const num = Object.keys(CARDS).find((n) => CARDS[n].type === "mamodo" && CARDS[n].related_mamodo === family);
  return num && TEXT[num] ? TEXT[num].name : family;
}

function effectTarget(e) {
  if (e.target_slot !== null && e.target_slot !== undefined) {
    const owner = e.target_player !== null && e.target_player !== undefined ? e.target_player : e.owner;
    const slot = S.players[owner].slots.find((sl) => sl.uid === e.target_slot);
    return slot ? cname(slot.top) : t("ui.effects.gone_mamodo");
  }
  return e.target_player !== null && e.target_player !== undefined ? pname(e.target_player) : pname(e.owner);
}

function effectText(e) {
  let key = e.type === "modifier" && e.kind === "restriction"
    ? `effect.restriction.${e.flag}` : `effect.${e.type}.${e.kind}`;
  if (e.mamodo && DICT[`${key}.mamodo`] !== undefined) key += ".mamodo";   // 限定魔物的版本
  if (e.used && DICT[`${key}.used`] !== undefined) key += ".used";          // E-010 借用的效果已使用
  if (DICT[key] === undefined) return (TEXT[e.source] && TEXT[e.source].effect) || e.source;
  const changes = [];
  if (e.power_delta) changes.push(t("effect.piece.power", { n: signed(e.power_delta) }));
  if (e.cost_delta) changes.push(t("effect.piece.cost", { n: signed(e.cost_delta) }));
  if (e.optional) changes.push(t("effect.piece.optional"));
  return t(key, { target: effectTarget(e), amount: signed(e.amount || 0),
    mamodo: e.mamodo ? mamodoName(e.mamodo) : t("effect.any_mamodo"),
    card: e.card ? cname(e.card) : "", changes: changes.join(t("ui.sep.list")) });
}

// 時效:「至下回合結束」「下一回合」依建立回合相對於目前回合換算
function effectWhen(e) {
  if (e.type === "standby") return t(`effect.expires.${e.expires}`);
  const later = e.created_turn === S.turn_no;
  if (e.duration === "until_end_next_turn" || e.duration === "next_turn") {
    return t(later ? `effect.duration.${e.duration}` : "effect.duration.turn");
  }
  return t(`effect.duration.${e.duration}`);
}

document.getElementById("effects-toggle").onclick = () => renderEffectsInfo();
document.getElementById("prefs-toggle").onclick = () => renderPrefsInfo();
document.getElementById("lang-toggle").onclick = () => renderLangInfo();

// ---------------------------------------------------------------- 意見回報

// 給開發者看的環境資訊:固定格式、不翻譯;不帶 token、暱稱、牌組
function feedbackContext() {
  const parts = [`lang=${LANG}`, `ver=${META.version || "unknown"}`];
  if (SESSION) parts.push(`mode=${SESSION.mode}`, `room=${SESSION.code}`);
  if (S) parts.push(`turn=${S.turn_no}`, `phase=${S.phase}`);
  parts.push(`ua=${navigator.userAgent}`);
  return parts.join("; ");
}

function feedbackFormUrl(context) {
  const url = new URL(FEEDBACK.formUrl);
  if (FEEDBACK.contextEntry) {
    url.searchParams.set("usp", "pp_url");
    url.searchParams.set(FEEDBACK.contextEntry, context);
  }
  return url.href;
}

function openFeedback() {
  const context = feedbackContext();
  const channel = (kind, href) => {
    const sec = document.createElement("div");
    sec.className = "info-section feedback-channel";
    const link = document.createElement("a");
    link.className = `feedback-${kind}`;
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = t(`ui.feedback.${kind}`);
    const desc = document.createElement("p");
    desc.className = "feedback-desc";
    desc.textContent = t(`ui.feedback.${kind}_desc`);
    sec.append(link, desc);
    return sec;
  };
  const body = [];
  const intro = document.createElement("p");
  intro.className = "feedback-desc";
  intro.textContent = t("ui.feedback.intro");
  body.push(intro);
  if (FEEDBACK.formUrl) body.push(channel("form", feedbackFormUrl(context)));
  body.push(channel("github", FEEDBACK.issuesUrl));

  const sec = document.createElement("div");
  sec.className = "info-section";
  const h = document.createElement("h4");
  h.textContent = t("ui.feedback.context");
  const text = document.createElement("code");
  text.className = "feedback-context";
  text.textContent = context;
  const copy = document.createElement("button");
  copy.className = "feedback-copy";
  copy.textContent = t("ui.feedback.copy");
  copy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(context);
      copy.textContent = t("ui.feedback.copied");
    } catch {
      copy.textContent = t("ui.feedback.copy_failed");
    }
  };
  sec.append(h, text, copy);
  body.push(sec);
  showInfo("feedback", t("ui.feedback.title"), body);
}
document.getElementById("feedback-toggle").onclick = () => openFeedback();

// ---------------------------------------------------------------- 規則頁

// 時機指示的步驟與行動欄提示 → 規則頁段落(測試檢查每個段落都存在)
const RULE_LINKS = {
  "timing.start": "turn",
  "timing.nonbattle": "actions",
  "timing.battle_in": "battle",
  "timing.defense": "battle",
  "timing.effects": "battle",
  "timing.end": "advanced",
  "hint.start": "turn",
  "hint.play": "actions",
  "hint.field_effect": "actions",
  "hint.own_turn_cards": "actions",
  "hint.opp_turn_cards": "actions",
  "hint.pass_end": "actions",
  "hint.attack": "battle",
  "hint.allow_battle": "battle",
  "hint.insert_action": "battle",
  "hint.defend": "battle",
  "hint.no_defense": "battle",
  "hint.battle_effects": "battle",
  "hint.pass_showdown": "battle",
  "hint.deploy": "advanced",
};

// 範例卡上各圖示的位置:卡圖(465×679)上的像素框 [範例卡, x, y, w, h],換成百分比後與卡圖一起等比例縮放。
// 範例卡標示與圖示對照共用這份位置表;換卡圖版本時只需調整這裡
const ART_W = 465, ART_H = 679;
const ART_BOXES = {
  type: ["M-001", 18, 28, 88, 88],
  power: ["M-001", 28, 575, 94, 70],
  battle: ["M-001", 30, 488, 54, 42],
  cost: ["S-001", 378, 26, 58, 56],
  attack: ["S-001", 380, 90, 60, 58],
  defense: ["S-001", 382, 155, 54, 54],
  damage: ["S-001", 362, 598, 62, 56],
  nobattle: ["S-026", 380, 155, 60, 60],
  cutin: ["M-026", 30, 492, 54, 50],
};
const RULE_FIGURES = ["M-001", "S-001", "S-026", "M-026"];
const RULE_ICONS = ["cost", "attack", "defense", "nobattle", "battle", "cutin", "power", "damage"];
const ICON_FALLBACK = { cost: "1", attack: "A", defense: "D", nobattle: "NO BATTLE", battle: "BATTLE",
                        cutin: "CUT-IN", power: "Power", damage: "1→" };   // 缺圖時的文字標籤

// 卡圖是另外安裝的外部資源:逐張探測,載入失敗時改以文字呈現
const artProbe = {};
function probeArt(num) {
  if (!artProbe[num]) {
    artProbe[num] = new Promise((done) => {
      const img = new Image();
      img.onload = () => done(true);
      img.onerror = () => done(false);
      img.src = artUrl(num);
    });
  }
  return artProbe[num];
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function rulesMissingNote(body) {
  if (!body.querySelector(".rules-missing-art")) {
    body.querySelector(".rules-figure-wrap").prepend(el("div", "rules-missing-art", RULES.figure.missing));
  }
}

function renderRuleFigure(body) {
  const wrap = el("div", "rules-figure-wrap");
  const row = el("div", "rules-figures");
  const legend = el("ol", "rules-legend");
  let n = 0;
  for (const card of RULE_FIGURES) {
    const box = el("figure", "rules-figure");
    const frame = el("div", "rules-art");
    const img = el("img");
    img.alt = cname(card);
    frame.appendChild(img);
    for (const [key, [owner, x, y, w, h]] of Object.entries(ART_BOXES)) {
      if (owner !== card) continue;
      n += 1;
      const ring = el("span", "rules-mark");          // 框住圖示、編號放在角落,不遮住圖示
      Object.assign(ring.style, { left: `${(x / ART_W) * 100}%`, top: `${(y / ART_H) * 100}%`,
        width: `${(w / ART_W) * 100}%`, height: `${(h / ART_H) * 100}%` });
      ring.appendChild(el("span", "rules-mark-no", String(n)));
      frame.appendChild(ring);
      legend.appendChild(el("li", null, RULES.figure.marks[key]));
    }
    box.append(frame, el("figcaption", null, cname(card)));
    row.appendChild(box);
    probeArt(card).then((ok) => {
      if (ok) { img.src = artUrl(card); return; }
      frame.replaceChildren(el("div", "rules-art-missing", cname(card)));
      rulesMissingNote(body);
    });
  }
  wrap.append(el("h4", null, RULES.figure.title), row, legend);
  return wrap;
}

function renderRuleIcons(body) {
  const wrap = el("div", "rules-icons");
  wrap.appendChild(el("h4", null, RULES.figure.icons_title));
  for (const key of RULE_ICONS) {
    const [card, x, y, w, h] = ART_BOXES[key];
    const fallback = ICON_FALLBACK[key];
    const item = el("div", "rules-icon");
    const slot = el("span", "icon-slot");
    item.append(slot, el("span", null, RULES.figure.marks[key]));
    wrap.appendChild(item);
    probeArt(card).then((ok) => {
      if (!ok) {
        slot.replaceChildren(el("span", "icon-fallback", fallback));
        rulesMissingNote(body);
        return;
      }
      const crop = el("span", "icon-crop");   // 以百分比裁出卡圖上的單一圖示
      crop.style.backgroundImage = `url(${artUrl(card)})`;
      crop.style.aspectRatio = `${w} / ${h}`;
      crop.style.backgroundSize = `${(ART_W / w) * 100}% auto`;
      crop.style.backgroundPosition = `${(x / (ART_W - w)) * 100}% ${(y / (ART_H - h)) * 100}%`;
      slot.replaceChildren(crop);
    });
  }
  return wrap;
}

function buildRules() {
  const body = document.getElementById("rules-body");
  const toc = document.getElementById("rules-toc");
  if (body.dataset.built) return;
  body.dataset.built = "1";
  document.getElementById("rules-title").textContent = RULES.title;
  toc.replaceChildren(el("div", "rules-toc-title", RULES.toc));
  for (const sec of RULES.sections) {
    const link = el("button", "rules-toc-item", sec.title);
    link.dataset.section = sec.id;
    link.onclick = () => scrollToRule(sec.id);
    toc.appendChild(link);
    const box = el("section", "rules-section");
    box.id = `rules-sec-${sec.id}`;
    box.appendChild(el("h4", null, sec.title));
    for (const block of sec.blocks) {
      if (block.p) box.appendChild(el("p", null, block.p));
      if (block.list) {
        const ul = el("ul");
        for (const item of block.list) ul.appendChild(el("li", null, item));
        box.appendChild(ul);
      }
      if (block.figure) box.appendChild(renderRuleFigure(body));
      if (block.icons) box.appendChild(renderRuleIcons(body));
    }
    body.appendChild(box);
  }
  body.addEventListener("scroll", markRuleToc);
}

// 目錄標示:內容區頂端所在的段落
function markRuleToc() {
  const body = document.getElementById("rules-body");
  const top = body.getBoundingClientRect().top + 50;
  let current = RULES.sections[0].id;
  for (const sec of RULES.sections) {
    if (document.getElementById(`rules-sec-${sec.id}`).getBoundingClientRect().top <= top) current = sec.id;
  }
  for (const item of document.querySelectorAll("#rules-toc .rules-toc-item")) {
    item.classList.toggle("current", item.dataset.section === current);
  }
}

function scrollToRule(sectionId) {
  const sec = document.getElementById(`rules-sec-${sectionId}`);
  const body = document.getElementById("rules-body");
  if (sec) body.scrollTop += sec.getBoundingClientRect().top - body.getBoundingClientRect().top;
  markRuleToc();
}

// 開啟規則頁(可指定段落);只是蓋在畫面上,對局照常進行
function openRules(sectionId = null) {
  if (!RULES) return;
  buildRules();
  const close = document.getElementById("rules-close");
  close.textContent = RULES.close;
  close.onclick = closeRules;
  document.getElementById("rules-overlay").classList.remove("hidden");
  if (sectionId) scrollToRule(sectionId);
  else markRuleToc();
}

function closeRules() {
  document.getElementById("rules-overlay").classList.add("hidden");
}
document.getElementById("rules-overlay").onclick = (e) => {
  if (e.target.id === "rules-overlay") closeRules();
};
document.getElementById("rules-toggle").onclick = () => openRules();

function showDiscard(p) {
  const ps = S.players[p];
  showDialog(pname(p) + t("ui.sep.meta") + t("ui.discard", { n: ps.discard.length }),
    ps.discard.length
      ? ps.discard.map((num, index) => {
        const ctx = { kind: "pick", zone: "discard", p, index };   // 決策目標:放大檢視提供「選擇」
        const target = pickValue(ctx) !== undefined;
        return { cardNum: num, pickable: target, onpick: () => zoom(num, target ? ctx : undefined) };
      })
      : [{ label: t("ui.close"), onpick: () => {} }]);
}

// 查閱魔書:對頁網格呈現 32 頁,標示當前翻開 / 已離場 / 已用戰術頁。
// 決策目標在魔書中時,可選頁發光,點了在放大檢視選擇;對手的魔書只有選項中的頁有卡面,其他頁為卡背
let BOOK_VIEW = null;   // 開啟中的魔書網格屬於哪位玩家

function showBookReview(p) {
  const ps = S.players[p];
  const targets = PICK ? [...PICK.book.keys()].filter((k) => k.startsWith(`${p}:`)) : [];
  const overlay = document.getElementById("book-review-overlay");
  if (!ps.book && !targets.length) { closeBookReview(); return; }
  // 開啟時捲到當前翻開的對頁;開啟期間的重繪保留玩家捲動的位置
  const box = document.getElementById("book-review");
  const keepScroll = BOOK_VIEW === p ? box.scrollTop : null;
  BOOK_VIEW = p;
  document.getElementById("book-review-title").textContent =
    ps.book && iControl(p) ? t("ui.book_review_title") : pname(p) + t("ui.book");
  const close = document.getElementById("book-review-close");
  close.textContent = t("ui.close");
  close.onclick = closeBookReview;
  const grid = document.getElementById("book-review-grid");
  grid.innerHTML = "";
  const consumed = new Set(ps.consumed_pages || []);
  const usedSpell = new Set(ps.used_spell_pages || []);
  const isOpen = (pg) => pg === ps.pos || pg === ps.pos + 1;

  const anyPage = new Map((ps.any_page_spells || []).map((e) => [e.page, e]));
  const cell = (pg) => {
    const ctx = { kind: "pick", zone: "book", p, page: pg };
    const target = PICK && PICK.book.get(`${p}:${pg}`);
    const usable = anyPage.get(pg);   // P-015:可從魔書使用的戰術頁
    const num = ps.book ? ps.book[pg - 1] : target && target.card;
    const wrap = document.createElement("div");
    wrap.className = "review-cell";
    wrap.dataset.page = pg;
    if (isOpen(pg) && !consumed.has(pg)) wrap.classList.add("open");
    if (target || usable) wrap.classList.add("pickable");
    const tag = (cls, key) => `<span class="review-tag ${cls}">${t(key)}</span>`;
    let marks = "";
    if (isOpen(pg) && !consumed.has(pg)) marks += tag("cur", "ui.book_page_current");
    if (consumed.has(pg)) marks += tag("left", "ui.book_page_left");
    else if (usedSpell.has(pg)) marks += tag("used", "ui.book_spell_used");
    let card;
    if (num && !consumed.has(pg)) {
      const zoomCtx = target ? ctx : usable ? { kind: "any_page", p, page: pg } : undefined;
      card = cardEl(num, { small: true, zoomCtx });
      card.dataset.card = num;
      if (target || usable) card.classList.add("pickable");
    } else {
      card = cardBackEl(pg, consumed.has(pg));
      if (target) card.onclick = () => choosePick(target.value);   // 空頁:沒有卡面可放大,點了即選
    }
    wrap.appendChild(card);
    const foot = document.createElement("div");
    foot.className = "review-foot";
    foot.innerHTML = `<span class="review-pno">${t("ui.page_n", { n: pg })}</span>${marks}`;
    wrap.appendChild(foot);
    return wrap;
  };

  const spread = (pages, single) => {
    const el = document.createElement("div");
    el.className = "review-spread" + (single ? " single" : "");
    for (const pg of pages) el.appendChild(cell(pg));
    grid.appendChild(el);
  };
  spread([1], true);
  for (let i = 2; i <= 31; i += 2) spread([i, i + 1], false);
  spread([32], true);
  overlay.classList.remove("hidden");
  if (keepScroll !== null) {
    box.scrollTop = keepScroll;
  } else {
    const cur = grid.querySelector(`.review-cell[data-page="${Math.max(ps.pos, 1)}"]`);
    box.scrollTop = 0;
    const head = document.getElementById("book-review-head").offsetHeight;   // 標題列固定在上緣
    if (cur) box.scrollTop = cur.parentElement.getBoundingClientRect().top - box.getBoundingClientRect().top - head - 8;
  }
}

function closeBookReview() {
  BOOK_VIEW = null;
  document.getElementById("book-review-overlay").classList.add("hidden");
}
document.getElementById("book-review-overlay").onclick = (e) => {
  if (e.target.id === "book-review-overlay") closeBookReview();
};

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
    case "page_turn_restricted": return t("log.page_turn_restricted", { ...P, source: cname(ev.source) || ev.source });
    case "mp_changed":
      return ev.delta >= 0 ? t("log.mp_changed_gain", { ...P, delta: ev.delta, mp: ev.mp })
                           : t("log.mp_changed_pay", { ...P, delta: -ev.delta, mp: ev.mp });
    case "card_played":
      if (ev.stacked) return t("log.card_played_stacked", { ...P, card: cname(ev.card) });
      if (ev.forced) return t("log.card_played_forced", { ...P, card: cname(ev.card) });
      return t("log.card_played", { ...P, card: cname(ev.card) });
    case "book_card_used":   // 戰術依是否帶使用魔物描述;事件卡維持「使用事件卡」
      if (CARDS[ev.card] && CARDS[ev.card].type === "spell") {
        return ev.mamodo
          ? t("log.spell_used_by", { ...P, mamodo: cname(ev.mamodo), card: cname(ev.card) })
          : t("log.spell_used", { ...P, card: cname(ev.card) });
      }
      return t("log.book_card_used", { ...P, card: cname(ev.card) });
    case "ability_used":
      return ev.via   // E-010 借用的搭檔效果:顯示為使用者經 E-010 使用
        ? t("log.ability_used_borrowed", { ...P, source: cname(ev.via), card: cname(ev.card) })
        : t("log.ability_used", { ...P, card: cname(ev.card) });
    case "passed": return t("log.passed", P);
    case "battle_in_check":
      return ev.spell
        ? t("log.battle_in_check", { player: pname(ev.attacker), spell: cname(ev.spell) })
        : t("log.battle_in_check_mamodo", { player: pname(ev.attacker), mamodo: cname(ev.mamodo) });
    case "battle_in_voided": return t("log.battle_in_voided");
    case "battle_started":
      return ev.spell
        ? t("log.battle_started", { player: pname(ev.attacker), spell: cname(ev.spell) })
        : t("log.battle_started_mamodo", { player: pname(ev.attacker), mamodo: cname(ev.mamodo) });
    case "card_returned_to_book": return t("log.card_returned_to_book", { ...P, card: cname(ev.card) });
    case "stack_detached": return t("log.stack_detached", { ...P, card: cname(ev.detached) });
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
    case "damage_prevented":
      return ev.reason === "no_target" ? t("log.damage_no_target", P) : t("log.damage_prevented", P);
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
    case "effect_negated": return t("log.effect_negated", { ...P, source: cname(ev.source), card: cname(ev.negated) });
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
    linkCardNames(el, cardRefs(ev));  // 卡名可點開檢視
    if (ev.type === "showdown" && ev.attacker_breakdown) {
      const ref = document.createElement("span");
      ref.className = "breakdown-ref";
      ref.textContent = t("ui.breakdown.open");
      ref.onclick = () => showBreakdown(ev);
      el.appendChild(ref);
    }
    holder.appendChild(el);
  }
  holder.scrollTop = holder.scrollHeight;
  updateLogTab();
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
  const opts = [["blank", t("builder.new_blank")]];
  for (const p of PRESETS) {                 // 從探索得到的每個預組複製起手
    opts.push(["preset:" + p.id, t("builder.new_from_deck", { name: presetName(p) })]);
  }
  for (const d of DeckStore.list()) {
    opts.push(["copy:" + d.id, t("builder.new_from_deck", { name: d.name })]);
  }
  for (const [value, label] of opts) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  sel.onchange = async () => {
    const v = sel.value;
    sel.value = "";
    if (!v) return;
    let pages = Array(32).fill(null);
    if (v.startsWith("preset:")) {
      pages = await fetchPresetPages(v.slice(7));
    } else if (v.startsWith("copy:")) {
      const src = DeckStore.get(v.slice(5));
      if (src) pages = [...src.pages];
    }
    loadDeckIntoBuilder({ id: null, name: t("builder.new"), pages });
  };
}

function renderPoolFilters() {
  renderCardPoolFilters(document.getElementById("pool-filters"), B, renderPool);
}

function renderCardPoolFilters(holder, filters, onChange) {
  holder.innerHTML = "";
  const typeSel = document.createElement("select");
  typeSel.innerHTML = `<option value="">${t("builder.filter.type")}:${t("builder.filter.all")}</option>`;
  for (const ty of ["mamodo", "partner", "spell", "event"]) {
    typeSel.innerHTML += `<option value="${ty}">${t("builder.type." + ty)}</option>`;
  }
  typeSel.setAttribute("aria-label", t("builder.filter.type"));
  typeSel.value = filters.ftype;
  typeSel.onchange = () => {
    filters.ftype = typeSel.value;
    mamodoSel.disabled = filters.ftype === "event";   // 事件沒有對應魔物:暫停對應魔物篩選(保留選擇)
    onChange();
  };
  holder.appendChild(typeSel);

  const mamodoSel = document.createElement("select");
  const names = [...new Set(Object.values(CARDS)
    .map((c) => c.related_mamodo).filter((m) => m && m !== COMMAND_MAMODO))].sort();
  mamodoSel.innerHTML = `<option value="">${t("builder.filter.mamodo")}:${t("builder.filter.all")}</option>`
    + `<option value="${MAMODO_NONE}">${t("builder.filter.mamodo")}:${t("builder.filter.none")}</option>`;
  for (const name of names) {
    const numAny = Object.values(CARDS).find(
      (c) => c.type === "mamodo" && c.related_mamodo === name);
    const label = numAny && TEXT[numAny.number] ? TEXT[numAny.number].name : name;
    mamodoSel.innerHTML += `<option value="${name}">${label}</option>`;
  }
  mamodoSel.setAttribute("aria-label", t("builder.filter.mamodo"));
  mamodoSel.value = filters.fmamodo;
  mamodoSel.disabled = filters.ftype === "event";
  mamodoSel.onchange = () => { filters.fmamodo = mamodoSel.value; onChange(); };
  holder.appendChild(mamodoSel);

  // 產品(彈數)篩選:同一張卡可屬多個產品
  const productSel = document.createElement("select");
  const products = [...new Set(Object.values(CARDS).flatMap((c) => c.sets || []))].sort();
  productSel.innerHTML = `<option value="">${t("builder.filter.product")}:${t("builder.filter.all")}</option>`;
  for (const tag of products) {
    productSel.innerHTML += `<option value="${tag}">${tag}</option>`;
  }
  productSel.setAttribute("aria-label", t("builder.filter.product"));
  productSel.value = filters.fproduct;
  productSel.onchange = () => { filters.fproduct = productSel.value; onChange(); };
  holder.appendChild(productSel);
}

function renderPool() {
  renderCardPool(document.getElementById("pool-grid"), B, placeCard, { detail: true });
}

// 對應魔物篩選:「無」只留指令戰術;類型為事件時暫停(事件沒有對應魔物)
const MAMODO_NONE = "__none__";
function matchesMamodoFilter(def, filters) {
  if (!filters.fmamodo || filters.ftype === "event") return true;
  if (filters.fmamodo === MAMODO_NONE) return isCommandSpell(def);
  return def.related_mamodo === filters.fmamodo;
}

function renderCardPool(grid, filters, onPick, opts = {}) {
  grid.innerHTML = "";
  const numbers = Object.keys(CARDS).sort();
  for (const num of numbers) {
    const def = CARDS[num];
    if (filters.ftype && def.type !== filters.ftype) continue;
    if (!matchesMamodoFilter(def, filters)) continue;
    if (filters.fproduct && !(def.sets || []).includes(filters.fproduct)) continue;
    const el = cardEl(num, { small: true, detail: opts.detail });
    el.onclick = () => onPick(num);
    el.setAttribute("role", "button");
    el.tabIndex = 0;
    el.setAttribute("aria-label", `${num} ${cname(num)}`);
    el.onkeydown = (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onPick(num); }
    };
    grid.appendChild(el);
  }
}

function pageSlotEl(i) {
  return bookPageSlotEl(i, B.deck.pages, B.selected, {
    scope: "builder", enabled: () => true, select: togglePage, swap: swapPages, detail: true,
  });
}

function bookPageSlotEl(i, pages, selected, actions) {
  const slot = document.createElement("div");
  slot.className = "page-slot" + (selected === i ? " selected" : "")
    + (pages[i] ? " filled" : "");
  slot.dataset.page = i;
  slot.setAttribute("role", "button");
  slot.setAttribute("aria-pressed", String(selected === i));
  slot.setAttribute("aria-label", `P${i + 1} ${pages[i] ? cname(pages[i]) : t("builder.empty_page", { n: i + 1 })}`);
  slot.tabIndex = 0;
  const pick = () => { if (actions.enabled()) actions.select(i); };
  const pno = document.createElement("span");
  pno.className = "pno";
  const num = pages[i];
  const full = i === 0 ? t("builder.page_first") : i === 31 ? t("builder.page_last") : `P${i + 1}`;
  // 放了卡時首頁 / 末頁只顯示頁碼,讓出右上角給卡號;完整說明留在提示與空頁
  pno.textContent = num ? `P${i + 1}` : full;
  pno.title = full;
  slot.appendChild(pno);
  if (num) {
    const card = cardEl(num, { small: true, detail: actions.detail });
    card.onclick = (ev) => { ev.stopPropagation(); pick(); };
    card.querySelector("img").draggable = false;
    slot.appendChild(card);
    slot.draggable = true;
    slot.ondragstart = (ev) => {
      if (!actions.enabled()) { ev.preventDefault(); return; }
      ev.dataTransfer.setData("application/x-gash-page", JSON.stringify({ scope: actions.scope, index: i }));
      ev.dataTransfer.effectAllowed = "move";
    };
  } else {
    const label = document.createElement("span");
    label.className = "empty-label";
    label.textContent = t("builder.empty_page", { n: i + 1 });
    slot.appendChild(label);
  }
  slot.onclick = pick;
  slot.onkeydown = (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); }
  };
  slot.ondragover = (ev) => {
    if (!actions.enabled() || !Array.from(ev.dataTransfer.types).includes("application/x-gash-page")) return;
    ev.preventDefault();
    slot.classList.add("dragover");
  };
  slot.ondragleave = () => slot.classList.remove("dragover");
  slot.ondragend = () => slot.classList.remove("dragover");
  slot.ondrop = (ev) => {
    ev.preventDefault();
    slot.classList.remove("dragover");
    if (!actions.enabled()) return;
    try {
      const from = JSON.parse(ev.dataTransfer.getData("application/x-gash-page"));
      if (from.scope === actions.scope && Number.isInteger(from.index) &&
          from.index >= 0 && from.index < pages.length && from.index !== i) actions.swap(from.index, i);
    } catch (_) { /* 忽略外部拖入的非頁位資料。 */ }
  };
  return slot;
}

function renderBook() {
  renderBookGrid(document.getElementById("book-grid"), pageSlotEl);
}

function renderBookGrid(grid, renderSlot) {
  const focused = grid.contains(document.activeElement)
    ? document.activeElement.closest(".page-slot")?.dataset.page : null;
  grid.replaceChildren();
  const spread = (indices, single) => {
    const el = document.createElement("div");
    el.className = "spread" + (single ? " single" : "");
    for (const i of indices) el.appendChild(renderSlot(i));
    grid.appendChild(el);
  };
  spread([0], true);
  for (let i = 1; i < 31; i += 2) spread([i, i + 1], false);
  spread([31], true);
  if (focused != null) grid.querySelector(`[data-page="${focused}"]`)?.focus({ preventScroll: true });
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

// ---------------------------------------------------------------- 設定頁

const SETUP_MODES = ["npc", "friend", "local"];
let friendMode = "create";

// 上次的選擇(localStorage gash-setup):{npc: {deck, opp, level}, friend: {deck, timer, mode}, local: {deck0, deck1}}
const SETUP_FIELDS = {
  "deck-npc": ["npc", "deck"], "deck-npc-opp": ["npc", "opp"], "npc-level": ["npc", "level"],
  "deck-friend": ["friend", "deck"], "timer-select": ["friend", "timer"],
  "deck-local-0": ["local", "deck0"], "deck-local-1": ["local", "deck1"],
};

function loadSetup() {
  try {
    const v = JSON.parse(localStorage.getItem("gash-setup"));
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  } catch (_) {
    return {};
  }
}

function setupPref(mode) {
  const v = loadSetup()[mode];
  return v && typeof v === "object" ? v : {};
}

function rememberSetup(mode, key, value) {
  const all = loadSetup();
  all[mode] = { ...setupPref(mode), [key]: value };
  try { localStorage.setItem("gash-setup", JSON.stringify(all)); } catch (_) { /* 不可用時不記 */ }
}

// 選單重新產生後還原:記住的值是可選的選項才選,否則維持缺省
function restoreSetup() {
  for (const [id, [mode, key]] of Object.entries(SETUP_FIELDS)) {
    const sel = document.getElementById(id);
    const value = setupPref(mode)[key];
    const opt = [...sel.options].find((o) => o.value === value);
    if (opt && !opt.disabled) sel.value = value;
  }
}

function openSetup(mode, opts = {}) {
  for (const m of SETUP_MODES) {
    document.getElementById(`setup-${m}`).classList.toggle("hidden", m !== mode);
  }
  document.getElementById("setup-title").textContent = t(`ui.landing.${mode}`);
  if (mode === "friend") {
    const saved = setupPref("friend").mode;
    setFriendMode(opts.friendMode || (saved === "join" ? "join" : "create"), false);
  }
  show("setup");
}

function closeSetup() {
  history.replaceState(null, "", "/");   // 由加入連結進來時,避免重新整理又回到加入模式
  show("landing");
}

// 與朋友對戰:建立 / 加入切換,只改顯示,不清除已填的值;remember 為 false 時(加入連結)不記住
function setFriendMode(mode, remember = true) {
  friendMode = mode;
  for (const btn of document.querySelectorAll("#friend-mode button")) {
    const on = btn.dataset.mode === mode;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", String(on));
  }
  document.getElementById("friend-desc").textContent = t(`ui.landing.${mode}_desc`);
  document.getElementById("friend-timer-row").classList.toggle("hidden", mode !== "create");
  document.getElementById("friend-code-row").classList.toggle("hidden", mode !== "join");
  document.getElementById("friend-submit").textContent = t(`ui.landing.${mode}`);
  if (remember) rememberSetup("friend", "mode", mode);
}

function submitFriend() {
  if (friendMode === "create") { createRoom(); return; }
  const code = document.getElementById("join-code").value.trim();
  if (code) joinRoom(code);
}

// ---------------------------------------------------------------- 對戰中人數(首頁)

// 只在首頁且頁面可見時更新:進入首頁、回到頁面時立即抓取,之後每 30 秒一次
const ONLINE_REFRESH_MS = 30000;
let onlineTimer = null;
let onlineSeq = 0;      // 請求交錯時只採用最後一次發出的結果

async function refreshOnline() {
  const seq = ++onlineSeq;
  let count = null;
  try {
    const res = await fetch("/api/online");
    if (res.ok) count = (await res.json()).count;
  } catch (_) { /* 失敗:不顯示 */ }
  if (seq !== onlineSeq) return;
  const ok = Number.isInteger(count) && count >= 0;
  const el = document.getElementById("landing-online");
  el.textContent = !ok ? "" : count > 0 ? t("ui.online.count", { n: count }) : t("ui.online.none");
  el.classList.toggle("hidden", !ok);   // 失敗時不留著舊值,也不當成 0
  el.classList.toggle("none", count === 0);
}

function syncOnline() {
  clearInterval(onlineTimer);
  onlineTimer = null;
  const onLanding = !document.getElementById("landing").classList.contains("hidden");
  if (!onLanding || document.visibilityState === "hidden") return;
  refreshOnline();
  onlineTimer = setInterval(refreshOnline, ONLINE_REFRESH_MS);
}

document.addEventListener("visibilitychange", syncOnline);

// ---------------------------------------------------------------- 入口頁渲染與啟動

function renderLanding() {
  document.getElementById("landing-title").setAttribute("aria-label", t("app.title"));
  const entries = {
    npc: () => openSetup("npc"),
    friend: () => openSetup("friend"),
    local: () => openSetup("local"),
    builder: () => {
      history.replaceState(null, "", "/?builder=1");
      showBuilder();
    },
    rules: () => openRules(),
    feedback: () => openFeedback(),
  };
  for (const [key, onclick] of Object.entries(entries)) {
    const entry = document.getElementById(`entry-${key}`);
    entry.querySelector(".entry-title").textContent = t(`ui.landing.${key}`);
    entry.querySelector(".entry-desc").textContent = t(`ui.landing.${key}_desc`);
    entry.onclick = onclick;
  }
  document.getElementById("disclaimer-fan").textContent = t("ui.landing.disclaimer_fan");
  document.getElementById("disclaimer-rights").textContent = t("ui.landing.disclaimer_rights", { feedback: t("ui.landing.feedback") });
  document.getElementById("landing-version").textContent = META.version ? t("ui.version", { v: META.version }) : "";
  const releaseOpen = document.getElementById("release-open");
  releaseOpen.textContent = t("ui.release.open");
  releaseOpen.classList.toggle("hidden", !RELEASES);
  releaseOpen.onclick = showReleaseHistory;

  // 設定頁
  document.getElementById("setup-back").textContent = t("ui.setup.back");
  document.getElementById("setup-back").onclick = closeSetup;
  document.getElementById("npc-start").textContent = t("ui.landing.go");
  document.getElementById("npc-start").onclick = startNpc;
  document.getElementById("local-start").textContent = t("ui.landing.go");
  document.getElementById("local-start").onclick = startLocal;
  document.getElementById("friend-submit").onclick = submitFriend;
  for (const btn of document.querySelectorAll("#friend-mode button")) {
    btn.textContent = t(`ui.landing.${btn.dataset.mode}`);
    btn.onclick = () => setFriendMode(btn.dataset.mode);
  }
  setFriendMode(friendMode, false);

  document.getElementById("npc-level-label").textContent = t("ui.npc.level");
  const levelSel = document.getElementById("npc-level");
  levelSel.innerHTML = "";
  for (const level of ["normal", "dummy"]) {          // 缺省:一般
    const opt = document.createElement("option");
    opt.value = level;
    opt.textContent = t(`ui.npc.level.${level}`);
    levelSel.appendChild(opt);
  }

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
  document.getElementById("join-code-label").textContent = t("ui.landing.room_code");

  // 暱稱欄位(標籤/placeholder/預填上次;本機測試的兩個暱稱不預填)
  document.getElementById("name-local-0-label").textContent = t("ui.name.p1");
  document.getElementById("name-local-1-label").textContent = t("ui.name.p2");
  document.getElementById("name-friend-label").textContent = t("ui.name.self");
  document.getElementById("name-npc-label").textContent = t("ui.name.self");
  for (const id of ["name-local-0", "name-local-1", "name-npc", "name-friend"]) {
    document.getElementById(id).placeholder = t("ui.name.placeholder");
  }
  for (const id of ["name-npc", "name-friend"]) {
    document.getElementById(id).value = loadNick();
  }

  // 牌組選單(本機×2 / NPC / 與朋友對戰)
  document.getElementById("deck-local-0-label").textContent = t("ui.deck.p1");
  document.getElementById("deck-local-1-label").textContent = t("ui.deck.p2");
  document.getElementById("deck-friend-label").textContent = t("ui.deck.select");
  document.getElementById("deck-npc-label").textContent = t("ui.deck.select");
  document.getElementById("deck-npc-opp-label").textContent = t("ui.deck.npc");
  for (const id of ["deck-local-0", "deck-local-1", "deck-npc", "deck-npc-opp", "deck-friend"]) {
    deckOptions(document.getElementById(id));
  }
  const npcDeck = document.getElementById("deck-npc-opp");
  const random = document.createElement("option");      // 缺省:隨機
  random.value = NPC_RANDOM_DECK;
  random.textContent = t("ui.deck.random");
  npcDeck.prepend(random);
  npcDeck.value = NPC_RANDOM_DECK;

  // 上次的選擇:變更時就記住(先去構築器再回來也保留),重新產生選單後還原
  for (const [id, [mode, key]] of Object.entries(SETUP_FIELDS)) {
    const field = document.getElementById(id);
    field.onchange = () => rememberSetup(mode, key, field.value);
  }
  restoreSetup();

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
  renderAssetsHint();
}

// 卡圖未安裝/不完整的非阻斷提示(不擋任何流程,缺圖卡面以卡背佔位)
function renderAssetsHint() {
  const el = document.getElementById("assets-hint");
  const a = META.assets;
  if (!a) { el.classList.add("hidden"); return; }
  if (!a.installed || a.count === 0) {
    el.textContent = t("ui.assets.missing", { dir: a.install_dir });
  } else if (a.count < a.expected) {
    el.textContent = t("ui.assets.partial", { count: a.count, expected: a.expected });
  } else {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
}

// 構築器複製起手用:按需抓某預組的 32 頁(避免探索清單背全部 pages)
async function fetchPresetPages(id) {
  try {
    const d = await fetch(`/data/decks/${encodeURIComponent(id)}.json`).then((r) => r.json());
    return Array.isArray(d.pages) ? [...d.pages] : Array(32).fill(null);
  } catch (_) {
    return Array(32).fill(null);
  }
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

// 目前語言的字典與卡片文字;載入失敗時退回中文,不讓頁面空白
async function loadLanguage() {
  LANGS = await fetchJson("/static/i18n/languages.json").catch(() => LANGS);
  LANG = detectLang();
  const files = (lang) => Promise.all([fetchJson(`/static/i18n/${lang}.json`), fetchJson(`/data/cards.${lang}.json`)]);
  try {
    [DICT, TEXT] = await files(LANG);
  } catch (_) {
    LANG = FALLBACK_LANG;
    [DICT, TEXT] = await files(LANG);
  }
  RULES = await fetchJson(`/static/i18n/rules.${LANG}.json`)
    .catch(() => fetchJson(`/static/i18n/rules.${FALLBACK_LANG}.json`)).catch(() => null);
  const releases = await fetchJson(`/static/i18n/releases.${LANG}.json`)
    .catch(() => fetchJson(`/static/i18n/releases.${FALLBACK_LANG}.json`)).catch(() => null);
  RELEASES = releases && Array.isArray(releases.releases) && releases.releases.length ? releases.releases : null;
  document.documentElement.lang = LANG;   // 日文以 :lang(ja) 換日文字型
}

async function boot() {
  let presets;
  [, CARDS, presets, META] = await Promise.all([
    loadLanguage(),
    fetch("/data/cards.json").then((r) => r.json()).then((list) =>
      Object.fromEntries(list.map((c) => [c.number, c]))),
    fetch("/api/decks").then((r) => r.json()).then((d) => d.decks).catch(() => []),
    fetch("/api/meta").then((r) => r.json()).catch(() => META),
  ]);
  PRESETS = presets && presets.length ? presets : [{ id: DEFAULT_PRESET, name: DEFAULT_PRESET }];
  applyMotionClass();
  renderLanding();
  renderTopbar();

  const params = new URLSearchParams(location.search);
  if (params.has("join")) {
    // 開與朋友對戰的加入模式並預填房號,讓加入者先選暱稱與牌組再加入
    document.getElementById("join-code").value = params.get("join").toUpperCase();
    openSetup("friend", { friendMode: "join" });
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
