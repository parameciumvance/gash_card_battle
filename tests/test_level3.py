"""第三彈卡片效果測試(card-effects「第三彈卡片分批開放」)。依日文效果文逐卡驗證可觀察的結果。

第 1 批:ブラゴ(M-033 / M-053 / P-021 / S-101)、ザバス(M-043 / P-029 / S-080 / S-081)、
バーゴ(M-044 / P-030 / S-082〜S-085)、ゾボロン(M-041 / P-027 / S-076 / S-077)、
事件 E-030 / E-032 / E-033 / E-038 / E-040。
"""

import json

import pytest

from gash.engine.cards import DATA_DIR, pending_cards
from gash.engine.engine import IllegalCommand, submit
from gash.engine.state import MamodoSlot
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle

BATCH1 = ("M-033", "M-053", "P-021", "S-101", "M-043", "P-029", "S-080", "S-081",
          "M-044", "P-030", "S-082", "S-083", "S-084", "S-085", "M-041", "P-027", "S-076", "S-077",
          "E-030", "E-032", "E-033", "E-038", "E-040")


def add_slot(g, player, *stack, partner=None):
    s = MamodoSlot(uid=g.state.next_uid(), stack=list(stack), partner=partner)
    g.state.players[player].slots.append(s)
    return s


def code(g, command):
    with pytest.raises(IllegalCommand) as e:
        submit(g, command)
    return e.value.code


def ability(player, slot, zone="mamodo"):
    return {"type": "use_field_ability", "player": player, "zone": zone, "slot_uid": slot.uid}


def attack(g, page, slot=None, defend_page=None):
    """玩家 0 宣告攻擊、玩家 1 迎戰;defend_page 為 None 時不防禦。停在戰鬥中效果的時機(攻方先)。"""
    cmd = {"type": "declare_attack", "player": 0, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    submit(g, cmd)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    if defend_page is None:
        submit(g, {"type": "no_defense", "player": 1})
    else:
        submit(g, {"type": "declare_defense", "player": 1, "page": defend_page})


def pass_effects(g):
    """雙方在戰鬥中效果的時機 pass,直到魔力勝負後出現決策或戰鬥結束。"""
    st = g.state
    while st.battle is not None and st.pending is None:
        submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})


def no_protect(g):
    while g.state.pending is not None and g.state.pending.kind == "protect":
        submit(g, {"type": "choose", "player": g.state.pending.player, "value": None})


def events_of(events, type_):
    return [e for e in events if e["type"] == type_]


# ---------------------------------------------------------------- 開放

def test_batch1_cards_are_open():
    assert not set(BATCH1) & pending_cards()
    listed = json.loads((DATA_DIR / "pending_cards.json").read_text(encoding="utf-8"))["cards"]
    assert len(listed) == 102 - len(BATCH1)


# ---------------------------------------------------------------- ブラゴ

def test_m033_discards_itself_and_adds_damage_to_spells_this_turn():
    # 《嘲笑》このカードを捨て札にする→【ステイ】このターン中、自分が使う、「魔物の効果」や術のダメージを+1する
    g, _ = mk(book("M-033", "S-001"), book("M-001"))
    st = g.state
    brago = st.players[0].slots[0]
    gash = add_slot(g, 0, "M-001")
    brago.partner = "P-021"
    st.players[0].mp = 10
    to_battle(g, 0)
    events = submit(g, ability(0, brago))
    assert brago not in st.players[0].slots
    assert {"M-033", "P-021"} <= set(st.players[0].discard)                # 費用:此魔物(與其搭檔)入墓
    assert events_of(events, "mamodo_discarded")[0]["reason"] == "cost"
    submit(g, {"type": "pass", "player": 1})
    pos1 = st.players[1].pos
    attack(g, 2, slot=gash)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 2                                # ザケル 1 + 1


def test_m033_adds_damage_to_counter():
    # 對手回合使用:之後以【反擊】戰術防禦獲勝,反擊傷害也 +1
    g, _ = mk(book("M-001", "S-001"), book("M-033", "S-030"))
    st = g.state
    brago = st.players[1].slots[0]
    gash = add_slot(g, 1, "M-001")
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, brago))
    pos0 = st.players[0].pos
    attack(g, 2, defend_page=2)
    assert st.battle.defense_slot == gash.uid
    pass_effects(g)
    no_protect(g)
    assert st.players[0].pos == pos0 + 2 * 2                                # ラシルド 反擊 1 + 1


def test_m033_only_outside_battle():
    g, _ = mk(book("M-001", "S-001"), book("M-033"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.timing"


def _attack_m053(spell, mp=10):
    g, _ = mk(book("M-001", spell), book("M-053"))
    st = g.state
    st.players[0].mp = mp
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    return g, st.players[1].slots[0]


def test_m053_protecting_one_damage_attack_takes_no_damage():
    # 《王の風格》この魔物は、1ダメージの攻撃によるダメージを受けない
    g, brago = _attack_m053("S-001")
    st = g.state
    pos1 = st.players[1].pos
    assert st.pending.kind == "protect"
    events = submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert brago in st.players[1].slots and not brago.injured
    assert st.players[1].pos == pos1
    assert events_of(events, "damage_prevented")[0]["reason"] == "immunity"


def test_m053_two_damage_attack_injures():
    g, brago = _attack_m053("S-002")
    submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert brago.injured


def test_m053_counts_damage_after_bonus():
    # 傷害值以加成後的攻擊傷害判定:ザケル + M-033 的 +1 = 2 → 受傷
    g, _ = mk(book("M-033", "S-001"), book("M-053"))
    st = g.state
    user = add_slot(g, 0, "M-001")
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    attack(g, 2, slot=user)
    pass_effects(g)
    brago = st.players[1].slots[0]
    submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert brago.injured


def test_p021_blocks_opponent_mp_reduction_this_turn():
    # 《あきらめぬ心》このカードを捨て札にする→【ステイ】このターン中、相手の効果によって自分のMPがへることはない
    g, _ = mk(book("M-033"), book("M-001", "E-018"))
    st = g.state
    slot = st.players[0].slots[0]
    slot.partner = "P-021"
    st.players[0].mp, st.players[1].mp = 8, 10
    to_battle(g, 0)
    submit(g, ability(0, slot, zone="partner"))
    assert "P-021" in st.players[0].discard
    events = submit(g, {"type": "use_book_card", "player": 1, "page": 2})   # 對手的 E-018
    assert st.players[0].mp == 8
    assert events_of(events, "mp_reduction_prevented")[0]["player"] == 0
    assert st.players[1].mp == 8                                            # 自己付的費用照常


def test_p021_does_not_block_own_costs_or_next_turn():
    g, _ = mk(book("M-033", "S-101"), book("M-001", "E-018"))
    st = g.state
    slot = st.players[0].slots[0]
    slot.partner = "P-021"
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    submit(g, ability(0, slot, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "pass", "player": 0})                                # 回合結束
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    before = st.players[0].mp
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    assert st.players[0].mp == before - 4


def test_s101_damages_book_and_all_mamodo():
    # 相手の魔物すべてを選ぶ。相手の魔本と、選んだ魔物すべてにダメージをあたえる
    g, _ = mk(book("M-033", "S-101"), book("M-001"))
    st = g.state
    add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    while st.pending is not None:
        kind = st.pending.kind
        submit(g, {"type": "choose", "player": 1, "value": 0 if kind == "damage_order" else None})
    assert st.players[1].pos == pos1 + 2 * 3
    assert all(s.injured for s in st.players[1].slots)


# ---------------------------------------------------------------- ザバス

def _zabas_defends(spell):
    g, _ = mk(book("M-001", spell), book("M-043"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 3
    to_battle(g, 0)
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    return g, st.players[1].slots[0]


def test_m043_negates_one_damage_attack():
    # 《鎧の羽》MPを1へらす→このバトルの、相手の1ダメージの攻撃1つを無効にする
    g, zabas = _zabas_defends("S-001")
    st = g.state
    pos1 = st.players[1].pos
    submit(g, ability(1, zabas))
    assert st.battle.attack_negated and st.players[1].mp == 2
    pass_effects(g)
    assert st.players[1].pos == pos1 and st.battle is None


def test_m043_stays_negated_when_damage_changes_later():
    # 發動當下判定;發動後攻擊傷害再被加成,已無效的攻擊維持無效
    g, zabas = _zabas_defends("S-001")
    st = g.state
    pos1 = st.players[1].pos
    submit(g, ability(1, zabas))
    st.battle.data["attack_damage_delta"] = 1                              # 之後的加成使傷害變為 2
    pass_effects(g)
    assert st.players[1].pos == pos1 and not st.players[1].slots[0].injured


def test_m043_rejects_two_damage_attack():
    g, zabas = _zabas_defends("S-002")
    assert code(g, ability(1, zabas)) == "ability.condition"
    assert g.state.players[1].mp == 3


def test_m043_not_against_own_attack():
    g, _ = mk(book("M-043", "S-080"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


def test_m043_only_in_battle():
    g, _ = mk(book("M-043"), book("M-001"))
    to_battle(g, 0)
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.timing"


def test_p029_zabas_uses_wind_spells_this_turn():
    # 《妖岩島の戦い》このカードを捨て札にする→【ステイ】このターン中、自分は、「ザバス」ですべての「風」属性の術を使える
    g, _ = mk(book("M-043", "S-037", "S-001"), book("M-001"))
    st = g.state
    zabas = st.players[0].slots[0]
    zabas.partner = "P-029"
    st.players[0].mp = 10
    to_battle(g, 0)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": zabas.uid}) == "spell.no_mamodo"
    submit(g, ability(0, zabas, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": zabas.uid})   # 風屬性 S-037
    assert g.state.battle_in is not None or g.state.battle is not None


def test_p029_not_other_attributes():
    g, _ = mk(book("M-043", "S-001"), book("M-001"))
    st = g.state
    zabas = st.players[0].slots[0]
    zabas.partner = "P-029"
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, zabas, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": zabas.uid}) == "spell.no_mamodo"


@pytest.mark.parametrize("heads, protectable", [(HEADS, False), (TAILS, True)])
def test_s081_coin_disables_protection(heads, protectable):
    # 相手の魔本にダメージ。コインを投げてオモテなら、相手は、この術のダメージを「かばう」ことができない
    g, _ = mk(book("M-043", "S-081"), book("M-001"))
    st = g.state
    g.rng = Rng(heads)
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    assert (st.pending is not None and st.pending.kind == "protect") == protectable
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_s081_no_coin_when_defending():
    g, _ = mk(book("M-001", "S-001"), book("M-043", "S-081"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    assert not [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") != "setup"]


# ---------------------------------------------------------------- バーゴ

def test_m044_moves_three_mp():
    # 《略奪》使用を宣言する→この効果は、相手のMPが8以上のとき使える。●相手のMPを3へらす。●自分のMPを3ふやす
    g, _ = mk(book("M-044"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 1, 8
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    assert (st.players[0].mp, st.players[1].mp) == (4, 5)


def test_m044_requires_opponent_mp_8():
    g, _ = mk(book("M-044"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 1, 7
    to_battle(g, 0)
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


def test_p030_gains_mp_when_opponent_uses_event():
    # 《羊泥棒》このカードが場にある→相手がイベントカード1つを使うたびに、自分のMPを2ふやす
    g, _ = mk(book("M-044", "E-024"), book("M-001", "E-024"))
    st = g.state
    st.players[0].slots[0].partner = "P-030"
    st.players[0].mp, st.players[1].mp = 0, 0
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})          # 自己的事件卡:不觸發
    if st.pending is not None:
        submit(g, {"type": "choose", "player": 0, "value": st.pending.options[0]["value"]})
    assert st.players[0].mp == 0
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})          # 對手的事件卡
    if st.pending is not None:
        submit(g, {"type": "choose", "player": 1, "value": st.pending.options[0]["value"]})
    assert st.players[0].mp == 2


@pytest.mark.parametrize("spell, heads, damage", [
    ("S-082", HEADS, 2), ("S-082", TAILS, 1), ("S-083", HEADS, 3), ("S-083", TAILS, 1)])
def test_s082_s083_coin_adds_damage(spell, heads, damage):
    # コインを投げてオモテなら、この術のダメージを+1(フレイド)/ +2(リン・フレイド)する
    g, _ = mk(book("M-044", spell), book("M-001"))
    st = g.state
    g.rng = Rng(heads)
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * damage


@pytest.mark.parametrize("heads, undefendable", [(HEADS, True), (TAILS, False)])
def test_s084_coin_makes_undefendable(heads, undefendable):
    # コインを投げてオモテなら、相手はこの術を防御できない
    g, _ = mk(book("M-044", "S-084"), book("M-001", "S-001"))
    st = g.state
    g.rng = Rng(heads)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    cmd = {"type": "declare_defense", "player": 1, "page": 2}
    if undefendable:
        assert code(g, cmd) == "defense.undefendable"
    else:
        submit(g, cmd)


@pytest.mark.parametrize("spell, mamodo, damage", [("S-080", "M-043", 2), ("S-085", "M-044", 3)])
def test_vanilla_spells(spell, mamodo, damage):
    g, _ = mk(book(mamodo, spell), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * damage


# ---------------------------------------------------------------- ゾボロン

def test_m041_attaches_hige_from_book():
    # 《奇妙なペット》MPを2へらす→自分の魔本の好きなページから、パートナーカード「ヒゲ」1枚を選び、場に出す
    g, _ = mk(book("M-041", "S-001", "S-001", "S-001", "S-001", "P-027"), book("M-001"))
    st = g.state
    zoboron = st.players[0].slots[0]
    st.players[0].mp = 3
    to_battle(g, 0)
    submit(g, ability(0, zoboron))                                         # 只有一張ヒゲ:自動選擇
    assert zoboron.partner == "P-027" and st.players[0].mp == 1
    assert 6 in st.players[0].consumed_pages


def test_m041_requires_hige_in_book():
    g, _ = mk(book("M-041"), book("M-001"))
    st = g.state
    st.players[0].mp = 3
    to_battle(g, 0)
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


def _hige_defender(attacker_extra=()):
    """玩家 1 的ゾボロン裝ヒゲ;玩家 0 以ザケル攻擊,停在玩家 1 使用戰鬥中效果的時機。"""
    g, _ = mk(book("M-001", "S-001"), book("M-041"))
    st = g.state
    for number in attacker_extra:
        add_slot(g, 0, number)
    zoboron = st.players[1].slots[0]
    zoboron.partner = "P-027"
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    return g, zoboron


def test_p027_protect_book_with_opponent_mamodo():
    # 《魔物の盾》このカードを捨て札にする→【スタンバイ】「ゾボロン」以外の相手の魔物1体を選ぶ。このバトル中、
    # 相手の攻撃で自分の魔本がダメージを受けるとき、そのダメージを、選んだ魔物で「かばう」ことができる
    g, zoboron = _hige_defender()
    st = g.state
    gash = st.players[0].slots[0]
    submit(g, ability(1, zoboron, zone="partner"))                        # 只有一個對象:自動選擇
    assert "P-027" in st.players[1].discard
    pos1 = st.players[1].pos
    pass_effects(g)
    assert st.pending.kind == "protect" and st.pending.player == 1
    assert {"player": 0, "value": gash.uid} in [{"player": o.get("player"), "value": o["value"]}
                                               for o in st.pending.options]
    opt = next(o for o in st.pending.options if o["value"] == gash.uid)
    assert opt["player"] == 0                                              # 選項標示保護者的持有者
    events = submit(g, {"type": "choose", "player": 1, "value": gash.uid})
    assert gash.injured and st.players[1].pos == pos1                      # 對手的魔物承受傷害
    prot = events_of(events, "protected")[0]
    assert (prot["player"], prot["slot"], prot["target"], prot["target_player"]) == (0, gash.uid, "book", 1)


def test_protect_option_player_is_receiver_normally():
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    own = st.players[1].slots[0]
    assert [o["player"] for o in st.pending.options if o["value"] is not None] == [1]
    events = submit(g, {"type": "choose", "player": 1, "value": own.uid})
    prot = events_of(events, "protected")[0]
    assert (prot["player"], prot["target_player"]) == (1, 1)


def test_p027_player_chooses_among_opponent_mamodo_except_zoboron():
    g, zoboron = _hige_defender(attacker_extra=("M-041", "M-002"))
    st = g.state
    gash, _, other = st.players[0].slots
    submit(g, ability(1, zoboron, zone="partner"))
    assert st.pending.player == 1
    assert [o["value"] for o in st.pending.options] == [gash.uid, other.uid]   # 對手的ゾボロン不能選
    assert code(g, {"type": "choose", "player": 1, "value": st.players[0].slots[1].uid}) == "choose.invalid"
    submit(g, {"type": "choose", "player": 1, "value": other.uid})
    pass_effects(g)
    protectors = [o["value"] for o in st.pending.options if o["value"] is not None]
    assert other.uid in protectors and gash.uid not in protectors


def test_p027_needs_target():
    g, zoboron = _hige_defender()
    st = g.state
    st.players[0].slots[0].stack = ["M-041"]                               # 對手只有ゾボロン
    assert code(g, ability(1, zoboron, zone="partner")) == "ability.condition"


def test_p027_only_this_battle():
    g, zoboron = _hige_defender()
    st = g.state
    gash = st.players[0].slots[0]
    submit(g, ability(1, zoboron, zone="partner"))
    assert [m.target_slot for m in st.modifiers if m.source == "P-027"] == [gash.uid]
    pass_effects(g)
    no_protect(g)
    assert st.battle is None and not [m for m in st.modifiers if m.source == "P-027"]


@pytest.mark.parametrize("spell", ["S-076", "S-077"])
def test_s076_s077_damaged_mamodo_discarded(spell):
    # 相手の魔本にダメージ。この術のダメージを受けた魔物は捨て札になる
    g, _ = mk(book("M-041", spell), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    protector = st.players[1].slots[0]
    attack(g, 2)
    pass_effects(g)
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    assert protector not in st.players[1].slots and "M-001" in st.players[1].discard


# ---------------------------------------------------------------- 事件卡

def _event(number, *, mp=10, book1=("M-001",)):
    g, _ = mk(book("M-001", number), book(*book1))
    g.state.players[0].mp = mp
    to_battle(g, 0)
    return g


def use_event(g, page=2):
    return submit(g, {"type": "use_book_card", "player": 0, "page": page})


def test_e030_discards_chosen_opponent_partner():
    # 相手の場のパートナー1枚を選び、捨て札にする
    g = _event("E-030")
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002", partner="P-002")
    a.partner = "P-001"
    use_event(g)
    assert st.pending.player == 0 and {o["value"] for o in st.pending.options} == {a.uid, b.uid}
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert b.partner is None and a.partner == "P-001" and "P-002" in st.players[1].discard


def test_e030_needs_opponent_partner():
    g = _event("E-030")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_e032_gains_5_mp():
    # 自分のMPを5ふやす
    g = _event("E-032", mp=2)
    use_event(g)
    assert g.state.players[0].mp == 5


def test_e033_returns_mamodo_to_empty_page():
    # 自分の捨て札の魔物カード1枚を選び、自分の魔本の空いてるページにもどす
    g = _event("E-033")
    ps = g.state.players[0]
    ps.discard = ["P-001", "M-002", "M-005"]
    ps.consumed_pages = {1, 7}
    use_event(g)
    pending = g.state.pending
    assert pending.player == 0 and [o["card"] for o in pending.options] == ["M-002", "M-005"]   # 只有魔物卡
    submit(g, {"type": "choose", "player": 0, "value": pending.options[1]["value"]})
    assert [o["value"] for o in g.state.pending.options] == [1, 7]
    submit(g, {"type": "choose", "player": 0, "value": 7})
    assert ps.book[6] == "M-005" and 7 not in ps.consumed_pages and ps.discard == ["P-001", "M-002"]


@pytest.mark.parametrize("discard, consumed", [(["P-001"], {1}), (["M-002"], set())])
def test_e033_needs_mamodo_and_empty_page(discard, consumed):
    g = _event("E-033")
    ps = g.state.players[0]
    ps.discard, ps.consumed_pages = discard, consumed
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_e038_gains_4_mp_at_end_phase():
    # 【スタンバイ】このターンのエンドフェイズに、自分のMPを4ふやす
    g = _event("E-038", mp=0)
    st = g.state
    use_event(g)
    assert st.players[0].mp == 0
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert st.turn_player == 1 and st.players[0].mp == 2 + 4                # 強制翻頁 +2、E-038 +4
    assert not [sb for sb in st.standby if sb.source == "E-038"]


def test_e040_heals_all_own_mamodo():
    # この効果は、自分の場に魔物が2体以上いれば使える。自分の場の魔物すべてを選び、「健康状態」にする
    g = _event("E-040")
    st = g.state
    a = st.players[0].slots[0]
    b = add_slot(g, 0, "M-002")
    a.injured = b.injured = True
    use_event(g)
    assert not a.injured and not b.injured


def test_e040_needs_two_mamodo():
    g = _event("E-040")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_e040_usable_without_injured_mamodo():
    g = _event("E-040")
    add_slot(g, 0, "M-002")
    use_event(g)
    assert g.state.players[0].used_event_this_turn


def test_effects_view_shows_amount_and_attr():
    from gash.api.views import snapshot
    g = _event("E-038")
    use_event(g)
    zabas = add_slot(g, 0, "M-043", partner="P-029")
    submit(g, {"type": "pass", "player": 1})
    submit(g, ability(0, zabas, zone="partner"))
    effects = {e["source"]: e for e in snapshot(g, 1)["effects"]}
    assert effects["E-038"]["amount"] == 4 and effects["E-038"]["kind"] == "end_phase_mp"
    assert (effects["P-029"]["mamodo"], effects["P-029"]["attr"]) == ("ザバス", "風")



def test_m053_immune_when_protecting_opponent_book_via_p027():
    # 「1ダメージの攻撃によるダメージを受けない」不限對手的攻擊:被 P-027 指定、替對手的魔書保護時也不受傷
    g, zoboron = _hige_defender(attacker_extra=("M-053",))
    st = g.state
    brago = st.players[0].slots[1]
    submit(g, ability(1, zoboron, zone="partner"))
    submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    pos1 = st.players[1].pos
    pass_effects(g)
    events = submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert not brago.injured and st.players[1].pos == pos1                  # ザケル(傷害 1):M-053 不受傷
    assert events_of(events, "damage_prevented")[0]["reason"] == "immunity"
