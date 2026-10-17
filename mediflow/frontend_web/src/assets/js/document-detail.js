/* S3-07.3: ciclo de lectura del diálogo existente, sin mutaciones de documentos. */
(function (root) {
  "use strict";
  function createDetail({ dialog, status, json, loadDocument }) {
    let version = 0, activeId = null, activeTask = null;
    const pending = new Map();
    dialog.addEventListener("close", () => {
      version++;
      activeId = activeTask = null;
      dialog.setAttribute("aria-busy", "false");
    });
    function open(id) {
      if (dialog.open && activeId === id) return activeTask;
      const current = ++version;
      activeId = id;
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
    return { open };
  }
  root.MediFlowDocumentDetail = { createDetail };
  if (typeof module !== "undefined") module.exports = { createDetail };
})(typeof window !== "undefined" ? window : globalThis);
