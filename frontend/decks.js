/* 牌組資料層:localStorage 儲存、七條構築規則驗證、gash1 文字碼匯出/匯入。
 * 純邏輯無 DOM;依賴全域 CARDS(app.js boot 時載入)。
 * 驗證回傳 [{key, params}] 供 i18n 渲染;伺服器 validate_deck 才是最終裁決。 */

"use strict";

const DECKS_KEY = "gash-decks";
const DRAFT_KEY = "gash-deck-draft";
const BOOK_SIZE = 32;
const DECK_CODE_PREFIX = "gash1:";

const DeckStore = {
  list() {
    try {
      return JSON.parse(localStorage.getItem(DECKS_KEY)) || [];
    } catch (_) {
      return [];
    }
  },

  get(id) {
    return this.list().find((d) => d.id === id) || null;
  },

  save(deck) {
    const decks = this.list();
    if (!deck.id) {
      deck.id = "d" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    }
    deck.valid = validateDeckPages(deck.pages).length === 0;
    deck.updated_at = Date.now();
    const i = decks.findIndex((d) => d.id === deck.id);
    if (i >= 0) decks[i] = deck;
    else decks.push(deck);
    localStorage.setItem(DECKS_KEY, JSON.stringify(decks));
    return deck;
  },

  remove(id) {
    localStorage.setItem(DECKS_KEY, JSON.stringify(this.list().filter((d) => d.id !== id)));
  },

  create(name, basePages = null) {
    return this.save({
      id: "d" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      name,
      pages: basePages ? [...basePages] : Array(BOOK_SIZE).fill(null),
    });
  },

  validList() {
    return this.list().filter((d) => d.valid);
  },

  saveDraft(deck) {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(deck));
  },

  loadDraft() {
    try {
      return JSON.parse(localStorage.getItem(DRAFT_KEY));
    } catch (_) {
      return null;
    }
  },
};

/* 七條構築規則(rule3.md「魔本檔案夾」)+ 空頁檢查。pages: [32×卡號|null] */
function validateDeckPages(pages) {
  const errors = [];
  if (!Array.isArray(pages) || pages.length !== BOOK_SIZE) {
    return [{ key: "deck.err.size", params: { n: pages ? pages.length : 0 } }];
  }
  const empty = pages.filter((c) => !c).length;
  if (empty) errors.push({ key: "deck.err.incomplete", params: { n: empty } });

  const unknown = pages.filter((c) => c && !CARDS[c]);
  if (unknown.length) {
    errors.push({ key: "deck.err.unknown", params: { cards: unknown.join(", ") } });
    return errors; // 未知卡號後續規則無法判定
  }
  if (pages[0] && CARDS[pages[0]].type !== "mamodo") {
    errors.push({ key: "deck.err.first_page", params: {} });
  }
  if (pages[31] && CARDS[pages[31]].type !== "spell") {
    errors.push({ key: "deck.err.last_page", params: {} });
  }
  pages.forEach((num, i) => {
    if (!num) return;
    const klass = CARDS[num].class;
    if (klass === "intermediate" && i + 1 < 12) {
      errors.push({ key: "deck.err.intermediate_page", params: { card: num, page: i + 1 } });
    }
    if (klass === "superior" && i + 1 < 22) {
      errors.push({ key: "deck.err.superior_page", params: { card: num, page: i + 1 } });
    }
  });
  const counts = {};
  for (const num of pages) if (num) counts[num] = (counts[num] || 0) + 1;
  for (const [num, n] of Object.entries(counts)) {
    if (n > 4) errors.push({ key: "deck.err.max_copies", params: { card: num, n } });
  }
  const mamodo = pages.filter((c) => c && CARDS[c].type === "mamodo").length;
  if (mamodo > 8) errors.push({ key: "deck.err.max_mamodo", params: { n: mamodo } });
  return errors;
}

function exportDeckCode(pages) {
  return DECK_CODE_PREFIX + pages.map((c) => c || "-").join(",");
}

/* 回傳 {pages} 或 {error: {key, params}} */
function importDeckCode(text) {
  const s = (text || "").trim();
  if (!s.startsWith(DECK_CODE_PREFIX)) {
    return { error: { key: "deck.err.bad_code", params: {} } };
  }
  const parts = s.slice(DECK_CODE_PREFIX.length).split(",").map((x) => x.trim());
  if (parts.length !== BOOK_SIZE) {
    return { error: { key: "deck.err.size", params: { n: parts.length } } };
  }
  const pages = parts.map((x) => (x === "-" || x === "" ? null : x));
  const unknown = pages.filter((c) => c && !CARDS[c]);
  if (unknown.length) {
    return { error: { key: "deck.err.unknown", params: { cards: unknown.join(", ") } } };
  }
  return { pages };
}
