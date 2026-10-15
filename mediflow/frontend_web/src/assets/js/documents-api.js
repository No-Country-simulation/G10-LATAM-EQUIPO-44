/* Agregado por Edil: GET real para el historial. No envia documentos ni usa Gemini. */
(function (root) {
  "use strict";
  class DocumentsApiError extends Error {
    constructor(message, status) { super(message); this.name = "DocumentsApiError"; this.status = status; }
  }
  async function getDocuments(options = {}) {
    let base;
    try {
      base = new URL(options.baseUrl || root.MEDIFLOW_API_BASE_URL || "http://127.0.0.1:8000");
      if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error();
    } catch (_) { throw new DocumentsApiError("La direccion de la API no es valida."); }
    const endpoint = new URL(base.toString().replace(/\/$/, "") + "/api/documents");
    endpoint.searchParams.set("limit", "500");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 20000);
    try {
      const response = await (options.fetchImpl || root.fetch)(endpoint, {
        headers: { Accept: "application/json" }, signal: controller.signal, redirect: "error"
      });
      if (!response.ok) throw new DocumentsApiError("No se pudo consultar el historial. HTTP " + response.status + ".", response.status);
      let data;
      try { data = await response.json(); }
      catch (_) { throw new DocumentsApiError("El servidor devolvio un historial invalido."); }
      if (!Array.isArray(data)) throw new DocumentsApiError("El servidor devolvio un historial invalido.");
      return data;
    } catch (error) {
      if (error instanceof DocumentsApiError) throw error;
      throw new DocumentsApiError(controller.signal.aborted
        ? "La consulta del historial agoto el tiempo de espera."
        : "No se pudo conectar con el backend. Comprueba que este iniciado.");
    } finally { clearTimeout(timer); }
  }
  const api = { getDocuments, DocumentsApiError };
  root.MediFlowDocumentsApi = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
