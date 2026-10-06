"""版本號(battle-api「執行環境中繼資訊」、docker-deployment「Production 容器映像檔」、
standalone-release「發行打包」)。"""
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from gash import version
from gash.api.app import app

ROOT = Path(__file__).resolve().parents[1]


def fresh(monkeypatch, *, env=None, data_dir=None, root=None):
    version.app_version.cache_clear()
    if env is None:
        monkeypatch.delenv("GASH_VERSION", raising=False)
    else:
        monkeypatch.setenv("GASH_VERSION", env)
    if data_dir is not None:
        monkeypatch.setattr(version, "data_dir", lambda: data_dir)
    if root is not None:
        monkeypatch.setattr(version, "app_root", lambda: root)
    return version.app_version()


def test_env_first(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("v-file\n", encoding="utf-8")
    assert fresh(monkeypatch, env="v0.9.1", data_dir=tmp_path) == "v0.9.1"


def test_version_file_second(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("v0.9.0-2-gabc\n", encoding="utf-8")
    assert fresh(monkeypatch, data_dir=tmp_path) == "v0.9.0-2-gabc"


def test_git_describe_in_dev(monkeypatch, tmp_path):
    expected = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    assert expected
    assert fresh(monkeypatch, data_dir=tmp_path, root=ROOT) == expected


def test_dev_when_nothing_available(monkeypatch, tmp_path):
    assert fresh(monkeypatch, data_dir=tmp_path, root=tmp_path) == "dev"


def test_meta_reports_version(monkeypatch):
    fresh(monkeypatch, env="v0.9.1")
    assert TestClient(app).get("/api/meta").json()["version"] == "v0.9.1"
    version.app_version.cache_clear()


def test_docker_and_ci_pass_tag():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG GASH_VERSION" in dockerfile and "ENV GASH_VERSION=$GASH_VERSION" in dockerfile
    deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "GASH_VERSION=${{ github.ref_name }}" in deploy


def test_release_writes_version_file():
    source = (ROOT / "tools/build_release.py").read_text(encoding="utf-8")
    assert '"version.txt"' in source
    assert "data/version.txt" in (ROOT / ".gitignore").read_text(encoding="utf-8")
