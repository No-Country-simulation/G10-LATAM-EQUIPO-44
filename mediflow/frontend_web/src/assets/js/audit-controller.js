/* Agregado por Edil: estado del panel independiente del DOM para probar carreras,
   confirmaciones y errores sin OCI/Gemini ni escrituras reales. */
(function (root) {
  "use strict";
  const ledgerKey = "mediflow.review.uncertain.v1";
  function createController({ client, onChange = () => {}, storage = null, authenticatedUser = null }) {
    // Agregado por Edil: conservar una copia de la identidad suministrada por
    // el servidor. El formulario no puede cambiar el responsable de la decisión.
    const principal = typeof authenticatedUser?.login === "string" && authenticatedUser.login.trim()
      ? Object.freeze({ login: authenticatedUser.login.trim(), canReview: authenticatedUser.canReview === true }) : null;
    const state = {
      rows: [], listStatus: "idle", listError: null, selectedId: null, document: null,
      detailStatus: "idle", detailError: null, observation: "", reviewerId: principal?.login || "", authenticatedUser: principal, confirmation: null,
      submitStatus: "idle", submitError: null, receipt: null, reviewAlreadyFinal: false,
      history: [], historyStatus: "idle", historyError: null,
      capabilities: client.capabilities, uncertain: new Set(), storageAvailable: !!storage
    };
    let listTask = null, detailTask = null, submitTask = null, historyTask = null, version = 0;
    const confirmedIds = new Set();
    try {
      if (storage) {
        const saved = JSON.parse(storage.getItem(ledgerKey) || "[]");
        if (!Array.isArray(saved) || saved.some(id => typeof id !== "string")) throw Error();
        state.uncertain = new Set(saved);
      }
    } catch (_) { state.storageAvailable = false; }
    const emit = () => onChange(state);
    function saveLedger() {
      try { if (!state.storageAvailable) return false; storage.setItem(ledgerKey, JSON.stringify([...state.uncertain])); return true; }
      catch (_) { state.storageAvailable = false; return false; }
    }
    function load() {
      if (listTask) return listTask;
      state.listStatus = "loading"; state.listError = null; emit();
      listTask = Promise.resolve().then(() => client.listPending()).then(rows => {
        state.rows = rows.filter(doc => !confirmedIds.has(doc.documento_id)); state.listStatus = "ready";
      }).catch(error => { state.listStatus = "error"; state.listError = error; })
        .finally(() => { listTask = null; emit(); });
      return listTask;
    }
    function open(id) {
      if (state.submitStatus === "sending") return Promise.resolve();
      if (state.selectedId === id && detailTask) return detailTask;
      const current = ++version;
      if (state.selectedId !== id) { state.document = null; state.observation = ""; }
      state.selectedId = id; state.confirmation = null; state.receipt = null;
      state.reviewAlreadyFinal = confirmedIds.has(id);
      state.submitStatus = "idle"; state.submitError = null;
      state.history = []; state.historyStatus = "idle"; state.historyError = null;
      state.detailStatus = "loading"; state.detailError = null; emit();
      const task = Promise.resolve().then(() => client.getDocument(id)).then(doc => {
        if (version !== current) return;
        state.document = doc; state.detailStatus = "ready";
      }).catch(error => {
        if (version !== current) return;
        state.detailStatus = "error"; state.detailError = error;
      }).finally(() => { if (version === current) { detailTask = null; emit(); } });
      detailTask = task;
      task.then(() => { if (version === current && state.detailStatus === "ready") loadHistory(); });
      return task;
    }
    function close() {
      if (state.submitStatus === "sending") return false;
      version++; state.selectedId = null; state.confirmation = null; detailTask = null; emit(); return true;
    }
    function setObservation(value) {
      if (state.submitStatus === "sending" || state.confirmation) return;
      state.observation = value; // No se persiste texto clínico en almacenamiento del navegador.
    }
    // Agregado por Edil: se conserva el método por compatibilidad con la vista
    // anterior; el servidor es ahora la única fuente de identidad del auditor.
    function setReviewerId() { return false; }
    function canSubmit(decision) {
      return !!(principal?.canReview && state.capabilities.submit && state.storageAvailable && state.detailStatus === "ready" &&
        (!state.capabilities.requiresReviewerId || state.reviewerId.trim()) &&
        (!state.capabilities.requiresRejectionObservation || decision !== "reject" || state.observation.trim()) &&
        state.document?.status === "auditoria_humana" && state.document.documento_id === state.selectedId &&
        !confirmedIds.has(state.selectedId) &&
        !state.uncertain.has(state.selectedId) && !["sending", "confirmed"].includes(state.submitStatus));
    }
    function confirm(decision) {
      if (!["approve", "reject"].includes(decision) || !canSubmit(decision)) return false;
      state.confirmation = { documentId: state.selectedId, decision, observation: state.observation.trim(),
        ...(state.capabilities.requiresReviewerId ? { reviewerId: principal.login } : {}) };
      state.submitError = null; emit(); return true;
    }
    function cancelConfirmation() { if (state.submitStatus !== "sending") { state.confirmation = null; emit(); } }
    function submit() {
      if (submitTask) return submitTask;
      if (!state.confirmation || !canSubmit(state.confirmation.decision)) return Promise.resolve(false);
      const input = { ...state.confirmation };
      // Marcar antes del POST. Si se recarga o se pierde la respuesta, no reenviar.
      // Solo guardamos ID; no simula una revisión persistida ni guarda observaciones.
      state.uncertain.add(input.documentId);
      if (!saveLedger()) { state.uncertain.delete(input.documentId); emit(); return Promise.resolve(false); }
      state.submitStatus = "sending"; state.submitError = null; emit();
      submitTask = Promise.resolve().then(() => client.submitReview(input)).then(receipt => {
        state.receipt = receipt; state.submitStatus = "confirmed"; state.confirmation = null; state.reviewAlreadyFinal = true;
        confirmedIds.add(input.documentId);
        state.uncertain.delete(input.documentId); saveLedger();
        state.rows = state.rows.filter(doc => doc.documento_id !== input.documentId);
      }).catch(error => {
        state.submitError = error; state.submitStatus = error.uncertain ? "uncertain" : "error";
        state.confirmation = null;
        if (!error.uncertain) { state.uncertain.delete(input.documentId); saveLedger(); }
        // Un 409/404 puede indicar un cambio concurrente: exigir un nuevo GET.
        if ([404, 409].includes(error.status)) state.detailStatus = "stale";
      }).finally(() => {
        submitTask = null; emit();
        if (state.submitStatus === "confirmed") { load(); loadHistory(); }
      });
      return submitTask;
    }
    function loadHistory() {
      if (!state.capabilities.history || !state.selectedId) return Promise.resolve();
      const id = state.selectedId, current = version;
      if (historyTask?.id === id && historyTask.version === current) return historyTask.task;
      state.historyStatus = "loading"; state.historyError = null; emit();
      const task = Promise.resolve().then(() => client.getReviewHistory(id)).then(entries => {
        if (version !== current) return;
        state.history = entries; state.historyStatus = "ready";
        // Agregado por Edil: una decisión final leída del servidor bloquea
        // otra aprobación aunque el análisis siga en auditoria_humana. No
        // atribuirla a nuestro envío incierto ni fabricar un recibo de éxito.
        if (entries.some(entry => entry.documentId === id && ["approve", "reject"].includes(entry.decision))) {
          confirmedIds.add(id); state.reviewAlreadyFinal = true;
          state.rows = state.rows.filter(document => document.documento_id !== id);
        }
        // Agregado por Edil: ni una fila antigua ni un historial vacío prueban
        // qué ocurrió con nuestro POST. Mostrar el historial sin desbloquear
        // reenvíos ni anunciar confirmación; reconciliación pendiente del contrato.
      }).catch(error => { if (version === current) { state.historyStatus = "error"; state.historyError = error; } })
        .finally(() => { if (version === current) { historyTask = null; emit(); } });
      historyTask = { id, version: current, task }; return task;
    }
    return { state, load, open, close, setObservation, setReviewerId, canSubmit, confirm, cancelConfirmation, submit, loadHistory };
  }
  root.MediFlowAuditController = { createController };
  if (typeof module !== "undefined") module.exports = { createController };
})(typeof window !== "undefined" ? window : globalThis);
