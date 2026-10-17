"""Carga la configuración local sin depender del directorio de ejecución."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def load_environment() -> None:
    """Carga mediflow/.env; las variables ya exportadas tienen prioridad."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)

class RuntimeSettings(BaseSettings):
    """Opciones tipadas del servidor; .env se carga solo por load_environment."""

    model_config = SettingsConfigDict(extra="ignore")
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def accept_release_mode(cls, value):
        # Some Windows tooling exports DEBUG=release; never enable debug for it.
        if isinstance(value, str) and value.strip().lower() == "release":
            return False
        return value
