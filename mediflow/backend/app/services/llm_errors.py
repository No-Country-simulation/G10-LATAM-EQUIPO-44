# Agregado por Edil: completa el módulo LLM pendiente; conserva las entregas previas.
"""Errores públicos sanitizados; no contienen documentos ni mensajes del proveedor."""


class LLMError(RuntimeError):
    """Fallo controlado del módulo LLM."""


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
