/* ==========================================================================
   MediFlow Clinical Portal — Pantalla Historial
   Repositorio documental: un único apply() filtra -> ordena -> pagina -> pinta.
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
      icon(tono === "rojo" ? "i-alert" : tono === "naranja" ? "i-funnel" : "i-check") +
      '<div class="notice__body">' + esc(mensaje) + "</div>";
    host.appendChild(el);
    window.setTimeout(() => el.remove(), 4600);
  }

  /* Búsqueda insensible a mayúsculas y acentos */
  function norm(texto) {
    return String(texto)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  const collator = new Intl.Collator("es", { numeric: true, sensitivity: "base" });

  /* --------------------------------------------------------------------
     CATÁLOGOS
     -------------------------------------------------------------------- */
  const MTS = {
    urgente: { nombre: "Urgente", orden: 0 },
    rutina: { nombre: "Rutina", orden: 1 },
    pendiente: { nombre: "Pendiente", orden: 2 }
  };

  const ESTADOS = {
    recibido: { id: "recibido", nombre: "Recibido", orden: 0 },
    procesado: { id: "procesado", nombre: "Procesado", orden: 1 },
    auditoria: { id: "auditoria", nombre: "Auditoría", orden: 2 }
  };

  const TIPOS = {
    "Informe de urgencias": "i-notes",
    "Informe de enfermería": "i-clipboard",
    Analítica: "i-flask",
    "Analítica de orina": "i-flask",
    Ecografía: "i-image",
    "Radiografía de tórax": "i-image",
    "Tomografía computizada": "i-image",
    Electrocardiograma: "i-activity",
    Receta: "i-pill",
    Consentimiento: "i-file-check"
  };

  const COLUMNAS = {
    id: { etiqueta: "ID de documento", tipo: "texto" },
    paciente: { etiqueta: "Paciente", tipo: "texto" },
    tipo: { etiqueta: "Tipo de documento", tipo: "texto" },
    prioridad: { etiqueta: "Prioridad", tipo: "prioridad" },
    estado: { etiqueta: "Estado", tipo: "estado" },
    fecha: { etiqueta: "Fecha", tipo: "fecha" },
    ruta: { etiqueta: "Ruta de almacenamiento", tipo: "texto" }
  };

  /* --------------------------------------------------------------------
     REGISTROS
     Filas de ejemplo con marcadores genéricos: sin datos de pacientes.
     Este array es el único punto de sustitución: reemplazar por la
     respuesta del endpoint de documentos al conectar el backend.
     -------------------------------------------------------------------- */
  const records = window.MediFlowDocuments.documents.map(window.MediFlowDocuments.toRow);

  /* --------------------------------------------------------------------
     ESTADO CENTRAL
     -------------------------------------------------------------------- */
  const state = {
    query: "",
    prioridad: "todos",
    estado: "todos",
    sortBy: "fecha",
    sortDir: "desc",
    page: 1,
    pageSize: 10
  };

  const PARAMETROS = { query: "q", prioridad: "prioridad", estado: "estado", sortBy: "orden", sortDir: "dir", page: "pagina", pageSize: "por" };

  /* --------------------------------------------------------------------
     PIPELINE: filtrar -> ordenar -> paginar -> renderizar
     -------------------------------------------------------------------- */
  function filtrar() {
    const q = norm(state.query.trim());
    return records.filter((r) => {
      if (state.prioridad !== "todos" && r.prioridad !== state.prioridad) return false;
      if (state.estado !== "todos" && r.estado !== state.estado) return false;
      if (!q) return true;
      return (
        norm(r.id).indexOf(q) !== -1 ||
        norm(r.paciente).indexOf(q) !== -1 ||
        norm(r.ruta).indexOf(q) !== -1 ||
        norm(r.ingreso).indexOf(q) !== -1 ||
        norm(r.tipo).indexOf(q) !== -1
      );
    });
  }

  function ordenar(lista) {
    const col = COLUMNAS[state.sortBy];
    const signo = state.sortDir === "asc" ? 1 : -1;
    return lista.slice().sort((a, b) => {
      let cmp = 0;
      if (state.sortBy === "fecha") {
        cmp = new Date(a.fecha).getTime() - new Date(b.fecha).getTime();
      } else if (col.tipo === "prioridad") {
        cmp = MTS[a.prioridad].orden - MTS[b.prioridad].orden;
      } else if (col.tipo === "estado") {
        cmp = ESTADOS[a.estado].orden - ESTADOS[b.estado].orden;
      } else {
        cmp = collator.compare(String(a[state.sortBy]), String(b[state.sortBy]));
      }
      if (cmp === 0) cmp = collator.compare(a.id, b.id);
      return cmp * signo;
    });
  }

  function apply(opciones) {
    const filtrados = ordenar(filtrar());
    const totalPaginas = Math.max(1, Math.ceil(filtrados.length / state.pageSize));
    if (state.page > totalPaginas) state.page = totalPaginas;
    if (state.page < 1) state.page = 1;

    const desde = (state.page - 1) * state.pageSize;
    const pagina = filtrados.slice(desde, desde + state.pageSize);

    renderCabeceras();
    renderFilas(pagina);
    renderPaginacion(filtrados.length, totalPaginas, desde, pagina.length);
    renderContador(filtrados.length);
    renderFiltrosActivos();
    if (!(opciones && opciones.silentioURL)) sincronizarURL();
  }

  /* --------------------------------------------------------------------
     RENDER
     -------------------------------------------------------------------- */
  function renderCabeceras() {
    $$("#theadHist th").forEach((th) => {
      const activa = th.dataset.sort === state.sortBy;
      th.setAttribute("aria-sort", activa ? (state.sortDir === "asc" ? "ascending" : "descending") : "none");
    });
  }

  function fechaTexto(iso) {
    if (!iso) return { dia: "No informada", hora: "" };
    const d = new Date(iso);
    const p = (n) => String(n).padStart(2, "0");
    return {
      dia: p(d.getDate()) + "/" + p(d.getMonth() + 1) + "/" + d.getFullYear(),
      hora: p(d.getHours()) + ":" + p(d.getMinutes())
    };
  }

  function renderFilas(lista) {
    $("#tbodyHist").innerHTML = lista
      .map((r) => {
        const prioridad = MTS[r.prioridad];
        const est = ESTADOS[r.estado];
        const f = fechaTexto(r.fecha);
        const alternativa = r.estado === "recibido" && r.recibidoAzul === true;
        /* El identificador puede traer un segmento de año intercalado; si no
           lo trae, se conserva tal cual. */
        return (
          "<tr>" +
          '<td><button type="button" class="linkbtn" data-document="' + esc(r.id) + '">' + esc(r.id) + '</button></td>' +

          '<td><div class="idcell"><span class="idcell__avatar" aria-hidden="true">' + esc(iniciales(r.paciente)) + "</span>" +
          '<span class="idcell__text"><span class="idcell__name" title="' + esc(r.paciente) + '">' + esc(r.paciente) + "</span>" +
          '<span class="idcell__meta">DNI ' + esc(r.dni) + " · " + esc(r.ingreso) + "</span></span></div></td>" +

          '<td><div class="tipo-doc" title="' + esc(r.tipo) + '">' + icon(TIPOS[r.tipo] || "i-notes", "icon--sm") +
          '<span class="tipo-doc__txt">' + esc(r.tipo) + "</span></div></td>" +

          '<td><span class="prioridad-tag prioridad-tag--' + r.prioridad + '" title="' + esc(prioridad.nombre) + '">' +
          '<span class="prioridad-tag__dot" aria-hidden="true"></span>' + esc(prioridad.nombre) + "</span></td>" +

          '<td><span class="estado-chip estado-chip--' + r.estado + (alternativa ? " estado-chip--alt" : "") + '">' +
          '<span class="estado-chip__dot" aria-hidden="true"></span>' + esc(est.nombre) + "</span></td>" +

          '<td><span class="fecha">' + f.dia + '<span class="sub">' + f.hora + "</span></span></td>" +

          '<td><div class="ruta-cell"><span class="ruta" title="' + esc(r.ruta) + '">' + esc(r.ruta) + "</span>" +
          '<button type="button" class="btn-copiar" data-ruta="' + esc(r.ruta) + '" title="Copiar ruta de almacenamiento" aria-label="Copiar ruta de almacenamiento de ' + esc(r.id) + '">' +
          icon("i-copy", "icon--sm") + "Copiar</button></div></td>" +

          "</tr>"
        );
      })
      .join("");

    $("#vacio").hidden = lista.length > 0;
  }

  function iniciales(nombre) {
    return nombre
      .split(" ")
      .filter((p) => p.length > 2)
      .slice(0, 2)
      .map((p) => p.charAt(0).toUpperCase())
      .join("");
  }

  function renderContador(matching) {
    $("#contador").textContent = "Mostrando " + matching + " de " + records.length + " registros";
  }

  function renderFiltrosActivos() {
    const partes = [];
    if (state.query.trim()) {
      partes.push('<span class="filtro-tag">Búsqueda: <b>' + esc(state.query.trim()) + "</b></span>");
    }
    if (state.prioridad !== "todos") {
      partes.push(
        '<span class="filtro-tag filtro-tag--prioridad" style="--ac:var(--prioridad-' + state.prioridad + ');--ac-bg:var(--prioridad-' + state.prioridad + '-bg);--ac-bd:var(--prioridad-' + state.prioridad + '-border);--ac-ink:var(--prioridad-' + state.prioridad + '-ink)">' +
          '<span class="filtro-tag--dot" aria-hidden="true"></span>' + esc(MTS[state.prioridad].nombre) + "</span>"
      );
    }
    if (state.estado !== "todos") {
      partes.push('<span class="filtro-tag filtro-tag--estado">' + esc(ESTADOS[state.estado].nombre) + "</span>");
    }
    const orden = COLUMNAS[state.sortBy].etiqueta + (state.sortDir === "asc" ? " ↑" : " ↓");
    partes.push('<span class="filtro-tag">Orden: <b>' + esc(orden) + "</b></span>");
    $("#filtrosActivos").innerHTML = partes.join("");
  }

  function ventanaPaginas(total, actual) {
    if (total <= 7) return Array.from({ length: total }, (x, i) => i + 1);
    if (actual <= 4) return [1, 2, 3, 4, 5, "gap", total];
    if (actual >= total - 3) return [1, "gap", total - 4, total - 3, total - 2, total - 1, total];
    return [1, "gap", actual - 1, actual, actual + 1, "gap", total];
  }

  function renderPaginacion(matching, totalPaginas, desde, enPagina) {
    $("#btnPrev").disabled = state.page <= 1;
    $("#btnNext").disabled = state.page >= totalPaginas;

    $("#rangoInfo").textContent = matching
      ? "Filas " + (desde + 1) + "–" + (desde + enPagina) + " · página " + state.page + " de " + totalPaginas
      : "Sin filas que mostrar";

    $("#paginas").innerHTML = ventanaPaginas(totalPaginas, state.page)
      .map((p) =>
        p === "gap"
          ? '<span class="page-gap" aria-hidden="true">…</span>'
          : '<button type="button" class="page-btn' + (p === state.page ? " is-on" : "") + '" data-pagina="' + p + '"' +
            (p === state.page ? ' aria-current="page"' : "") + ' aria-label="Página ' + p + '">' + p + "</button>"
      )
      .join("");
  }

  /* --------------------------------------------------------------------
     SINCRONIZACIÓN CON LA URL
     -------------------------------------------------------------------- */
  function leerURL() {
    const p = new URLSearchParams(window.location.search);
    const q = p.get(PARAMETROS.query);
    if (q !== null) state.query = q;
    const prioridad = p.get(PARAMETROS.prioridad);
    if (prioridad && MTS[prioridad]) state.prioridad = prioridad;
    const est = p.get(PARAMETROS.estado);
    if (est && ESTADOS[est]) state.estado = est;
    const orden = p.get(PARAMETROS.sortBy);
    if (orden && COLUMNAS[orden]) state.sortBy = orden;
    const dir = p.get(PARAMETROS.sortDir);
    if (dir === "asc" || dir === "desc") state.sortDir = dir;
    const por = parseInt(p.get(PARAMETROS.pageSize), 10);
    if ([10, 25, 50].indexOf(por) !== -1) state.pageSize = por;
    const pagina = parseInt(p.get(PARAMETROS.page), 10);
    if (pagina > 0) state.page = pagina;
  }

  function sincronizarURL() {
    const p = new URLSearchParams();
    if (state.query.trim()) p.set(PARAMETROS.query, state.query.trim());
    if (state.prioridad !== "todos") p.set(PARAMETROS.prioridad, state.prioridad);
    if (state.estado !== "todos") p.set(PARAMETROS.estado, state.estado);
    if (state.sortBy !== "fecha" || state.sortDir !== "desc") {
      p.set(PARAMETROS.sortBy, state.sortBy);
      p.set(PARAMETROS.sortDir, state.sortDir);
    }
    if (state.pageSize !== 10) p.set(PARAMETROS.pageSize, state.pageSize);
    if (state.page !== 1) p.set(PARAMETROS.page, state.page);
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
  }

  /* --------------------------------------------------------------------
     COPIAR AL PORTAPAPELES
     -------------------------------------------------------------------- */
  function copiarTexto(texto) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(texto);
    }
    return new Promise((resolve, reject) => {
      const area = document.createElement("textarea");
      area.value = texto;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (e) {
        ok = false;
      }
      area.remove();
      ok ? resolve() : reject(new Error("sin acceso al portapapeles"));
    });
  }

  function copiarRuta(boton) {
    const ruta = boton.dataset.ruta;
    copiarTexto(ruta)
      .then(() => {
        boton.classList.add("is-ok");
        boton.innerHTML = icon("i-check", "icon--sm") + "Copiado ✓";
        window.setTimeout(() => {
          boton.classList.remove("is-ok");
          boton.innerHTML = icon("i-copy", "icon--sm") + "Copiar";
        }, 1800);
      })
      .catch(() => toast("No se pudo copiar. Ruta: " + ruta, "naranja"));
  }

  /* --------------------------------------------------------------------
     ACCIONES
     -------------------------------------------------------------------- */
  function limpiarFiltros(silencioso) {
    state.query = "";
    state.prioridad = "todos";
    state.estado = "todos";
    state.page = 1;
    $("#qHist").value = "";
    $("#selMts").value = "todos";
    $("#selEstado").value = "todos";
    apply({ silenciosoURL: silencioso });
    if (!silencioso) toast("Filtros y búsqueda restablecidos.", "naranja");
  }

  function alternarOrden(columna) {
    if (state.sortBy === columna) {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
      state.sortBy = columna;
      state.sortDir = columna === "fecha" ? "desc" : "asc";
    }
    state.page = 1;
    apply();
  }

  function irAPagina(pagina) {
    state.page = pagina;
    apply();
    const cabecera = $(".table-card");
    if (cabecera) cabecera.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* --------------------------------------------------------------------
     CHROME: navegación, menú, avisos
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
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      menu.hidden = !menu.hidden;
      btn.setAttribute("aria-expanded", String(!menu.hidden));
    });
    document.addEventListener("click", (ev) => {
      if (!menu.hidden && !menu.contains(ev.target)) cerrar();
    });
    $$(".menu__item").forEach((item) => item.addEventListener("click", cerrar));
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !menu.hidden) {
        cerrar();
        btn.focus();
      }
    });
  }

  function initAvisos() {
    $$("[data-toast]").forEach((el) => el.addEventListener("click", () => toast(el.dataset.toast, "azul")));

    $("#btnCopiarEnlace").addEventListener("click", () => {
      copiarTexto(window.location.href)
        .then(() => toast("Enlace de la vista copiado al portapapeles.", "verde"))
        .catch(() => toast("No se pudo copiar el enlace.", "naranja"));
    });
  }

  function initInteraccion() {
    let t;
    $("#qHist").addEventListener("input", (ev) => {
      window.clearTimeout(t);
      const v = ev.target.value;
      t = window.setTimeout(() => {
        state.query = v;
        state.page = 1;
        apply();
      }, 250);
    });

    $("#selMts").addEventListener("change", (ev) => {
      state.prioridad = ev.target.value;
      state.page = 1;
      apply();
    });

    $("#selEstado").addEventListener("change", (ev) => {
      state.estado = ev.target.value;
      state.page = 1;
      apply();
    });

    $("#selPageSize").addEventListener("change", (ev) => {
      state.pageSize = parseInt(ev.target.value, 10);
      state.page = 1;
      apply();
    });

    $("#theadHist").addEventListener("click", (ev) => {
      const th = ev.target.closest("th[data-sort]");
      if (th) alternarOrden(th.dataset.sort);
    });

    $("#tbodyHist").addEventListener("click", (ev) => {
      const detail = ev.target.closest("[data-document]");
      if (detail) {
        const row = records.find((record) => record.id === detail.dataset.document);
        $("#documentDetailJson").textContent = JSON.stringify(row.documento, null, 2);
        $("#documentDetail").showModal();
        return;
      }
      const btn = ev.target.closest("[data-ruta]");
      if (btn) copiarRuta(btn);
    });

    $("#paginas").addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-pagina]");
      if (btn) irAPagina(parseInt(btn.dataset.pagina, 10));
    });

    $("#btnPrev").addEventListener("click", () => irAPagina(state.page - 1));
    $("#btnNext").addEventListener("click", () => irAPagina(state.page + 1));
    $("#btnLimpiar").addEventListener("click", () => limpiarFiltros(false));
    $("#btnLimpiarVacio").addEventListener("click", () => limpiarFiltros(true));

    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === "f" || ev.key === "k")) {
        ev.preventDefault();
        $("#qHist").focus();
        $("#qHist").select();
      }
    });

    window.addEventListener("popstate", () => {
      leerURL();
      $("#qHist").value = state.query;
      $("#selMts").value = state.prioridad;
      $("#selEstado").value = state.estado;
      $("#selPageSize").value = String(state.pageSize);
      apply({ silenciosoURL: true });
    });
  }

  /* --------------------------------------------------------------------
     ARRANQUE
     -------------------------------------------------------------------- */
  function init() {
    sincronizarNav();
    leerURL();
    $("#qHist").value = state.query;
    $("#selMts").value = state.prioridad;
    $("#selEstado").value = state.estado;
    $("#selPageSize").value = String(state.pageSize);
    apply({ silenciosoURL: true });

    initMenu();
    initAvisos();
    initInteraccion();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
