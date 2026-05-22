"""Application configuration: paths and environment variable loading."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (no-op if missing)."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


@dataclass
class AppConfig:
    """Central configuration object.  Instantiate once at application start."""

    finmind_token: str = field(default_factory=lambda: os.getenv("FINMIND_TOKEN", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    env: str = field(default_factory=lambda: os.getenv("MIDAS_ENV", "production"))

    # Data directory: %APPDATA%\Midas  (or overridden by MIDAS_DATA_DIR)
    data_dir: Path = field(init=False)
    db_path: Path = field(init=False)

    def __post_init__(self) -> None:
        override = os.getenv("MIDAS_DATA_DIR", "").strip()
        if override:
            self.data_dir = Path(override)
        else:
            self.data_dir = Path(user_data_dir("Midas", appauthor=False))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "midas.db"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


def load_config() -> AppConfig:
    """Load .env file (if present) then return an AppConfig instance."""
    _load_env_file(_ENV_FILE)
    return AppConfig()
