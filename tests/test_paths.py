"""資源目錄解析:搜尋順序、環境變數優先、未安裝回報、開發模式等價。"""

from pathlib import Path

from gash import paths


def test_dev_mode_matches_repo_layout():
    root = paths.app_root()
    assert (root / "frontend" / "index.html").is_file()
    assert (root / "data" / "cards.json").is_file()
    assert paths.frontend_dir() == root / "frontend"
    assert paths.data_dir() == root / "data"


def test_dev_mode_assets_fall_back_to_repo(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "user_assets_dir", lambda: tmp_path / "nope")
    info = paths.resolve_assets(env={})
    assert info.installed
    assert info.dir == paths.frontend_dir() / "assets"


def test_env_var_wins_even_if_missing(tmp_path):
    missing = tmp_path / "custom"
    info = paths.resolve_assets(env={paths.ENV_ASSETS: str(missing)})
    assert info.dir == missing
    assert not info.installed

    (missing / "cards").mkdir(parents=True)
    info = paths.resolve_assets(env={paths.ENV_ASSETS: str(missing)})
    assert info.installed


def test_frozen_prefers_exe_adjacent(monkeypatch, tmp_path):
    exe_assets = tmp_path / "exe" / "assets"
    (exe_assets / "cards").mkdir(parents=True)
    user = tmp_path / "user" / "assets"
    (user / "cards").mkdir(parents=True)
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "exe_dir", lambda: tmp_path / "exe")
    monkeypatch.setattr(paths, "user_assets_dir", lambda: user)
    info = paths.resolve_assets(env={})
    assert info.dir == exe_assets


def test_empty_dir_not_treated_as_installed(monkeypatch, tmp_path):
    # 自動建立的空安裝點不得搶走解析(否則開發模式會解析到空目錄)
    empty_user = tmp_path / "user" / "assets"
    empty_user.mkdir(parents=True)
    monkeypatch.setattr(paths, "user_assets_dir", lambda: empty_user)
    info = paths.resolve_assets(env={})
    assert info.dir == paths.frontend_dir() / "assets"


def test_frozen_falls_back_to_user_dir(monkeypatch, tmp_path):
    user = tmp_path / "user" / "assets"
    (user / "cards").mkdir(parents=True)
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "exe_dir", lambda: tmp_path / "exe")
    monkeypatch.setattr(paths, "user_assets_dir", lambda: user)
    info = paths.resolve_assets(env={})
    assert info.dir == user
    assert info.installed


def test_frozen_nothing_installed_reports_install_dir(monkeypatch, tmp_path):
    user = tmp_path / "user" / "assets"
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "exe_dir", lambda: tmp_path / "exe")
    monkeypatch.setattr(paths, "user_assets_dir", lambda: user)
    info = paths.resolve_assets(env={})
    assert not info.installed
    assert info.install_dir == user
    assert info.dir == user
