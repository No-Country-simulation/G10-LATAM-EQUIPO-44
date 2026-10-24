const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { createClient, AuthApiError } = require("../src/assets/js/auth-api.js");
const baseUrl = "http://127.0.0.1:8787";
const session = { authenticated: true, user: { login: "synthetic-auditor", canReview: true } };
const response = (data = session, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => data });

test("login envía la contraseña solo en JSON al mismo origen con cookie HttpOnly gestionada por navegador", async () => {
  const client = createClient({ baseUrl, fetchImpl: async (url, options) => {
    assert.equal(url, baseUrl + "/api/auth/login");
    assert.equal(options.method, "POST"); assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store"); assert.equal(options.redirect, "error");
    assert.equal(options.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(options.body), { username: "synthetic-auditor", password: "synthetic-test-only" });
    assert.ok(!url.includes("synthetic-test-only"));
    return response();
  } });
  assert.deepEqual(await client.login(" synthetic-auditor ", "synthetic-test-only"), session);
});

test("consulta de sesión no agrega contraseña ni token y admite sesión ausente", async () => {
  const client = createClient({ baseUrl, fetchImpl: async (url, options) => {
    assert.equal(url, baseUrl + "/api/auth/session"); assert.equal(options.method, "GET");
    assert.equal(options.body, undefined); assert.equal(options.headers.Authorization, undefined);
    return response({ authenticated: false, user: null });
  } });
  assert.deepEqual(await client.getSession(), { authenticated: false, user: null });
});

test("logout exige confirmación 204 y no persiste datos locales", async () => {
  const client = createClient({ baseUrl, fetchImpl: async (url, options) => {
    assert.equal(url, baseUrl + "/api/auth/logout"); assert.equal(options.method, "POST");
    assert.equal(options.body, undefined); return response(null, 204);
  } });
  assert.equal(await client.logout(), undefined);
  await assert.rejects(createClient({ baseUrl, fetchImpl: async () => response() }).logout(), /confirmó/);
});

for (const status of [400, 401, 403, 422, 429, 500, 503]) {
  test("error HTTP " + status + " no muestra cuerpo sensible del servidor", async () => {
    await assert.rejects(createClient({ baseUrl, fetchImpl: async () => ({ ok: false, status, json: () => assert.fail("No leer cuerpos privados") }) }).login("test", "synthetic-test-only"),
      error => error instanceof AuthApiError && error.status === status && !error.message.includes("synthetic-test-only"));
  });
}

for (const data of [null, [], {}, { authenticated: "true", user: null }, { authenticated: false, user: {} },
  { authenticated: true, user: { login: "", canReview: true } }, { authenticated: true, user: { login: "user", canReview: "yes" } }]) {
  test("rechaza respuesta de sesión incompatible: " + JSON.stringify(data), async () => {
    await assert.rejects(createClient({ baseUrl, fetchImpl: async () => response(data) }).getSession(), /no es válida/);
  });
}

test("login no anuncia éxito si el servidor devuelve sesión anónima", async () => {
  await assert.rejects(createClient({ baseUrl, fetchImpl: async () => response({ authenticated: false, user: null }) }).login("test", "synthetic-test-only"), /no confirmó/);
});

for (const unsafe of ["https://user:secret@example.test", "ftp://example.test", "https://example.test/path", "https://example.test?token=secret", "http://example.test"]) {
  test("dirección de sesión inválida no realiza HTTP: " + unsafe, async () => {
    await assert.rejects(createClient({ baseUrl: unsafe, fetchImpl: () => assert.fail() }).getSession(), error => error.status === 400);
  });
}

test("el navegador rechaza un origen de API distinto para enviar credenciales", async () => {
  const original = globalThis.location;
  globalThis.location = { origin: "https://presentation.test" };
  try {
    await assert.rejects(createClient({ baseUrl: "https://foreign.test", fetchImpl: () => assert.fail() }).login("test", "synthetic-test-only"), error => error.status === 400);
  } finally { if (original === undefined) delete globalThis.location; else globalThis.location = original; }
});

test("red, JSON malformado y timeout son errores genéricos sin contraseña", async () => {
  await assert.rejects(createClient({ baseUrl, fetchImpl: async () => { throw Error("PRIVATE_SECRET"); } }).getSession(), error => !error.message.includes("PRIVATE_SECRET"));
  await assert.rejects(createClient({ baseUrl, fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw Error("PRIVATE_SECRET"); } }) }).getSession(), /no es válida/);
  await assert.rejects(createClient({ baseUrl, timeoutMs: 5, fetchImpl: (_, { signal }) => new Promise((_, reject) => signal.addEventListener("abort", () => reject(Error("PRIVATE_SECRET")))) }).getSession(), /agotó/);
});

test("los nuevos archivos de acceso no usan almacenamiento local ni consola para credenciales", () => {
  for (const file of ["../src/assets/js/auth-api.js", "../src/login/app.js"]) {
    const source = fs.readFileSync(require.resolve(file), "utf8");
    assert.doesNotMatch(source, /(?:localStorage|sessionStorage|console\.(?:log|error|warn))/);
  }
});
