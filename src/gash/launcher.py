"""單機啟動器:本機伺服器 + Cloudflare Quick Tunnel + 自動開瀏覽器。

發行版執行檔的進入點;開發環境可 `python -m gash.launcher` 走同一流程。
cloudflared 缺席或通道逾時 → 降級為僅本機/區網模式,遊戲照常可用。
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from .paths import exe_dir, is_frozen

DEFAULT_PORT = 8000
TUNNEL_TIMEOUT = 30.0
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_free_port(preferred: int = DEFAULT_PORT) -> int:
    """優先用預設埠,被占用時取系統分配的可用埠。"""
    for port in (preferred, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
        except OSError:
            continue
    raise RuntimeError("no free port")


def find_cloudflared() -> str | None:
    """發行佈局:執行檔旁;開發環境退而求其次找 PATH。"""
    name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    beside = exe_dir() / name
    if is_frozen():
        return str(beside) if beside.is_file() else None
    return str(beside) if beside.is_file() else shutil.which("cloudflared")


def read_tunnel_url(stream, timeout: float = TUNNEL_TIMEOUT) -> tuple[str | None, list[str]]:
    """從 cloudflared 輸出逐行找公開網址;逾時放棄並保留原始輸出供除錯。"""
    lines: list[str] = []
    found: list[str | None] = [None]

    def reader():
        for raw in stream:
            line = raw.rstrip("\n")
            lines.append(line)
            m = TUNNEL_RE.search(line)
            if m:
                found[0] = m.group(0)
                return

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    th.join(timeout)
    return found[0], lines


def start_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    cf = find_cloudflared()
    if not cf:
        return None, None
    proc = subprocess.Popen(
        [cf, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url, lines = read_tunnel_url(proc.stdout)
    if url is None:
        print("[launcher] 通道網址解析逾時,降級為僅本機模式。cloudflared 輸出:", file=sys.stderr)
        for line in lines[-20:]:
            print("  " + line, file=sys.stderr)
        proc.terminate()
        return None, None
    # 網址到手後持續消化輸出,避免子行程因 pipe 滿而卡住
    threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
    return proc, url


def main() -> None:
    import uvicorn

    from .api import app as app_module

    port = find_free_port()
    server = uvicorn.Server(uvicorn.Config(
        app_module.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if not th.is_alive() or time.monotonic() > deadline:
            print("[launcher] 伺服器啟動失敗", file=sys.stderr)
            sys.exit(1)
        time.sleep(0.05)

    local_url = f"http://127.0.0.1:{port}/"
    print(f"[launcher] 本機網址:{local_url}")

    tunnel_proc, tunnel_url = start_tunnel(port)
    if tunnel_url:
        app_module.launch_info["tunnel_url"] = tunnel_url
        print(f"[launcher] 邀請網址:{tunnel_url}(建房後把加入連結貼給對手)")
    else:
        print("[launcher] 無公開通道(缺 cloudflared 或逾時),僅限本機/區網遊玩")

    webbrowser.open(local_url)
    print("[launcher] 關閉此視窗或按 Ctrl+C 結束")
    try:
        while th.is_alive():
            th.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        if tunnel_proc:
            tunnel_proc.terminate()


if __name__ == "__main__":
    main()
