/* Agregado por Edil: vista conectada sobre el diseño existente; ningún mock
   se carga desde esta pantalla. Las mutaciones necesitan adaptador aprobado. */
(function (root) {
  "use strict";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const available = value => value === null || value === undefined || value === "" ? "No disponible" : String(value);
  const confidence = doc => `${Math.round(doc.clasificacion.score_confianza_clasificacion * 100)} %`;
  const field = (label, value) => `<div><dt>${esc(label)}</dt><dd>${esc(available(value))}</dd></div>`;
  function mount(doc, options = {}) {
    const $ = selector => doc.querySelector(selector);
    const dialog = $("#auditDetail"), confirmation = $("#reviewConfirmation");
    let storage = null, focusBeforeDetail = null, controller, logoutTask = null, logoutComplete = false;
    try { storage = root.sessionStorage; } catch (_) { /* Se conserva lectura; no se habilita envío sin protección. */ }
    const client = options.client || root.MediFlowReviewsApi.createClient({ approvedAdapter: root.MediFlowApprovedReviewAdapter });
    const authClient = options.authClient || root.MediFlowAuthApi?.createClient();
    const logoutDialog = $("#logoutConfirmation");
    const message = error => root.MediFlowReviewsApi.errorMessage(error);
    function updateDecisionButtons() {
      $("#approveReview").disabled = !controller.canSubmit("approve");
      $("#rejectReview").disabled = !controller.canSubmit("reject");
    }
    function setText(id, value) { $(id).textContent = value; }
    function render(state) {
      const loading = state.listStatus === "loading";
      // Agregado por Edil: sesión de aplicación propia. La conexión de red no
      // convierte a sus integrantes en usuarios ni auditores de MediFlow.
      const user = state.authenticatedUser;
      // Agregado por Edil: sin permiso verificado no se muestran acciones de decisión.
      $("#approveReview").hidden = $("#rejectReview").hidden = user?.canReview !== true;
      setText("#authSessionUser", user ? "Sesión: " + user.login : "Sin sesión de MediFlow");
      $("#authLoginLink").hidden = !!user && state.submitError?.status !== 401;
      $("#authLogout").hidden = !user;
      $("#authLogout").disabled = state.submitStatus === "sending" || !!logoutTask || logoutComplete || !authClient;
      setText("#authSessionStatus", state.submitError?.status === 401 ? "La sesión ya no es válida. Inicia sesión de nuevo; se conserva el resultado y las observaciones."
        : options.sessionError ? "No se pudo verificar la sesión. Las decisiones están deshabilitadas; vuelve a cargar para consultar de nuevo." : "");
      $("#refreshAudit").disabled = loading || state.submitStatus === "sending";
      $("#auditList").setAttribute("aria-busy", String(loading));
      setText("#auditLoadStatus", loading ? "Consultando pendientes…" : state.listError
        ? message(state.listError) + (state.rows.length ? " Se conserva la última bandeja recibida; puede estar desactualizada." : "")
        : state.listStatus === "ready" ? (state.capabilities.pendingReviews
          ? "Bandeja de revisiones pendientes recibida del backend. Actualiza para consultar cambios."
          : "Bandeja recibida del backend. Hasta 500 documentos; no es un historial de decisiones humanas.") : "Preparando consulta…");
      $("#auditLoadStatus").dataset.state = state.listStatus;
      setText("#auditConnection", loading ? "Consultando" : state.listError ? "Consulta fallida" : "Backend conectado");
      $("#auditConnection").dataset.state = state.listStatus;
      setText("#auditContract", state.capabilities.submit
        ? "Decisiones mediante adaptador de contrato aprobado. El análisis original y la prioridad se conservan."
        : state.capabilities.pendingReviews ? "API de revisión integrada para consulta. Las decisiones requieren aprobación y habilitación explícita del contrato."
        : "Lectura conectada. Aprobar y rechazar estarán disponibles cuando el equipo apruebe e implemente la API de revisión.");
      const query = $("#q").value.trim().toLocaleLowerCase("es");
      const priority = $("#auditPriority").value;
      const rows = state.rows.filter(d => [d.documento_id, d.clasificacion.tipo_documento].join(" ").toLocaleLowerCase("es").includes(query) &&
        (priority === "all" || d.clasificacion.nivel_prioridad === priority));
      setText("#navAuditTotal", state.listStatus === "idle" || (loading && !state.rows.length) ? "—" : String(state.rows.length));
      setText("#auditCount", `${rows.length} documento${rows.length === 1 ? "" : "s"} en esta bandeja`);
      $("#auditList").innerHTML = rows.map(d => `<article class="audit-live-card">
        <div class="audit-live-card__head"><span class="audit-id">${esc(d.documento_id)}</span><span class="audit-priority ${d.clasificacion.nivel_prioridad === "Urgente" ? "is-urgent" : ""}">${esc(d.clasificacion.nivel_prioridad)}</span></div>
        <h2>${esc(d.clasificacion.tipo_documento)}</h2><dl class="audit-facts">${field("Estado del análisis", d.status)}${field("Confianza de clasificación", confidence(d))}</dl>
        <p class="audit-muted">${esc(d.decision_enrutamiento.justificacion_enrutamiento || "Motivo no disponible en el análisis.")}</p>
        <button type="button" class="btn btn--primary" data-open-document="${esc(d.documento_id)}" ${state.submitStatus === "sending" ? "disabled" : ""}>Abrir detalle y revisar</button></article>`).join("");
      $("#auditEmpty").hidden = loading || state.listStatus !== "ready" || rows.length > 0;
      setText("#auditEmpty", query || priority !== "all" ? "No hay documentos que coincidan con los filtros." : "No hay documentos pendientes en la respuesta recibida.");
      if (!state.selectedId) return;
      const sending = state.submitStatus === "sending";
      dialog.setAttribute("aria-busy", String(state.detailStatus === "loading" || sending));
      setText("#auditDetailStatus", state.detailStatus === "loading" ? "Consultando análisis por ID…" : state.detailError
        ? message(state.detailError) + (state.document ? " Se conserva el resultado anterior; vuelve a consultar antes de decidir." : "")
        : state.detailStatus === "stale" ? "El documento cambió. Consulta el detalle de nuevo antes de decidir."
        : "Análisis recibido por GET individual.");
      setText("#auditDetailTitle", "Documento " + state.selectedId);
      $("#auditRetryDetail").disabled = state.detailStatus === "loading" || sending;
      $("#auditClose").disabled = sending;
      const d = state.document;
      $("#auditDetailContent").hidden = !d;
      if (d) {
        const data = d.datos_extraidos;
        $("#auditSummary").innerHTML = field("Tipo documental", d.clasificacion.tipo_documento) + field("Estado del análisis", d.status) +
          field("Cargado por", d.cargado_por) +
          field("Prioridad del backend", d.clasificacion.nivel_prioridad) + field("Confianza de clasificación", confidence(d)) +
          field("Requiere revisión humana", d.decision_enrutamiento.requiere_auditoria_humana ? "Sí" : "No") +
          field("Destino del análisis", d.decision_enrutamiento.destino_principal);
        $("#auditUrgent").hidden = d.clasificacion.nivel_prioridad !== "Urgente";
        setText("#auditReason", d.decision_enrutamiento.justificacion_enrutamiento || "No disponible");
        $("#auditExtracted").innerHTML = field("Paciente", data.paciente.nombre) + field("Edad", data.paciente.edad) +
          field("Profesional solicitante", data.medico_solicitante.nombre) + field("Matrícula", data.medico_solicitante.matricula) +
          field("Estudio realizado", data.estudio_realizado) + field("Diagnóstico consignado", data.diagnostico_principal) + field("CIE-10 sugerido", data.cie10_sugerido);
        setText("#auditMedicines", data.medicamentos_recetados.length
          ? data.medicamentos_recetados.map(m => `${m.medicamento}: ${available(m.dosis)}`).join("; ") : "No hay medicamentos consignados.");
        setText("#auditRawJson", JSON.stringify(d, null, 2));
      }
      const obs = $("#reviewObservation");
      if (obs.value !== state.observation) obs.value = state.observation;
      obs.disabled = sending || !!state.confirmation;
      $("#reviewerField").hidden = !state.capabilities.requiresReviewerId;
      if ($("#reviewerId").value !== state.reviewerId) $("#reviewerId").value = state.reviewerId;
      // Agregado por Edil: mostrar quién está autenticado, sin permitir que el
      // navegador elija otra identidad para el registro persistido.
      $("#reviewerId").readOnly = true;
      $("#reviewerId").setAttribute("aria-readonly", "true");
      $("#reviewerId").disabled = true;
      updateDecisionButtons();
      const uncertain = state.uncertain.has(state.selectedId);
      setText("#reviewAvailability", !state.capabilities.submit ? "Envío deshabilitado: contrato de aprobación/rechazo pendiente. La observación solo se mantiene mientras esta página esté abierta."
        : !state.authenticatedUser ? "Envío deshabilitado: no hay una identidad autenticada. Inicia sesión con tu cuenta de MediFlow."
        : !state.authenticatedUser.canReview ? "Envío deshabilitado: tu identidad no tiene permiso de auditor."
        : !state.storageAvailable ? "No se pudo proteger el envío contra recargas. Revisa el almacenamiento de sesión antes de decidir."
        : uncertain ? "Hay un envío sin confirmación. No vuelvas a enviarlo; consulta el historial y solicita verificación al equipo."
        : state.reviewAlreadyFinal ? "Ya existe una decisión final confirmada por el backend. El documento queda en consulta; no se permite otra decisión."
        : state.capabilities.requiresReviewerId ? "Auditor autenticado por el servidor. Para rechazar, añade una observación. El éxito requiere confirmación del backend."
        : "La decisión se anunciará registrada únicamente tras una confirmación válida de persistencia.");
      setText("#reviewResult", sending ? "Registrando decisión… No cierres esta ventana ni repitas el envío."
        : state.receipt ? `Decisión persistida. Revisión ${state.receipt.reviewId}; auditor ${state.receipt.auditor}; fecha ${state.receipt.reviewedAt}.`
        : state.submitError ? message(state.submitError) + (uncertain ? " No repitas el envío." : "") : "");
      setText("#reviewHistoryStatus", !state.capabilities.history ? "Historial persistido pendiente de contrato y API aprobados. No se genera un historial local."
        : state.historyStatus === "loading" ? "Consultando historial persistido…" : state.historyError ? message(state.historyError)
        : state.history.length ? "Historial recibido del backend." : "Sin decisiones en la respuesta del historial.");
      $("#refreshReviewHistory").hidden = !state.capabilities.history;
      $("#refreshReviewHistory").disabled = sending || state.historyStatus === "loading";
      $("#reviewHistory").innerHTML = state.history.map(e => `<li><dl class="audit-facts">${field("ID de revisión", e.reviewId)}${field("Decisión", e.decision === "approve" ? "Aprobado" : "Rechazado")}${field("Auditor", e.auditor)}${field("Fecha del servidor", e.reviewedAt)}${field("Observación", e.observation)}</dl></li>`).join("");
      if (state.confirmation) {
        setText("#reviewConfirmationText", `${state.confirmation.decision === "approve" ? "Aprobar" : "Rechazar"} el documento ${state.confirmation.documentId}. El análisis original y su prioridad no se modifican desde este panel.`);
        setText("#reviewConfirmationObservation", state.confirmation.observation || "Sin observación.");
        if (!confirmation.open) confirmation.showModal();
      } else if (confirmation.open) confirmation.close();
      $("#reviewConfirmSend").disabled = $("#reviewCancelSend").disabled = sending;
      setText("#reviewConfirmProgress", sending ? "Enviando; espera la confirmación del servidor." : "");
    }
    controller = root.MediFlowAuditController.createController({ client, storage: options.storage || storage, onChange: render,
      authenticatedUser: Object.prototype.hasOwnProperty.call(options, "authenticatedUser")
        ? options.authenticatedUser : root.MEDIFLOW_AUTHENTICATED_USER });
    $("#refreshAudit").addEventListener("click", () => controller.load());
    $("#q").addEventListener("input", () => render(controller.state));
    $("#auditPriority").addEventListener("change", () => render(controller.state));
    $("#auditList").addEventListener("click", event => {
      const target = event.target.closest("[data-open-document]");
      if (!target || target.disabled) return;
      focusBeforeDetail = target;
      if (!dialog.open) dialog.showModal();
      controller.open(target.dataset.openDocument);
    });
    function closeDetail() {
      const id = controller.state.selectedId;
      if (controller.close()) {
        dialog.close();
        const currentButton = [...$("#auditList").querySelectorAll("[data-open-document]")].find(button => button.dataset.openDocument === id);
        (currentButton || (focusBeforeDetail?.isConnected ? focusBeforeDetail : $("#refreshAudit"))).focus();
      }
    }
    $("#auditClose").addEventListener("click", closeDetail);
    dialog.addEventListener("cancel", event => { event.preventDefault(); if (!confirmation.open) closeDetail(); });
    $("#auditRetryDetail").addEventListener("click", () => controller.open(controller.state.selectedId));
    $("#reviewObservation").addEventListener("input", event => { controller.setObservation(event.target.value); updateDecisionButtons(); });
    $("#approveReview").addEventListener("click", () => controller.confirm("approve"));
    $("#rejectReview").addEventListener("click", () => controller.confirm("reject"));
    $("#reviewCancelSend").addEventListener("click", () => controller.cancelConfirmation());
    confirmation.addEventListener("cancel", event => { event.preventDefault(); controller.cancelConfirmation(); });
    $("#reviewConfirmSend").addEventListener("click", () => controller.submit());
    $("#refreshReviewHistory").addEventListener("click", () => controller.loadHistory());
    // Agregado por Edil: no abandonar una escritura en curso ni cerrar sesión
    // por un clic accidental. El cierre solo se confirma después del HTTP 204.
    $("#authLogout").addEventListener("click", () => {
      if (!authClient || controller.state.submitStatus === "sending" || logoutTask || logoutComplete) return;
      setText("#logoutStatus", ""); logoutDialog.showModal();
    });
    $("#logoutCancel").addEventListener("click", () => { if (!logoutTask) logoutDialog.close(); });
    logoutDialog.addEventListener("cancel", event => { event.preventDefault(); if (!logoutTask) logoutDialog.close(); });
    $("#logoutConfirm").addEventListener("click", () => {
      if (!authClient || !logoutDialog.open || logoutTask || logoutComplete || controller.state.submitStatus === "sending") return;
      $("#logoutConfirm").disabled = $("#logoutCancel").disabled = true;
      setText("#logoutStatus", "Cerrando sesión…");
      logoutTask = Promise.resolve().then(() => authClient.logout()).then(() => {
        logoutComplete = true;
        setText("#logoutStatus", "Sesión cerrada.");
        // No borrar el ledger de envíos inciertos ni escribir datos clínicos.
        if (options.onLoggedOut) options.onLoggedOut();
        else root.location.assign("../login/index.html");
      }).catch(() => { setText("#logoutStatus", "No se pudo confirmar el cierre de sesión. Intenta nuevamente."); })
        .finally(() => {
          logoutTask = null;
          $("#logoutConfirm").disabled = $("#logoutCancel").disabled = logoutComplete;
          render(controller.state);
        });
    });
    controller.load();
    return controller;
  }
  // Agregado por Edil: arrancar la web estática con la sesión real, antes de
  // crear el adaptador que captura la identidad. No sustituir fallos por la
  // identidad inyectada: la bandera de contrato sigue siendo independiente.
  async function mountFromSession(doc, options = {}) {
    const $ = selector => doc.querySelector(selector);
    $("#approveReview").hidden = $("#rejectReview").hidden = true;
    $("#approveReview").disabled = $("#rejectReview").disabled = true;
    $("#authSessionStatus").textContent = "Verificando sesión…";
    const authClient = options.authClient || root.MediFlowAuthApi?.createClient();
    let authenticatedUser = null, sessionError = false;
    try {
      const session = await authClient.getSession();
      if (session?.authenticated === true && typeof session.user?.login === "string" && session.user.login.trim()
          && typeof session.user.canReview === "boolean") {
        authenticatedUser = { login: session.user.login, canReview: session.user.canReview };
      } else if (!(session?.authenticated === false && session.user === null)) {
        throw Error("Invalid session");
      }
    } catch (_) { sessionError = true; }
    const factory = options.adapterFactory || root.MediFlowReviewHttpAdapter?.createAdapter;
    const adapter = factory ? factory({
      decisionApproved: root.MEDIFLOW_REVIEW_CONTRACT_APPROVED === true,
      authenticatedUser,
    }) : null;
    const client = options.client || root.MediFlowReviewsApi.createClient({ approvedAdapter: adapter });
    return mount(doc, { ...options, authClient, client, authenticatedUser, sessionError });
  }
  root.MediFlowAuditPanel = { mount, mountFromSession };
  if (typeof module !== "undefined") module.exports = { mount, mountFromSession };
})(typeof window !== "undefined" ? window : globalThis);
