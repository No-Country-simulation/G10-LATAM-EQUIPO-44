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
    pass


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
