"""Cliente de inferencia Cohere para la extraccion clinica controlada."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import pymupdf as fitz
import requests

from app.core.config import settings


class LLMError(RuntimeError):
    """Error controlado durante la llamada o validacion del LLM."""


class LLMConfigurationError(LLMError):
    """La configuracion del proveedor no esta disponible."""


class LLMInputError(LLMError):
    """El formato de entrada no esta soportado por el proveedor actual."""


class LLMResponseError(LLMError):
    """La respuesta del proveedor no tiene el JSON esperado."""


@dataclass(frozen=True)
class CohereClient:
    api_key: str
    model: str
    vision_model: str = "command-a-vision-07-2025"
    endpoint: str = "https://api.cohere.com/v2/chat"
    timeout_seconds: float = 30.0

    @classmethod
    def from_settings(cls) -> "CohereClient":
        if not settings.COHERE_API_KEY:
            raise LLMConfigurationError(
                "COHERE_API_KEY no esta configurada en el entorno."
            )
        if settings.LLM_PROVIDER.lower() != "cohere":
            raise LLMConfigurationError(
                f"Proveedor LLM no soportado: {settings.LLM_PROVIDER}."
            )
        return cls(
            api_key=settings.COHERE_API_KEY,
            model=settings.COHERE_MODEL,
            vision_model=settings.COHERE_VISION_MODEL,
            endpoint=settings.COHERE_API_URL,
            timeout_seconds=settings.COHERE_TIMEOUT_SECONDS,
        )

    def extract_text(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        if extension != ".txt":
            raise LLMInputError(
                "La extraccion de texto solo admite documentos TXT."
            )
        try:
            document_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise LLMInputError("El documento TXT no esta codificado en UTF-8.") from error
        return self._extract_text_content(document_text)

    def extract_document(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Extrae texto o contenido visual segun el formato recibido."""
        extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        if extension == ".txt":
            return self.extract_text(file_bytes, filename)
        if extension == ".pdf":
            return self._extract_pdf(file_bytes)
        if extension in {".jpg", ".jpeg", ".png"}:
            mime_type = "image/png" if extension == ".png" else "image/jpeg"
            return self._extract_images([(file_bytes, mime_type)])
        raise LLMInputError(f"Formato no soportado por el extractor: {extension}")

    def _extract_text_content(self, document_text: str) -> dict[str, Any]:
        prompt = _build_prompt(document_text)
        response_data = self._request(
            model=self.model,
            content=prompt,
        )
        return _parse_extraction(response_data)

    def _extract_pdf(self, file_bytes: bytes) -> dict[str, Any]:
        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
        except (fitz.FileDataError, ValueError) as error:
            raise LLMInputError("El PDF no se puede leer.") from error

        text = "\n".join(page.get_text("text") for page in document).strip()
        if text:
            return self._extract_text_content(text)

        # PDF escaneado: limita paginas para controlar tamano y costo de inferencia.
        images = []
        for page in document[:5]:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            images.append((pixmap.tobytes("png"), "image/png"))
        if not images:
            raise LLMInputError("El PDF no contiene paginas procesables.")
        return self._extract_images(images)

    def _extract_images(self, images: list[tuple[bytes, str]]) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": _build_prompt(
            "Analiza las imagenes adjuntas del documento clinico."
        )}]
        import base64

        for image_bytes, mime_type in images:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
            })
        return _parse_extraction(self._request(model=self.vision_model, content=content))

    def _request(self, model: str, content: str | list[dict[str, Any]]) -> Any:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as error:
            raise LLMError("No fue posible comunicarse con Cohere.") from error
        except ValueError as error:
            raise LLMResponseError("Cohere devolvio una respuesta no JSON.") from error

        return response_data


def _parse_extraction(response_data: Any) -> dict[str, Any]:
    text = _response_text(response_data)
    try:
        result = json.loads(text)
    except json.JSONDecodeError as error:
        raise LLMResponseError("Cohere no devolvio JSON clinico valido.") from error
    if not isinstance(result, dict):
        raise LLMResponseError("La salida de Cohere debe ser un objeto JSON.")
    return _normalize_extraction(result)


def _response_text(response_data: Any) -> str:
    try:
        content = response_data["message"]["content"]
        if isinstance(content, list):
            text = next(item["text"] for item in content if isinstance(item, dict) and "text" in item)
            return str(text)
        return str(content)
    except (KeyError, IndexError, StopIteration, TypeError) as error:
        raise LLMResponseError("La respuesta de Cohere no contiene message.content.") from error


def _build_prompt(document_text: str) -> str:
    return f"""Extrae datos clinicos del siguiente documento y responde SOLO con JSON valido.

El JSON debe contener exactamente estas claves de nivel superior:
- clasificacion: tipo_documento, especialidad, nivel_prioridad, score_confianza_clasificacion
- datos_extraidos: paciente, medico_solicitante, estudio_realizado, diagnostico_principal, cie10_sugerido

Devuelve exactamente esta forma. paciente y medico_solicitante deben ser objetos, no textos:
{{
    "clasificacion": {{
        "tipo_documento": "No identificado",
        "especialidad": "No identificada",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.0
    }},
    "datos_extraidos": {{
        "paciente": {{"nombre": null, "edad": null}},
        "medico_solicitante": {{"nombre": null, "matricula": null}},
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null
    }}
}}
Usa null en datos opcionales cuando no aparezcan. tipo_documento y especialidad siempre deben ser texto.
score_confianza_clasificacion debe estar entre 0 y 1.
No inventes datos clinicos.

DOCUMENTO:
{document_text}
"""


def _normalize_extraction(result: dict[str, Any]) -> dict[str, Any]:
    classification = result.get("clasificacion")
    extracted = result.get("datos_extraidos")
    if not isinstance(classification, dict) or not isinstance(extracted, dict):
        raise LLMResponseError(
            "La respuesta de Cohere debe contener clasificacion y datos_extraidos como objetos."
        )

    classification = dict(classification)
    classification["tipo_documento"] = classification.get("tipo_documento") or "No identificado"
    classification["especialidad"] = classification.get("especialidad") or "No identificada"

    extracted = dict(extracted)
    patient = extracted.get("paciente")
    if isinstance(patient, str):
        extracted["paciente"] = {"nombre": patient, "edad": None}
    elif patient is None:
        extracted["paciente"] = {"nombre": None, "edad": None}

    doctor = extracted.get("medico_solicitante")
    if isinstance(doctor, str):
        extracted["medico_solicitante"] = {"nombre": doctor, "matricula": None}
    elif doctor is None:
        extracted["medico_solicitante"] = {"nombre": None, "matricula": None}

    return {"clasificacion": classification, "datos_extraidos": extracted}
