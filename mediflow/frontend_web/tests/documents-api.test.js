const test = require("node:test");
const assert = require("node:assert/strict");
const { getDocuments } = require("../src/assets/js/documents-api.js");
const { toRow, documents } = require("../src/assets/js/documents-mock.js");

test("GET usa API real y adapta el contrato sin inventar fechas", async () => {
  let calls = 0;
  const rows = await getDocuments({ fetchImpl: async (url, options) => {
    calls++;
    assert.equal(url.pathname, "/api/documents");
    assert.equal(url.searchParams.get("limit"), "500");
    assert.equal(options.headers.Accept, "application/json");
    return { ok: true, json: async () => documents };
  }});
  assert.equal(calls, 1);
  assert.equal(toRow(rows[0]).id, documents[0].documento_id);
  assert.equal(toRow(rows[0]).fecha, null);
});
test("un fallo HTTP no se convierte en datos mock", async () => {
  await assert.rejects(getDocuments({ fetchImpl: async () => ({ ok: false, status: 503 }) }), /HTTP 503/);
});
test("rechaza JSON que no sea listado", async () => {
  await assert.rejects(getDocuments({ fetchImpl: async () => ({ ok: true, json: async () => ({ detail: "private" }) }) }), /invalido/);
});
test("no expone errores privados de la red", async () => {
  await assert.rejects(getDocuments({ fetchImpl: async () => { throw Error("private-token"); } }),
    e => !e.message.includes("private"));
});
test("timeout cancela la lectura del backend", async () => {
  await assert.rejects(getDocuments({ timeoutMs: 10, fetchImpl: (_, { signal }) => new Promise((_, reject) => {
    signal.addEventListener("abort", () => reject(Error("private")));
  }) }), /tiempo de espera/);
});
test("rechaza destinos con credenciales embebidas", async () => {
  await assert.rejects(getDocuments({ baseUrl: "http://user:private@localhost:8000" }), /no es valida/);
});
