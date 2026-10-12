# Agregado por Edil: completa el módulo LLM pendiente; conserva las entregas previas.
"""Prueba manual opt-in de Gemini con documentos sintéticos. No hace llamadas OCI."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prueba manual del módulo LLM MediFlow")
    parser.add_argument("--file", type=Path, help="TXT, PDF, JPG o PNG, exclusivamente sintético")
    parser.add_argument("--allow-gemini", action="store_true", help="Autoriza una llamada real que puede generar costes")
    parser.add_argument("--synthetic", action="store_true", help="Confirma que el archivo no contiene datos clínicos reales")
    args = parser.parse_args(argv)
    if not args.allow_gemini or not args.synthetic:
        print("Prueba real desactivada. Requiere --allow-gemini y --synthetic.")
        return 2
    if args.file is None:
        print("Indica un archivo sintético mediante --file.")
        return 2

    # Entrada manual portable; importa el mismo paquete app usado por FastAPI.
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_dir))
    from app.services.document_text import MAX_DOCUMENT_BYTES
    from app.services.gemini_client import GeminiClinicalClient
    from app.services.llm_errors import LLMError

    try:
        with args.file.open("rb") as source:
            content = source.read(MAX_DOCUMENT_BYTES + 1)
        with GeminiClinicalClient() as service:
            # Agregado por Edil: reutiliza el cliente seguro para los formatos de Nicolás.
            # La extracción de PDF con texto sigue separada; las imágenes requieren un modelo compatible.
            service.process_document(
                content, args.file.name,
                document_id="DOC-DEMO-GEMINI",
                storage={
                    "bucket": "recibidos",
                    "ruta_objeto": "demo-gemini.txt",
                    "status_backup": "no_verificado",
                },
            )
        print("GEMINI_OK: respuesta recibida y contrato validado.")
        print("No se muestran datos clínicos ni se ha almacenado ningún objeto en OCI.")
        return 0
    except LLMError as error:
        print(str(error))  # Solo mensajes sanitizados del módulo.
        return 1
    except OSError:
        print("No se pudo leer el archivo de prueba.")
        return 2
    except Exception:
        print("No se pudo completar la prueba; revisa las dependencias locales.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
