const test = require("node:test");
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
require("../src/assets/js/documents-api.js");
const { createClient, ReviewApiError } = require("../src/assets/js/reviews-api.js");
const { createAdapter } = require("../src/assets/js/review-http-adapter.js");
const principal = { login: "test-auditor", canReview: true };
const record = overrides => ({ documento_id: "DOC-SYNTHETIC", review_id: "REV-SYNTHETIC-1", review_status: "aprobado", reviewer_id: "test-auditor", observacion: null, reviewed_at: "2026-10-23T12:00:00Z", ...overrides });
const input = overrides => ({ documentId: "DOC-SYNTHETIC", decision: "approve", reviewerId: "test-auditor", observation: "", ...overrides });
const response = data => ({ ok: true, status: 200, json: async () => data });

test("sin aprobación explícita del equipo se permiten lecturas y se bloquea POST", async () => {
  let calls = 0;
  const adapter = createAdapter({ fetchImpl: async () => { calls++; return response([]); } });
  const client = createClient({ approvedAdapter: adapter });
  assert.equal(client.capabilities.submit, false); assert.equal(client.capabilities.history, true);
  assert.deepEqual(await client.listPending(), []);
  await assert.rejects(adapter.submitReview(input()), error => error.status === 403);
  assert.equal(calls, 1);
});
test("aprobar el contrato no concede identidad ni permiso de auditor", async () => {
  for (const authenticatedUser of [null, { login: "synthetic-reader", canReview: false }]) {
    const adapter = createAdapter({ decisionApproved: true, authenticatedUser, fetchImpl: () => assert.fail("No debe iniciar HTTP") });
    await assert.rejects(adapter.submitReview(input()), e => e.status === (authenticatedUser ? 403 : 401));
  }
});
test("no permite sustituir la identidad autenticada por otro reviewer_id", async () => {
  const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, fetchImpl: () => assert.fail("No debe iniciar HTTP") });
  await assert.rejects(adapter.submitReview(input({ reviewerId: "other-auditor" })), e => e.status === 403);
});

test("adaptador envía solo los cuatro campos contractuales y valida el recibo de seis campos", async () => {
  const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, baseUrl: "http://localhost:8000", fetchImpl: async (url, options) => {
    assert.equal(url, "http://localhost:8000/api/documents/DOC-SYNTHETIC/review");
    assert.equal(options.method, "POST"); assert.equal(options.redirect, "error");
    assert.deepEqual(JSON.parse(options.body), { decision: "aprobado", reviewer_id: "test-auditor", observacion: null, expected_review_status: "pendiente" });
    return response(record());
  } });
  const result = await adapter.submitReview(input());
  assert.equal(result.persisted, true); assert.equal(result.auditor, "test-auditor"); assert.equal(result.observation, "");
});
for (const invalid of [input({ documentId: "../secret" }), input({ reviewerId: " " }), input({ decision: "reject", observation: " " })]) {
  test("entrada inválida no realiza HTTP: " + JSON.stringify(invalid), async () => {
    await assert.rejects(createAdapter({ decisionApproved: true, authenticatedUser: principal, fetchImpl: () => assert.fail() }).submitReview(invalid), e => e.status === 422);
  });
}
for (const bad of [record({ extra: "not allowed" }), record({ documento_id: "OTHER" }), record({ reviewer_id: "other-auditor" }),
  record({ reviewed_at: "2026-10-23T12:00:00+01:00" }), record({ review_status: "rechazado", observacion: "OTHER" }), record({ review_id: "INVALID" })]) {
  test("confirmación incompatible se trata como incierta: " + JSON.stringify(bad), async () => {
    await assert.rejects(createAdapter({ decisionApproved: true, authenticatedUser: principal, fetchImpl: async () => response(bad) }).submitReview(input()), e => e.uncertain);
  });
}
for (const status of [400, 401, 403, 404, 409, 422, 500, 502, 504]) {
  test("HTTP " + status + " no imprime cuerpos privados", async () => {
    const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, fetchImpl: async () => ({ ok: false, status, json: () => assert.fail() }) });
    await assert.rejects(adapter.listPending(), e => e.status === status && !e.message.includes("PRIVATE"));
  });
}
test("listado e historial usan rutas de revisión y observación nullable", async () => {
  const calls = [];
  const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, fetchImpl: async url => { calls.push(url); return response(url.endsWith("review-history") ? [record()] : []); } });
  assert.deepEqual(await adapter.listPending(), []);
  const history = await adapter.getReviewHistory("DOC-SYNTHETIC"); assert.equal(history.entries[0].observation, "");
  assert.ok(calls[0].endsWith("/api/reviews/pending")); assert.ok(calls[1].endsWith("/api/documents/DOC-SYNTHETIC/review-history"));
});
test("timeout de fetch aborta y no permite repetir un POST incierto", async () => {
  let calls = 0;
  const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, timeoutMs: 5, fetchImpl: (_, { signal }) => { calls++; return new Promise((_, reject) => signal.addEventListener("abort", () => reject(Error("PRIVATE")))); } });
  const client = createClient({ approvedAdapter: adapter });
  await assert.rejects(client.submitReview(input()), e => e.uncertain);
  await assert.rejects(client.submitReview(input()), e => e.uncertain); assert.equal(calls, 1);
});
test("integración HTTP local: frontend → FastAPI → gestor real de Brando → SDK simulado", { timeout: 30000 }, async t => {
  const backend = path.resolve(__dirname, "../../backend");
  const python = process.env.MEDIFLOW_TEST_PYTHON || path.join(backend, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  assert.ok(fs.existsSync(python), "Configura MEDIFLOW_TEST_PYTHON con las dependencias del backend");
  const child = spawn(python, [path.join(__dirname, "support/review-api-server.py")], { cwd: backend, windowsHide: true, stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, RUN_OCI_INTEGRATION: "0", PYTHONDONTWRITEBYTECODE: "1" } });
  t.after(() => child.kill());
  let stderr = ""; child.stderr.on("data", chunk => { stderr += chunk.toString(); });
  const port = await new Promise((resolve, reject) => {
    let text = ""; const timer = setTimeout(() => reject(Error("No arrancó el servidor sintético: " + stderr)), 15000);
    child.once("error", error => { clearTimeout(timer); reject(error); });
    child.once("exit", () => { clearTimeout(timer); reject(Error("Servidor terminó antes de estar listo: " + stderr)); });
    child.stdout.on("data", chunk => { text += chunk.toString(); if (text.includes("\n")) { clearTimeout(timer); resolve(JSON.parse(text.split("\n")[0]).port); } });
  });
  const baseUrl = `http://127.0.0.1:${port}`;
  for (let i = 0; ; i++) {
    try { if ((await fetch(baseUrl)).ok) break; } catch (_) { /* Esperar únicamente al servidor local de prueba. */ }
    if (i >= 60) assert.fail("No inició FastAPI: " + stderr);
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  const adapter = createAdapter({ decisionApproved: true, authenticatedUser: principal, baseUrl }); const client = createClient({ approvedAdapter: adapter, requestOptions: { baseUrl } });
  assert.equal((await client.listPending()).length, 2);
  for (const [documentId, decision] of [["DOC-SYNTHETIC-APPROVE", "approve"], ["DOC-SYNTHETIC-REJECT", "reject"]]) {
    const before = await client.getDocument(documentId);
    const result = await client.submitReview(input({ documentId, decision, observation: decision === "reject" ? "Caso sintético insuficiente" : "" }));
    assert.equal(result.persisted, true); assert.equal(result.decision, decision);
    const history = await client.getReviewHistory(documentId); assert.equal(history.length, 1); assert.equal(history[0].reviewId, result.reviewId);
    assert.deepEqual(await client.getDocument(documentId), before); assert.equal(before.clasificacion.nivel_prioridad, "Urgente");
    await assert.rejects(adapter.submitReview(input({ documentId, decision, observation: "otro intento sintético" })), e => e.status === 409);
  }
  assert.deepEqual(await client.listPending(), []);
  const invalid = await fetch(baseUrl + "/api/documents/DOC-SYNTHETIC/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: "aprobado", reviewer_id: "synthetic" }) });
  assert.equal(invalid.status, 422);
  assert.equal((await fetch(baseUrl + "/api/auditoria/revision", { method: "POST" })).status, 404);
});
