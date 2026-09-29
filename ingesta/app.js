/* ==========================================================================
   MediFlow Clinical Portal — Pantalla Ingesta
   Vanilla JS: datos de ejemplo en arrays + render() que pinta el DOM.
   ========================================================================== */
(function () {
  "use strict";

  /* --------------------------------------------------------------------
     DATOS DE EJEMPLO
     -------------------------------------------------------------------- */

  /* Niveles del sistema de triaje de Manchester (MTS) */
  const data = [
    {
      id: "rojo",
      nombre: "Rojo",
      categoria: "Inmediato",
      sla: 0,
      color: "rojo",
      desc: "Amenaza para la vida: intervención inmediata con equipo de resucitación movilizado.",
      criticos: 1,
      icus: "9,8 % de rescates"
    },
    {
      id: "naranja",
      nombre: "Naranja",
      categoria: "Muy urgente",
      sla: 10,
      color: "naranja",
      desc: "Alta situación de amenaza: valoración médica y tratamiento en los primeros 10 min.",
      criticos: 3,
      icus: "6,4 % de rescates"
    },
    {
      id: "amarillo",
      nombre: "Amarillo",
      categoria: "Urgente",
      sla: 60,
      color: "amarillo",
      desc: "Situación urgente: estable, pero con dolor intenso o resultados que pueden deteriorarse.",
      criticos: 9,
      icus: "1,7 % de rescates"
    },
    {
      id: "verde",
      nombre: "Verde",
      categoria: "Normal",
      sla: 120,
      color: "verde",
      desc: "Situación estándar: dolor moderado controlado, sin factores de riesgo de deterioro.",
      criticos: 14,
      icus: "0,3 % de rescates"
    },
    {
      id: "azul",
      nombre: "Azul",
      categoria: "No urgente",
      sla: 240,
      color: "azul",
      desc: "Estable sin dolor agudo; puede ser derivado a consulta externa o atención primaria.",
      criticos: 21,
      icus: "0,05 % de rescates"
    }
  ];

  /* Motivos de consulta frecuentes en ED-1 (30 días) */
  const motivos = [
    { id: "m1", texto: "Dolor torácico", n: 142 },
    { id: "m2", texto: "Dolor abdominal", n: 118 },
    { id: "m3", texto: "Dificultad respiratoria", n: 96 },
    { id: "m4", texto: "Trauma", n: 74 },
    { id: "m5", texto: "Fiebre alta", n: 61 },
    { id: "m6", texto: "Síncope", n: 43 },
    { id: "m7", texto: "Accidente cerebrovascular", n: 27 },
    { id: "m8", texto: "Reacción alérgica", n: 19 }
  ];

  /* Constantes vitales y sus rangos de referencia (adultos) */
  const constantes = [
    { id: "v-pa", nombre: "Presión arterial", unidad: "mmHg", ref: "Ref. 90–140 / 60–90", tipo: "par",
      rango: { min: 90, max: 140 }, critico: { min: 80, max: 180 }, ejemplo: "128/82" },
    { id: "v-fc", nombre: "Frecuencia cardíaca", unidad: "lpm", ref: "Ref. 50–100", tipo: "simple",
      rango: { min: 50, max: 100 }, critico: { min: 35, max: 130 }, ejemplo: "96" },
    { id: "v-fr", nombre: "Frecuencia respiratoria", unidad: "rpm", ref: "Ref. 12–20", tipo: "simple",
      rango: { min: 12, max: 20 }, critico: { min: 10, max: 28 }, ejemplo: "18" },
    { id: "v-temp", nombre: "Temperatura", unidad: "°C", ref: "Ref. 36,0–37,5", tipo: "simple",
      rango: { min: 36, max: 37.5 }, critico: { min: 35, max: 39.5 }, ejemplo: "36,8" },
    { id: "v-sato2", nombre: "Saturación de O₂", unidad: "%", ref: "Ref. 94–100", tipo: "simple",
      rango: { min: 94, max: 100 }, critico: { min: 90, max: 101 }, ejemplo: "97" },
    { id: "v-gcs", nombre: "Escala de coma de Glasgow", unidad: "/15", ref: "Ref. 13–15", tipo: "simple",
      rango: { min: 13, max: 15 }, critico: { min: 0, max: 8 }, ejemplo: "15" },
    { id: "v-gluc", nombre: "Glucemia capilar", unidad: "mg/dL", ref: "Ref. 70–140", tipo: "simple",
      rango: { min: 70, max: 140 }, critico: { min: 54, max: 300 }, ejemplo: "112" },
    { id: "v-pdi", nombre: "Perímetro de cefálica", unidad: "cm", ref: "Ref. 34–36", tipo: "simple",
      rango: { min: 34, max: 36 }, critico: { min: 0, max: 28 }, ejemplo: "35" }
  ];

  /* Controles de seguridad obligatorios antes de publicar el ingreso */
  const seguridad = [
    { id: "s1", texto: "Identificación del paciente con dos identificadores", ok: true },
    { id: "s2", texto: "Alergias y medication declaradas en el HIS", ok: true },
    { id: "s3", texto: "Consentimiento de atención informatizada firmado", ok: true },
    { id: "s4", texto: "Nivel de riesgo de caída evaluado (escala Morse)", ok: false },
    { id: "s5", texto: "Preaviso al equipo de destino confirmado", ok: false }
  ];

  /* Checklists según nivel MTS: qué debe cumplirse antes de la atención */
  const prioridades = [
    { id: "p1", nivel: "rojo", texto: "Monitor cardíaco y desfibrilador operativo", ok: true },
    { id: "p2", nivel: "rojo", texto: "Vía venosa de dos accesos", ok: true },
    { id: "p3", nivel: "rojo", texto: "Hemograma, coagulograma y grupo de sangre", ok: false },
    { id: "p4", nivel: "naranja", texto: "Monitor de constantes cada 15 min", ok: true },
    { id: "p5", nivel: "naranja", texto: "Analítica urgente solicitada", ok: false },
    { id: "p6", nivel: "amarillo", texto: "Control de constantes cada 60 min", ok: false },
    { id: "p7", nivel: "amarillo", texto: "Analítica diferida programada", ok: false },
    { id: "p8", nivel: "verde", texto: "Registro de analgesia y constantes", ok: false },
    { id: "p9", nivel: "azul", texto: "Derivación a consulta externa", ok: false }
  ];

  /* Ingresos ya presentes en la cola de ED-1 */
  const recientes = [
    { id: "ING-2418", nombre: "Carlos Andrés Ferreira Lima", initials: "CF", edad: 67, mts: "rojo", motivo: "Dolor torácico", espera: 4, destino: "Monitor 2" },
    { id: "ING-2417", nombre: "Lucía Fernández Piriz", initials: "LF", edad: 34, mts: "naranja", motivo: "Dificultad respiratoria", espera: 11, destino: "Sala A · 3" },
    { id: "ING-2416", nombre: "Hugo Nicolás Sosa Herrera", initials: "HS", edad: 51, mts: "naranja", motivo: "Dolor abdominal", espera: 8, destino: "Sala A · 1" },
    { id: "ING-2415", nombre: "Ana Belén Pereira Gómez", initials: "AP", edad: 8, mts: "amarillo", motivo: "Fiebre alta", espera: 38, destino: "Sala B · 2" },
    { id: "ING-2414", nombre: "Jorge Wilson Arocena", initials: "JA", edad: 72, mts: "amarillo", motivo: "Síncope", espera: 52, destino: "Sala B · 4" }
  ];

  /* Totales de los badges del sidebar (idénticos en todas las pantallas) */
  const navTotals = { colas: 0, auditoria: 4 };

  /* --------------------------------------------------------------------
     UTILIDADES
     -------------------------------------------------------------------- */
  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => Array.prototype.slice.call((ctx || document).querySelectorAll(sel));

  const esc = (txt) =>
    String(txt).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const icon = (id, cls) =>
    '<svg class="' + (cls || "icon icon--sm") + '" aria-hidden="true"><use href="#' + id + '"></use></svg>';

  const nivelPorId = (id) => data.find((n) => n.id === id) || null;

  const badgeMts = (nivel, texto) =>
    '<span class="badge badge--' + nivel.color + '"><span class="badge__dot" aria-hidden="true"></span>' +
    esc(texto || (nivel.nombre + " · " + nivel.sla + " min")) + "</span>";

  /* --------------------------------------------------------------------
     RENDER
     -------------------------------------------------------------------- */

  /* 1. Tarjetas de nivel MTS */
  function renderMts() {
    $("#mtsGrid").innerHTML = data
      .map(
        (n) => '<label class="mts-card">' +
        '  <input type="radio" name="mts" id="mts-' + n.id + '" value="' + n.id + '">' +
        '  <span class="mts-card__box" data-tone="' + n.color + '">' +
        '    <span class="mts-card__check">' + icon("i-check") + "</span>" +
        '    <span class="mts-card__head">' +
        '      <span class="mts-card__name">' + esc(n.nombre) + "</span>" +
        '      <span class="mts-card__sla">≤ ' + n.sla + " min</span>" +
        "    </span>" +
        '    <span class="mts-card__desc">' + esc(n.desc) + "</span>" +
        '    <span class="mts-card__foot">' +
        badgeMts(n, n.categoria) +
        '      <span class="chip">' + n.criticos + " hoy</span>" +
        "    </span>" +
        "  </span>" +
        "</label>"
      )
      .join("");

    $$("#mtsGrid input[name='mts']").forEach((radio) => {
      radio.addEventListener("change", onMtsChange);
    });
  }

  /* 2. Motivos frecuentes */
  function renderMotivos() {
    $("#motivos").innerHTML = motivos
      .map(
        (m) => '<button type="button" class="filter motivo-chip" data-motivo="' + m.id + '" aria-pressed="false">' +
          esc(m.texto) + ' <span class="motivo-chip__count">' + m.n + "</span></button>"
      )
      .join("");

    $$("#motivos .motivo-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const activo = chip.classList.toggle("is-on");
        chip.setAttribute("aria-pressed", String(activo));
        agregarAlDetalle(chip.dataset.motivo, activo);
      });
    });
  }

  /* 3. Constantes vitales */
  function renderVitals() {
    $("#vitals").innerHTML = constantes
      .map(
        (v) => '<div class="vital" data-vital="' + v.id + '">' +
        '  <label class="vital__label" for="' + v.id + '" title="' + esc(v.nombre) + '">' + esc(v.nombre) + "</label>" +
        '  <span class="vital__control">' +
        '    <input class="input" id="' + v.id + '" inputmode="' + (v.tipo === "par" ? "text" : "decimal") + '"' +
        '           placeholder="' + esc(v.ejemplo) + '" data-vital-input="' + v.id + '"' +
        '           aria-describedby="' + v.id + '-ref">' +
        '    <span class="vital__unit" aria-hidden="true">' + esc(v.unidad) + "</span>" +
        "  </span>" +
        '  <span class="vital__ref" id="' + v.id + '-ref"><span data-ref="' + v.id + '">' + esc(v.ref) + "</span></span>" +
        "</div>"
      )
      .join("");

    $$("[data-vital-input]").forEach((input) => {
      input.addEventListener("input", () => evaluarVital(input));
      input.addEventListener("blur", () => evaluarVital(input));
    });
  }

  /* 4. Ingresos recientes */
  function renderRecientes() {
    $("#recientes").innerHTML = recientes
      .map(
        (r) => '<li><a class="recientes__item" href="../colas/index.html" title="' + esc(r.nombre) + " · " + esc(r.id) + '">' +
        '  <span class="idcell__avatar" aria-hidden="true">' + esc(r.initials) + "</span>" +
        '  <span class="recientes__body">' +
        '    <span class="recientes__name">' + esc(r.nombre) + "</span>" +
        '    <span class="recientes__meta" title="' + esc(r.id + " · " + r.edad + " años · " + r.motivo) + '">' +
          esc(r.id) + " · " + r.edad + " años · " + esc(r.motivo) + "</span>" +
        "  </span>" +
        '  <span class="recientes__espera">' +
          badgeMts({ color: r.mts }, nivelPorId(r.mts).nombre) +
          '    <b class="tabnum">' + r.espera + " min</b>" +
          '    <span class="nowrap">' + esc(r.destino) + "</span>" +
        "  </span>" +
        "</a></li>"
      )
      .join("");
  }

  /* 5. Controles de seguridad */
  function renderSeguridad() {
    $("#seguridad").innerHTML = seguridad
      .map(
        (s) => '<div class="priority-list__item ' + (s.ok ? "" : "is-pending") + '">' +
          icon(s.ok ? "i-check" : "i-alert") +
          '<span class="priority-list__text" title="' + esc(s.texto) + '">' + esc(s.texto) + "</span>" +
          "</div>"
      )
      .join("");
  }

  /* 6. Checklist del nivel MTS seleccionado */
  function renderPrioridad(nivelId) {
    const box = $("#resumenAlertas");
    if (!nivelId) {
      box.innerHTML = '<div class="notice notice--azul">' + icon("i-layers") +
        '<div class="notice__body"><strong>Selecciona un nivel MTS</strong> para activar el checklist de atención y el temporizador de la cola.</div></div>';
      return;
    }
    const nivel = nivelPorId(nivelId);
    const items = prioridades.filter((p) => p.nivel === nivelId);
    const faltan = items.filter((p) => !p.ok).length;

    box.innerHTML =
      '<div class="notice notice--' + nivel.color + '">' + icon("i-shield") +
      '<div class="notice__body"><strong>Checklist ' + esc(nivel.nombre) + "</strong> · " +
      (items.length - faltan) + " de " + items.length + " completados" +
      (faltan ? " · faltan " + faltan + " antes de publicar" : " · listo para publicar") + "</div></div>" +
      '<div class="priority-list">' +
      items
        .map(
          (p) => '<div class="priority-list__item ' + (p.ok ? "" : "is-pending") + '">' +
            icon(p.ok ? "i-check" : "i-alert") +
            '<span class="priority-list__text" title="' + esc(p.texto) + '">' + esc(p.texto) + "</span></div>"
        )
        .join("") +
      "</div>";
  }

  /* 7. Resumen del triaje */
  function renderResumen() {
    const marcado = $('input[name="mts"]:checked');
    const nivel = nivelPorId(marcado ? marcado.value : null);
    const priors = $("#resumenPrio");

    priors.style.setProperty("--c", nivel ? "var(--mts-" + nivel.color + ")" : "#94A3B8");
    priors.style.setProperty("--c-ink", nivel ? "var(--mts-" + nivel.color + "-ink)" : "var(--text)");
    priors.style.setProperty("--c-bg", nivel ? "var(--mts-" + nivel.color + "-bg)" : "#F1F5F9");
    priors.style.setProperty("--c-bd", nivel ? "var(--mts-" + nivel.color + "-border)" : "var(--border)");

    $("#resumenNivel").textContent = nivel ? nivel.nombre + " · " + nivel.categoria : "Sin asignar";
    $("#resumenSla").textContent = nivel
      ? "Atención máxima ≤ " + nivel.sla + " min · " + nivel.icus
      : "Selecciona un nivel MTS";

    const f = (id) => ($("#" + id) ? $("#" + id).value.trim() : "");
    const sexo = $('input[name="sexo"]:checked');
    const vitales = constantes.filter((v) => f(v.id).length > 0).length;
    const anom = constantes.filter((v) => { const c = estadoVital(v); return c === "alerta" || c === "critico"; }).length;

    $("#resumenDl").innerHTML = [
      ["Cédula", f("doc") || "—"],
      ["Paciente", f("nom") || "—"],
      ["Edad / sexo", f("nac") ? f("nac") + " · " + (sexo ? sexo.value : "—") : "—"],
      ["Motivo", f("detalle") ? f("detalle").slice(0, 40) + (f("detalle").length > 40 ? "…" : "") : "—"],
      ["Dolor EVA", f("eva") + "/10"],
      ["Constantes", vitales + " de " + constantes.length + (anom ? " · " + anom + " alteradas" : "")],
      ["Destino", f("destino") || "—"],
      ["Médico", f("medico") || "—"]
    ]
      .map((r) => "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>")
      .join("");

    renderPrioridad(nivel ? nivel.id : null);

    $("#chipEstado").innerHTML = nivel
      ? icon("i-check") + '<span class="nowrap">Nivel asignado: ' + esc(nivel.nombre) + "</span>"
      : icon("i-clipboard") + '<span class="nowrap">Borrador sin confirmar</span>';

    $("#mtsHint").className = "badge " + (nivel ? "badge--" + nivel.color : "badge--azul");
    $("#mtsHint").innerHTML = nivel
      ? '<span class="badge__dot" aria-hidden="true"></span>' + esc(nivel.nombre + " · " + nivel.sla + " min")
      : "Selecciona un nivel";
  }

  function render() {
    renderMts();
    renderMotivos();
    renderVitals();
    renderRecientes();
    renderSeguridad();
    renderResumen();
    sincronizarNav();
  }

  /* --------------------------------------------------------------------
     LÓGICA DE CONSTANTES VITALES
     -------------------------------------------------------------------- */
  const toNum = (txt) => {
    const n = parseFloat(String(txt).replace(",", ".").replace(/[^\d.]/g, ""));
    return isNaN(n) ? null : n;
  };

  function estadoVital(v) {
    const valor = $("#" + v.id) ? $("#" + v.id).value.trim() : "";
    if (!valor) return "vacio";

    if (v.tipo === "par") {
      const partes = valor.split("/").map(toNum);
      if (partes.length < 2 || partes[0] === null || partes[1] === null) return "alerta";
      const sis = partes[0];
      if (sis < v.critico.min || sis > v.critico.max) return "critico";
      if (sis < v.rango.min || sis > v.rango.max) return "alerta";
      return "ok";
    }

    const n = toNum(valor);
    if (n === null) return "alerta";
    if (n < v.critico.min || n > v.critico.max) return "critico";
    if (n < v.rango.min || n > v.rango.max) return "alerta";
    return "ok";
  }

  function evaluarVital(input) {
    const v = constantes.find((c) => c.id === input.dataset.vitalInput);
    if (!v) return;
    const cont = input.closest(".vital");
    const estado = estadoVital(v);
    const ref = cont.querySelector("[data-ref]");

    cont.classList.remove("is-ok", "is-alerta", "is-critico");

    if (estado === "vacio") {
      ref.textContent = v.ref;
      renderResumen();
      return;
    }

    cont.classList.add("is-" + estado);
    const etiquetas = {
      ok: "En rango",
      alerta: "Fuera de rango",
      critico: "Valor crítico"
    };
    ref.innerHTML = '<span class="vital__flag">' + icon("i-activity") + etiquetas[estado] + "</span> · " + esc(v.ref);
    renderResumen();
  }

  function tomarDelMonitor() {
    constantes.forEach((v) => {
      const input = $("#" + v.id);
      input.value = v.ejemplo;
      evaluarVital(input);
    });
    toast("Constantes importadas del monitor LE-1 (paquete de 22:39 h).", "verde");
  }

  /* --------------------------------------------------------------------
     FORMULARIO
     -------------------------------------------------------------------- */
  function calcularEdad() {
    const nac = $("#nac").value;
    if (!nac) { $("#edadHint").textContent = "— años"; return; }
    const hoy = new Date();
    const fecha = new Date(nac + "T00:00:00");
    let años = hoy.getFullYear() - fecha.getFullYear();
    const mes = hoy.getMonth() - fecha.getMonth();
    if (mes < 0 || (mes === 0 && hoy.getDate() < fecha.getDate())) años--;
    $("#edadHint").textContent = años + (años === 1 ? " año" : " años") + (años < 18 ? " · menor de edad" : "");
  }

  function validarDoc(input) {
    const digitos = input.value.replace(/\D/g, "");
    const ok = digitos.length === 8 || digitos.length === 9;
    input.classList.toggle("is-invalid", input.value.length > 0 && !ok);
    input.setAttribute("aria-invalid", String(input.value.length > 0 && !ok));
    $("#docHint").textContent = ok ? "Cédula verificada contra el padrón" : "Formato UY: 8 dígitos + verificador";
    return ok;
  }

  function agregarAlDetalle(motivoId, activo) {
    const motivo = motivos.find((m) => m.id === motivoId);
    if (!motivo) return;
    const area = $("#detalle");
    if (activo) {
      const previo = area.value.trim();
      area.value = previo ? previo + "; " + motivo.texto.toLowerCase() : motivo.texto + ": ";
      area.focus();
    } else {
      area.value = area.value.split("; ").filter((t) => t.toLowerCase() !== motivo.texto.toLowerCase()).join("; ");
    }
    area.dispatchEvent(new Event("input"));
  }

  function limpiar() {
    $("#formPaciente").reset();
    $("#detalle").value = "";
    $("#obs").value = "";
    $("#detalle").classList.remove("is-invalid");
    $("#detalleLen").textContent = "0";
    $$('input[name="mts"]').forEach((r) => (r.checked = false));
    $$(".motivo-chip").forEach((c) => { c.classList.remove("is-on"); c.setAttribute("aria-pressed", "false"); });
    renderVitals();
    $("#eva").value = 4;
    $("#evaVal").textContent = "4";
    $("#docHint").textContent = "Formato UY: 8 dígitos + verificador";
    calcularEdad();
    renderResumen();
    toast("Formulario limpio. Listo para un nuevo ingreso.");
  }

  function validarFormulario() {
    const errores = [];
    const doc = $("#doc");
    if (!doc.value.trim()) errores.push("La cédula es obligatoria.");
    else if (!validarDoc(doc)) errores.push("El formato de la cédula no es válido (8 dígitos + verificador).");
    if (!$("#nom").value.trim()) errores.push("El nombre del paciente es obligatorio.");
    if (!$("#nac").value) errores.push("La fecha de nacimiento es obligatoria.");
    const detalle = $("#detalle").value.trim();
    if (!detalle) errores.push("Describe el motivo de consulta.");
    else if (detalle.length < 25) errores.push("Amplía el motivo de consulta (mínimo 25 caracteres).");
    if (!$('input[name="mts"]:checked')) errores.push("Selecciona el nivel de triaje MTS.");

    $$(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
    return errores;
  }

  /* --------------------------------------------------------------------
     CONFIRMACIÓN
     -------------------------------------------------------------------- */
  function abrirModal() {
    const errores = validarFormulario();
    if (errores.length) {
      toast(errores[0], "rojo");
      const foco = $("#doc");
      if (!$("#doc").value.trim()) foco.classList.add("is-invalid");
      if (!$("#detalle").value.trim()) $("#detalle").classList.add("is-invalid");
      $("#mtsGrid").scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    const nivel = nivelPorId($('input[name="mts"]:checked').value);
    const filas = [
      ["Cédula", $("#doc").value],
      ["Destino", $("#destino").value],
      ["Temporizador", "Inicia al publicar"]
    ];
    $("#modalBody").innerHTML =
      '<p>Se publicará el ingreso de <strong>' + esc($("#nom").value) + "</strong> en la cola de <strong>ED-1</strong> con prioridad " +
      badgeMts(nivel) + ".</p>" +
      '<dl class="dl" style="margin:10px 0 0">' +
      filas.map((r) => "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>").join("") +
      "</dl>";

    const modal = $("#modalConfirmar");
    modal.hidden = false;
    $("#btnConfirmarFinal").focus();
  }

  function cerrarModal() {
    $("#modalConfirmar").hidden = true;
    $("#btnConfirmar").focus();
  }

  function confirmar() {
    const nivel = nivelPorId($('input[name="mts"]:checked').value);
    cerrarModal();
    const chip = $("#chipEstado");
    chip.className = "chip";
    chip.innerHTML = icon("i-check") + '<span class="nowrap">Ingreso publicado · ' + esc(nivel.nombre) + "</span>";
    toast("Ingreso publicado en la cola ED-1 con prioridad " + nivel.nombre + ". Temporizador iniciado.", "verde");
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
    el.innerHTML = icon(tono === "rojo" ? "i-alert" : "i-check") + '<div class="notice__body">' + esc(mensaje) + "</div>";
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

    $("#nac").addEventListener("change", calcularEdad);
    $("#doc").addEventListener("blur", () => validarDoc($("#doc")));
    $("#detalle").addEventListener("input", (ev) => {
      $("#detalleLen").textContent = ev.target.value.length;
      renderResumen();
    });
    $("#eva").addEventListener("input", (ev) => { $("#evaVal").textContent = ev.target.value; });
    $("#eva").addEventListener("change", renderResumen);
    $("#btnVitals").addEventListener("click", tomarDelMonitor);
    $("#btnLimpiar").addEventListener("click", limpiar);
    $("#btnConfirmar").addEventListener("click", abrirModal);
    $("#btnConfirmarFinal").addEventListener("click", confirmar);
    $$("[data-close-modal]").forEach((b) => b.addEventListener("click", cerrarModal));
    $("#modalConfirmar").addEventListener("click", (ev) => { if (ev.target.id === "modalConfirmar") cerrarModal(); });
    $$("[data-toast]").forEach((b) => b.addEventListener("click", () => toast(b.dataset.toast, "verde")));

    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        $("#q").focus();
      }
      if (ev.key === "Escape" && !$("#modalConfirmar").hidden) cerrarModal();
    });

    const hoy = new Date();
    const reloj = $(".page-head__actions .badge--navy");
    if (reloj) {
      reloj.innerHTML = icon("i-calendar", "icon icon--sm") +
        '<span class="nowrap">Turno noche · ' +
        String(hoy.getHours()).padStart(2, "0") + ":" + String(hoy.getMinutes()).padStart(2, "0") + "</span>";
    }
  }

  function onMtsChange() { renderResumen(); }

  document.addEventListener("DOMContentLoaded", init);
})();
