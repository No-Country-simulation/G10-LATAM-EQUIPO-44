"""Prueba local de Gemini: documentos sintéticos exclusivamente. No ejecutar con datos reales sin autorización."""
# Importación de librerías para manejo de argumentos de consola, JSON, variables de entorno y rutas
import argparse
import json
import os
from pathlib import Path

# Importación del SDK oficial de Google GenAI
from google import genai
from google.genai import types

# Importación de validadores para asegurar la integridad de los datos mediante JSON Schema
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

# Definición del directorio raíz relativo al script actual
ROOT = Path(__file__).resolve().parent

# Mapeo de extensiones de archivos multimedia válidos a sus respectivos tipos MIME
MIMES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

# Función principal para analizar documentos médicos con el modelo de IA
def analyze(document: Path, model: str, processing_date: str | None = None) -> dict:
    # Verifica que el archivo de entrada exista realmente
    if not document.is_file():
        raise FileNotFoundError(document)
    # Asegura que la extensión del archivo sea soportada (.txt o imágenes/PDF estructurados)
    if document.suffix.lower() not in set(MIMES) | {".txt"}:
        raise ValueError(f"Formato no admitido: {document.suffix}")
    # Verifica que la clave de la API esté definida en el sistema antes de iniciar
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("Falta GEMINI_API_KEY en las variables de entorno")

    # Carga del esquema para la estructura JSON esperada, las reglas de negocio y el prompt principal
    schema = json.loads((ROOT / "schemas/mediflow_schema.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "rules/triage_rules_v1.json").read_text(encoding="utf-8"))
    prompt = (ROOT / "prompts/master_prompt.txt").read_text(encoding="utf-8")
    
    # Valida que el archivo de esquema JSON cargado sea sintácticamente correcto
    Draft202012Validator.check_schema(schema)

    # Preparación de las entradas/parámetros para el modelo (prompt, reglas y fecha contextual)
    # Nota: Se omite intencionadamente el nombre del archivo para prevenir sesgos de clasificación
    contents = [prompt, "Reglas experimentales:\n" + json.dumps(rules, ensure_ascii=False),
                "Fecha de procesamiento externa: " + (processing_date or "no proporcionada")]
                
    # Inserción del contenido del archivo ya sea como texto o binario con tipo MIME correcto
    if document.suffix.lower() == ".txt":
        contents.append(document.read_text(encoding="utf-8"))
    else:
        contents.append(types.Part.from_bytes(data=document.read_bytes(), mime_type=MIMES[document.suffix.lower()]))

    # Inicialización de la sesión del cliente de Google GenAI
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    # Petición a la API de Gemini configurando un formato estructurado e induciendo baja variabilidad con temperature=0
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,
        ),
    )
    
    # Validación de que la API de Gemini haya retornado un texto legible
    if not response.text:
        raise RuntimeError("Gemini no devolvió texto JSON")
        
    # Conversión del texto retornado a un diccionario nativo de Python y validación de esquema estándar
    result = json.loads(response.text)
    Draft202012Validator(schema).validate(result)
    
    # Validación cruzada personalizada de las reglas de consistencia de negocio
    validate_consistency(result)
    return result


# Función secundaria que contiene e implementa las reglas lógicas invariables del proceso sanitario
def validate_consistency(result: dict) -> None:
    """Valida invariantes de la matriz de estados; no constituye triaje clínico."""
    state = result["status"]
    routing = result["decision_enrutamiento"]
    review = routing["requiere_auditoria_humana"]
    dest = routing["destino_principal"]
    
    # Regla: El estado de auditoría humana debe obligatoriamente solicitar revisión y apuntar a la cola correcta
    if state == "auditoria_humana" and (not review or dest != "Cola_Revision_Humana"):
        raise ValueError("auditoria_humana requiere revisión y Cola_Revision_Humana")
    
    # Regla: Un estado completamente procesado no puede tener tareas de auditoría ni colas pendientes humanas
    if state == "procesado" and (review or dest == "Cola_Revision_Humana"):
        raise ValueError("procesado no puede requerir auditoría humana")
        
    # Regla: Si existe algún medicamento catalogado explícitamente como 'ILLEGIBLE', se debe pausar para auditoría
    if any(m["dosis"] == "ILLEGIBLE" for m in result["datos_extraidos encampados"] if "medicamentos_recetados" in result["datos_extraidos"] for m in result["datos_extraidos"]["medicamentos_recetados"]):
        if state != "auditoria_humana":
            raise ValueError("Dosis ilegible exige auditoria_humana")
            
    # Regla alternativa rápida para comprobar 'medicamentos_recetados'
    if any(m.get("dosis") == "ILLEGIBLE" for m in result.get("datos_extraidos", {}).get("medicamentos_recetados", [])):
        if state != "auditoria_humana":
            raise ValueError("Dosis ilegible exige auditoria_humana")
            
    # Regla: Todo caso clasificado como urgente de forma directa requiere la cola de emergencias médicas
    if result.get("clasificacion", {}).get("nivel_prioridad") == "Urgente" and state == "procesado":
        if dest != "Cola_Emergencia_Medica":
            raise ValueError("Urgente procesado exige cola de emergencia en las reglas de prueba")

# Función para gestionar la ejecución autónoma en terminal / CLI
def main():
    parser = argparse.ArgumentParser(description="MediFlow S2-01: prueba de extracción con Gemini")
    parser.add_argument("document", type=Path, help="Ruta al documento médico de prueba")
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), help="Modelo de Gemini a llamar")
    parser.add_argument("--processing-date", help="Fecha externa YYYY-MM-DD para pruebas de vigencia")
    parser.add_argument("--output", type=Path, default=Path("resultado_gemini.json"), help="Destino final del archivo resultante")
    args = parser.parse_args()
    
    # Validación sintáctica para fechas proporcionadas desde la CLI
    if args.processing_date:
        from datetime import date
        try:
            date.fromisoformat(args.processing_date)
        except ValueError as exc:
            parser.error(f"--processing-date debe tener formato YYYY-MM-DD: {exc}")
            
    # Ejecución del análisis y guardado formateado con sangría de 2 espacios
    result = analyze(args.document, args.model, args.processing_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"JSON validado y guardado: {args.output}")


# Declaración de punto de entrada inicial del archivo ejecutable
if __name__ == "__main__":
    main()
