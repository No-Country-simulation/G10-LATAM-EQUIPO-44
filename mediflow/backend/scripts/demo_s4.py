"""Demos técnicas S4-04 sobre dataset sintético. No procesa pacientes reales."""
import argparse
import os
from pathlib import Path

from app.services.gemini_client import GeminiClinicalClient
from app.services.servicio_orquestador import procesar_con_orquestador

CASES = {
    "MF_005": ("normal", "Rutina"),
    "MF_008": ("urgente", "Urgente"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("caso", choices=CASES)
    args = parser.parse_args()
    if os.environ.get("TRIAGE_RULES_PROFILE") != "synthetic_demo_v1":
        parser.error("Configura TRIAGE_RULES_PROFILE=synthetic_demo_v1 explícitamente")
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GEMINI_MODEL"):
        parser.error("Faltan GEMINI_API_KEY o GEMINI_MODEL")
    folder, expected = CASES[args.caso]
    files = list((Path(__file__).resolve().parent / "data_ai" / "dataset" / folder).glob(args.caso + "*.jpg"))
    if len(files) != 1:
        parser.error("No se encontró un único JPG para " + args.caso)
    file = files[0]
    # Simulación contractual; no prueba ni escribe OCI.
    storage = {"bucket": "recibidos", "ruta_objeto": "synthetic/" + file.name, "status_backup": "exito"}
    print("CASO:", args.caso, "| MODELO:", os.environ["GEMINI_MODEL"], flush=True)
    try:
        with GeminiClinicalClient() as client:
            doc, source = client.process_document_with_source(
                file.read_bytes(), file.name, document_id=args.caso, storage=storage)
        before = doc.model_dump()
        after = procesar_con_orquestador(before, source_text=source)
        dec0, dec1 = before["decision_enrutamiento"], after["decision_enrutamiento"]
        print("GEMINI:", before["clasificacion"]["nivel_prioridad"], dec0["destino_principal"], dec0["requiere_auditoria_humana"])
        print("FINAL:", after["clasificacion"]["nivel_prioridad"], dec1["destino_principal"], dec1["requiere_auditoria_humana"], after["status"])
        print("FUENTE DISPONIBLE:", bool(source.strip()))
        success = after["clasificacion"]["nivel_prioridad"] == expected
        print("ESPERADO:", expected, "| RESULTADO:", "PASS" if success else "FAIL")
        if not success:
            raise SystemExit(1)
    except Exception as error:
        print("ERROR:", type(error).__name__, str(error))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
