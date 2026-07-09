"""launcher:埠號避讓、cloudflared 偵測與降級、通道網址解析。"""

import io
import socket
import time

from gash import launcher


def test_find_free_port_prefers_default_style():
    port = launcher.find_free_port(preferred=0)  # 0 → 系統分配
    assert 1 <= port <= 65535


def test_find_free_port_avoids_occupied():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        occupied = s.getsockname()[1]
        port = launcher.find_free_port(preferred=occupied)
        assert port != occupied


def test_tunnel_url_regex_matches_cloudflared_output():
    sample = io.StringIO(
        "2026-07-09T00:00:00Z INF Thank you for trying Cloudflare Tunnel.\n"
        "2026-07-09T00:00:01Z INF +--------------------------------------+\n"
        "2026-07-09T00:00:01Z INF |  https://tiny-red-fox.trycloudflare.com  |\n"
    )
    url, lines = launcher.read_tunnel_url(sample, timeout=5)
    assert url == "https://tiny-red-fox.trycloudflare.com"
    assert len(lines) == 3


def test_read_tunnel_url_times_out_without_match():
    class Slow:
        def __iter__(self):
            return self

        def __next__(self):
            time.sleep(0.05)
            return "INF still connecting...\n"

    url, lines = launcher.read_tunnel_url(Slow(), timeout=0.3)
    assert url is None
    assert lines  # 原始輸出保留供除錯


def test_start_tunnel_degrades_without_cloudflared(monkeypatch):
    monkeypatch.setattr(launcher, "find_cloudflared", lambda: None)
    proc, url = launcher.start_tunnel(8000)
    assert proc is None and url is None


def test_find_cloudflared_frozen_requires_beside_exe(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "is_frozen", lambda: True)
    monkeypatch.setattr(launcher, "exe_dir", lambda: tmp_path)
    assert launcher.find_cloudflared() is None
    name = "cloudflared.exe" if launcher.sys.platform == "win32" else "cloudflared"
    (tmp_path / name).write_bytes(b"")
    assert launcher.find_cloudflared() == str(tmp_path / name)
