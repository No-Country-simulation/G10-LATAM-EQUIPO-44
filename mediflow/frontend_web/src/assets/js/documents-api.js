/* Agregado por Edil: GET real para el historial. No envia documentos ni usa Gemini. */
(function (root) {
  "use strict";
  class DocumentsApiError extends Error {
    constructor(message, status) { super(message); this.name = "DocumentsApiError"; this.status = status; }
  }
  async function requestDocuments(options, id) {
    const individual = id !== undefined;
    const subject = individual ? "el documento" : "el historial";
    if (individual && (typeof id !== "string" || !id.trim() || id === "." || id === "..")) {
      throw new DocumentsApiError("El identificador del documento no es valido.");
    }
    let base;
    try {
      base = new URL(options.baseUrl || root.MEDIFLOW_API_BASE_URL || "http://127.0.0.1:8000");
      if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error();
    } catch (_) { throw new DocumentsApiError("La direccion de la API no es valida."); }
    const endpoint = new URL(base.toString().replace(/\/$/, "") + "/api/documents");
    if (individual) endpoint.pathname += "/" + encodeURIComponent(id);
    else endpoint.searchParams.set("limit", "500");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 20000);
    try {
      const response = await (options.fetchImpl || root.fetch)(endpoint, {
        method: "GET", headers: { Accept: "application/json" }, signal: controller.signal, redirect: "error"
      });
      if (!response.ok) {
        if (individual && response.status === 404) throw new DocumentsApiError("El documento no existe o ya no esta disponible.", 404);
        throw new DocumentsApiError("No se pudo consultar " + subject + ". HTTP " + response.status + ".", response.status);
      }
      let data;
      try { data = await response.json(); }
      catch (_) { throw new DocumentsApiError(individual ? "El servidor devolvio un documento invalido." : "El servidor devolvio un historial invalido."); }
      if (individual ? !validDocument(data, id) : !Array.isArray(data)) throw new DocumentsApiError(individual ? "El servidor devolvio un documento invalido." : "El servidor devolvio un historial invalido.");
      return data;
    } catch (error) {
      if (error instanceof DocumentsApiError) throw error;
      throw new DocumentsApiError(controller.signal.aborted
        ? "La consulta " + (individual ? "del documento" : "del historial") + " agoto el tiempo de espera."
        : "No se pudo conectar con el backend. Comprueba que este iniciado.");
    } finally { clearTimeout(timer); }
  }
  // Validación de la respuesta individual conforme a los campos públicos existentes.
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const nullableText = value => value === null || value === undefined || typeof value === "string";
  function validDocument(doc, id) {
    if (!object(doc) || doc.documento_id !== id || !["recibido", "procesado", "auditoria_humana"].includes(doc.status)) return false;
    const c = doc.clasificacion, d = doc.datos_extraidos, r = doc.decision_enrutamiento, o = doc.almacenamiento_oci;
    if (![c, d, r, o].every(object)) return false;
    if (typeof c.tipo_documento !== "string" || !nullableText(c.especialidad) || !["Rutina", "Urgente"].includes(c.nivel_prioridad) ||
        typeof c.score_confianza_clasificacion !== "number" || !Number.isFinite(c.score_confianza_clasificacion) ||
        c.score_confianza_clasificacion < 0 || c.score_confianza_clasificacion > 1) return false;
    if (!object(d.paciente) || !object(d.medico_solicitante) || !nullableText(d.paciente.nombre) ||
        !(d.paciente.edad == null || Number.isInteger(d.paciente.edad)) ||
        !nullableText(d.medico_solicitante.nombre) || !nullableText(d.medico_solicitante.matricula) ||
        ![d.estudio_realizado, d.diagnostico_principal, d.cie10_sugerido].every(nullableText) ||
        !Array.isArray(d.medicamentos_recetados) || !d.medicamentos_recetados.every(m => object(m) && typeof m.medicamento === "string" && nullableText(m.dosis))) return false;
    return typeof r.destino_principal === "string" && typeof r.requiere_auditoria_humana === "boolean" &&
      typeof r.justificacion_enrutamiento === "string" && [o.bucket, o.ruta_objeto, o.status_backup].every(v => typeof v === "string") &&
      (doc.notificacion_generada == null || object(doc.notificacion_generada));
  }
  const getDocuments = (options = {}) => requestDocuments(options);
  const getDocument = (id, options = {}) => requestDocuments(options, id === undefined ? null : id);
  const api = { getDocuments, getDocument, DocumentsApiError };
  root.MediFlowDocumentsApi = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
