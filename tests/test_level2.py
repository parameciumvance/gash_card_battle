"""Level 2 卡池機制與逐卡效果測試(card-effects / game-engine 差分)。

以自訂魔本(直接指定各頁卡號)驅動,聚焦第二彈新機制:無術攻擊、被動觸發器、
書內/墓地搜卡、變身合體鏈、傷害上限/負傷代替、行為禁止旗標、翻頁每回合一次。
"""

import pytest

from gash.engine.cards import card_db
from gash.engine.engine import IllegalCommand, new_game, submit
from gash.engine.state import BATTLE, GAME_OVER

DB = card_db()


class Rng:
    """腳本化 RNG:random() 依序回傳 seq,之後固定 0.9(反面)。"""

    def __init__(self, *seq):
        self.seq = list(seq)

    def random(self):
        return self.seq.pop(0) if self.seq else 0.9

    def randint(self, a, b):
        return a


HEADS, TAILS = 0.1, 0.9


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
    # 先用 S-048(非戰鬥術)疊裝甲
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
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


# ---------------------------------------------------------------- 書內搜卡(M-021 裝搭檔)

def test_m021_attach_partner_from_book():
    # P1=M-021 海爾, P5=P-011 窪塚泳太(在後頁,不在翻開頁)
    b0 = book("M-021", "S-029", "S-029", "P-011")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    uid = slot_uid(g, 0, "M-021")
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": uid})
    # 只有 1 張窪塚泳太 → 自動裝上
    assert g.state.players[0].slots[0].partner == "P-011"
    assert 4 in g.state.players[0].consumed_pages  # P4(index的P-011在page4)


# ---------------------------------------------------------------- 術相容擴充(M-023 可用木屬性術)

def test_m023_wood_attr_spell_compat():
    # M-023 波克利歐搭配 S-014(スギナ家族、木屬性)攻擊:家族不同但屬性相容
    b0 = book("M-023", "S-014")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.battle.attack_spell == "S-014"


# ---------------------------------------------------------------- 書內任意頁用術(P-015 → S-042)

def test_p015_allows_spell_from_closed_page():
    # P1=M-024 羅布諾斯(分身体), P5=S-042 比萊茲(不在翻開頁 1/2 內)
    b0 = book("M-024", "S-029", "S-029", "S-029", "S-042")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    slot.partner = "P-015"
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": slot.uid})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 5, "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.battle.attack_spell == "S-042"


# ---------------------------------------------------------------- 非戰鬥術(S-026/S-041/S-043/S-048/S-057)

def test_s041_self_immune():
    # P1=M-023 波克利歐(ポッケリオ家族),P2=S-041(擲幣正→自身免疫)
    b0 = book("M-023", "S-041")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS)
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    assert any(m.kind == "full_immune" and m.owner == 0 for m in g.state.modifiers)


def test_s043_fuse_two_doubles_into_complete():
    # P1=M-024(分身体,起始魔物;準備階段已翻開 P2/P3), P6=M-024(第 2 隻), P7=S-043,
    # P8=M-025(完全体,供合體效果自書任意頁取出)
    b0 = book("M-024", "S-029", "S-029", "S-029", "S-029", "M-024", "S-043", "M-025")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    submit(g, {"type": "flip_pages", "player": 0, "count": 2})  # pos=2+4=6, open=[6,7]
    submit(g, {"type": "play_card", "player": 0, "page": 6})  # 放出第 2 隻 M-024
    submit(g, {"type": "pass", "player": 1})
    assert sum(1 for s in g.state.players[0].slots if s.top == "M-024") == 2
    submit(g, {"type": "use_book_card", "player": 0, "page": 7})  # S-043 合體
    if g.state.pending is not None:  # M-025 登場觸發:選一張墓地羅布諾斯放回書空頁
        submit(g, {"type": "choose", "player": 0, "value": g.state.pending.options[0]["value"]})
    submit(g, {"type": "pass", "player": 1})
    assert any(s.top == "M-025" for s in g.state.players[0].slots)
    assert not any(s.top == "M-024" for s in g.state.players[0].slots)


def test_s057_sets_injure_instead_standby():
    # P1=M-001, P2=S-057(コマンド指示術,擲幣正→[待命] 下次攻擊獲勝改為負傷代替傷害)
    b0 = book("M-001", "S-057")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS)
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    assert any(sb.kind == "injure_instead" and sb.owner == 0 for sb in g.state.standby)


@pytest.mark.parametrize("number,page", [
    ("S-026", 2), ("S-041", 2), ("S-043", 2), ("S-048", 2), ("S-057", 2),
])
def test_nonbattle_spell_cannot_declare_attack(number, page):
    b0 = book("M-001", number)
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": page})
    assert e.value.code == "spell.no_attack_icon"


def test_use_book_card_rejects_battle_spell():
    # S-001 是一般戰鬥術(effect_icon 非 nonbattle),不能經 use_book_card 使用
    b0 = book("M-001", "S-001")
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert e.value.code == "spell.not_nonbattle"


def test_nonbattle_spell_wrong_turn_timing():
    # S-041 ad="A"(僅自分のターン)。玩家0先讓出優先權,非回合玩家1即使拿到行動權也不能使用
    b0 = book("M-001", "S-029")
    b1 = book("M-023", "S-041")
    g, tp = mk(b0, b1)
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})  # 優先權轉給玩家1,回合仍是玩家0的
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    assert e.value.code == "spell.timing"


def test_nonbattle_spell_requires_matching_mamodo():
    # 場上沒有ポッケリオ家族魔物,不能使用 S-041
    b0 = book("M-001", "S-041")
    g, tp = mk(b0, book("M-001"))
    to_battle(g, 0)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert e.value.code == "spell.no_mamodo"


def test_nonbattle_spell_insufficient_mp():
    b0 = book("M-023", "S-041")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 0  # S-041 費用 1,MP 不足
    to_battle(g, 0)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert e.value.code == "spell.mp"


def _end_turn(g):
    st = g.state
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})
    submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "pass", "player": st.action_player})


def test_used_nonbattle_spell_blocks_same_turn_reuse():
    # P1=M-023, P2=S-041
    b0 = book("M-023", "S-041")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(TAILS)  # 硬幣結果不影響本測試(僅驗證使用次數限制)
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert e.value.code == "spell.used"
    submit(g, {"type": "pass", "player": 0})  # 連續 2 次 pass,結束玩家 0 回合
    _end_turn(g)  # 結束玩家 1 回合,輪回玩家 0
    # 下回合(輪到自己時)應恢復可用(回合結束的強制翻頁會讓 S-041 離開開啟頁範圍,
    # 故直接驗證使用紀錄已清空,而非重新對同一頁提交指令)
    assert "S-041" not in g.state.players[0].used_nonbattle_spells


# ---------------------------------------------------------------- 傷害管線修正(S-036)

def _resolve_damage_choices(g, receiver, protect_index=None):
    """依序處理 damage_order(固定選第一項)/ protect(依 protect_index 決定庇護對象或不庇護)。"""
    while g.state.pending is not None and g.state.pending.kind in ("damage_order", "protect"):
        pending = g.state.pending
        if pending.kind == "damage_order":
            submit(g, {"type": "choose", "player": receiver, "value": 0})
        else:
            value = pending.options[protect_index]["value"] if protect_index is not None else None
            submit(g, {"type": "choose", "player": receiver, "value": value})


def test_s036_damages_book_and_all_mamodo():
    # 玩家0 用 M-005(布拉哥) + S-036;對手 1 隻魔物(不庇護),魔本+魔物皆應受傷害
    from gash.engine.state import MamodoSlot
    b0 = book("M-005", "S-036")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    to_battle(g, 0)
    pos1 = opp.pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    _resolve_damage_choices(g, 1, protect_index=None)
    assert opp.pos == pos1 + 2 * 3  # S-036 傷害 3
    assert all(s.injured for s in opp.slots)


def test_s036_damage_can_be_protected():
    # 對手有 2 隻魔物,庇護其中一份魔物傷害
    from gash.engine.state import MamodoSlot
    b0 = book("M-005", "S-036")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    opp.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-001"]))
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    # 遇到第一個 protect 詢問時選擇庇護(用另一隻魔物頂替)
    protected_once = False
    while g.state.pending is not None and g.state.pending.kind in ("damage_order", "protect"):
        pending = g.state.pending
        if pending.kind == "damage_order":
            submit(g, {"type": "choose", "player": 1, "value": 0})
        elif not protected_once and len(pending.options) > 1:
            submit(g, {"type": "choose", "player": 1, "value": pending.options[1]["value"]})
            protected_once = True
        else:
            submit(g, {"type": "choose", "player": 1, "value": None})
    assert protected_once
    # 庇護後:恰有一隻魔物因為頂替而額外受傷,但不因此變成兩隻皆負傷又都入墓
    assert any(not s.injured for s in opp.slots) or len(opp.slots) < 2


def test_s036_damage_negated_by_p006():
    # 防方 M-010(變身後コルル)裝 P-006,待命無效 1 次傷害
    b0 = book("M-005", "S-036")
    g, tp = mk(b0, book("M-009"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    kolulu = opp.slots[0]
    kolulu.stack.append("M-010")
    kolulu.partner = "P-006"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})  # 讓出優先權給玩家1
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": kolulu.uid})
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    _resolve_damage_choices(g, 1, protect_index=None)
    assert not kolulu.injured  # P-006 無效了這份傷害


def test_s036_damage_blocked_by_no_damage_modifier():
    # 防方魔物有作用中的 no_damage modifier(比照 M-013/M-015),S-036 對其傷害被阻擋
    from gash.engine.effects.primitives import add_modifier
    from gash.engine.state import DUR_BATTLE
    b0 = book("M-005", "S-036")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    to_battle(g, 0)
    add_modifier(g, [], kind="no_damage", source="test", owner=1,
                duration=DUR_BATTLE, target_player=1, target_slot=opp.slots[0].uid)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    _resolve_damage_choices(g, 1, protect_index=None)
    assert not opp.slots[0].injured


# ---------------------------------------------------------------- 負傷代替傷害(S-058)

def test_s058_injure_instead():
    from gash.engine.effects import registry as reg
    assert reg.SPELL_RIDERS["S-058"].injure_instead is True


# ---------------------------------------------------------------- 新增實作(S-042/S-045/S-046)

def test_s042_damage_bonus_at_8000_power():
    from gash.engine.effects.primitives import add_power
    from gash.engine.state import DUR_BATTLE
    b0 = book("M-024", "S-042")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    add_power(g, [], source="test", owner=0, target_player=0, target_slot=slot.uid,
             amount=2000, duration=DUR_BATTLE)  # 3000(M-024)+3000(S-042)+2000=8000
    pos1 = g.state.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert g.state.players[1].pos == pos1 + 2 * 3  # 基礎傷害 1 + 2 = 3


def test_s042_no_bonus_below_8000_power():
    b0 = book("M-024", "S-042")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    pos1 = g.state.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert g.state.players[1].pos == pos1 + 2 * 1  # 合計 6000 < 8000,傷害維持 1


def test_s045_two_heads_undefendable():
    b0 = book("M-026", "S-045")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS, HEADS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert e.value.code == "defense.undefendable"


def test_s045_not_both_heads_still_defendable():
    b0 = book("M-026", "S-045")
    b1 = book("M-001", "S-001")
    g, tp = mk(b0, b1)
    g.rng = Rng(HEADS, TAILS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})  # 不被拒


def test_s046_one_head_undefendable():
    b0 = book("M-026", "S-046")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert e.value.code == "defense.undefendable"


def test_s046_tails_still_defendable():
    b0 = book("M-026", "S-046")
    b1 = book("M-001", "S-001")
    g, tp = mk(b0, b1)
    g.rng = Rng(TAILS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})  # 不被拒


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
    # 疊裝甲(S-048 非戰鬥術)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
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
