const test = require("node:test");
const assert = require("node:assert/strict");
require("../src/assets/js/documents-api.js");
const { ReviewApiError } = require("../src/assets/js/reviews-api.js");
const { createController } = require("../src/assets/js/audit-controller.js");
const { documents } = require("../src/assets/js/documents-mock.js");
const sample = () => structuredClone(documents[3]);
const principal = { login: "auditor_sintetico", canReview: true };
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
const storage = () => { const values = new Map(); return { getItem: k => values.get(k) || null, setItem: (k, v) => values.set(k, v) }; };
const fakeClient = overrides => ({ capabilities: { submit: true, history: false }, listPending: async () => [sample()], getDocument: async () => sample(),
  submitReview: async input => ({ ...input, persisted: true, reviewId: "TEST-1", auditor: "Sintético", reviewedAt: "2026-10-17T18:00:00Z" }), ...overrides });
async function ready(overrides = {}, store = storage(), authenticatedUser = principal) {
  const c = createController({ client: fakeClient(overrides), storage: store, authenticatedUser });
  await c.load(); await c.open(sample().documento_id); return c;
}
test("carga deduplicada y filtro vacío válido", async () => {
  const d = deferred(); let calls = 0;
  const c = createController({ client: fakeClient({ listPending: () => { calls++; return d.promise; } }) });
  const a = c.load(), b = c.load(); assert.equal(a, b); assert.equal(c.state.listStatus, "loading");
  d.resolve([]); await a; assert.equal(calls, 1); assert.equal(c.state.listStatus, "ready"); assert.deepEqual(c.state.rows, []);
});
test("fallo de actualización conserva bandeja previa y permite reintentar", async () => {
  let fail = false;
  const c = await ready({ listPending: async () => { if (fail) throw new ReviewApiError("Red"); return [sample()]; } });
  fail = true; await c.load(); assert.equal(c.state.rows.length, 1); assert.equal(c.state.listStatus, "error");
  fail = false; await c.load(); assert.equal(c.state.listStatus, "ready");
});
test("detalle deduplicado; respuestas fuera de orden no cambian el documento activo", async () => {
  const a = deferred(), b = deferred();
  const c = createController({ client: fakeClient({ getDocument: id => id === "A" ? a.promise : b.promise }) });
  const first = c.open("A"); assert.equal(c.open("A"), first);
  const second = c.open("B");
  b.resolve({ ...sample(), documento_id: "B" }); await second;
  a.resolve({ ...sample(), documento_id: "A" }); await first;
  assert.equal(c.state.selectedId, "B"); assert.equal(c.state.document.documento_id, "B");
});
test("cerrar descarta respuestas tardías", async () => {
  const d = deferred(); const c = createController({ client: fakeClient({ getDocument: () => d.promise }) });
  const task = c.open("A"); c.close(); d.resolve(sample()); await task;
  assert.equal(c.state.selectedId, null); assert.equal(c.state.document, null);
});
test("fallo de detalle conserva análisis anterior y bloquea decisiones sobre datos viejos", async () => {
  let fail = false; const c = await ready({ getDocument: async () => { if (fail) throw new ReviewApiError("Error", 503); return sample(); } });
  const old = c.state.document; fail = true; await c.open(sample().documento_id);
  assert.equal(c.state.document, old); assert.equal(c.canSubmit(), false); assert.equal(c.state.detailStatus, "error");
});
test("sin contrato, sin almacenamiento o fuera de auditoría no se puede enviar", async () => {
  const c = await ready({ capabilities: { submit: false, history: false } }); assert.equal(c.confirm("approve"), false);
  const noStorage = await ready({}, null); assert.equal(noStorage.canSubmit(), false);
  const processed = await ready({ getDocument: async () => ({ ...sample(), status: "procesado" }) }); assert.equal(processed.canSubmit(), false);
});
test("contrato integrado usa el auditor autenticado y exige observación para rechazar", async () => {
  const c = await ready({ capabilities: { submit: true, history: false, requiresReviewerId: true, requiresRejectionObservation: true } });
  assert.equal(c.state.reviewerId, "auditor_sintetico");
  c.setReviewerId("other");
  assert.equal(c.canSubmit("approve"), true); assert.equal(c.canSubmit("reject"), false);
  c.setObservation("Información sintética insuficiente"); assert.equal(c.canSubmit("reject"), true);
  c.confirm("reject"); assert.equal(c.state.confirmation.reviewerId, "auditor_sintetico");
  c.setReviewerId("other"); assert.equal(c.state.reviewerId, "auditor_sintetico");
});
test("sin identidad o sin permiso no se envía aunque el contrato esté aprobado", async () => {
  for (const identity of [null, { login: "lector_sintetico", canReview: false }, { login: "", canReview: true }]) {
    let calls = 0;
    const c = await ready({ submitReview: async () => { calls++; } }, storage(), identity);
    c.setReviewerId("auditor_sintetico");
    assert.equal(c.canSubmit("approve"), false); assert.equal(c.confirm("approve"), false);
    await c.submit(); assert.equal(calls, 0);
  }
});
test("observación y confirmación: cancelar no envía nada", async () => {
  let sent = 0; const c = await ready({ submitReview: async () => { sent++; } });
  c.setObservation("observación sintética"); c.confirm("reject");
  assert.equal(c.state.confirmation.observation, "observación sintética");
  c.setObservation("cambio durante confirmación"); assert.equal(c.state.observation, "observación sintética");
  c.cancelConfirmation(); await c.submit(); assert.equal(sent, 0);
});
test("doble confirmación, prioridad Urgente conservada y retirada solo tras confirmación", async () => {
  const d = deferred(); let calls = 0; const doc = sample(); doc.clasificacion.nivel_prioridad = "Urgente";
  const c = await ready({ getDocument: async () => doc, listPending: async () => [doc], submitReview: () => { calls++; return d.promise; } });
  c.setObservation("Validación de test"); c.confirm("approve");
  const a = c.submit(), b = c.submit(); assert.equal(a, b); assert.equal(c.state.rows.length, 1);
  assert.equal(c.state.submitStatus, "sending"); assert.equal(c.close(), false);
  await c.open("OTHER"); assert.equal(c.state.selectedId, doc.documento_id);
  d.resolve({ reviewId: "TEST" }); await a; await c.load();
  assert.equal(calls, 1); assert.equal(c.state.rows.length, 0); assert.equal(c.state.submitStatus, "confirmed");
  assert.equal(doc.clasificacion.nivel_prioridad, "Urgente"); assert.equal(c.confirm("reject"), false);
});
test("envío incierto se bloquea incluso tras recarga sin guardar observación", async () => {
  const store = storage(); let calls = 0;
  const client = { submitReview: async () => { calls++; throw new ReviewApiError("Timeout", undefined, true); } };
  const c = await ready(client, store); c.setObservation("NO DEBE GUARDARSE"); c.confirm("approve"); await c.submit();
  assert.equal(c.state.submitStatus, "uncertain"); assert.equal(c.canSubmit(), false);
  assert.ok(!store.getItem("mediflow.review.uncertain.v1").includes("NO DEBE GUARDARSE"));
  const reloaded = await ready(client, store); assert.equal(reloaded.canSubmit(), false); await reloaded.submit(); assert.equal(calls, 1);
});
for (const status of [400, 401, 403, 404, 409, 422]) {
  test("error definido " + status + " conserva observación/bandeja y no anuncia éxito", async () => {
    const c = await ready({ submitReview: async () => { throw new ReviewApiError("Error", status); } });
    c.setObservation("conservar"); c.confirm("reject"); await c.submit();
    assert.equal(c.state.receipt, null); assert.equal(c.state.rows.length, 1); assert.equal(c.state.observation, "conservar");
    assert.equal(c.state.submitStatus, "error");
    if ([404, 409].includes(status)) assert.equal(c.canSubmit(), false);
  });
}
test("almacenamiento bloqueado o corrupto impide POST", async () => {
  for (const store of [{ getItem: () => "not-json" }, { getItem: () => null, setItem: () => { throw Error(); } }]) {
    let calls = 0; const c = await ready({ submitReview: async () => { calls++; } }, store);
    c.confirm("approve"); await c.submit(); assert.equal(calls, 0); assert.equal(c.state.storageAvailable, false);
  }
});
test("historial fallido conserva filas previas; no borra bloqueo de envío incierto", async () => {
  let fail = false;
  const c = await ready({ capabilities: { submit: true, history: true }, getReviewHistory: async () => { if (fail) throw new ReviewApiError("red"); return [{ reviewId: "OLD" }]; },
    submitReview: async () => { throw new ReviewApiError("Timeout", undefined, true); } });
  await c.loadHistory(); assert.equal(c.state.history.length, 1);
  fail = true; await c.loadHistory(); assert.equal(c.state.history.length, 1); assert.equal(c.state.historyStatus, "error");
  c.confirm("approve"); await c.submit(); fail = false; await c.loadHistory(); assert.equal(c.canSubmit(), false); assert.equal(c.state.submitStatus, "uncertain");
});
test("actualizar detalle después de éxito no vuelve a habilitar una segunda decisión", async () => {
  const c = await ready(); c.confirm("approve"); await c.submit();
  await c.open(sample().documento_id);
  assert.equal(c.state.reviewAlreadyFinal, true); assert.equal(c.canSubmit("approve"), false);
});
test("historial final bloquea otra decisión sin inventar recibo para un envío incierto", async () => {
  const id = sample().documento_id;
  const c = await ready({ capabilities: { submit: true, history: true },
    getReviewHistory: async () => [{ documentId: id, decision: "reject", reviewId: "REV-OTHER" }] });
  await c.loadHistory();
  assert.equal(c.state.reviewAlreadyFinal, true); assert.equal(c.canSubmit("approve"), false);
  assert.equal(c.state.receipt, null); assert.notEqual(c.state.submitStatus, "confirmed");
});
