"""預組探索端點與具名預組解析(battle-api 差分)。"""

import json

import gash.api.app as appmod
from fastapi.testclient import TestClient

client = TestClient(appmod.app)


def _rescan():
    appmod._PRESETS = None  # 清快取,強制重新掃描 data/decks/


def test_list_decks_contains_level1():
    _rescan()
    res = client.get("/api/decks")
    assert res.status_code == 200
    decks = res.json()["decks"]
    ids = [d["id"] for d in decks]
    assert "level1" in ids
    lvl1 = next(d for d in decks if d["id"] == "level1")
    assert lvl1["name"]  # 有可顯示名(name_key 解析不到 → fallback 到內嵌 name)
    assert decks[0]["id"] == "level1"  # 預設預組置頂


def test_dropping_a_deck_file_appears(tmp_path):
    # 於 data/decks/ 放一個新預組檔,重掃後即出現
    src = appmod.DECKS_DIR / "level1.json"
    new = appmod.DECKS_DIR / "_e2e_tmp_preset.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    d["id"] = "_e2e_tmp_preset"
    d.pop("name_key", None)
    d["name"] = "臨時測試預組"
    new.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    try:
        _rescan()
        decks = client.get("/api/decks").json()["decks"]
        entry = next((x for x in decks if x["id"] == "_e2e_tmp_preset"), None)
        assert entry is not None and entry["name"] == "臨時測試預組"
        # 可用它開本機局
        res = client.post("/api/rooms", json={"mode": "local",
                          "decks": [{"preset": "_e2e_tmp_preset"}, {"preset": "level1"}]})
        assert res.status_code == 200
    finally:
        new.unlink()
        _rescan()


def test_invalid_deck_file_excluded(tmp_path):
    bad = appmod.DECKS_DIR / "_e2e_bad.json"
    bad.write_text('{"id": "_e2e_bad", "pages": ["NOPE"]}', encoding="utf-8")
    try:
        _rescan()
        ids = [d["id"] for d in client.get("/api/decks").json()["decks"]]
        assert "_e2e_bad" not in ids  # 壞檔被排除,端點不掛
    finally:
        bad.unlink()
        _rescan()


def test_unknown_preset_rejected():
    _rescan()
    for bad in ["../../etc/passwd", "level99", "", "..%2f..%2f"]:
        res = client.post("/api/rooms", json={"mode": "local",
                          "decks": [{"preset": bad}, {"preset": "level1"}]})
        assert res.status_code == 404, (bad, res.status_code)
        assert res.json()["detail"]["code"] == "deck.unknown_preset"


def test_named_preset_opens_game():
    _rescan()
    res = client.post("/api/rooms", json={"mode": "local",
                      "decks": [{"preset": "level1"}, {"preset": "level1"}]})
    assert res.status_code == 200
    body = res.json()
    assert body["state"]["players"][0]["slots"][0]["top"] == "M-001"


def test_default_deck_unchanged():
    _rescan()
    # 缺省(無 deck 欄位)= level1 預設
    res = client.post("/api/rooms", json={"mode": "local"})
    assert res.status_code == 200
    assert res.json()["state"]["players"][0]["slots"][0]["top"] == "M-001"


def test_custom_pages_still_validated():
    _rescan()
    res = client.post("/api/rooms", json={"mode": "online",
                      "deck": {"pages": ["NOPE"] * 32}})
    assert res.status_code == 422
