const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const documentsApi = require("../src/assets/js/documents-api.js");
const { createClient, ReviewApiError } = require("../src/assets/js/reviews-api.js");
require("../src/assets/js/audit-controller.js");
const { mount, mountFromSession } = require("../src/auditoria/audit-panel.js");
const { createAdapter } = require("../src/assets/js/review-http-adapter.js");
const { documents } = require("../src/assets/js/documents-mock.js");

// Agregado por Edil: DOM mínimo de prueba para ejercitar handlers/renderizado.
// No sustituye una prueba visual con un motor de navegador real.
class Element {
  constructor() { this.value = ""; this.dataset = {}; this.handlers = {}; this.disabled = false; this.hidden = false;
    this.textContent = ""; this.innerHTML = ""; this.open = false; this.isConnected = true; this.attrs = {}; }
  addEventListener(name, handler) { (this.handlers[name] ||= []).push(handler); }
  fire(name, event = {}) { if (this.disabled && name === "click") return; for (const cb of this.handlers[name] || []) cb({ preventDefault() {}, target: this, ...event }); }
  setAttribute(name, value) { this.attrs[name] = value; }
  showModal() { this.open = true; }
  close() { this.open = false; }
  focus() { this.focused = true; }
  querySelectorAll() { return []; }
}
function view(overrides = {}) {
  const elements = new Map();
  const doc = { querySelector(selector) { if (!elements.has(selector)) elements.set(selector, new Element()); return elements.get(selector); } };
  const $ = id => doc.querySelector(id);
  $("#auditPriority").value = "all";
  const sample = structuredClone(documents[3]); sample.clasificacion.nivel_prioridad = "Urgente";
  let calls = { list: 0, detail: 0, submit: 0, history: 0 };
  const api = { ...documentsApi,
    getDocuments: async () => { calls.list++; if (overrides.listError) throw overrides.listError; return overrides.rows || [sample]; },
    getDocument: async id => { calls.detail++; if (overrides.detailError) throw overrides.detailError; return { ...sample, documento_id: id }; } };
  const adapter = overrides.approved ? { approved: true, contractReference: "TEST-ONLY-NOT-PRODUCTION",
    requiresReviewerId: !!overrides.contract, requiresRejectionObservation: !!overrides.contract,
    submitReview: async request => { calls.submit++; if (overrides.submitError) throw overrides.submitError;
      return { ...request, persisted: true, reviewId: "TEST-1", auditor: "Auditor sintético", reviewedAt: "2026-10-17T20:00:00Z" }; },
    getReviewHistory: async id => { calls.history++; return { documentId: id, entries: overrides.entries || [] }; }
  } : null;
  const values = new Map(); const storage = { getItem: key => values.get(key) || null, setItem: (key, val) => values.set(key, val) };
  const client = createClient({ documentsApi: api, approvedAdapter: adapter });
  // Identidad exclusiva de pruebas; producción la recibe del servidor privado.
  const authenticatedUser = Object.prototype.hasOwnProperty.call(overrides, "authenticatedUser")
    ? overrides.authenticatedUser : { login: "synthetic-auditor", canReview: true };
  const controller = mount(doc, { client, storage, authenticatedUser, authClient: overrides.authClient, onLoggedOut: overrides.onLoggedOut });
  async function open() {
    const button = { disabled: false, dataset: { openDocument: sample.documento_id }, isConnected: false, closest() { return this; } };
    $("#auditList").fire("click", { target: button }); await controller.open(sample.documento_id);
  }
  return { $, controller, calls, sample, overrides, open };
}
test("bandeja usa fuente real por interfaz, carga y muestra ID/tipo/prioridad/confianza/estado", async () => {
  const v = view(); assert.equal(v.$("#refreshAudit").disabled, true);
  await v.controller.load(); const html = v.$("#auditList").innerHTML;
  assert.ok(html.includes(v.sample.documento_id)); assert.ok(html.includes("Urgente"));
  assert.ok(html.includes("Confianza de clasificación")); assert.ok(html.includes("auditoria_humana"));
  assert.equal(v.calls.list, 1); assert.equal(v.$("#refreshAudit").disabled, false);
});
test("buscador y filtro de prioridad actualizan filas y vacío sin nuevo GET", async () => {
  const v = view(); await v.controller.load();
  v.$("#q").value = "sin coincidencia"; v.$("#q").fire("input");
  assert.equal(v.$("#auditList").innerHTML, ""); assert.equal(v.$("#auditEmpty").hidden, false);
  v.$("#q").value = ""; v.$("#auditPriority").value = "Rutina"; v.$("#auditPriority").fire("change");
  assert.equal(v.$("#auditList").innerHTML, "");
  v.$("#auditPriority").value = "Urgente"; v.$("#auditPriority").fire("change");
  assert.ok(v.$("#auditList").innerHTML.includes("Urgente")); assert.equal(v.calls.list, 1);
});
test("bandeja vacía se anuncia sin inventar documentos", async () => {
  const v = view({ rows: [] }); await v.controller.load();
  assert.equal(v.$("#auditEmpty").hidden, false); assert.equal(v.$("#navAuditTotal").textContent, "0");
});
test("actualizar fallido conserva bandeja y muestra advertencia de datos antiguos", async () => {
  const v = view(); await v.controller.load(); v.overrides.listError = new ReviewApiError("red");
  v.$("#refreshAudit").fire("click"); await v.controller.load();
  assert.ok(v.$("#auditList").innerHTML.includes(v.sample.documento_id));
  assert.match(v.$("#auditLoadStatus").textContent, /desactualizada/);
});
test("abrir detalle ejecuta GET individual, muestra motivo/JSON y conserva Urgente", async () => {
  const v = view(); await v.controller.load(); await v.open();
  assert.equal(v.calls.detail, 1); assert.equal(v.$("#auditDetail").open, true);
  assert.equal(v.$("#auditUrgent").hidden, false); assert.match(v.$("#auditSummary").innerHTML, /Urgente/);
  assert.equal(v.$("#auditReason").textContent, v.sample.decision_enrutamiento.justificacion_enrutamiento);
  assert.equal(JSON.parse(v.$("#auditRawJson").textContent).clasificacion.nivel_prioridad, "Urgente");
});
test("cargado_por muestra identidad del JSON y no inventa datos en documentos históricos", async () => {
  const v = view(); v.sample.cargado_por = "synthetic-uploader";
  await v.controller.load(); await v.open();
  assert.match(v.$("#auditSummary").innerHTML, /synthetic-uploader/);
  v.sample.cargado_por = null; await v.controller.open(v.sample.documento_id);
  assert.match(v.$("#auditSummary").innerHTML, /Cargado por<\/dt><dd>No disponible/);
});
test("sin aprobación de contrato las acciones y el historial no simulan persistencia", async () => {
  const v = view(); await v.controller.load(); await v.open();
  assert.equal(v.$("#approveReview").disabled, true); assert.equal(v.$("#rejectReview").disabled, true);
  assert.match(v.$("#reviewAvailability").textContent, /pendiente/);
  assert.match(v.$("#reviewHistoryStatus").textContent, /No se genera un historial local/);
  v.$("#approveReview").fire("click"); assert.equal(v.calls.submit, 0); assert.equal(v.calls.history, 0);
});
test("formulario muestra auditor autenticado de solo lectura y exige observación para rechazo", async () => {
  const v = view({ approved: true, contract: true }); await v.controller.load(); await v.open();
  assert.equal(v.$("#reviewerField").hidden, false);
  assert.equal(v.$("#reviewerId").value, "synthetic-auditor");
  assert.equal(v.$("#reviewerId").disabled, true); assert.equal(v.$("#reviewerId").readOnly, true);
  assert.equal(v.$("#reviewerId").attrs["aria-readonly"], "true");
  assert.equal(v.$("#approveReview").disabled, false); assert.equal(v.$("#rejectReview").disabled, true);
  v.$("#reviewObservation").value = "observación sintética"; v.$("#reviewObservation").fire("input");
  assert.equal(v.$("#rejectReview").disabled, false);
  v.$("#rejectReview").fire("click"); assert.equal(v.$("#reviewerId").disabled, true);
});
test("identidad ausente o sin permiso mantiene el panel en consulta", async () => {
  for (const authenticatedUser of [null, { login: "synthetic-reader", canReview: false }]) {
    const v = view({ approved: true, contract: true, authenticatedUser });
    await v.controller.load(); await v.open();
    assert.equal(v.$("#approveReview").disabled, true); assert.equal(v.$("#rejectReview").disabled, true);
    assert.match(v.$("#reviewAvailability").textContent, /identidad/);
    assert.equal(v.calls.submit, 0);
  }
});

test("panel muestra acceso propio de MediFlow y cerrar sesión requiere confirmar", async () => {
  let logouts = 0, left = 0;
  const v = view({ authClient: { logout: async () => { logouts++; } }, onLoggedOut: () => { left++; } });
  await v.controller.load();
  assert.equal(v.$("#authLoginLink").hidden, true); assert.equal(v.$("#authLogout").hidden, false);
  assert.equal(v.$("#authSessionUser").textContent, "Sesión: synthetic-auditor");
  v.$("#authLogout").fire("click"); assert.equal(v.$("#logoutConfirmation").open, true); assert.equal(logouts, 0);
  v.$("#logoutCancel").fire("click"); assert.equal(v.$("#logoutConfirmation").open, false); assert.equal(logouts, 0);
  v.$("#authLogout").fire("click"); v.$("#logoutConfirm").fire("click"); v.$("#logoutConfirm").fire("click");
  await new Promise(resolve => setImmediate(resolve)); assert.equal(logouts, 1); assert.equal(left, 1);
});

test("sin sesión aparece enlace de acceso y un fallo de logout conserva la página", async () => {
  const anonymous = view({ authenticatedUser: null }); await anonymous.controller.load();
  assert.equal(anonymous.$("#authLoginLink").hidden, false); assert.equal(anonymous.$("#authLogout").hidden, true);
  const v = view({ authClient: { logout: async () => { throw Error("PRIVATE"); } }, onLoggedOut: () => assert.fail() });
  await v.controller.load(); v.$("#authLogout").fire("click"); v.$("#logoutConfirm").fire("click");
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(v.$("#logoutConfirmation").open, true); assert.match(v.$("#logoutStatus").textContent, /No se pudo confirmar/);
  assert.ok(!v.$("#logoutStatus").textContent.includes("PRIVATE")); assert.equal(v.$("#logoutConfirm").disabled, false);
});

test("no se cierra sesión ni se abandona una decisión mientras se envía", async () => {
  let finish;
  const v = view({ approved: true, authClient: { logout: () => assert.fail() } });
  await v.controller.load(); await v.open();
  v.controller.state.submitStatus = "sending";
  v.$("#authLogout").fire("click"); assert.equal(v.$("#logoutConfirmation").open, false);
});
for (const decision of ["approve", "reject"]) {
  test("interacción " + decision + ": observar, confirmar, cancelar y enviar una sola vez", async () => {
    const v = view({ approved: true }); await v.controller.load(); await v.open();
    v.$("#reviewObservation").value = "Observación sintética"; v.$("#reviewObservation").fire("input");
    v.$(decision === "approve" ? "#approveReview" : "#rejectReview").fire("click");
    assert.equal(v.$("#reviewConfirmation").open, true); assert.equal(v.calls.submit, 0);
    assert.equal(v.$("#reviewConfirmationObservation").textContent, "Observación sintética");
    v.$("#reviewCancelSend").fire("click"); assert.equal(v.$("#reviewConfirmation").open, false);
    v.$(decision === "approve" ? "#approveReview" : "#rejectReview").fire("click");
    v.$("#reviewConfirmSend").fire("click"); v.$("#reviewConfirmSend").fire("click"); await v.controller.submit();
    assert.equal(v.calls.submit, 1); assert.match(v.$("#reviewResult").textContent, /Decisión persistida/);
    assert.equal(v.$("#reviewConfirmation").open, false); assert.equal(v.sample.clasificacion.nivel_prioridad, "Urgente");
  });
}
for (const status of [400, 401, 403, 404, 409, 422, 500]) {
  test("error visual de detalle HTTP " + status + " permite consultar de nuevo", async () => {
    const v = view({ detailError: new documentsApi.DocumentsApiError("Error de consulta", status) });
    await v.controller.load(); await v.open();
    assert.ok(v.$("#auditDetailStatus").textContent); assert.equal(v.$("#approveReview").disabled, true);
    v.overrides.detailError = null; v.$("#auditRetryDetail").fire("click"); await v.controller.open(v.sample.documento_id);
    assert.equal(v.controller.state.detailStatus, "ready"); assert.equal(v.calls.detail, 2);
  });
}
test("fallo incierto de envío mantiene observación, bloquea reenvío y no muestra éxito", async () => {
  const v = view({ approved: true, submitError: Error("PRIVATE") }); await v.controller.load(); await v.open();
  v.$("#reviewObservation").value = "conservar"; v.$("#reviewObservation").fire("input");
  v.$("#approveReview").fire("click"); v.$("#reviewConfirmSend").fire("click"); await v.controller.submit();
  assert.equal(v.$("#reviewObservation").value, "conservar"); assert.equal(v.$("#approveReview").disabled, true);
  assert.match(v.$("#reviewAvailability").textContent, /sin confirmación/);
  assert.ok(!v.$("#reviewResult").textContent.includes("PRIVATE"));
  assert.ok(!v.$("#reviewResult").textContent.includes("Decisión persistida"));
});
test("historial disponible muestra campos del servidor, sin fabricar auditor/fecha", async () => {
  const entry = { documentId: documents[3].documento_id, decision: "reject", observation: "<script>test</script>", reviewId: "REVIEW-X", auditor: "Test Reviewer", reviewedAt: "2026-10-17T20:00:00Z" };
  const v = view({ approved: true, entries: [entry] }); await v.controller.load(); await v.open(); await v.controller.loadHistory();
  const html = v.$("#reviewHistory").innerHTML;
  assert.match(html, /REVIEW-X/); assert.match(html, /Test Reviewer/); assert.match(html, /2026-10-17/);
  assert.ok(!html.includes("<script>")); assert.ok(html.includes("&lt;script&gt;"));
});
test("una revisión final encontrada deja botones deshabilitados y aviso de solo consulta", async () => {
  const entry = { documentId: documents[3].documento_id, decision: "approve", observation: "", reviewId: "REV-OTHER", auditor: "Auditor sintético", reviewedAt: "2026-10-24T12:00:00Z" };
  const v = view({ approved: true, entries: [entry] }); await v.controller.load(); await v.open(); await v.controller.loadHistory();
  assert.equal(v.$("#approveReview").disabled, true); assert.equal(v.$("#rejectReview").disabled, true);
  assert.match(v.$("#reviewAvailability").textContent, /Ya existe una decisión final/);
  assert.equal(v.$("#reviewResult").textContent, "");
});
test("texto del servidor se escapa en tarjetas, detalle e historial", async () => {
  const v = view(); v.sample.clasificacion.tipo_documento = '<img src=x onerror="PRIVATE">';
  v.sample.datos_extraidos.paciente.nombre = "<script>PRIVATE</script>";
  await v.controller.load(); await v.open();
  assert.ok(!v.$("#auditList").innerHTML.includes("<img")); assert.ok(!v.$("#auditExtracted").innerHTML.includes("<script>"));
});
test("cerrar con botón/Escape devuelve foco y una respuesta tardía no reabre", async () => {
  const v = view(); await v.controller.load(); await v.open();
  v.$("#auditClose").fire("click"); assert.equal(v.$("#auditDetail").open, false); assert.equal(v.controller.state.selectedId, null);
  assert.equal(v.$("#refreshAudit").focused, true);
  await v.open(); v.$("#auditDetail").fire("cancel"); assert.equal(v.$("#auditDetail").open, false);
});
test("HTML mantiene shell, prototipo inerte, semántica y CSS de anchura móvil", () => {
  const html = fs.readFileSync(require.resolve("../src/auditoria/index.html"), "utf8");
  const active = html.replace(/<template\b[^>]*>[\s\S]*?<\/template>/g, "");
  assert.match(html, /<template id="auditLegacyMain">/); assert.match(html, /<template id="auditLegacyDialogs">/);
  assert.ok(!active.includes("documents-mock.js")); assert.ok(!active.includes("Dr. M. Vance")); assert.ok(!active.includes("HIS Connected"));
  assert.match(active, /<dialog id="auditDetail"[^>]*aria-labelledby/); assert.match(active, /aria-live="polite"/);
  assert.match(active, /name="viewport"/);
  const css = fs.readFileSync(require.resolve("../src/auditoria/styles.css"), "utf8");
  assert.match(css, /body\[data-screen="auditoria"\] \[hidden\]\s*\{\s*display: none !important/);
  assert.match(css, /@media \(max-width: 680px\)/); assert.match(css, /width: calc\(100vw - 16px\)/);
});

// Agregado por Edil: arranque estático con respuestas de sesión simuladas,
// sin servidor, cookies reales ni escrituras externas.
function sessionView(getSession) {
  const elements = new Map(), values = new Map(), adapters = [];
  const doc = { querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  } };
  const $ = selector => doc.querySelector(selector);
  $('#auditPriority').value = 'all';
  let sessionCalls = 0, requests = 0;
  const ready = mountFromSession(doc, {
    authClient: { getSession: async () => { sessionCalls++; return getSession(); }, logout: async () => {} },
    storage: { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value) },
    adapterFactory: options => {
      const adapter = createAdapter({ ...options, fetchImpl: async (_, request) => {
        requests++; assert.equal(request.credentials, 'include');
        assert.equal(request.method, 'GET'); // No ejecutar decisiones en esta fixture.
        return { ok: true, status: 200, json: async () => [] };
      } });
      adapters.push({ options, adapter }); return adapter;
    },
  });
  return { $, ready, adapters, sessionCalls: () => sessionCalls, requests: () => requests };
}
async function configuredContract(flag, callback) {
  const present = Object.prototype.hasOwnProperty.call(globalThis, 'MEDIFLOW_REVIEW_CONTRACT_APPROVED');
  const previous = globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED;
  if (flag === undefined) delete globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED;
  else globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED = flag;
  try { await callback(); }
  finally {
    if (present) globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED = previous;
    else delete globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED;
  }
}
test('arranque espera sesión y crea adaptador con la identidad real antes de permitir acciones', async () => {
  await configuredContract(true, async () => {
    let finish;
    const v = sessionView(() => new Promise(resolve => { finish = resolve; }));
    assert.equal(v.$('#approveReview').hidden, true);
    assert.equal(v.$('#rejectReview').disabled, true);
    assert.equal(v.adapters.length, 0); assert.equal(v.requests(), 0);
    const user = { login: 'session-auditor', canReview: true };
    finish({ authenticated: true, user });
    const controller = await v.ready; await controller.load();
    assert.equal(v.sessionCalls(), 1);
    assert.deepEqual(controller.state.authenticatedUser, user);
    assert.deepEqual(v.adapters[0].options.authenticatedUser, user);
    assert.equal(v.$('#approveReview').hidden, false);
    assert.equal(v.$('#authLoginLink').hidden, true);
    assert.equal(controller.state.capabilities.submit, true);
    assert.equal(controller.canSubmit('approve'), false); // Falta detalle fresco, no se salta ese control.
  });
});
test('sesión ausente no reutiliza identidad inyectada y muestra acceso sin decisiones', async () => {
  const previous = globalThis.MEDIFLOW_AUTHENTICATED_USER;
  globalThis.MEDIFLOW_AUTHENTICATED_USER = { login: 'stale-injected-user', canReview: true };
  try {
    await configuredContract(true, async () => {
      const v = sessionView(async () => ({ authenticated: false, user: null }));
      const controller = await v.ready; await controller.load();
      assert.equal(controller.state.authenticatedUser, null);
      assert.equal(v.adapters[0].options.authenticatedUser, null);
      assert.equal(v.$('#approveReview').hidden, true);
      assert.equal(v.$('#authLoginLink').hidden, false);
      assert.equal(controller.canSubmit('reject'), false);
      await assert.rejects(v.adapters[0].adapter.submitReview({}), error => error.status === 401);
    });
  } finally { globalThis.MEDIFLOW_AUTHENTICATED_USER = previous; }
});
test('usuario autenticado sin canReview no ve aprobar/rechazar ni obtiene permiso del contrato', async () => {
  await configuredContract(true, async () => {
    const v = sessionView(async () => ({ authenticated: true, user: { login: 'reader', canReview: false } }));
    const controller = await v.ready; await controller.load();
    assert.equal(controller.state.authenticatedUser.canReview, false);
    assert.equal(v.$('#approveReview').hidden, true); assert.equal(v.$('#rejectReview').hidden, true);
    assert.equal(v.$('#authLoginLink').hidden, true);
    assert.equal(controller.canSubmit('approve'), false);
    await assert.rejects(v.adapters[0].adapter.submitReview({}), error => error.status === 403);
  });
});
for (const flag of [undefined, false]) {
  test('sesión válida no habilita contrato pendiente: ' + String(flag), async () => {
    await configuredContract(flag, async () => {
      const v = sessionView(async () => ({ authenticated: true, user: { login: 'auditor', canReview: true } }));
      const controller = await v.ready; await controller.load();
      assert.equal(controller.state.capabilities.submit, false);
      assert.equal(v.adapters[0].options.decisionApproved, false);
      assert.equal(globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED, flag);
      await assert.rejects(v.adapters[0].adapter.submitReview({}), error => error.status === 403);
    });
  });
}
test('error de sesión permite solo consulta y muestra aviso seguro aunque hubiera identidad inyectada', async () => {
  await configuredContract(true, async () => {
    const v = sessionView(async () => { throw Error('PRIVATE-SESSION-TOKEN'); });
    const controller = await v.ready; await controller.load();
    assert.equal(controller.state.authenticatedUser, null);
    assert.equal(v.$('#approveReview').hidden, true);
    assert.match(v.$('#authSessionStatus').textContent, /No se pudo verificar/);
    assert.ok(!v.$('#authSessionStatus').textContent.includes('PRIVATE'));
    assert.equal(v.$('#authLoginLink').hidden, false);
  });
});
for (const session of [
  { authenticated: false, user: { login: 'forged', canReview: true } },
  { authenticated: true, user: { login: 'forged', canReview: 'true' } },
  { authenticated: true, user: null },
]) {
  test('sesión malformada no concede identidad: ' + JSON.stringify(session), async () => {
    const v = sessionView(async () => session);
    const controller = await v.ready; await controller.load();
    assert.equal(controller.state.authenticatedUser, null);
    assert.equal(v.$('#approveReview').hidden, true);
    assert.match(v.$('#authSessionStatus').textContent, /No se pudo verificar/);
  });
}
test('página real usa arranque de sesión y conserva bandera externa de contrato', () => {
  const source = fs.readFileSync(require.resolve('../src/auditoria/app.js'), 'utf8');
  assert.match(source, /mountFromSession\(document\)/);
  const panel = fs.readFileSync(require.resolve('../src/auditoria/audit-panel.js'), 'utf8');
  assert.doesNotMatch(panel, /MEDIFLOW_REVIEW_CONTRACT_APPROVED\s*=\s*true/);
});

// Agregado por Edil: ejecutar la declaración real del HTML, no una copia en tests.
function applyHtmlContract(target = globalThis) {
  const html = fs.readFileSync(require.resolve('../src/auditoria/index.html'), 'utf8');
  const script = html.match(/<script id="review-contract-config">([\s\S]*?)<\/script>/);
  assert.ok(script, 'La declaración explícita del contrato debe existir');
  vm.runInNewContext(script[1], { window: target });
}
for (const injected of [undefined, true, false]) {
  test('HTML estático habilita solo ausencia y respeta presentación: ' + String(injected), async () => {
    await configuredContract(injected, async () => {
      applyHtmlContract();
      const expected = injected !== false;
      assert.equal(globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED, expected);
      const v = sessionView(async () => ({ authenticated: true, user: { login: 'auditor', canReview: true } }));
      const controller = await v.ready; await controller.load();
      assert.equal(v.adapters[0].options.decisionApproved, expected);
      assert.equal(controller.state.capabilities.submit, expected);
      assert.equal(controller.state.listStatus, 'ready');
      assert.ok(v.requests() > 0, 'Las lecturas deben funcionar también con contrato deshabilitado');
      if (!expected) {
        await assert.rejects(v.adapters[0].adapter.submitReview({}), error => error.status === 403);
      }
    });
  });
}
for (const session of [
  { authenticated: false, user: null },
  { authenticated: true, user: { login: 'reader', canReview: false } },
]) {
  test('contrato estático aprobado no concede identidad ni permiso: ' + String(session.authenticated), async () => {
    await configuredContract(undefined, async () => {
      applyHtmlContract();
      const v = sessionView(async () => session);
      const controller = await v.ready; await controller.load();
      assert.equal(globalThis.MEDIFLOW_REVIEW_CONTRACT_APPROVED, true);
      assert.equal(v.$('#approveReview').hidden, true);
      assert.equal(v.$('#rejectReview').hidden, true);
      assert.equal(controller.canSubmit('approve'), false);
      assert.equal(controller.canSubmit('reject'), false);
      await assert.rejects(v.adapters[0].adapter.submitReview({}), error => error.status === (session.authenticated ? 403 : 401));
    });
  });
}
test('contrato explícito se ejecuta antes del adaptador y panel, sin depender de identidad o almacenamiento', () => {
  const html = fs.readFileSync(require.resolve('../src/auditoria/index.html'), 'utf8');
  const start = html.indexOf('<script id="review-contract-config">');
  const end = html.indexOf('</script>', start);
  assert.ok(start >= 0 && end < html.indexOf('src="../assets/js/review-http-adapter.js'));
  assert.ok(end < html.indexOf('src="audit-panel.js'));
  assert.ok(end < html.indexOf('src="app.js'));
  const source = html.slice(start, end);
  assert.doesNotMatch(source, /canReview|authenticated|localStorage|sessionStorage|location|URLSearchParams/);
  for (const value of ['true', null]) {
    const target = { MEDIFLOW_REVIEW_CONTRACT_APPROVED: value };
    applyHtmlContract(target);
    assert.equal(target.MEDIFLOW_REVIEW_CONTRACT_APPROVED, value);
  }
});
