# 05 — Navegación entre listado, detalle y auditoría

> Punto 6 de la lista: *«Definir la navegación entre listado y detalle/auditoría»*.
> Wireframe visual: [`html/detalle.html`](html/detalle.html)

---

## 1. El hueco que este documento cubre

**No existe ninguna vista de detalle en el proyecto.** No es una vista pendiente de refinar: no existe ninguna. Verificado:

| Búsqueda | Resultado |
|---|---|
| Carpetas `detalle/`, `detail/`, `doc/` | 0 |
| `index.html` adicionales | 0, solo los 5 de pantalla |
| `location.href` / `assign` / `replace` / `window.open` / `target="_blank"` | 0 en las 5 pantallas |
| `history.pushState` | 0 (solo un `replaceState` de filtros) |
| Funciones tipo `abrirDetalle` / `verDetalle` / `verDocumento` | 0 |

**Comportamiento real hoy:**

- En el listado, el `<tr>` **no tiene handler**. El único listener delegado (`historial/app.js:477-480`) atiende `[data-ruta]` para copiar la ruta. Clic en cualquier otro punto de la fila no hace nada.
- En el panel de auditoría, la tarjeta **no abre nada al pulsarla**. El único listener (`auditoria/app.js:868-875`) atiende los tres `data-accion`.
- En el resultado, el botón de estudio solo dispara un toast: *«Abriendo informe de …»* (`resultado/app.js:355, 370-376`), sin abrir nada.

Consecuencia: los identificadores `data-doc="AUD-000N"` y `data-id` de las tarjetas de cola son **identificadores inertes**. Sirven para encontrar el nodo DOM al animarlo, y nada más. Ninguna pantalla puede mostrar un documento concreto en una URL.

**Este documento define esa navegación, que es literalmente lo que pide el punto 6.**

---

## 2. Decisión: pantalla direccionable con `?doc=ID`

El detalle es una **pantalla nueva** en `detalle/index.html`, direccionable por `?doc=DOC-0001`.

### 2.1 Por qué pantalla y no drawer

Un drawer lateral se descartó porque **no tiene URL propia**, y perder la URL es perder tres cosas a la vez: la posibilidad de compartir un documento por correo o mensajería, la de abrirlo en otra pestaña para compararlo con la cola, y la de que el soporte pueda pedir a un profesional «envíame el enlace del caso».

### 2.2 Por qué `?doc=` y no una ruta

`detalle/DOC-0001.html` obliga a un archivo por documento. El proyecto no tiene router ni build, así que eso exigiría una infraestructura que no existe. Un parámetro de consulta sobre una sola página mantiene el patrón que ya usa `historial` para sus filtros (`replaceState` con `URLSearchParams`, `historial/app.js:319`), de modo que la navegación a detalle reutiliza un mecanismo **ya presente y probado** en el proyecto.

### 2.3 Por qué no entra en el sidebar

El detalle no es una sección: es un drill-down sobre un elemento concreto. Meterlo en la navegación principal le daría la misma jerarquía que a «Ingesta» o «Colas», que es semánticamente falso. Se llega desde el listado y desde la tarjeta de auditoría, y se vuelve con las migas de pan o con el botón atrás del navegador.

---

## 3. Grafo de navegación

```
                    ┌───────────┐
                    │  INGESTA  │
                    └─────┬─────┘
                          │ alta confirmada
                          ▼
   ┌──────────────────────────────────────────┐
   │            COLAS  (Kanban)                │
   │  nivel MTS, ubicación, tiempo objetivo     │
   └───────┬────────────────────────┬──────────┘
           │ N3 Ir a la cola         │ inferencia
           │                         ▼
           │              ┌──────────────────────┐
           │              │      RESULTADO       │
           │              │  A / B / confianza    │
           │              └──────┬───────────────┘
           │                     │ D1, D2 o D3
           │                     ▼
           │              ┌──────────────────────┐
           │              │  AUDITORÍA (panel)   │◀──┐
           │              │  4 zonas por tarjeta  │   │
           │              └──────┬───────────────┘   │
           │                     │ N1 Ver detalle     │
           │                     ▼                   │
           │  ┌──────────────────────────────────┐  │
           │  │  HISTORIAL (listado, 7 columnas) │──┼──┐
           │  └──────────────┬───────────────────┘  │  │
           │                 │ clic en fila         │  │
           │                 ▼                      │  │
           └────────────▶┌──────────────────────┐  │  │
                          │  DETALLE  ?doc=ID    │◀─┘  │
                          │  estado + inferencia  │     │
                          │  + historial + firma  │     │
                          └──────┬───────────────┘     │
                                 │ N2 Ver en el listado │
                                 └─────────────────────▶┘
```

**Cinco transiciones de detalle a contexto, dos de ida:**

| # | Desde | Hacia | Disparador | Visible en |
|---|---|---|---|---|
| N1 | Auditoría | Detalle | «Ver detalle completo» en la zona de confianza | El panel no tiene otro camino al detalle |
| N2 | Detalle | Historial | «Ver en el listado», con el filtro fijado al documento | Filtros ya reflected en la URL |
| N3 | Detalle | Colas | «Ir a la cola», visible solo si hay nivel MTS asignado | Un documento `Recibido` sin nivel no tiene fila en la cola |
| N4 | Detalle | — | migas de pan / botón atrás | Siempre |
| N5 | Detalle | — | estado vacío si falta o no existe `?doc` | Siempre |

La navegación principal entre secciones **no cambia**: sigue siendo el sidebar de 5 entradas.

---

## 4. Especificación de la vista de detalle

### 4.1 Parámetros de URL

| Parámetro | Obligatorio | Comportamiento |
|---|---|---|
| `?doc=` | Sí | Identificador del documento. Sin valor, con valor vacío o con un ID inexistente → estado vacío, nunca error |
| `?estado=` | No | Filtro de estado a la vista, desde el enlace N2 |
| `?q=` | No | Búsqueda a la vista, desde el enlace N2 |

Al cargar, el detalle **reemplaza** los parámetros de navegación para no acumular historial: abrir un documento desde otro no debe crear una entrada de pila por cada documento revisado.

### 4.2 Estructura

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Historial  /  DOC-0001                       [Copiar enlace]  │  migas + acción
├─────────────────────────────────────────────────────────────────┤
│  Nombre del paciente                              MTS: Rojo     │  identidad
│  DNI · Ingreso                          Objetivo: inmediato    │
│                                                                 │
│  ┌── Estado ──────────────────────────────────────────────────┐ │
│  │  ● Auditoría     Motivo: gravedad crítica                  │ │  estado + motivos
│  │  Motivo: confianza bajo umbral                             │ │
│  │  [ Ver en el listado ]  [ Ir a la cola ]                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Signos vitales ──────────┐  ┌─ Inferencia del modelo ────┐ │
│  │ PA   90/60  ⚠  100-180    │  │ Diagnóstico A · alerta      │ │
│  │ FC   120     ⚠  60-100    │  │ Diagnóstico B · alt.        │ │
│  │ …                          │  │ Discriminador: …            │ │
│  └────────────────────────────┘  └────────────────────────────┘ │
│                                                                 │
│  ┌─ Confianza del algoritmo ──────────────────────────────────┐ │
│  │  Confianza media   En zona de revisión                      │ │
│  │  [      ▓▓▓▓▓▓|▓▓▓▓      ]   Baja / Media / Alta            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Historial de estados ─────────────────────────────────────┐ │
│  │  01 feb 09:00  Recibido                                    │ │
│  │  01 feb 09:02  Auditoría  · motivo: confianza baja         │ │
│  │  01 feb 09:41  Aprobado  Dr. M. Vance, MD  MED-99120-VANCE  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Registro de auditoría ────────────────────────────────────┐ │
│  │  01 feb 09:41  Aprobado   Dr. M. Vance, MD                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Contenido por sección

| Sección | Fuente | Nota |
|---|---|---|
| Identidad | `id`, `paciente`, `dni`, `ingreso` | |
| Estado | `estado` + motivos D1/D2/D3 | Ver [`02-estados.md`](02-estados.md) |
| Signos vitales | `vitals` | Reutiliza la zona B de la tarjeta |
| Inferencia | `diagA`, `diagB`, `discriminador`, `advertencia` | Reutiliza la zona C |
| Confianza | banda, estado, barra, marcador | **Nunca el número** |
| Historial de estados | nuevos `eventos[]` | Especificación pendiente, ver §5 |
| Registro de auditoría | `registro[]` filtrado por documento | Resuelve H7 |
| Tipo y ruta | `tipo`, `ruta` + copiar | Reutiliza columnas 3 y 7 del listado |
| Fecha de alta | `fecha` | Reutiliza columna 6 |

**Las secciones 1 a 5 reutilizan componentes existentes.** El detalle no inventa nada visual: es la tarjeta de auditoría descompuesta en secciones apiladas, más lo que la tarjeta no tenía sitio para mostrar.

### 4.4 Reutilización de las zonas de la tarjeta

Esta es la decisión que hace el detalle barato de construir: la tarjeta del panel de auditoría **es** el detalle comprimido. Las zonas B, C y D se extraen a funciones compartidas (`zonaVitales`, `zonaIA`, `zonaConfianza` ya existen como funciones independientes en `auditoria/app.js:369-438`) y ambas pantallas las consumen. El detalle no duplica markup ni lógica de presentación; solo cambia el contenedor de rejilla por uno de columna.

Consecuencia: cualquier corrección de las zonas benefita a las dos pantallas a la vez, y no puede haber divergencia entre lo que ve el revisor y lo que ve el médico que abre el detalle.

### 4.5 Acciones en el detalle

| Acción | Visible cuando | Destino |
|---|---|---|
| Ver en el listado | siempre | `historial/index.html?doc=…` |
| Ir a la cola | hay nivel MTS asignado | `colas/index.html` |
| Copiar enlace | siempre | portapapeles, con toast |
| Aprobar / Rechazar / Editar | `estado === "auditoria"` | reutiliza los diálogos existentes |

La última fila conecta los puntos 5 y 6: **el detalle ofrece las mismas acciones que el panel, sobre los mismos diálogos**, de modo que un revisor puede trabajar desde cualquiera de los dos sitios sin aprender dos interfaces. Es la razón por la que el detalle no se limita a mostrar: sería un callejón sin salida profesional.

---

## 5. Estados límite

Una vista direccionable por URL recibe entradas que no controla. Los cuatro casos se especifican:

| Entrada | Comportamiento | Razón |
|---|---|---|
| `?doc` ausente | Estado vacío con enlace a Historial | Una URL naked es un error de navegación, no un documento |
| `?doc=` vacío | Igual que ausente | `URLSearchParams` no distingue ambos casos, y no debe |
| `?doc=DESCONOCIDO` | Estado vacío con enlace a Historial | El ID puede venir de un enlace antiguo o de un documento ya borrado |
| `?doc=` con caracteres especiales | Se escapa y se busca literal | Se registra en consola en desarrollo; nunca se inyecta en el HTML |

> **Nota de seguridad.** El identificador nunca se concatena en una consulta ni en un comando. El proyecto no tiene backend, así que hoy no hay vector de inyección, pero el contrato de datos de [`01-listado.md` §3](01-listado.md) debe fijar que `id` se trata como dato opaco y se compara, no se interpreta.

---

## 6. Accesibilidad de la navegación

| Requisito | Aplicación |
|---|---|
| La fila del listado es un objetivo de clic | El `<tr>` recibe `tabindex="0"` y `role="link"`, o la fila contiene un enlace real en la celda del ID. La opción preferida es un `<a>` en la celda del ID, por semántica nativa |
| Foco visible | El `--focus-ring` de `assets/css/styles.css:57` se aplica a filas y a migas |
| Doble confirmación del contexto | Al llegar al detalle, el breadcrumb y el H1 repiten el ID, para que un usuario que abre un enlace directo sepa dónde está |
| Enlace compartible | Visible y siempre disponible: es la razón de que el detalle tenga URL |
| Volver | Migas de pan, botón atrás del navegador y `Escape` cuando no hay entrada de historial que.pop() |
| Sin dependen de JavaScript | Con JS desactivado, el enlace del listado sigue llevando a una página que muestra el estado de carga en lugar de fallar en blanco |

---

## 7. Criterios de aceptación

1. `detalle/index.html?doc=DOC-0001` muestra ese documento; cualquier otro valor no rompe la pantalla.
2. El detalle es alcanzable desde el listado haciendo clic en la fila, y con el teclado usando `Tab` y `Enter`.
3. El detalle es alcanzable desde la tarjeta de auditoría mediante una acción explícita y etiquetada.
4. El detalle tiene migas de pan que enlazan a la pantalla de origen.
5. El detalle tiene una acción de copiar enlace cuyo resultado se confirma con toast.
6. Ningún identificador de documento aparece en la URL de ninguna pantalla sin ser enlazable.
7. Las zonas de vitales, inferencia y confianza renderizan el mismo contenido en el detalle y en la tarjeta de auditoría.
8. El detalle no expone ningún score numérico.
9. El detalle ofrece Aprobar, Rechazar y Editar cuando el documento está en auditoría, y no las ofrece cuando no lo está.
10. Abrir un documento no ensucia el historial del navegador con una entrada por documento.

---

Ver también: [`01-listado.md`](01-listado.md) · [`03-panel-auditoria.md`](03-panel-auditoria.md) · [`04-acciones.md`](04-acciones.md) · [`06-auto-revision.md`](06-auto-revision.md) · [`07-sprint2.md`](07-sprint2.md)
