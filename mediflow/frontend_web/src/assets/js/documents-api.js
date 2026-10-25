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
    else {
      endpoint.searchParams.set("limit", "500");
      // Agregado por Edil: reutilizar el filtro que ya admite GET /api/documents.
      if (options.status !== undefined) {
        if (!["recibido", "procesado", "auditoria_humana"].includes(options.status)) throw new DocumentsApiError("El estado solicitado no es valido.");
        endpoint.searchParams.set("status", options.status);
      }
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 20000);
    try {
      const response = await (options.fetchImpl || root.fetch)(endpoint, {
        // Agregado por Edil: conservar la sesión también al recuperar una carga entre puertos HTTPS.
        method: "GET", credentials: "include", headers: { Accept: "application/json" }, signal: controller.signal, redirect: "error"
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
  // Agregado por Edil: navegación al original protegido, sin enlaces OCI ni selección local.
  function originalUrl(id, options = {}) {
    if (!/^[A-Za-z0-9_-]{1,128}$/.test(id)) throw new DocumentsApiError('Identificador inválido.');
    try {
      const base = new URL(options.baseUrl || root.MEDIFLOW_API_BASE_URL);
      if (!['https:', 'http:'].includes(base.protocol) || base.username || base.password || base.search || base.hash ||
          !['/', '/api', '/api/'].includes(base.pathname) ||
          (base.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(base.hostname))) throw Error();
      return new URL('/api/documents/' + encodeURIComponent(id) + '/original', base.origin).href;
    } catch (_) { throw new DocumentsApiError('La dirección de la API no es válida.'); }
  }
  // Agregado por Edil: leer el original autenticado; no depender del nombre
  // Content-Disposition, que no está expuesto por CORS ni hace falta al visor.
  async function getOriginal(id, options = {}) {
    const url = originalUrl(id, options), abort = new AbortController();
    const cancel = () => abort.abort();
    options.signal?.addEventListener('abort', cancel, { once: true });
    if (options.signal?.aborted) abort.abort();
    const timer = setTimeout(cancel, options.timeoutMs || 20000);
    try {
      const response = await (options.fetchImpl || root.fetch)(url, {
        method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'error', signal: abort.signal,
        headers: { Accept: 'image/jpeg, image/png, application/pdf, text/plain' },
      });
      if (!response.ok) {
        const messages = { 401: 'Inicia sesión para ver el original.', 403: 'No tienes permiso para ver este original.', 404: 'El documento original no está disponible.' };
        throw new DocumentsApiError(messages[response.status] || 'No se pudo recuperar el original de OCI.', response.status);
      }
      const mime = (response.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
      if (response.status !== 200 || !['image/jpeg', 'image/png', 'application/pdf', 'text/plain'].includes(mime)) {
        throw new DocumentsApiError('El original tiene un formato no permitido para el visor.');
      }
      const blob = await response.blob();
      if (!blob.size || blob.size > 10 * 1024 * 1024) throw new DocumentsApiError('El original está vacío o supera 10 MiB.');
      return { blob: blob.slice(0, blob.size, mime), mime };
    } catch (error) {
      if (error instanceof DocumentsApiError) throw error;
      throw new DocumentsApiError(abort.signal.aborted ? 'La consulta del original agotó el tiempo de espera o se canceló.' : 'No se pudo conectar para recuperar el original.');
    } finally { clearTimeout(timer); options.signal?.removeEventListener('abort', cancel); }
  }
  // Agregado por Edil: visor efímero compartido. Nunca interpreta HTML ni
  // persiste bytes. Al cambiar/cerrar revoca URL y descarta respuestas tardías.
  function createFileViewer(doc, prefix, { onError = () => {} } = {}) {
    const $ = suffix => doc.querySelector('#' + prefix + suffix);
    let url = null, version = 0, pending = null;
    function clear() {
      version++; if (pending) { pending(false); pending = null; }
      for (const name of ['Image', 'Pdf', 'Text', 'Link']) {
        const element = $(name); element.hidden = true;
        element.onload = element.onerror = null;
        element.removeAttribute?.(name === 'Link' ? 'href' : 'src');
      }
      $('Text').textContent = '';
      $('Link').onclick = null;
      if (url) root.URL.revokeObjectURL(url);
      url = null;
    }
    async function show({ blob, mime }) {
      clear(); const current = version;
      if (!blob?.size || !['image/jpeg', 'image/png', 'application/pdf', 'text/plain'].includes(mime)) throw new DocumentsApiError('No hay un archivo compatible para visualizar.');
      url = root.URL.createObjectURL(blob);
      $('Link').href = url; $('Link').hidden = false;
      if (mime === 'text/plain') {
        const text = await blob.slice(0, 65536).text();
        if (current !== version) return false;
        $('Text').textContent = text + (blob.size > 65536 ? '\n[Vista limitada a 64 KiB; abre el original para leerlo completo.]' : '');
        $('Text').hidden = false; return true;
      }
      const element = $(mime === 'application/pdf' ? 'Pdf' : 'Image');
      return new Promise(resolve => {
        pending = resolve;
        element.onload = () => { if (current === version) { pending = null; resolve(true); } };
        // Algunos navegadores no muestran PDF en un frame sandboxed. El
        // enlace abre los mismos bytes ya autorizados, sin otra petición OCI.
        if (mime === 'application/pdf') $('Link').onclick = element.onload;
        element.onerror = () => {
          if (current !== version) return;
          clear(); onError(); resolve(false);
        };
        element.src = url; element.hidden = false;
      });
    }
    clear(); return { show, clear };
  }
  const api = { getDocuments, getDocument, getOriginal, createFileViewer, originalUrl, DocumentsApiError, isValidDocument: validDocument };
  root.MediFlowDocumentsApi = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
