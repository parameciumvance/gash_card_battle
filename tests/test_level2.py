"""Level 2 卡池機制與逐卡效果測試(card-effects / game-engine 差分)。

以自訂魔本(直接指定各頁卡號)驅動,聚焦第二彈新機制:無術攻擊、被動觸發器、
書內/墓地搜卡、變身合體鏈、傷害上限/負傷代替、行為禁止旗標、翻頁每回合一次。
"""

import pytest

from gash.engine.cards import card_db
from gash.engine.engine import IllegalCommand, new_game, submit
from gash.engine.state import BATTLE, GAME_OVER

DB = card_db()


def book(*pages):
    """建立 32 頁魔本:給定前綴頁,其餘以香草填充卡補滿(P1 須為魔物)。"""
    filler = "S-029"  # 香草賈修術(AD),不影響測試
    b = list(pages)
    while len(b) < 32:
        b.append(filler)
    return b[:32]


def mk(book0, book1, seed=0):
    """建立對局,強制玩家 0 先攻(機制單元測試不驗證先攻公平性)。"""
    g = new_game(book0, seed=seed, db=DB, decks=(list(book0), list(book1)))
    g.state.turn_player = 0
    return g, 0


def to_battle(g, tp):
    """回合玩家不翻頁,直接進入戰鬥階段。"""
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    assert g.state.phase == BATTLE


def slot_uid(g, player, top):
    return next(s.uid for s in g.state.players[player].slots if s.top == top)


# ---------------------------------------------------------------- 無術攻擊(M-027 / S-048)

def test_mamodo_attack_full_battle():
    # P1=M-028 巴爾特羅, P2=S-048 傑貝爾, P3=M-027 裝甲
    b0 = book("M-028", "S-048", "M-027")
    b1 = book("M-028")  # 對手也用巴爾特羅當初始魔物
    g, tp = mk(b0, b1)
    if tp != 0:
        # 讓玩家 0 先攻:換 seed
        g, tp = mk(b0, b1, seed=1)
    if tp != 0:
        pytest.skip("seed 未給玩家0先攻")
    g.state.players[0].mp = 10
    to_battle(g, 0)
    # 先用 S-048 疊裝甲(不可防禦、無魔本傷害)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    # S-048 為不可防禦,防方只能不防禦
    submit(g, {"type": "no_defense", "player": 1})
    # 戰鬥中效果雙方 pass
    _pass_effects(g, 0)
    # 裝甲已疊上
    slot = g.state.players[0].slots[0]
    assert slot.top == "M-027" and len(slot.stack) == 2
    # 現在無術攻擊
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo",
               "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.battle.attack_spell is None
    assert g.state.battle.data["attack_fixed_power"] == 5000


def test_plain_mamodo_cannot_mamodo_attack():
    g, tp = mk(book("M-001"), book("M-001"))
    g.state.players[tp].mp = 5
    to_battle(g, tp)
    uid = slot_uid(g, tp, "M-001")
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": tp, "mode": "mamodo", "slot_uid": uid})
    assert e.value.code == "attack.no_mamodo_attack"


def _pass_effects(g, attacker):
    """戰鬥中效果階段雙方 pass 至結算。"""
    b = g.state.battle
    if b is None:
        return
    order = [attacker, 1 - attacker]
    for p in order:
        if g.state.battle and g.state.battle.step == "effects":
            submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})


# ---------------------------------------------------------------- 同名雙隻(M-024)

def test_m024_two_copies_allowed():
    b0 = book("M-024", "M-024", "M-024")  # P2/P3 也是雙體
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    # 場上已有 1 隻(初始);放出第 2 隻(P2)
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert sum(1 for s in g.state.players[0].slots if s.top == "M-024") == 2
    # 放第 3 隻應被拒(同名上限 2)
    submit(g, {"type": "pass", "player": 1})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "play_card", "player": 0, "page": 3})
    assert e.value.code == "play.same_name"


# ---------------------------------------------------------------- 傷害上限(S-032)

def test_s032_damage_cap():
    from gash.engine.effects import registry as reg
    assert reg.SPELL_RIDERS["S-032"].damage_cap == 3
    assert reg.SPELL_RIDERS["S-034"].damage_cap == 4


# ---------------------------------------------------------------- 被動觸發器(P-013)

def test_p013_trigger_on_opponent_discard():
    # 玩家0 有 P-013 可可(裝在佐菲斯上);玩家1 一隻魔物入墓 → 玩家1 被翻 1 頁
    b0 = book("M-022", "P-013")  # P-013 對應佐菲斯
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    submit(g, {"type": "play_card", "player": 0, "page": 2})  # 裝 P-013
    assert g.state.players[0].slots[0].partner == "P-013"
    opp_pos_before = g.state.players[1].pos
    # 直接令玩家1 的魔物入墓,觸發器應翻其書
    from gash.engine.engine import _discard_slot
    batch = []
    _discard_slot(g, batch, 1, g.state.players[1].slots[0], reason="test")
    assert g.state.players[1].pos > opp_pos_before or g.state.phase == GAME_OVER


# ---------------------------------------------------------------- 翻頁每回合一次(P-010)

def test_p010_page_turn_once_per_turn():
    b0 = book("M-001", "P-010")
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    pos0 = g.state.players[0].pos
    submit(g, {"type": "play_card", "player": 0, "page": 2})  # 裝 P-010(優先權轉對手)
    submit(g, {"type": "pass", "player": 1})                  # 對手讓回優先權
    uid = g.state.players[0].slots[0].uid
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": uid})
    assert g.state.players[0].pos == pos0 + 2  # 翻了 1 頁
    assert g.state.players[0].page_effect_used


# ---------------------------------------------------------------- 書內搜卡(M-020 裝搭檔)

def test_m020_attach_partner_from_book():
    # P1=M-020 蒂歐, P5=P-009 大海惠(在後頁,不在翻開頁)
    b0 = book("M-020", "S-029", "S-029", "P-009")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    uid = slot_uid(g, 0, "M-020")
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": uid})
    # 只有 1 張大海惠 → 自動裝上
    assert g.state.players[0].slots[0].partner == "P-009"
    assert 4 in g.state.players[0].consumed_pages  # P4(index的P-009在page4)


# ---------------------------------------------------------------- 負傷代替傷害(S-058)

def test_s058_injure_instead():
    from gash.engine.effects import registry as reg
    assert reg.SPELL_RIDERS["S-058"].injure_instead is True


# ---------------------------------------------------------------- 術相容擴充(M-029 出賈修ザケル)

def test_m029_zaker_compat():
    # M-029 傑洛可用賈修的 S-029 ザケル
    b0 = book("M-029", "S-029")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    # S-029 的 related_mamodo 是 Zatch Bell,但傑洛在場 → 相容
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert g.state.battle_in is not None


# ---------------------------------------------------------------- 事件卡 j 版差異(E-018)

def test_e018_j_version_consecutive_limit():
    # E-018 j 版:上一回合減過對手 MP 則本次不減
    b0 = book("M-001", "E-018")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 5
    g.state.players[1].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[1].mp == 6  # 10 - 4
    # 標記本回合已減
    assert g.state.players[0].__dict__.get("_mp_reduce_turn") == g.state.turn_no


def test_full_regression_level1_deck_still_plays():
    """既有 level1 對局不受影響。"""
    from gash.engine.deck import load_deck
    from gash.engine.cards import DATA_DIR
    pages = load_deck(DATA_DIR / "decks/level1.json", DB).pages
    g = new_game(pages, seed=3, db=DB)
    tp = g.state.turn_player
    submit(g, {"type": "flip_pages", "player": tp, "count": 1})
    assert g.state.phase == BATTLE


# ---------------------------------------------------------------- 整合:無術攻擊造成傷害

def _run_attack_to_damage(g, attacker, defender):
    """防方不防禦、雙方戰鬥中 pass,推進到傷害/庇護決策點。"""
    submit(g, {"type": "no_defense", "player": defender})
    while g.state.battle and g.state.battle.step == "effects" and g.state.pending is None:
        submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})


def test_mamodo_attack_deals_book_damage():
    b0 = book("M-028", "S-048", "M-027")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    # 疊裝甲
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    while g.state.battle and g.state.battle.step == "effects":
        submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    slot = g.state.players[0].slots[0]
    assert slot.top == "M-027"
    pos1 = g.state.players[1].pos
    # 無術攻擊,防方無魔物可庇護魔本(對手只有 1 隻魔物,可庇護)→ 選不庇護
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    while g.state.battle and g.state.battle.step == "effects" and g.state.pending is None:
        submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    # 合計魔力 5000 > 0,攻擊成功 → 進入庇護決策或直接傷害
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})  # 不庇護
    assert g.state.players[1].pos == pos1 + 4  # 傷害 2 → 翻 2 對頁


def test_s058_injure_instead_in_battle():
    # 玩家0 傑洛 + S-058;對手 1 隻魔物 → 攻擊獲勝改為負傷對手魔物
    b0 = book("M-029", "S-058")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    while g.state.battle and g.state.battle.step == "effects" and g.state.pending is None:
        submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    # 對手只有 1 隻魔物 → 自動負傷,無魔本傷害
    assert g.state.players[1].slots[0].injured is True
    assert g.state.players[1].pos == 2  # 魔本未受傷害


def test_no_attack_spell_restriction():
    # 玩家1 用 P-014 禁玩家0 攻擊術(佩利可對應波克利歐)
    b0 = book("M-023", "S-029")  # 波克利歐 + 賈修香草術(相容需 M-023?否)
    # 用 S-023 波克利歐術更準確;此處僅測 restriction 生效
    from gash.engine.state import DUR_TURN, NO_ATTACK_SPELL
    from gash.engine.effects.primitives import add_restriction
    g, tp = mk(book("M-001", "S-029"), book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    batch = []
    add_restriction(g, batch, source="test", owner=1, target_player=0,
                    flag=NO_ATTACK_SPELL, duration=DUR_TURN)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert e.value.code == "spell.attack_restricted"
