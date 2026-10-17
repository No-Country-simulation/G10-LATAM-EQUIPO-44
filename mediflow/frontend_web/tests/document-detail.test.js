const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const vm = require("node:vm");
const api = require("../src/assets/js/documents-api.js");
const { createDetail } = require("../src/assets/js/document-detail.js");
const { documents } = require("../src/assets/js/documents-mock.js");
const sample = () => structuredClone(documents[1]);
const response = doc => ({ ok: true, json: async () => doc });

test("GET individual usa ID real codificado y no agrega limit", async () => {
  const doc = sample(); doc.documento_id = "DOC /?á#%";
  let calls = 0;
  const result = await api.getDocument(doc.documento_id, { baseUrl: "http://localhost:8000", fetchImpl: async (url, options) => {
    calls++;
    assert.equal(url.pathname, "/api/documents/" + encodeURIComponent(doc.documento_id));
    assert.equal(url.search, "");
    assert.equal(options.method, "GET");
    assert.equal(options.headers.Accept, "application/json");
    return response(doc);
  }});
  assert.equal(calls, 1);
  assert.deepEqual(result, doc);
});

test("404 conserva estado inexistente sin exponer respuesta privada", async () => {
  await assert.rejects(api.getDocument("DOC-MISSING", { fetchImpl: async () => ({ ok: false, status: 404, json: () => { throw Error("private"); } }) }),
    error => error.status === 404 && /no existe/.test(error.message) && !error.message.includes("private"));
});

test("HTTP 503 no devuelve datos del listado ni mocks", async () => {
  await assert.rejects(api.getDocument("DOC-X", { fetchImpl: async () => ({ ok: false, status: 503 }) }), /HTTP 503/);
});

for (const id of [undefined, null, "", " ", 23, ".", ".."]) {
  test("ID inválido se rechaza antes de fetch: " + String(id), async () => {
    await assert.rejects(api.getDocument(id, { fetchImpl: () => { assert.fail("no fetch"); } }), /identificador/);
  });
}

for (const [name, mutate] of [
  ["lista", () => []], ["null", () => null], ["error JSON", () => ({ detail: "private" })],
  ["ID distinto", d => ({ ...d, documento_id: "DOC-OTHER" })],
  ["estado inválido", d => ({ ...d, status: "inventado" })],
  ["score booleano", d => { d.clasificacion.score_confianza_clasificacion = true; return d; }],
  ["score fuera de rango", d => { d.clasificacion.score_confianza_clasificacion = 2; return d; }],
  ["medicación inválida", d => { d.datos_extraidos.medicamentos_recetados = [null]; return d; }],
  ["sin decisión", d => { delete d.decision_enrutamiento; return d; }],
]) {
  test("respuesta individual inválida: " + name, async () => {
    const doc = sample();
    await assert.rejects(api.getDocument(doc.documento_id, { fetchImpl: async () => response(mutate(doc)) }), /documento invalido/);
  });
}

test("JSON malformado es error controlado", async () => {
  await assert.rejects(api.getDocument("DOC-X", { fetchImpl: async () => ({ ok: true, json: async () => { throw Error("private"); } }) }), /documento invalido/);
});

test("red y timeout del detalle no exponen mensajes privados", async () => {
  await assert.rejects(api.getDocument("DOC-X", { fetchImpl: async () => { throw Error("private"); } }), e => /backend/.test(e.message) && !e.message.includes("private"));
  await assert.rejects(api.getDocument("DOC-X", { timeoutMs: 5, fetchImpl: (_, { signal }) => new Promise((_, reject) => {
    signal.addEventListener("abort", () => reject(Error("private")));
  }) }), /tiempo de espera/);
});

function view(loadDocument) {
  const handlers = {};
  const dialog = { open: false, attrs: {}, addEventListener: (name, cb) => handlers[name] = cb,
    setAttribute(name, value) { this.attrs[name] = value; },
    showModal() { this.open = true; }, close() { this.open = false; handlers.close(); } };
  const status = { dataset: {}, textContent: "" }, json = { textContent: "OLD-LIST-DATA" };
  return { dialog, status, json, controller: createDetail({ dialog, status, json, loadDocument }) };
}
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; };

test("diálogo muestra carga, una consulta por apertura y respuesta individual actualizada", async () => {
  const request = deferred(); let calls = 0;
  const v = view(id => { calls++; assert.equal(id, "DOC-X"); return request.promise; });
  const task = v.controller.open("DOC-X");
  assert.equal(v.status.dataset.state, "loading");
  assert.equal(v.json.textContent, "");
  assert.equal(v.dialog.attrs["aria-busy"], "true");
  assert.equal(v.controller.open("DOC-X"), task);
  const doc = sample(); doc.documento_id = "DOC-X"; doc.status = "auditoria_humana";
  request.resolve(doc); await task;
  assert.equal(calls, 1);
  assert.deepEqual(JSON.parse(v.json.textContent), doc);
  assert.equal(v.status.dataset.state, "ready");
  assert.equal(v.dialog.attrs["aria-busy"], "false");
  await v.controller.open("DOC-X"); assert.equal(calls, 1);
  v.dialog.close(); await v.controller.open("DOC-X"); assert.equal(calls, 2);
});

test("cerrar y reabrir durante carga reutiliza solicitud y descarta resultado anterior", async () => {
  const request = deferred(); let calls = 0;
  const v = view(() => { calls++; return request.promise; });
  const first = v.controller.open("DOC-X");
  v.dialog.close(); const second = v.controller.open("DOC-X");
  request.resolve(sample()); await Promise.all([first, second]);
  assert.equal(calls, 1); assert.equal(v.status.dataset.state, "ready");
});

test("cambiar documento o cerrar impide que una respuesta tardía sobrescriba el detalle", async () => {
  const requests = { A: deferred(), B: deferred() };
  const v = view(id => requests[id].promise);
  const a = v.controller.open("A"), b = v.controller.open("B");
  requests.B.resolve({ documento_id: "B" }); await b;
  requests.A.resolve({ documento_id: "A" }); await a;
  assert.equal(JSON.parse(v.json.textContent).documento_id, "B");
  v.dialog.close();
  const c = v.controller.open("A"); v.dialog.close(); await c;
  assert.equal(v.json.textContent, "");
});

for (const [name, error, expected] of [
  ["404", new api.DocumentsApiError("No existe", 404), "not-found"],
  ["inválido", new api.DocumentsApiError("Documento invalido"), "error"],
  ["red", Error("private-token"), "error"],
]) {
  test("diálogo conserva error " + name + " y permite nueva consulta al reabrir", async () => {
    let fail = true;
    const v = view(() => { if (fail) throw error; return sample(); });
    await v.controller.open("DOC-X");
    assert.equal(v.status.dataset.state, expected);
    assert.equal(v.json.textContent, "");
    assert.ok(!v.status.textContent.includes("private"));
    fail = false; v.dialog.close(); await v.controller.open("DOC-X");
    assert.equal(v.status.dataset.state, "ready");
  });
}

for (const demo of [false, true]) {
  test("historial abre ID real y conserva listado; demo=" + demo, async () => {
    const elements = new Map(), listeners = {}, documentListeners = {};
    const element = selector => {
      if (!elements.has(selector)) elements.set(selector, {
        addEventListener: (type, fn) => listeners[selector + ":" + type] = fn,
        classList: { toggle() {} }, setAttribute() {}, removeAttribute() {},
        dataset: {}, textContent: "", value: "", open: false,
        showModal() { this.open = true; }
      });
      return elements.get(selector);
    };
    let detailCalls = 0, listCalls = 0;
    const listed = sample(), current = sample();
    current.status = "auditoria_humana";
    const window = {
      location: { search: demo ? "?demo=1" : "", pathname: "/historial/" },
      history: { replaceState() {} }, addEventListener() {},
      MediFlowDocumentDetail: { createDetail },
      MediFlowDocuments: { ...require("../src/assets/js/documents-mock.js"), documents: [listed] },
      MediFlowDocumentsApi: { ...api,
        getDocuments: async () => { listCalls++; return [listed]; },
        getDocument: async id => { detailCalls++; assert.equal(id, listed.documento_id); return current; }
      }
    };
    const document = { querySelector: element, querySelectorAll: () => [],
      body: { dataset: { screen: "historial" } }, readyState: "loading",
      addEventListener: (type, fn) => documentListeners[type] = fn };
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/historial/app.js"), "utf8"), { window, document, URLSearchParams, Intl });
    documentListeners.DOMContentLoaded();
    await new Promise(resolve => setImmediate(resolve));
    const listBefore = element("#tbodyHist").innerHTML;
    const click = { target: { closest: selector => selector === "[data-document]" ? { dataset: { document: listed.documento_id } } : null } };
    listeners["#tbodyHist:click"](click);
    listeners["#tbodyHist:click"](click);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(listCalls, demo ? 0 : 1);
    assert.equal(detailCalls, demo ? 0 : 1);
    assert.equal(JSON.parse(element("#documentDetailJson").textContent).status, demo ? listed.status : current.status);
    assert.equal(element("#documentDetailStatus").dataset.state, "ready");
    assert.equal(element("#tbodyHist").innerHTML, listBefore);
  });
}

test("GET por HTTP real local conserva ID y devuelve el documento individual, sin consultar listado", async t => {
  const calls = [], doc = sample(); doc.documento_id = "DOC-S3-07-SYNTHETIC";
  const server = http.createServer((req, res) => {
    calls.push({ method: req.method, path: req.url });
    res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify(doc));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); });
  const result = await api.getDocument(doc.documento_id, { baseUrl: "http://127.0.0.1:" + server.address().port });
  assert.deepEqual(result, doc);
  assert.deepEqual(calls, [{ method: "GET", path: "/api/documents/DOC-S3-07-SYNTHETIC" }]);
});
