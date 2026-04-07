from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_BASE_URL = "https://api.mova-lab.eu"
CONFIG_DIR = Path.home() / ".mova"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class MovaConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    profile_id: str | None = None
    default_owner_id: str | None = None
    admin_read_token: str | None = None
    runtime_execute_token: str | None = None
    operator_recovery_token: str | None = None
    connector_registry: list[dict[str, str]] = field(default_factory=list)


def load_config(path: Path = CONFIG_PATH) -> MovaConfig:
    if not path.exists():
        config = MovaConfig()
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        config = MovaConfig(
            api_key=payload.get("api_key") or os.environ.get("MOVA_API_KEY"),
            base_url=payload.get("platform_url", payload.get("base_url", DEFAULT_BASE_URL)),
            profile_id=payload.get("profile_id"),
            default_owner_id=payload.get("default_owner_id"),
            admin_read_token=payload.get("admin_read_token"),
            runtime_execute_token=payload.get("runtime_execute_token"),
            operator_recovery_token=payload.get("operator_recovery_token"),
            connector_registry=list(payload.get("connector_registry", [])),
        )

    config.api_key = config.api_key or os.environ.get("MOVA_API_KEY")
    # `MOVA_PLATFORM_URL` is canonical; `MOVA_BASE_URL` remains a local/dev compatibility alias.
    config.base_url = (
        os.environ.get("MOVA_PLATFORM_URL")
        or os.environ.get("MOVA_BASE_URL")
        or config.base_url
        or DEFAULT_BASE_URL
    )
    return config


def save_config(config: MovaConfig, path: Path = CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    return path
