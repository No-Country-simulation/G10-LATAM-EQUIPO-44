"""Verifica carga de entorno sin acceder a credenciales ni OCI."""

from pathlib import Path

from app.core import environment
from app.core.oci_client import OCISettings


def test_env_path_is_relative_to_project():
    assert environment.ENV_FILE == Path(__file__).resolve().parents[2] / ".env"


def test_loads_oci_variables_without_overriding_terminal(tmp_path, monkeypatch):
    config = tmp_path / ".env"
    config.write_text(
        "OCI_CONFIG_PROFILE=DEFAULT\n"
        "OCI_BUCKET_RECIBIDOS=recibidos\n"
        "OCI_BUCKET_PROCESADOS=procesados\n"
        "OCI_BUCKET_AUDITORIA=auditoria_humana\n", encoding="utf-8",
    )
    monkeypatch.setattr(environment, "ENV_FILE", config)
    for name in ("OCI_BUCKET_RECIBIDOS", "OCI_BUCKET_PROCESADOS", "OCI_BUCKET_AUDITORIA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OCI_CONFIG_PROFILE", "PERFIL_TERMINAL")
    environment.load_environment()
    settings = OCISettings.from_environment()
    assert settings.config_profile == "PERFIL_TERMINAL"
    assert settings.bucket_recibidos == "recibidos"
    assert settings.bucket_procesados == "procesados"
    assert settings.bucket_auditoria == "auditoria_humana"


def test_missing_env_is_optional(tmp_path, monkeypatch):
    monkeypatch.setattr(environment, "ENV_FILE", tmp_path / "missing.env")
    environment.load_environment()

def test_runtime_settings_parse_booleans_and_environment(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    settings = environment.RuntimeSettings()
    assert settings.DEBUG is False
    assert settings.ENVIRONMENT == "staging"


def test_runtime_settings_reject_invalid_debug(monkeypatch):
    import pytest
    from pydantic import ValidationError
    monkeypatch.setenv("DEBUG", "invalid")
    with pytest.raises(ValidationError):
        environment.RuntimeSettings()


def test_runtime_settings_accept_tooling_release_without_enabling_debug(monkeypatch):
    monkeypatch.setenv("DEBUG", "release")
    assert environment.RuntimeSettings().DEBUG is False
