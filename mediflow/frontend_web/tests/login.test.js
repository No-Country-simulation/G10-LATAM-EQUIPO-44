const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { AuthApiError } = require("../src/assets/js/auth-api.js");
const { mount } = require("../src/login/app.js");

function view(overrides = {}) {
  const elements = new Map();
  const doc = { querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, { value: "", textContent: "", dataset: {}, disabled: false, attrs: {}, handlers: {},
      setAttribute(key, value) { this.attrs[key] = value; }, addEventListener(name, handler) { this.handlers[name] = handler; } });
    return elements.get(selector);
  } };
  const $ = selector => doc.querySelector(selector);
  let calls = 0, navigations = 0;
  const client = { getSession: overrides.getSession || (async () => ({ authenticated: false, user: null })), login: async (...args) => {
    calls++; if (overrides.login) return overrides.login(...args); return { authenticated: true, user: { login: "synthetic", canReview: true } };
  } };
  const form = mount(doc, { client, navigate: () => { navigations++; } });
  const submit = () => form.submit({ preventDefault() {} });
  return { $, form, submit, calls: () => calls, navigations: () => navigations };
}

test("sesión anónima habilita formulario y sesión existente abre solamente panel fijo", async () => {
  const anonymous = view(); assert.equal(anonymous.$("#loginSubmit").disabled, true);
  await anonymous.form.ready; assert.equal(anonymous.$("#loginSubmit").disabled, false); assert.equal(anonymous.navigations(), 0);
  const existing = view({ getSession: async () => ({ authenticated: true, user: { login: "synthetic", canReview: true } }) });
  await existing.form.ready; assert.equal(existing.navigations(), 1);
});

test("doble submit envía una vez, limpia contraseña del DOM y redirige tras confirmación", async () => {
  let finish;
  const v = view({ login: () => new Promise(resolve => { finish = resolve; }) }); await v.form.ready;
  v.$("#username").value = "synthetic"; v.$("#password").value = "synthetic-test-only";
  const one = v.submit(), two = v.submit(); await Promise.resolve();
  assert.equal(v.calls(), 1); assert.equal(one, two); assert.equal(v.$("#password").value, "");
  assert.equal(v.$("#loginSubmit").disabled, true); assert.equal(v.navigations(), 0);
  finish({ authenticated: true, user: { login: "synthetic", canReview: true } }); await one;
  assert.equal(v.navigations(), 1);
});

for (const status of [401, 429, 503]) {
  test("login fallido " + status + " conserva usuario, borra contraseña y permite reintentar", async () => {
    const v = view({ login: async () => { throw new AuthApiError("Mensaje seguro de prueba", status); } }); await v.form.ready;
    v.$("#username").value = "synthetic"; v.$("#password").value = "synthetic-test-only";
    await v.submit();
    assert.equal(v.$("#username").value, "synthetic"); assert.equal(v.$("#password").value, "");
    assert.equal(v.$("#loginSubmit").disabled, false); assert.equal(v.$("#loginStatus").dataset.state, "error");
    assert.equal(v.navigations(), 0);
  });
}

test("error de conexión no revela mensajes privados y fallo de consulta no impide ingresar", async () => {
  const v = view({ getSession: async () => { throw Error("PRIVATE"); }, login: async () => { throw Error("PRIVATE"); } });
  await v.form.ready; assert.equal(v.$("#loginSubmit").disabled, false);
  assert.ok(!v.$("#loginStatus").textContent.includes("PRIVATE"));
  v.$("#username").value = "synthetic"; v.$("#password").value = "synthetic-test-only";
  await v.submit(); assert.ok(!v.$("#loginStatus").textContent.includes("PRIVATE"));
});

test("HTML accesible y responsive no transmite la contraseña en query ni elige redirección externa", () => {
  const html = fs.readFileSync(require.resolve("../src/login/index.html"), "utf8");
  assert.match(html, /name="viewport"/); assert.match(html, /method="post"/); assert.match(html, /type="password"/);
  assert.match(html, /autocomplete="current-password"/); assert.match(html, /for="username"/); assert.match(html, /aria-live="polite"/);
  const source = fs.readFileSync(require.resolve("../src/login/app.js"), "utf8");
  assert.match(source, /location.assign\("\.\.\/auditoria\/index.html"\)/); assert.doesNotMatch(source, /URLSearchParams|location.search/);
  const css = fs.readFileSync(require.resolve("../src/login/styles.css"), "utf8");
  assert.match(css, /@media \(max-width: 480px\)/); assert.match(css, /overflow: auto/);
});
