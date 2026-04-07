from .client import MovaClient
from .config import MovaConfig, load_config, save_config
from .forge import ForgeSession, start_forge


class Mova(MovaClient):
    """Canonical public Python API entrypoint."""


class Forge:
    api_key: str | None = None

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def start(self, intent: str | None = None, from_path: str | None = None) -> ForgeSession:
        return start_forge(intent=intent, source_path=from_path)


__all__ = [
    "Mova",
    "Forge",
    "ForgeSession",
    "MovaClient",
    "MovaConfig",
    "load_config",
    "save_config",
    "start_forge",
]
