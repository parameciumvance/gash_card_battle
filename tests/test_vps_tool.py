"""tools/vps.py:正式站維運腳本(docker-deployment「維運腳本的連線」「卡圖同步」「發布公告前的驗證」
「發布與撤下公告」「正式站狀態查詢」)。

以假的 Remote(記錄遠端指令、模擬 app 容器的檔案)與假的公開 API 代替 VPS,不需要網路。
"""

import io
import json
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.vps as vps  # noqa: E402

FUTURE = "2999-01-01T00:00:00+08:00"
GOOD = {"id": "m1", "until": FUTURE,
        "message": {"zh-TW": "今晚維護", "zh-CN": "今晚维护", "en": "Maintenance tonight", "ja": "今夜メンテナンス"}}


class FakeRemote(vps.Remote):
    """模擬 app 容器:卡圖檔名集合與公告檔;記錄每個遠端指令。"""

    def __init__(self, cards=(), announcement=None):
        super().__init__("dev@test", "/opt/test")
        self.cards = set(cards)
        self.announcement = announcement
        self.calls = []                 # (compose_args, stdin)
        self.uploaded = []              # 每次 tar 上傳的檔名

    def run(self, compose_args, stdin=None):
        self.calls.append((compose_args, stdin))
        if compose_args[0] == "ps":
            return "app\tUp 2 hours (healthy)\ncloudflared\tUp 2 hours\nwatchtower\tUp 2 days (healthy)\n"
        script = compose_args[-1]
        if script.startswith("find "):
            return "".join(f"{n}\n" for n in sorted(self.cards))
        if script.startswith("tar -x"):
            with tarfile.open(fileobj=io.BytesIO(stdin)) as tar:
                members = tar.getmembers()
            assert all(m.uid == m.gid == vps.CARD_OWNER for m in members)
            names = [m.name for m in members]
            self.uploaded.append(names)
            self.cards |= set(names)
            return ""
        if script.startswith("cat > "):
            self.announcement = stdin.decode("utf-8")
            return ""
        if script.startswith("if [ -e "):
            if self.announcement is None:
                return ""
            self.announcement = None
            return "removed\n"
        raise AssertionError(f"未預期的遠端指令:{compose_args}")

    def scripts(self):
        return [args[-1] for args, _ in self.calls]


@pytest.fixture
def local_cards(tmp_path, monkeypatch):
    def make(*numbers):
        for n in numbers:
            (tmp_path / f"{n}.webp").write_bytes(b"RIFF" + n.encode())
        return tmp_path
    monkeypatch.setattr(vps, "LOCAL_CARDS", tmp_path)
    return make


@pytest.fixture
def live(monkeypatch):
    """假的公開 API:預設依 FakeRemote 的公告檔回應(伺服器即時讀檔)。"""
    state = {"remote": None, "meta": {"version": "v1.3.3"}, "error": None, "override": "unset"}

    def fetch(base_url, path):
        if state["error"]:
            raise state["error"]
        if path == "/api/meta":
            return state["meta"]
        if state["override"] != "unset":
            return {"announcement": state["override"]}
        text = state["remote"].announcement if state["remote"] else None
        return {"announcement": vps.parse_announcement(text) if text else None}
    monkeypatch.setattr(vps, "fetch_json", fetch)
    return state


def run(argv, remote, ask=lambda prompt: "y"):
    out = io.StringIO()
    code = vps.main(argv, remote=remote, out=out, ask=ask)
    return code, out.getvalue()


# ---- 連線 ----

def test_target_and_dir_from_env(monkeypatch, local_cards, live):
    local_cards()
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    monkeypatch.setattr(vps.subprocess, "run", fake_run)
    monkeypatch.setenv("GASH_VPS", "ops@other-host")
    monkeypatch.setenv("GASH_VPS_DIR", "/srv/my dir")
    assert vps.main(["cards"], out=io.StringIO()) == 0
    ssh, batch, target, inner = seen["argv"][0], seen["argv"][2], seen["argv"][3], seen["argv"][4]
    assert (ssh, batch, target) == ("ssh", "BatchMode=yes", "ops@other-host")
    assert inner.startswith("cd '/srv/my dir' && docker compose exec -T app sh -c ")


def test_default_target():
    r = vps.Remote(vps.DEFAULT_TARGET, vps.DEFAULT_DIR)
    argv = r.command(["exec", "-T", "app", "sh", "-c", "echo 'a b'"])
    assert argv[3] == "dev@dev-vps"
    assert shlex.split(argv[4]) == ["cd", "/opt/gash-card-battle", "&&", "docker", "compose", "exec", "-T", "app",
                                    "sh", "-c", "echo 'a b'"]               # 遠端 shell 拆出來的參數與原本相同


def test_ssh_failure(monkeypatch, local_cards, capsys):
    local_cards("M-001")
    monkeypatch.setattr(vps.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(
        argv, 255, b"", b"ssh: Could not resolve hostname dev-vps"))
    assert vps.main(["cards"], out=io.StringIO()) == 1
    captured = capsys.readouterr()
    assert "Could not resolve hostname dev-vps" in captured.err
    assert "完成" not in captured.out and "上傳" not in captured.out


# ---- cards ----

def test_cards_uploads_only_missing(local_cards):
    local_cards("M-001", "M-054")
    remote = FakeRemote(cards={"M-001.webp", "S-999.webp"})
    code, out = run(["cards"], remote)
    assert code == 0
    assert remote.uploaded == [["M-054.webp"]]
    assert "上傳 1 張:M-054" in out
    assert "共 3 張" in out                                    # 只在 VPS 的 S-999 不刪
    assert not any("rm " in s for s in remote.scripts())


def test_cards_force_reupload(local_cards):
    local_cards("M-001", "M-002")
    remote = FakeRemote(cards={"M-001.webp", "M-002.webp"})
    code, out = run(["cards", "--force", "M-001"], remote)
    assert code == 0
    assert remote.uploaded == [["M-001.webp"]]


def test_cards_force_unknown_card(local_cards):
    local_cards("M-001")
    remote = FakeRemote()
    code, _ = run(["cards", "--force", "M-404"], remote)
    assert code == 1 and remote.calls == []


def test_cards_already_synced(local_cards):
    local_cards("M-001")
    remote = FakeRemote(cards={"M-001.webp"})
    code, out = run(["cards"], remote)
    assert code == 0 and remote.uploaded == []
    assert "已經同步" in out


# ---- announce ----

def write(tmp_path, data):
    p = tmp_path / "ann.json"
    p.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.mark.parametrize("data, word", [
    ({**GOOD, "until": "2000-01-01T00:00:00+08:00"}, "until 已經過了"),
    ({"id": "m1", "until": FUTURE}, "message"),
    ("{oops", "JSON"),
])
def test_announce_rejected(tmp_path, live, capsys, data, word):
    remote = FakeRemote()
    live["remote"] = remote
    code = vps.main(["announce", str(write(tmp_path, data)), "--yes"], remote=remote, out=io.StringIO())
    assert code == 1
    assert remote.calls == []                                    # 沒有上傳
    err = capsys.readouterr().err
    assert word in err and "伺服器會視為沒有公告" in err


def test_announce_confirm_and_publish(tmp_path, live):
    remote = FakeRemote()
    live["remote"] = remote
    prompts = []
    code, out = run(["announce", str(write(tmp_path, GOOD))], remote, ask=lambda p: prompts.append(p) or "y")
    assert code == 0 and prompts
    assert "en:Maintenance tonight" in out and "提醒" not in out
    assert json.loads(remote.announcement)["id"] == "m1"
    script = remote.scripts()[-1]
    assert script.startswith("cat > /app/assets/announcement.json.tmp && mv /app/assets/announcement.json.tmp "
                             "/app/assets/announcement.json")       # 同目錄暫存檔 + mv:原子替換
    assert "已生效" in out and "m1" in out


def test_announce_declined(tmp_path, live):
    remote = FakeRemote()
    live["remote"] = remote
    code, out = run(["announce", str(write(tmp_path, GOOD))], remote, ask=lambda p: "n")
    assert code == 1 and remote.calls == []
    assert "已取消" in out


def test_announce_warnings_then_decline(tmp_path, live):
    remote = FakeRemote()
    live["remote"] = remote
    data = {"id": "m1", "message": {"zh-TW": "今晚維護", "zh-CN": "123", "en": "..."}}
    code, out = run(["announce", str(write(tmp_path, data))], remote, ask=lambda p: "")
    assert code == 1 and remote.calls == []
    assert "提醒:zh-CN 像佔位文字" in out and "提醒:en 像佔位文字" in out and "提醒:缺少 ja" in out


def test_announce_yes_skips_prompt(tmp_path, live):
    remote = FakeRemote()
    live["remote"] = remote

    def never(prompt):
        raise AssertionError("--yes 不應詢問")
    code, _ = run(["announce", str(write(tmp_path, GOOD)), "--yes"], remote, ask=never)
    assert code == 0 and remote.announcement


def test_announce_live_mismatch(tmp_path, live, capsys):
    remote = FakeRemote()
    live["override"] = {"id": "old", "message": {"zh-TW": "x"}, "until": None}
    code = vps.main(["announce", str(write(tmp_path, GOOD)), "--yes"], remote=remote, out=io.StringIO())
    assert code == 1
    assert '"id": "old"' in capsys.readouterr().err


def test_announce_live_unreachable(tmp_path, live, capsys):
    remote = FakeRemote()
    live["error"] = OSError("timed out")
    code = vps.main(["announce", str(write(tmp_path, GOOD)), "--yes"], remote=remote, out=io.StringIO())
    assert code == 1 and remote.announcement                     # 已上傳,只是無法確認
    assert "無法" in capsys.readouterr().err


def test_announce_needs_file_or_clear(live):
    with pytest.raises(SystemExit):
        vps.main(["announce"], remote=FakeRemote(), out=io.StringIO())


# ---- announce --clear ----

def test_clear(live):
    remote = FakeRemote(announcement=json.dumps(GOOD))
    live["remote"] = remote
    code, out = run(["announce", "--clear"], remote)
    assert code == 0 and remote.announcement is None
    assert "沒有公告" in out


def test_clear_without_announcement(live):
    remote = FakeRemote()
    live["remote"] = remote
    code, out = run(["announce", "--clear"], remote)
    assert code == 0
    assert "目前沒有公告檔" in out


# ---- status ----

def test_status_is_read_only(local_cards, live):
    local_cards("M-001", "M-002")
    remote = FakeRemote(cards={"M-001.webp"}, announcement=json.dumps(GOOD))
    live["remote"] = remote
    code, out = run(["status"], remote)
    assert code == 0
    assert "線上版本:v1.3.3" in out
    assert "app\tUp 2 hours (healthy)" in out and "watchtower" in out
    assert "VPS 1 張,本機 2 張" in out
    assert "公告:m1" in out and "今晚維護" in out
    assert all(s.startswith("find ") for s in remote.scripts() if s != "{{.Service}}\t{{.Status}}")
    assert remote.uploaded == [] and remote.announcement
