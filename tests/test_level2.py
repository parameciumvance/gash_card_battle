"""Level 2 卡池機制與逐卡效果測試(card-effects / game-engine 差分)。

以自訂魔本(直接指定各頁卡號)驅動,聚焦第二彈新機制:無術攻擊、被動觸發器、
書內/墓地搜卡、變身合體鏈、傷害上限/負傷代替、行為禁止旗標、翻頁每回合一次。
"""

import pytest

from gash.engine.cards import card_db
from gash.engine.engine import IllegalCommand, new_game, side_breakdown, submit
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
    assert g.state.pending.kind == "pick_card_in_own_discard"   # M-025 登場:可選擇把墓地羅布諾斯放回魔本空頁
    submit(g, {"type": "choose", "player": 0, "value": None})   # 不使用
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
    assert g.state.pending is None          # 擲出正面時不詢問是否使用(宣告使用即表示意願)
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
    """依序處理 damage_order(固定選第一項)/ protect(依 protect_index 決定保護對象或不保護)。"""
    while g.state.pending is not None and g.state.pending.kind in ("damage_order", "protect"):
        pending = g.state.pending
        if pending.kind == "damage_order":
            submit(g, {"type": "choose", "player": receiver, "value": 0})
        else:
            value = pending.options[protect_index]["value"] if protect_index is not None else None
            submit(g, {"type": "choose", "player": receiver, "value": value})


def test_s036_damages_book_and_all_mamodo():
    # 玩家0 用 M-005(布拉哥) + S-036;對手 1 隻魔物(不保護),魔本+魔物皆應受傷害
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
    # 對手有 2 隻魔物,保護其中一份魔物傷害
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
    # 遇到第一個 protect 詢問時選擇保護(用另一隻魔物頂替)
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
    # 保護後:恰有一隻魔物因為頂替而額外受傷,但不因此變成兩隻皆負傷又都入墓
    assert any(not s.injured for s in opp.slots) or len(opp.slots) < 2


def test_s036_protector_discarded_own_damage_item_skipped():
    # 對手 A(健康)、B(已負傷)。B 頂替 A 的傷害後因已負傷而入墓,
    # B 自己那份原始傷害此時目標已不存在,應直接作廢,不得再詢問是否保護
    from gash.engine.state import MamodoSlot
    b0 = book("M-005", "S-036")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    a_slot = opp.slots[0]
    b_slot = MamodoSlot(uid=g.state.next_uid(), stack=["M-001"], injured=True)
    opp.slots.append(b_slot)
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    events = submit(g, {"type": "pass", "player": 1})

    pending = g.state.pending
    assert pending.kind == "damage_order"
    a_index = next(o["index"] for o in pending.options
                  if o["item"]["kind"] == "slot" and o["item"]["slot_uid"] == a_slot.uid)
    events += submit(g, {"type": "choose", "player": 1, "value": a_index})

    pending = g.state.pending
    assert pending.kind == "protect"
    assert pending.data["ctx"]["items"][0]["slot_uid"] == a_slot.uid
    events += submit(g, {"type": "choose", "player": 1, "value": b_slot.uid})  # 用 B 頂替 A
    assert b_slot not in opp.slots  # B 已負傷,頂替後直接入墓

    # 剩餘流程走到底(book 傷害若詢問保護一律選不保護),收集全部事件
    while g.state.pending is not None:
        pending = g.state.pending
        if pending.kind == "protect":
            events += submit(g, {"type": "choose", "player": 1, "value": None})
        else:
            raise AssertionError(f"未預期的 pending: {pending.kind}")

    protect_targets = [e.get("item", {}).get("slot_uid") for e in events
                       if e["type"] == "choice_required" and e["kind"] == "protect"]
    assert b_slot.uid not in protect_targets  # 從未針對 B 已消失的那份傷害詢問保護
    assert any(e["type"] == "damage_prevented" and e.get("slot") == b_slot.uid
              and e.get("reason") == "no_target" for e in events)
    assert not a_slot.injured  # A 的傷害被 B 頂替,A 本身未受傷


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
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    # P-006 帶「バトル」圖示:在戰鬥中使用
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": kolulu.uid})
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


def _attack_until_damage(g, page=2):
    """玩家 0 以第 page 頁的術攻擊,對手不防禦,雙方 pass 到傷害階段。"""
    submit(g, {"type": "declare_attack", "player": 0, "page": page})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})


def test_s030_counter_damages_attacker_book():
    b0 = book("M-001", "S-029")
    b1 = book("M-001", "S-030")
    g, tp = mk(b0, b1)
    g.state.players[0].mp = 10
    g.state.players[1].mp = 10
    to_battle(g, 0)
    pos0 = g.state.players[0].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    # 反擊:防方獲勝時對攻方魔本造成傷害(攻方可保護)
    assert g.state.pending is not None and g.state.pending.kind == "protect"
    assert g.state.pending.player == 0
    submit(g, {"type": "choose", "player": 0, "value": None})
    assert g.state.players[0].pos == pos0 + 2 * 1


def test_s031_protecting_mamodo_goes_to_discard():
    b0 = book("M-001", "S-031")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    protector = g.state.players[1].slots[0]
    _attack_until_damage(g)
    assert g.state.pending.kind == "protect"
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})  # 以魔物保護魔本
    assert protector not in g.state.players[1].slots          # 直接入墓,不是負傷
    assert "M-001" in g.state.players[1].discard


def test_s033_weakens_all_opponent_mamodo_after_damage():
    from gash.engine.state import MamodoSlot
    b0 = book("M-005", "S-033")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    opp = g.state.players[1]
    opp.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-002"]))
    to_battle(g, 0)
    _attack_until_damage(g)
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    mods = [m for m in g.state.modifiers if m.source == "S-033"]
    assert sorted(m.target_slot for m in mods) == sorted(s.uid for s in opp.slots)
    assert all(m.kind == "power" and m.amount == -2000 and m.owner == 0
               and m.target_player == 1 for m in mods)


def test_s038_full_immune_after_damage():
    b0 = book("M-021", "S-038")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    _attack_until_damage(g)
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert any(m.kind == "full_immune" and m.owner == 0 and m.target_player == 0
               for m in g.state.modifiers)


def test_s039_discards_opponent_partner_after_damage():
    b0 = book("M-022", "S-039")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    target = g.state.players[1].slots[0]
    target.partner = "P-001"
    to_battle(g, 0)
    _attack_until_damage(g)
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert target.partner is None                 # 唯一目標自動棄掉
    assert "P-001" in g.state.players[1].discard


def test_s039_no_partner_no_effect():
    b0 = book("M-022", "S-039")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    _attack_until_damage(g)
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert g.state.pending is None


def _s056_battle(defender_bonus=0):
    """玩家 0 以 S-029 攻擊;玩家 1 以 S-056(指示術,MP 0)防禦,雙方 pass 到魔力勝負。"""
    from gash.engine.effects.primitives import add_power
    from gash.engine.state import DUR_TURN
    g, tp = mk(book("M-001", "S-029"), book("M-001", "S-056"))
    g.state.players[0].mp = 10
    g.state.players[1].mp = 0
    if defender_bonus:
        d = g.state.players[1].slots[0]
        add_power(g, [], source="test", owner=1, target_player=1, target_slot=d.uid,
                  amount=defender_bonus, duration=DUR_TURN)
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2,
               "slot_uid": g.state.players[1].slots[0].uid})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    return g


def test_s056_defender_damaged_gains_mp_per_page():
    g = _s056_battle()                          # 4000+3000 > 4000+0 → 攻方勝
    pos1 = g.state.players[1].pos
    assert g.state.pending is not None and g.state.pending.kind == "protect"
    submit(g, {"type": "choose", "player": 1, "value": None})   # 不保護,魔本受傷
    pages = (g.state.players[1].pos - pos1) // 2
    assert pages > 0
    assert g.state.players[1].mp == 2 * pages


def test_s056_defense_wins_no_damage_no_mp():
    g = _s056_battle(defender_bonus=5000)      # 4000+3000 < 9000+0 → 防方勝,攻擊無效
    assert g.state.pending is None and g.state.battle is None   # 戰鬥已結束,沒有傷害
    assert g.state.players[1].mp == 0


def test_e012_stacks_transformed_mamodo_onto_base():
    # 場上 M-006(ゴフレ),魔本有 M-007(變身後,疊放於 M-006)→ E-012 唯一目標自動疊放
    b0 = book("M-006", "E-012", "S-029", "S-029", "S-029", "S-029", "S-029", "S-029", "M-007")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    base = g.state.players[0].slots[0]
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert base.stack == ["M-006", "M-007"]
    assert 9 in g.state.players[0].consumed_pages
    played = [e for e in events if e["type"] == "card_played" and e["card"] == "M-007"]
    assert played and played[0].get("stacked") is True


def test_e016_reveal_opponent_book_discard_spell_pay_cost():
    b0 = book("M-001", "E-016")
    b1 = book("M-001", "S-001", "S-002")
    g, tp = mk(b0, b1)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert any(e["type"] == "book_revealed" and e["viewer"] == 0 for e in events)
    pend = g.state.pending
    assert pend.kind == "pick_opponent_book_card"
    pages = [o["value"] for o in pend.options]
    assert 1 not in pages and 32 not in pages and 3 in pages   # 魔物、末頁除外
    mp = g.state.players[0].mp
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "choose", "player": 0, "value": 1})   # 魔物頁不合法
    submit(g, {"type": "choose", "player": 0, "value": 3})
    assert 3 in g.state.players[1].consumed_pages
    assert "S-002" in g.state.players[1].discard
    assert g.state.players[0].mp == mp - DB["S-002"].cost


def test_e017_single_event_auto_discard_pay_cost():
    b0 = book("M-001", "E-017")
    b1 = book("M-001", "E-003")
    g, tp = mk(b0, b1)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    mp_before_use = g.state.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending is None                              # 唯一事件卡自動選
    assert "E-003" in g.state.players[1].discard
    assert g.state.players[0].mp == mp_before_use - DB["E-017"].cost - DB["E-003"].cost


def test_s043_split_complete_into_two_doubles():
    b0 = book("M-025", "S-043", "M-024", "M-024")
    g, tp = mk(b0, book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    assert g.state.pending is None
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})   # 無二體可融合 → 唯一選項「分裂」
    tops = [s.top for s in g.state.players[0].slots]
    assert tops.count("M-024") == 2 and "M-025" not in tops
    assert {3, 4} <= g.state.players[0].consumed_pages
    assert "M-025" in g.state.players[0].discard


def test_s035_two_heads_no_protect():
    b0 = book("M-005", "S-035")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS, HEADS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    pos1 = g.state.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert g.state.pending is None  # 2 正 → 不能保護,傷害直接生效
    assert g.state.players[1].pos == pos1 + 2 * 3


def test_s035_not_both_heads_can_still_protect():
    b0 = book("M-005", "S-035")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS, TAILS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert g.state.pending is not None and g.state.pending.kind == "protect"


def test_s037_full_immune_after_damage():
    b0 = book("M-021", "S-037")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS)
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert any(m.kind == "full_immune" and m.owner == 0 for m in g.state.modifiers)


def test_s040_bonus_scales_with_heads():
    b0 = book("M-023", "S-040")
    g, tp = mk(b0, book("M-001"))
    g.rng = Rng(HEADS, HEADS, TAILS)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _, items = side_breakdown(g, g.state.battle, "attack")
    assert {"kind": "spell_bonus", "source": "S-040", "amount": 4000} in items   # 2 正 × 2000


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


@pytest.mark.parametrize("spell,allowed", [
    ("S-001", True), ("S-002", True), ("S-029", True),   # 賈修的「ザケル」
    ("S-005", False), ("S-031", False),                   # 「バオウ・ザケルガ」不是「ザケル」
])
def test_m029_can_use_only_gash_spell_named_zakeru(spell, allowed):
    # 效果文:自分は、この魔物で「ガッシュ・ベル」の術「ザケル」を使える
    g, tp = mk(book("M-029", spell), book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    if allowed:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2})
        assert g.state.battle_in is not None
    else:
        with pytest.raises(IllegalCommand) as e:
            submit(g, {"type": "declare_attack", "player": 0, "page": 2})
        assert e.value.code == "spell.no_mamodo"


def _deploy_m025(discard=("M-024",)):
    """以 E-012 從第 9 頁放出 M-025(登場效果觸發)。回傳 (g, ps)。"""
    g, _ = mk(book("M-001", "E-012", "S-029", "S-029", "S-029", "S-029", "S-029", "S-029", "M-025"),
              book("M-001"))
    ps = g.state.players[0]
    ps.mp = 10
    ps.discard.extend(discard)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})   # E-012 費用 3
    return g, ps


def test_m025_return_is_optional_and_mp_comes_after():
    # 效果文:①捨て札のロブノス1枚を…もどすことができる ②MPを2ふやす(この順で)
    g, ps = _deploy_m025()
    assert g.state.pending.kind == "pick_card_in_own_discard"
    assert [o["value"] for o in g.state.pending.options] == [0, None]     # 可選擇不放回
    assert ps.mp == 7                                                      # ② 還沒執行
    submit(g, {"type": "choose", "player": 0, "value": None})
    assert ps.discard == ["M-024"] and 1 in ps.consumed_pages
    assert ps.mp == 9


def test_m025_player_chooses_card_then_empty_page():
    g, ps = _deploy_m025()
    submit(g, {"type": "choose", "player": 0, "value": 0})
    assert g.state.pending.kind == "pick_own_empty_page"
    assert [o["value"] for o in g.state.pending.options] == [1, 9]        # 兩個空頁
    assert ps.mp == 7
    submit(g, {"type": "choose", "player": 0, "value": 9})
    assert ps.card_at(9) == "M-024" and 9 not in ps.consumed_pages and 1 in ps.consumed_pages
    assert ps.discard == [] and ps.mp == 9


def test_m025_no_robnos_in_discard_just_gains_mp():
    g, ps = _deploy_m025(discard=("M-001",))
    assert g.state.pending is None and ps.mp == 9


def _attack_with_page(g, page, slot_uid):
    """玩家 0 以第 page 頁的術、由 slot_uid 的魔物攻擊,推進到戰鬥結束(防方不防禦、不保護)。"""
    submit(g, {"type": "declare_attack", "player": 0, "page": page, "slot_uid": slot_uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    while g.state.pending is not None and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})
    assert g.state.battle is None


def _two_robnos_game(copies=2):
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-024", "S-042"), book("M-001", "S-029", "S-029"))
    ps = g.state.players[0]
    ps.mp = 20
    for _ in range(copies - 1):
        ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-024"]))
    to_battle(g, 0)
    return g, ps


def test_m024_two_doubles_let_biraitsu_be_used_twice_per_turn():
    # 效果文:自分の「ロブノス(分身体)」が2体いるとき、術カード「ビライツ」を1枚につき1ターンに2回使える
    from gash.api.views import snapshot
    g, ps = _two_robnos_game(copies=2)
    uid = ps.slots[0].uid
    _attack_with_page(g, 2, uid)
    assert 2 not in snapshot(g, 0)["players"][0]["used_spell_pages"]   # 還能再用一次
    _attack_with_page(g, 2, uid)
    assert 2 in snapshot(g, 0)["players"][0]["used_spell_pages"]
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": uid})
    assert e.value.code == "spell.used"


def test_m024_single_double_biraitsu_once_per_turn():
    g, ps = _two_robnos_game(copies=1)
    uid = ps.slots[0].uid
    _attack_with_page(g, 2, uid)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": uid})
    assert e.value.code == "spell.used"


def test_m024_second_use_needs_two_doubles_at_that_time():
    g, ps = _two_robnos_game(copies=2)
    uid = ps.slots[0].uid
    _attack_with_page(g, 2, uid)
    ps.slots.pop()                                             # 一隻分身體離場
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": uid})
    assert e.value.code == "spell.used"


# ---------------------------------------------------------------- M-026《裏切り者》(ジャマー)

def _jammer_battle(p1_mp=5, p0_has_jammer=False):
    """玩家 0 以 M-017 攻擊並使用其效果(攻擊時 +2000);玩家 1 場上有 M-026。"""
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-017", "S-009"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, p1_mp
    st.players[1].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-026"]))
    if p0_has_jammer:
        st.players[0].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-026"]))
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    mp_before_ability = st.players[0].mp
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": st.players[0].slots[0].uid})
    return g, mp_before_ability


def _m017_boost_active(g):
    return any(m.source == "M-017" and m.kind == "power" for m in g.state.modifiers)


def test_m026_offered_right_after_opponent_mamodo_effect_and_negates_it():
    g, mp0 = _jammer_battle()
    st = g.state
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    assert [o["value"] for o in st.pending.options] == [None, True]      # 第一個是「不使用」
    assert _m017_boost_active(g)
    events = submit(g, {"type": "choose", "player": 1, "value": True})
    assert not _m017_boost_active(g)                                     # 效果被還原
    assert st.players[0].mp == mp0 - 2 and "mamodo:M-017" in st.players[0].used_abilities   # 費用照付
    assert st.players[1].mp == 5 - 2 and "mamodo:M-026" in st.players[1].used_abilities
    assert [e for e in events if e["type"] == "effect_negated"][0]["negated"] == "M-017"
    assert st.pending is None and st.battle.data["effect_turn"] == 1       # 輪到防方


def test_m026_skip_keeps_effect():
    g, mp0 = _jammer_battle()
    submit(g, {"type": "choose", "player": 1, "value": None})
    assert _m017_boost_active(g) and g.state.players[1].mp == 5
    assert g.state.battle.data["effect_turn"] == 1


@pytest.mark.parametrize("setup", ["low_mp", "used", "restricted"])
def test_m026_not_offered_when_unusable(setup):
    from gash.engine.effects.primitives import add_restriction
    from gash.engine.state import DUR_TURN, NO_MAMODO_EFFECTS
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-017", "S-009"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, (1 if setup == "low_mp" else 5)
    st.players[1].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-026"]))
    if setup == "used":
        st.players[1].used_abilities.add("mamodo:M-026")
    if setup == "restricted":
        add_restriction(g, [], source="E-025", owner=0, target_player=1, flag=NO_MAMODO_EFFECTS,
                        duration=DUR_TURN)
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": st.players[0].slots[0].uid})
    assert st.pending is None and _m017_boost_active(g)


def test_m026_cannot_be_declared_manually():
    g, _ = _jammer_battle()
    submit(g, {"type": "choose", "player": 1, "value": None})
    m026 = g.state.players[1].slots[-1]
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 1, "zone": "mamodo", "slot_uid": m026.uid})
    assert e.value.code == "ability.none"


def test_m026_chain_original_player_negates_the_negation():
    g, mp0 = _jammer_battle(p0_has_jammer=True)
    st = g.state
    submit(g, {"type": "choose", "player": 1, "value": True})           # 玩家 1 無效 M-017
    assert st.pending.kind == "jammer_negate" and st.pending.player == 0
    submit(g, {"type": "choose", "player": 0, "value": True})           # 玩家 0 無效玩家 1 的 M-026
    assert _m017_boost_active(g)                                         # M-017 的效果回來
    assert st.players[0].mp == mp0 - 2 - 2 and st.players[1].mp == 5 - 2
    assert st.pending is None                                            # 雙方都用過,不再連鎖


def test_m026_waits_for_opponent_effect_choices_then_restores():
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-022"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    a = st.players[1].slots[0]
    a.partner = "P-001"
    b = MamodoSlot(uid=st.next_uid(), stack=["M-004"], partner="P-002")
    st.players[1].slots += [b, MamodoSlot(uid=st.next_uid(), stack=["M-026"])]
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": st.players[0].slots[0].uid})
    assert st.pending.kind == "pick_opponent_partner"                                # 先完成對手效果的選擇
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert b.partner is None and st.pending.kind == "jammer_negate"
    submit(g, {"type": "choose", "player": 1, "value": True})
    b = st.slot_by_uid(1, b.uid)
    assert b.partner == "P-002" and "P-002" not in st.players[1].discard
    assert st.players[0].mp == 10 - 5 and st.action_player == 1


def test_m026_not_offered_for_partner_effects():
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-004"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-002"
    st.players[1].mp = 5
    st.players[1].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-026"]))
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": st.players[0].slots[0].uid})
    assert st.pending is None


def test_timeout_default_prefers_skip_option():
    from gash.engine.awaiting import default_command
    g, _ = _jammer_battle()
    assert default_command(g) == {"type": "choose", "value": None}


# ---------------------------------------------------------------- 夥伴卡:依使用者決定與效果文

def _pokkerio_uses_sugina_spell(setup):
    """場上有 M-008 スギナ 與 M-023 ポッケリオ(可用木屬性術);第 2 頁為スギナ的 S-014(木)。"""
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-008", "S-014"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    pokkerio = MamodoSlot(uid=st.next_uid(), stack=["M-023"])
    st.players[0].slots.append(pokkerio)
    sugina = st.players[0].slots[0]
    to_battle(g, 0)
    setup(g, sugina)
    return g, sugina, pokkerio


def test_p005_cost_zero_only_when_sugina_uses_the_spell():
    # 使用者決定:「スギナ」の術 以使用術的魔物判定 → ポッケリオ 用 スギナ 的術不免費
    from gash.engine.engine import spell_cost
    def use_p005(g, sugina):
        sugina.partner = "P-005"
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": sugina.uid})
        submit(g, {"type": "pass", "player": 1})
    g, sugina, pokkerio = _pokkerio_uses_sugina_spell(use_p005)
    card = g.db["S-014"]
    mp = g.state.players[0].mp
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": pokkerio.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})   # 開戰時才扣費
    assert g.state.players[0].mp == mp - card.cost
    assert spell_cost(g, 0, 2, card, slot=sugina) == 0
    assert spell_cost(g, 0, 2, card, slot=pokkerio) == card.cost
    assert spell_cost(g, 0, 2, card) == 0                             # 未指定魔物:取可用魔物中最低


def test_m008_bonus_only_when_sugina_uses_the_spell():
    def use_m008(g, sugina):
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": sugina.uid})
        submit(g, {"type": "pass", "player": 1})
    g, sugina, pokkerio = _pokkerio_uses_sugina_spell(use_m008)
    card = g.db["S-014"]
    mp = g.state.players[0].mp
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": pokkerio.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.players[0].mp == mp - card.cost                    # 不減費
    _, items = side_breakdown(g, g.state.battle, "attack")
    assert not any(i["kind"] == "spell_bonus" for i in items)          # 不減魔力


def test_p006_only_usable_in_battle():
    g, _ = mk(book("M-009"), book("M-001"))
    st = g.state
    koruru = st.players[0].slots[0]
    koruru.stack.append("M-010")
    koruru.partner = "P-006"
    to_battle(g, 0)
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": koruru.uid})
    assert e.value.code == "ability.timing"


def test_p006_negation_lasts_only_this_battle():
    # 效果文:【スタンバイ】このバトル中、…ダメージを受けないとき → 只在這場戰鬥中
    g, _ = mk(book("M-001", "S-001", "S-001"), book("M-009", "S-016"))
    st = g.state
    koruru = st.players[1].slots[0]
    koruru.stack.append("M-010")
    koruru.partner = "P-006"
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    # 第 1 場:防方以 S-016 防禦並使用 P-006,再加魔力確保防方獲勝 → コルル 沒受傷
    from gash.engine.effects.primitives import add_power
    from gash.engine.state import DUR_BATTLE
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": koruru.uid})
    add_power(g, [], source="test", owner=1, target_player=1, target_slot=koruru.uid,
              amount=10000, duration=DUR_BATTLE)
    while st.battle is not None and st.pending is None:
        submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    assert st.battle is None and koruru.injured is False
    # 第 2 場:以 コルル 保護魔本 → 受傷(P-006 的效果已隨上一場戰鬥結束)
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    assert st.pending.kind == "protect"
    events = submit(g, {"type": "choose", "player": 1, "value": koruru.uid})
    assert not [e for e in events if e["type"] == "damage_negated"]
    assert st.slot_by_uid(1, koruru.uid).injured is True


def test_p008_discarded_partner_counts_as_discarded_this_turn():
    # 效果文:相手のパートナーカード1枚を選び、捨て札にする → 算是「本回合入墓」,對手的 E-022 可取回
    g, _ = mk(book("M-001", "E-022"), book("M-012"))
    st = g.state
    st.players[0].slots[0].partner = "P-001"
    st.players[1].slots[0].partner = "P-008"
    st.players[0].mp, st.players[1].mp = 10, 10
    g.rng = Rng(HEADS)
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})                          # 行動權到玩家 1
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner",
               "slot_uid": st.players[1].slots[0].uid})               # P-008 棄掉玩家 0 的 P-001
    assert st.players[0].slots[0].partner is None
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})      # E-022 擲幣正 → 取回
    assert st.players[0].slots[0].partner == "P-001"


def _armored_attack_until_defender_acts():
    """玩家 0 以裝甲巴爾特羅無術攻擊,玩家 1(場上 M-004 裝 P-009)不防禦,攻方 pass。"""
    g, _ = mk(book("M-028", "S-048", "M-027"), book("M-004"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].slots[0].partner = "P-009"
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    slot = st.players[0].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    return g


def test_p009_cannot_negate_spellless_attack():
    # 效果文:このバトルの、相手が使った「術」1つを無効にする → 無術攻擊不是術
    g = _armored_attack_until_defender_acts()
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner",
                   "slot_uid": g.state.players[1].slots[0].uid})
    assert e.value.code == "ability.condition"


def _p013_game():
    """玩家 0:M-022 ゾフィス 裝 P-013 ココ,另有 M-029 ゼオン(7MP 棄掉對手負傷魔物)。"""
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-022"), book("M-001"))
    st = g.state
    st.players[0].mp = 20
    st.players[0].slots[0].partner = "P-013"
    zeon = MamodoSlot(uid=st.next_uid(), stack=["M-029"])
    st.players[0].slots.append(zeon)
    to_battle(g, 0)
    return g, zeon


@pytest.mark.parametrize("stack,pages", [(["M-009", "M-010"], 2), (["M-028", "M-027"], 1)])
def test_p013_turns_one_page_per_opponent_mamodo_card(stack, pages):
    # 效果文:相手の魔物カード1枚が捨て札になるたびに、相手の魔本を1枚めくる
    #   疊著兩張的魔物整隻入墓 → 2 張;裝甲單獨入墓(本體留下)→ 1 張
    from gash.engine.state import MamodoSlot
    g, zeon = _p013_game()
    st = g.state
    target = MamodoSlot(uid=st.next_uid(), stack=list(stack), injured=True)
    st.players[1].slots.append(target)
    pos1 = st.players[1].pos
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": zeon.uid})
    assert st.players[1].pos == pos1 + 2 * pages


def test_p013_counts_mamodo_card_discarded_from_book():
    from gash.engine.state import MamodoSlot
    g, _ = _p013_game()
    st = g.state
    st.players[1].book[9] = "M-002"                         # 對手魔本第 10 頁放一張魔物卡
    fein = MamodoSlot(uid=st.next_uid(), stack=["M-011"])
    st.players[0].slots.append(fein)
    pos1 = st.players[1].pos
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": fein.uid})
    assert st.pending is None                               # 唯一的魔物卡 → 自動選
    assert "M-002" in st.players[1].discard
    assert st.players[1].pos == pos1 + 2


def test_p019_two_mp_per_page_turned_back():
    # 效果文:相手が相手自身の魔本のページを1枚もどすたびに、相手のMPを2へらす
    g, _ = mk(book("M-001"), book("M-001", "E-005"))
    st = g.state
    st.players[0].slots[0].partner = "P-019"
    to_battle(g, 0)
    _end_turn(g)
    g.rng = Rng(HEADS, HEADS)
    st.players[1].mp, st.players[1].pos = 10, 6            # 翻開 6、7;可回翻 2 張
    st.players[1].book[5] = "E-005"
    submit(g, {"type": "use_book_card", "player": 1, "page": 6})   # E-005 正正 → 回翻 2 張
    assert st.players[1].pos == 2
    assert st.players[1].mp == 10 - g.db["E-005"].cost - 2 * 2


@pytest.mark.parametrize("pos,after,mp_lost", [(4, 2, 2), (2, 2, 0)])
def test_p019_counts_pages_actually_turned_back(pos, after, mp_lost):
    # 回翻到第一頁為止:E-005 正正在 pos 4 只回翻 1 張、在 pos 2 沒有回翻
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-019"
    to_battle(g, 0)
    _end_turn(g)
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    g.rng = Rng(HEADS, HEADS)
    st.players[1].mp, st.players[1].pos = 10, pos
    st.players[1].book[pos - 1] = "E-005"
    events = submit(g, {"type": "use_book_card", "player": 1, "page": pos})
    assert st.players[1].pos == after
    assert [e["count"] for e in events if e["type"] == "pages_turned"] == ([-(pos - after) // 2] if mp_lost else [])
    assert st.players[1].mp == 10 - g.db["E-005"].cost - mp_lost


def test_p010_usable_on_last_page_and_turning_past_end_loses():
    # 效果文沒有限制:在最後一頁使用 → 自己的魔本翻完 → 敗北
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-010"
    st.players[0].pos = 32
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": st.players[0].slots[0].uid})
    assert st.phase == "game_over" and st.winner == 1


# ---------------------------------------------------------------- 夥伴卡(照原樣遷移者的行為測試)

def _use_partner(g, player, slot):
    return submit(g, {"type": "use_field_ability", "player": player, "zone": "partner", "slot_uid": slot.uid})


def test_p011_player_chooses_opponent_mamodo_power_zero_this_turn():
    # 效果文:相手の魔物1体を選ぶ。このターン中、その魔物の魔力を0にする。
    from gash.engine.engine import slot_power
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    me = st.players[0].slots[0]
    me.partner = "P-011"
    a = st.players[1].slots[0]
    b = MamodoSlot(uid=st.next_uid(), stack=["M-004"])
    st.players[1].slots.append(b)
    to_battle(g, 0)
    _use_partner(g, 0, me)
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0
    with pytest.raises(IllegalCommand) as e:                           # 對手不能代選
        submit(g, {"type": "choose", "player": 1, "value": b.uid})
    assert e.value.code == "choice.required" and st.pending.kind == "pick_opponent_mamodo"
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert slot_power(g, 1, b) == 0 and slot_power(g, 1, a) == 4000
    _end_turn(g)
    assert slot_power(g, 1, b) == 3000                                 # 只到本回合結束


@pytest.mark.parametrize("page,attacker_top,discarded", [
    (2, "M-005", True),                     # ブラゴ 的 S-008 → 保護的魔物入墓
    (3, "M-001", False),                    # ガッシュ 的 S-001 → 只受傷
])
def test_p012_protector_of_own_brago_damage_is_discarded(page, attacker_top, discarded):
    # 効果文:このターン中、自分の「ブラゴ」によるダメージを「かばって」、ダメージを受けた魔物は捨て札になる。
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-005", "S-008", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    brago = st.players[0].slots[0]
    brago.partner = "P-012"
    st.players[0].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-001"]))
    protector = MamodoSlot(uid=st.next_uid(), stack=["M-004"])
    st.players[1].slots.append(protector)
    to_battle(g, 0)
    _use_partner(g, 0, brago)
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": page,
               "slot_uid": slot_uid(g, 0, attacker_top)})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    assert st.pending.kind == "protect"
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    if discarded:
        assert protector not in st.players[1].slots and "M-004" in st.players[1].discard
    else:
        assert protector in st.players[1].slots and protector.injured is True


def test_p014_opponent_cannot_attack_with_spells_this_turn():
    # 効果文:このターン中、相手は術で攻撃できない。
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].slots[0].partner = "P-014"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    _use_partner(g, 1, st.players[1].slots[0])                         # 對手在我的回合使用
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert e.value.code == "spell.attack_restricted"
    _end_turn(g)                                                       # 結束玩家 0 的回合
    _end_turn(g)                                                       # 結束玩家 1 的回合
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    assert st.turn_player == 0 and st.phase == BATTLE
    submit(g, {"type": "declare_attack", "player": 0, "page": st.players[0].pos})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.battle.attack_spell == "S-029"                           # 下一個回合可以攻擊


def _spell_battle(defend, p0_partner=None, p1_partner=None):
    """玩家 0 以 S-001 攻擊;玩家 1 以 S-029 防禦(defend)或不防禦。效果階段由攻方先行動。"""
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    st.players[0].slots[0].partner = p0_partner
    st.players[1].slots[0].partner = p1_partner
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    if defend:
        submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    else:
        submit(g, {"type": "no_defense", "player": 1})
    return g


def test_p016_defender_negates_opponent_spell_attack():
    # 効果文:このバトルの、相手の術による攻撃1つを無効にする。
    g = _spell_battle(defend=False, p1_partner="P-016")
    st = g.state
    submit(g, {"type": "pass", "player": 0})
    events = _use_partner(g, 1, st.players[1].slots[0])
    assert st.battle.attack_negated is True
    assert [e["source"] for e in events if e["type"] == "attack_negated"] == ["P-016"]


def test_p016_attacker_cannot_use_it():
    g = _spell_battle(defend=True, p0_partner="P-016")
    with pytest.raises(IllegalCommand) as e:
        _use_partner(g, 0, g.state.players[0].slots[0])
    assert e.value.code == "ability.condition"


def test_p016_cannot_negate_spellless_attack():
    g = _armored_attack_until_defender_acts()
    g.state.players[1].slots[0].partner = "P-016"
    with pytest.raises(IllegalCommand) as e:
        _use_partner(g, 1, g.state.players[1].slots[0])
    assert e.value.code == "ability.condition"


def test_p017_attacker_negates_opponent_spell_defense():
    # 効果文:このバトルの、相手の術による防御1つを無効にする。
    g = _spell_battle(defend=True, p0_partner="P-017")
    st = g.state
    events = _use_partner(g, 0, st.players[0].slots[0])
    assert st.battle.defense_negated is True
    assert [e["source"] for e in events if e["type"] == "defense_negated"] == ["P-017"]


@pytest.mark.parametrize("defend,user", [(False, 0), (True, 1)])
def test_p017_needs_opponent_spell_defense(defend, user):
    # 對手沒有以術防禦(不防禦)、或自己是防方時都不能使用
    partners = {"p0_partner": "P-017"} if user == 0 else {"p1_partner": "P-017"}
    g = _spell_battle(defend=defend, **partners)
    st = g.state
    if user == 1:
        submit(g, {"type": "pass", "player": 0})
    with pytest.raises(IllegalCommand) as e:
        _use_partner(g, user, st.players[user].slots[0])
    assert e.value.code == "ability.condition"


def test_p018_turn_back_one_leaf():
    # 効果文:自分の魔本を1枚もどす。
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    me = st.players[0].slots[0]
    me.partner = "P-018"
    to_battle(g, 0)
    st.players[0].pos = 6
    events = _use_partner(g, 0, me)
    assert st.players[0].pos == 4 and me.partner is None
    assert [e["count"] for e in events if e["type"] == "pages_turned"] == [-1]


def _p018_first_page_game(coins=()):
    """玩家 0:M-001 裝 P-018,第 3 頁為 E-005;對手 M-001 裝 P-019。魔本在第一頁。"""
    g, _ = mk(book("M-001", "S-029", "E-005"), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    st.players[0].slots[0].partner = "P-018"
    st.players[1].slots[0].partner = "P-019"
    g.rng = Rng(*coins)
    to_battle(g, 0)
    assert st.players[0].pos == 2
    return g


def test_p018_usable_on_first_page_turns_nothing_but_counts_as_the_one_use():
    # 效果文沒有限制(專案負責人決定依效果文):第一頁也能使用;回翻 0 張,但 P-018 本身算 1 次
    g = _p018_first_page_game(coins=(HEADS, HEADS))
    st = g.state
    first = st.players[0].slots[0]
    events = _use_partner(g, 0, first)
    assert first.partner is None and "P-018" in st.players[0].discarded_this_turn
    assert st.players[0].pos == 2 and st.players[1].mp == 10          # 沒回翻,對手 P-019 不觸發
    assert not [e for e in events if e["type"] == "pages_turned"]
    submit(g, {"type": "pass", "player": 1})
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 3})   # E-005 正正:合計1回已用掉
    assert [e["source"] for e in events if e["type"] == "page_turn_restricted"] == ["E-005"]


def test_p018_usable_after_e005_turned_back_nothing_on_first_page():
    # 回翻 0 張不算用過回翻效果(Inferred)→ 之後仍可使用 P-018
    g = _p018_first_page_game(coins=(HEADS, HEADS))
    st = g.state
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 3})   # E-005 正正,在第一頁
    assert not [e for e in events if e["type"] in ("pages_turned", "page_turn_restricted")]
    submit(g, {"type": "pass", "player": 1})
    _use_partner(g, 0, st.players[0].slots[0])
    assert st.players[0].slots[0].partner is None


# ---------------------------------------------------------------- 「このターン中の次のバトル」(P-001 / P-007 / M-008)

def _finish_battle(g):
    """雙方 pass 到戰鬥結束;傷害 / 保護決策一律不保護、依序處理。"""
    st = g.state
    while st.battle is not None:
        if st.pending is not None:
            _resolve_damage_choices(g, st.pending.player)
        else:
            submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})


def _two_battles(first_book, other, use, first_page, second_page):
    """玩家 0:P1 魔物(first_book[0])與另一隻 other;use(g, main) 使用效果後,
    第 1 場以 other 用第 first_page 頁攻擊並打完,回傳 (g, main) 供第 2 場使用。"""
    from gash.engine.state import MamodoSlot
    g, _ = mk(book(*first_book), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 20
    main = st.players[0].slots[0]
    helper = MamodoSlot(uid=st.next_uid(), stack=[other])
    st.players[0].slots.append(helper)
    to_battle(g, 0)
    use(g, main)
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": first_page, "slot_uid": helper.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    _finish_battle(g)
    assert st.battle is None and st.phase == BATTLE and st.action_player == 0
    submit(g, {"type": "declare_attack", "player": 0, "page": second_page, "slot_uid": main.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    return g, main


def _use_partner_card(number):
    def use(g, main):
        main.partner = number
        _use_partner(g, 0, main)
    return use


def test_p001_only_applies_to_the_next_battle():
    # 効果文:このターン中の次のバトルで、自分が「ガッシュ・ベル」の術で攻撃するとき、相手は防御できない。
    #   下一場由ブラゴ攻擊 → 效果用掉;第 2 場ガッシュ攻擊時可以防禦
    g, _ = _two_battles(("M-001", "S-008", "S-001"), "M-005", _use_partner_card("P-001"), 2, 3)
    submit(g, {"type": "declare_defense", "player": 1, "page": g.state.players[1].pos})
    assert g.state.battle.defense_spell == "S-029"


def test_p007_only_applies_to_the_next_battle():
    # 効果文:このターン中の次のバトルで、自分が使う「フェイン」の術の魔力を+4000する。
    from .test_cards import showdown_of
    g, _ = _two_battles(("M-011", "S-001", "S-018"), "M-001", _use_partner_card("P-007"), 2, 3)
    submit(g, {"type": "no_defense", "player": 1})
    events = []
    while g.state.battle is not None and g.state.battle.step == "effects" and g.state.pending is None:
        events += submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    assert showdown_of(events)["attacker_total"] == 3000 + 2000


def test_m008_only_applies_to_the_next_battle():
    # 効果文:このターン中の次のバトルで、この魔物の術を本来より1低いコストで使うことができる。
    def use_m008(g, main):
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": main.uid})
    mp_before = {}

    def use_and_record(g, main):
        use_m008(g, main)
        mp_before["mp"] = g.state.players[0].mp
    g, _ = _two_battles(("M-008", "S-001", "S-014"), "M-001", use_and_record, 2, 3)
    assert g.state.players[0].mp == mp_before["mp"] - g.db["S-001"].cost - g.db["S-014"].cost


def test_p007_applies_when_defending_in_the_next_battle():
    # 「自分が使うフェインの術」:對手回合中使用,下一場戰鬥以フェイン的術防禦時也適用
    from .test_cards import showdown_of
    g, _ = mk(book("M-001", "S-001"), book("M-011", "S-019"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    st.players[1].slots[0].partner = "P-007"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    _use_partner(g, 1, st.players[1].slots[0])
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    events = []
    while st.battle is not None and st.battle.step == "effects" and st.pending is None:
        events += submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    assert showdown_of(events)["defender_total"] == 3000 + 3000 + 4000


def test_s026_next_battle_undefendable_applies_to_mamodo_attack():
    # S-026 効果文:このターン中の次のバトルで、相手は防御できない。→ 無術攻擊的戰鬥也是「次のバトル」
    g, _ = mk(book("M-028", "S-048", "S-026", "S-029", "M-027"), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    g.rng = Rng(HEADS)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})      # S-048 疊上裝甲體
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "use_book_card", "player": 0, "page": 3})      # S-026 正面
    submit(g, {"type": "pass", "player": 1})
    slot = st.players[0].slots[0]
    assert slot.top == "M-027"
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert e.value.code == "defense.undefendable"


def test_next_battle_standby_expires_at_turn_end_without_battle():
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    st.players[0].slots[0].partner = "P-001"
    to_battle(g, 0)
    _use_partner(g, 0, st.players[0].slots[0])
    _end_turn(g)                                                       # 本回合沒有戰鬥
    _end_turn(g)
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "declare_attack", "player": 0, "page": st.players[0].pos})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": st.players[1].pos})
    assert st.battle.defense_declared is True


# ---------------------------------------------------------------- M-008「1低いコストで使うことができる」:可選

def _m008_declared_attack(mp, partner=None):
    """玩家 0 的 M-008 スギナ 宣告使用後,以第 2 頁的 S-014(費用 2、魔力 2000)宣告攻擊。"""
    g, _ = mk(book("M-008", "S-014"), book("M-001"))
    st = g.state
    st.players[0].mp = mp
    sugina = st.players[0].slots[0]
    sugina.partner = partner
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": sugina.uid})
    submit(g, {"type": "pass", "player": 1})
    if partner:
        _use_partner(g, 0, sugina)
        submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    return g


def _showdown(g, defend_page=None):
    from .test_cards import showdown_of
    st = g.state
    events = []
    if st.battle.step == "defense":
        if defend_page is None:
            events += submit(g, {"type": "no_defense", "player": st.battle.defender})
        else:
            events += submit(g, {"type": "declare_defense", "player": st.battle.defender, "page": defend_page})
    while st.battle is not None and st.battle.step == "effects" and st.pending is None:
        events += submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    return showdown_of(events)


@pytest.mark.parametrize("value,paid,total", [
    (True, 1, 3500 + 2000 - 1000),          # 使用:少付 1、術的魔力 -1000
    (None, 2, 3500 + 2000),                 # 不使用:付原價、魔力不變
])
def test_m008_discount_is_chosen_when_declaring(value, paid, total):
    g = _m008_declared_attack(mp=5)
    st = g.state
    assert st.pending.kind == "spell_discount" and st.pending.player == 0
    assert [o["label"] for o in st.pending.options] == ["spell_discount_use", "skip"]
    with pytest.raises(IllegalCommand) as e:                           # 對手不能代選
        submit(g, {"type": "choose", "player": 1, "value": True})
    assert e.value.code == "choice.required"
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "choose", "player": 0, "value": 3})
    assert e.value.code == "choose.invalid" and st.pending.kind == "spell_discount"
    submit(g, {"type": "choose", "player": 0, "value": value})
    assert st.pending is None and st.battle_in is not None and st.action_player == 0
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == 5 - paid
    assert _showdown(g)["attacker_total"] == total


def test_m008_discount_applied_without_asking_when_mp_only_covers_it():
    g = _m008_declared_attack(mp=1)
    st = g.state
    assert st.pending is None and st.battle_in is not None
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == 0
    assert _showdown(g)["attacker_total"] == 3500 + 2000 - 1000


def test_m008_not_offered_when_base_cost_is_zero():
    # P-005 使スギナ的術「本来のコスト」為 0 → 無法「本来より1低い」,不詢問、魔力不減
    g = _m008_declared_attack(mp=5, partner="P-005")
    st = g.state
    assert st.pending is None
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == 5
    assert _showdown(g)["attacker_total"] == 3500 + 2000


def test_m008_discount_chosen_when_defending():
    g, _ = mk(book("M-001", "S-001"), book("M-008", "S-014"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "mamodo",
               "slot_uid": st.players[1].slots[0].uid})
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert st.pending.kind == "spell_discount" and st.pending.player == 1
    assert st.battle.defense_declared is False                          # 決定前尚未宣告完成
    submit(g, {"type": "choose", "player": 1, "value": True})
    assert st.players[1].mp == 4 and st.battle.step == "effects"
    assert _showdown(g)["defender_total"] == 3500 + 2000 - 1000


def test_spell_power_cut_not_below_zero():
    # M-008:その術の魔力は-1000される(0より小さくはならない)→ 只減術的魔力,不影響魔物本身
    from gash.engine.engine import _side_total
    from gash.engine.state import BattleState
    g, _ = mk(book("M-001"), book("M-008"))
    st = g.state
    sugina = st.players[1].slots[0]
    st.battle = BattleState(attacker=0, step="effects", attack_page=2, attack_spell="S-001",
                            attack_slot=st.players[0].slots[0].uid, defense_page=2,
                            defense_spell="S-056", defense_slot=sugina.uid,
                            data={"defense_spell_power": [
                                {"kind": "spell_bonus", "source": "M-008", "amount": -1000}]})
    assert _side_total(g, st.battle, "defense") == 3500 + 0
    total, items = side_breakdown(g, st.battle, "defense")
    assert sum(i["amount"] for i in items) == total
    assert any(i["kind"] == "spell_floor" for i in items)            # 不低於 0 的調整項


# ---------------------------------------------------------------- 「自分の魔本をめくる/もどす」効果を合計1回(P-010 / P-018 與 E-005)

def _own_book_game(pos, e005_page, coins, partner):
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[0].slots[0].partner = partner
    st.players[0].book[e005_page - 1] = "E-005"
    g.rng = Rng(*coins)
    to_battle(g, 0)
    st.players[0].pos = pos
    return g


def _use_e005(g, page):
    events = submit(g, {"type": "use_book_card", "player": 0, "page": page})
    submit(g, {"type": "pass", "player": 1})
    return events


@pytest.mark.parametrize("partner,pos,after_partner,coins", [
    ("P-010", 2, 4, (TAILS, TAILS)),        # P-010 翻 1 張後,E-005 反反不再翻
    ("P-018", 6, 4, (HEADS, HEADS)),        # P-018 回翻 1 張後,E-005 正正不再回翻
])
def test_e005_same_direction_blocked_after_partner(partner, pos, after_partner, coins):
    g = _own_book_game(pos, after_partner, coins, partner)
    st = g.state
    _use_partner(g, 0, st.players[0].slots[0])
    submit(g, {"type": "pass", "player": 1})
    assert st.players[0].pos == after_partner
    events = _use_e005(g, after_partner)
    assert st.players[0].pos == after_partner
    assert not [e for e in events if e["type"] == "pages_turned"]
    assert [e["source"] for e in events if e["type"] == "page_turn_restricted"] == ["E-005"]


def test_e005_other_direction_not_blocked_after_p010():
    g = _own_book_game(6, 8, (HEADS, HEADS), "P-010")
    st = g.state
    _use_partner(g, 0, st.players[0].slots[0])                         # 翻 1 張 → 8
    submit(g, {"type": "pass", "player": 1})
    _use_e005(g, 8)                                                    # 正正回翻 2 張
    assert st.players[0].pos == 4


@pytest.mark.parametrize("partner,pos,coins,after_e005", [
    ("P-010", 2, (TAILS, TAILS), 6),        # E-005 已翻過自己的魔本 → 不能再用 P-010
    ("P-018", 10, (HEADS, HEADS), 6),       # E-005 已回翻過 → 不能再用 P-018
])
def test_partner_blocked_after_e005_same_direction(partner, pos, coins, after_e005):
    g = _own_book_game(pos, pos, coins, partner)
    st = g.state
    _use_e005(g, pos)
    assert st.players[0].pos == after_e005
    with pytest.raises(IllegalCommand) as e:
        _use_partner(g, 0, st.players[0].slots[0])
    assert e.value.code == "ability.condition"


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
    # 記錄本回合已減(PlayerState 的正式欄位;直前回合限制的行為測試見 test_effect_characterization)
    assert g.state.turn_no in g.state.players[0].opp_mp_reduced_turns


def _end_turn(g):
    st = g.state
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})
    submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})


def _give_action_to(g, player):
    if g.state.action_player != player:
        submit(g, {"type": "pass", "player": g.state.action_player})


def _use_e018(g, page, opp_mp=10):
    """玩家 0 使用第 page 頁的 E-018(必要時調整 pos 讓該頁翻開),回傳對手 MP 的變化量。"""
    ps = g.state.players[0]
    ps.mp = max(ps.mp, 5)
    if page not in ps.open_pages():
        ps.pos = page
    g.state.players[1].mp = opp_mp
    _give_action_to(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": page})
    return g.state.players[1].mp - opp_mp


def test_e018_zero_after_partner_p002_reduced_opponent_mp_last_turn():
    # 效果文:直前回合用過「任何」減少對手 MP 的效果 → 減 0(不限 E-018 自己)
    g, _ = mk(book("M-004", "E-018"), book("M-001"))
    g.state.players[0].slots[0].partner = "P-002"
    g.state.players[1].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": g.state.players[0].slots[0].uid})
    assert g.state.players[1].mp == 2                         # P-002:對手 MP-3
    _end_turn(g)                                               # 進入對手回合(直前回合 = 用了 P-002)
    assert _use_e018(g, 2) == 0


def test_e018_zero_after_e004_zeroed_opponent_mp_last_turn():
    # E-004 註記:MP 為 1 以上時視為「減少 MP」的效果
    g, _ = mk(book("M-001", "E-004", "E-018"), book("M-001"))
    g.state.players[0].mp, g.state.players[1].mp = 10, 5
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    _end_turn(g)
    assert _use_e018(g, 3) == 0


def test_e018_e004_on_zero_opponent_mp_does_not_count():
    g, _ = mk(book("M-001", "E-004", "E-018"), book("M-001"))
    g.state.players[0].mp, g.state.players[1].mp = 10, 0
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    _end_turn(g)
    assert _use_e018(g, 3) == -4


def test_e018_used_but_limited_to_zero_still_counts_as_reducing_effect():
    # 第 1 回合減 4;第 2 回合因限制減 0,但仍「使用了減少對手 MP 的效果」→ 第 3 回合也減 0
    g, _ = mk(book("M-001", "E-018", "E-018", "E-018"), book("M-001"))
    to_battle(g, 0)
    assert _use_e018(g, 2) == -4
    _end_turn(g)
    assert _use_e018(g, 3) == 0
    _end_turn(g)
    assert _use_e018(g, 4) == 0


def test_e018_zero_after_passive_p019_reduced_opponent_mp_last_turn():
    # 規則書:「此卡在場上→」效果的使用為自動進行 → P-019 的被動效果也算「使用了」
    g, _ = mk(book("M-001", "E-018"), book("M-001", "E-005"))
    g.state.players[0].slots[0].partner = "P-019"
    to_battle(g, 0)
    _end_turn(g)                                               # 對手回合
    g.rng = Rng(HEADS, HEADS)
    g.state.players[1].mp, g.state.players[1].pos = 5, 6
    g.state.players[1].book[5] = "E-005"
    submit(g, {"type": "use_book_card", "player": 1, "page": 6})   # E-005 正正 → 對手自己回翻 2 張
    assert g.state.players[1].mp == 5 - 2 * 2                  # P-019 觸發:每張 MP-2
    _end_turn(g)                                               # 回到玩家 0(直前回合 = P-019 觸發的回合)
    assert _use_e018(g, 2) == 0


def _m017_attack_total(use_ability):
    g, _ = mk(book("M-017", "S-009"), book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    if use_ability:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": slot.uid})
        submit(g, {"type": "pass", "player": 1})
    events = submit(g, {"type": "pass", "player": 0})
    if g.state.battle is not None and not any(e["type"] == "showdown" for e in events):
        events += submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    return next(e for e in events if e["type"] == "showdown")["attacker_total"], g


def test_m017_attack_power_plus_2000():
    base, _ = _m017_attack_total(False)
    boosted, g = _m017_attack_total(True)
    assert boosted == base + 2000
    assert g.state.players[0].mp == 10 - DB["S-009"].cost - 2


def test_m017_not_usable_when_defending():
    g, _ = mk(book("M-001", "S-029"), book("M-017", "S-009"))
    g.state.players[0].mp = g.state.players[1].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})                   # 輪到防方行動
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 1, "zone": "mamodo",
                   "slot_uid": g.state.players[1].slots[0].uid})
    assert e.value.code == "ability.condition"


@pytest.mark.parametrize("opp_page3,gain", [("E-003", 2), ("S-029", 0)])
def test_m018_gain_mp_if_opponent_open_pages_lack_defense(opp_page3, gain):
    # 對手翻開第 2、3 頁;第 2 頁固定為事件卡,第 3 頁決定有無可防禦的術
    g, _ = mk(book("M-018"), book("M-001", "E-003", opp_page3))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": g.state.players[0].slots[0].uid})
    assert g.state.players[0].mp == 5 - 1 + gain


def test_m030_skip_end_flip_on_last_page_once_per_game():
    g, _ = mk(book("M-030"), book("M-001"))
    ps = g.state.players[0]
    ps.pos = 30
    to_battle(g, 0)
    slot_uid = ps.slots[0].uid
    with pytest.raises(IllegalCommand) as e:                   # 不在最後一頁
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": slot_uid})
    assert e.value.code == "ability.condition"
    ps.pos = 32
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": slot_uid})
    submit(g, {"type": "pass", "player": g.state.action_player})
    submit(g, {"type": "pass", "player": g.state.action_player})
    assert g.state.phase == "start" and g.state.turn_player == 1 and ps.pos == 32   # 沒翻頁、沒敗北
    _end_turn(g)                                                # 對手回合結束,回到玩家 0
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": slot_uid})
    assert e.value.code == "ability.per_game"


def _use_ability(g, player, slot):
    return submit(g, {"type": "use_field_ability", "player": player, "zone": "mamodo",
                      "slot_uid": slot.uid})


def test_m016_swap_open_page_with_earlier_page_once_per_game():
    g, _ = mk(book("M-016", "E-003", "S-029", "E-004", "S-001"), book("M-001"))
    ps = g.state.players[0]
    to_battle(g, 0)
    slot = ps.slots[0]
    with pytest.raises(IllegalCommand) as e:                   # pos=2:沒有「之前的頁」
        _use_ability(g, 0, slot)
    assert e.value.code == "ability.condition"
    ps.pos = 4                                                  # 翻開 4、5;之前頁為 2、3
    _use_ability(g, 0, slot)
    assert g.state.pending.kind == "pick_own_open_page"
    assert [o["value"] for o in g.state.pending.options] == [4, 5]
    submit(g, {"type": "choose", "player": 0, "value": 4})
    assert g.state.pending.kind == "pick_own_earlier_page"
    assert [o["value"] for o in g.state.pending.options] == [2, 3]
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "choose", "player": 0, "value": 5})   # 不是之前的頁
    submit(g, {"type": "choose", "player": 0, "value": 2})
    assert (ps.card_at(2), ps.card_at(4)) == ("E-004", "E-003")
    _end_turn(g)
    _end_turn(g)
    with pytest.raises(IllegalCommand) as e:
        _use_ability(g, 0, slot)
    assert e.value.code == "ability.per_game"


def test_m022_discard_chosen_opponent_partner():
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-022"), book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    with pytest.raises(IllegalCommand) as e:                   # 對手沒有夥伴
        _use_ability(g, 0, slot)
    assert e.value.code == "ability.condition"
    opp = g.state.players[1]
    a = opp.slots[0]
    a.partner = "P-001"
    b = MamodoSlot(uid=g.state.next_uid(), stack=["M-004"], partner="P-002")
    opp.slots.append(b)
    _use_ability(g, 0, slot)
    assert g.state.pending.kind == "pick_opponent_partner"
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert b.partner is None and a.partner == "P-001" and "P-002" in opp.discard
    assert g.state.players[0].mp == 10 - 5


def test_m029_discards_injured_armor_and_m028_turns_attacker_pages():
    # M-029:棄掉對手 1 隻負傷魔物。目標是疊著 M-027 的 M-028 → 只有裝甲入墓(本體留下),
    # 觸發對手 M-028:「重なっているアーマー体が捨て札になったとき、相手の魔本を2枚めくる」
    from gash.engine.state import MamodoSlot
    g, _ = mk(book("M-029"), book("M-001"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    with pytest.raises(IllegalCommand) as e:                   # 對手沒有負傷魔物
        _use_ability(g, 0, slot)
    assert e.value.code == "ability.condition"
    opp = g.state.players[1]
    armored = MamodoSlot(uid=g.state.next_uid(), stack=["M-028", "M-027"], injured=True)
    opp.slots.append(armored)
    pos0 = g.state.players[0].pos
    events = _use_ability(g, 0, slot)
    assert armored in opp.slots and armored.stack == ["M-028"]
    assert "M-027" in opp.discard
    assert [e["type"] for e in events if e["type"] in ("stack_detached", "pages_turned")] == [
        "stack_detached", "pages_turned"]
    assert g.state.players[0].pos == pos0 + 4                   # 玩家 0 的魔本被翻 2 張


@pytest.mark.parametrize("spell,immune", [("S-001", True), ("S-029", False)])
def test_m031_immune_to_spell_damage_at_most_6000(spell, immune):
    # 攻方 M-001(4000)+ S-001(+2000)= 6000 → 免疫;+ S-029(+3000)= 7000 → 受傷
    g, _ = mk(book("M-001", spell), book("M-031"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    kyclops = g.state.players[1].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    assert g.state.pending.kind == "protect"
    events = submit(g, {"type": "choose", "player": 1, "value": kyclops.uid})   # 以キクロプ保護魔本
    prevented = [e for e in events if e["type"] == "damage_prevented" and e.get("reason") == "immunity"]
    assert bool(prevented) is immune
    assert kyclops.injured is (not immune)


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
    """防方不防禦、雙方戰鬥中 pass,推進到傷害/保護決策點。"""
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
    # 無術攻擊,防方無魔物可保護魔本(對手只有 1 隻魔物,可保護)→ 選不保護
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    while g.state.battle and g.state.battle.step == "effects" and g.state.pending is None:
        submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    # 合計魔力 5000 > 0,攻擊成功 → 進入保護決策或直接傷害
    if g.state.pending and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": 1, "value": None})  # 不保護
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
