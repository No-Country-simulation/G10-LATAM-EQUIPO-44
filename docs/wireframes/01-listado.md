# 01 — Estructura del listado e información por documento

> **Punto 1 de la lista:** *«Definir la estructura del listado de documentos»* → §1 y §2.
> **Punto 2 de la lista:** *«Definir qué información básica debe verse por documento»* → §2.1 y §3.
> Wireframe visual: [`html/listado.html`](html/listado.html)
> Pantalla real: [`historial/`](../../historial/index.html)

---

## 1. Decisión de estructura

**El listado de documentos es una tabla densa de 7 columnas, no un grid de tarjetas.**

Motivos, todos derivados del volumen que maneja el proyecto:

| Criterio | Lectura |
|---|---|
| El listado es de **consulta y triaje**, no de lectura | Un profesional necesita localizar un documento concreto entre decenas, comparar estados en un vistazo y verificar una ubicación. Una tabla da densidad de información por pantalla alta; un grid de tarjetas obliga a paginar antes de comparar. |
| Los campos son de **longitud heterogénea y baja** | ID, nivel, estado y fecha son tokens cortos. El tipo de documento es una etiqueta. El paciente es un nombre. En una tabla cada columna se dimensiona a su contenido; en un grid las tarjetas quedan con huecos o se recortan. |
| La información es **comparable entre filas** | Ver 40 estados de una vez es la tarea principal. La alineación vertical de columnas lo hace posible; el grid no. |
| El listado debe **ordenar por columna** | Todas las columnas son ordenables. Un grid no ofrece orden natural sin un control adicional. |
| El uso real es **auditoría de flujo** | La ruta de almacenamiento, que es un dato técnico, ocupa una columna propia porque la comprobación de integridad documental es una tarea recurrente en el triaje. |

La tabla también hace que la fila completa sea clicable sin ambigüedad, que es lo que resuelve el punto 6.

---

## 2. Las 7 columnas

Orden fijo, verificado en `historial/app.js:73-81` (`COLUMNAS`) y `historial/index.html:250-258`.

| # | Columna | Campo | Tipo de dato | Contenido de la celda | Orden |
|---|---|---|---|---|---|
| 1 | **ID de documento** | `id` | texto | `.doc-id` con el identificador, y sufijo de año descompuesto en `.doc-id__year` | `id` |
| 2 | **Paciente** | `paciente` `dni` `ingreso` | compuesto | Avatar de iniciales + nombre, y debajo DNI e ingreso | `paciente` |
| 3 | **Tipo de documento** | `tipo` | enum | Icono según tipo + etiqueta | `tipo` |
| 4 | **Nivel MTS** | `mts` | enum | `.mts-tag--{nivel}` con punto de color, nombre y tiempo objetivo en el `title` | `mts` |
| 5 | **Estado** | `estado` | enum | `.estado-chip--{estado}` con punto | `estado` |
| 6 | **Fecha** | `fecha` | fecha | `dd/mm/aaaa` y hora `HH:MM` en línea secundaria | `fecha` |
| 7 | **Ruta de almacenamiento** | `ruta` | texto | Ruta en monoespaciada, recortada, con botón de copiar | `ruta` |

### 2.1 Justificación de cada columna

| Columna | Por qué está |
|---|---|
| ID de documento | Es la clave primaria del sistema. Va en primera posición porque es lo que se cita en conversación clínica («el DOC-0042») y lo que se pega en otros sistemas. Es también el parámetro de la URL del detalle (punto 6). |
| Paciente | Con DNI e ingreso en la misma celda. El nombre identifica, el ingreso sitúa en el episodio en curso y el DNI desambigua entre homónimos. Agruparlos evita repetir el avatar tres veces. |
| Tipo de documento | Permite escanear de un vistazo qué mezcla de estudios hay en el lote, que es la pregunta habitual en triaje. El icono acelera el escaneo: imagen, laboratorio, hoja de fármacos. |
| Nivel MTS | Es el eje de urgencia del protocolo. Color y punto permiten priorizar por barrido visual sin leer. El tiempo objetivo va en el `title` para no gastar ancho. |
| Estado | Cuánto le falta al documento. Es la columna que responde «¿qué tengo pendiente?». Ver [`02-estados.md`](02-estados.md). |
| Fecha | Orden de llegada. La fecha y la hora en dos líneas hacen ordenables ambas sin duplicar columna. |
| Ruta de almacenamiento | Verificación de integridad: confirmar que el documento está realmente donde dice estar. Es el único dato de la tabla que no es clínico, y por eso va al final, fuera del recorrido de lectura clínica. |

### 2.2 Campos disponibles que no son columna

El array `records` (`historial/app.js:89-94`) tiene 9 campos. Siete son columnas. Los dos restantes van dentro de otra celda:

| Campo | Dónde se muestra |
|---|---|
| `dni` | Línea secundaria de la celda de Paciente |
| `ingreso` | Línea secundaria de la celda de Paciente |

Un tercer campo, `recibidoAzul`, no es contenido sino modificador visual del chip de estado (ver [`02-estados.md` §4.2](02-estados.md)).

**No hay columna de acciones.** Es deliberado: la acción depende del estado, y un documento `Procesado` no tiene nada que aprobar. Meter una columna de acciones obligaría a pintar celdas vacías en la mayoría de las filas. La acción vive en el detalle, y la fila completa lleva al detalle.

---

## 3. Contrato de datos

Fuente de sustitución única: el array `records` de `historial/app.js:89`. El comentario del propio código lo declara: *«Este array es el único punto de sustituir: reemplazar por la respuesta del endpoint de documentos al conectar el backend»*.

```js
{
  id:      "DOC-0001",        // clave primaria, string
  paciente:"…",               // string
  dni:     "…",               // string
  ingreso: "…",               // string
  tipo:    "Informe de urgencias",  // clave de TIPOS
  mts:     "rojo",            // clave de MTS: rojo|naranja|amarillo|verde|azul
  estado:  "recibido",        // clave de ESTADOS: recibido|procesado|auditoria
  fecha:   "2026-01-01T09:00",// ISO sin zona
  ruta:    "his://…",         // string
  recibidoAzul: true          // opcional, solo aplica a estado "recibido"
}
```

**Invariante que este contrato impone:** `estado` y `mts` son ejes independientes. Un documento puede estar `recibido` y `rojo` a la vez (`DOC-0001`) o `recibido` y `verde` (`DOC-0004`). El estado responde a la pregunta de proceso, el nivel MTS a la de gravedad. La interfaz no debe derivar uno del otro.

---

## 4. Catálogos de referencia

### 4.1 Tipos de documento

10 valores en `historial/app.js:60-71`, mapeados a 5 iconos: notas (`i-notes`), enfermería (`i-clipboard`), laboratorio (`i-flask`), imagen (`i-image`), señal (`i-activity`), fármacos (`i-pill`), consentimiento (`i-file-check`).

### 4.2 Niveles MTS

5 valores en `historial/app.js:46-52`, con su tiempo objetivo:

| Nivel | Tiempo objetivo | Orden |
|---|---|---|
| Rojo | 0 min — Inmediato | 0 |
| Naranja | 10 min — Muy Urgente | 1 |
| Amarillo | 60 min — Urgente | 2 |
| Verde | 120 min | 3 |
| Azul | 240 min | 4 |

> **Inconsistencia a resolver:** el panel de auditoría solo define **3** de estos 5 niveles (`auditoria/app.js:41-45`). El selector de nivel del modal de edición de auditoría no puede asignar verde ni azul. Detallado en [`06-auto-revision.md` §H9](06-auto-revision.md).

---

## 5. Interacción del listado

Capacidades ya implementadas, que el wireframe fija como contrato:

| Capacidad | Comportamiento | Referencia |
|---|---|---|
| Ordenar | Por cualquiera de las 7 columnas, ascendente y descendente, con `aria-sort` | `historial/app.js` |
| Buscar | Coincidencia insensible a mayúsculas y acentos, con debounce de 250 ms | `norm()` `app.js:34-39` |
| Filtrar | Por nivel MTS y por estado, combinables | `#selMts`, `#selEstado` |
| Paginar | 10, 25 o 50 filas por página | `#selPorPagina` |
| Copiar ruta | Por celda, con confirmación | `.btn-copiar` |
| Compartir estado | Los filtros se reflejan en la URL mediante `replaceState` | `app.js:319` |
| Estado vacío | Mensaje específico cuando no hay coincidencias | — |

**Lo que el listado NO tiene y este wireframe no inventa:** edición en línea, acciones masivas por selección, arrastre de filas, columnas configurables, exportación, vista de detalle integrada. Ninguna de ellas es necesaria para el alcance y todas ampliarían el alcance de Sprint 2. La selección masiva es la única que se justifica a medio plazo y queda como P3 en [`07-sprint2.md`](07-sprint2.md).

---

## 6. Criterios de aceptación

1. Las 7 columnas están presentes, en ese orden, en todos los anchos de escritorio.
2. Los 5 niveles MTS y los 3 estados son representables sin colisión de colores.
3. Ordenar por cualquier columna produce un orden estable y reversible.
4. La búsqueda ignora mayúsculas, acentos y la puntuación de los IDs.
5. Los filtros son combinables y se reflejan en la URL, de modo que el listado sea reproducible por enlace.
6. La fila completa es un objetivo de clic con foco por teclado, y su destino es el detalle del documento.
7. Con 0 resultados se muestra un estado vacío accionable, no una tabla vacía.
8. Ninguna columna depende de leer un color para la información esencial: el nivel MTS y el estado tienen además texto e icono.

---

Ver también: [`02-estados.md`](02-estados.md) · [`05-navegacion.md`](05-navegacion.md) · [`06-auto-revision.md`](06-auto-revision.md)
