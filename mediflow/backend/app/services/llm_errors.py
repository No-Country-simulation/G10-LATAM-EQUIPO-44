# Agregado por Edil: completa el módulo LLM pendiente; conserva las entregas previas.
"""Errores públicos sanitizados; no contienen documentos ni mensajes del proveedor."""

import re


class LLMError(RuntimeError):
    """Fallo controlado del módulo LLM."""

    # Agregado por Edil: diagnóstico interno acotado, sin guardar el error original.
    def __init__(self, message, *, provider_http_status=None, original_exception_class=None):
        super().__init__(message)
        self.provider_http_status = (
            provider_http_status
            if type(provider_http_status) is int and 100 <= provider_http_status <= 599
            else None
        )
        self.original_exception_class = (
            original_exception_class
            if isinstance(original_exception_class, str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,99}", original_exception_class)
            else None
        )

    @classmethod
    def from_exception(cls, message, original, *, provider_http_status=None):
        return cls(message, provider_http_status=provider_http_status,
                   original_exception_class=type(original).__name__)


class LLMConfigurationError(LLMError):
    pass


class LLMInputError(LLMError):
    pass


class LLMResponseError(LLMError):
    # Agregado por Edil: catálogo cerrado; nunca usar mensajes ni datos de IA
    # como etapa/motivo. Estos atributos son internos, no campos del contrato.
    _DIAGNOSTICS = {
        "generation": {"max_tokens", "safety", "recitation", "blocklist",
                       "prohibited_content", "spii", "non_stop_finish"},
        "response_read": {"text_unavailable"},
        "clinical_json": {"empty_or_oversized", "invalid_json", "invalid_root"},
        "clinical_schema": {"missing_fields", "unexpected_fields", "schema_mismatch"},
        "routing_consistency": {"review_destination_mismatch", "illegible_dose_without_review"},
        "source_evidence": {"empty_or_oversized", "invalid_json", "invalid_envelope", "invalid_source_text"},
        "response_assembly": {"schema_mismatch"},
        "orchestration_input": {"invalid_input", "schema_mismatch", "unprocessed_document"},
        "orchestration_rules": {"evaluation_failed"},
        "orchestration_output": {"invalid_output", "schema_mismatch"},
    }

    def __init__(self, message, *, stage=None, reason=None, **metadata):
        super().__init__(message, **metadata)
        valid = (isinstance(stage, str) and isinstance(reason, str)
                 and reason in self._DIAGNOSTICS.get(stage, ()))
        self.stage = stage if valid else None
        self.reason = reason if valid else None


class LLMTimeoutError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


class LLMQuotaError(LLMError):
    pass


class LLMNetworkError(LLMError):
    pass


class LLMUnavailableError(LLMError):
    pass


class LLMRequestError(LLMError):
    pass


class DocumentExtractionError(LLMInputError):
    pass


class OCRRequiredError(DocumentExtractionError):
    pass
