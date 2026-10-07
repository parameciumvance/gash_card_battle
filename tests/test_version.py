"""版本號(battle-api「執行環境中繼資訊」、docker-deployment「Production 容器映像檔」)。"""
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from gash import version
from gash.api.app import app

ROOT = Path(__file__).resolve().parents[1]


def fresh(monkeypatch, *, env=None, root=None):
    version.app_version.cache_clear()
    if env is None:
        monkeypatch.delenv("GASH_VERSION", raising=False)
    else:
        monkeypatch.setenv("GASH_VERSION", env)
    if root is not None:
        monkeypatch.setattr(version, "app_root", lambda: root)
    return version.app_version()


def test_env_first(monkeypatch):
    assert fresh(monkeypatch, env="v0.9.1", root=ROOT) == "v0.9.1"


def test_git_describe_in_dev(monkeypatch):
    expected = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    assert expected
    assert fresh(monkeypatch, root=ROOT) == expected


def test_dev_when_nothing_available(monkeypatch, tmp_path):
    assert fresh(monkeypatch, root=tmp_path) == "dev"


def test_meta_reports_version(monkeypatch):
    fresh(monkeypatch, env="v0.9.1")
    assert TestClient(app).get("/api/meta").json()["version"] == "v0.9.1"
    version.app_version.cache_clear()


def test_docker_and_ci_pass_tag():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG GASH_VERSION" in dockerfile and "ENV GASH_VERSION=$GASH_VERSION" in dockerfile
    deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "GASH_VERSION=${{ github.ref_name }}" in deploy
