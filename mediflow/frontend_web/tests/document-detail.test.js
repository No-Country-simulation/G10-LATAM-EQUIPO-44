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

function view(loadDocument, options = {}) {
  const handlers = {};
  const dialog = { open: false, attrs: {}, addEventListener: (name, cb) => handlers[name] = cb,
    setAttribute(name, value) { this.attrs[name] = value; },
    showModal() { this.open = true; }, close() { this.open = false; handlers.close(); } };
  const status = { dataset: {}, textContent: "" }, json = { textContent: "OLD-LIST-DATA" };
  return { dialog, status, json, controller: createDetail({ dialog, status, json, loadDocument, ...options }) };
}
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; };

// Agregado por Edil: el resumen y el visor reutilizan el GET autorizado, sin
// duplicar consultas ni conservar el original de otro documento.
function originalControls(loadOriginal) {
  const handlers = {}, shown = [];
  const originalButton = { hidden: true, disabled: true, addEventListener: (name, fn) => handlers[name] = fn };
  const originalStatus = { textContent: "", dataset: {} }, summary = { textContent: "" };
  let clears = 0;
  const originalViewer = { clear: () => clears++, show: async file => { shown.push(file); return true; } };
  return { options: { originalButton, originalStatus, summary, originalViewer, loadOriginal },
    originalButton, originalStatus, summary, shown, handlers, clearCount: () => clears };
}

test("resumen usa texto del documento real y original solo se consulta una vez al pedirlo", async () => {
  const request = deferred(), doc = sample(); let calls = 0;
  doc.datos_extraidos.paciente.nombre = "<script>texto no confiable</script>";
  const controls = originalControls(id => { calls++; assert.equal(id, doc.documento_id); return request.promise; });
  const v = view(() => doc, controls.options);
  await v.controller.open(doc.documento_id);
  assert.equal(calls, 0); assert.equal(controls.originalButton.hidden, false);
  assert.match(controls.summary.textContent, /<script>texto no confiable<\/script>/);
  assert.match(controls.summary.textContent, /no mide seguridad clínica/);
  const first = v.controller.showOriginal(), second = v.controller.showOriginal();
  assert.equal(first, second); assert.equal(controls.originalButton.disabled, true);
  request.resolve({ blob: new Blob(["Documento sintético"]), mime: "text/plain" }); await first;
  assert.equal(calls, 1); assert.equal(controls.shown.length, 1);
  assert.equal(controls.originalStatus.dataset.state, "ready");
  assert.equal(controls.originalButton.disabled, false);
});

test("cambiar ID aborta el original y descarta su respuesta tardía; cerrar limpia visor", async () => {
  const request = deferred(); let signal;
  const controls = originalControls((id, options) => { signal = options.signal; return request.promise; });
  const v = view(id => ({ ...sample(), documento_id: id }), controls.options);
  await v.controller.open("DOC-A");
  const task = v.controller.showOriginal(); await Promise.resolve();
  await v.controller.open("DOC-B"); assert.equal(signal.aborted, true);
  request.resolve({ blob: new Blob(["Documento anterior"]), mime: "text/plain" }); await task;
  assert.equal(controls.shown.length, 0);
  assert.match(controls.summary.textContent, /DOC-B/);
  assert.equal(controls.originalStatus.textContent, "");
  const previousClears = controls.clearCount(); v.dialog.close();
  assert.ok(controls.clearCount() > previousClears);
  assert.equal(controls.summary.textContent, ""); assert.equal(controls.originalButton.hidden, true);
});

for (const code of [401, 403, 404, null]) {
  test("fallo de original " + code + " conserva análisis y no revela mensajes privados", async () => {
    const controls = originalControls(() => {
      if (code) throw new api.DocumentsApiError("Original no disponible (HTTP " + code + ").", code);
      throw Error("private-token");
    });
    const v = view(sample, controls.options); await v.controller.open("DOC-X");
    const json = v.json.textContent; await v.controller.showOriginal();
    assert.equal(v.json.textContent, json); assert.equal(controls.shown.length, 0);
    assert.equal(controls.originalStatus.dataset.state, "error");
    assert.equal(controls.originalButton.disabled, false);
    assert.doesNotMatch(controls.originalStatus.textContent, /private-token/);
  });
}

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

for (const { demo, listFailure } of [{ demo: false }, { demo: true }, { demo: false, listFailure: true }]) {
  test("historial usa API real; demo=" + demo + "; error de listado=" + !!listFailure, async () => {
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
      MediFlowDocumentsApi: { ...api,
        getDocuments: async () => {
          listCalls++;
          if (listFailure) throw new api.DocumentsApiError("No se pudo consultar el historial.", 503);
          return [listed];
        },
        getDocument: async id => { detailCalls++; assert.equal(id, listed.documento_id); return current; }
      }
    };
    const document = { querySelector: element, querySelectorAll: () => [],
      body: { dataset: { screen: "historial" } }, readyState: "loading",
      addEventListener: (type, fn) => documentListeners[type] = fn };
    vm.runInNewContext(fs.readFileSync(require.resolve("../src/historial/app.js"), "utf8"), { window, document, URLSearchParams, Intl });
    documentListeners.DOMContentLoaded();
    await new Promise(resolve => setImmediate(resolve));
    if (listFailure) {
      assert.equal(listCalls, 1); assert.equal(detailCalls, 0);
      assert.equal(element("#documentLoadStatus").dataset.state, "error");
      for (const id of ["historyTotal", "historyProcessed", "historyAudit", "historyUrgent"]) {
        assert.equal(element("#" + id).textContent, "—");
      }
      assert.equal(element("#tbodyHist").innerHTML, "");
      return;
    }
    assert.equal(element("#historyTotal").textContent, "1");
    assert.equal(element("#historyProcessed").textContent, "1");
    assert.equal(element("#historyAudit").textContent, "0");
    assert.equal(element("#historyUrgent").textContent, "0");
    const listBefore = element("#tbodyHist").innerHTML;
    const click = { target: { closest: selector => selector === "[data-document]" ? { dataset: { document: listed.documento_id } } : null } };
    listeners["#tbodyHist:click"](click);
    listeners["#tbodyHist:click"](click);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(listCalls, 1);
    assert.equal(detailCalls, 1);
    assert.equal(JSON.parse(element("#documentDetailJson").textContent).status, current.status);
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

// Agregado por Edil: bandejas sobre fixtures de API, nunca datos de producción.
async function routingHistoryView(source, { search = "", fail = false } = {}) {
  const elements = new Map(), listeners = {}, events = {}, calls = { list: 0, detail: 0 };
  const element = selector => {
    if (!elements.has(selector)) elements.set(selector, {
      attrs: {}, dataset: {}, textContent: "", value: "", open: false,
      addEventListener(type, fn) { listeners[selector + ":" + type] = fn; },
      classList: { toggle() {} }, setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute() {},
      showModal() { this.open = true; }, scrollIntoView() {}, focus() {}, select() {}
    });
    return elements.get(selector);
  };
  const window = { location: { search, pathname: "/historial/index.html" },
    history: { replaceState(_a, _b, url) { window.location.search = url.startsWith("?") ? url : ""; } },
    addEventListener(type, fn) { events[type] = fn; }, setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
    MediFlowDocumentDetail: { createDetail },
    MediFlowDocumentsApi: { ...api,
      getDocuments: async () => { calls.list++; if (fail) throw new api.DocumentsApiError("Consulta no disponible", 503); return source; },
      getDocument: async id => { calls.detail++; return source.find(doc => doc.documento_id === id); }
    }
  };
  const document = { querySelector: element, querySelectorAll: () => [], body: { dataset: { screen: "historial" } },
    readyState: "loading", addEventListener(type, fn) { events[type] = fn; } };
  vm.runInNewContext(fs.readFileSync(require.resolve("../src/historial/app.js"), "utf8"), { window, document, URLSearchParams, Intl });
  events.DOMContentLoaded();
  const loadingCount = element("#tray-count-todos").textContent;
  await new Promise(resolve => setImmediate(resolve));
  function tray(key) { listeners["#destinationTrays:click"]({ target: { closest: () => ({ dataset: { tray: key }, disabled: false }) } }); }
  function change(selector, value) { element(selector).value = value; listeners[selector + ":change"]({ target: element(selector) }); }
  return { element, listeners, events, calls, window, tray, change, loadingCount };
}
function routedDocument(id, status, destination, priority = "Rutina") {
  const doc = sample(); doc.documento_id = id; doc.status = status;
  doc.clasificacion.nivel_prioridad = priority;
  doc.decision_enrutamiento.destino_principal = destination;
  doc.decision_enrutamiento.requiere_auditoria_humana = status === "auditoria_humana";
  return doc;
}

test("bandejas clasifican por destino, priorizan recepción y conservan Urgente en auditoría", async () => {
  const rows = [
    routedDocument("DOC-URG", "procesado", "Cola_Emergencia_Medica", "Urgente"),
    routedDocument("DOC-FAR", "procesado", "Cola_Farmacia"),
    routedDocument("DOC-HIS", "procesado", "Cola_Historia_Clinica"),
    routedDocument("DOC-AUD", "auditoria_humana", "Cola_Revision_Humana", "Urgente"),
    routedDocument("DOC-REC", "recibido", "Cola_Farmacia"),
    routedDocument("DOC-INI", "recibido", "Cola_Procesamiento_Inicial"),
    routedDocument("DOC-OTR", "procesado", "<script>destino-desconocido</script>")
  ];
  const before = structuredClone(rows), v = await routingHistoryView(rows);
  assert.equal(v.loadingCount, "—");
  for (const [tray, count] of Object.entries({ todos: 7, urgencias: 1, farmacia: 1, historia: 1, auditoria: 1, recibidos: 2, otros: 1 })) {
    assert.equal(v.element("#tray-count-" + tray).textContent, String(count));
  }
  for (const [tray, ids] of Object.entries({ urgencias: ["DOC-URG"], farmacia: ["DOC-FAR"], historia: ["DOC-HIS"], auditoria: ["DOC-AUD"], recibidos: ["DOC-REC", "DOC-INI"], otros: ["DOC-OTR"] })) {
    v.tray(tray);
    const html = v.element("#tbodyHist").innerHTML;
    for (const doc of rows) assert.equal(html.includes('data-document="' + doc.documento_id + '"'), ids.includes(doc.documento_id));
    assert.equal(v.element("#tray-" + tray).attrs["aria-pressed"], "true");
    if (tray === "recibidos") { assert.match(html, /Pendiente de procesamiento/); assert.match(html, /Ver recepción/); assert.doesNotMatch(html, /Rutina|Ver análisis/); }
    if (tray === "auditoria") assert.match(html, /Urgente/);
    if (tray === "otros") { assert.match(html, /Otros destinos/); assert.match(html, /&lt;script&gt;/); assert.doesNotMatch(html, /<script>/); }
  }
  assert.equal(v.calls.list, 1); assert.equal(v.calls.detail, 0);
  assert.deepEqual(rows, before);
  v.tray("farmacia"); v.change("#selMts", "urgente");
  assert.equal(v.element("#tbodyHist").innerHTML, ""); assert.equal(v.element("#vacio").hidden, false);
  assert.equal(v.element("#tray-count-farmacia").textContent, "1");
  v.change("#selMts", "todos"); v.change("#selEstado", "auditoria");
  assert.equal(v.element("#tbodyHist").innerHTML, "");
  v.listeners["#btnLimpiarVacio:click"]();
  assert.equal(v.element("#tray-todos").attrs["aria-pressed"], "true");
  assert.equal(v.element("#tray-count-todos").textContent, "7");
});

test("bandeja conserva filtros, paginación, enlace y detalle sin repetir consultas del listado", async () => {
  const docs = Array.from({ length: 12 }, (_, i) => routedDocument("DOC-FAR-" + i, "procesado", "Cola_Farmacia"));
  const v = await routingHistoryView(docs, { search: "?bandeja=farmacia&por=10" });
  assert.equal((v.element("#tbodyHist").innerHTML.match(/data-document=/g) || []).length, 10);
  v.listeners["#btnNext:click"]();
  assert.equal((v.element("#tbodyHist").innerHTML.match(/data-document=/g) || []).length, 2);
  assert.equal(v.element("#tray-count-farmacia").textContent, "12");
  assert.match(v.window.location.search, /bandeja=farmacia/); assert.match(v.window.location.search, /pagina=2/);
  v.tray("historia");
  assert.equal(v.element("#tbodyHist").innerHTML, ""); assert.doesNotMatch(v.window.location.search, /pagina=2/);
  v.tray("farmacia");
  v.element("#qHist").value = "DOC-FAR-11";
  v.listeners["#qHist:input"]({ target: v.element("#qHist") });
  assert.equal((v.element("#tbodyHist").innerHTML.match(/data-document=/g) || []).length, 1);
  v.listeners["#tbodyHist:click"]({ target: { closest: selector => selector === "[data-document]" ? { dataset: { document: "DOC-FAR-11" } } : null } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(v.calls.detail, 1); assert.equal(v.calls.list, 1);
  assert.equal(JSON.parse(v.element("#documentDetailJson").textContent).documento_id, "DOC-FAR-11");
  v.window.location.search = ""; v.events.popstate();
  assert.equal(v.element("#tray-todos").attrs["aria-pressed"], "true");
  assert.equal(v.element("#qHist").value, "");
  assert.equal((v.element("#tbodyHist").innerHTML.match(/data-document=/g) || []).length, 10);
});

for (const fail of [false, true]) {
  test("bandejas vacías y error no inventan cantidades; error=" + fail, async () => {
    const v = await routingHistoryView([], { fail, search: "?bandeja=desconocida" });
    for (const key of ["todos", "urgencias", "farmacia", "historia", "auditoria", "recibidos", "otros"]) {
      assert.equal(v.element("#tray-count-" + key).textContent, fail ? "—" : "0");
    }
    assert.equal(v.element("#tray-todos").attrs["aria-pressed"], "true");
    assert.equal(v.element("#tray-otros").hidden, true);
    assert.equal(v.element("#documentLoadStatus").dataset.state, fail ? "error" : "success");
    assert.equal(v.element("#tbodyHist").innerHTML, "");
    assert.equal(v.calls.list, 1);
  });
}
