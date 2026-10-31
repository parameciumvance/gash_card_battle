"""「〇〇の術」的判定(card-effects「『〇〇の術』的判定」):戰術卡的對應魔物是 X,或由名稱 X 的魔物使用。

指示詞(この / その / 選んだ魔物)以那隻魔物的名稱代入 X;「魔物の効果」與「かばう」的限制只看選定的那一隻。
"""

from gash.engine.engine import mamodo_effect_block, submit
from tests.test_level2 import DB, HEADS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, use_event


def next_turn(g):
    """玩家 0 的行動剛 pass 給對手、對手也 pass 之後:玩家 0 再 pass 結束回合,玩家 1 不翻頁進入戰鬥階段。"""
    submit(g, {"type": "pass", "player": 0})
    to_battle(g, 1)


def defend_code(g, page=2, slot=None):
    cmd = {"type": "declare_defense", "player": 1, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    return code(g, cmd)


# ---------------------------------------------------------------- 加成類:其他魔物使用 X 的戰術

def _zeon_with_gash_partner(partner):
    """玩家 0:M-029 ゼオン(第 2 頁 S-001「ザケル」)與帶 partner 的 ガッシュ・ベル;使用該搭檔效果。"""
    g, _ = mk(book("M-029", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].mp = 10
    zeon = st.players[0].slots[0]
    gash = add_slot(g, 0, "M-001", partner=partner)
    to_battle(g, 0)
    submit(g, ability(0, gash, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    return g, zeon, gash


def test_p001_applies_when_zeon_uses_zakeru():
    # 自分が「ガッシュ・ベル」の術で攻撃するとき、相手は防御できない。M-029 使用的「ザケル」是 ガッシュ・ベル 的戰術
    g, zeon, _ = _zeon_with_gash_partner("P-001")
    battle_in(g, 2, slot=zeon)
    assert defend_code(g) == "defense.undefendable"


def test_ex007_applies_when_zeon_uses_zakeru():
    # 自分の「ガッシュ・ベル」の術1つの、本来のコストを0にする
    g, zeon, _ = _zeon_with_gash_partner("Ex-007")
    mp = g.state.players[0].mp
    battle_in(g, 2, slot=zeon)
    assert g.state.players[0].mp == mp


def _m054(attacker_top):
    g, _ = mk(book("M-054", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].mp = 10
    to_battle(g, 0)
    m054 = st.players[0].slots[0]
    other = add_slot(g, 0, attacker_top)
    g.rng = Rng(HEADS)
    submit(g, ability(0, m054))
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2, slot=other)
    return g


def test_m054_applies_to_another_gash():
    # 自分がこの魔物の術で攻撃したとき → 「この魔物」= ガッシュ・ベル,同名的另一隻使用的戰術也算
    assert defend_code(_m054("M-001")) == "defense.undefendable"


def test_m054_applies_when_zeon_uses_zakeru():
    assert defend_code(_m054("M-029")) == "defense.undefendable"


def test_p022_applies_when_furigaro_uses_other_ice_spell():
    # 由 フリガロ 使用的戰術算「フリガロ」の術(既有行為)
    g, _ = mk(book("M-036", "S-006"), book("M-001"))
    st = g.state
    furi = st.players[0].slots[0]
    furi.partner = "P-022"
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, furi, zone="partner"))
    choose(g, b.uid)
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2, slot=furi)
    submit(g, {"type": "no_defense", "player": 1})
    while st.battle is not None and st.pending is None:
        submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    while st.pending is not None and st.pending.kind in ("protect", "damage_order"):
        choose(g, 0 if st.pending.kind == "damage_order" else None)
    assert b.injured and not a.injured


def test_m005_applies_when_other_brago_attacks_with_brago_spell():
    # この魔物の「魔物の効果」や術のダメージを1ふやす:「この魔物の術」= ブラゴ 的戰術,另一隻 ブラゴ 攻擊時也算
    g, _ = mk(book("M-005", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    m005 = st.players[0].slots[0]
    other = add_slot(g, 0, "M-017")
    pos1 = st.players[1].pos
    battle_in(g, 2, slot=other)                                         # S-008 傷害 2
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, ability(0, m005))
    while st.battle is not None and st.pending is None:
        submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    while st.pending is not None and st.pending.kind in ("protect", "damage_order"):
        choose(g, 0 if st.pending.kind == "damage_order" else None)
    assert st.players[1].pos == pos1 + 2 * 3                            # 傷害 2 + 1


def test_m055_applies_when_other_brago_attacks():
    # 自分がこの魔物の「相手の魔本にダメージをあたえる」効果の術で攻撃したとき使える
    g, _ = mk(book("M-055", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    other = add_slot(g, 0, "M-017")
    battle_in(g, 2, slot=other)
    assert st.pending is not None and st.pending.kind == "pick_effect" and st.pending.player == 0


# ---------------------------------------------------------------- 限制類

def _e047(chosen_top="M-001", others=("M-001",)):
    """玩家 0 以 E-047 選玩家 1 的第一隻魔物;玩家 1 另有 others。回到玩家 1 的回合前停在 E-047 之後。"""
    g, _ = mk(book("M-001", "E-047", "S-001"), book(chosen_top, "S-001", "S-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    chosen = st.players[1].slots[0]
    extra = [add_slot(g, 1, top) for top in others]
    st.players[1].mp = 10
    use_event(g, 2)
    choose(g, chosen.uid)
    submit(g, {"type": "pass", "player": 1})
    return g, chosen, extra


def test_e047_blocks_same_name_mamodo():
    # 相手はその魔物の術を使えない:その魔物 = ガッシュ・ベル,同名的另一隻使用的戰術也是 ガッシュ・ベル 的戰術
    g, chosen, (other,) = _e047()
    battle_in(g, 3)
    assert defend_code(g, slot=other) == "spell.restricted"


def test_e047_blocks_zeon_using_zakeru_but_not_own_spell():
    g, _ = mk(book("M-001", "E-047", "S-001"), book("M-001", "S-001", "S-099"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    gash = st.players[1].slots[0]
    zeon = add_slot(g, 1, "M-029")
    st.players[1].mp = 10
    use_event(g, 2)
    choose(g, gash.uid)
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    assert defend_code(g, page=2, slot=zeon) == "spell.restricted"      # ガッシュ・ベル 的「ザケル」
    submit(g, {"type": "declare_defense", "player": 1, "page": 3, "slot_uid": zeon.uid})   # ゼオン 自己的「ザケル」
    assert g.state.battle.defense_spell == "S-099"


def test_e047_still_applies_after_chosen_leaves():
    g, chosen, (other,) = _e047(others=("M-002",))
    st = g.state
    st.players[1].slots.remove(chosen)                                  # 選定的魔物離場
    battle_in(g, 3)
    assert defend_code(g, slot=other) == "spell.restricted"


def test_e024_same_name_spell_blocked_but_effect_usable():
    # 相手はその魔物の「魔物の効果」や術を使えない:戰術依名稱,魔物效果只看選定的那一隻
    g, _ = mk(book("M-001", "E-024", "S-001"), book("M-001", "S-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[1].mp = 10
    use_event(g, 2)
    choose(g, a.uid)
    submit(g, {"type": "pass", "player": 1})
    assert mamodo_effect_block(g, 1, b) is None
    assert mamodo_effect_block(g, 1, a) is not None
    battle_in(g, 3)
    assert defend_code(g, slot=b) == "spell.mamodo_locked"


def test_p033_blocks_same_name_attack():
    # 相手の魔物1体を選ぶ。このターン中、相手はその魔物の術で攻撃できない:選了 A,同名的 B 也不能用戰術攻擊
    g, _ = mk(book("M-001", "S-001"), book("M-050"))
    st = g.state
    a = st.players[0].slots[0]
    b = add_slot(g, 0, "M-002")
    st.players[1].slots[0].partner = "P-033"
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    choose(g, a.uid)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": b.uid}) == "spell.attack_restricted"


def test_pr009_blocks_gash_using_command_defense_spell():
    # 自分は、「ガッシュ・ベル」の術を使えない:ガッシュ・ベル 使用的指令戰術也是 ガッシュ・ベル 的戰術
    g, _ = mk(book("M-001", "PR-009", "S-029", "S-028"), book("M-001", "S-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].mp = 10
    to_battle(g, 0)
    gash = st.players[0].slots[0]
    tio = add_slot(g, 0, "M-050")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    next_turn(g)
    submit(g, {"type": "declare_attack", "player": 1, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 0, "allow": True})
    assert code(g, {"type": "declare_defense", "player": 0, "page": 4, "slot_uid": gash.uid}) == "spell.restricted"
    submit(g, {"type": "declare_defense", "player": 0, "page": 4, "slot_uid": tio.uid})   # 其他魔物可以
    assert st.battle.defense_spell == "S-028"


def test_pr009_blocks_zeon_using_zakeru():
    g, _ = mk(book("M-029", "PR-009", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    add_slot(g, 0, "M-001")                                             # PR-009 由 ガッシュ・ベル 使用
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    zeon = st.players[0].slots[0]
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3, "slot_uid": zeon.uid}) == "spell.restricted"


# ---------------------------------------------------------------- E-043

def _e043(*opp_tops):
    g, _ = mk(book("M-001", "E-043"), book(*opp_tops[:1], "S-001", "S-028"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    slots = [st.players[1].slots[0]] + [add_slot(g, 1, top) for top in opp_tops[1:]]
    st.players[1].mp = 10
    use_event(g, 2)
    assert st.pending.player == 1                                       # 相手は、相手の魔物1体を選ぶ
    choose(g, slots[0].uid)
    submit(g, {"type": "pass", "player": 1})
    return g, slots


def test_e043_same_name_other_blocks_chosen_spells():
    # 選んだ魔物以外の魔物(A(2)、B)の術 = A の術と B の術 → A(1) 使用的戰術都是 A 的戰術
    g, (a1, a2, b) = _e043("M-001", "M-002", "M-050")
    assert mamodo_effect_block(g, 1, a1) is None                        # A(1) 的魔物效果可以使用
    battle_in(g, 3)
    assert defend_code(g, page=2, slot=a1) == "spell.mamodo_locked"
    assert defend_code(g, page=3, slot=a1) == "spell.mamodo_locked"     # 指令戰術由 A(1) 使用也是 A 的戰術


def test_e043_chosen_without_same_name_can_use_spells():
    g, (a, b) = _e043("M-001", "M-050")
    battle_in(g, 3)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": a.uid})
    assert g.state.battle.defense_spell == "S-001"


# ---------------------------------------------------------------- P-043

def test_p043_defense_spell_lock_after_target_leaves():
    # 相手の魔物1体を選ぶ。…「ウォンレイ」の術で攻撃するとき、●相手は、選んだ魔物の防御の術を使えない。
    # 選定的魔物離場後,依名稱仍然有效;「かばう」的選項不提供
    g, _ = mk(book("M-069", "S-078"), book("M-001", "S-001"))
    st = g.state
    won = st.players[0].slots[0]
    won.partner = "P-043"
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    st.players[1].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, won, zone="partner"))
    choose(g, a.uid)
    submit(g, {"type": "pass", "player": 1})
    st.players[1].slots.remove(a)
    battle_in(g, 2)                                                     # 只剩「防御の術」一個選項:自動使用
    assert st.pending is None
    assert defend_code(g, slot=b) == "spell.restricted"


# ---------------------------------------------------------------- 資料前提

def test_zakeru_spells_belong_to_gash_or_zeon():
    # PR-004 / PR-010 只看所屬的前提(design D6):名為「ザケル」的戰術只屬於 ガッシュ・ベル 與 ゼオン
    owners = {c.related_mamodo for c in DB.values() if c.type == "spell" and c.name_ja == "ザケル"}
    assert owners == {"ガッシュ・ベル", "ゼオン"}
