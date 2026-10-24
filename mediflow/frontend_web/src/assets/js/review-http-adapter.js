/* Agregado por Edil: conectar el panel preparado al contrato de Eliana y a
   los tres endpoints entregados por Drazen, con persistencia OCI de Brando.
   No contiene credenciales ni modifica el análisis o la prioridad. */
(function (root) {
  "use strict";
  const recordFields = ["documento_id", "review_id", "review_status", "reviewer_id", "observacion", "reviewed_at"];
  const validId = id => typeof id === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(id);
  function createAdapter({ baseUrl, fetchImpl, timeoutMs = 20000, decisionApproved = false, authenticatedUser = null } = {}) {
    const ErrorType = root.MediFlowReviewsApi.ReviewApiError;
    // Agregado por Edil: la identidad se recibe del servidor; un nombre escrito
    // en el formulario no acredita a un auditor. El backend vuelve a validarla.
    const principal = typeof authenticatedUser?.login === "string" && authenticatedUser.login.trim()
      ? Object.freeze({ login: authenticatedUser.login.trim(), canReview: authenticatedUser.canReview === true }) : null;
    function normalize(record, documentId) {
      if (!record || typeof record !== "object" || Array.isArray(record) || Object.keys(record).length !== 6 ||
        !recordFields.every(key => Object.prototype.hasOwnProperty.call(record, key)) || record.documento_id !== documentId ||
        !validId(documentId) || !["aprobado", "rechazado"].includes(record.review_status) ||
        typeof record.reviewer_id !== "string" || !record.reviewer_id.trim() ||
        !(record.observacion === null || typeof record.observacion === "string") ||
        (record.review_status === "rechazado" && !(record.observacion || "").trim()) ||
        typeof record.review_id !== "string" || !/^(?:REV-[A-Za-z0-9_-]{1,64}|[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i.test(record.review_id) ||
        typeof record.reviewed_at !== "string" || !/^\d{4}-\d\d-\d\dT.*Z$/.test(record.reviewed_at) || !Number.isFinite(Date.parse(record.reviewed_at))) {
        throw new ErrorType("El registro de revisión no cumple el contrato de seis campos.");
      }
      return { documentId, reviewId: record.review_id, decision: record.review_status === "aprobado" ? "approve" : "reject",
        auditor: record.reviewer_id, observation: record.observacion ?? "", reviewedAt: record.reviewed_at };
    }
    async function request(path, { method = "GET", body, signal } = {}) {
      let base;
      try {
        base = new URL(baseUrl || root.MEDIFLOW_API_BASE_URL || "http://127.0.0.1:8000");
        if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw Error();
      } catch (_) { throw new ErrorType("La dirección de la API no es válida.", 400); }
      const controller = new AbortController();
      const abort = () => controller.abort();
      if (signal?.aborted) abort();
      signal?.addEventListener("abort", abort, { once: true });
      const timer = setTimeout(abort, timeoutMs);
      try {
        const response = await (fetchImpl || root.fetch)(base.toString().replace(/\/$/, "") + path, {
          method, headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
          ...(body ? { body: JSON.stringify(body) } : {}), signal: controller.signal, redirect: "error"
        });
        if (!response.ok) throw new ErrorType("La API no pudo completar la operación de revisión.", response.status);
        if (response.status !== 200) throw new ErrorType("La API devolvió una confirmación inesperada.", undefined, method === "POST");
        try { return await response.json(); }
        catch (_) { throw new ErrorType("La API devolvió un JSON de revisión inválido.", undefined, method === "POST"); }
      } catch (error) {
        if (error instanceof ErrorType) throw error;
        throw new ErrorType(controller.signal.aborted ? "La operación de revisión agotó el tiempo de espera." : "No se pudo conectar con la API de revisión.", undefined, method === "POST");
      } finally { clearTimeout(timer); signal?.removeEventListener("abort", abort); }
    }
    return {
      approved: true,
      contractReference: "docs/S4-Eliana.md; API d286de4; persistencia 5e8f503",
      // Agregado por Edil: integrar código no sustituye la aprobación del equipo.
      // Lecturas disponibles; POST solo tras habilitación explícita del contrato.
      requiresDecisionApproval: true,
      decisionApproved: decisionApproved === true,
      requiresReviewerId: true,
      requiresRejectionObservation: true,
      async listPending({ signal } = {}) { return request("/api/reviews/pending", { signal }); },
      async submitReview(input, { signal } = {}) {
        if (decisionApproved !== true) throw new ErrorType("El contrato de decisión aún no está habilitado por el equipo.", 403);
        if (!principal) throw new ErrorType("Se requiere una identidad autenticada para registrar una revisión.", 401);
        if (!principal.canReview) throw new ErrorType("Tu identidad no tiene permiso de auditor.", 403);
        if (!validId(input.documentId) || !["approve", "reject"].includes(input.decision) ||
          typeof input.reviewerId !== "string" || !input.reviewerId.trim() || typeof input.observation !== "string" ||
          (input.decision === "reject" && !input.observation.trim())) {
          throw new ErrorType("Revisa el identificador del auditor y la observación obligatoria para rechazo.", 422);
        }
        if (input.reviewerId.trim() !== principal.login) throw new ErrorType("El auditor debe coincidir con la identidad autenticada.", 403);
        const payload = { decision: input.decision === "approve" ? "aprobado" : "rechazado", reviewer_id: principal.login,
          observacion: input.observation.trim() || null, expected_review_status: "pendiente" };
        const record = await request("/api/documents/" + encodeURIComponent(input.documentId) + "/review", { method: "POST", body: payload, signal });
        let normalized;
        try { normalized = normalize(record, input.documentId); }
        catch (_) { throw new ErrorType("No se pudo verificar el recibo persistido. No repitas el envío.", undefined, true); }
        if (record.review_status !== payload.decision || record.reviewer_id !== payload.reviewer_id || normalized.observation !== (payload.observacion ?? "")) {
          throw new ErrorType("El recibo no coincide con la decisión enviada. No repitas el envío.", undefined, true);
        }
        // Campo solo de la interfaz interna: la API devuelve los seis campos;
        // HTTP 200 y un registro válido son su confirmación de persistencia.
        return { ...normalized, persisted: true };
      },
      async getReviewHistory(documentId, { signal } = {}) {
        if (!validId(documentId)) throw new ErrorType("El identificador del documento no es válido.", 400);
        const rows = await request("/api/documents/" + encodeURIComponent(documentId) + "/review-history", { signal });
        if (!Array.isArray(rows)) throw new ErrorType("El historial de revisión no es una lista válida.");
        return { documentId, entries: rows.map(row => normalize(row, documentId)) };
      }
    };
  }
  root.MediFlowReviewHttpAdapter = { createAdapter };
  if (typeof window !== "undefined" && !root.MediFlowApprovedReviewAdapter) {
    root.MediFlowApprovedReviewAdapter = createAdapter({ decisionApproved: root.MEDIFLOW_REVIEW_CONTRACT_APPROVED === true,
      authenticatedUser: root.MEDIFLOW_AUTHENTICATED_USER });
  }
  if (typeof module !== "undefined") module.exports = { createAdapter };
})(typeof window !== "undefined" ? window : globalThis);
