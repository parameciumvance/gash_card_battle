"""正式站維運腳本(docker-deployment「維運腳本的連線」等):在本機執行,經 ssh 操作 VPS 部署目錄的 compose 服務。

  python tools/vps.py status              唯讀:線上版本、容器狀態、卡圖張數、目前公告
  python tools/vps.py cards [--force 卡號 ...]
                                          只上傳 VPS 上沒有的卡圖;--force 的卡覆蓋重傳
  python tools/vps.py announce FILE [--yes]
                                          驗證後發布公告(先列出訊息與提醒並詢問;--yes 略過)
  python tools/vps.py announce --clear    撤下公告

- ssh 目標 GASH_VPS(預設 dev@dev-vps)、部署目錄 GASH_VPS_DIR(預設 /opt/gash-card-battle)、
  確認用的公開網址 GASH_PUBLIC_URL(預設 https://card-battle.zatchholic.com)。
- 資料從 ssh 的 stdin 串流進 app 容器(docker compose exec -T app),VPS 上不留暫存檔;不讀 .env、不重啟容器。
- ssh 以 BatchMode 執行:不會停下來等密碼或主機金鑰確認(那會吃掉串流的資料);第一次連新主機時先手動 ssh 一次。
- 公告驗證與伺服器共用 gash.announcement,需在裝好專案的環境(pip install -e .)執行。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

from gash.announcement import AnnouncementError, announcement_warnings, parse_announcement

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CARDS = ROOT / "frontend/assets/cards"
REMOTE_CARDS = "/app/assets/cards"
REMOTE_ANN = "/app/assets/announcement.json"
CARD_OWNER = 1000          # 與 VPS 上 cards/ 目錄的擁有者相同

DEFAULT_TARGET = "dev@dev-vps"
DEFAULT_DIR = "/opt/gash-card-battle"
DEFAULT_URL = "https://card-battle.zatchholic.com"

REJECT_REASONS = {
    "json": "不是合法的 JSON 物件",
    "id": "缺少 id,或 id 不是非空的字串",
    "message": "message 必須是「語言代碼 → 文字」的物件,且不能是空的",
    "until": "until 不是 ISO 8601 時間",
    "expired": "until 已經過了",
}


class RemoteError(Exception):
    pass


class Remote:
    """VPS 部署目錄裡的 docker compose;所有遠端指令都經過這裡(測試以假的取代)。"""

    def __init__(self, target: str, deploy_dir: str):
        self.target, self.deploy_dir = target, deploy_dir

    def command(self, compose_args: list[str]) -> list[str]:
        inner = f"cd {shlex.quote(self.deploy_dir)} && docker compose {shlex.join(compose_args)}"
        return ["ssh", "-o", "BatchMode=yes", self.target, inner]

    def run(self, compose_args: list[str], stdin: bytes | None = None) -> str:
        p = subprocess.run(self.command(compose_args), input=stdin if stdin is not None else b"",
                           capture_output=True)
        if p.returncode != 0:
            raise RemoteError(p.stderr.decode(errors="replace").strip() or f"結束碼 {p.returncode}")
        return p.stdout.decode(errors="replace")

    def app(self, script: str, stdin: bytes | None = None) -> str:
        """在 app 容器裡以 sh 執行。"""
        return self.run(["exec", "-T", "app", "sh", "-c", script], stdin)


def fetch_json(base_url: str, path: str) -> dict:
    req = urllib.request.Request(base_url.rstrip("/") + path, headers={"User-Agent": "gash-vps-tool"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


# ---- cards ----

def remote_card_names(remote: Remote) -> set[str]:
    out = remote.app(f"find {REMOTE_CARDS} -maxdepth 1 -name '*.webp' -exec basename {{}} \\;")
    return {line.strip() for line in out.splitlines() if line.strip()}


def card_tar(files: list[Path]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for f in files:
            info = tarfile.TarInfo(f.name)
            info.size, info.mode, info.mtime = f.stat().st_size, 0o644, int(time.time())
            info.uid = info.gid = CARD_OWNER
            with f.open("rb") as fh:
                tar.addfile(info, fh)
    return buf.getvalue()


def cmd_cards(remote: Remote, force: list[str], out) -> int:
    local = {f.name: f for f in sorted(LOCAL_CARDS.glob("*.webp"))}
    missing_force = [n for n in force if f"{n}.webp" not in local]
    if missing_force:
        print(f"本機沒有這些卡圖:{'、'.join(missing_force)}", file=sys.stderr)
        return 1
    have = remote_card_names(remote)
    upload = [f for name, f in local.items() if name not in have or f.stem in force]
    if not upload:
        print(f"已經同步:VPS 上已有本機全部 {len(local)} 張卡圖", file=out)
        return 0
    print(f"上傳 {len(upload)} 張:{'、'.join(f.stem for f in upload)}", file=out)
    remote.app(f"tar -x -C {REMOTE_CARDS}", stdin=card_tar(upload))
    print(f"完成:VPS 上共 {len(remote_card_names(remote))} 張卡圖", file=out)
    return 0


# ---- announce ----

def show_announcement(ann: dict, out) -> None:
    print(f"id:{ann['id']}", file=out)
    print(f"until:{ann['until'] or '(不限)'}", file=out)
    for lang, text in ann["message"].items():
        print(f"  {lang}:{text}", file=out)


def confirm_live(base_url: str, expected_id: str | None, out) -> int:
    try:
        live = fetch_json(base_url, "/api/announcement")["announcement"]
    except Exception as exc:  # noqa: BLE001 — 連線、HTTP、JSON 錯誤都一樣處理
        print(f"VPS 上的檔案已更新,但無法從 {base_url} 確認:{exc}(稍後可用 status 查看)", file=sys.stderr)
        return 1
    live_id = live["id"] if live else None
    if live_id != expected_id:
        print(f"線上的公告與預期不符:{json.dumps(live, ensure_ascii=False)}", file=sys.stderr)
        return 1
    print("已生效:線上" + (f"顯示公告 {live_id}" if live_id else "沒有公告"), file=out)
    return 0


def cmd_announce(remote: Remote, path: Path, yes: bool, base_url: str, out, ask=input) -> int:
    text = path.read_text(encoding="utf-8")
    try:
        ann = parse_announcement(text)
    except AnnouncementError as exc:
        print(f"不上傳:{REJECT_REASONS[exc.reason]}({exc}),伺服器會視為沒有公告", file=sys.stderr)
        return 1
    show_announcement(ann, out)
    for w in announcement_warnings(ann):
        print(f"提醒:{w}", file=out)
    if not yes and ask("發布這則公告?[y/N] ").strip().lower() not in ("y", "yes"):
        print("已取消,沒有上傳", file=out)
        return 1
    tmp = REMOTE_ANN + ".tmp"
    remote.app(f"cat > {tmp} && mv {tmp} {REMOTE_ANN} || {{ rm -f {tmp}; exit 1; }}", stdin=text.encode("utf-8"))
    return confirm_live(base_url, ann["id"], out)


def cmd_clear(remote: Remote, base_url: str, out) -> int:
    removed = remote.app(f"if [ -e {REMOTE_ANN} ]; then rm {REMOTE_ANN} && echo removed; fi").strip()
    if removed != "removed":
        print("目前沒有公告檔,不需要撤下", file=out)
        return 0
    return confirm_live(base_url, None, out)


# ---- status ----

def cmd_status(remote: Remote, base_url: str, out) -> int:
    try:
        version = fetch_json(base_url, "/api/meta").get("version")
        ann = fetch_json(base_url, "/api/announcement")["announcement"]
    except Exception as exc:  # noqa: BLE001
        version = ann = None
        print(f"無法連線 {base_url}:{exc}", file=out)
    print(f"線上版本:{version or '(無法取得)'}", file=out)
    print("容器:", file=out)
    for line in remote.run(["ps", "--format", "{{.Service}}\t{{.Status}}"]).splitlines():
        print(f"  {line}", file=out)
    print(f"卡圖:VPS {len(remote_card_names(remote))} 張,本機 {len(list(LOCAL_CARDS.glob('*.webp')))} 張", file=out)
    if ann:
        print(f"公告:{ann['id']}(until {ann['until'] or '不限'}){ann['message'].get('zh-TW', '')}", file=out)
    else:
        print("公告:沒有", file=out)
    return 0


def main(argv: list[str] | None = None, remote: Remote | None = None, out=None, ask=input) -> int:
    parser = argparse.ArgumentParser(prog="tools/vps.py", description="正式站維運(經 ssh 操作 VPS)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="唯讀:線上版本、容器狀態、卡圖張數、目前公告")
    p_cards = sub.add_parser("cards", help="只上傳 VPS 上沒有的卡圖")
    p_cards.add_argument("--force", nargs="+", default=[], metavar="卡號", help="覆蓋重傳這些卡(換圖時用)")
    p_ann = sub.add_parser("announce", help="發布或撤下維護公告")
    p_ann.add_argument("file", nargs="?", type=Path, help="公告檔(格式見 README「維護公告」)")
    p_ann.add_argument("--clear", action="store_true", help="撤下公告")
    p_ann.add_argument("--yes", action="store_true", help="不詢問直接發布")
    args = parser.parse_args(argv)

    out = out or sys.stdout
    remote = remote or Remote(os.environ.get("GASH_VPS", DEFAULT_TARGET), os.environ.get("GASH_VPS_DIR", DEFAULT_DIR))
    base_url = os.environ.get("GASH_PUBLIC_URL", DEFAULT_URL)
    try:
        if args.cmd == "status":
            return cmd_status(remote, base_url, out)
        if args.cmd == "cards":
            return cmd_cards(remote, args.force, out)
        if args.clear == bool(args.file):
            parser.error("announce 需要公告檔,或 --clear(兩者擇一)")
        if args.clear:
            return cmd_clear(remote, base_url, out)
        return cmd_announce(remote, args.file, args.yes, base_url, out, ask)
    except RemoteError as exc:
        print(f"遠端指令失敗({remote.target}):{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
