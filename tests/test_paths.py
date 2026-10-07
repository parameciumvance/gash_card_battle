"""卡圖目錄解析(battle-api「卡圖靜態資源外部化」)與程式資源的 repo 佈局。"""

from gash import paths


def test_program_resources_use_repo_layout():
    root = paths.app_root()
    assert (root / "frontend" / "index.html").is_file()
    assert (root / "data" / "cards.json").is_file()
    assert paths.frontend_dir() == root / "frontend"
    assert paths.data_dir() == root / "data"


def test_assets_default_to_repo_frontend():
    assert paths.resolve_assets(env={}).dir == paths.frontend_dir() / "assets"


def test_env_var_wins_even_if_missing(tmp_path):
    missing = tmp_path / "custom"
    info = paths.resolve_assets(env={paths.ENV_ASSETS: str(missing)})
    assert info.dir == missing
    assert not info.installed

    (missing / "cards").mkdir(parents=True)
    info = paths.resolve_assets(env={paths.ENV_ASSETS: str(missing)})
    assert info.installed


def test_installed_requires_cards_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "frontend_dir", lambda: tmp_path)
    (tmp_path / "assets").mkdir()                       # 空的 assets/ 不算已安裝
    info = paths.resolve_assets(env={})
    assert info.dir == tmp_path / "assets"
    assert not info.installed
    (tmp_path / "assets" / "cards").mkdir()
    assert paths.resolve_assets(env={}).installed


def test_user_data_dir_is_not_searched(monkeypatch, tmp_path):
    # 舊單機版的使用者資料夾即使有卡圖也不讀
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    (tmp_path / "gash-card-battle" / "assets" / "cards").mkdir(parents=True)
    assert paths.resolve_assets(env={}).dir == paths.frontend_dir() / "assets"
