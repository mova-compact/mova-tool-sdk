from pathlib import Path

from mova_tool_sdk.config import DEFAULT_BASE_URL, load_config


def test_load_config_uses_env_base_url_override(monkeypatch):
    monkeypatch.setenv("MOVA_BASE_URL", "http://127.0.0.1:8787")
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == "http://127.0.0.1:8787"


def test_load_config_defaults_without_env(monkeypatch):
    monkeypatch.delenv("MOVA_BASE_URL", raising=False)
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == DEFAULT_BASE_URL
