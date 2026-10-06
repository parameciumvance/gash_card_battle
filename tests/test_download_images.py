"""tools/download_images.py:下載後轉成 WebP、續抓只認 WebP(card-data「卡圖資產與備援」)。

以假的下載函式代替 Google Drive,不需要網路。
"""

import io
import json
import sys
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


def test_resume_only_counts_webp(tmp_path, monkeypatch):
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps([
        {"number": "T-001", "image_url": "https://drive.google.com/file/d/id-one/view"},
        {"number": "T-002", "image_url": "https://drive.google.com/file/d/id-two/view"},
    ]), encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "T-001.webp").write_bytes(b"already")
    (out_dir / "T-002.jpg").write_bytes(rounded_card_png())      # 舊格式不算已下載
    fetched = []

    def fake_fetch(file_id):
        fetched.append(file_id)
        return rounded_card_png()

    monkeypatch.setattr(dl, "CARDS", cards)
    monkeypatch.setattr(dl, "OUT_DIR", out_dir)
    monkeypatch.setattr(dl, "FAILED", out_dir / "_failed.txt")
    monkeypatch.setattr(dl, "fetch", fake_fetch)
    monkeypatch.setattr(dl.time, "sleep", lambda s: None)
    dl.main()

    assert fetched == ["id-two"]
    assert (out_dir / "T-001.webp").read_bytes() == b"already"
    assert Image.open(out_dir / "T-002.webp").format == "WEBP"
    assert not (out_dir / "_failed.txt").exists()
