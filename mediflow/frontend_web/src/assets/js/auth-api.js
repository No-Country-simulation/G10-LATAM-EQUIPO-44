/* Agregado por Edil: sesión propia de MediFlow con cookie HttpOnly.
   La contraseña solo viaja al login del mismo origen; no se guarda en el navegador. */
(function (root) {
  "use strict";
  class AuthApiError extends Error {
    constructor(message, status) { super(message); this.name = "AuthApiError"; this.status = status; }
  }
  function messageFor(status) {
    if (status === 401) return "Usuario o contraseña incorrectos.";
    if (status === 403) return "El acceso debe realizarse desde la dirección autorizada de MediFlow.";
    if (status === 429) return "Se alcanzó el límite de intentos. Espera antes de volver a ingresar.";
    if (status === 400 || status === 422) return "Revisa el usuario y la contraseña ingresados.";
    return "No se pudo completar la operación de sesión. Intenta nuevamente.";
  }
  function createClient({ baseUrl, fetchImpl, timeoutMs = 12000 } = {}) {
    const configured = baseUrl || root.MEDIFLOW_API_BASE_URL || root.location?.origin;
    function urlFor(path) {
      try {
        const base = new URL(configured);
        if (!["http:", "https:"].includes(base.protocol) || (base.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(base.hostname)) ||
          base.username || base.password || base.search || base.hash ||
          !["", "/"].includes(base.pathname) || (root.location?.origin && base.origin !== root.location.origin)) throw Error();
        return base.origin + path;
      } catch (_) { throw new AuthApiError("La sesión necesita la web y la API en el mismo origen autorizado.", 400); }
    }
    async function request(path, { method = "GET", body, expectEmpty = false } = {}) {
      const url = urlFor(path), abort = new AbortController();
      const timer = setTimeout(() => abort.abort(), timeoutMs);
      try {
        const response = await (fetchImpl || root.fetch)(url, {
          method, credentials: "same-origin", cache: "no-store", redirect: "error", signal: abort.signal,
          headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
          ...(body ? { body: JSON.stringify(body) } : {}),
        });
        if (!response.ok) throw new AuthApiError(messageFor(response.status), response.status);
        if (expectEmpty) {
          if (response.status !== 204) throw new AuthApiError("El servidor no confirmó el cierre de sesión.");
          return;
        }
        if (response.status !== 200) throw new AuthApiError("La respuesta de sesión no es válida.");
        let data;
        try { data = await response.json(); } catch (_) { throw new AuthApiError("La respuesta de sesión no es válida."); }
        if (!data || typeof data.authenticated !== "boolean" ||
          (data.authenticated ? (!data.user || typeof data.user.login !== "string" || !data.user.login.trim() || typeof data.user.canReview !== "boolean") : data.user !== null)) {
          throw new AuthApiError("La respuesta de sesión no es válida.");
        }
        return { authenticated: data.authenticated, user: data.authenticated ? { login: data.user.login, canReview: data.user.canReview } : null };
      } catch (error) {
        if (error instanceof AuthApiError) throw error;
        throw new AuthApiError(abort.signal.aborted ? "La operación de sesión agotó el tiempo de espera." : "No se pudo conectar con MediFlow.");
      } finally { clearTimeout(timer); }
    }
    return {
      getSession: () => request("/api/auth/session"),
      async login(username, password) {
        if (typeof username !== "string" || !username.trim() || username.trim().length > 128 ||
          typeof password !== "string" || !password || password.length > 1024) {
          throw new AuthApiError("Completa el usuario y la contraseña.", 422);
        }
        const session = await request("/api/auth/login", { method: "POST", body: { username: username.trim(), password } });
        if (!session.authenticated) throw new AuthApiError("El servidor no confirmó el inicio de sesión.");
        return session;
      },
      logout: () => request("/api/auth/logout", { method: "POST", expectEmpty: true }),
    };
  }
  root.MediFlowAuthApi = { createClient, AuthApiError };
  if (typeof module !== "undefined") module.exports = { createClient, AuthApiError };
})(typeof window !== "undefined" ? window : globalThis);
