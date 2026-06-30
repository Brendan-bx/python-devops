import json
import logging
import pathlib
from models import Server

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    pass


class ConfigLoader:
    def __init__(self, path: str):
        self.path = pathlib.Path(path)

    def load(self) -> list[Server]:
        logger.info("Loading config from %s", self.path)
        try:
            raw = json.loads(self.path.read_text())
        except FileNotFoundError:
            logger.error("Config file not found: %s", self.path)
            raise ConfigError(f"File not found: {self.path}")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON: %s", e)
            raise ConfigError(f"Invalid JSON: {e}") from e

        servers = []
        for i, entry in enumerate(raw, start=1):
            servers.append(Server(
                id=i,
                name=entry["name"],
                host=entry["host"],
                port=entry["port"],
            ))
        logger.info("Loaded %d servers", len(servers))
        return servers
