/* ==========================================================================
   MediFlow Clinical Portal — Pantalla Auditoría Algorítmica
   Supervisión humana (HITL) sobre la inferencia diagnóstica MTS-AI.
   ========================================================================== */
(function () {
  "use strict";

  /* --------------------------------------------------------------------
     UTILIDADES
     -------------------------------------------------------------------- */
  const $ = (sel, raiz) => (raiz || document).querySelector(sel);
  const $$ = (sel, raiz) => Array.prototype.slice.call((raiz || document).querySelectorAll(sel));

  function esc(t) {
    return String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function icon(id, extra) {
    return '<svg class="icon ' + (extra || "") + '" aria-hidden="true"><use href="#' + id + '"></use></svg>';
  }

  function toast(mensaje, tono) {
    const host = $("#toastHost");
    const el = document.createElement("div");
    el.className = "toast toast--" + (tono || "verde");
    el.innerHTML =
      icon(tono === "rojo" ? "i-alert" : tono === "naranja" ? "i-shield-search" : "i-check") +
      '<div class="notice__body">' + esc(mensaje) + "</div>";
    host.appendChild(el);
    window.setTimeout(() => el.remove(), 4600);
  }

  /* --------------------------------------------------------------------
     CONSTANTES DE DOMINIO
     -------------------------------------------------------------------- */
  const MEDICO = "Dr. M. Vance, MD";
  const FIRMA = "MED-99120-VANCE";
  const UMBRAL = 0.6;
  const UMBRAL_RAPIDA = 0.55;

  const MTS = {
    rojo: { id: "rojo", nivel: 1, min: 0, color: "Rojo", base: "Inmediato", orden: 0, tono: ["--mts-rojo", "--mts-rojo-ink", "--mts-rojo-bg", "--mts-rojo-border"] },
    naranja: { id: "naranja", nivel: 2, min: 10, color: "Naranja", base: "Muy Urgente", orden: 1, tono: ["--mts-naranja", "--mts-naranja-ink", "--mts-naranja-bg", "--mts-naranja-border"] },
    amarillo: { id: "amarillo", nivel: 3, min: 60, color: "Amarillo", base: "Urgente", orden: 2, tono: ["--mts-amarillo", "--mts-amarillo-ink", "--mts-amarillo-bg", "--mts-amarillo-border"] }
  };

  const TABS = [
    { id: "todos", texto: "Todos" },
    { id: "critico", texto: "Críticos", tone: "rojo" },
    { id: "discrepancia", texto: "Discrepancias" },
    { id: "revision", texto: "En revisión" }
  ];

  const FILTROS_VITALES = {
    PA: { ref: "100-180 / 60-90", min: 90, max: 180, critLo: 90, critHi: 200, plausMin: 50, plausMax: 260, paso: 1, def: "120" },
    FC: { ref: "60-100 lpm", min: 60, max: 100, critLo: 45, critHi: 130, plausMin: 30, plausMax: 220, paso: 1, def: "80" },
    SpO2: { ref: "≥ 95 %", min: 95, max: 100, critLo: 88, critHi: 101, plausMin: 50, plausMax: 100, paso: 1, def: "98" },
    FR: { ref: "12-20 rpm", min: 12, max: 20, critLo: 8, critHi: 30, plausMin: 6, plausMax: 60, paso: 1, def: "16" },
    T: { ref: "36.0-37.5 °C", min: 36, max: 37.5, critLo: 35.5, critHi: 38.5, plausMin: 30, plausMax: 43, paso: 0.1, def: "36.8" },
    GLUC: { ref: "70-140 mg/dL", min: 70, max: 140, critLo: 54, critHi: 250, plausMin: 20, plausMax: 600, paso: 1, def: "95" },
    EVA: { ref: "0-3", min: 0, max: 3, critLo: -1, critHi: 7, plausMin: 0, plausMax: 10, paso: 1, def: "2" },
    Glasgow: { ref: "3-15", min: 9, max: 15, critLo: 8, critHi: 16, plausMin: 3, plausMax: 15, paso: 1, def: "15" },
    Pupilas: { texto: true, valores: ["Isocóricas", "Anisocoría D", "Anisocoría I", "Midriáticas", "No reactivas"], def: "Isocóricas" }
  };

  const UNIDADES = { PA: "mmHg", FC: "lpm", SpO2: "%", FR: "rpm", T: "°C", GLUC: "mg/dL", EVA: "", Glasgow: "", Pupilas: "" };

  /* --------------------------------------------------------------------
     DOCUMENTOS PAUSADOS POR EL MODELO
     Estructura de ejemplo con marcadores genéricos: sin datos clínicos
     reales. Sustituir por la respuesta del endpoint de auditoría.
     -------------------------------------------------------------------- */
  const docs = [
    {
      id: "AUD-0001",
      paciente: "Nombre del paciente",
      edad: null,
      dni: "00.000.000-0",
      nivelMTS: "rojo",
      mtsSufijo: "Nivel MTS reservado",
      ubicacion: "Ubicación / box",
      origen: "Origen del ingreso",
      nota: "Descripción del motivo de ingreso.",
      vitales: {
        PA: { v: "—", n: null },
        FC: { v: "—", n: null },
        SpO2: { v: "—", n: null },
        FR: { v: "—", n: null },
        T: { v: "—", n: null },
        Glasgow: { v: "—", n: null },
        Pupilas: { v: "—", mal: false }
      },
      diagA: "Diagnóstico A (alerta)",
      diagB: "Diagnóstico B (alternativo)",
      discriminador: "Discriminador clínico detectado por el modelo.",
      advertencia: "Advertencia del modelo pendiente de validación clínica.",
      score: 0.32,
      estado: "critico",
      estadoIA: "Estado inferido por MTS-AI",
      gravedad: "rojo",
      espera: 4,
      maxEspera: 0
    },
    {
      id: "AUD-0002",
      paciente: "Nombre del paciente",
      edad: null,
      dni: "00.000.000-0",
      nivelMTS: "rojo",
      mtsSufijo: "Nivel MTS reservado",
      ubicacion: "Ubicación / box",
      origen: "Origen del ingreso",
      nota: "Descripción del motivo de ingreso.",
      vitales: {
        PA: { v: "—", n: null },
        FC: { v: "—", n: null },
        SpO2: { v: "—", n: null },
        FR: { v: "—", n: null },
        T: { v: "—", n: null },
        Glasgow: { v: "—", n: null },
        Pupilas: { v: "—", mal: false }
      },
      diagA: "Diagnóstico A (alerta)",
      diagB: "Diagnóstico B (alternativo)",
      discriminador: "Discriminador clínico detectado por el modelo.",
      advertencia: "Advertencia del modelo pendiente de validación clínica.",
      score: 0.45,
      estado: "critico",
      estadoIA: "Estado inferido por MTS-AI",
      gravedad: "rojo",
      espera: 7,
      maxEspera: 0
    },
    {
      id: "AUD-0003",
      paciente: "Nombre del paciente",
      edad: null,
      dni: "00.000.000-0",
      nivelMTS: "naranja",
      ubicacion: "Ubicación / box",
      origen: "Origen del ingreso",
      antecedentes: "Antecedentes relevantes del paciente.",
      vitales: {
        PA: { v: "—", n: null },
        FC: { v: "—", n: null },
        SpO2: { v: "—", n: null },
        FR: { v: "—", n: null },
        T: { v: "—", n: null },
        GLUC: { v: "—", n: null }
      },
      diagA: "Diagnóstico A (alerta)",
      diagB: "Diagnóstico B (alternativo)",
      discriminador: "Discriminador clínico detectado por el modelo.",
      advertencia: "Advertencia del modelo pendiente de validación clínica.",
      score: 0.55,
      estado: "discrepancia",
      estadoIA: "Estado inferido por MTS-AI",
      gravedad: "naranja",
      espera: 8,
      maxEspera: 10
    },
    {
      id: "AUD-0004",
      paciente: "Nombre del paciente",
      edad: null,
      dni: "00.000.000-0",
      nivelMTS: "amarillo",
      ubicacion: "Ubicación / box",
      origen: "Origen del ingreso",
      antecedentes: "Antecedentes relevantes del paciente.",
      vitales: {
        PA: { v: "—", n: null },
        FC: { v: "—", n: null },
        SpO2: { v: "—", n: null },
        FR: { v: "—", n: null },
        T: { v: "—", n: null },
        EVA: { v: "—", n: null }
      },
      diagA: "Diagnóstico A (alerta)",
      diagB: "Diagnóstico B (alternativo)",
      discriminador: "Discriminador clínico detectado por el modelo.",
      advertencia: "Advertencia del modelo pendiente de validación clínica.",
      score: 0.61,
      estado: "discrepancia",
      estadoIA: "Estado inferido por MTS-AI",
      gravedad: "amarillo",
      espera: 19,
      maxEspera: 60
    },
    {
      id: "AUD-0005",
      paciente: "Nombre del paciente",
      edad: null,
      dni: "00.000.000-0",
      nivelMTS: "naranja",
      ubicacion: "Ubicación / box",
      origen: "Origen del ingreso",
      antecedentes: "Antecedentes relevantes del paciente.",
      vitales: {
        PA: { v: "—", n: null },
        FC: { v: "—", n: null },
        SpO2: { v: "—", n: null },
        FR: { v: "—", n: null },
        T: { v: "—", n: null },
        GLUC: { v: "—", n: null }
      },
      diagA: "Diagnóstico A (alerta)",
      diagB: "Diagnóstico B (alternativo)",
      discriminador: "Discriminador clínico detectado por el modelo.",
      advertencia: "Advertencia del modelo pendiente de validación clínica.",
      score: 0.78,
      estado: "revision",
      estadoIA: "Estado inferido por MTS-AI",
      gravedad: "naranja",
      espera: 13,
      maxEspera: 10
    }
  ];

  /* --------------------------------------------------------------------
     REGISTRO DE AUDITORÍA
     Cada acción firmada deja una traza {accion, fecha, medico}.
     -------------------------------------------------------------------- */
  const registro = [];

  /* --------------------------------------------------------------------
     ESTADO
     -------------------------------------------------------------------- */
  let filtro = "todos";
  let busqueda = "";
  let docAprobar = null;
  let docRechazar = null;
  let docEditar = null;
  let dialogoActual = null;
  let ultimoFoco = null;
  let analyzing = false;

  /* --------------------------------------------------------------------
     CÁLCULOS
     -------------------------------------------------------------------- */
  const pendientes = () => docs.filter((d) => !d.resuelto);
  const porId = (id) => docs.find((d) => d.id === id) || null;

  function nivelDe(id) {
    return MTS[id] || MTS.amarillo;
  }

  function mtsTexto(d) {
    const n = nivelDe(d.nivelMTS);
    return n.color + " Nivel " + n.nivel + " (" + n.min + " min) – " + n.base + (d.mtsSufijo ? " / " + d.mtsSufijo : "");
  }

  /* El score alimenta el ancho de la barra, el orden y los umbrales de
     validación, pero nunca se muestra como número: solo como banda. */
  const BANDA = { baja: "Confianza baja", media: "Confianza media", alta: "Confianza alta" };

  function bandaConfianza(score) {
    if (score < 0.5) return "baja";
    if (score < UMBRAL) return "media";
    return "alta";
  }

  const VERDE = ["--mts-verde", "--mts-verde-ink", "--mts-verde-bg", "--mts-verde-border"];

  function tonoConfianza(score) {
    if (score < 0.5) return MTS.rojo.tono;
    if (score < UMBRAL) return MTS.naranja.tono;
    return VERDE;
  }

  function estiloTono(tono) {
    return "--c:" + tono[0] + ";--c-ink:" + tono[1] + ";--c-bg:" + tono[2] + ";--c-bd:" + tono[3];
  }

  function ordenVitales(d) {
    return d.vitales.Glasgow
      ? ["PA", "FC", "SpO2", "FR", "T", "Glasgow", "Pupilas"]
      : ["PA", "FC", "SpO2", "FR", "T", "GLUC"];
  }

  function normalizar(t) {
    return String(t)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function visibles() {
    const q = normalizar(busqueda.trim());
    return pendientes()
      .filter((d) => (filtro === "todos" ? true : d.estado === filtro))
      .filter((d) => {
        if (!q) return true;
        return (
          normalizar(d.id).indexOf(q) !== -1 ||
          normalizar(d.paciente).indexOf(q) !== -1 ||
          normalizar(d.dni).indexOf(q) !== -1 ||
          normalizar(d.ubicacion).indexOf(q) !== -1 ||
          normalizar(d.estadoIA).indexOf(q) !== -1 ||
          normalizar(d.diagA).indexOf(q) !== -1 ||
          normalizar(d.diagB).indexOf(q) !== -1
        );
      })
      .sort((a, b) => {
        const g = nivelDe(a.gravedad).orden - nivelDe(b.gravedad).orden;
        return g !== 0 ? g : a.score - b.score;
      });
  }

  /* --------------------------------------------------------------------
     RENDER — banner, pestañas y lista
     -------------------------------------------------------------------- */
  function renderBanner() {
    const p = pendientes();
    const bajos = p.filter((d) => d.score < UMBRAL).length;
    const criticos = p.filter((d) => d.estado === "critico").length;
    const disc = p.filter((d) => d.estado === "discrepancia").length;
    const revision = p.filter((d) => d.estado === "revision").length;
    const ok = p.length > 0 && bajos === 0;

    const banner = $("#alertBanner");
    banner.classList.toggle("alert-banner--ok", ok);
    $("#alertTitulo").textContent = ok
      ? "Lote Validado por Supervisión Humana"
      : "Revisión Algorítmica Requerida";
    $("#alertTotal").textContent = String(p.length);
    $("#alertParrafo").innerHTML = p.length
      ? '<span id="alertTotal">' + p.length + "</span> documentos clínicos críticos han sido pausados por el modelo de inferencia diagnóstica MTS-AI. " +
        "Requieren validación y firma facultativa presencial antes de su derivación a las colas definitivas del Servicio de Urgencias."
      : "No quedan documentos pendientes de validación. El lote completo ha sido firmado y derivado a las colas del Servicio de Urgencias.";

    const badge = $("#alertBadge");
    badge.className = "badge " + (ok ? "badge--verde" : "badge--rojo") + " alert-banner__badge";
    badge.innerHTML = icon("i-gauge", "icon--sm") + (ok ? "CONFIANZA SOBRE UMBRAL" : "NIVEL DE CONFIANZA BAJO");

    $("#alertKpis").innerHTML = [
      { v: p.length, l: "Pendientes", t: "rojo" },
      { v: bajos, l: "Bajo umbral", t: "naranja" },
      { v: criticos, l: "Críticos", t: "rojo" },
      { v: disc, l: "Discrepancias", t: "naranja" },
      { v: revision, l: "En revisión", t: "azul" }
    ]
      .map((k) => '<div class="alert-kpi alert-kpi--' + k.t + '">' +
        '<span class="alert-kpi__value">' + k.v + "</span>" +
        '<span class="alert-kpi__label">' + k.l + "</span></div>")
      .join("");

    $("#navAuditTotal").textContent = String(p.length);
    $("#latencia").textContent = analyzing ? "—" : "112ms";
  }

  function renderTabs() {
    const p = pendientes();
    const cuenta = {
      todos: p.length,
      critico: p.filter((d) => d.estado === "critico").length,
      discrepancia: p.filter((d) => d.estado === "discrepancia").length,
      revision: p.filter((d) => d.estado === "revision").length
    };
    $("#tabsFiltro").innerHTML = TABS.map(
      (t) =>
        '<button type="button" class="filter' + (filtro === t.id ? " is-on" : "") + (t.tone ? " filter--mts" : "") + '"' +
        (t.tone ? ' data-tone="' + t.tone + '"' : "") +
        ' data-filtro="' + t.id + '" aria-pressed="' + (filtro === t.id) + '">' +
        t.texto + '<span class="filter__count">' + cuenta[t.id] + "</span></button>"
    ).join("");
  }

  function zonaVitales(d) {
    return (
      '<section class="audit-card__zone audit-card__zone--vitales" aria-label="Signos vitales">' +
      '<div class="zone-label">' + icon("i-activity") + "Signos Vitales</div>" +
      '<div class="vitals">' +
      ordenVitales(d)
        .map((k) => {
          const f = FILTROS_VITALES[k];
          const v = d.vitales[k];
          const esTexto = f.texto;
          const crit = !esTexto && v.n !== null && (v.n < f.critLo || v.n > f.critHi);
          const mal = crit || v.mal === true;
          const unidad = UNIDADES[k] && !esTexto ? f.ref.indexOf(UNIDADES[k]) === -1 ? " " + UNIDADES[k] : "" : "";
          return (
            '<div class="vital' + (crit ? " vital--crit" : mal ? " vital--mal" : "") + '">' +
            '<span class="vital__k">' + k + "</span>" +
            '<span class="vital__v">' + esc(v.v) + unidad + "</span>" +
            '<span class="vital__r">' + esc(esTexto ? "" : f.ref) + "</span>" +
            "</div>"
          );
        })
        .join("") +
      "</div>" +
      notaHTML(d) +
      "</section>"
    );
  }

  function zonaIA(d) {
    return (
      '<section class="audit-card__zone audit-card__zone--ia" aria-label="Inferencia diagnóstica">' +
      '<div class="ia__head">' +
      '<span class="ia__label">' + icon("i-compare", "icon--sm") + "Diagnóstico / discriminador detectado</span>" +
      '<span class="ia__estado">' + icon("i-shield-search", "icon--sm") + esc(d.estadoIA) + "</span>" +
      "</div>" +
      '<div class="dx-compare">' +
      '<div class="dx dx--a"><span class="dx__k">Diagnóstico A · alerta</span><span class="dx__v">' + esc(d.diagA) + "</span></div>" +
      '<span class="dx__vs">vs</span>' +
      '<div class="dx dx--b"><span class="dx__k">Diagnóstico B · alternativo</span><span class="dx__v">' + esc(d.diagB) + "</span></div>" +
      "</div>" +
      '<div class="disc"><span class="disc__k">Razonamiento discriminador</span>' + esc(d.discriminador) + "</div>" +
      '<div class="warn" style="' + estiloTono(nivelDe(d.gravedad).tono) + '">' +
      icon("i-alert") + "<span><strong>Advertencia:</strong> " + esc(d.advertencia) + "</span></div>" +
      "</section>"
    );
  }

  function zonaConfianza(d) {
    const tono = estiloTono(tonoConfianza(d.score));
    const banda = bandaConfianza(d.score);
    const estadoTxt =
      d.score < 0.5 ? "Por debajo del umbral" : d.score < UMBRAL ? "En zona de revisión" : "Sobre el umbral";
    return (
      '<section class="audit-card__zone audit-card__zone--conf" style="' + tono + '" aria-label="Confianza del algoritmo">' +
      '<div class="zone-label">' + icon("i-gauge") + "Confianza del Algoritmo</div>" +
      '<p class="conf__pct"><span class="conf__band conf__band--' + banda + '">' + BANDA[banda] + "</span>" +
      '<span class="conf__state">' + estadoTxt + "</span></p>" +
      '<div class="conf__bar" role="img" aria-label="Barra de confianza del algoritmo MTS-AI: ' + BANDA[banda] + '">' +
      '<span class="conf__fill" style="width:' + Math.max(2, d.score * 100) + '%"></span>' +
      '<span class="conf__marker" aria-hidden="true"></span></div>' +
      '<div class="conf__scale" aria-hidden="true"><span>Baja</span><span>Media</span><span>Alta</span></div>' +
      '<p class="conf__cut">Umbral de corte aplicado en validación</p>' +
      '<div class="conf__acts">' +
      '<button type="button" class="btn btn--sm" data-accion="editar" data-id="' + d.id + '">' + icon("i-pencil", "icon--sm") + "Editar datos</button>" +
      '<button type="button" class="btn btn--sm btn--outline-rojo" data-accion="rechazar" data-id="' + d.id + '">' + icon("i-x", "icon--sm") + "Rechazar</button>" +
      '<button type="button" class="btn btn--sm ' + (d.nivelMTS === "rojo" ? "btn--aprobar-rojo" : "btn--primary") + '" data-accion="aprobar" data-id="' + d.id + '">' +
      icon("i-check", "icon--sm") + "Aprobar</button>" +
      "</div></section>"
    );
  }

  function notaHTML(d) {
    if (d.antecedentes) {
      return '<div class="vitals-note"><strong>Antecedentes:</strong>' + esc(d.antecedentes) + "</div>";
    }
    if (d.nota) {
      return '<div class="vitals-note"><strong>Episodio:</strong>' + esc(d.nota) + "</div>";
    }
    return "";
  }

  function tarjetaHTML(d) {
    const retraso = d.espera - d.maxEspera;
    const agotado = retraso > 0;

    return (
      '<article class="audit-card audit-card--' + d.nivelMTS + '" data-doc="' + d.id + '" aria-label="Auditoría ' + esc(d.id) + '">' +

      '<header class="audit-card__head">' +
      '<div class="audit-card__idline">' +
      '<span class="mts-badge" title="Nivel MTS oficial asignado por MTS-AI"><span class="mts-badge__dot" aria-hidden="true"></span>' + esc(mtsTexto(d)) + "</span>" +
      '<span class="doc-id">' + esc(d.id) + "</span>" +
      (d.editado
        ? '<span class="edited-flag" title="Datos validados o corregidos por facultativo">' + icon("i-pencil") + "Editado por humano</span>"
        : "") +
      '<span class="audit-card__lugar" title="Ubicación del paciente">' + icon("i-inbox", "icon--sm") + esc(d.ubicacion) + "</span>" +
      "</div>" +
      '<div class="audit-card__identity">' +
      '<strong class="audit-card__paciente">' + esc(d.paciente) + "</strong>" +
      '<span class="audit-card__datos">' + (d.edad === null ? "Edad y DNI reservados" : d.edad + " años · DNI " + esc(d.dni)) + "</span>" +
      "</div>" +
      '<div class="audit-card__idline">' +
      '<span class="audit-card__timer' + (agotado ? " audit-card__timer--late" : "") + '">' + icon("i-clock", "icon--sm") +
      "Espera: " + String(d.espera).padStart(2, "0") + " min / " + d.maxEspera + " min máx</span>" +
      (agotado
        ? '<span class="audit-card__timerlate">' + icon("i-alert", "icon--sm") + "TIEMPO AGOTADO: " + String(retraso).padStart(2, "0") + " min de retraso</span>"
        : "") +
      '<span class="audit-card__origen" title="Origen del ingreso">' + icon("i-logout", "icon--sm") + esc(d.origen) + "</span>" +
      "</div></header>" +

      '<div class="audit-card__body">' + zonaVitales(d) + zonaIA(d) + zonaConfianza(d) + "</div>" +
      "</article>"
    );
  }

  function render() {
    renderBanner();
    renderTabs();
    const lista = visibles();
    $("#listaDocs").innerHTML = lista.map(tarjetaHTML).join("");
    $("#audVacio").hidden = lista.length > 0;
    if (!lista.length) {
      const vacio = $("#audVacio");
      vacio.querySelector(".empty__title").textContent = pendientes().length
        ? "No hay documentos que coincidan con el filtro"
        : "No hay documentos pendientes de auditoría";
      vacio.querySelector(".empty__text").textContent = pendientes().length
        ? "Cambia de pestaña en la barra de herramientas o limpia el buscador para volver a ver el lote completo."
        : "Todos los documentos del lote han sido validados y derivados a las colas del Servicio de Urgencias.";
    }
  }

  /* --------------------------------------------------------------------
     MODALES: apertura, cierre y trampa de foco
     -------------------------------------------------------------------- */
  const FOCALIZABLES =
    'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  function abrirDialogo(id, focoInicial) {
    const dlg = $("#" + id);
    if (dialogoActual) cerrarDialogo(false);
    ultimoFoco = document.activeElement;
    dlg.hidden = false;
    document.body.classList.add("is-locked");
    dialogoActual = dlg;
    const inicial = focoInicial || dlg.querySelector(FOCALIZABLES);
    if (inicial) inicial.focus();
    dlg.addEventListener("keydown", trampaFoco);
  }

  function cerrarDialogo(restaurar) {
    if (!dialogoActual) return;
    dialogoActual.removeEventListener("keydown", trampaFoco);
    dialogoActual.hidden = true;
    document.body.classList.remove("is-locked");
    dialogoActual = null;
    if (restaurar !== false && ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
    ultimoFoco = null;
  }

  function trampaFoco(ev) {
    if (ev.key !== "Tab") return;
    const nodos = $$(FOCALIZABLES, dialogoActual).filter((n) => n.offsetParent !== null || n === document.activeElement);
    if (!nodos.length) return;
    const primero = nodos[0];
    const ultimo = nodos[nodos.length - 1];
    if (ev.shiftKey && document.activeElement === primero) {
      ev.preventDefault();
      ultimo.focus();
    } else if (!ev.shiftKey && document.activeElement === ultimo) {
      ev.preventDefault();
      primero.focus();
    }
  }

  /* --------------------------------------------------------------------
     ACCIONES
     -------------------------------------------------------------------- */
  function anotar(accion, id) {
    registro.push({
      accion: accion,
      documento: id,
      fecha: new Date().toLocaleString("es-ES", { dateStyle: "short", timeStyle: "medium" }),
      medico: MEDICO,
      firma: FIRMA
    });
  }

  function retirar(doc, alResolver) {
    const el = document.querySelector('[data-doc="' + doc.id + '"]');
    let hecho = false;
    const cerrar = () => {
      if (hecho) return;
      hecho = true;
      alResolver();
      render();
    };
    if (!el) return cerrar();
    el.classList.add("audit-card--saliendo");
    el.addEventListener("animationend", cerrar, { once: true });
    /* Respaldo si la animación se suprime por prefers-reduced-motion. */
    window.setTimeout(cerrar, 500);
  }

  /* --- Aprobar --- */
  function pedirAprobar(id) {
    const d = porId(id);
    if (!d || d.resuelto) return;
    docAprobar = d;
    const rojo = d.nivelMTS === "rojo";

    $("#mAprobarIconBox").className = "side__unit-icon" + (rojo ? " side__unit-icon--rojo" : "");
    $("#mAprobarIconUse").setAttribute("href", rojo ? "#i-alert" : "#i-check");
    $("#mAprobarTitulo").textContent = rojo ? "Confirmar aprobación de nivel Rojo" : "Confirmar aprobación de triaje";
    $("#mAprobarCta").textContent = rojo ? "Firmar y aprobar nivel Rojo" : "Firmar y aprobar";
    $("#mAprobarRojo").hidden = !rojo;
    $("#chkRojo").checked = false;
    $("#btnAprobarOk").disabled = rojo;

    $("#mAprobarResumen").innerHTML =
      "<dl class=\"dl\">" +
      [
        ["Documento", d.id],
        ["Paciente", d.paciente],
        ["Nivel MTS", mtsTexto(d)],
        ["Ubicación", d.ubicacion],
        ["Diagnóstico A", d.diagA],
        ["Confianza", BANDA[bandaConfianza(d.score)]]
      ]
        .map((r) => "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>")
        .join("") +
      "</dl>";

    $("#mAprobarHora").textContent =
      "Sello temporal aplicado al confirmar · " + new Date().toLocaleString("es-ES", { dateStyle: "short", timeStyle: "medium" });

    abrirDialogo("modalAprobar", rojo ? $("#chkRojo") : $("#btnAprobarOk"));
  }

  function confirmarAprobar() {
    const d = docAprobar;
    if (!d) return;
    if (d.nivelMTS === "rojo" && !$("#chkRojo").checked) {
      toast("Debes confirmar la valoración presencial para aprobar un nivel Rojo.", "rojo");
      return;
    }
    anotar("aprobado", d.id);
    const rojo = d.nivelMTS === "rojo";
    cerrarDialogo();
    retirar(d, () => {
      d.resuelto = true;
    });
    toast("Documento " + d.id + " aprobado y firmado por " + MEDICO + (rojo ? " · escalado a Jefatura de ED-1." : "."), "verde");
    docAprobar = null;
  }

  /* --- Rechazar --- */
  function pedirRechazar(id) {
    const d = porId(id);
    if (!d || d.resuelto) return;
    docRechazar = d;
    $("#mRechazarIntro").innerHTML =
      "El documento <strong>" + esc(d.id) + "</strong> de <strong>" + esc(d.paciente) + "</strong> se retirará de la auditoría algorítmica y volverá al circuito de triaje humano.";
    $("#txtMotivo").value = "";
    $("#motivoCont").textContent = "0";
    $("#mRechazarError").hidden = true;
    abrirDialogo("modalRechazar", $("#txtMotivo"));
  }

  function confirmarRechazar() {
    const d = docRechazar;
    if (!d) return;
    const motivo = $("#txtMotivo").value.trim();
    if (motivo.length < 10) {
      $("#mRechazarError").hidden = false;
      $("#txtMotivo").focus();
      return;
    }
    d.motivo = motivo;
    anotar("rechazado", d.id);
    cerrarDialogo();
    retirar(d, () => {
      d.resuelto = true;
    });
    toast("Documento " + d.id + " rechazado y devuelto a triaje humano.", "naranja");
    docRechazar = null;
  }

  /* --- Editar --- */
  function pedirEditar(id) {
    const d = porId(id);
    if (!d || d.resuelto) return;
    docEditar = d;

    $("#edNivel").innerHTML = Object.keys(MTS)
      .map(
        (k) =>
          '<option value="' + k + '"' + (d.nivelMTS === k ? " selected" : "") + ">" +
          MTS[k].color + " — " + MTS[k].base + "</option>"
      )
      .join("");
    $("#edUbicacion").value = d.ubicacion;
    $("#edDiagA").value = d.diagA;
    $("#edDiagB").value = d.diagB;
    $("#edDiscriminador").value = d.discriminador;

    $("#edVitales").innerHTML = ordenVitales(d)
      .map((k) => {
        const f = FILTROS_VITALES[k];
        const v = d.vitales[k];
        if (f.texto) {
          return (
            '<div class="field col-4"><label class="field__label" for="edV_' + k + '">' + k + "</label>" +
            '<select class="select" id="edV_' + k + '">' +
            f.valores.map((o) => '<option' + (o === v.v ? " selected" : "") + ">" + esc(o) + "</option>").join("") +
            "</select></div>"
          );
        }
        const unidad = UNIDADES[k] ? " (" + UNIDADES[k] + ")" : "";
        return (
          '<div class="field col-4"><label class="field__label" for="edV_' + k + '">' + k + "</label>" +
          '<input class="input" id="edV_' + k + '" type="number" inputmode="decimal" step="' + f.paso + '"' +
          ' min="' + f.plausMin + '" max="' + f.plausMax + '" value="' + esc(v.n === null ? "" : v.n) + '"' +
          ' data-unidad="' + esc(UNIDADES[k]) + '" data-paso="' + f.paso + '" data-clave="' + k + '"></div>'
        );
      })
      .join("");

    $("#mEditarError").hidden = true;
    abrirDialogo("modalEditar", $("#edUbicacion"));
  }

  function confirmarEditar() {
    const d = docEditar;
    if (!d) return;

    let valido = true;
    let subio = false;

    ordenVitales(d).forEach((k) => {
      const f = FILTROS_VITALES[k];
      const campo = $("#edV_" + k);
      if (!campo) return;
      campo.classList.remove("input--error");

      if (f.texto) {
        d.vitales[k].v = campo.value;
        d.vitales[k].mal = campo.value !== "Isocóricas" && campo.value !== "Midriáticas";
        return;
      }
      const bruto = campo.value.trim();
      if (bruto === "") {
        d.vitales[k].v = "—";
        d.vitales[k].n = null;
        return;
      }
      const n = parseFloat(bruto.replace(",", "."));
      if (isNaN(n) || n < f.plausMin || n > f.plausMax) {
        campo.classList.add("input--error");
        valido = false;
        return;
      }
      d.vitales[k].n = n;
      d.vitales[k].v = f.paso < 1 ? n.toFixed(1) : String(n);
      if (n > f.critHi) subio = true;
    });

    if (!valido) {
      $("#mEditarError").hidden = false;
      return;
    }

    const nivelNuevo = $("#edNivel").value;
    if (nivelNuevo !== d.nivelMTS) {
      const gravedadAntes = nivelDe(d.gravedad).orden;
      const gravedadDespues = nivelDe(nivelNuevo).orden;
      d.nivelMTS = nivelNuevo;
      d.gravedad = nivelNuevo;
      /* Un salto hacia un nivel más urgente obliga a subir la confianza. */
      if (gravedadDespues < gravedadAntes) subio = true;
      d.mtsSufijo = null;
    }
    d.ubicacion = $("#edUbicacion").value.trim() || d.ubicacion;
    d.diagA = $("#edDiagA").value.trim() || d.diagA;
    d.diagB = $("#edDiagB").value.trim() || d.diagB;
    d.discriminador = $("#edDiscriminador").value.trim() || d.discriminador;

    d.editado = true;
    d.score = Math.min(0.99, Math.round((d.score + 0.05 + (subio ? 0.03 : 0)) * 100) / 100);
    anotar("editado", d.id);

    cerrarDialogo();
    render();
    toast(
      "Datos guardados, confianza recalculada a " + BANDA[bandaConfianza(d.score)].toLowerCase() + " y marcado como editado por humano.",
      "verde"
    );
    docEditar = null;
  }

  /* --- Reanalizar lote --- */
  function reanalizar() {
    if (analyzing) return;
    const p = pendientes();
    if (!p.length) {
      toast("No hay documentos pendientes que reanalizar.", "naranja");
      return;
    }
    analyzing = true;
    $("#btnReanalizar").disabled = true;
    $("#btnReanalizar").classList.add("is-loading");
    renderBanner();

    window.setTimeout(() => {
      let cambiados = 0;
      p.forEach((d) => {
        const delta = (Math.random() * 0.3 - 0.15);
        const nuevo = Math.min(0.93, Math.max(0.28, Math.round((d.score + delta) * 100) / 100));
        if (nuevo !== d.score) cambiados++;
        d.score = nuevo;
      });
      analyzing = false;
      $("#btnReanalizar").disabled = false;
      $("#btnReanalizar").classList.remove("is-loading");
      render();
      toast("Lote reprocesado con MTS-AI v5.2: " + cambiados + " de " + p.length + " documentos con confianza recalculada.", "naranja");
    }, 1400);
  }

  /* --- Aprobación rápida asistida --- */
  function elegiblesRapida() {
    return pendientes().filter((d) => d.score >= UMBRAL_RAPIDA && d.nivelMTS !== "rojo");
  }

  function pedirRapida() {
    const lista = elegiblesRapida();
    if (!lista.length) {
      toast("No hay documentos con confianza suficiente para aprobación rápida.", "naranja");
      return;
    }
    $("#mRapidaLista").innerHTML = lista
      .map(
        (d) =>
          "<li>" + icon("i-file-check") +
          '<span class="rapida__who">' + esc(d.paciente) + " · " + esc(d.id) + "</span>" +
          '<span class="rapida__n rapida__n--' + bandaConfianza(d.score) + '">' + BANDA[bandaConfianza(d.score)] + "</span></li>"
      )
      .join("");
    $("#mRapidaCta").textContent = "Aprobar " + lista.length + (lista.length === 1 ? " documento" : " documentos");
    abrirDialogo("modalRapida", $("#btnRapidaOk"));
  }

  function confirmarRapida() {
    const lista = elegiblesRapida();
    if (!lista.length) return;
    lista.forEach((d) => {
      anotar("aprobado", d.id);
      d.resuelto = true;
    });
    cerrarDialogo();
    render();
    toast(lista.length + (lista.length === 1 ? " documento aprobado" : " documentos aprobados") + " en lote por " + MEDICO + ".", "verde");
  }

  /* --------------------------------------------------------------------
     CHROME: menú de usuario, avisos y atajos
     -------------------------------------------------------------------- */
  function initMenu() {
    const btn = $("#userBtn");
    const menu = $("#userMenu");
    const cerrar = () => {
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    };
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      menu.hidden = !menu.hidden;
      btn.setAttribute("aria-expanded", String(!menu.hidden));
    });
    document.addEventListener("click", (ev) => {
      if (!menu.hidden && !menu.contains(ev.target)) cerrar();
    });
    $$(".menu__item", menu).forEach((i) => i.addEventListener("click", cerrar));
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !menu.hidden) {
        cerrar();
        btn.focus();
      }
    });
  }

  function initEventos() {
    $("#tabsFiltro").addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-filtro]");
      if (!b) return;
      filtro = b.dataset.filtro;
      render();
    });

    $("#listaDocs").addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-accion]");
      if (!b) return;
      const id = b.dataset.id;
      if (b.dataset.accion === "aprobar") pedirAprobar(id);
      else if (b.dataset.accion === "rechazar") pedirRechazar(id);
      else if (b.dataset.accion === "editar") pedirEditar(id);
    });

    let t;
    $("#q").addEventListener("input", (ev) => {
      window.clearTimeout(t);
      const v = ev.target.value;
      t = window.setTimeout(() => {
        busqueda = v;
        render();
      }, 250);
    });

    $("#btnReanalizar").addEventListener("click", reanalizar);
    $("#btnRapida").addEventListener("click", pedirRapida);
    $("#btnAprobarOk").addEventListener("click", confirmarAprobar);
    $("#btnRechazarOk").addEventListener("click", confirmarRechazar);
    $("#btnEditarOk").addEventListener("click", confirmarEditar);
    $("#btnRapidaOk").addEventListener("click", confirmarRapida);

    $("#chkRojo").addEventListener("change", (ev) => {
      $("#btnAprobarOk").disabled = !ev.target.checked;
    });

    $("#txtMotivo").addEventListener("input", (ev) => {
      const largo = ev.target.value.trim().length;
      $("#motivoCont").textContent = String(Math.min(largo, 999));
      if (largo >= 10) $("#mRechazarError").hidden = true;
    });

    $$("[data-close-modal]").forEach((b) => b.addEventListener("click", () => cerrarDialogo()));

    $$(".modal").forEach((m) =>
      m.addEventListener("mousedown", (ev) => {
        if (ev.target === m) cerrarDialogo();
      })
    );

    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && dialogoActual) {
        cerrarDialogo();
        return;
      }
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === "f" || ev.key === "k")) {
        ev.preventDefault();
        $("#q").focus();
        $("#q").select();
      }
    });

    $$("[data-toast]").forEach((el) => el.addEventListener("click", () => toast(el.dataset.toast, "azul")));
    $("#lnkRegistro").addEventListener("click", (ev) => {
      ev.preventDefault();
      toast(
        registro.length
          ? "Registro de auditoría: " + registro.length + (registro.length === 1 ? " acción firmada." : " acciones firmadas.")
          : "Registro de auditoría: sin acciones firmadas en esta sesión.",
        "azul"
      );
    });
  }

  function init() {
    render();
    initMenu();
    initEventos();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

