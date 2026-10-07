/* 音效 — Web Audio 即時合成,不使用音檔。
 * 事件 → 音效種類(CUES),同一時間點只播最重要的一個(PRIORITY);播放時機由 anim.js 的管線決定。
 * 瀏覽器要求使用者互動後才能出聲:第一次點擊或按鍵時建立 / 恢復 AudioContext,之前的音效靜默略過。
 * 只看演出設定的「音效」(pref("sound")),不受聚焦與動畫設定影響。 */

"use strict";

const Sfx = (() => {
  // 由重到輕;同一時間點只播排在最前面的
  const PRIORITY = ["win", "lose", "damage", "hurt", "block", "heal", "attack", "defense",
    "effect", "card", "coin", "showdown", "page", "pass"];
  const CUES = {
    damage_dealt: "damage",
    mamodo_injured: "hurt",
    mamodo_discarded: "hurt",
    card_discarded: (ev) => (ev.reason === "cost" ? null : "hurt"),
    protected: "block",
    damage_prevented: "block",
    damage_negated: "block",
    attack_negated: "block",
    defense_negated: "block",
    effect_negated: "block",
    mamodo_healed: "heal",
    battle_in_check: "attack",
    defense_declared: "defense",
    book_card_used: "effect",
    ability_used: "effect",
    card_played: "card",
    coin_flipped: (ev) => (ev.source === "setup" ? null : "coin"),
    showdown: "showdown",
    pages_flipped: (ev) => (ev.count ? "page" : null),
    pages_turned: (ev) => (ev.count ? "page" : null),
    passed: "pass",
    no_defense: "pass",
  };
  const played = [];   // 決定播放的音效名稱(測試用)
  let ctx = null;
  let master = null;

  // me:自己(0 / 1);本機與觀戰為 null,對局結束一律為勝利音效
  function cueFor(ev, me) {
    if (ev.type === "game_ended") return me === null || ev.winner === me ? "win" : "lose";
    const cue = CUES[ev.type];
    return typeof cue === "function" ? cue(ev) : cue || null;
  }

  function pick(events, me) {
    let best = null;
    for (const ev of events) {
      const cue = cueFor(ev, me);
      if (cue && (best === null || PRIORITY.indexOf(cue) < PRIORITY.indexOf(best))) best = cue;
    }
    return best;
  }

  function enabled() { return pref("sound") === "on"; }

  // delay:毫秒;回傳是否決定播放
  function play(name, delay = 0) {
    if (!name || !enabled()) return false;
    played.push(name);
    try { synth(name, delay / 1000); } catch (_) { /* 音效失敗不影響對局 */ }
    return true;
  }

  // ---------------------------------------------------------------- AudioContext

  function unlock() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!ctx) {
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = 0.25;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume().catch(() => { /* 仍未允許 */ });
  }
  window.addEventListener("pointerdown", unlock, true);
  window.addEventListener("keydown", unlock, true);

  // ---------------------------------------------------------------- 合成

  // 單音:頻率 f 滑到 f2,快速起音後指數衰減
  function tone(at, { f, f2 = f, dur, type = "sine", gain = 1 }) {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(f, at);
    if (f2 !== f) osc.frequency.exponentialRampToValueAtTime(f2, at + dur);
    env.gain.setValueAtTime(0.0001, at);
    env.gain.exponentialRampToValueAtTime(gain, at + 0.01);
    env.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(env).connect(master);
    osc.start(at);
    osc.stop(at + dur + 0.02);
  }

  // 噪音:帶通濾波的白噪音(翻頁、撞擊)
  function noise(at, { dur, freq, q = 1, gain = 1 }) {
    const len = Math.ceil(ctx.sampleRate * dur);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = freq;
    filter.Q.value = q;
    const env = ctx.createGain();
    env.gain.setValueAtTime(gain, at);
    env.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    src.connect(filter).connect(env).connect(master);
    src.start(at);
  }

  const notes = (at, freqs, step, opts) =>
    freqs.forEach((f, i) => tone(at + i * step, { f, dur: step * 1.8, ...opts }));

  const SOUNDS = {
    card: (at) => { noise(at, { dur: 0.06, freq: 2500, gain: 0.5 }); tone(at, { f: 520, f2: 700, dur: 0.1, type: "triangle", gain: 0.6 }); },
    effect: (at) => notes(at, [1047, 1568], 0.06, { gain: 0.5 }),
    attack: (at) => { tone(at, { f: 240, f2: 90, dur: 0.22, type: "sawtooth", gain: 0.5 }); noise(at, { dur: 0.15, freq: 600, gain: 0.7 }); },
    defense: (at) => { tone(at, { f: 392, dur: 0.18, type: "square", gain: 0.25 }); tone(at, { f: 523, dur: 0.18, type: "triangle", gain: 0.5 }); },
    pass: (at) => tone(at, { f: 440, f2: 400, dur: 0.08, gain: 0.35 }),
    damage: (at) => { tone(at, { f: 170, f2: 55, dur: 0.35, gain: 1 }); noise(at, { dur: 0.18, freq: 300, gain: 0.8 }); },
    hurt: (at) => tone(at, { f: 330, f2: 140, dur: 0.25, type: "square", gain: 0.3 }),
    block: (at) => { tone(at, { f: 1320, dur: 0.25, type: "triangle", gain: 0.5 }); tone(at, { f: 1980, dur: 0.18, gain: 0.3 }); },
    heal: (at) => notes(at, [523, 659, 784], 0.07, { type: "triangle", gain: 0.5 }),
    coin: (at) => { tone(at, { f: 2093, dur: 0.12, gain: 0.35 }); tone(at + 0.07, { f: 2637, dur: 0.18, gain: 0.3 }); },
    showdown: (at) => { tone(at, { f: 196, dur: 0.12, type: "sawtooth", gain: 0.35 }); tone(at + 0.12, { f: 294, dur: 0.3, type: "sawtooth", gain: 0.4 }); },
    page: (at) => noise(at, { dur: 0.14, freq: 1800, q: 0.7, gain: 0.6 }),
    your_turn: (at) => notes(at, [659, 988], 0.12, { gain: 0.8 }),
    win: (at) => notes(at, [523, 659, 784, 1047], 0.11, { type: "triangle", gain: 0.7 }),
    lose: (at) => notes(at, [392, 330, 262], 0.16, { type: "triangle", gain: 0.6 }),
  };

  function synth(name, delay) {
    if (!ctx || ctx.state !== "running" || !SOUNDS[name]) return;   // 尚未允許出聲:靜默略過
    SOUNDS[name](ctx.currentTime + delay);
  }

  return { cueFor, pick, play, played };
})();
