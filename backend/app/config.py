import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
REPLAY_DIR = DATA_DIR / "replay"


def _load_env_file() -> None:
    env = BACKEND_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_env_file()


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    offline: bool = _flag("JAGAPADI_OFFLINE")
    record: bool = _flag("JAGAPADI_RECORD")
    openweather_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "").lower()
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "claude-opus-5-5")
    user_agent: str = os.getenv("JAGAPADI_USER_AGENT", "Jagapadi/0.1 (rice field monitoring research prototype)")
    # Fields above this size slow the satellite reads and multiply elevation requests.
    max_field_ha: float = float(os.getenv("JAGAPADI_MAX_FIELD_HA", "200"))
    allowed_origins: str = os.getenv("JAGAPADI_CORS", "http://localhost:5173")


settings = Settings()
