import pytest

from app.config import load_settings


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError):
        load_settings()


def test_defaults_when_only_key_given(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-tests")
    # 必须显式清掉，否则读到的是本地 .env 里灌进来的值，测的就不是默认值了
    # （CI 上没 .env，不清的话本地和流水线会跑出两种结果）
    for key in ("DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "CHAOXI_DB"):
        monkeypatch.delenv(key, raising=False)
    s = load_settings()
    assert s.deepseek_base_url == "https://api.deepseek.com"
    assert s.deepseek_model == "deepseek-flash"
    assert s.db_path.name == "chaoxi.db"