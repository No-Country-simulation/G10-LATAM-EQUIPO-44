/* Agregado por Edil: multipart real; la URL procede de api-config.js, sin secretos. */
(function (root) {
  "use strict";
  const documents = root.MediFlowDocumentsApi || (typeof require === "function" ? require("./documents-api.js") : null);
  class TriageApiError extends Error {
    constructor(message, { status, documentId = null, uncertain = false } = {}) {
      super(message); this.name = "TriageApiError";
      Object.assign(this, { status, documentId, uncertain });
    }
  }
  function validateFile(file) {
    if (!file || !/\.(pdf|jpe?g|png|txt)$/i.test(file.name || "")) throw new TriageApiError("Selecciona un archivo PDF, JPG, PNG o TXT.");
    if (!Number.isFinite(file.size) || file.size <= 0) throw new TriageApiError("El archivo está vacío.");
    if (file.size > 10 * 1024 * 1024) throw new TriageApiError("El archivo supera el límite de 10 MiB.");
  }
  function createClient({ baseUrl, fetchImpl, timeoutMs = 180000 } = {}) {
    function endpoint() {
      try {
        const url = new URL(baseUrl || root.MEDIFLOW_API_BASE_URL);
        if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash ||
            !['/', '/api', '/api/'].includes(url.pathname) ||
            (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) throw Error();
        return new URL('/api/triage', url.origin);
      } catch (_) { throw new TriageApiError("La dirección del backend no está configurada correctamente."); }
    }
    return { async upload(file, consent) {
      validateFile(file);
      if (consent !== true) throw new TriageApiError("Debes autorizar el envío y análisis del documento.");
      const url = endpoint(), body = new FormData();
      body.append('file', file, file.name); body.append('analyze', 'true');
      const abort = new AbortController(), timer = setTimeout(() => abort.abort(), timeoutMs);
      try {
        const response = await (fetchImpl || root.fetch)(url, {
          method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error',
          headers: { Accept: 'application/json' }, body, signal: abort.signal,
        }); // El navegador añade el boundary multipart; no fijar Content-Type.
        const rawId = response.headers.get('X-Document-ID');
        const documentId = /^DOC-CLIN-[A-Z0-9]+$/.test(rawId || '') ? rawId : null;
        if (!response.ok) {
          const messages = { 400: 'El archivo enviado no es válido.', 401: 'Inicia sesión para continuar.',
            403: 'No tienes permiso para esta operación.', 413: 'El archivo supera 10 MiB.',
            415: 'El formato no está permitido.', 422: 'El documento no puede analizarse en su formato actual.',
            429: 'El servicio de análisis alcanzó su cuota. El documento podría estar recibido.',
            502: 'El proveedor de análisis no pudo completar la solicitud.',
            503: 'El análisis no está disponible o no está configurado.', 504: 'El análisis agotó el tiempo de espera.' };
          throw new TriageApiError(messages[response.status] || 'El servidor no pudo completar el procesamiento.', {
            status: response.status, documentId, uncertain: !!documentId || response.status >= 500 || response.status === 429,
          });
        }
        let data;
        try { data = await response.json(); }
        catch (_) { throw new TriageApiError('El servidor devolvió una respuesta ilegible. Consulta el historial antes de reenviar.', { uncertain: true, documentId }); }
        if (response.status !== 201 || !documents.isValidDocument(data, data?.documento_id) ||
            typeof data.documento_id !== 'string' || !data.documento_id.trim()) {
          throw new TriageApiError('La respuesta no cumple el contrato. Comprueba el historial antes de reenviar.', { uncertain: true, documentId });
        }
        return data;
      } catch (error) {
        if (error instanceof TriageApiError) throw error;
        throw new TriageApiError(abort.signal.aborted ? 'Se agotó el tiempo de espera. La recepción no está confirmada.' :
          'No se pudo confirmar la recepción. Comprueba la conexión y el historial antes de reenviar.', { uncertain: true });
      } finally { clearTimeout(timer); }
    } };
  }
  const api = { createClient, validateFile, TriageApiError };
  root.MediFlowTriageApi = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
