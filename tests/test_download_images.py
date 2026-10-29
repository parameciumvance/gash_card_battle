"""tools/download_images.py:從使用者維護的資料夾依 {卡號}.webp 下載、WebP 原樣存檔、其他格式轉成 WebP、
續抓只認 WebP(card-data「卡圖資產與備援」)。

以固定的資料夾頁面樣本與假的下載函式代替 Google Drive,不需要網路。
"""

import io
import json
import sys

import pytest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.download_images as dl  # noqa: E402

W, H = 465, 679


def rounded_card_png() -> bytes:
    """仿原圖:465×679 RGBA PNG,四角透明、其餘不透明。"""
    im = Image.new("RGBA", (W, H), (30, 120, 40, 255))
    for x, y in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        for dx in range(6):
            for dy in range(6):
                im.putpixel((abs(x - dx), abs(y - dy)), (0, 0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_to_webp_keeps_size_and_transparent_corners():
    out = Image.open(io.BytesIO(dl.to_webp(rounded_card_png())))
    assert out.format == "WEBP"
    assert out.size == (W, H)
    out = out.convert("RGBA")
    assert out.getpixel((0, 0))[3] < 10
    assert out.getpixel((W - 1, H - 1))[3] < 10
    assert out.getpixel((W // 2, H // 2))[3] > 245


def webp_bytes() -> bytes:
    return dl.to_webp(rounded_card_png())


def entry(file_id, title):
    """仿 embeddedfolderview 的一筆檔案。"""
    return (f'<div class="flip-entry" id="entry-{file_id}" tabindex="0" role="link"><div class="flip-entry-info">'
            f'<a href="https://drive.google.com/file/d/{file_id}/view?usp=drive_web" target="_blank">'
            f'<div class="flip-entry-visual"><img src="x" alt=""/></div>'
            f'<div class="flip-entry-title">{title}</div></a></div>'
            f'<div class="flip-entry-last-modified"><div>Oct 6</div></div></div>')


def folder_page(*entries):
    return '<html><body><div class="flip-entries">' + "".join(entry(*e) for e in entries) + "</div></body></html>"


def test_parse_folder_maps_title_to_id():
    page = folder_page(("id-one", "T-001.webp"), ("id-two", "T-002.webp"), ("id-e", "T-003e.webp"))
    assert dl.parse_folder(page) == {"T-001.webp": "id-one", "T-002.webp": "id-two", "T-003e.webp": "id-e"}


def run(tmp_path, monkeypatch, numbers, page, files, existing=()):
    """以假的資料夾與下載執行 main();回傳 (輸出目錄, 下載過的檔案 ID)。"""
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps([{"number": n} for n in numbers]), encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    for name, data in existing:
        (out_dir / name).write_bytes(data)
    fetched = []

    def fake_fetch(file_id):
        fetched.append(file_id)
        return files[file_id]

    monkeypatch.setattr(dl, "CARDS", cards)
    monkeypatch.setattr(dl, "OUT_DIR", out_dir)
    monkeypatch.setattr(dl, "FAILED", out_dir / "_failed.txt")
    monkeypatch.setattr(dl, "fetch_folder_page", lambda: page)
    monkeypatch.setattr(dl, "fetch", fake_fetch)
    monkeypatch.setattr(dl.time, "sleep", lambda s: None)
    dl.main()
    return out_dir, fetched


def test_downloads_folder_webp_as_is(tmp_path, monkeypatch):
    data = webp_bytes()
    page = folder_page(("id-one", "T-001.webp"), ("id-one-e", "T-001e.webp"))
    out_dir, fetched = run(tmp_path, monkeypatch, ["T-001"], page, {"id-one": data})
    assert fetched == ["id-one"]
    assert (out_dir / "T-001.webp").read_bytes() == data          # 原樣存檔,不再壓縮一次
    assert not (out_dir / "_failed.txt").exists()


def test_card_missing_from_folder_is_recorded_and_others_continue(tmp_path, monkeypatch):
    page = folder_page(("id-two", "T-002.webp"))
    out_dir, fetched = run(tmp_path, monkeypatch, ["T-001", "T-002"], page, {"id-two": webp_bytes()})
    assert fetched == ["id-two"]
    assert (out_dir / "T-002.webp").exists() and not (out_dir / "T-001.webp").exists()
    assert (out_dir / "_failed.txt").read_text(encoding="utf-8").split("\t")[0] == "T-001"


def test_login_page_is_recorded_as_failure(tmp_path, monkeypatch):
    page = folder_page(("id-one", "T-001.webp"))
    out_dir, _ = run(tmp_path, monkeypatch, ["T-001"], page, {"id-one": None})
    assert not (out_dir / "T-001.webp").exists()
    assert (out_dir / "_failed.txt").read_text(encoding="utf-8").startswith("T-001")


def test_non_webp_is_converted(tmp_path, monkeypatch):
    page = folder_page(("id-one", "T-001.webp"))
    out_dir, _ = run(tmp_path, monkeypatch, ["T-001"], page, {"id-one": rounded_card_png()})
    out = Image.open(out_dir / "T-001.webp")
    assert out.format == "WEBP" and out.size == (W, H)


def test_resume_only_counts_webp(tmp_path, monkeypatch):
    page = folder_page(("id-one", "T-001.webp"), ("id-two", "T-002.webp"))
    out_dir, fetched = run(tmp_path, monkeypatch, ["T-001", "T-002"], page, {"id-two": webp_bytes()},
                           existing=[("T-001.webp", b"already"), ("T-002.jpg", rounded_card_png())])  # 舊格式不算已下載
    assert fetched == ["id-two"]
    assert (out_dir / "T-001.webp").read_bytes() == b"already"
    assert Image.open(out_dir / "T-002.webp").format == "WEBP"
    assert not (out_dir / "_failed.txt").exists()


def test_unparsable_folder_page_aborts(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        run(tmp_path, monkeypatch, ["T-001"], "<html>sign in</html>", {})
    assert not (tmp_path / "out" / "_failed.txt").exists()


def test_ex_card_from_uppercase_filename(tmp_path, monkeypatch):
    # 資料夾檔名寫 EX-001.webp,卡號依 atwiki 為 Ex-001(card-data「外部來源的擴張卡號寫法」)
    data = webp_bytes()
    page = folder_page(("id-ex", "EX-001.webp"), ("id-m", "M-001.webp"))
    out_dir, fetched = run(tmp_path, monkeypatch, ["Ex-001", "M-001"], page, {"id-ex": data, "id-m": data})
    assert sorted(fetched) == ["id-ex", "id-m"]
    assert (out_dir / "Ex-001.webp").read_bytes() == data
    assert not (out_dir / "_failed.txt").exists()
