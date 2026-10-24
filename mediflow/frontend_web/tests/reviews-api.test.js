const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const documentsApi = require("../src/assets/js/documents-api.js");
const { createClient, ReviewApiError, errorMessage } = require("../src/assets/js/reviews-api.js");
const { documents } = require("../src/assets/js/documents-mock.js");
// Agregado por Edil: todas las respuestas de revisión son exclusivas de pruebas.
const sample = () => structuredClone(documents[3]);
const input = () => ({ documentId: sample().documento_id, decision: "approve", observation: "Revisión sintética" });
const receipt = (request = input()) => ({ ...request, persisted: true, reviewId: "TEST-REVIEW-1", auditor: "Auditor sintético", reviewedAt: "2026-10-17T18:00:00Z" });
const adapter = overrides => ({ approved: true, contractReference: "test-only-interface", ...overrides });
const docs = overrides => ({ ...documentsApi, getDocuments: async () => [sample()], getDocument: async () => sample(), ...overrides });

test("sin contrato no invoca rutas propuestas, no permite escribir ni inventa historial", async () => {
  let calls = 0;
  const client = createClient({ documentsApi: docs({ getDocuments: async options => {
    calls++; assert.equal(options.status, "auditoria_humana"); return [sample()];
  } }) });
  assert.deepEqual(client.capabilities, { submit: false, history: false });
  await client.listPending(); assert.equal(calls, 1);
  await assert.rejects(client.submitReview(input()), /pendientes de contrato/);
  await assert.rejects(client.getReviewHistory(input().documentId), /pendiente de contrato/);
  assert.equal(calls, 1);
});
for (const config of [{}, { approved: false, contractReference: "test" }, { approved: true }, { approved: true, contractReference: " " }]) {
  test("adaptador sin aprobación y referencia completas queda deshabilitado " + JSON.stringify(config), () => {
    const client = createClient({ approvedAdapter: { ...config, submitReview() { assert.fail(); } } });
    assert.equal(client.capabilities.submit, false);
  });
}
test("bandeja valida, filtra y deduplica sin cambiar prioridad ni estado", async () => {
  const urgent = sample(); urgent.clasificacion.nivel_prioridad = "Urgente";
  const before = structuredClone(urgent);
  const client = createClient({ documentsApi: docs({ getDocuments: async () => [documents[0], urgent, urgent] }) });
  assert.deepEqual(await client.listPending(), [before]);
  assert.deepEqual(urgent, before);
});
for (const bad of [null, {}, [null], [{ documento_id: "broken" }]]) {
  test("no muestra bandeja parcial ni datos incompatibles: " + JSON.stringify(bad), async () => {
    const client = createClient({ documentsApi: docs({ getDocuments: async () => bad }) });
    await assert.rejects(client.listPending(), /no cumple el contrato/);
  });
}
test("GET individual reutiliza el cliente y sus opciones de conexión", async () => {
  let calls = 0;
  const client = createClient({ requestOptions: { baseUrl: "http://localhost:8123" }, documentsApi: docs({ getDocument: async (id, options) => {
    assert.equal(id, input().documentId); assert.equal(options.baseUrl, "http://localhost:8123"); calls++; return sample();
  } }) });
  await client.getDocument(input().documentId); assert.equal(calls, 1);
  await assert.rejects(client.getDocument(".."), /identificador/); assert.equal(calls, 1);
});
test("GET HTTP local usa filtro aprobado y codifica ID; solo servidor sintético de test", async t => {
  const doc = sample(); doc.documento_id = "DOC /?á#"; const requests = [];
  const server = http.createServer((req, res) => {
    requests.push(req.url); res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(req.url.startsWith("/api/documents?") ? [doc] : doc));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const client = createClient({ requestOptions: { baseUrl: `http://127.0.0.1:${server.address().port}` } });
  await client.listPending(); await client.getDocument(doc.documento_id);
  const list = new URL(requests[0], "http://localhost");
  assert.equal(list.pathname, "/api/documents"); assert.equal(list.searchParams.get("status"), "auditoria_humana"); assert.equal(list.searchParams.get("limit"), "500");
  assert.equal(requests[1], "/api/documents/" + encodeURIComponent(doc.documento_id));
});
test("filtro inválido se rechaza antes de usar HTTP", async () => {
  await assert.rejects(documentsApi.getDocuments({ status: "approved", fetchImpl: () => assert.fail() }), /estado solicitado/);
});
for (const status of [400, 401, 403, 404, 409, 422, 500, 502, 503]) {
  test("HTTP " + status + " se conserva sin mostrar contenido privado", async () => {
    const client = createClient({ requestOptions: { fetchImpl: async () => ({ ok: false, status, json: () => assert.fail("do not read private response") }) } });
    await assert.rejects(client.listPending(), error => {
      assert.equal(error.status, status); assert.ok(!errorMessage(error).includes("private")); return true;
    });
  });
}
test("red, timeout y JSON malformado son errores controlados", async () => {
  for (const options of [
    { fetchImpl: async () => { throw Error("PRIVATE"); } },
    { timeoutMs: 5, fetchImpl: (_, { signal }) => new Promise((_, reject) => signal.addEventListener("abort", () => reject(Error("PRIVATE")))) },
    { fetchImpl: async () => ({ ok: true, json: async () => { throw Error("PRIVATE"); } }) }
  ]) {
    await assert.rejects(createClient({ requestOptions: options }).listPending(), error => !errorMessage(error).includes("PRIVATE"));
  }
});
test("doble clic approve/reject genera solo un envío; solo un recibo válido confirma", async () => {
  let resolve, calls = 0;
  const client = createClient({ approvedAdapter: adapter({ submitReview: request => { calls++; return new Promise(r => { resolve = () => r(receipt(request)); }); } }) });
  const first = client.submitReview(input()), second = client.submitReview({ ...input(), decision: "reject" });
  assert.equal(first, second); await Promise.resolve(); assert.equal(calls, 1);
  resolve(); assert.equal((await first).persisted, true);
  await assert.rejects(client.submitReview(input()), error => error.status === 409);
});
for (const mutate of [r => ({ ...r, persisted: false }), r => ({ ...r, documentId: "OTHER" }), r => ({ ...r, reviewId: "" }),
  r => ({ ...r, auditor: "" }), r => ({ ...r, reviewedAt: "ayer" }), r => ({ ...r, decision: "reject" }), r => ({ ...r, observation: "OTHER" })]) {
  test("recibo insuficiente no anuncia persistencia: " + mutate.toString(), async () => {
    const client = createClient({ approvedAdapter: adapter({ submitReview: async () => mutate(receipt()) }) });
    await assert.rejects(client.submitReview(input()), error => error.uncertain === true);
  });
}
for (const error of [Error("PRIVATE"), new ReviewApiError("PRIVATE", 503)]) {
  test("fallo durante envío queda incierto sin exponer errores privados: " + error.name, async () => {
    const client = createClient({ approvedAdapter: adapter({ submitReview: async () => { throw error; } }) });
    await assert.rejects(client.submitReview(input()), e => e.uncertain && !e.message.includes("PRIVATE"));
  });
}
test("timeout del adaptador es incierto y señaliza abort; sin reintento automático", async () => {
  let calls = 0, aborted = false;
  const client = createClient({ timeoutMs: 5, approvedAdapter: adapter({ submitReview: (_, { signal }) => {
    calls++; signal.addEventListener("abort", () => { aborted = true; }); return new Promise(() => {});
  } }) });
  await assert.rejects(client.submitReview(input()), e => e.uncertain);
  assert.equal(calls, 1); assert.equal(aborted, true);
  await assert.rejects(client.submitReview(input()), e => e.uncertain);
  assert.equal(calls, 1);
});
test("errores definitivos del adaptador conservan 422 sin marcar persistencia", async () => {
  const client = createClient({ approvedAdapter: adapter({ submitReview: async () => { throw new ReviewApiError("No válido", 422); } }) });
  await assert.rejects(client.submitReview(input()), e => e.status === 422 && !e.uncertain);
});
test("historial muestra solo respuesta normalizada válida del adaptador aprobado", async () => {
  const client = createClient({ approvedAdapter: adapter({ getReviewHistory: async id => ({ documentId: id, entries: [receipt()] }) }) });
  assert.equal((await client.getReviewHistory(input().documentId))[0].reviewId, "TEST-REVIEW-1");
});
for (const result of [null, { documentId: "OTHER", entries: [] }, { documentId: input().documentId, entries: [{}] }]) {
  test("historial inválido no se sustituye por registros locales: " + JSON.stringify(result), async () => {
    const client = createClient({ approvedAdapter: adapter({ getReviewHistory: async () => result }) });
    await assert.rejects(client.getReviewHistory(input().documentId), /no cumple la interfaz/);
  });
}
