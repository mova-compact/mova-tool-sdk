from pathlib import Path

from mova_tool_sdk.config import DEFAULT_BASE_URL, load_config, mova_home


def test_load_config_uses_env_base_url_override(monkeypatch):
    monkeypatch.setenv("MOVA_BASE_URL", "http://127.0.0.1:8787")
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == "http://127.0.0.1:8787"


def test_load_config_prefers_platform_url(monkeypatch):
    monkeypatch.setenv("MOVA_PLATFORM_URL", "https://api.mova-lab.eu")
    monkeypatch.setenv("MOVA_BASE_URL", "http://127.0.0.1:8787")
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == "https://api.mova-lab.eu"


def test_load_config_defaults_without_env(monkeypatch):
    monkeypatch.delenv("MOVA_BASE_URL", raising=False)
    monkeypatch.delenv("MOVA_PLATFORM_URL", raising=False)
    monkeypatch.delenv("MCP_DOOR_BASE_URL", raising=False)
    monkeypatch.delenv("MOVA_DOOR_BASE_URL", raising=False)
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == DEFAULT_BASE_URL


def test_load_config_accepts_existing_mcp_door_url_alias(monkeypatch):
    monkeypatch.delenv("MOVA_PLATFORM_URL", raising=False)
    monkeypatch.delenv("MOVA_BASE_URL", raising=False)
    monkeypatch.setenv("MCP_DOOR_BASE_URL", "https://engine15.example.workers.dev")
    config = load_config(Path("tests") / "_missing_config.json")
    assert config.base_url == "https://engine15.example.workers.dev"


def test_mova_home_uses_env_override(monkeypatch):
    monkeypatch.setenv("MOVA_HOME", "D:/Projects_MOVA/_mova_meta/tmp/mova_home_test")
    assert str(mova_home()).endswith("D:\\Projects_MOVA\\_mova_meta\\tmp\\mova_home_test")
