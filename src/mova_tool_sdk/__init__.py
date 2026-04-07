from dataclasses import dataclass

from .client import MovaClient
from .config import MovaConfig, load_config, save_config


class Mova(MovaClient):
    """Canonical public Python API entrypoint."""


@dataclass
class Forge:
    api_key: str | None = None

    def start(self, intent: str | None = None) -> dict[str, object]:
        return {
            "ok": True,
            "status": "scaffold",
            "message": "Forge interactive flow is the next SDK slice.",
            "intent": intent,
        }


__all__ = [
    "Mova",
    "Forge",
    "MovaClient",
    "MovaConfig",
    "load_config",
    "save_config",
]
