"""第三彈卡片效果測試(card-effects「第三彈卡片分批開放」)。依日文效果文逐卡驗證可觀察的結果。

第 1 批:ブラゴ(M-033 / M-053 / P-021 / S-101)、ザバス(M-043 / P-029 / S-080 / S-081)、
バーゴ(M-044 / P-030 / S-082〜S-085)、ゾボロン(M-041 / P-027 / S-076 / S-077)、
事件 E-030 / E-032 / E-033 / E-038 / E-040。
第 2 批:パピプリオ(M-040 / P-026 / S-073〜S-075)、ゼオン(M-051 / P-034 / S-099 / S-100)、
ロップス(M-038 / P-024 / S-069〜S-071)、ウォンレイ(M-042 / P-028 / S-078 / S-079)、事件 E-031 / E-036 / E-043。
第 3 批:エシュロス(M-037 / P-023 / S-065〜S-068)、ティオ(M-050 / P-033 / S-061 / S-096〜S-098)、
バリー(M-052 / P-035 / S-102〜S-106)、フリガロ(M-036 / P-022 / S-062〜S-064)、事件 E-028 / E-034 / E-035。
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
BATCH2 = ("M-040", "P-026", "S-073", "S-074", "S-075", "M-051", "P-034", "S-099", "S-100",
          "M-038", "P-024", "S-069", "S-070", "S-071", "M-042", "P-028", "S-078", "S-079",
          "E-031", "E-036", "E-043")
BATCH3 = ("M-037", "P-023", "S-065", "S-066", "S-067", "S-068", "M-050", "P-033", "S-061", "S-096", "S-097",
          "S-098", "M-052", "P-035", "S-102", "S-103", "S-104", "S-105", "S-106", "M-036", "P-022", "S-062",
          "S-063", "S-064", "E-028", "E-034", "E-035")


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
    assert not (set(BATCH1) | set(BATCH2) | set(BATCH3)) & pending_cards()
    listed = json.loads((DATA_DIR / "pending_cards.json").read_text(encoding="utf-8"))["cards"]
    assert len(listed) == 102 - len(BATCH1) - len(BATCH2) - len(BATCH3)


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


# ================================================================ 第 2 批

def restrict(g, target, flag, *, owner=None, slot=None, duration=None, source="TEST"):
    from gash.engine.effects.primitives import add_restriction
    from gash.engine.state import DUR_TURN
    m = add_restriction(g, [], source=source, owner=1 - target if owner is None else owner,
                        target_player=target, flag=flag, duration=duration or DUR_TURN)
    m.target_slot = slot
    return m


def declare(g, player, page, slot=None):
    cmd = {"type": "declare_attack", "player": player, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    return submit(g, cmd)


def pass_turn(g):
    """目前回合雙方 pass 結束回合,下一位回合玩家不翻頁進入戰鬥階段。"""
    st = g.state
    while st.phase == "battle" and st.battle is None and st.pending is None:
        submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})


# ---------------------------------------------------------------- 限制的分類、無視與移除

def test_m038_ignores_no_attack_spell():
    # 「術を使えない」含不能用戰術攻擊(P-014):M-038 的戰術照樣能用,其他魔物的戰術不行
    from gash.engine.state import NO_ATTACK_SPELL
    g, _ = mk(book("M-038", "S-070", "S-001"), book("M-001"))
    st = g.state
    rops = st.players[0].slots[0]
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp = 10
    to_battle(g, 0)
    st.players[0].pos = 2                                                     # 翻開第 2、3 頁
    restrict(g, 0, NO_ATTACK_SPELL, source="P-014")
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3, "slot_uid": gash.uid}) == "spell.attack_restricted"
    declare(g, 0, 2, rops)
    assert st.battle_in is not None


def test_m038_ignores_lock_on_itself():
    # 被 E-024 封鎖時,M-038 的戰術照樣能用(「術を使えない」),啟動效果的封鎖不受影響
    from gash.engine.state import MAMODO_LOCKED
    g, _ = mk(book("M-038", "S-070"), book("M-001"))
    st = g.state
    rops = st.players[0].slots[0]
    st.players[0].mp = 10
    to_battle(g, 0)
    restrict(g, 0, MAMODO_LOCKED, slot=rops.uid, source="E-024")
    declare(g, 0, 2, rops)
    assert st.battle_in is not None


def test_nonbattle_spell_blocked_by_no_spells():
    # 「術を使えない」不分戰鬥與非戰鬥(使用者確認):E-002 等生效時非戰鬥戰術也不能用
    from gash.engine.state import NO_SPELLS
    g, _ = mk(book("M-001", "S-026"), book("M-001"))
    to_battle(g, 0)
    restrict(g, 0, NO_SPELLS, source="E-002")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.restricted"


def _wonrei_defender(*extra, mp=10):
    """玩家 1 的場上:ウォンレイ(M-042)與 extra;回傳 (g, wonrei)。"""
    g, _ = mk(book("M-001", "S-001", "S-002"), book("M-042", "E-031"))
    for number in extra:
        add_slot(g, 1, number)
    g.state.players[0].mp, g.state.players[1].mp = 10, mp
    to_battle(g, 0)
    return g, g.state.players[1].slots[0]


def _protectors(g):
    return [o["value"] for o in g.state.pending.options if o["value"] is not None]


def test_p026_only_chosen_mamodo_protects():
    # 《羽交い絞め》【ステイ】相手の魔物を1体選ぶ。このターン中、相手は、その魔物以外の魔物で、ダメージを「かばう」ことができない
    g, wonrei = _wonrei_defender("M-001")
    st = g.state
    other = st.players[1].slots[1]
    st.players[0].slots[0].partner = "P-026"
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert st.pending.player == 0
    submit(g, {"type": "choose", "player": 0, "value": other.uid})
    submit(g, {"type": "pass", "player": 1})
    attack(g, 2)
    pass_effects(g)
    assert _protectors(g) == [other.uid]


def test_m042_protects_even_when_restricted():
    # 《守る王》MPを1へらす→【ステイ】このターン中、自分は「かばうことができない」ときにでも、この魔物でダメージを「かばう」ことができる
    g, wonrei = _wonrei_defender("M-001")
    st = g.state
    other = st.players[1].slots[1]
    restrict(g, 1, "protect_only", slot=other.uid, source="P-026")
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, wonrei))
    attack(g, 2)
    pass_effects(g)
    assert set(_protectors(g)) == {wonrei.uid, other.uid}


def test_e031_protects_even_when_spell_forbids():
    # 【ステイ】このターン中、自分は「かばうことができない」ときにも「かばう」ことができる(S-081 正面:不能保護此戰術的傷害)
    g, _ = mk(book("M-043", "S-081"), book("M-001", "E-031"))
    st = g.state
    g.rng = Rng(HEADS)
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    attack(g, 2)
    pass_effects(g)
    assert st.pending is not None and _protectors(g) == [st.players[1].slots[0].uid]


def test_m051_never_protects_and_takes_no_damage():
    # この魔物は「かばう」ことができない(「かばうことができる」ときにも)。《無敵》この魔物はダメージを受けない
    g, _ = mk(book("M-001", "S-058"), book("M-051", "E-031"))
    st = g.state
    zeon = st.players[1].slots[0]
    other = add_slot(g, 1, "M-001")
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})          # E-031 也不能讓它保護
    st.players[0].book[1] = "S-001"
    attack(g, 2)
    pass_effects(g)
    assert _protectors(g) == [other.uid]


def test_m051_immune_to_damage():
    g, _ = mk(book("M-051", "S-058"), book("M-051"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)                                                          # S-058:負傷代替,唯一對象 M-051
    assert not st.players[1].slots[0].injured


def test_p034_removes_own_spell_restrictions_whole():
    # 《氷の仮面》「ステイ」または「スタンバイ」している、自分が術を使えなくなる効果すべてを取りのぞく
    from gash.engine.state import MAMODO_LOCKED, NO_SPELLS
    g, _ = mk(book("M-051", "S-099"), book("M-001"))
    st = g.state
    zeon = st.players[0].slots[0]
    zeon.partner = "P-034"
    st.players[0].mp = 10
    to_battle(g, 0)
    restrict(g, 0, MAMODO_LOCKED, slot=zeon.uid, source="E-024")
    restrict(g, 0, NO_SPELLS, source="E-002")
    theirs = restrict(g, 1, NO_SPELLS, owner=0, source="E-002")
    events = submit(g, ability(0, zeon, zone="partner"))
    assert [m for m in st.modifiers if m.kind == "restriction"] == [theirs]  # 封鎖整個移除;對手的不移除
    assert sorted(events_of(events, "restrictions_removed")[0]["sources"]) == ["E-002", "E-024"]


def test_p034_removes_s074_standby():
    g, _ = mk(book("M-051"), book("M-040", "S-074"))
    st = g.state
    zeon = st.players[0].slots[0]
    zeon.partner = "P-034"
    st.players[1].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})             # 對手(玩家 1)的 S-074 指定賽昂
    assert any(sb.source == "S-074" for sb in st.standby)
    submit(g, ability(0, zeon, zone="partner"))
    assert not any(sb.source == "S-074" for sb in st.standby)


def test_e036_removes_both_players_three_kinds():
    # 「ステイ」または「スタンバイ」している、「術を使えない」「かばうことができない」「魔物の効果を使えない」効果すべてを取りのぞく
    from gash.engine.state import NO_DEFENSE, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_SPELLS
    g, _ = mk(book("M-001", "E-036"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    restrict(g, 0, NO_SPELLS, source="E-002")
    restrict(g, 1, NO_SPELLS, owner=0, source="E-002")
    restrict(g, 0, NO_MAMODO_EFFECTS, source="E-025")
    restrict(g, 0, "protect_only", slot=st.players[0].slots[0].uid, source="P-026")
    kept_partner = restrict(g, 0, NO_PARTNER_EFFECTS, source="E-008")
    kept_defense = restrict(g, 1, NO_DEFENSE, owner=0, source="S-073")
    from gash.engine.effects.primitives import schedule_standby
    schedule_standby(g, [], kind="no_protect_book", source="E-013", owner=1)
    use_event(g)
    assert [m for m in st.modifiers if m.kind == "restriction"] == [kept_partner, kept_defense]
    assert not [sb for sb in st.standby if sb.kind == "no_protect_book"]


# ---------------------------------------------------------------- パピプリオ

def test_m040_opponent_event_costs_one_more():
    # 《ダダっ子》このカードが場にある→相手が使うイベントカードのコストは1ふえる
    g, _ = mk(book("M-040"), book("M-001", "E-024"))
    st = g.state
    st.players[1].mp = 0
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.mp"
    st.players[1].mp = 1
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    assert st.players[1].mp == 0


def test_s073_opponent_cannot_defend_this_turn():
    # 【ステイ】このターン中、相手は防御できない
    g, _ = mk(book("M-040", "S-073", "S-001"), book("M-001", "S-001"))
    st = g.state
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    use_event(g)
    submit(g, {"type": "pass", "player": 1})
    st.players[0].pos = 2
    declare(g, 0, 3, gash)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert code(g, {"type": "declare_defense", "player": 1, "page": 2}) == "defense.restricted"


def test_s074_locks_chosen_mamodo_next_turn():
    # 次のターンのスタートフェイズまで【スタンバイ】し、次のターン中【ステイ】。相手の魔物1体を選ぶ。次のターン中、その魔物の「魔物の効果」や術を使えない
    g, _ = mk(book("M-040", "S-074"), book("M-001", "S-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    use_event(g)                                                             # 對手只有 1 隻:自動選擇
    assert not [m for m in st.modifiers if m.kind == "restriction"]          # 本回合尚未封鎖
    pass_turn(g)
    assert code(g, {"type": "declare_attack", "player": 1, "page": 2}) == "spell.mamodo_locked"


def test_s075_lasts_until_users_next_turn():
    # 【ステイ】次の自分のターンのエンドフェイズまで、自分も相手も、「魔物の効果」や術を使えない
    g, _ = mk(book("M-040", "S-075"), book("M-001", "S-001"))
    st = g.state
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp, st.players[1].mp = 10, 10
    st.players[0].book[2] = "S-001"
    to_battle(g, 0)
    use_event(g)
    pass_turn(g)                                                             # 對手的回合
    st.players[1].pos = 1
    assert code(g, {"type": "declare_attack", "player": 1, "page": 2}) == "spell.restricted"
    pass_turn(g)                                                             # 使用者的下一個回合
    st.players[0].pos = 2
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3, "slot_uid": gash.uid}) == "spell.restricted"
    pass_turn(g)                                                             # 再下一個回合:恢復
    st.players[1].pos = 1
    declare(g, 1, 2)
    assert st.battle_in is not None


def test_s075_blocks_mamodo_effects():
    g, _ = mk(book("M-040", "S-075"), book("M-044"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    use_event(g)
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.mamodo_restricted"
    pass_turn(g)                                                             # 對手的回合
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.mamodo_restricted"


# ---------------------------------------------------------------- ゼオン

def test_s100_damages_even_when_defender_wins():
    # 魔力勝負の勝敗にかかわらず、相手の魔本にダメージ。相手はこの術を防御できない
    g, _ = mk(book("M-051", "S-100"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].slots[0].stack = ["M-051"]                                  # 防方魔物 6000,攻方合計 6000 不勝
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.battle.attack_undefendable
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_s100_no_damage_when_negated():
    g, _ = mk(book("M-051", "S-100"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    st.battle.attack_negated = True
    pass_effects(g)
    assert st.players[1].pos == pos1 and st.battle is None


@pytest.mark.parametrize("spell, mamodo, damage", [("S-099", "M-051", 1), ("S-071", "M-038", 4)])
def test_batch2_vanilla_spells(spell, mamodo, damage):
    g, _ = mk(book(mamodo, spell), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * damage


# ---------------------------------------------------------------- ロップス

@pytest.mark.parametrize("heads, damage", [(HEADS, 1), (TAILS, 0)])
def test_s069_attack_undefendable_coin_damage(heads, damage):
    # ●攻撃に使ったとき相手は、この攻撃を防御できない。コインを投げてオモテなら、相手の魔本にダメージ
    g, _ = mk(book("M-038", "S-069"), book("M-001"))
    st = g.state
    g.rng = Rng(heads)
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.battle.attack_undefendable
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * damage


@pytest.mark.parametrize("heads, negated", [(HEADS, True), (TAILS, False)])
def test_s069_defense_coin_negates(heads, negated):
    # ●防御に使ったとき魔力勝負の勝敗にかかわらず、コインを投げてオモテなら、相手の攻撃を無効にする
    g, _ = mk(book("M-001", "S-005"), book("M-038", "S-069"))
    st = g.state
    g.rng = Rng(heads)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    assert st.battle.attack_negated == negated


@pytest.mark.parametrize("pick_book", [True, False])
def test_s070_attacker_chooses_book_or_mamodo(pick_book):
    # 次の効果の1つを使う。●相手の魔本にダメージ。●相手の魔物1体を選び、ダメージをあたえる(宣告時選擇)
    g, _ = mk(book("M-038", "S-070"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.pending.player == 0 and st.pending.kind == "pick_effect"
    submit(g, {"type": "choose", "player": 0, "value": "book" if pick_book else "mamodo"})
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    no_protect(g)
    target = st.players[1].slots[0]
    if pick_book:
        assert st.players[1].pos == pos1 + 2 * 2 and not target.injured
    else:
        assert st.players[1].pos == pos1 and target.injured


# ---------------------------------------------------------------- ウォンレイ

def test_p028_negates_wonrei_first_damage():
    # 《好きある!》【スタンバイ】このバトル中1回だけ、「ウォンレイ」がダメージを受けるとき、そのダメージを受けない
    g, wonrei = _wonrei_defender()
    st = g.state
    wonrei.partner = "P-028"
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, wonrei, zone="partner"))
    pass_effects(g)
    submit(g, {"type": "choose", "player": 1, "value": wonrei.uid})        # 以ウォンレイ保護
    assert not wonrei.injured


def test_s078_discards_card_from_opponent_open_pages():
    # 相手の魔本か魔物にダメージをあたえたとき、相手の魔本を見て、今のページのカード1枚を選び、捨て札にする
    # 造成傷害後才檢視:對手翻開第 2、3 頁,受到傷害 2 → 翻開第 6、7 頁
    g, _ = mk(book("M-042", "S-078"), book("M-001", "S-001", "S-001", "S-001", "S-001", "S-001", "E-024"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].open_pages() == [6, 7]
    assert st.pending.player == 0 and {o["page"] for o in st.pending.options} == {6, 7}
    submit(g, {"type": "choose", "player": 0, "value": 7})
    assert "E-024" in st.players[1].discard and 7 in st.players[1].consumed_pages


@pytest.mark.parametrize("protect_with_wonrei", [True, False])
def test_s079_wonrei_protector_takes_no_damage(protect_with_wonrei):
    # 魔力勝負の勝敗にかかわらず、自分が相手の攻撃のダメージを「ウォンレイ」で「かばう」とき、その「ウォンレイ」はダメージを受けない
    g, _ = mk(book("M-001", "S-005"), book("M-042", "S-079"))
    st = g.state
    wonrei = st.players[1].slots[0]
    other = add_slot(g, 1, "M-002")
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    pass_effects(g)
    protector = wonrei if protect_with_wonrei else other
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    assert protector.injured != protect_with_wonrei


# ---------------------------------------------------------------- 事件

def test_e043_opponent_chooses_and_others_locked():
    # 【ステイ】相手は、相手の魔物1体を選ぶ。このターン中、相手は選んだ魔物以外の魔物の「魔物の効果」や術を使えず、
    # 選んだ魔物以外の魔物で「かばう」ことはできない
    g, _ = mk(book("M-001", "E-043", "S-001"), book("M-001", "S-001"))
    st = g.state
    kept = st.players[1].slots[0]
    other = add_slot(g, 1, "M-044")
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    use_event(g)
    assert st.pending.player == 1
    submit(g, {"type": "choose", "player": 1, "value": kept.uid})
    assert code(g, ability(1, other)) == "ability.mamodo_locked"
    submit(g, {"type": "pass", "player": 1})
    st.players[0].pos = 2
    declare(g, 0, 3)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert _protectors(g) == [kept.uid]


def test_e043_usable_without_opponent_mamodo():
    g, _ = mk(book("M-001", "E-043"), book("M-001"))
    st = g.state
    st.players[1].slots.clear()
    to_battle(g, 0)
    use_event(g)
    assert st.players[0].used_event_this_turn


# ---------------------------------------------------------------- 快照與 NPC

def test_p024_reveals_opponent_open_pages():
    # 《予測》このカードが場にある→相手は、相手の魔本の今のページが見えるようにプレイする
    from gash.api.views import snapshot
    from gash.npc.determinize import known_opponent_pages
    g, _ = mk(book("M-038"), book("M-001", "S-001"))
    st = g.state
    to_battle(g, 0)
    pages = lambda viewer: snapshot(g, viewer)["players"][1]["open_pages"]  # noqa: E731
    assert all("card" not in e for e in pages(0))
    st.players[0].slots[0].partner = "P-024"
    assert [e["card"] for e in pages(0)] == [st.players[1].card_at(p) for p in st.players[1].open_pages()]
    assert all("card" not in e for e in pages(None))                        # 觀戰者不變
    assert set(known_opponent_pages(g, 0)) >= set(st.players[1].open_pages())


def test_event_cost_in_snapshot_includes_m040():
    from gash.api.views import snapshot
    g, _ = mk(book("M-040"), book("M-001", "E-024"))
    to_battle(g, 0)
    entry = next(e for e in snapshot(g, 1)["players"][1]["open_pages"] if e["page"] == 2)
    assert entry["cost"] == 1


# ================================================================ 第 3 批

def battle_in(g, page, slot=None, player=0):
    cmd = {"type": "declare_attack", "player": player, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    submit(g, cmd)
    submit(g, {"type": "battle_in_response", "player": 1 - player, "allow": True})


def choose(g, value):
    return submit(g, {"type": "choose", "player": g.state.pending.player, "value": value})


def finish_damage(g):
    """處理受傷順序 / 保護(一律不保護、順序取第一項)。"""
    st = g.state
    while st.pending is not None and st.pending.kind in ("protect", "damage_order"):
        choose(g, 0 if st.pending.kind == "damage_order" else None)


# ---------------------------------------------------------------- エシュロス

@pytest.mark.parametrize("extra, mp_left, damage", [(0, 4, 1), (2, 2, 2), (4, 0, 3)])
def test_s067_extra_cost(extra, mp_left, damage):
    # この術を使うとき、追加でコストを2ふやすごとに、この術の魔力を+2000、ダメージを+1することができる(追加は6まで)
    g, _ = mk(book("M-037", "S-067"), book("M-001"))
    st = g.state
    st.players[0].mp = 6
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert st.pending.kind == "spell_extra_cost" and st.pending.player == 0
    assert [o["value"] for o in st.pending.options] == [0, 2, 4]          # MP 6:費用 2 + 追加至多 4
    choose(g, extra)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == mp_left
    attack_items = st.battle.data.get("attack_spell_power", [])
    assert sum(i["amount"] for i in attack_items) == 1000 * extra
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * damage


def no_defense_pass(g):
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)


def test_s067_no_extra_when_unaffordable():
    g, _ = mk(book("M-037", "S-067"), book("M-001"))
    st = g.state
    st.players[0].mp = 3
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert st.pending is None and st.battle_in is not None                    # 只有追加 0:不詢問


def test_s066_counter_when_defending():
    # 相手の魔本にダメージ。【カウンター】魔力勝負で勝ったとき、相手の魔本にダメージ
    g, _ = mk(book("M-001", "S-001"), book("M-037", "S-066"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos0 = st.players[0].pos
    attack(g, 2, defend_page=2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].pos == pos0 + 2 * 1


@pytest.mark.parametrize("heads", [True, False])
def test_s068_restriction_after_battle(heads):
    # 【ステイ】魔力勝負の勝敗にかかわらず、コインを投げてオモテなら、このバトルの終了後、このターン中、相手は術を使えない
    g, _ = mk(book("M-037", "S-068"), book("M-001", "S-002"))
    st = g.state
    g.rng = Rng(HEADS if heads else TAILS)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    events = []
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    events += submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert [e["source"] for e in events if e["type"] == "coin_flipped"] == ["S-068"]   # 宣告時擲
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})             # 本場戰鬥中仍可用戰術
    pass_effects(g)
    finish_damage(g)
    assert st.battle is None
    blocked = [m for m in st.modifiers if m.source == "S-068" and m.target_player == 1]
    assert bool(blocked) == heads


def test_s068_not_applied_when_attack_negated():
    g, _ = mk(book("M-037", "S-068"), book("M-001"))
    st = g.state
    g.rng = Rng(HEADS)
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    st.battle.attack_negated = True
    pass_effects(g)
    assert st.battle is None and not [m for m in st.modifiers if m.source == "S-068"]


def test_s068_pending_removed_by_e036():
    from gash.engine.engine import remove_restrictions
    g, _ = mk(book("M-037", "S-068"), book("M-001"))
    st = g.state
    g.rng = Rng(HEADS)
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    remove_restrictions(g, [], 1, {"spells"}, "both")                         # 排定期間的待命也能移除
    pass_effects(g)
    finish_damage(g)
    assert not [m for m in st.modifiers if m.source == "S-068"]


def test_m037_spell_from_next_two_spreads():
    # 《エリート》MPを2へらす→【スタンバイ】このターン中の次のバトルで、自分の魔本の今のページから2枚後ろまでの
    # ページの「エシュロス」の術1つを使える(翻開第 2、3 頁 → 第 4〜7 頁)
    g, _ = mk(book("M-037", "S-001", "S-001", "S-001", "S-065", "S-001", "S-065", "S-065"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 5}) == "page.not_open"
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "declare_attack", "player": 0, "page": 8}) == "page.not_open"   # 範圍外
    battle_in(g, 5)
    assert st.battle is not None and st.battle.attack_page == 5


def test_p023_mp_then_bonus_on_first_eshros_spell():
    # 《僕の意思》●自分のＭＰを2ふやす。●【スタンバイ】このターン中のバトルで、自分の「エシュロス」の術1つの魔力を＋2000
    g, _ = mk(book("M-037", "S-065", "S-065"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-023"
    st.players[0].mp = 4
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert st.players[0].mp == 6
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2)
    assert sum(i["amount"] for i in st.battle.data.get("attack_spell_power", [])) == 2000
    no_defense_pass(g)
    finish_damage(g)
    battle_in(g, 3)
    assert not st.battle.data.get("attack_spell_power")                       # 只有一張


# ---------------------------------------------------------------- ティオ

def test_s061_counter_equals_attack_damage():
    # 【カウンター】魔力勝負で勝ったとき、相手の魔本にダメージ。ダメージの値は、相手の攻撃のダメージと同じ
    g, _ = mk(book("M-001", "S-005"), book("M-050", "S-061"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos0 = st.players[0].pos
    attack(g, 2, defend_page=2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].pos == pos0 + 2 * 3                                   # バオウ・ザケルガ 傷害 3


@pytest.mark.parametrize("extra", [0, 2])
def test_s097_extra_cost_defense(extra):
    # この術を使うとき、追加でコストを2ふやせば、この術の魔力を+4000することができる
    g, _ = mk(book("M-001", "S-001"), book("M-050", "S-097"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    to_battle(g, 0)
    attack_cmd = {"type": "declare_defense", "player": 1, "page": 2}
    battle_in(g, 2)
    submit(g, attack_cmd)
    assert st.pending.kind == "spell_extra_cost" and [o["value"] for o in st.pending.options] == [0, 2]
    choose(g, extra)
    assert st.players[1].mp == 5 - 3 - extra
    assert sum(i["amount"] for i in st.battle.data.get("defense_spell_power", [])) == 2000 * extra


def test_m050_other_mamodo_plus_2000():
    # 《私たちは1人じゃない》使用を宣言する→【ステイ】自分の他の魔物1体を選ぶ。このターン中、その魔物の魔力を+2000
    from gash.engine.engine import slot_power
    g, _ = mk(book("M-050"), book("M-001"))
    st = g.state
    tia = st.players[0].slots[0]
    to_battle(g, 0)
    assert code(g, ability(0, tia)) == "ability.condition"
    other = add_slot(g, 0, "M-001")
    submit(g, ability(0, tia))
    assert slot_power(g, 0, other) == 4000 + 2000


def test_p033_chosen_mamodo_cannot_attack_with_spells():
    # 《私達は一人じゃない》【ステイ】相手の魔物1体を選ぶ。このターン中、相手はその魔物の術で攻撃できない
    g, _ = mk(book("M-001", "S-001", "S-002"), book("M-050"))
    st = g.state
    gash = st.players[0].slots[0]
    st.players[1].slots[0].partner = "P-033"
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))             # 對手只有賈修:自動選擇
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2}) == "spell.attack_restricted"


def _s098_after_attack(injured=True):
    """玩家 0:ティオ(M-050)與賈修;已用第 3 頁的 S-001 與第 4 頁的 S-002 攻擊,接著翻開第 2 頁的 S-098。"""
    g, _ = mk(book("M-050", "S-098", "S-001", "S-002"), book("M-001"))
    st = g.state
    tia = st.players[0].slots[0]
    tia.injured = injured
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp = 20
    to_battle(g, 0)
    for page in (3, 4):
        st.players[0].pos = 3
        battle_in(g, page, gash)
        no_defense_pass(g)
        finish_damage(g)
    st.players[0].pos = 2
    return g, tia, gash


def test_s098_heal_then_choose_spell_to_reuse():
    # 次の効果の、片方または両方を、この順で使う。●負傷状態の魔物1体を「健康状態」にする。
    # ●【スタンバイ】このターン中すでに自分が使った、術1つを、コスト0で、もう1回使えるようにする(使用時選定)
    g, tia, gash = _s098_after_attack()
    st = g.state
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) in ("spell.used", "page.not_open")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": tia.uid})
    assert st.pending.kind == "pick_effect" and {o["value"] for o in st.pending.options} == {"heal", None}
    choose(g, "heal")
    assert not tia.injured
    assert st.pending.kind == "pick_used_spell" and {o["value"] for o in st.pending.options} == {3, 4, None}
    choose(g, 3)                                                               # 選定第 3 頁的 S-001
    submit(g, {"type": "pass", "player": 1})
    st.players[0].pos = 3
    assert code(g, {"type": "declare_attack", "player": 0, "page": 4, "slot_uid": gash.uid}) == "spell.used"
    mp = st.players[0].mp
    battle_in(g, 3, gash)                                                      # 選定的那一張:費用 0
    assert st.players[0].mp == mp and st.battle is not None
    no_defense_pass(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) == "spell.used"   # 只有一次


def test_s098_skip_heal_then_choose_spell():
    g, tia, gash = _s098_after_attack()
    st = g.state
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": tia.uid})
    choose(g, None)                                                            # 不回復:至少一個,直接選重用
    assert tia.injured
    assert st.pending.kind == "pick_used_spell" and None not in {o["value"] for o in st.pending.options}
    choose(g, 4)
    assert [sb.data.get("page") for sb in st.standby if sb.kind == "spell_reuse"] == [4]


def test_s098_no_injured_goes_to_spell_choice():
    g, tia, gash = _s098_after_attack(injured=False)
    st = g.state
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": tia.uid})
    assert st.pending.kind == "pick_used_spell"


def test_s098_needs_injured_or_used_spell():
    g, _ = mk(book("M-050", "S-098"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


def test_e034_puts_tia_and_megumi():
    # 自分の魔本の好きなページから、魔物カード「ティオ」とパートナーカード「大海恵」をそれぞれ1枚まで選び、場に出す
    g, _ = mk(book("M-001", "E-034", "S-001", "S-001", "M-050", "P-009"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    use_event(g)
    while st.pending is not None:
        choose(g, next(o["value"] for o in st.pending.options if o["value"] is not None))
    tia = next(s for s in st.players[0].slots if s.top == "M-050")
    assert tia.partner == "P-009"


def test_e034_needs_target():
    g, _ = mk(book("M-001", "E-034"), book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- バリー

def test_m052_only_when_this_mamodo_attacks():
    # 《強き王》MPを1へらす→【ステイ】このターン中、自分がこの魔物で攻撃するバトル中、この魔物の魔力を+1000し、
    # 攻撃のダメージを1ふやす
    g, _ = mk(book("M-052", "S-102", "S-001"), book("M-001"))
    st = g.state
    barry = st.players[0].slots[0]
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, ability(0, barry))
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3, gash)                                                      # 賈修攻擊:不套用
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 1
    battle_in(g, 2, barry)
    from gash.engine.engine import side_breakdown
    assert side_breakdown(g, st.battle, "attack")[0] == 5000 + 1000 + 2000
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 1 + 2 * 2


def test_p035_reduces_twice_start_phase_gain():
    # 《強さの哲学》相手がこのターンのスタートフェイズにふやしたＭＰの数×２だけ、相手のＭＰをへらす
    g, _ = mk(book("M-052"), book("M-001"))
    st = g.state
    barry = st.players[0].slots[0]
    barry.partner = "P-035"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "flip_pages", "player": 1, "count": 2})               # 對手開始階段 +4
    before = st.players[1].mp
    submit(g, {"type": "pass", "player": 1})
    submit(g, ability(0, barry, zone="partner"))
    assert st.players[1].mp == max(0, before - 8)


def test_s104_damage_plus_two_without_spells_on_open_pages():
    # 相手の魔本を見て、今のページに術カードがないとき、この術のダメージを+2(攻擊成功時才檢視判斷,使用者確認)
    g, _ = mk(book("M-052", "S-104"), book("M-001", "E-024", "E-024"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    assert not [e for e in g.events if e["type"] == "pages_peeked"]            # 宣告時不檢視
    pass_effects(g)
    assert [e for e in g.events if e["type"] == "pages_peeked" and e["viewer"] == 0]
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 4


def test_s104_no_peek_when_attack_fails():
    g, _ = mk(book("M-052", "S-104"), book("M-001", "E-024", "E-024"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    st.battle.attack_negated = True
    pass_effects(g)
    assert st.battle is None and not [e for e in g.events if e["type"] == "pages_peeked"]


def test_s104_no_bonus_with_spell():
    g, _ = mk(book("M-052", "S-104"), book("M-001", "S-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_s103_sets_battle_restriction():
    # このバトル中、魔力勝負以降に、相手は魔本のカードの効果を新たに使えない
    g, _ = mk(book("M-052", "S-103"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    assert st.pending is not None and st.pending.kind == "protect"            # 傷害處理中:限制已設置
    assert [m.flag for m in st.modifiers if m.source == "S-103"] == ["no_book_cards"]
    finish_damage(g)
    assert not [m for m in st.modifiers if m.source == "S-103"]               # 戰鬥結束時移除


def test_s106_negates_and_turns_own_page():
    # 魔力勝負の勝敗にかかわらず、相手の攻撃を無効にする。そうしたなら、自分の魔本を1枚めくる
    g, _ = mk(book("M-001", "S-005"), book("M-052", "S-106"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2, defend_page=2)
    assert st.battle.attack_negated and st.players[1].pos == pos1 + 2
    pass_effects(g)
    assert st.battle is None and st.players[1].pos == pos1 + 2


@pytest.mark.parametrize("spell, mamodo, damage", [("S-065", "M-037", 1), ("S-096", "M-050", 1),
                                                   ("S-102", "M-052", 1), ("S-105", "M-052", 3)])
def test_batch3_vanilla_spells(spell, mamodo, damage):
    g, _ = mk(book(mamodo, spell), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * damage


# ---------------------------------------------------------------- フリガロ

def test_m036_uses_other_ice_spells():
    g, _ = mk(book("M-036", "S-006"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    battle_in(g, 2, st.players[0].slots[0])
    assert st.battle is not None


def test_p022_redirects_furigaro_damage():
    # 《氷の戦い》【スタンバイ】相手の魔物1体を選ぶ。このターン中の次のバトルで、自分が「フリガロ」の術で攻撃するとき、
    # その術のダメージは、選んだ魔物にあたえられる
    g, _ = mk(book("M-036", "S-062"), book("M-001"))
    st = g.state
    furi = st.players[0].slots[0]
    furi.partner = "P-022"
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    submit(g, ability(0, furi, zone="partner"))
    choose(g, b.uid)
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2)
    assert st.pending is None                                                  # 對象已選,不再詢問
    no_defense_pass(g)
    finish_damage(g)
    assert b.injured and not a.injured and st.players[1].pos == pos1


def test_s062_ice_bonus_after_battle_no_stack():
    # 【ステイ】魔力勝負の勝敗にかかわらず、このバトル後、次の自分のターンのエンドフェイズまで、
    # 自分と相手が使う「氷」属性の術の魔力は+2000される(重複しない)
    g, _ = mk(book("M-036", "S-062", "S-062"), book("M-001"))
    st = g.state
    st.players[0].mp = 20
    to_battle(g, 0)
    from gash.engine.engine import side_breakdown

    def bonus():
        return sum(i["amount"] for i in side_breakdown(g, st.battle, "attack")[1] if i["kind"] == "attr_power")
    battle_in(g, 2)
    assert bonus() == 0                                                        # 本場戰鬥不受影響
    no_defense_pass(g)
    finish_damage(g)
    battle_in(g, 3)
    assert bonus() == 2000
    no_defense_pass(g)
    finish_damage(g)
    assert len([m for m in st.modifiers if m.source == "S-062"]) == 1          # 不重複


def test_s064_target_at_declaration():
    g, _ = mk(book("M-036", "S-064"), book("M-001"))
    st = g.state
    b = add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    battle_in(g, 2)
    assert st.pending.kind == "injure_instead_target"
    choose(g, b.uid)
    no_defense_pass(g)
    finish_damage(g)
    assert b.injured


# ---------------------------------------------------------------- 事件

def _reduced_by_opponent(g):
    """玩家 0 的回合:玩家 1 以 E-018 減少玩家 0 的 MP 4。"""
    st = g.state
    st.players[1].book[1] = "E-018"
    st.players[1].mp = 5
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})


def test_e028_gains_reduced_total():
    # この効果は、このターン中に、相手の効果で自分のMPがへらされていれば使える。へらされたMPの合計だけ、自分のMPをふやす
    g, _ = mk(book("M-001", "E-028"), book("M-001"))
    st = g.state
    st.players[0].mp = 6
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"
    _reduced_by_opponent(g)
    assert st.players[0].mp == 2
    use_event(g)
    assert st.players[0].mp == 6


def test_e035_turns_opponent_pages():
    g, _ = mk(book("M-001", "E-035"), book("M-001"))
    st = g.state
    st.players[0].mp = 6
    to_battle(g, 0)
    _reduced_by_opponent(g)
    pos1 = st.players[1].pos
    use_event(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_mp_reduction_record_excludes_guarded_and_costs():
    from gash.engine.state import DUR_TURN
    from gash.engine.effects.primitives import add_modifier
    g, _ = mk(book("M-001", "E-028"), book("M-001"))
    st = g.state
    st.players[0].mp = 6
    to_battle(g, 0)
    add_modifier(g, [], kind="mp_guard", source="P-021", owner=0, duration=DUR_TURN, target_player=0)
    _reduced_by_opponent(g)                                                    # P-021 擋下:不算
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_npc_answers_extra_cost_and_s098():
    import random
    from gash import npc
    g, _ = mk(book("M-037", "S-067"), book("M-001"))
    g.state.players[0].mp = 8
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert g.state.pending.kind == "spell_extra_cost"
    cmd, _ = npc.submit_ranked(g, 0, npc.decide(g, 0, "normal", random.Random(0)))
    assert cmd["type"] == "choose" and g.state.pending is None


def test_s098_target_in_effects_and_event():
    # 作用中效果與記錄看得出 S-098 選定的戰術
    from gash.api.views import snapshot
    g, tia, gash = _s098_after_attack(injured=False)
    st = g.state
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": tia.uid})
    events = choose(g, 4)
    entry = next(e for e in snapshot(g, 1)["effects"] if e["kind"] == "spell_reuse")
    assert (entry["card"], entry["page"]) == ("S-002", 4)
    ev = next(e for e in events if e["type"] == "standby_set" and e["kind"] == "spell_reuse")
    assert (ev["card"], ev["page"]) == ("S-002", 4)
