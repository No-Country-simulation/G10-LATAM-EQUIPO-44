/* Agregado por Edil: formulario de acceso. Sin contraseñas en URL, logs o storage. */
(function (root) {
  "use strict";
  function mount(doc, { client, navigate } = {}) {
    const $ = selector => doc.querySelector(selector);
    const api = client || root.MediFlowAuthApi.createClient();
    const goToPanel = navigate || (() => root.location.assign("../auditoria/index.html"));
    let busy = false, loginTask = null, checking = true;
    function render(message, error = false) {
      $("#loginStatus").textContent = message;
      $("#loginStatus").dataset.state = error ? "error" : "status";
      $("#loginForm").setAttribute("aria-busy", String(busy || checking));
      $("#loginSubmit").disabled = $("#username").disabled = $("#password").disabled = busy || checking;
    }
    const safeMessage = error => error instanceof root.MediFlowAuthApi.AuthApiError ? error.message : "No se pudo conectar con MediFlow.";
    function submit(event) {
      event.preventDefault();
      if (busy || checking) return loginTask || Promise.resolve();
      const username = $("#username").value, password = $("#password").value;
      // La contraseña deja de estar en el DOM mientras se espera la respuesta.
      $("#password").value = "";
      busy = true; render("Ingresando…");
      loginTask = Promise.resolve().then(() => api.login(username, password)).then(() => {
        render("Sesión iniciada. Abriendo el panel…"); goToPanel();
      }).catch(error => { render(safeMessage(error), true); })
        .finally(() => { busy = false; loginTask = null; render($("#loginStatus").textContent, $("#loginStatus").dataset.state === "error"); });
      return loginTask;
    }
    $("#loginForm").addEventListener("submit", submit);
    render("Comprobando sesión…");
    const ready = Promise.resolve().then(() => api.getSession()).then(session => {
      if (session.authenticated) { render("Sesión iniciada. Abriendo el panel…"); goToPanel(); }
      else render("Ingresa tu usuario y contraseña de MediFlow.");
    }).catch(error => { render(safeMessage(error), true); })
      .finally(() => { checking = false; render($("#loginStatus").textContent, $("#loginStatus").dataset.state === "error"); });
    return { ready, submit };
  }
  root.MediFlowLogin = { mount };
  if (typeof module !== "undefined") module.exports = { mount };
  if (typeof window !== "undefined" && root.document) mount(root.document);
})(typeof window !== "undefined" ? window : globalThis);
