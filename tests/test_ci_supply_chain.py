"""CI 與映像檔的供應鏈設定(docker-deployment「CI 的權限與相依鎖定」,ci-supply-chain)。

靜態檢查:token 最小權限、action 釘 commit SHA、相依依 hash 安裝、映像檔釘 digest、Dependabot 涵蓋這些來源。
"""
import re
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------- workflow

@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_declares_top_level_permissions(path):
    # 頂層權限:測試唯讀、部署預設不給(建置 job 自己打開);repo 預設也是唯讀,這裡再寫明
    text = path.read_text(encoding="utf-8")
    top = re.search(r"^permissions:(.*)$", text, re.M)
    assert top, f"{path.name} 沒有頂層 permissions"
    block = text[top.start():].split("\n\n", 1)[0]
    assert "write" not in block


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_actions_pinned_to_commit_sha(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(?:-\s*)?uses:\s*(\S+)(.*)$", line)
        if not m or m.group(1).startswith("./"):
            continue
        ref = m.group(1).rsplit("@", 1)
        assert len(ref) == 2 and SHA_RE.match(ref[1]), f"{path.name}: {line.strip()} 不是 commit SHA"
        assert re.search(r"#\s*v\d+\.\d+\.\d+", m.group(2)), f"{path.name}: {line.strip()} 缺少版本號註解"


def test_only_build_job_can_write():
    deploy = read(".github/workflows/deploy.yml")
    assert re.search(r"^permissions: \{\}$", deploy, re.M)
    writes = re.findall(r"^\s+(\w+): write", deploy, re.M)
    assert sorted(writes) == ["contents", "packages"]                       # 只在 build-and-push


def test_ci_installs_from_hashed_lock():
    test = read(".github/workflows/test.yml")
    assert "pip install --require-hashes -r requirements-dev.lock" in test
    assert "pip install --no-deps --no-build-isolation -e ." in test
    assert 'pip install -e ".[dev]"' not in test


# ---------------------------------------------------------------- lock 檔

def pins(rel: str) -> dict[str, str]:
    """lock 檔的 {套件: 版本};每個版本都要帶 hash。"""
    out = {}
    blocks = re.split(r"\n(?=[A-Za-z0-9])", read(rel))
    for block in blocks:
        m = re.match(r"([A-Za-z0-9_.\-]+)==([^\s\\]+)", block)
        if not m:
            continue
        assert "--hash=sha256:" in block, f"{rel}: {m.group(1)} 沒有 hash"
        out[canonicalize_name(m.group(1))] = m.group(2)
    return out


def project():
    return tomllib.loads(read("pyproject.toml"))


@pytest.mark.parametrize("rel, extras", [("requirements.lock", ()), ("requirements-dev.lock", ("dev",))])
def test_lock_covers_pyproject(rel, extras):
    # pyproject 的每個相依(含建置用的 setuptools)都在 lock 裡,版本符合範圍;改了 pyproject 忘了重產 lock 會失敗
    proj = project()
    reqs = list(proj["project"]["dependencies"]) + list(proj["build-system"]["requires"])
    for extra in extras:
        reqs += proj["project"]["optional-dependencies"][extra]
    locked = pins(rel)
    for spec in reqs:
        req = Requirement(spec)
        name = canonicalize_name(req.name)
        assert name in locked, f"{rel} 缺少 {req.name}"
        assert req.specifier.contains(locked[name], prereleases=True), f"{rel}: {name}=={locked[name]} 不符合 {spec}"


def test_production_lock_has_no_dev_packages():
    dev_only = {canonicalize_name(Requirement(s).name) for s in project()["project"]["optional-dependencies"]["dev"]}
    assert not dev_only & set(pins("requirements.lock"))


# ---------------------------------------------------------------- 映像檔

def test_dockerfile_pins_base_and_installs_with_hashes():
    docker = read("Dockerfile")
    assert re.search(r"^FROM \S+@sha256:[0-9a-f]{64}$", docker, re.M)
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock" in docker
    assert "pip install --no-cache-dir --no-deps --no-build-isolation -e ." in docker


def test_watchtower_pinned_cloudflared_auto():
    # watchtower 掛 Docker socket:釘版本與 digest;cloudflared 維持 :latest 自動更新(使用者決定)
    compose = read("docker-compose.yml")
    assert re.search(r"image: ghcr\.io/nicholas-fedor/watchtower:[\w.]+@sha256:[0-9a-f]{64}$", compose, re.M)
    assert "image: cloudflare/cloudflared:latest" in compose


# ---------------------------------------------------------------- Dependabot

def test_dependabot_covers_pinned_sources():
    text = read(".github/dependabot.yml")
    ecosystems = re.findall(r"package-ecosystem:\s*([\w-]+)", text)
    assert sorted(ecosystems) == ["docker", "docker-compose", "github-actions", "pip"]
    assert text.count("target-branch: dev") == len(ecosystems)
