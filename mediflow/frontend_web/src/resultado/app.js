/* ==========================================================================
   MediFlow Clinical Portal — Pantalla Resultado
   Vanilla JS: datos de ejemplo en arrays + render() que pinta el DOM.
   ========================================================================== */
(function () {
  "use strict";

  /* --------------------------------------------------------------------
     DATOS DE EJEMPLO
     -------------------------------------------------------------------- */

  /* Niveles MTS (referencia de tiempos máximos de atención) */
  const niveles = [
    { id: "rojo", nombre: "Rojo", categoria: "Inmediato", sla: 0, color: "rojo" },
    { id: "naranja", nombre: "Naranja", categoria: "Muy urgente", sla: 10, color: "naranja" },
    { id: "amarillo", nombre: "Amarillo", categoria: "Urgente", sla: 60, color: "amarillo" },
    { id: "verde", nombre: "Verde", categoria: "Normal", sla: 120, color: "verde" },
    { id: "azul", nombre: "Azul", categoria: "No urgente", sla: 240, color: "azul" }
  ];

  /* Pacientes con episodio abierto en ED-1 */
  const pacientes = [];

  /* Array vacío a propósito: los episodios vienen del endpoint, no de datos
     precargados. Es el único punto de sustitución de los datos de paciente.

     Contrato de cada episodio:
       id, nombre, doc, edad, sexo, iniciales, ingreso, mts, destino,
       medico, minutos, grupo, alergias[], ultimaToma, motivo */;

  /* Estudios solicitados: laboratorio, imagen, ECG y toxicología */
  const data = [];

  /* Array vacío a propósito. Contrato de cada estudio:
       id, pid (id de paciente), nombre, categoria, valor, unidad,
       ref, estado ("critico"|"alerta"|"normal"|"pendiente"), hora

     `categoria` es una de `categorias`; `estado`, una clave de ESTADOS. */;

  /* Estudios aún en curso, con tiempo estimado de entrega */
  const pendientes = [];

  /* Array vacío a propósito. Contrato de cada pendiente:
       pid, nombre, motivo, eta, estado ("espera"|"proceso") */;

  /* Alertas clínicas que se muestran junto a los resultados */
  const alertas = {};

  /* Objeto vacío a propósito, indexado por id de paciente.
       { [pid]: [{ tono, titulo, texto }] } */;

  /* Trazabilidad del episodio */
  const traza = {};

  /* Objeto vacío a propósito, indexado por id de paciente.
       { [pid]: [{ titulo, hora, texto }] } */;

  /* Signos vitales por paciente */
  const signos = {};

  /* Objeto vacío a propósito, indexado por id de paciente.
       { [pid]: [{ nombre, valor, unidad, ref, estado }] } */;

  const categorias = ["Laboratorio", "Imagen", "ECG", "Toxicología"];

  /* Totales de los badges del sidebar.
     `colas` lo mantiene la propia pantalla de Colas en su badge; aquí se
     refleja el mismo valor para que todas las pantallas coincidan. */
  const navTotals = { colas: 0, auditoria: 4 };

  /* Estado local de la vista. `null` cuando no hay ningún episodio cargado:
     es el estado normal mientras `pacientes` esté vacío. */
  let pacienteActual = pacientes.length ? pacientes[0].id : null;
  let categoriaActiva = "todas";
  let textoFiltro = "";

  /* --------------------------------------------------------------------
     UTILIDADES
     -------------------------------------------------------------------- */
  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => Array.prototype.slice.call((ctx || document).querySelectorAll(sel));

  const esc = (txt) =>
    String(txt == null ? "" : txt).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const icon = (id, cls) =>
    '<svg class="' + (cls || "icon icon--sm") + '" aria-hidden="true"><use href="#' + id + '"></use></svg>';

  const nivelDe = (id) => niveles.find((n) => n.id === id) || niveles[0];

  const badgeMts = (nivel) =>
    '<span class="badge badge--' + nivel.color + '"><span class="badge__dot" aria-hidden="true"></span>' +
    esc(nivel.nombre + " · " + nivel.sla + " min") + "</span>";

  const ESTADOS = {
    critico: { clase: "badge--rojo", texto: "Crítico" },
    alerta: { clase: "badge--naranja", texto: "Fuera de rango" },
    normal: { clase: "badge--verde", texto: "Normal" },
    pendiente: { clase: "badge--gris", texto: "Pendiente" }
  };

  const paciente = (id) => pacientes.find((p) => p.id === (id || pacienteActual));

  const estudiosDe = (pid) => data.filter((r) => r.pid === pid);

  /* --------------------------------------------------------------------
     RENDER
     -------------------------------------------------------------------- */

  function renderSelector() {
    $("#selPaciente").innerHTML = pacientes.length
      ? pacientes
          .map(
            (p) => '<option value="' + p.id + '"' + (p.id === pacienteActual ? " selected" : "") + ">" +
              esc(p.nombre + " · " + p.ingreso + " · " + nivelDe(p.mts).nombre) + "</option>"
          )
          .join("")
      : '<option value="">Sin episodios disponibles</option>';

    $("#selPaciente").disabled = !pacientes.length;
  }

  /* Estado sin episodio: vacía las regiones que dependen de un paciente
     seleccionado y deja el resto de la pantalla legible. Es el estado
     esperado mientras `pacientes` no reciba datos del endpoint. */
  function renderSinEpisodio() {
    $("#pbInitials").textContent = "—";
    $("#pbNombre").textContent = "Sin episodio cargado";
    $("#pbNombre").title = "";
    $("#pbMeta").textContent = "Los datos se rellenan al conectar el endpoint de episodios";
    $("#pbBadges").innerHTML = "";
    $("#pbAlerts").innerHTML = "";
    $("#vitalesHora").textContent = "Sin constantes cargadas";
    $("#kpis").innerHTML = "";
    $("#vitales").innerHTML = "";
    $("#filtrosRes").innerHTML = "";
    $("#tbodyRes").innerHTML = "";
    $("#resResumen").textContent = "Sin estudios que mostrar";
    $("#badgePendientes").textContent = "0";
    $("#pendientes").innerHTML = '<li class="pendientes__vacio">Sin estudios pendientes.</li>';
    $("#alertas").innerHTML = "";
    $("#traza").innerHTML = "";
    $("#resVacio").hidden = false;
  }

  function renderPaciente() {
    const p = paciente();
    if (!p) return renderSinEpisodio();
    const nivel = nivelDe(p.mts);

    $("#pbInitials").textContent = p.iniciales;
    $("#pbNombre").textContent = p.nombre;
    $("#pbNombre").title = p.nombre;
    $("#pbMeta").textContent = p.edad + " años · " + p.sexo + " · Cédula " + p.doc + " · Grupo " + p.grupo;
    $("#vitalesHora").textContent = "Última toma " + p.ultimaToma + " · Monitor LE-1";

    $("#pbBadges").innerHTML =
      badgeMts(nivel) +
      '<span class="badge badge--navy">' + icon("i-clipboard") + esc(p.ingreso) + "</span>" +
      '<span class="badge badge--gris">' + icon("i-clipboard") + esc(p.destino) + "</span>" +
      '<span class="badge badge--gris" title="' + esc("Tiempo en unidad: " + p.minutos + " minutos") + '">' +
        icon("i-clock") + esc(p.minutos + " min en unidad") + "</span>";

    const alertasPac = alertas[p.id] || [];
    $("#pbAlerts").innerHTML = alertasPac
      .filter((a) => a.tono === "rojo" || a.tono === "naranja")
      .map(
        (a) => '<div class="notice notice--' + a.tono + '">' + icon("i-alert") +
          '<div class="notice__body"><strong>' + esc(a.titulo) + "</strong> — " + esc(a.texto) + "</div></div>"
      )
      .join("");
  }

  function renderKpis() {
    const p = paciente();
    if (!p) return;
    const nivel = nivelDe(p.mts);
    const estudios = estudiosDe(p.id);
    const criticos = estudios.filter((r) => r.estado === "critico").length;
    const pendientesN = estudios.filter((r) => r.estado === "pendiente").length;

    const items = [
      { icono: "i-layers", tono: nivel.color === "rojo" ? "rojo" : nivel.color === "naranja" ? "naranja" : "azul",
        label: "Nivel MTS", valor: nivel.nombre, hint: nivel.categoria + " · ≤ " + nivel.sla + " min" },
      { icono: "i-clock", tono: "azul", label: "Tiempo en unidad", valor: p.minutos + " min", hint: "Ingreso " + p.ingreso },
      { icono: "i-alert", tono: criticos ? "rojo" : "verde", label: "Valores críticos", valor: String(criticos), hint: "De " + estudios.length + " estudios" },
      { icono: "i-clock", tono: "naranja", label: "Estudios pendientes", valor: String(pendientesN), hint: "Reclamar con laboratorio" }
    ];

    $("#kpis").innerHTML = items
      .map(
        (k) => '<div class="kpi kpi--' + k.tono + '" title="' + esc(k.hint) + '">' +
          '<span class="kpi__icon">' + icon(k.icono, "icon icon--lg") + "</span>" +
          '<span class="kpi__body">' +
            '<span class="kpi__label">' + esc(k.label) + "</span>" +
            '<span class="kpi__value">' + esc(k.valor) + "</span>" +
            '<span class="kpi__hint">' + esc(k.hint) + "</span>" +
          "</span></div>"
      )
      .join("");
  }

  function renderVitales() {
    $("#vitales").innerHTML = (signos[pacienteActual] || [])
      .map(
        (v) => '<div class="vital-chip is-' + v.estado + '" title="' + esc(v.nombre + " · referencia " + v.ref) + '">' +
          '<span class="vital-chip__label">' + esc(v.nombre) + "</span>" +
          '<span class="vital-chip__value">' + esc(v.valor) +
            '<span class="vital-chip__unit">' + esc(v.unidad) + "</span></span>" +
          '<span class="vital-chip__ref">' + esc(v.ref) + "</span>" +
        "</div>"
      )
      .join("");
  }

  function renderFiltros() {
    const estudios = estudiosDe(pacienteActual);
    const conteo = (cat) => (cat === "todas" ? estudios.length : estudios.filter((r) => r.categoria === cat).length);

    const botones = [{ id: "todas", texto: "Todos" }]
      .concat(categorias.map((c) => ({ id: c, texto: c })))
      .map(
        (c) => '<button type="button" class="filter' + (categoriaActiva === c.id ? " is-on" : "") +
          '" data-cat="' + esc(c.id) + '" aria-pressed="' + (categoriaActiva === c.id) + '">' +
          esc(c.texto) + ' <span class="filter__count">' + conteo(c.id) + "</span></button>"
      )
      .join("");

    $("#filtrosRes").innerHTML = botones;
    $$("#filtrosRes .filter").forEach((b) => {
      b.addEventListener("click", () => {
        categoriaActiva = b.dataset.cat;
        renderFiltros();
        renderTabla();
      });
    });
  }

  function renderTabla() {
    const estudios = estudiosDe(pacienteActual);
    const q = textoFiltro.trim().toLowerCase();

    const filtrados = estudios.filter((r) => {
      const okCat = categoriaActiva === "todas" || r.categoria === categoriaActiva;
      const okTxt = !q || r.nombre.toLowerCase().indexOf(q) > -1 || r.categoria.toLowerCase().indexOf(q) > -1;
      return okCat && okTxt;
    });

    $("#tbodyRes").innerHTML = filtrados
      .map((r) => {
        const e = ESTADOS[r.estado];
        return '<tr data-estado="' + r.estado + '">' +
          '<td><span class="estudio"><span class="estudio__name" title="' + esc(r.nombre) + '">' + esc(r.nombre) + "</span>" +
            '<span class="estudio__cat">' + esc(r.categoria) + "</span></span></td>" +
          '<td class="num"><span class="valor">' + (r.valor ? esc(r.valor) : "—") +
            (r.unidad ? '<span class="unit">' + esc(r.unidad) + "</span>" : "") + "</span></td>" +
          '<td class="nowrap">' + esc(r.ref) + "</td>" +
          '<td><span class="badge ' + e.clase + '"><span class="badge__dot" aria-hidden="true"></span>' + esc(e.texto) + "</span></td>" +
          '<td class="nowrap tabnum">' + esc(r.hora) + "</td>" +
          '<td class="actions"><button type="button" class="linkbtn" data-estudio="' + r.id + '">' +
            (r.estado === "pendiente" ? "Reclamar" : "Ver informe") + "</button></td>" +
        "</tr>";
      })
      .join("");

    $("#resVacio").hidden = filtrados.length > 0;

    const criticos = estudios.filter((r) => r.estado === "critico").length;
    const pend = estudios.filter((r) => r.estado === "pendiente").length;
    const recibidos = estudios.length - pend;
    $("#resResumen").textContent =
      "Mostrando " + filtrados.length + " de " + estudios.length + " estudios · " +
      recibidos + " recibidos · " + criticos + " críticos · " + pend + " pendientes";

    $$("#tbodyRes .linkbtn").forEach((b) => {
      b.addEventListener("click", () => {
        const r = data.find((x) => x.id === b.dataset.estudio);
        if (r.estado === "pendiente") toast("Reclamación enviada al laboratorio: " + r.nombre + ".", "naranja");
        else toast("Abriendo informe de " + r.nombre + " (" + r.hora + " h).");
      });
    });
  }

  function renderPendientes() {
    const lista = pendientes.filter((p) => p.pid === pacienteActual);
    $("#badgePendientes").textContent = lista.length;

    $("#pendientes").innerHTML = lista.length
      ? lista
          .map(
            (p) => '<li class="pendientes__item">' +
              '<span class="pendientes__icon' + (p.estado === "espera" ? " pendientes__icon--espera" : "") + '" aria-hidden="true">' +
                icon(p.estado === "proceso" ? "i-activity" : "i-clock") + "</span>" +
              '<span class="pendientes__body">' +
                '<span class="pendientes__name" title="' + esc(p.nombre) + '">' + esc(p.nombre) + "</span>" +
                '<span class="pendientes__meta">' + esc(p.motivo) + "</span>" +
              "</span>" +
              '<span class="pendientes__eta">' + esc(p.eta) + "</span>" +
            "</li>"
          )
          .join("")
      : '<li class="pendientes__vacio">Sin estudios pendientes para este paciente.</li>';
  }

  function renderAlertas() {
    const lista = alertas[pacienteActual] || [];
    $("#alertas").innerHTML = lista
      .map(
        (a) => '<div class="notice notice--' + a.tono + '">' + icon("i-alert") +
          '<div class="notice__body"><strong>' + esc(a.titulo) + "</strong><br>" + esc(a.texto) + "</div></div>"
      )
      .join("");
  }

  function renderTraza() {
    $("#traza").innerHTML = (traza[pacienteActual] || [])
      .map(
        (t) => '<div class="tl-item">' +
          '<span class="tl-item__dot" aria-hidden="true">' + icon("i-check") + "</span>" +
          '<div class="tl-item__body">' +
            '<div class="tl-item__head"><span class="tl-item__title">' + esc(t.titulo) + "</span>" +
              '<span class="tl-item__time">' + esc(t.hora) + "</span></div>" +
            '<p class="tl-item__text">' + esc(t.texto) + "</p>" +
          "</div>" +
        "</div>"
      )
      .join("");
  }

  function render() {
    renderSelector();
    if (!paciente()) {
      /* Sin episodio no hay nada que derivar: se vacían las regiones
         dependientes y se sale, en lugar de propagar un undefined. */
      renderSinEpisodio();
      sincronizarNav();
      return;
    }
    renderPaciente();
    renderKpis();
    renderVitales();
    renderFiltros();
    renderTabla();
    renderPendientes();
    renderAlertas();
    renderTraza();
    sincronizarNav();
  }

  /* --------------------------------------------------------------------
     CHROME: navegación activa, menú, avisos
     -------------------------------------------------------------------- */
  function sincronizarNav() {
    const pantalla = document.body.dataset.screen;
    $$(".nav__item[data-nav]").forEach((el) => {
      const activo = el.dataset.nav === pantalla;
      el.classList.toggle("is-active", activo);
      if (activo) el.setAttribute("aria-current", "page");
      else el.removeAttribute("aria-current");
    });
    if ($("#navQueueTotal")) $("#navQueueTotal").textContent = navTotals.colas;
    if ($("#navAuditTotal")) $("#navAuditTotal").textContent = navTotals.auditoria;
  }

  function toast(mensaje, tono) {
    const host = $("#toastHost");
    const el = document.createElement("div");
    el.className = "toast toast--" + (tono || "verde");
    el.innerHTML = icon(tono === "rojo" || tono === "naranja" ? "i-alert" : "i-check") +
      '<div class="notice__body">' + esc(mensaje) + "</div>";
    host.appendChild(el);
    window.setTimeout(() => el.remove(), 4600);
  }

  function initMenu() {
    const btn = $("#userBtn");
    const menu = $("#userMenu");
    btn.addEventListener("click", () => {
      const abierto = menu.hidden;
      menu.hidden = !abierto;
      btn.setAttribute("aria-expanded", String(abierto));
    });
    document.addEventListener("click", (ev) => {
      if (!menu.hidden && !menu.contains(ev.target) && ev.target !== btn) {
        menu.hidden = true;
        btn.setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !menu.hidden) {
        menu.hidden = true;
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* --------------------------------------------------------------------
     ARRANQUE
     -------------------------------------------------------------------- */
  function init() {
    render();
    initMenu();

    $("#selPaciente").addEventListener("change", (ev) => {
      if (!ev.target.value) return;
      pacienteActual = ev.target.value;
      categoriaActiva = "todas";
      textoFiltro = "";
      $("#qRes").value = "";
      render();
      toast("Mostrando resultados de " + paciente().nombre + ".", "verde");
    });

    $("#qRes").addEventListener("input", (ev) => {
      textoFiltro = ev.target.value;
      renderTabla();
    });

    $$("[data-toast]").forEach((b) => b.addEventListener("click", () => toast(b.dataset.toast, "verde")));

    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        $("#q").focus();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
