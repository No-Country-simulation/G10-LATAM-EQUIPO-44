from pathlib import Path
from typing import Optional, Dict, Any
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Rutas donde puede estar alojado el archivo .env:
# 1. mediflow/.env
# 2. Raíz del repositorio / .env
# 3. Directorio de ejecución actual
BACKEND_DIR = Path(__file__).resolve().parents[2]    # .../mediflow/backend
MEDIFLOW_DIR = BACKEND_DIR.parent                   # .../mediflow
REPO_ROOT = MEDIFLOW_DIR.parent                     # .../G10-LATAM-EQUIPO-44

ENV_CANDIDATES = (
    str(MEDIFLOW_DIR / ".env"),
    str(REPO_ROOT / ".env"),
    str(BACKEND_DIR / ".env"),
    ".env",
)


class Settings(BaseSettings):
    """
    Configuración global centralizada de la aplicación MediFlow.
    Carga variables de entorno desde el sistema y desde archivos .env.
    """
    model_config = SettingsConfigDict(
        env_file=ENV_CANDIDATES,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Entorno y servidor
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = True

    # Configuración de OCI (Oracle Cloud Infrastructure)
    OCI_USER_OCID: Optional[str] = None
    OCI_FINGERPRINT: Optional[str] = None
    OCI_KEY_FILE: Optional[str] = None
    OCI_TENANCY_OCID: Optional[str] = None
    OCI_REGION: Optional[str] = None
    OCI_COMPARTMENT_OCID: Optional[str] = None

    # OCI Object Storage (Buckets segregados por estado)
    OCI_BUCKET_NAME: str = "mediflow-documents"
    OCI_BUCKET_RECIBIDOS: str = "recibidos"
    OCI_BUCKET_PROCESADOS: str = "procesados"
    OCI_BUCKET_AUDITORIA: str = "auditoria_humana"
    OCI_NAMESPACE: Optional[str] = None

    # OCI Generative AI / Vision
    OCI_GENAI_ENDPOINT: Optional[str] = "https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com"
    OCI_GENAI_MODEL_ID: Optional[str] = "cohere.command-r-plus-08-2024"

    # Base de Datos / Almacenamiento local
    DATABASE_URL: str = "sqlite:///./mediflow.db"

    def has_oci_env_credentials(self) -> bool:
        """
        Verifica si se proveyeron las credenciales de OCI completas y válidas vía .env o variables de entorno.
        Descarta valores de ejemplo del .env.example (como 'example', '...') y verifica que el archivo de clave exista.
        """
        required = [
            self.OCI_USER_OCID,
            self.OCI_FINGERPRINT,
            self.OCI_KEY_FILE,
            self.OCI_TENANCY_OCID,
            self.OCI_REGION,
        ]

        # Validar presencia y que no sean placeholders de ejemplo
        dummy_markers = ("example", "...", "ocid1.user.oc1..example")
        for val in required:
            if not val or any(marker in str(val) for marker in dummy_markers):
                return False

        # Validar que el archivo de clave privada exista en disco
        key_path = os.path.expanduser(self.OCI_KEY_FILE) if self.OCI_KEY_FILE else ""
        return os.path.isfile(key_path)

    def get_oci_config_dict(self) -> Optional[Dict[str, Any]]:
        """
        Genera el diccionario de configuración para autenticarse con el SDK de OCI.
        Retorna None si no se cuenta con las credenciales completas en el entorno.
        """
        if not self.has_oci_env_credentials():
            return None

        key_path = os.path.expanduser(self.OCI_KEY_FILE) if self.OCI_KEY_FILE else ""
        return {
            "user": self.OCI_USER_OCID,
            "fingerprint": self.OCI_FINGERPRINT,
            "key_file": key_path,
            "tenancy": self.OCI_TENANCY_OCID,
            "region": self.OCI_REGION,
        }


settings = Settings()
