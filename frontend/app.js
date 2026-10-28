/* Gash Card Battle Online — 前端
 * 模式:本機(local, 全視角雙 token)/ 線上(online, 單 token + WS)/ NPC 對戰(npc, 同線上,對手由伺服器驅動)
 * / 觀戰(spectator)。
 * 規則裁決與資訊過濾全在後端;前端渲染視角化快照、送指令、渲染事件 log。 */

"use strict";

let DICT = {};        // i18n 字典(目前語言)
let CARDS = {};       // 卡片數值資料(decks.js 的驗證也依賴)
let PENDING = new Set();   // 資料已收錄、效果尚未實作的卡號(data/pending_cards.json):卡池不顯示、構築規則拒絕

// 已開放的卡(卡池、篩選選項用)
function openCards() { return Object.values(CARDS).filter((c) => !PENDING.has(c.number)); }
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
  // 檢視對手魔書(M-011 / E-016 / E-017):記下整本內容,挑卡時網格以它補上非候選頁
  const reveals = live ? fresh.filter((ev) => ev.type === "book_revealed" && ev.cards) : [];
  for (const ev of reveals) {
    REVEALED[ev.player] = { turn: S.turn_no, cards: new Map(ev.cards.map((c) => [c.page, c.card])) };
  }
  // 等飛卡、棄牌等特效播完,網格才不會蓋住演出。同一批經 HTTP 與 WS 各到一次時,第二次沒有新事件,
  // 仍要等第一次的特效:記下最早可開啟的時間,之後的觸發都等到那時
  const settle = Anim.overlaySettleMs(fresh);
  played.then(() => {
    pickOpenNotBefore = Math.max(pickOpenNotBefore, performance.now() + settle);
    setTimeout(autoOpenPick, Math.max(0, pickOpenNotBefore - performance.now()));
  });
}

// 決策開始時,可選的目標都在同一本魔書或同一個棄牌區(場上沒有目標)就自動開啟它;
// 每個決策只自動開啟一次,關閉後由決策提示的按鈕再開(可關閉查閱場面)
let autoOpenedPick = null;
let pickOpenNotBefore = 0;   // 疊加演出播完的時間;自動開啟不早於此
function autoOpenPick() {
  const wait = pickOpenNotBefore - performance.now();
  if (wait > 0) { setTimeout(autoOpenPick, wait); return; }
  if (!PICK || PICK.local || !S || !S.pending) return;
  const key = JSON.stringify([S.pending.kind, S.pending.player, S.pending.source, S.pending.options]);
  if (key === autoOpenedPick) return;
  autoOpenedPick = key;
  if (PICK.slot.size || PICK.books.size + PICK.discards.size !== 1) return;
  if (PICK.books.size) showBookReview([...PICK.books][0]);
  else showDiscard([...PICK.discards][0]);
}

// 被檢視的對手魔書:玩家 → {turn, cards: Map(頁 → 卡號)}。只在檢視的那個回合、挑卡決策期間有效
const REVEALED = {};
function revealedBook(p) {
  // 等待結束檢視的決策附整本卡面(只送給檢視者),重新整理後也有
  const pd = S && S.pending;
  const end = pd && pd.kind === "end_book_review" && iControl(pd.player) && (pd.options || [])[0];
  if (end && end.player === p && end.cards) return new Map(end.cards.map((c) => [c.page, c.card]));
  // 挑卡決策期間以 book_revealed 的內容補上非候選頁;決策結束(檢視結束)後不再提供,網格隨之關閉
  const r = REVEALED[p];
  return r && S && r.turn === S.turn_no && bookTargets(p).length ? r.cards : null;
}

// 選擇提示:目前的決策在 p 的魔書(zone="book")或棄牌區(zone="discard")有目標時,
// 回傳 {title: 決策的通用標題, source: 來源卡號};只是查閱時為 null
function pickHint(p, zone) {
  if (!PICK || PICK.local || !S.pending) return null;
  const has = zone === "book" ? PICK.books.has(p) : PICK.discards.has(p);
  if (!has) return null;
  const key = `choice.title.${S.pending.kind}`;
  return { title: DICT[key] ? t(key) : S.pending.kind, source: S.pending.source || null };
}

function bookTargets(p) {
  return PICK ? [...PICK.book.keys()].filter((k) => k.startsWith(`${p}:`)) : [];
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
  if (sectionId === "landing") { maybeShowRelease(); refreshResumeRooms(); }
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

// ---------------------------------------------------------------- 返回進行中的對局
// 瀏覽器記得的房間(gash-room-<房號>)中,伺服器上仍在、尚未結束的列在首頁;不存在的移除記錄
let resumeGen = 0;
async function refreshResumeRooms() {
  const gen = ++resumeGen;
  const box = document.getElementById("landing-resume");
  const codes = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("gash-room-")) codes.push(key.slice("gash-room-".length));
    }
  } catch (_) { /* 無法讀取:不顯示 */ }
  const found = await Promise.all(codes.map(async (code) => {
    let saved;
    try { saved = loadSession(code); } catch (_) { return null; }
    if (!saved || !saved.tokens) return null;
    const token = saved.mode === "local" ? Object.values(saved.tokens)[0] : saved.tokens.me;
    try {
      const body = await api(`/api/rooms/${code}/state`, { headers: { "X-Player-Token": token } });
      if (body.state && body.state.phase === "game_over") return null;
      return { code, saved, body };
    } catch (_) {
      try { localStorage.removeItem(`gash-room-${code}`); } catch (__) { /* 忽略 */ }
      return null;
    }
  }));
  if (gen !== resumeGen) return;                      // 期間又進了一次首頁:以後來的為準
  const items = found.filter(Boolean);
  box.classList.toggle("hidden", !items.length);
  box.querySelector(".resume-title").textContent = t("ui.resume.title");
  box.querySelector(".resume-list").replaceChildren(...items.map(({ code, saved, body }) => {
    const btn = document.createElement("button");
    btn.className = "resume-item";
    btn.dataset.code = code;
    const room = body.room || {};
    const names = room.names || [];
    const me = saved.viewer === 0 || saved.viewer === 1 ? saved.viewer : null;
    const opp = me === null ? null : names[1 - me] || t(saved.mode === "npc" ? "ui.resume.npc" : "ui.resume.opponent");
    const status = room.started && body.state ? t("ui.turn", { n: body.state.turn_no }) : t("ui.resume.waiting");
    const parts = [t(`ui.landing.${saved.mode === "online" ? "friend" : saved.mode}`)];
    if (opp && saved.mode !== "local") parts.push(t("ui.resume.vs", { name: opp }));
    parts.push(t("ui.resume.code", { code }), status);
    btn.textContent = parts.join(t("ui.sep.bar"));
    btn.onclick = () => {
      history.replaceState(null, "", `/?room=${code}`);
      resumeRoom(code);
    };
    return btn;
  }));
}

// 頂欄標題字:回到首頁(在房間中等同離開房間,對局仍可從首頁返回)
function goHome() {
  if (SESSION) { leaveRoom(); return; }
  history.replaceState(null, "", "/");
  renderLanding();
  show("landing");
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
  const bits = [];   // 魔力與費用只以徽章呈現(見下),資訊列不重複
  const cost = valueChange(def.cost, opts.cost, true);
  const power = def.power && valueChange(def.power.base, opts.power, false);
  // 魔力徽章的數值:魔物(與固定魔力的戰術)為魔力,戰術為魔力加值「+N」或「特殊」
  const powerText = power ? String(power.value)
    : def.power && def.power.bonus !== undefined ? `+${def.power.bonus}`
    : def.power && def.power.special ? t("ui.power_special") : null;
  if (def.damage) bits.push(t("ui.damage", { n: def.damage }));
  else if (def.damage_variable) bits.push(t("ui.damage", { n: "?" }));   // 卡面「ダメージ?」:傷害依效果決定
  if (def.ad) bits.push(def.ad);
  bits.forEach((b, i) => meta.append(...(i ? [t("ui.sep.meta"), b] : [b])));
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

  // 魔力與費用一律以角落徽章呈現(所有卡面;缺卡圖時也是);傳入目前數值時與卡面不同依有利 / 不利著色
  if (cost) {    // 費用:只寫數值,蓋在卡圖原本的費用格上
    const vb = document.createElement("span");
    vb.className = "val-badge val-cost" + (cost.cls ? ` ${cost.cls}` : "");
    vb.textContent = String(cost.value);
    el.appendChild(vb);
  }
  if (powerText) {   // 魔力:卡名下方(左下角);標籤只在放大檢視顯示(兩行),小卡面只寫數值
    const vb = document.createElement("span");
    vb.className = "val-badge val-power" + (power && power.cls ? ` ${power.cls}` : "");
    const label = document.createElement("span");
    label.className = "val-label";
    label.textContent = t("ui.power_label");
    const num = document.createElement("span");
    num.className = "val-num";
    num.textContent = powerText;
    vb.append(label, num);
    el.appendChild(vb);
    el.classList.add("has-power");   // 放大檢視為兩行徽章預留底部空間
  }

  const numEl = document.createElement("div");
  numEl.className = "cnum";
  numEl.textContent = num;
  el.appendChild(numEl);   // 卡號放在徽章之後:放大檢視以它為詳情內容的最後一項

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

// 卡面數值與目前數值:{value, cls};cls 為 val-good / val-bad(對持有者有利 / 不利)或 null。卡面沒有此數值時 null。
// lowerIsGood:費用低於卡面為有利;魔力相反
function valueChange(base, current, lowerIsGood) {
  if (base === null || base === undefined) return null;
  const value = current !== undefined && current !== null ? current : base;
  if (value === base) return { value, cls: null };
  return { value, cls: (value < base) === lowerIsGood ? "val-good" : "val-bad" };
}

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

// 放大檢視的數值明細與失效中的效果:數值與卡面不同時列明細(格式同魔力勝負明細);沒有可列的內容時 null
function zoomDetails(num, ctx) {
  const ps = S && S.players[ctx.p];
  if (!ps) return null;
  const def = CARDS[num] || {};
  const sections = [];
  const breakdown = (title, items) => infoSection(title, items.map((i) => infoRow(
    t(`breakdown.${i.kind}`, { card: i.source ? cname(i.source) : "" }), i.source ? [i.source] : [],
    BREAKDOWN_BASE.has(i.kind) ? String(i.amount) : signed(i.amount), "info-amount")), "");
  const slot = ctx.kind === "slot" || ctx.kind === "partner" ? ps.slots.find((x) => x.uid === ctx.uid) : null;
  if (ctx.kind === "slot" && slot && slot.top === num && def.power && slot.power !== def.power.base
      && slot.power_breakdown) {
    sections.push(breakdown(t("ui.zoom.power_detail", { n: slot.power }), slot.power_breakdown));
  }
  const entry = ctx.kind === "page" ? ps.open_pages.find((e) => e.page === ctx.page)
    : ctx.kind === "any_page" ? (ps.any_page_spells || []).find((e) => e.page === ctx.page) : null;
  if (entry && entry.cost_breakdown && entry.cost !== def.cost) {
    sections.push(breakdown(t("ui.zoom.cost_detail", { n: entry.cost }), entry.cost_breakdown));
  }
  const blocked = slot ? (slot.blocked_effects || []).filter((b) => b.card === num) : [];
  if (blocked.length) {
    sections.push(infoSection(t("ui.effect_blocked.title"), blocked.map((b) => infoRow(
      t("ui.effect_blocked.item", { card: cname(b.card), by: b.by.map((n) => `《${cname(n)}》`).join(t("ui.sep.list")) }),
      [b.card, ...b.by], "", "")), ""));
  }
  if (!sections.length) return null;
  const box = document.createElement("div");
  box.className = "zoom-details";
  box.onclick = (ev) => ev.stopPropagation();
  box.append(...sections);
  return box;
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
    if (ZOOM.ctx.kind === "any_page") {
      const entry = (S.players[ZOOM.ctx.p].any_page_spells || []).find((e) => e.page === ZOOM.ctx.page);
      if (entry) opts.cost = entry.cost;
    }
    if (ZOOM.ctx.kind === "slot") {
      const zs = S.players[ZOOM.ctx.p].slots.find((x) => x.uid === ZOOM.ctx.uid);
      if (zs && zs.top === ZOOM.num) opts.power = zs.power;
    }
  }

  opts.fullName = true;
  const card = cardEl(ZOOM.num, opts);
  card.onclick = (ev) => ev.stopPropagation();  // 點卡面不關閉、不重開
  holder.appendChild(card);

  // 疊放中的魔物:列出疊在下方的卡(由上而下),點了改為純展示並可返回
  const slot = ZOOM.ctx && ZOOM.ctx.kind === "slot"
    ? S.players[ZOOM.ctx.p].slots.find((x) => x.uid === ZOOM.ctx.uid) : null;
  if (slot && slot.stack && slot.stack.length > 1) {
    const box = document.createElement("div");
    box.className = "zoom-stack";
    box.onclick = (ev) => ev.stopPropagation();
    const head = document.createElement("div");
    head.className = "zoom-stack-title";
    head.textContent = t("ui.stack_under");
    const row = document.createElement("div");
    row.className = "zoom-stack-cards";
    const back = { num: ZOOM.num, ctx: ZOOM.ctx };
    for (const num of slot.stack.slice(0, -1).reverse()) {
      const el = cardEl(num, { small: true });
      el.dataset.card = num;
      el.onclick = (ev) => { ev.stopPropagation(); ZOOM = { num, ctx: null, back }; renderZoom(); };
      row.appendChild(el);
    }
    box.append(head, row);
    actions.appendChild(box);
  }
  const details = ZOOM.ctx && ZOOM.num ? zoomDetails(ZOOM.num, ZOOM.ctx) : null;
  if (details) actions.appendChild(details);
  if (ZOOM.back) {
    const prev = ZOOM.back;
    buttons = [...buttons, { label: t("ui.back"), onclick: () => zoom(prev.num, prev.ctx), keepOpen: true }];
  }

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
      btn.onclick = (ev) => { ev.stopPropagation(); if (!b.keepOpen) closeZoom(); b.onclick(); };
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
  if ((ps.used_nonbattle_pages || []).includes(entry.page)) return { ok: false, reason: t("ui.used") };   // 以頁計,同名的另一頁仍可用
  if (entry.condition_ok === false) return { ok: false, reason: t("ui.condition") };   // 例如選不到對象
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
// 搭檔卡的裝備對象:快照的 targets(引擎依家族判定,M-047 視為ガッシュ・ベル),UI 不自行比對對應
function pickPartnerTarget(p, entry, cb) {
  const free = entry.targets || [];
  if (free.length <= 1) { if (free.length) cb(free[0]); return; }
  startLocalPick({
    player: p, title: t("choice.title.pick_mamodo_for_partner"), source: entry.card, onpick: cb,
    options: new Map(free.map((uid) => [uid, { selectable: true }])),
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
  renderTurnDial();
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
    active: 0, selected: [null, null], ...newPoolFilters(), busy: false, applied: false };
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
  // 雙方目前翻開的頁(依對局狀態,不受草稿修改影響)
  document.getElementById("cheat-current").textContent = [0, 1].map((p) => t("ui.cheat.current_pages",
    { player: pname(p), a: S.players[p].pos, b: S.players[p].pos + 1 })).join(t("ui.sep.bar"));
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
  const ps = S.players[player];
  renderBookGrid(grid, (i) => cheatMark(i + 1, ps, bookPageSlotEl(i, pages, selected, {
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
  })));
}

// 金手指網格:目前翻開的兩頁與已離開魔書的頁
function cheatMark(page, ps, el) {
  if (page === ps.pos || page === ps.pos + 1) {
    el.classList.add("cheat-open");
    el.appendChild(Object.assign(document.createElement("span"), { className: "cheat-tag", textContent: t("ui.cheat.open_tag") }));
  } else if ((ps.consumed_pages || []).includes(page)) {
    el.classList.add("cheat-gone");
    el.appendChild(Object.assign(document.createElement("span"), { className: "cheat-tag", textContent: t("ui.cheat.gone_tag") }));
  }
  return el;
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
  document.getElementById("title").setAttribute("aria-label", `${t("app.title")} — ${t("ui.resume.home")}`);
  document.getElementById("title").title = t("ui.resume.home");
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
  // 依快照的欄位排列(魔物離場後那一欄留空,其他魔物不移動);沒有欄位時退回清單順序
  const byColumn = [];
  ps.slots.forEach((s, i) => { byColumn[Number.isInteger(s.column) ? s.column : i] = s; });
  for (let i = 0; i < Math.max(FIELD_COLUMNS, byColumn.length); i++) {
    const slot = byColumn[i];
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
// 例外:進行中的「從魔書挑頁」決策的目標頁(與魔書網格相同:發光、點開按「選擇」;空頁點卡背即選),
// 以及待命允許從魔書任意頁使用的戰術頁(P-015,放大檢視提供「攻擊」)
function browsedPageEl(p, ps, pg) {
  const target = PICK && PICK.book.get(`${p}:${pg}`);
  if ((ps.consumed_pages || []).includes(pg)) {
    const back = cardBackEl(pg, true);
    if (target) {
      back.classList.add("pickable");
      back.onclick = () => choosePick(target.value);
    }
    return back;
  }
  const usable = (ps.any_page_spells || []).some((e) => e.page === pg);
  const zoomCtx = target ? { kind: "pick", zone: "book", p, page: pg }
    : usable ? { kind: "any_page", p, page: pg } : undefined;
  const el = cardEl(ps.book[pg - 1], { zoomCtx });
  if (target || usable) el.classList.add("pickable");
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
    const usable = abilityUsableNow(p, ab, slot.ability_used);
    buttons.push({
      label, disabled: !usable.ok, reason: usable.reason,
      onclick: () => send({ type: "use_field_ability", player: p, zone: "mamodo", slot_uid: slot.uid }),
    });
  }
  // 無戰術攻擊(M-027 バルトロ〈裝甲〉):回合玩家、非戰鬥、非決策時可宣告
  if (slot.mamodo_attack && iControl(p) && p === S.turn_player && canActNow(p)) {
    const spec = slot.mamodo_attack;
    const blocked = usedReason(slot.mamodo_attack_used)
      || (S.players[p].mp < spec.mp_cost ? `MP < ${spec.mp_cost}` : null);
    buttons.push({
      label: t("ui.mamodo_attack", { power: spec.power, dam: spec.damage }),
      primary: true, disabled: !!blocked, reason: blocked,
      onclick: () => send({ type: "declare_attack", player: p, mode: "mamodo", slot_uid: slot.uid }),
    });
  }
  // 魔物效果防禦(M-039):防禦宣告時,防方可不用戰術卡、以這隻魔物防禦
  if (slot.mamodo_defense && iControl(p) && !S.pending && S.battle && S.battle.step === "defense"
      && p === 1 - S.battle.attacker) {
    const spec = slot.mamodo_defense;
    const blocked = S.battle.attack_undefendable ? t("ui.undefendable")
      : usedReason(slot.mamodo_defense_used)
      || (S.players[p].mp < spec.mp_cost ? `MP < ${spec.mp_cost}` : null);
    buttons.push({
      label: t("ui.mamodo_defense", { power: spec.power }),
      primary: true, disabled: !!blocked, reason: blocked,
      onclick: () => send({ type: "declare_defense", player: p, mode: "mamodo", slot_uid: slot.uid }),
    });
  }
  // 「1アクションを使って…捨て札にできる」(M-046):非戰鬥中、輪到自己行動時
  if (slot.action_discard && canActNow(p)) {
    buttons.push({
      label: t("ui.action_discard"),
      onclick: () => send({ type: "use_action_effect", player: p, zone: "mamodo", slot_uid: slot.uid }),
    });
  }
  return buttons;
}

function slotEl(p, slot) {
  const ctx = { kind: "slot", p, uid: slot.uid };
  return markPickable(markUsable(cardEl(slot.top, {
    injured: slot.injured,
    power: slot.power,
    badges: blockedBadges(slot, slot.top),
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
    const usable = abilityUsableNow(p, ab, slot.partner_ability_used);
    buttons.push({
      label, disabled: !usable.ok, reason: usable.reason,
      onclick: () => send({ type: "use_field_ability", player: p, zone: "partner", slot_uid: slot.uid }),
    });
  }
  if (slot.partner_action_discard && canActNow(p)) {   // P-020:1 個行動棄掉
    buttons.push({
      label: t("ui.action_discard"),
      onclick: () => send({ type: "use_action_effect", player: p, zone: "partner", slot_uid: slot.uid }),
    });
  }
  return buttons;
}

function partnerEl(p, slot) {
  const ctx = { kind: "partner", p, uid: slot.uid };
  return markPickable(markUsable(cardEl(slot.partner, { small: true, zoomCtx: ctx,
    badges: blockedBadges(slot, slot.partner) }), ctx), ctx);
}

// 常駐效果失效中(快照 blocked_effects):卡上的「失效」標記
function blockedBadges(slot, num) {
  return (slot.blocked_effects || []).some((b) => b.card === num)
    ? [{ cls: "blocked-mark", text: t("ui.effect_blocked.badge") }] : [];
}

// 效果已使用(快照的 *_used:"turn" 本回合已用、"game" 一場限 1 次已用)時的停用原因;未使用回傳 null
function usedReason(used) {
  return used === "game" ? t("ui.ability.used_game") : used ? t("ui.ability.used_turn") : null;
}

function abilityUsableNow(p, ab, used) {
  if (usedReason(used)) return { ok: false, reason: usedReason(used) };
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
      // 能不能放出依快照的 play_block(與指令同一判斷);搭檔的裝備對象兩隻以上時由玩家選
      const blocked = entry.play_block ? t(`error.play.${entry.play_block}`) : null;
      buttons.push({
        label: t("ui.play"), primary: true, disabled: !!blocked, reason: blocked,
        onclick: () => (def.type === "partner"
          ? pickPartnerTarget(p, entry, (uid) => send({ type: "play_card", player: p, page: entry.page, slot_uid: uid }))
          : send({ type: "play_card", player: p, page: entry.page })),
      });
    } else if (def.type === "event") {
      const ps = S.players[p];
      const cost = entry.cost !== undefined ? entry.cost : (def.cost || 0);   // 快照的費用含 M-040 的加成
      const blocked = ps.events_exhausted ? t("ui.used")
        : entry.condition_ok === false ? t("ui.condition")
        : cost > ps.mp ? `MP < ${cost}`
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
// 無戰術攻擊時代替戰術呈現的固定魔力來源卡(魔力明細中 kind 為 fixed 的來源;與魔物本身相同時不另列)。
// 對決舞台與魔力對決對峙演出共用
function fixedPowerSource(breakdown, mamodo) {
  const fixed = (breakdown || []).find((i) => i.kind === "fixed");
  return fixed && fixed.source && fixed.source !== mamodo ? fixed.source : null;
}

// 對決舞台一方的縮小卡面:魔物+戰術(無戰術攻擊為固定魔力來源卡),點擊開純展示放大檢視;被無效時加標記
function stageCards(player, slotUid, spell, breakdown, negated) {
  const box = document.createElement("div");
  box.className = "stage-cards";
  const slot = S.players[player].slots.find((s) => s.uid === slotUid);
  const mamodo = slot ? slot.top : null;
  if (!spell) spell = fixedPowerSource(breakdown, mamodo);
  for (const num of [mamodo, spell]) {
    if (!num) continue;
    const cell = document.createElement("div");
    cell.className = "stage-card";
    cell.dataset.card = num;
    cell.appendChild(cardEl(num));
    cell.onclick = (ev) => { ev.stopPropagation(); zoom(num); };
    box.appendChild(cell);
  }
  if (negated) {
    const mark = document.createElement("span");
    mark.className = "stage-negated";
    mark.textContent = t("anim.showdown.negated");
    box.appendChild(mark);
  }
  return box;
}

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

// 回合轉盤(行動欄左端,取代摘要文字):外圈「回合玩家」箭頭指向回合玩家那一側(下方 0°、上方 180°);
// 非戰鬥中已 pass 一次順時鐘多轉 45°,表示再 pass 就換人。角度累計保存:轉回時反向 45°,其餘一律順時鐘轉到目標。
// 右側「行動玩家」箭頭指向等待輸入的一方。轉盤元素常駐(不隨行動欄重建),旋轉才有動畫。
let dialAngle = null;
let dialRoom = null;

function renderTurnDial() {
  const cluster = document.getElementById("turn-cluster");
  const timing = currentTiming();
  cluster.classList.toggle("hidden", timing === "over");
  if (timing === "over") return;
  const dial = document.getElementById("turn-dial");
  const tilted = (timing === "nonbattle" || timing === "end") && S.consecutive_passes >= 1;
  const target = (topPlayerIndex() === S.turn_player ? 180 : 0) + (tilted ? 45 : 0);
  const room = SESSION && SESSION.code;
  const instant = dialAngle === null || dialRoom !== room;
  if (instant) {
    dialAngle = target;
  } else {
    const cur = ((dialAngle % 360) + 360) % 360;
    if (target === (cur + 315) % 360) dialAngle -= 45;               // 有人行動:轉回
    else dialAngle += (target - cur + 360) % 360;                    // 順時鐘前進
  }
  dialRoom = room;
  dial.classList.toggle("instant", instant);
  dial.dataset.angle = dialAngle;
  dial.style.setProperty("--dial-angle", `${dialAngle}deg`);
  dial.querySelector(".dial-tab-text").textContent = t("ui.turn_dial.label");
  dial.querySelector(".dial-tab").classList.toggle("up", topPlayerIndex() === S.turn_player);
  const center = dial.querySelector(".dial-center");
  const phase = IN_BATTLE_STEPS.includes(timing) ? "battle" : timing;   // start / nonbattle / battle / end
  center.textContent = t(`ui.turn_dial.${phase}`);
  center.dataset.phase = phase;

  const awaited = awaitedPlayer();
  const pointer = document.getElementById("acting-pointer");
  pointer.querySelector(".pointer-text").textContent = t("ui.turn_dial.acting");
  pointer.classList.toggle("up", awaited !== null && topPlayerIndex() === awaited);
  pointer.classList.toggle("hidden", awaited === null);
  cluster.setAttribute("aria-label", awaited === null ? "" : actionSummary(awaited, timing));

  const note = document.getElementById("dial-note");               // 傾斜時的固定小字提示(不隨外圈旋轉)
  const me = selfPlayer();                                            // 下一個回合是誰的,依觀看者稱呼
  note.textContent = me === null ? t("ui.turn_dial.one_pass.named", { player: pname(1 - S.turn_player) })
    : t(S.turn_player === me ? "ui.turn_dial.one_pass.opp" : "ui.turn_dial.one_pass.mine");
  note.classList.toggle("hidden", !(tilted && timing === "nonbattle"));
  if (instant) {
    void dial.offsetWidth;                                           // 先套用角度再恢復動畫
    dial.classList.remove("instant");
  }
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
    const att = document.createElement("div");
    att.className = "stage-side attack";
    att.appendChild(stageCards(bi.attacker, bi.slot, bi.spell || null, null, false));
    content.appendChild(att);
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
  att.appendChild(stageCards(b.attacker, b.attack_slot, b.attack_spell, b.attacker_breakdown, b.attack_negated));
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
  // 防禦方:宣告前「等待防禦宣告」、不防禦時「不防禦」;魔物效果防禦(M-039)沒有戰術,以魔物名呈現
  const defender = 1 - b.attacker;
  const negatedNote = b.defense_negated ? `(${t("ui.negated")})` : "";
  def.appendChild(b.defense_spell
    ? mkLabel("side-label",
        t("ui.battle_defense", { player: pname(defender), spell: cname(b.defense_spell) }) + negatedNote,
        [b.defense_spell])
    : b.defense_slot
      ? mkLabel("side-label", t("ui.battle_defense_mamodo", { player: pname(defender),
          mamodo: attackerName(defender, b.defense_slot) }) + negatedNote)
      : mkLabel("side-label", t(b.step === "defense" ? "ui.battle_no_defense_yet" : "anim.showdown.no_defense")));
  const defTotal = document.createElement("span");
  defTotal.className = "side-total";
  defTotal.id = "stage-def-total";
  defTotal.textContent = b.defender_total;
  defTotal.onclick = () => showBreakdown({ ...b, live: true });
  def.appendChild(defTotal);
  if (b.defense_slot) def.appendChild(stageCards(defender, b.defense_slot, b.defense_spell, null, b.defense_negated));
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

// 行動欄摘要(回合轉盤的 aria-label):輪到誰、誰的回合、目前的時機。可操作的一方以「你」稱呼(本機與觀戰以名稱)
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
  const outer = document.getElementById("action-bar");
  const bar = document.getElementById("action-main");   // 左端的回合轉盤常駐,只重建右側內容
  bar.innerHTML = "";
  outer.classList.remove("mine");
  if (!S || S.phase === "game_over") return;
  const timing = currentTiming();
  const awaited = awaitedPlayer();
  const mine = awaited !== null && iControl(awaited);
  outer.classList.toggle("mine", mine);              // 輪到自己:行動欄醒目
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
  const addBtn = (label, onclick, primary, note) => {
    const btn = document.createElement("button");
    if (note) {                                        // 兩行:上行按鈕名稱,下行小字附註
      const main = document.createElement("span");
      main.className = "btn-label";
      main.textContent = label;
      const sub = document.createElement("span");
      sub.className = "btn-note";
      sub.textContent = note;
      btn.classList.add("noted");
      btn.append(main, sub);
    } else {
      btn.textContent = label;
    }
    if (primary) btn.classList.add("primary");
    btn.onclick = onclick;
    bar.appendChild(btn);
  };

  if (mine && !S.pending) {
    if (timing === "start") {
      // 依魔書翻閱到的對頁決定翻幾張:目前頁 = 不翻頁,往後第 n 個對頁 = 翻 n 張;不對應時只給提示
      const tp = S.turn_player;
      const pos = S.players[tp].pos;
      const maxFlip = Math.min(3, Math.floor((32 - pos) / 2));
      const n = ((bookBrowsable(tp) ? browseStart(tp) : null) ?? pos) - pos;
      const count = n / 2;
      if (count >= 0 && count <= maxFlip) {
        addBtn(count === 0 ? t("ui.flip_0") : t("ui.flip_n", { n: count, mp: 2 * count }),
          () => send({ type: "flip_pages", player: tp, count }), true);
      } else {
        const hint = document.createElement("span");
        hint.className = "flip-hint";
        hint.textContent = t("ui.flip_browse_hint", { max: maxFlip });
        bar.appendChild(hint);
      }
    } else if (timing === "battle_in") {
      addBtn(t("ui.allow_battle"),
        () => send({ type: "battle_in_response", player: awaited, allow: true }), true, t("ui.allow_battle_note"));
    } else if (timing === "defense") {
      addBtn(t("ui.no_defense"), () => send({ type: "no_defense", player: awaited }));
    } else {
      const passNote = timing === "effects" ? "ui.pass_note.battle"
        : awaited === S.turn_player ? "ui.pass_note.own_turn" : "ui.pass_note.opp_turn";
      addBtn(t("ui.pass"), () => send({ type: "pass", player: awaited }), false, t(passNote));
      const borrow = borrowedEffect(awaited);        // E-010:借來的搭檔效果(該搭檔離場也在)
      if (borrow) {
        addBtn(t("ui.borrowed_effect", { card: cname(borrow.card) }),
          () => zoom(borrow.card, { kind: "borrowed", p: awaited }));
      }
      // P-015:待命允許從魔書任意頁使用的戰術,在可宣告攻擊時從魔書網格使用
      const anyPage = S.players[awaited].any_page_spells || [];
      if (anyPage.length && awaited === S.turn_player && !S.battle && !S.battle_in) {
        if (anyPage.length === 1) {
          addBtn(t("ui.any_page_spell", { card: cname(anyPage[0].card) }), () => showBookReview(awaited));
        } else {   // M-037:範圍內有多張可用時,每一頁各一個按鈕,直接開該頁的放大檢視
          for (const entry of anyPage) {
            addBtn(t("ui.any_page_spell_page", { card: cname(entry.card), page: entry.page }),
              () => zoom(entry.card, { kind: "any_page", p: awaited, page: entry.page }));
          }
        }
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
    if (opt.label === "end_review") pick.books.add(opt.player);   // 結束檢視:另給開啟對手魔書的按鈕
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
    case "opp_reflip": {
      const face = results[opt.value] ? t(`ui.coin_face.${results[opt.value]}`) : "";
      return t("choice.opp_reflip", { n: opt.value + 1, face });
    }
    case "pay_reflip": return t("choice.pay_reflip");
    case "stop": return t("choice.stop");
    case "skip": return t("choice.skip");
    case "jammer_use": return t(opt.discard ? "choice.jammer_use.discard" : "choice.jammer_use", { card: cname(opt.card) });
    case "set_heads": return t("choice.set_heads", { n: opt.coin + 1 });
    case "end_phase_effect": return t("choice.end_phase_effect", { card: cname(opt.card) });
    case "spell_discount_use": return t("choice.spell_discount_use");
    case "s043_fuse": return t("choice.s043_fuse");
    case "s043_split": return t("choice.s043_split");
    case "heal_injured": return t("choice.heal_injured");
    case "gain_mp_2": return t("choice.gain_mp_2");
    case "extra_cost": return opt.amount ? t("choice.extra_cost", { amount: opt.amount, power: opt.power, damage: opt.damage })
      : t("choice.extra_cost_none");
    case "damage_book": return t("choice.damage_book");
    case "damage_mamodo": return t("choice.damage_mamodo");
    case "end_review": return t("choice.end_review");
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

function protectDamageText(d) {
  if (d.kind === "book") {
    const text = t("choice.protect_damage.book", { player: pname(d.player), amount: d.amount });
    return d.lethal ? text + t("choice.protect_damage.lethal") : text;
  }
  const slot = S.players[d.player]?.slots.find((s) => s.uid === d.slot);
  const name = slot ? cname(slot.top) : "";
  return t(d.injured ? "choice.protect_damage.slot_injured" : "choice.protect_damage.slot", { card: name });
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
  const damage = pd.info && pd.info.damage;   // 保護決策:目前這份傷害
  if (damage) {
    const note = document.createElement("div");
    note.className = "choice-notes choice-damage";
    note.textContent = protectDamageText(damage);
    box.appendChild(note);
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
  const addBtn = (label, onclick, primary, note) => {
    const btn = document.createElement("button");
    if (note) {                                        // 兩行:上行按鈕名稱,下行小字附註
      const main = document.createElement("span");
      main.className = "btn-label";
      main.textContent = label;
      const sub = document.createElement("span");
      sub.className = "btn-note";
      sub.textContent = note;
      btn.classList.add("noted");
      btn.append(main, sub);
    } else {
      btn.textContent = label;
    }
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

const BREAKDOWN_BASE = new Set(["mamodo", "spell", "fixed", "card"]);   // 基礎值不帶正負號(card 為卡面費用)

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
  if (e.copy_card && DICT[`${key}.copy`] !== undefined) key += ".copy";    // M-035 魔力等於選定的魔物
  if (DICT[key] === undefined) return (TEXT[e.source] && TEXT[e.source].effect) || e.source;
  const changes = [];
  if (e.power_delta) changes.push(t("effect.piece.power", { n: signed(e.power_delta) }));
  if (e.cost_delta) changes.push(t("effect.piece.cost", { n: signed(e.cost_delta) }));
  if (e.optional) changes.push(t("effect.piece.optional"));
  return t(key, { target: effectTarget(e), amount: signed(e.amount || 0),
    mamodo: e.mamodo ? mamodoName(e.mamodo) : t("effect.any_mamodo"),
    card: e.card ? cname(e.card) : "", changes: changes.join(t("ui.sep.list")),
    attr: e.attr ? t(`attr.${e.attr}`) : "", page: e.page ?? "",
    value: e.value ?? 0, copy: e.copy_card ? cname(e.copy_card) : "", turn: e.turn ?? "",
    min_total: e.min_total ?? "", count: e.count ?? "" });
}

// 時效:「至下回合結束」「下一回合」依建立回合相對於目前回合換算
function effectWhen(e) {
  if (e.type === "standby") return t(`effect.expires.${e.expires}`);
  if (e.type === "static") return t("effect.duration.while_on_field");   // P-031 等場上的常駐禁止
  const later = e.created_turn === S.turn_no;
  if (e.duration === "until_end_next_turn" || e.duration === "next_turn") {
    return t(later ? `effect.duration.${e.duration}` : "effect.duration.turn");
  }
  if (e.duration === "until_end_own_next_turn") {   // S-075:建立回合、下一回合、再下一回合依序縮短
    const passed = S.turn_no - e.created_turn;
    return t(passed <= 0 ? "effect.duration.until_end_own_next_turn"
      : passed === 1 ? "effect.duration.until_end_next_turn" : "effect.duration.turn");
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

// 以百分比裁出卡圖上的 [x, y, w, h] 範圍(規則頁圖示、卡池篩選的類型徽章與魔物圖示共用)
function artCrop(card, [x, y, w, h], cls = "icon-crop") {
  const crop = el("span", cls);
  crop.style.backgroundImage = `url(${artUrl(card)})`;
  crop.style.aspectRatio = `${w} / ${h}`;
  crop.style.backgroundSize = `${(ART_W / w) * 100}% auto`;
  crop.style.backgroundPosition = `${(x / (ART_W - w)) * 100}% ${(y / (ART_H - h)) * 100}%`;
  return crop;
}

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
      slot.replaceChildren(artCrop(card, [x, y, w, h]));
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
  const hint = pickHint(p, "discard");            // 決策目標:另以決策標題與來源卡提示要選什麼
  showDialog(pname(p) + t("ui.sep.meta") + t("ui.discard", { n: ps.discard.length }),
    ps.discard.length
      ? ps.discard.map((num, index) => {
        const ctx = { kind: "pick", zone: "discard", p, index };   // 決策目標:放大檢視提供「選擇」
        const target = pickValue(ctx) !== undefined;
        return { cardNum: num, pickable: target, onpick: () => zoom(num, target ? ctx : undefined) };
      })
      : [{ label: t("ui.close"), onpick: () => {} }],
    hint ? hint.source : null, hint ? [hint.title] : []);
}

// 查閱魔書:對頁網格呈現 32 頁,標示當前翻開 / 已離場 / 已用戰術頁。
// 決策目標在魔書中時,可選頁發光,點了在放大檢視選擇;對手的魔書只有選項中的頁有卡面,其他頁為卡背
let BOOK_VIEW = null;   // 開啟中的魔書網格屬於哪位玩家

function showBookReview(p) {
  const ps = S.players[p];
  const targets = bookTargets(p);
  const revealed = ps.book ? null : revealedBook(p);   // 檢視對手魔書:整本卡面
  const overlay = document.getElementById("book-review-overlay");
  if (!ps.book && !targets.length && !revealed) { closeBookReview(); return; }
  // 開啟時捲到當前翻開的對頁;開啟期間的重繪保留玩家捲動的位置
  const box = document.getElementById("book-review");
  const keepScroll = BOOK_VIEW === p ? box.scrollTop : null;
  BOOK_VIEW = p;
  document.getElementById("book-review-title").textContent =
    ps.book && iControl(p) ? t("ui.book_review_title")
      : revealed ? t(targets.length ? "ui.book_revealed_title" : "ui.book_revealed_none", { player: pname(p) })
        : pname(p) + t("ui.book");
  const hint = pickHint(p, "book");               // 除了發光,也寫出這次要選什麼
  const hintEl = document.getElementById("book-review-hint");
  hintEl.textContent = !hint ? ""
    : hint.source ? t("ui.pick_hint_with_source", { title: hint.title, card: cname(hint.source) }) : hint.title;
  hintEl.classList.toggle("hidden", !hint);
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
    const num = ps.book ? ps.book[pg - 1] : target ? target.card : revealed && revealed.get(pg);
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
    case "restrictions_removed":
      return ev.sources && ev.sources.length
        ? t("log.restrictions_removed", { ...P, cards: ev.sources.map((n) => `《${cname(n)}》`).join(t("ui.sep.list")) })
        : t("log.restrictions_removed_none", P);
    case "mp_reduction_prevented": return t("log.mp_reduction_prevented", { ...P, source: cname(ev.source) || ev.source });
    case "mp_gain_prevented": return t("log.mp_gain_prevented", { ...P, source: cname(ev.source) || ev.source });
    case "opp_mp_reduction_restricted": return t("log.opp_mp_reduction_restricted", { ...P, source: cname(ev.source) || ev.source });
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
    case "coin_set": return t("log.coin_set", { ...P, card: cname(ev.card), n: ev.index + 1 });
    case "action_effect_used": return t("log.action_effect_used", { ...P, card: cname(ev.card) });
    case "discard_prevented": return t("log.discard_prevented", { ...P, card: cname(ev.card) });
    case "opponent_pages_swapped": return t("log.opponent_pages_swapped", { ...P, a: ev.pages[0], b: ev.pages[1] });
    case "defense_declared":   // 魔物效果防禦(M-039)沒有戰術
      return ev.spell ? t("log.defense_declared", { ...P, spell: cname(ev.spell) })
        : t("log.mamodo_defense_declared", { ...P, card: cname(ev.mamodo) });
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
      return ev.reason === "no_target" ? t("log.damage_no_target", P)
        : ev.source ? t("log.damage_prevented_by", { ...P, card: cname(ev.source) }) : t("log.damage_prevented", P);
    case "effect_blocked":   // 一次性時點的常駐效果被「使えない」擋下
      return t("log.effect_blocked", { ...P, card: cname(ev.card),
        by: (ev.by || []).map((n) => `《${cname(n)}》`).join(t("ui.sep.list")) });
    case "damage_negated": return t("log.damage_negated", { card: cname(ev.card) });
    case "protected":   // P-027:保護者是對手的魔物時,寫出持有者與被保護的一方
      return ev.target_player !== undefined && ev.target_player !== ev.player
        ? t("log.protected_by_opponent", { player: pname(ev.target_player), owner: pname(ev.player), card: cname(ev.card) })
        : t("log.protected", { ...P, card: cname(ev.card) });
    case "mamodo_injured": return t("log.mamodo_injured", { ...P, card: cname(ev.card) });
    case "mamodo_discarded": return t("log.mamodo_discarded", { ...P, card: cname(ev.cards[ev.cards.length - 1]) });
    case "mamodo_healed": return t("log.mamodo_healed", { ...P, card: cname(ev.card) });
    case "card_discarded": return t("log.card_discarded", { ...P, card: cname(ev.card) });
    case "first_player_set": return t("log.first_player_set", { player: pname(ev.player) });
    case "standby_set":
      return ev.kind === "spell_reuse" && ev.card   // S-098:寫出選定的戰術
        ? t("log.spell_reuse_set", { player: pname(ev.owner), source: cname(ev.source), card: cname(ev.card), page: ev.page })
        : t("log.standby_set", { player: pname(ev.owner), card: cname(ev.source) });
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

let B = null;  // {deck:{id,name,pages[32]}, selected: 頁index|null, 篩選(newPoolFilters)}

function showBuilder() {
  const draft = DeckStore.loadDraft();
  const deck = draft && Array.isArray(draft.pages) && draft.pages.length === 32
    ? draft
    : { id: null, name: t("builder.new"), pages: Array(32).fill(null) };
  B = { deck, selected: null, ...newPoolFilters() };
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
    B.selected = null;                   // 再點選中的頁 → 取消選取(移除改用頁位上的「移除」,避免連點誤刪)
  } else if (B.selected !== null && pages[B.selected]) {
    [pages[B.selected], pages[i]] = [pages[i], pages[B.selected]];  // 移動/互換
    B.selected = null;
  } else {
    B.selected = i;
  }
  builderMutated();
}

function removePage(i) {
  B.deck.pages[i] = null;                // 移除後仍選中這頁,可直接從卡池補卡
  B.selected = i;
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

// 卡池圖示篩選(deck-builder「卡池圖示篩選列」「卡池篩選的選取方式」):類型徽章平鋪(多選),魔物、產品各一顆按鈕展開圖示網格(單選)。
// ftypes 為集合,空集合不篩選;fmamodo / fproduct 為選取的項目,null 不篩選;跨組全部符合。filters.fopen 記目前展開的網格
const POOL_TYPES = ["mamodo", "partner", "spell", "event"];
const TYPE_BADGES = { mamodo: ["M-001", "魔"], partner: ["P-001", "使"], spell: ["S-001", "術"], event: ["E-001", "鍵"] };
const MAMODO_ART = [26, 24, 412, 388];   // 魔物卡的插圖區(卡名列以上),所有魔物卡共用
let FILTER_CFG = { products: [], mamodo: [], mamodo_merge: {} };   // frontend/pool-filters.json:產品分排、魔物順序與合併

function newPoolFilters() {
  return { ftypes: new Set(), fmamodo: null, fproduct: null, fopen: null };
}

// 卡圖裁切的圖示(探測結果有快取,重繪不閃爍)。fallback 為文字時先放文字,卡圖可載入才換成裁切;
// 沒有 fallback 時卡圖無法載入就移除圖示,只留旁邊的文字
function artIcon(card, box, fallback, cls) {
  const holder = el("span", "filter-icon " + cls, fallback || "");
  if (!card) { if (!fallback) holder.remove(); return holder; }
  probeArt(card).then((ok) => {
    if (ok) holder.replaceChildren(artCrop(card, box, "filter-crop"));
    else if (!fallback) holder.remove();
  });
  return holder;
}

function productIcon(code) {
  const holder = el("span", "filter-icon product-icon");
  const img = new Image();
  img.alt = "";
  img.onerror = () => holder.remove();   // 缺圖:只留產品名稱
  img.src = `/static/products/${code}.webp`;
  holder.appendChild(img);
  return holder;
}

// 魔物篩選用的家族:設定檔 mamodo_merge 列出的家族併入目標家族(如金色のガッシュベル → ガッシュ・ベル)
function filterFamily(fam) {
  return (FILTER_CFG.mamodo_merge || {})[fam] || fam;
}

// 魔物名稱去掉括號註記(「ロブノス(分身体)」→「ロブノス」)
function familyLabel(name) {
  return name.replace(/\s*[（(][^（()）]*[）)]\s*$/, "");
}

// 魔物網格的項目:有開放卡片的家族,依設定檔順序,沒列出的依代表卡卡號接在最後;另加「無」(指令戰術)
function mamodoFilterItems() {
  const reps = {};   // 家族 → 代表卡(卡號最小的魔物卡;沒有開放的魔物卡時為 null,只顯示名稱)
  for (const c of openCards()) {
    const fam = filterFamily(c.related_mamodo);
    if (!fam || fam === COMMAND_MAMODO) continue;
    if (!(fam in reps)) reps[fam] = null;
    if (c.type === "mamodo" && (!reps[fam] || c.number < reps[fam])) reps[fam] = c.number;
  }
  const order = FILTER_CFG.mamodo || [];
  const rank = (fam) => (order.includes(fam) ? order.indexOf(fam) : order.length);
  const fams = Object.keys(reps).sort((x, y) => rank(x) - rank(y)
    || (reps[x] || "~").localeCompare(reps[y] || "~"));
  return fams.map((fam) => ({ key: fam, card: reps[fam],
    label: familyLabel(reps[fam] && TEXT[reps[fam]] ? TEXT[reps[fam]].name : fam) }));
}

// 產品網格的各排:依設定檔,只列有開放卡片的產品(再收錄產品不在設定檔中,不列出)
function productFilterRows() {
  const present = new Set(openCards().flatMap((c) => c.sets || []));
  return (FILTER_CFG.products || []).map((row) => row.filter((code) => present.has(code)))
    .filter((row) => row.length);
}

// 只勾「事件」時魔物篩選停用(事件沒有對應魔物),保留選取
function mamodoFilterPaused(filters) {
  return filters.ftypes.size === 1 && filters.ftypes.has("event");
}

function poolCardMatches(def, filters) {
  if (filters.ftypes.size && !filters.ftypes.has(def.type)) return false;
  if (filters.fmamodo && !mamodoFilterPaused(filters)
      && filters.fmamodo !== (isCommandSpell(def) ? MAMODO_NONE : filterFamily(def.related_mamodo))) return false;   // 事件沒有對應魔物,不符合
  if (filters.fproduct && !(def.sets || []).includes(filters.fproduct)) return false;
  return true;
}

function renderCardPoolFilters(holder, filters, onChange) {
  holder.replaceChildren();
  holder.classList.add("pool-filters");
  const bar = el("div", "filter-bar");

  const typeButtons = POOL_TYPES.map((ty) => {
    const [card, mark] = TYPE_BADGES[ty];
    const btn = el("button", "filter-type");
    btn.type = "button";
    btn.dataset.type = ty;
    btn.title = btn.ariaLabel = t("builder.type." + ty);
    btn.append(artIcon(card, ART_BOXES.type.slice(1), mark, "type-icon"),   // 各類型卡的徽章與 M-001 同位置
      el("span", "filter-label", t("builder.type." + ty)));
    btn.onclick = () => {
      if (filters.ftypes.has(ty)) filters.ftypes.delete(ty); else filters.ftypes.add(ty);
      sync(); onChange();
    };
    bar.appendChild(btn);
    return btn;
  });

  const mamodoItems = mamodoFilterItems();
  const productRows = productFilterRows();
  const groups = {
    mamodo: { key: "fmamodo", label: t("builder.filter.mamodo"),
      items: [{ key: MAMODO_NONE, label: t("builder.filter.none"), title: t("builder.filter.none_title") },
        ...mamodoItems] },
    product: { key: "fproduct", label: t("builder.filter.product"),
      items: productRows.flat().map((code) => ({ key: code, label: t("product." + code) })) },
  };
  // 圖示 + 文字;「無」只有文字
  const itemFace = (group, item) => {
    const face = [];
    if (group === "product") face.push(productIcon(item.key));
    else if (item.key !== MAMODO_NONE) face.push(artIcon(item.card, MAMODO_ART, null, "mamodo-icon"));
    face.push(el("span", "filter-caption", item.label));
    return face;
  };
  const choose = (group, key) => {
    filters[groups[group].key] = key;
    filters.fopen = null;
    sync(); onChange();
    menus[group].btn.focus();
  };

  const menus = {};
  for (const group of ["mamodo", "product"]) {
    const g = groups[group];
    const btn = el("button", "filter-menu");
    btn.type = "button";
    btn.dataset.group = group;
    btn.setAttribute("aria-haspopup", "true");
    btn.append(el("span", "filter-menu-label", g.label), el("span", "filter-summary"));
    btn.onclick = () => { filters.fopen = filters.fopen === group ? null : group; sync(); };
    bar.appendChild(btn);

    const panel = el("div", "filter-panel hidden");
    panel.dataset.group = group;
    panel.setAttribute("role", "group");
    panel.ariaLabel = g.label;
    const allBtn = el("button", "filter-tile filter-all", t("builder.filter.all"));
    allBtn.type = "button";
    allBtn.onclick = () => choose(group, null);
    panel.appendChild(allBtn);
    const tiles = {};
    const tileFor = (item) => {
      const tile = el("button", "filter-tile");
      tile.type = "button";
      tile.dataset.key = item.key;
      tile.title = tile.ariaLabel = item.title || item.label;
      tile.append(...itemFace(group, item));
      tile.onclick = () => choose(group, item.key);
      tiles[item.key] = tile;
      return tile;
    };
    if (group === "product") {
      for (const row of productRows) {
        const line = el("div", "filter-row");
        for (const code of row) line.appendChild(tileFor(g.items.find((it) => it.key === code)));
        panel.appendChild(line);
      }
    } else {
      const grid = el("div", "filter-grid");
      for (const item of g.items) grid.appendChild(tileFor(item));
      panel.appendChild(grid);
    }
    menus[group] = { btn, panel, tiles, allBtn };
  }
  holder.append(bar, menus.mamodo.panel, menus.product.panel);

  function sync() {
    for (const btn of typeButtons) btn.setAttribute("aria-pressed", String(filters.ftypes.has(btn.dataset.type)));
    const paused = mamodoFilterPaused(filters);
    if (paused && filters.fopen === "mamodo") filters.fopen = null;
    for (const group of ["mamodo", "product"]) {
      const { btn, panel, tiles, allBtn } = menus[group];
      const g = groups[group];
      const current = filters[g.key];
      const open = filters.fopen === group;
      btn.disabled = group === "mamodo" && paused;
      btn.setAttribute("aria-expanded", String(open));
      panel.classList.toggle("hidden", !open);
      allBtn.setAttribute("aria-pressed", String(!current));
      for (const [key, tile] of Object.entries(tiles)) tile.setAttribute("aria-pressed", String(current === key));
      // 按鈕摘要:未選取為「全部」,否則為選取項目的圖示與名稱
      const summary = btn.querySelector(".filter-summary");
      const picked = g.items.find((item) => item.key === current);
      summary.replaceChildren(...(picked ? itemFace(group, picked) : [t("builder.filter.all")]));
      btn.ariaLabel = `${g.label}: ${picked ? picked.label : t("builder.filter.all")}`;
    }
  }
  sync();

  // 點網格外或 Esc 收起(每個 holder 只掛一組監聽)
  document.removeEventListener("pointerdown", holder._closeFilters, true);
  holder._closeFilters = (ev) => {
    if (filters.fopen && !holder.contains(ev.target)) { filters.fopen = null; sync(); }
  };
  document.addEventListener("pointerdown", holder._closeFilters, true);
  holder.onkeydown = (ev) => {
    if (ev.key !== "Escape" || !filters.fopen) return;
    ev.preventDefault();
    ev.stopPropagation();   // 金手指是 dialog:Esc 只收起網格,不關閉視窗
    const btn = menus[filters.fopen].btn;
    filters.fopen = null;
    sync();
    btn.focus();
  };
}

function renderPool() {
  renderCardPool(document.getElementById("pool-grid"), B, placeCard, { detail: true });
}

// 卡池排序(deck-builder「卡池排序」):依類型 魔物 → 搭檔 → 戰術 → 事件,同類型依卡號
function comparePoolCards(a, b) {
  return POOL_TYPES.indexOf(CARDS[a].type) - POOL_TYPES.indexOf(CARDS[b].type) || a.localeCompare(b);
}

// 魔物篩選的「無」:只留指令戰術
const MAMODO_NONE = "__none__";

function renderCardPool(grid, filters, onPick, opts = {}) {
  grid.innerHTML = "";
  const numbers = openCards().map((c) => c.number).sort(comparePoolCards);
  for (const num of numbers) {
    const def = CARDS[num];
    if (!poolCardMatches(def, filters)) continue;
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
    scope: "builder", enabled: () => true, select: togglePage, swap: swapPages, remove: removePage, detail: true,
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
    if (actions.remove && selected === i) {     // 選中的有卡頁位:明確的移除按鈕
      const rm = document.createElement("button");
      rm.className = "slot-remove";
      rm.textContent = t("builder.remove");
      rm.onclick = (ev) => { ev.stopPropagation(); if (actions.enabled()) actions.remove(i); };
      slot.appendChild(rm);
    }
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
    else if ((ev.key === "Delete" || ev.key === "Backspace") && actions.remove && selected === i && pages[i]
             && actions.enabled()) { ev.preventDefault(); actions.remove(i); }
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
  const title = document.getElementById("title");
  title.onclick = goHome;
  title.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); goHome(); } };
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

// ---------------------------------------------------------------- 維護公告
// 伺服器上的公告檔(GET /api/announcement):載入時與每 2 分鐘查詢,對局中的玩家也看得到;
// 關閉的公告 id 記在瀏覽器,同一則不再顯示,新的 id 再顯示
const ANN_KEY = "gash-announcement-dismissed";
const ANN_POLL_MS = 120000;
let ANNOUNCEMENT = null;

async function refreshAnnouncement() {
  try {
    const r = await fetch("/api/announcement");
    if (!r.ok) return;                                // 查詢失敗:維持目前顯示
    ANNOUNCEMENT = (await r.json()).announcement;
  } catch (_) { return; }
  renderAnnouncement();
}

function renderAnnouncement() {
  const el = document.getElementById("announcement");
  const a = ANNOUNCEMENT;
  let dismissed = null;
  try { dismissed = localStorage.getItem(ANN_KEY); } catch (_) { /* 無法讀取:視為沒關閉過 */ }
  const msg = a && (a.message[LANG] || a.message["zh-TW"] || Object.values(a.message)[0]);
  const visible = !!(a && msg && a.id !== dismissed);
  el.classList.toggle("hidden", !visible);
  if (!visible) return;
  el.querySelector(".ann-text").textContent = msg;   // 純文字
  const close = el.querySelector(".ann-close");
  close.textContent = "×";
  close.title = close.ariaLabel = t("ui.close");
  close.onclick = () => {
    try { localStorage.setItem(ANN_KEY, a.id); } catch (_) { /* 只在本次隱藏 */ }
    el.classList.add("hidden");
  };
}

async function boot() {
  let presets;
  [, CARDS, presets, META] = await Promise.all([
    loadLanguage(),
    fetch("/data/cards.json").then((r) => r.json()).then((list) =>
      Object.fromEntries(list.map((c) => [c.number, c]))),
    fetch("/api/decks").then((r) => r.json()).then((d) => d.decks).catch(() => []),
    fetch("/api/meta").then((r) => r.json()).catch(() => META),
    fetch("/data/pending_cards.json").then((r) => r.json())
      .then((d) => { PENDING = new Set(d.cards || []); }).catch(() => {}),
    fetch("/static/pool-filters.json").then((r) => r.json())
      .then((d) => { FILTER_CFG = d; }).catch(() => {}),
  ]);
  PRESETS = presets && presets.length ? presets : [{ id: DEFAULT_PRESET, name: DEFAULT_PRESET }];
  applyMotionClass();
  renderLanding();
  renderTopbar();
  refreshAnnouncement();
  setInterval(refreshAnnouncement, ANN_POLL_MS);

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
