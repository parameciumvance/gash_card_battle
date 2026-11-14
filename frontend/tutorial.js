// 教學對局(tutorial):步驟表、鎖定、目標發光、教學面板與對手節奏。
// 與 app.js 共用全域(S、SESSION、t、send、api…),只在執行時呼叫,所以可以先於 app.js 載入。
// 玩家固定是座位 0、先攻;對手(座位 1)由伺服器的腳本操作,玩家每送出一個指令後暫停,
// 由這裡呼叫 /tutorial/continue 放行(tutorial「對手腳本的節奏」)。

const TUTORIAL_ME = 0;
const TUTORIAL_OPP = 1;
const TUTORIAL_STEP_KEY = "gash-tutorial-step";
const TUTORIAL_DONE_KEY = "gash-tutorial-done";
let TUTORIAL = null;   // {step, seen: {事件種類: 次數}(這一步開始後), acted, continuedSeq, scrolled}
let TUTORIAL_COLLAPSED = false;   // 教學面板收合(窄螢幕上讓出盤面);換步驟時自動展開

function isTutorial() { return !!(SESSION && SESSION.mode === "tutorial"); }

function tutorialDone() {
  try { return localStorage.getItem(TUTORIAL_DONE_KEY) === "1"; } catch (_) { return false; }
}

// ---------------------------------------------------------------- 步驟表

const tMe = () => S.players[TUTORIAL_ME];
const tOpenCard = (num) => (tMe().open_pages || []).find((e) => e.card === num);
const tSeen = (type) => (TUTORIAL.seen[type] || 0) > 0;
const tCalm = () => !S.pending && !S.battle && !S.battle_in;
const tBarButton = (key) => [...document.querySelectorAll("#action-bar button")]
  .find((b) => b.textContent.includes(t(key)));
const tPageEl = (num) => {
  const e = tOpenCard(num);
  return e ? document.querySelector(`.book-block[data-book-block="${TUTORIAL_ME}"] .book-pages [data-page="${e.page}"]`) : null;
};
const tSlotEl = (top, zone) => {
  const slot = tMe().slots.find((s) => s.top === top);
  return slot ? document.querySelector(`[data-slot-uid="${slot.uid}"][data-zone-kind="${zone}"]`) : null;
};

// 每一步:
//   next:顯示「下一步」(說明步驟;按下後才完成,並放行對手)
//   action(cmd):鎖定時要求的操作;做到之前其他指令不送出(tutorial「教學步驟的鎖定」)
//   done():依快照與這一步開始後的事件判斷完成(步驟只往前)
//   target():要發光的元素
const TUTORIAL_STEPS = [
  { id: 1, next: true },
  { id: 2, action: (c) => c.type === "flip_pages" && c.count === 0,
    done: () => S.phase === "battle", target: () => tBarButton("ui.flip_0") },
  { id: 3, action: (c) => c.type === "play_card" && tMe().book[c.page - 1] === "P-001",
    done: () => tMe().slots.some((s) => s.partner === "P-001"), target: () => tPageEl("P-001") },
  { id: 4, next: true },
  { id: 5, action: (c) => c.type === "use_field_ability" && c.zone === "partner",
    done: () => tSeen("ability_used"), target: () => tSlotEl("M-001", "partner") },
  { id: 6, action: (c) => c.type === "declare_attack",
    done: () => tSeen("battle_ended") && tCalm(), target: () => (S.battle ? tBarButton("ui.pass") : tPageEl("S-001")) },
  { id: 7, done: () => S.turn_player === TUTORIAL_OPP, target: () => tBarButton("ui.pass") },
  { id: 8, action: (c) => c.type === "play_card" && tMe().book[c.page - 1] === "Ex-005",
    done: () => tMe().slots.some((s) => s.top === "Ex-005"), target: () => (S.battle_in ? tPageEl("Ex-005") : null) },
  { id: 9, action: (c) => c.type === "battle_in_response",
    done: () => !!(S.battle && S.battle.step === "defense") || tSeen("battle_started"),
    target: () => tBarButton("ui.allow_battle") },
  { id: 10, action: (c) => c.type === "declare_defense",
    done: () => tSeen("battle_ended") && tCalm(), target: () => (S.battle && S.battle.step === "defense" ? tPageEl("S-022") : tBarButton("ui.pass")) },
  { id: 11, done: () => tSeen("coin_flipped") && tCalm() },
  { id: 12, done: () => S.turn_player === TUTORIAL_ME, target: () => tBarButton("ui.pass") },
  { id: 13, action: (c) => c.type === "flip_pages" && c.count >= 1,
    done: () => S.phase === "battle", target: () => document.querySelector(`.book-block[data-book-block="${TUTORIAL_ME}"] .book-next`) },
  { id: 14, action: (c) => c.type === "use_book_card" && tMe().book[c.page - 1] === "E-003",
    done: () => tSeen("book_card_used"), target: () => tPageEl("E-003") },
  { id: 15, action: (c) => c.type === "declare_attack",
    done: () => !!(S.battle && S.battle.step === "effects" && S.battle.defense_spell), target: () => tPageEl("S-001") },
  { id: 16, action: (c) => c.type === "use_field_ability" && c.zone === "mamodo",
    done: () => tSeen("battle_ended") && tCalm(),
    target: () => (TUTORIAL.acted ? tBarButton("ui.pass") : tSlotEl("M-001", "mamodo")) },
  { id: 17, final: true },
];

function tutorialStep() { return TUTORIAL ? TUTORIAL_STEPS[TUTORIAL.step] : null; }

function saveTutorialStep() {
  try { sessionStorage.setItem(TUTORIAL_STEP_KEY, JSON.stringify({ code: SESSION.code, step: TUTORIAL.step })); } catch (_) { /* 忽略 */ }
}

function enterTutorialStep(index) {
  TUTORIAL.step = index;
  TUTORIAL.seen = {};
  TUTORIAL.acted = false;
  TUTORIAL_COLLAPSED = false;
  saveTutorialStep();
  if (tutorialStep().final) {
    try { localStorage.setItem(TUTORIAL_DONE_KEY, "1"); } catch (_) { /* 寫不進去就當沒完成 */ }
  }
}

// ---------------------------------------------------------------- 開始、恢復、離開

async function startTutorial() {
  try {
    const body = await api("/api/rooms", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "tutorial" }),
    });
    SESSION = { code: body.code, mode: "tutorial", viewer: TUTORIAL_ME, tokens: { me: body.player_token } };
    saveSession();
    TUTORIAL = { step: 0, seen: {}, acted: false, continuedSeq: -1 };
    saveTutorialStep();
    history.replaceState(null, "", `/?room=${body.code}`);
    resetLog();
    applyPayload(body);
    show("layout");
    openWS();
  } catch (err) {
    toast(t("ui.error", { msg: err.message }));
  }
}

// 重新整理後恢復目前步驟(同一分頁)
function resumeTutorial() {
  let saved = null;
  try { saved = JSON.parse(sessionStorage.getItem(TUTORIAL_STEP_KEY) || "null"); } catch (_) { /* 忽略 */ }
  TUTORIAL = { step: saved && saved.code === SESSION.code ? saved.step : 0, seen: {}, acted: false, continuedSeq: -1 };
}

async function leaveTutorial(then) {
  const code = SESSION && SESSION.code;
  const token = SESSION && SESSION.tokens.me;
  TUTORIAL = null;
  try { sessionStorage.removeItem(TUTORIAL_STEP_KEY); } catch (_) { /* 忽略 */ }
  if (code) {
    try {
      await api(`/api/rooms/${code}/close`, { method: "POST", headers: { "X-Player-Token": token } });
    } catch (_) { /* 房間已不存在:照樣離開 */ }
  }
  document.getElementById("tutorial-panel").classList.add("hidden");
  leaveRoom();
  renderLanding();
  if (then) then();
}

// ---------------------------------------------------------------- 狀態更新、鎖定、對手放行

// applyPayload 之後呼叫:累計這一步開始後的事件,完成的步驟往前推進
function tutorialUpdate(fresh) {
  if (!isTutorial() || !S) return;
  if (!TUTORIAL) resumeTutorial();
  for (const ev of fresh) TUTORIAL.seen[ev.type] = (TUTORIAL.seen[ev.type] || 0) + 1;
  let step = tutorialStep();
  while (!step.next && !step.final && step.done && step.done()) {
    enterTutorialStep(TUTORIAL.step + 1);
    step = tutorialStep();
  }
  tutorialRelease();
}

// 輪到對手、這一步不是等玩家讀完的說明時,放行對手(每個盤面只放行一次)
function tutorialRelease(force) {
  if (!isTutorial() || !S || awaitedPlayer() !== TUTORIAL_OPP) return;
  if (!force && tutorialStep().next) return;
  const seq = logSeq;
  if (!force && TUTORIAL.continuedSeq === seq) return;
  TUTORIAL.continuedSeq = seq;
  api(`/api/rooms/${SESSION.code}/tutorial/continue`, { method: "POST", headers: { "X-Player-Token": SESSION.tokens.me } })
    .catch(() => { /* 房間已關閉等:忽略 */ });
}

// send() 開頭呼叫:鎖定中、不是要求的操作時不送出,提示這一步該做什麼
function tutorialAllows(command) {
  if (!isTutorial() || !TUTORIAL) return true;
  const step = tutorialStep();
  if (!step.action || TUTORIAL.acted) return true;
  if (step.action(command)) { TUTORIAL.acted = true; return true; }
  tutorialNudge();
  return false;
}

function tutorialNudge() {
  const panel = document.getElementById("tutorial-panel");
  panel.classList.remove("nudge");
  void panel.offsetWidth;   // 重新觸發動畫
  panel.classList.add("nudge");
  toast(t(`tutorial.lock.${tutorialStep().id}`, tNames()));
}

function tutorialNext() {
  const step = tutorialStep();
  if (!step || !step.next) return;
  enterTutorialStep(TUTORIAL.step + 1);
  tutorialUpdate([]);
  tutorialRelease(true);
  render();
}

// ---------------------------------------------------------------- 教學面板

// 說明中的卡名依各語言的卡片文字檔
function tNames() {
  return { gash: cname("M-001"), kiyo: cname("P-001"), zaker: cname("S-001"), tio: cname("Ex-005"),
    seoshi: cname("S-022"), buri: cname("E-003"), hyde: cname("M-021"), jikir: cname("S-037"),
    discard_btn: t("ui.ability_discard"), mp_btn: t("ui.ability_mp", { n: 1 }) };
}

function tutorialText(step) {
  // 回合 2 不保護而魔書受了傷害時,目前的對頁已經是ブリ與ザケル(傷害也會翻魔書)
  const key = step.id === 13 && (tOpenCard("E-003") || tOpenCard("S-001")) ? "tutorial.step.13_damaged"
    : `tutorial.step.${step.id}`;
  return t(key, tNames()).split("\n");
}

function renderTutorial() {
  const panel = document.getElementById("tutorial-panel");
  document.querySelectorAll(".tutorial-target").forEach((el) => el.classList.remove("tutorial-target"));
  if (!isTutorial() || !S || !TUTORIAL) { panel.classList.add("hidden"); return; }
  const step = tutorialStep();
  panel.classList.remove("hidden");
  panel.style.bottom = `${document.getElementById("action-bar").offsetHeight}px`;   // 貼在行動欄上方
  panel.innerHTML = "";
  const head = document.createElement("div");
  head.className = "tutorial-head";
  const title = document.createElement("span");
  title.className = "tutorial-progress";
  title.textContent = t("tutorial.progress", { n: step.id, total: TUTORIAL_STEPS.length });
  const fold = document.createElement("button");
  fold.className = "tutorial-fold";
  fold.textContent = t(TUTORIAL_COLLAPSED ? "tutorial.expand" : "tutorial.collapse");
  fold.onclick = () => { TUTORIAL_COLLAPSED = !TUTORIAL_COLLAPSED; renderTutorial(); };
  const leave = document.createElement("button");
  leave.className = "tutorial-leave";
  leave.textContent = t("tutorial.leave");
  leave.onclick = () => leaveTutorial();
  head.append(title, fold, leave);
  panel.appendChild(head);
  panel.classList.toggle("collapsed", TUTORIAL_COLLAPSED);
  for (const line of TUTORIAL_COLLAPSED ? [] : tutorialText(step)) {
    const p = document.createElement("p");
    p.className = "tutorial-text";
    p.textContent = line;
    panel.appendChild(p);
  }
  const actions = document.createElement("div");
  actions.className = "tutorial-actions";
  const btn = (key, onclick, primary) => {
    const b = document.createElement("button");
    b.textContent = t(key);
    if (primary) b.className = "primary";
    b.onclick = onclick;
    actions.appendChild(b);
  };
  if (step.next) btn("tutorial.next", tutorialNext, true);
  if (step.final) {
    btn("tutorial.rules", () => openRules());
    btn("tutorial.to_npc", () => leaveTutorial(() => openSetup("npc")), true);
    btn("tutorial.home", () => leaveTutorial());
  }
  if (actions.children.length) panel.appendChild(actions);
  const target = step.target && step.target();
  if (!target) return;
  target.classList.add("tutorial-target");
  // 換步驟(或目標換了)時把目標捲到畫面中央:窄螢幕上目標可能被教學面板與行動欄蓋住
  const key = `${TUTORIAL.step}:${target.dataset.page || target.dataset.slotUid || target.textContent}`;
  if (TUTORIAL.scrolled !== key) {
    TUTORIAL.scrolled = key;
    target.scrollIntoView({ block: "center", inline: "nearest" });
  }
}
