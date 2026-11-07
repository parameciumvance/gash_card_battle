"""魔書組合的提醒(deck-builder「魔書組合的提醒」):魔書中沒有魔物能使用的戰術、沒有對應魔物的搭檔。"""
import pytest
from fastapi.testclient import TestClient

from gash.api.app import app
from gash.engine.deck import deck_warnings


def book(**pages):
    """32 頁魔書(頁碼從 1 起),其餘為空頁。"""
    out = [None] * 32
    for key, number in pages.items():
        out[int(key[1:]) - 1] = number
    return out


def warned(pages):
    return {(w["kind"], w["page"], w["card"]) for w in deck_warnings(pages)}


def test_spell_without_user_then_add_mamodo():
    # S-001 ザケル(ガッシュ・ベル)
    assert warned(book(p1="M-004", p5="S-001")) == {("spell_no_user", 5, "S-001")}
    assert warned(book(p1="M-001", p5="S-001")) == set()


def test_command_spell_not_warned():
    assert warned(book(p1="M-004", p5="S-025")) == set()                  # S-025 逃げるぞ!:指令戰術


def test_m029_can_use_exactly_zakeru():
    # M-029 ゼオン:可用賈修名稱完全為「ザケル」的戰術;「バオウ・ザケルガ」不算
    assert warned(book(p1="M-029", p5="S-001")) == set()
    assert warned(book(p1="M-029", p5="Ex-020")) == {("spell_no_user", 5, "Ex-020")}


def test_m023_wood_compat():
    # M-023 ポッケリオ:可用木屬性的戰術(S-014 是スギナ的木屬性戰術)
    assert warned(book(p1="M-023", p5="S-014")) == set()
    assert warned(book(p1="M-004", p5="S-014")) == {("spell_no_user", 5, "S-014")}


def test_p029_grants_wind_spells_to_zabas():
    # P-029 ガリオント:本回合ザバス家族可用風屬性的戰術(S-037 是ハイド的風屬性戰術)
    assert warned(book(p1="M-043", p2="P-029", p5="S-037")) == set()
    assert ("spell_no_user", 5, "S-037") in warned(book(p1="M-004", p2="P-029", p5="S-037"))   # 沒有ザバス


def test_partner_without_mamodo():
    assert warned(book(p1="M-004", p8="P-001")) == {("partner_no_mamodo", 8, "P-001")}   # 高嶺清麿 → ガッシュ・ベル
    assert warned(book(p1="M-001", p8="P-001")) == set()


def test_empty_book():
    assert deck_warnings([None] * 32) == []


def test_api():
    client = TestClient(app)
    r = client.post("/api/decks/warnings", json={"pages": book(p1="M-004", p5="S-001", p8="P-001")})
    assert r.status_code == 200
    assert {(w["kind"], w["page"], w["card"]) for w in r.json()["warnings"]} == {
        ("spell_no_user", 5, "S-001"), ("partner_no_mamodo", 8, "P-001")}


@pytest.mark.parametrize("pages", [None, "x", [1, 2]])
def test_api_rejects_bad_input(pages):
    r = TestClient(app).post("/api/decks/warnings", json={"pages": pages})
    assert r.status_code in (400, 422)
