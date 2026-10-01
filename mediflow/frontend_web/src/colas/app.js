/* ==========================================================================
   MediFlow Clinical Portal — Pantalla Colas
   Tablero kanban del censo activo de ED-1.
   Los datos viven en el array `patients`; todo el tablero, el censo,
   los contadores y el badge del sidebar se derivan de ese array.
   ========================================================================== */
(function () {
  "use strict";

  /* --------------------------------------------------------------------
     NIVELES MTS — tiempo objetivo en minutos y orden de prioridad
     -------------------------------------------------------------------- */
  const niveles = [
    { id: "rojo", nombre: "Rojo", objetivo: 0, etiqueta: "Emergencia", orden: 0 },
    { id: "naranja", nombre: "Naranja", objetivo: 10, etiqueta: "Muy urgente", orden: 1 },
    { id: "amarillo", nombre: "Amarillo", objetivo: 60, etiqueta: "Urgente", orden: 2 },
    { id: "verde", nombre: "Verde", objetivo: 120, etiqueta: "Estándar", orden: 3 },
    { id: "azul", nombre: "Azul", objetivo: 240, etiqueta: "No urgente", orden: 4 }
  ];

  /* --------------------------------------------------------------------
     COLUMNAS DEL TABLERO
     -------------------------------------------------------------------- */
  const columnas = [
    { id: "medicas", titulo: "Urgencias Médicas", color: "rojo", sub: "Shock Room & Box Crítico · Atención Vital" },
    { id: "auditoria", titulo: "Auditoría Automática", color: "ambar", sub: "Validación de tokens MTS por IA" },
    { id: "farmacia", titulo: "Farmacia Hospitalaria", color: "azul", sub: "Dispensación y reconciliación" },
    { id: "hce", titulo: "HCE / HIS Sincronización", color: "azul-oscuro", sub: "Epidemiología y ficha clínica" },
    { id: "revision", titulo: "Revisión Humana", color: "verde", sub: "Confirmación del profesional de triaje" }
  ];

  /* Acciones disponibles en cada columna */
  const acciones = {
    medicas: [
      { texto: "Ver Monitoreo", icono: "i-monitor", variante: "btn--mini" },
      { texto: "Reevaluar", icono: "i-refresh", variante: "btn--mini btn--peligro" }
    ],
    auditoria: [{ texto: "Validar Token", icono: "i-token", variante: "btn--mini btn--primary" }],
    farmacia: [{ texto: "Reenviar Petición", icono: "i-send", variante: "btn--mini btn--primary" }],
    hce: [
      { texto: "Ajustar", icono: "i-sliders", variante: "btn--mini" },
      { texto: "Validar", icono: "i-check", variante: "btn--mini btn--primary" }
    ],
    revision: [
      { texto: "Ajustar", icono: "i-sliders", variante: "btn--mini" },
      { texto: "Validar", icono: "i-check", variante: "btn--mini btn--primary" }
    ]
  };

  /* --------------------------------------------------------------------
     PACIENTES DEL CENSO ACTIVO
     tipo: alert | vitals | rx | progress | discrepancy
     -------------------------------------------------------------------- */
  const patients = [];

  /* Array vacío a propósito: el censo se alimenta del endpoint, no de datos
     precargados. Es el único punto de sustitución de esta pantalla.

     Contrato de cada registro (los que ya leen las funciones de render):
       id, nombre, edad, doc, nivel, columna, espera, ubicacion,
       responsable, tipo
     y, según `tipo`, uno de estos bloques opcionales:
       alert       -> { motivo }
       vitals      -> { fc: {v,mal}, ta: {v,mal}, sat: {v,mal} }
       rx          -> { farmaco, protocolo, accion }
       progreso    -> { pct, texto }
       discrepancia-> { discrepancia }   (o texto plano en `discrepancia`)

     `nivel` es una clave de `niveles`; `columna`, una de `columnas`. Con el
     array vacío el tablero muestra el estado vacío por columna y el censo
     informa de 0 pacientes. */;

  /* --------------------------------------------------------------------
     UTILIDADES
     -------------------------------------------------------------------- */
  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => Array.prototype.slice.call((ctx || document).querySelectorAll(sel));

  const esc = (txt) =>
    String(txt == null ? "" : txt).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const icon = (id, cls) =>
    '<svg class="icon ' + (cls || "") + '" aria-hidden="true"><use href="#' + id + '"></use></svg>';

  const pad2 = (n) => String(n).padStart(2, "0");
  const nivelDe = (id) => niveles.filter((n) => n.id === id)[0];
  const esVencido = (p) => p.espera > nivelDe(p.nivel).objetivo;
  const mins = (n) => pad2(n) + " min";
  const dosDigitos = (n) => (n < 10 ? "0" + n : String(n));

  /* --------------------------------------------------------------------
     ESTADO LOCAL DE LA VISTA
     -------------------------------------------------------------------- */
  let mtsActivo = "";
  let textoFiltro = "";
  let soloVencidos = false;
  let verAlertas = true;
  let segundosSync = 4;
  let ultimaSync = new Date();
  let temporizadorBusqueda = null;

  /* --------------------------------------------------------------------
     FILTRADO Y ORDEN
     -------------------------------------------------------------------- */
  function coincide(p) {
    if (mtsActivo && p.nivel !== mtsActivo) return false;
    if (soloVencidos && !esVencido(p)) return false;
    const q = textoFiltro;
    if (!q) return true;
    return (
      p.nombre.toLowerCase().indexOf(q) > -1 ||
      p.doc.toLowerCase().indexOf(q) > -1 ||
      p.ubicacion.toLowerCase().indexOf(q) > -1 ||
      p.id.toLowerCase().indexOf(q) > -1
    );
  }

  function visiblesPorColumna(idColumna) {
    return patients
      .filter((p) => p.columna === idColumna && coincide(p))
      .sort((a, b) => {
        const d = nivelDe(a.nivel).orden - nivelDe(b.nivel).orden;
        return d !== 0 ? d : b.espera - a.espera;
      });
  }

  /* --------------------------------------------------------------------
     BARRA DE CENSO
     -------------------------------------------------------------------- */
  function renderCenso() {
    const total = patients.length;
    $("#censoTotal").textContent = total + " pac.";

    $("#censusChips").innerHTML = niveles
      .map((n) => {
        const conteo = patients.filter((p) => p.nivel === n.id).length;
        const on = mtsActivo === n.id;
        return (
          '<button type="button" class="chip chip--' + n.id + (on ? " is-on" : "") + '" data-mts="' + n.id + '"' +
          ' aria-pressed="' + (on ? "true" : "false") + '"' +
          ' title="' + esc(n.nombre + " · " + n.etiqueta + " · objetivo " + n.objetivo + " min") + '">' +
            '<span class="chip__dot" aria-hidden="true"></span>' +
            '<span class="chip__text">' +
              '<span class="chip__name">' + esc(n.nombre) + ' <span class="chip__target">(' + n.objetivo + ' min)</span></span>' +
              '<span class="chip__sub">' + esc(n.etiqueta) + " · <span class=\"chip__count\">" + conteo + "</span> pacientes</span>" +
            "</span>" +
          "</button>"
        );
      })
      .join("");

    /* Badge del sidebar: censo total de la unidad */
    if ($("#navQueueTotal")) $("#navQueueTotal").textContent = total;
  }

  /* --------------------------------------------------------------------
     BLOQUES CONTEXTUALES DE LA TARJETA
     -------------------------------------------------------------------- */
  function bloqueAlert(p) {
    return (
      '<div class="card__blk alert">' +
        '<span class="alert__motivo">' + esc(p.alert.motivo) + "</span>" +
        '<span class="alert__espera">' + dosDigitos(p.espera) + "m en espera</span>" +
      "</div>"
    );
  }

  function bloqueVitals(p) {
    const celda = (etiqueta, dato) =>
      '<span class="vital' + (dato.mal ? " is-alert" : "") + '">' +
        '<span class="vital__k">' + etiqueta + "</span>" +
        '<span class="vital__v">' + esc(dato.v) + "</span>" +
      "</span>";
    return (
      '<div class="card__blk vitals">' +
        celda("FC", p.vitals.fc) +
        celda("TA", p.vitals.ta) +
        celda("SatO2", p.vitals.sat) +
      "</div>"
    );
  }

  function bloqueRx(p) {
    return (
      '<div class="card__blk rx">' +
        '<span class="rx__farmaco">' + esc(p.rx.farmaco) + "</span>" +
        '<span class="rx__meta">' + esc(p.rx.protocolo) + "</span>" +
        '<span class="rx__accion">' + esc(p.rx.accion) + "</span>" +
      "</div>"
    );
  }

  function bloqueProgress(p) {
    const pct = Math.max(0, Math.min(100, p.progreso.pct));
    return (
      '<div class="card__blk progress">' +
        '<span class="progress__top"><span>Trámite pendiente</span><span class="progress__pct">' + pct + " %</span></span>" +
        '<span class="progress__track" role="progressbar" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100"' +
          ' aria-label="' + esc(p.progreso.texto) + '">' +
          '<span class="progress__fill" style="width:' + pct + '%"></span>' +
        "</span>" +
        '<span class="progress__texto">' + esc(p.progreso.texto) + "</span>" +
      "</div>"
    );
  }

  function bloqueDiscrepancy(p) {
    return (
      '<div class="card__blk discrepancy">' + icon("i-alert", "icon--sm") +
        "<span><b>Discordancia IA vs Enfermería:</b> " + esc(p.discrepancia.split(": ")[1] || p.discrepancia) + "</span>" +
      "</div>"
    );
  }

  const bloques = {
    alert: bloqueAlert,
    vitals: bloqueVitals,
    rx: bloqueRx,
    progress: bloqueProgress,
    discrepancy: bloqueDiscrepancy
  };

  /* --------------------------------------------------------------------
     TARJETA DE PACIENTE
     -------------------------------------------------------------------- */
  function tarjeta(p) {
    const n = nivelDe(p.nivel);
    const vencida = esVencido(p);
    const bloque = verAlertas && bloques[p.tipo] ? bloques[p.tipo](p) : "";

    const botones = (acciones[p.columna] || [])
      .map(
        (a) =>
          '<button type="button" class="btn ' + a.variante + '" data-accion="' + esc(a.texto) + '" data-id="' + p.id + '">' +
            icon(a.icono, "icon--sm") + "<span>" + esc(a.texto) + "</span>" +
          "</button>"
      )
      .join("");

    return (
      '<article class="card card--' + p.nivel + (vencida ? " is-overdue" : "") + '"' +
        ' data-id="' + p.id + '" data-nivel="' + p.nivel + '" data-columna="' + p.columna + '"' +
        ' aria-label="' + esc(p.nombre + " · " + n.nombre + " MTS · " + mins(p.espera) + " de espera") + '">' +

        '<div class="card__top">' +
          '<h3 class="card__name" title="' + esc(p.nombre) + '">' + esc(p.nombre) + "</h3>" +
          '<span class="card__time tabnum" title="Tiempo objetivo MTS ' + n.nombre + ": " + n.objetivo + ' min">' + n.objetivo + "m</span>" +
        "</div>" +

        '<p class="card__meta"><b>' + p.edad + " años</b><span aria-hidden=\"true\">·</span><span class=\"card__doc\">" + esc(p.doc) + "</span></p>" +

        bloque +

        '<div class="card__foot">' +
          '<span class="card__espera">Espera: ' + mins(p.espera) + "</span>" +
          '<span title="' + esc(p.ubicacion) + '">' + icon("i-pin", "icon--sm") + esc(p.ubicacion) + "</span>" +
          '<span title="' + esc(p.responsable) + '">' + icon("i-user", "icon--sm") + esc(p.responsable) + "</span>" +
        "</div>" +

        '<div class="card__act">' + botones + "</div>" +
      "</article>"
    );
  }

  /* --------------------------------------------------------------------
     TABLERO
     -------------------------------------------------------------------- */
  function renderTablero() {
    $("#board").innerHTML = columnas
      .map((c) => {
        const lista = visiblesPorColumna(c.id);
        const cuerpo = lista.length
          ? lista.map(tarjeta).join("")
          : '<p class="col__empty">Sin pacientes en esta columna</p>';

        return (
          '<div class="col col--' + c.color + '" data-col="' + c.id + '">' +
            '<div class="col__head">' +
              '<span class="col__dot" aria-hidden="true"></span>' +
              '<h2 class="col__title" title="' + esc(c.titulo) + '">' + esc(c.titulo) + "</h2>" +
              '<span class="col__pill">' + lista.length + " pac.</span>" +
              '<span class="col__sub" title="' + esc(c.sub) + '">' + esc(c.sub) + "</span>" +
            "</div>" +
            '<div class="col__body">' + cuerpo + "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  /* --------------------------------------------------------------------
     RENDER GLOBAL
     -------------------------------------------------------------------- */
  function render() {
    renderCenso();
    renderTablero();
  }

  /* --------------------------------------------------------------------
     SYNC Y RELOJ
     -------------------------------------------------------------------- */
  function pintarSync() {
    $("#syncTexto").textContent = "Sync en vivo (hace " + segundosSync + "s)";
    $("#syncChip").title =
      "Última sincronización con el HIS: " +
      pad2(ultimaSync.getHours()) + ":" + pad2(ultimaSync.getMinutes()) + ":" + pad2(ultimaSync.getSeconds());
  }

  function sincronizar() {
    segundosSync = 0;
    ultimaSync = new Date();
    $("#syncChip").classList.add("is-sync");
    pintarSync();
    window.setTimeout(function () {
      $("#syncChip").classList.remove("is-sync");
    }, 900);
  }

  function pintarReloj() {
    const d = new Date();
    $("#reloj").textContent = "Turno noche · " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  /* --------------------------------------------------------------------
     CHIPS DEL CENSO
     -------------------------------------------------------------------- */
  function initChips() {
    $("#censusChips").addEventListener("click", (e) => {
      const b = e.target.closest(".chip[data-mts]");
      if (!b) return;
      const id = b.dataset.mts;
      mtsActivo = mtsActivo === id ? "" : id;
      render();
    });
  }

  /* --------------------------------------------------------------------
     BUSCADOR (debounce 250 ms)
     -------------------------------------------------------------------- */
  function initBuscador() {
    const input = $("#q");
    input.addEventListener("input", () => {
      window.clearTimeout(temporizadorBusqueda);
      temporizadorBusqueda = window.setTimeout(() => {
        textoFiltro = input.value.trim().toLowerCase();
        render();
      }, 250);
    });

    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  /* --------------------------------------------------------------------
     PANEL DE FILTROS
     -------------------------------------------------------------------- */
  function initFiltros() {
    const btn = $("#btnFiltro");
    const panel = $("#panelFiltro");

    const colocar = () => {
      const r = btn.getBoundingClientRect();
      const w = panel.offsetWidth;
      const left = Math.min(Math.max(8, r.right - w), window.innerWidth - w - 8);
      panel.style.top = r.bottom + 6 + "px";
      panel.style.left = left + "px";
    };

    const cerrarPanel = () => {
      panel.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    };

    const alternar = () => {
      if (panel.hidden) {
        panel.hidden = false;
        btn.setAttribute("aria-expanded", "true");
        colocar();
      } else {
        cerrarPanel();
      }
    };

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      alternar();
    });

    document.addEventListener("click", (e) => {
      if (!panel.hidden && !panel.contains(e.target)) cerrarPanel();
    });

    window.addEventListener("resize", () => {
      if (!panel.hidden) colocar();
    });

    $("#soloVencidos").addEventListener("change", (e) => {
      soloVencidos = e.target.checked;
      render();
    });

    $("#verAlertas").addEventListener("change", (e) => {
      verAlertas = e.target.checked;
      render();
    });

    $("#btnLimpiar").addEventListener("click", () => {
      mtsActivo = "";
      textoFiltro = "";
      soloVencidos = false;
      verAlertas = true;
      $("#q").value = "";
      $("#soloVencidos").checked = false;
      $("#verAlertas").checked = true;
      render();
      toast("Filtros de la vista limpiados. Se muestra el censo completo.", "verde");
    });
  }

  /* --------------------------------------------------------------------
     ACCIONES DE LAS TARJETAS
     -------------------------------------------------------------------- */
  function initTablero() {
    $("#board").addEventListener("click", (e) => {
      const b = e.target.closest("[data-accion]");
      if (!b) return;
      const card = b.closest(".card");
      const p = patients.filter((x) => x.id === card.dataset.id)[0];
      if (!p) return;
      toast(b.dataset.accion + ": " + p.nombre + " (" + nivelDe(p.nivel).nombre + " MTS).", b.classList.contains("btn--peligro") ? "rojo" : "verde");
    });
  }

  /* --------------------------------------------------------------------
     NAVEGACIÓN, MENÚ Y AVISOS
     -------------------------------------------------------------------- */
  function sincronizarNav() {
    const pantalla = document.body.dataset.screen;
    $$(".nav__item[data-nav]").forEach((el) => {
      const activo = el.dataset.nav === pantalla;
      el.classList.toggle("is-active", activo);
      if (activo) el.setAttribute("aria-current", "page");
      else el.removeAttribute("aria-current");
    });
  }

  function initMenu() {
    const btn = $("#userBtn");
    const menu = $("#userMenu");

    const cerrar = () => {
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    };

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const abierto = menu.hidden;
      menu.hidden = !abierto;
      btn.setAttribute("aria-expanded", abierto ? "true" : "false");
    });

    document.addEventListener("click", (e) => {
      if (!menu.hidden && !menu.contains(e.target)) cerrar();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        cerrar();
        $("#panelFiltro").hidden = true;
        $("#btnFiltro").setAttribute("aria-expanded", "false");
      }
    });
    $$(".menu__item").forEach((item) => item.addEventListener("click", cerrar));
  }

  function initAvisos() {
    $$("[data-toast]").forEach((el) =>
      el.addEventListener("click", () => toast(el.dataset.toast, "azul"))
    );
  }

  function toast(mensaje, tono) {
    const host = $("#toastHost");
    const el = document.createElement("div");
    el.className = "toast toast--" + (tono || "verde");
    el.innerHTML = icon(tono === "rojo" ? "i-alert" : "i-check") + '<div class="notice__body">' + esc(mensaje) + "</div>";
    host.appendChild(el);
    window.setTimeout(() => el.remove(), 4600);
  }

  /* --------------------------------------------------------------------
     ARRANQUE
     -------------------------------------------------------------------- */
  function init() {
    sincronizarNav();
    render();
    pintarSync();
    pintarReloj();

    initChips();
    initBuscador();
    initFiltros();
    initTablero();
    initMenu();
    initAvisos();

    /* Reloj de la unidad */
    window.setInterval(pintarReloj, 20000);

    /* Contador del sync en vivo */
    window.setInterval(function () {
      segundosSync += 1;
      pintarSync();
    }, 1000);

    /* Cada 60 s sube la espera de todos los pacientes */
    window.setInterval(function () {
      patients.forEach((p) => {
        p.espera += 1;
      });
      render();
    }, 60000);

    /* Cada 15 s se simula la sincronización con el HIS */
    window.setInterval(sincronizar, 15000);
  }

  init();
})();
