const test = require("node:test");
const assert = require("node:assert/strict");
const { getDocuments } = require("../src/assets/js/documents-api.js");
const { getOriginal, createFileViewer, DocumentsApiError } = require("../src/assets/js/documents-api.js");
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

test('original usa GET autenticado, Content-Type real y no necesita Content-Disposition', async () => {
  for (const mime of ['image/jpeg', 'image/png', 'application/pdf', 'text/plain']) {
    const result = await getOriginal('DOC-TEST', { baseUrl: 'https://api.example.test', fetchImpl: async (url, options) => {
      assert.equal(url, 'https://api.example.test/api/documents/DOC-TEST/original');
      assert.equal(options.credentials, 'include'); assert.equal(options.cache, 'no-store');
      assert.equal(options.method, 'GET'); assert.equal(options.headers.Authorization, undefined);
      return { ok: true, status: 200, headers: { get(name) { assert.equal(name, 'Content-Type'); return mime + '; charset=utf-8'; } }, blob: async () => new Blob(['synthetic-bytes']) };
    } });
    assert.equal(result.mime, mime); assert.equal(result.blob.type, mime);
  }
});
test('original rechaza 401, 403, 404 y HTML sin interpretar cuerpos ni sustituir errores por datos', async () => {
  for (const status of [401, 403, 404]) {
    await assert.rejects(getOriginal('DOC-TEST', { baseUrl: 'https://api.example.test', fetchImpl: async () => ({
      ok: false, status, blob: () => assert.fail('No leer cuerpo privado'),
    }) }), error => error instanceof DocumentsApiError && error.status === status);
  }
  await assert.rejects(getOriginal('DOC-TEST', { baseUrl: 'https://api.example.test', fetchImpl: async () => ({
    ok: true, status: 200, headers: new Headers({ 'Content-Type': 'text/html' }), blob: () => assert.fail(),
  }) }), /formato/);
});
test('original vacío, error de red y timeout no permiten mostrar datos ni filtran detalles privados', async () => {
  const baseUrl = 'https://api.example.test';
  await assert.rejects(getOriginal('DOC-TEST', { baseUrl, fetchImpl: async () => ({
    ok: true, status: 200, headers: new Headers({ 'Content-Type': 'image/png' }), blob: async () => new Blob([]),
  }) }), /vacío/);
  await assert.rejects(getOriginal('DOC-TEST', { baseUrl, fetchImpl: async () => { throw Error('PRIVATE'); } }),
    error => error instanceof DocumentsApiError && !error.message.includes('PRIVATE'));
  await assert.rejects(getOriginal('DOC-TEST', { baseUrl, timeoutMs: 5,
    fetchImpl: (_, { signal }) => new Promise((_, reject) => signal.addEventListener('abort', () => reject(Error('PRIVATE')))),
  }), /tiempo de espera/);
});
test('visor mantiene TXT como texto, cambia formatos y libera todos los Blob URL', async () => {
  const elements = new Map(), revoked = [], created = [];
  const originalCreate = URL.createObjectURL, originalRevoke = URL.revokeObjectURL;
  URL.createObjectURL = () => { const value = 'blob:synthetic-' + created.length; created.push(value); return value; };
  URL.revokeObjectURL = value => revoked.push(value);
  const doc = { querySelector(id) {
    if (!elements.has(id)) elements.set(id, { hidden: true, textContent: '', innerHTML: '', removeAttribute(name) { delete this[name]; } });
    return elements.get(id);
  } };
  const $ = name => doc.querySelector('#test' + name);
  try {
    const viewer = createFileViewer(doc, 'test');
    await viewer.show({ mime: 'text/plain', blob: new Blob(['<script>PRIVATE</script>']) });
    assert.equal($('Text').textContent, '<script>PRIVATE</script>'); assert.equal($('Text').innerHTML, '');
    const image = viewer.show({ mime: 'image/png', blob: new Blob(['synthetic-image']) });
    assert.equal($('Text').textContent, ''); $('Image').onload(); assert.equal(await image, true);
    assert.equal($('Image').hidden, false);
    const pdf = viewer.show({ mime: 'application/pdf', blob: new Blob(['%PDF-synthetic']) });
    assert.equal($('Image').hidden, true);
    // La apertura alternativa permite comparar PDF si el visor nativo del frame no está disponible.
    $('Link').onclick(); assert.equal(await pdf, true);
    viewer.clear(); assert.equal($('Pdf').hidden, true); assert.equal($('Link').href, undefined); assert.equal($('Link').onclick, null);
    assert.deepEqual(revoked, created);
    let finish;
    const text = viewer.show({ mime: 'text/plain', blob: { size: 1, slice: () => ({ text: () => new Promise(resolve => { finish = resolve; }) }) } });
    viewer.clear(); finish('OLD'); assert.equal(await text, false); assert.equal($('Text').textContent, '');
  } finally { URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke; }
});
