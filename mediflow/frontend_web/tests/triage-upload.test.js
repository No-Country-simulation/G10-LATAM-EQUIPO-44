const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const api = require('../src/assets/js/triage-api.js');
globalThis.MediFlowTriageApi = api;
const { mount } = require('../src/ingesta/upload.js');
const { documents } = require('../src/assets/js/documents-mock.js');
const baseUrl = 'https://desktop-edilanti.tailf48a22.ts.net:8443';
const fixture = () => structuredClone(documents[0]);
function file(name = 'sintetico.txt', contents = 'Documento ficticio') {
  return new File([contents], name, { type: 'text/plain' });
}
function response(data = fixture(), status = 201, id = null) {
  return { ok: status >= 200 && status < 300, status, headers: new Headers(id ? { 'X-Document-ID': id } : {}), json: async () => data };
}
test('configuración desplegada y local se reutiliza sin duplicar /api', async () => {
  for (const [hostname, expected] of [['desktop-edilanti.tailf48a22.ts.net', baseUrl], ['127.0.0.1', 'http://127.0.0.1:8001']]) {
    const window = { location: { hostname } };
    vm.runInNewContext(fs.readFileSync(require.resolve('../src/assets/js/api-config.js'), 'utf8'), { window });
    assert.equal(window.MEDIFLOW_API_BASE_URL, expected);
  }
  for (const prefix of [baseUrl, baseUrl + '/api/']) {
    await api.createClient({ baseUrl: prefix, fetchImpl: async (url, opts) => {
      assert.equal(url.href, baseUrl + '/api/triage');
      assert.equal(opts.method, 'POST'); assert.equal(opts.credentials, 'include');
      assert.equal(opts.headers['Content-Type'], undefined);
      assert.equal(opts.body.get('analyze'), 'true'); assert.equal(await opts.body.get('file').text(), 'Documento ficticio');
      return response();
    } }).upload(file(), true);
  }
});
test('rechaza archivo vacío, formato, tamaño y falta de consentimiento antes de transmitir', async () => {
  let calls = 0;
  const client = api.createClient({ baseUrl, fetchImpl: () => { calls++; } });
  for (const [f, consent] of [[file('a.exe'), true], [file('a.txt', ''), true], [{ name: 'a.pdf', size: 10485761 }, true], [file(), false]]) {
    await assert.rejects(client.upload(f, consent), api.TriageApiError);
  }
  assert.equal(calls, 0);
});
for (const status of [400, 401, 403, 413, 415, 422, 429, 500, 502, 503, 504]) {
  test('HTTP ' + status + ' no se transforma en resultado simulado ni revela detalle privado', async () => {
    await assert.rejects(api.createClient({ baseUrl, fetchImpl: async () => response({ detail: 'SECRET' }, status) }).upload(file(), true),
      e => e.status === status && !e.message.includes('SECRET') && e.uncertain === (status >= 500 || status === 429));
  });
}
test('fallo de IA conserva X-Document-ID para GET; JSON inválido permanece incierto', async () => {
  const id = 'DOC-CLIN-ABC123';
  await assert.rejects(api.createClient({ baseUrl, fetchImpl: async () => response(null, 422, id) }).upload(file(), true), e => e.documentId === id && e.uncertain);
  await assert.rejects(api.createClient({ baseUrl, fetchImpl: async () => response({}) }).upload(file(), true), e => e.uncertain);
});
test('red y timeout no provocan reintentos ni exponen datos privados', async () => {
  let calls = 0;
  await assert.rejects(api.createClient({ baseUrl, fetchImpl: async () => { calls++; throw Error('SECRET'); } }).upload(file(), true), e => e.uncertain && !e.message.includes('SECRET'));
  assert.equal(calls, 1);
  await assert.rejects(api.createClient({ baseUrl, timeoutMs: 5, fetchImpl: (_, { signal }) => new Promise((_, reject) => signal.addEventListener('abort', () => reject(Error()))) }).upload(file(), true), /tiempo de espera/);
});
function view(client, { storage, documents: reads } = {}) {
  const elements = new Map();
  const doc = { querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, { textContent: '', dataset: {}, files: [file()], checked: true, hidden: true,
      setAttribute() {}, addEventListener() {}, reset() {} });
    return elements.get(selector);
  } };
  const memory = new Map();
  storage = storage || { getItem: k => memory.get(k), setItem: (k, v) => memory.set(k, v), removeItem: k => memory.delete(k) };
  const form = mount(doc, { client, storage, documents: reads || { getDocument: async () => fixture() }, originalUrl: id => baseUrl + '/api/documents/' + id + '/original', confirm: () => true });
  return { form, $: s => doc.querySelector(s), storage };
}
test('doble envío se bloquea; resultado urgente conserva revisión y no interpreta HTML', async () => {
  let finish, calls = 0;
  const v = view({ upload: () => { calls++; return new Promise(resolve => { finish = resolve; }); } });
  const first = v.form.submit(); await v.form.submit(); assert.equal(calls, 1);
  const data = fixture(); data.status = 'auditoria_humana'; data.clasificacion.nivel_prioridad = 'Urgente';
  data.decision_enrutamiento.requiere_auditoria_humana = true;
  data.decision_enrutamiento.justificacion_enrutamiento = '<script>ficticio</script>';
  finish(data); await first;
  assert.match(v.$('#uploadResult').textContent, /Urgente/);
  assert.match(v.$('#uploadResult').textContent, /Revisión humana: Requerida/);
  assert.match(v.$('#uploadResult').textContent, /<script>/);
  assert.equal(v.$('#uploadSubmit').disabled, true);
});
test('GET fallido conserva resultado anterior y error incierto sobrevive recarga', async () => {
  const v = view({ upload: async () => fixture() }, { documents: { getDocument: async () => { throw Error('SECRET'); } } });
  await v.form.submit(); const original = v.$('#uploadResult').textContent;
  await v.form.recover(); assert.equal(v.$('#uploadResult').textContent, original);
  const reloaded = view({}, { storage: v.storage }); assert.equal(reloaded.$('#uploadSubmit').disabled, true);
  const unknown = view({ upload: async () => { throw new api.TriageApiError('Sin confirmación', { uncertain: true }); } });
  await unknown.form.submit(); await unknown.form.submit(); assert.equal(unknown.$('#uploadSubmit').disabled, true);
  assert.equal(unknown.$('#uploadRecover').disabled, true);
});
test('consentimiento, errores recuperables y nueva carga conservan controles', async () => {
  let calls = 0;
  const v = view({ upload: async () => { calls++; throw new api.TriageApiError('Formato', { status: 415 }); } });
  v.$('#uploadConsent').checked = false; await v.form.submit(); assert.equal(calls, 0);
  v.$('#uploadConsent').checked = true; await v.form.submit(); assert.equal(calls, 1);
  assert.equal(v.$('#uploadSubmit').disabled, false);
  v.form.reset(); assert.equal(v.$('#uploadResult').hidden, true);
});
test('recepción pendiente no presenta prioridad ni confianza ficticias como análisis', async () => {
  const data = fixture(); data.status = 'recibido';
  const v = view({ upload: async () => data }); await v.form.submit();
  assert.match(v.$('#uploadResult').textContent, /análisis pendiente/);
  assert.doesNotMatch(v.$('#uploadResult').textContent, /Prioridad orientativa|Confianza de clasificación/);
});
test('error con ID habilita GET sin repetir POST; consulta confirma documento recibido', async () => {
  const id = 'DOC-CLIN-ABC123'; let uploads = 0, reads = 0;
  const data = fixture(); data.documento_id = id; data.status = 'recibido';
  const v = view({ upload: async () => { uploads++; throw new api.TriageApiError('IA no disponible', { status: 503, documentId: id, uncertain: true }); } },
    { documents: { getDocument: async actual => { assert.equal(actual, id); reads++; return data; } } });
  await v.form.submit(); assert.equal(v.$('#uploadRecover').disabled, false);
  await v.form.recover(); assert.equal(uploads, 1); assert.equal(reads, 1);
  assert.match(v.$('#uploadResult').textContent, /DOC-CLIN-ABC123/);
  assert.equal(v.$('#uploadSubmit').disabled, true);
});
test('HTML conserva carga real y deja inerte el prototipo sin ejecutar su script', () => {
  const html = fs.readFileSync(require.resolve('../src/ingesta/index.html'), 'utf8');
  assert.ok(html.indexOf('api-config.js') < html.indexOf('triage-api.js'));
  assert.match(html, /type="file"/); assert.match(html, /aria-live="polite"/);
  const active = html.replace(/<template\b[^>]*>[\s\S]*?<\/template>/g, '');
  assert.match(html, /<template id="ingestaLegacyForm">/);
  assert.doesNotMatch(active, /formPaciente|data-toast|Dr\. M\. Vance|HIS Connected|<script src="app\.js"/);
});
test('el ojo abre el original OCI por ID y persiste al recargar, nunca un archivo local', async () => {
  const v = view({ upload: async () => fixture() });
  await v.form.preview(file());
  assert.equal(v.$('#uploadPreviewLink').hidden, true);
  await v.form.submit();
  assert.equal(v.$('#uploadPreviewLink').hidden, false);
  assert.equal(v.$('#uploadPreviewLink').href, baseUrl + '/api/documents/' + fixture().documento_id + '/original');
  const reloaded = view({}, { storage: v.storage });
  assert.match(reloaded.$('#uploadFileInfo').textContent, /sintetico.txt/);
  assert.equal(reloaded.$('#uploadPreviewLink').href, v.$('#uploadPreviewLink').href);
  assert.equal(reloaded.$('#uploadSubmit').disabled, true);
  assert.ok(!v.storage.getItem('mediflow-ingesta-pending-v1').includes('Documento ficticio'));
});
test('sin ID confirmado no se inventa enlace OCI ni se abre explorador', async () => {
  const v = view({ upload: async () => { throw new api.TriageApiError('Timeout', { uncertain: true }); } });
  await v.form.submit();
  assert.equal(v.$('#uploadPreviewLink').hidden, true);
  const html = fs.readFileSync(require.resolve('../src/ingesta/index.html'), 'utf8');
  assert.doesNotMatch(html, /uploadOpenLocal|uploadPreviewFile/);
});
test('URL del original usa servidor configurado y evita duplicar api o referenciar otro origen', () => {
  const { originalUrl } = require('../src/assets/js/documents-api.js');
  assert.equal(originalUrl('DOC-CLIN-ABC123', { baseUrl: baseUrl + '/api/' }), baseUrl + '/api/documents/DOC-CLIN-ABC123/original');
  assert.throws(() => originalUrl('../bad', { baseUrl }));
  assert.throws(() => originalUrl('DOC-1', { baseUrl: 'https://secret:password@other.test' }));
});
 test('vista local compacta y original OCI conservan controles separados', () => {
  const html = fs.readFileSync(require.resolve('../src/ingesta/index.html'), 'utf8');
  assert.match(html, /class="upload-file-row"/);
  assert.match(html, /aria-label="Ver documento en otra pesta/);
  assert.match(html, /id="uploadLocalImage"/);
  assert.match(html, /id="uploadLocalPdf"[^>]*sandbox/);
  assert.match(html, /id="uploadLocalText"/);
});
test('selección y reemplazo muestran TXT seguro, tipo y tamaño sin enviar; reset limpia la copia local', async () => {
  let calls = 0;
  const v = view({ upload: async () => { calls++; return fixture(); } });
  await v.form.preview(file('primero.txt', '<b>Texto clínico sintético</b>'));
  assert.equal(v.$('#uploadLocalText').textContent, '<b>Texto clínico sintético</b>');
  assert.match(v.$('#uploadFileInfo').textContent, /primero.txt.*TXT.*KiB/);
  assert.match(v.$('#uploadFilePhase').textContent, /todavía sin enviar/);
  await v.form.preview(file('segundo.txt', 'Segundo documento'));
  assert.equal(v.$('#uploadLocalText').textContent, 'Segundo documento');
  assert.ok(!v.$('#uploadFileInfo').textContent.includes('primero.txt'));
  assert.equal(calls, 0);
  v.form.reset(); assert.equal(v.$('#uploadLocalText').textContent, '');
  assert.equal(v.$('#uploadLocalPanel').hidden, true);
});

// Agregado por Edil: las pantallas visibles solo ofrecen flujos disponibles.
test('Inicio y navegación no exponen pantallas ficticias ni acciones sin destino', () => {
  for (const page of ['index.html', 'ingesta/index.html', 'historial/index.html', 'auditoria/index.html', 'resultado/index.html', 'colas/index.html']) {
    const html = fs.readFileSync(require('node:path').join(__dirname, '../src', page), 'utf8');
    const active = html.replace(/<template\b[^>]*>[\s\S]*?<\/template>/g, '');
    assert.doesNotMatch(active, /data-toast|<a[^>]*href="#"|Dr\. M\. Vance|HIS Connected|documents-mock\.js|data-nav="(?:colas|resultado|inicio)"/);
    for (const screen of ['ingesta', 'historial', 'auditoria']) assert.ok(active.includes('data-nav="' + screen + '"'));
  }
  const home = fs.readFileSync(require.resolve('../src/index.html'), 'utf8');
  for (const screen of ['ingesta', 'historial', 'auditoria']) assert.ok(home.includes('href="' + screen + '/index.html"'));
});
