/* Agregado por Edil: interfaz interna, no un contrato HTTP de revisión inventado.
   Sin adaptador aprobado solo se realizan los GET de documentos existentes. */
(function (root) {
  "use strict";
  class ReviewApiError extends Error {
    constructor(message, status, uncertain = false) {
      super(message); this.name = "ReviewApiError"; this.status = status; this.uncertain = uncertain;
    }
  }
  const messages = {
    400: "La solicitud no es válida. Revisa los datos e inténtalo de nuevo.",
    401: "Se requiere una sesión válida. Inicia sesión con el mecanismo del backend.",
    403: "No tienes permiso para realizar esta operación.",
    404: "El documento o la revisión ya no están disponibles.",
    409: "El documento cambió o ya fue revisado. Actualiza antes de continuar.",
    422: "Los datos no cumplen el contrato del servidor. Revisa la observación."
  };
  function errorMessage(error) {
    const safe = error instanceof ReviewApiError ||
      (root.MediFlowDocumentsApi && error instanceof root.MediFlowDocumentsApi.DocumentsApiError);
    if (!safe) return "No se pudo completar la consulta. Comprueba la conexión e inténtalo de nuevo.";
    if (messages[error.status]) return messages[error.status];
    if (error.status >= 500) return "El servidor no pudo completar la operación. Conservamos los datos anteriores.";
    return error.message;
  }
  const text = value => typeof value === "string" && value.trim().length > 0;
  const validId = id => text(id) && ![".", ".."].includes(id);
  function validReview(entry, id) {
    return entry && entry.documentId === id && text(entry.reviewId) && text(entry.auditor) &&
      typeof entry.observation === "string" && ["approve", "reject"].includes(entry.decision) &&
      typeof entry.reviewedAt === "string" && /^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(entry.reviewedAt) &&
      Number.isFinite(Date.parse(entry.reviewedAt));
  }
  function createClient({ documentsApi = root.MediFlowDocumentsApi, approvedAdapter = null, requestOptions = {}, timeoutMs = 20000 } = {}) {
    // Un equipo debe implementar el adaptador tras aprobar rutas, JSON y autenticación.
    // No se habilita por parámetros de URL ni se incluye un adaptador simulado.
    const approved = approvedAdapter && approvedAdapter.approved === true && text(approvedAdapter.contractReference);
    const capabilities = Object.freeze({
      submit: !!(approved && typeof approvedAdapter.submitReview === "function" &&
        (!approvedAdapter.requiresDecisionApproval || approvedAdapter.decisionApproved === true)),
      history: !!(approved && typeof approvedAdapter.getReviewHistory === "function"),
      ...(approved && typeof approvedAdapter.listPending === "function" ? { pendingReviews: true } : {}),
      ...(approved && approvedAdapter.requiresReviewerId ? { requiresReviewerId: true } : {}),
      ...(approved && approvedAdapter.requiresRejectionObservation ? { requiresRejectionObservation: true } : {})
    });
    const inFlight = new Map(), completed = new Set(), unconfirmed = new Set();
    async function bounded(operation) {
      const controller = new AbortController(); let timer;
      try {
        return await Promise.race([
          Promise.resolve().then(() => operation(controller.signal)),
          new Promise((_, reject) => { timer = setTimeout(() => {
            controller.abort(); reject(new ReviewApiError("La operación agotó el tiempo de espera.", undefined, true));
          }, timeoutMs); })
        ]);
      } finally { clearTimeout(timer); }
    }
    async function listPending() {
      const docs = approved && typeof approvedAdapter.listPending === "function"
        ? await bounded(signal => approvedAdapter.listPending({ signal }))
        : await documentsApi.getDocuments({ ...requestOptions, status: "auditoria_humana" });
      if (!Array.isArray(docs) || docs.some(doc => !validId(doc?.documento_id) || !documentsApi.isValidDocument(doc, doc.documento_id))) {
        throw new ReviewApiError("La bandeja no cumple el contrato de documentos. No se muestran resultados parciales.");
      }
      const seen = new Set();
      return docs.filter(doc => {
        if (doc.status !== "auditoria_humana" || completed.has(doc.documento_id) || seen.has(doc.documento_id)) return false;
        seen.add(doc.documento_id); return true;
      });
    }
    async function getDocument(id) {
      if (!validId(id)) throw new ReviewApiError("El identificador del documento no es válido.");
      return documentsApi.getDocument(id, requestOptions);
    }
    async function getReviewHistory(id) {
      if (!capabilities.history) throw new ReviewApiError("Historial de revisión pendiente de contrato y API aprobados.");
      if (!validId(id)) throw new ReviewApiError("El identificador del documento no es válido.");
      const result = await bounded(signal => approvedAdapter.getReviewHistory(id, { signal }));
      if (!result || result.documentId !== id || !Array.isArray(result.entries) || result.entries.some(e => !validReview(e, id))) {
        throw new ReviewApiError("El historial persistido no cumple la interfaz del adaptador aprobado.");
      }
      return result.entries;
    }
    function submitReview(input) {
      if (!capabilities.submit) return Promise.reject(new ReviewApiError("Aprobación y rechazo pendientes de contrato y API aprobados."));
      if (!input || !validId(input.documentId) || !["approve", "reject"].includes(input.decision) || typeof input.observation !== "string") {
        return Promise.reject(new ReviewApiError("La decisión o su observación no son válidas.", 400));
      }
      // Agregado por Edil: respetar los datos obligatorios del contrato integrado.
      if ((capabilities.requiresReviewerId && !text(input.reviewerId)) ||
          (capabilities.requiresRejectionObservation && input.decision === "reject" && !input.observation.trim())) {
        return Promise.reject(new ReviewApiError("Completa el auditor y la observación obligatoria para rechazo.", 422));
      }
      if (completed.has(input.documentId)) return Promise.reject(new ReviewApiError(messages[409], 409));
      if (unconfirmed.has(input.documentId)) return Promise.reject(new ReviewApiError("Hay un envío sin confirmación. No repitas la decisión; verifica su persistencia con el equipo.", undefined, true));
      // Mismo documento: una sola operación, incluso si el segundo clic cambia la decisión.
      if (inFlight.has(input.documentId)) return inFlight.get(input.documentId);
      const task = bounded(signal => approvedAdapter.submitReview({ ...input, observation: input.observation.trim() }, { signal }))
        .then(receipt => {
          if (receipt?.persisted !== true || !validReview(receipt, input.documentId) || receipt.decision !== input.decision || receipt.observation !== input.observation.trim()) {
            throw new ReviewApiError("No se pudo verificar la persistencia. No repitas el envío; consulta el historial.", undefined, true);
          }
          completed.add(input.documentId); return receipt;
        }).catch(error => {
          if (error instanceof ReviewApiError && error.status && error.status < 500) throw error;
          const safeStatus = error instanceof ReviewApiError ? error.status : undefined;
          unconfirmed.add(input.documentId);
          throw new ReviewApiError("No sabemos si el servidor registró la decisión. No repitas el envío; verifica el historial con el equipo.", safeStatus, true);
        }).finally(() => inFlight.delete(input.documentId));
      inFlight.set(input.documentId, task); return task;
    }
    return { capabilities, listPending, getDocument, getReviewHistory, submitReview };
  }
  const api = { createClient, ReviewApiError, errorMessage };
  root.MediFlowReviewsApi = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
