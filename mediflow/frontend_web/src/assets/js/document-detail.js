/* S3-07.3: ciclo de lectura del diálogo existente, sin mutaciones de documentos. */
(function (root) {
  "use strict";
  function createDetail({ dialog, status, json, loadDocument, summary,
    originalButton, originalStatus, originalViewer, loadOriginal }) {
    let version = 0, activeId = null, activeTask = null;
    let ready = false, originalTask = null, originalAbort = null;
    const pending = new Map();
    // Agregado por Edil: el original se consulta a petición del usuario; nunca
    // se conserva una vista anterior al cerrar o cambiar de documento.
    function clearOriginal() {
      originalAbort?.abort(); originalAbort = originalTask = null;
      originalViewer?.clear();
      if (originalButton) { originalButton.hidden = true; originalButton.disabled = true; }
      if (originalStatus) { originalStatus.textContent = ""; originalStatus.dataset.state = "idle"; }
    }
    function summaryText(doc) {
      const c = doc.clasificacion || {}, r = doc.decision_enrutamiento || {};
      const extracted = doc.datos_extraidos || {};
      const labels = { recibido: "Recibido", procesado: "Procesado", auditoria_humana: "Requiere revisión humana" };
      const lines = ["Documento: " + doc.documento_id, "Estado: " + (labels[doc.status] || doc.status),
        "Tipo: " + (c.tipo_documento || "No informado")];
      if (doc.status !== "recibido") {
        lines.push("Prioridad orientativa: " + (c.nivel_prioridad || "No informada"));
        if (typeof c.score_confianza_clasificacion === "number") {
          lines.push("Confianza de clasificación: " + Math.round(c.score_confianza_clasificacion * 100) + "% (no mide seguridad clínica)");
        }
        lines.push("Revisión humana: " + (r.requiere_auditoria_humana === true ? "Requerida" : r.requiere_auditoria_humana === false ? "No requerida por el sistema" : "No informada"));
      } else lines.push("La recepción no confirma que el análisis haya terminado.");
      if (extracted.paciente?.nombre) lines.push("Paciente: " + extracted.paciente.nombre);
      if (extracted.estudio_realizado) lines.push("Estudio: " + extracted.estudio_realizado);
      if (extracted.diagnostico_principal) lines.push("Diagnóstico extraído: " + extracted.diagnostico_principal);
      if (r.justificacion_enrutamiento) lines.push("Motivo de enrutamiento: " + r.justificacion_enrutamiento);
      return lines.join("\n");
    }
    function showOriginal() {
      if (!ready || !dialog.open || !loadOriginal || !originalViewer) return;
      if (originalTask) return originalTask;
      const current = version, id = activeId;
      originalAbort = new AbortController();
      const signal = originalAbort.signal;
      if (originalButton) originalButton.disabled = true;
      if (originalStatus) { originalStatus.textContent = "Consultando original…"; originalStatus.dataset.state = "loading"; }
      originalViewer.clear();
      originalTask = Promise.resolve().then(() => {
        if (version !== current || !dialog.open) return;
        return loadOriginal(id, { signal });
      }).then(async file => {
        if (version !== current || !dialog.open) return;
        const displayed = await originalViewer.show(file);
        if (version !== current || !dialog.open) return;
        if (!displayed) throw Error("unsupported preview");
        if (originalStatus) { originalStatus.textContent = "Original recuperado con tu sesión de MediFlow."; originalStatus.dataset.state = "ready"; }
      }).catch(error => {
        if (version !== current || !dialog.open) return;
        originalViewer.clear();
        if (originalStatus) {
          originalStatus.textContent = error instanceof root.MediFlowDocumentsApi.DocumentsApiError
            ? error.message : "No se pudo consultar el original. Puedes intentarlo de nuevo.";
          originalStatus.dataset.state = "error";
        }
      }).finally(() => {
        if (version !== current) return;
        originalTask = originalAbort = null;
        if (originalButton) originalButton.disabled = false;
      });
      return originalTask;
    }
    originalButton?.addEventListener("click", showOriginal);
    dialog.addEventListener("close", () => {
      version++;
      ready = false; clearOriginal();
      if (summary) summary.textContent = "";
      activeId = activeTask = null;
      dialog.setAttribute("aria-busy", "false");
    });
    function open(id) {
      if (dialog.open && activeId === id) return activeTask;
      const current = ++version;
      activeId = id;
      ready = false; clearOriginal();
      if (summary) summary.textContent = "";
      json.textContent = "";
      status.textContent = "Consultando documento...";
      status.dataset.state = "loading";
      dialog.setAttribute("aria-busy", "true");
      if (!dialog.open) dialog.showModal();
      if (!pending.has(id)) {
        const request = Promise.resolve().then(() => loadDocument(id));
        pending.set(id, request);
        // Limpieza tanto en éxito como en fallo, sin crear un rechazo no observado.
        request.then(() => pending.delete(id), () => pending.delete(id));
      }
      activeTask = pending.get(id).then(doc => {
        if (version !== current || !dialog.open) return;
        json.textContent = JSON.stringify(doc, null, 2);
        if (summary) summary.textContent = summaryText(doc);
        ready = true;
        if (originalButton && originalViewer && loadOriginal) {
          originalButton.hidden = false; originalButton.disabled = false;
        }
        status.textContent = "Documento cargado.";
        status.dataset.state = "ready";
      }).catch(error => {
        if (version !== current || !dialog.open) return;
        const safe = error instanceof root.MediFlowDocumentsApi.DocumentsApiError;
        status.textContent = safe ? error.message : "No se pudo cargar el documento.";
        status.dataset.state = safe && error.status === 404 ? "not-found" : "error";
      }).finally(() => {
        if (version === current) dialog.setAttribute("aria-busy", "false");
      });
      return activeTask;
    }
    return { open, showOriginal };
  }
  root.MediFlowDocumentDetail = { createDetail };
  if (typeof module !== "undefined") module.exports = { createDetail };
})(typeof window !== "undefined" ? window : globalThis);
