# 02 — Estados del documento

> Punto 3 de la lista: *«Proponer visualmente estados como Recibido, Procesado y Auditoría usando criterios propios del alcance del proyecto»*.
> Wireframe visual: [`html/estados.html`](html/estados.html)

---

## 1. El problema que este documento resuelve

En el código actual conviven **dos vocabularios de estado que no se hablan**:

| Pantalla | Valores | Cantidad | Fuente |
|---|---|---|---|
| Historial | `recibido` · `procesado` · `auditoria` | 3 | `historial/app.js:54-58` |
| Auditoría | `critico` · `discrepancia` · `revision` | 3 | `auditoria/app.js:47-52` |
| Resultado | `critico` · `alerta` · `normal` · `pendiente` | 4 | `resultado/app.js:219-224` |

Son ejes **paralelos e incomparables**: el chip del listado y la pestaña del panel de auditoría no se pueden leer el uno contra el otro, y sus identificadores tampoco se corresponden (`DOC-0001` frente a `AUD-0001`).

**Este documento fija un único ciclo de vida de tres estados y degrada el segundo vocabulario a «motivos de entrada».** Es la decisión de diseño que sostiene los puntos 3 y 6.

---

## 2. Criterio de estado

El criterio se apoya en el hecho verificable del flujo del proyecto: un documento tiene o no **inferencia calculada**, y esa inferencia tiene o no **confianza suficiente** y **gravedad baja**. De ahí salen exactamente tres estados.

| Estado | Criterio de pertenencia | Qué ve el usuario | MTS aplicable |
|---|---|---|---|
| **Recibido** | El documento está admitido en el repositorio **y todavía no hay inferencia calculada**. Sin nivel MTS asignado, o con el nivel heredado del HIS sin confirmar. | Nada que decidir. Es un pendiente de proceso, no de criterio clínico. | Ninguno asignado |
| **Procesado** | Hay inferencia, la confianza es **≥ UMBRAL (0.60)** y el nivel MTS **no es rojo**. El algoritmo resolvió el caso sin intervención. | Está resuelto. Puede avanzar solo. | Verde, amarillo, azul |
| **Auditoría** | Requiere decisión humana. Se entra si se cumple **cualquiera** de los tres disparadores. | Requiere firma de un profesional. | Rojo, naranja, amarillo |

### 2.1 Disparadores de entrada en Auditoría

Ordenados por severidad, estos son los tres y solo estos tres motivos por los que un documento sale del circuito automático:

| # | Disparador | Condición | Umbral / origen |
|---|---|---|---|
| D1 | **Gravedad crítica** | `nivelMTS === "rojo"` | `auditoria/app.js:41-45` |
| D2 | **Confianza insuficiente** | `score < 0.60` | `UMBRAL`, `auditoria/app.js:38` |
| D3 | **Discrepancia diagnóstica** | El discriminador no separa con robustez el diagnóstico A (alerta) del B (alternativo) | `diagA` / `diagB` / `discriminador` |

> **D2 y el umbral de aprobación rápida son umbrales distintos y no deben fusionarse.** `UMBRAL = 0.60` decide si un documento entra a auditoría. `UMBRAL_RAPIDA = 0.55` decide si un médico puede aprobarlo en lote (`auditoria/app.js:39`, regla de elegibilidad en `799-801`). Son coherentes porque 0.55 < 0.60: todo lo aprobable en lote está por encima del umbral de auditoría, y el rango 0.55–0.60 queda como zona que **no** admite lote pero **tampoco** está claramente en auditoría. Esa franja es una decisión abierta, registrada en [`07-sprint2.md`](07-sprint2.md).

### 2.2 Los motivos de auditoría dejan de ser estados

`critico`, `discrepancia` y `revision` pasan a ser **etiquetas de motivo**, no estados del documento:

| Valor actual en `auditoria` | Reinterpretación | Se muestra como |
|---|---|---|
| `critico` | Documento en `Auditoría` por **D1**, gravedad crítica | Motivo: «Gravedad crítica» |
| `discrepancia` | Documento en `Auditoría` por **D3** | Motivo: «Discrepancia diagnóstica» |
| `revision` | Documento en `Auditoría` por **D2**, confianza insuficiente | Motivo: «Confianza bajo umbral» |

Consecuencia: un documento puede estar en `Auditoría` por dos motivos a la vez, y las pestañas del panel pasan a ser **filtros sobre una misma verdad** en lugar de categorizaciones que se pisan entre sí. Las cuatro pestañas (`todos` + los tres motivos) siguen funcionando sin cambio de comportamiento.

---

## 3. Máquina de estados

```
                      ┌──────────────────────────────────────┐
                      │                                      │
   alta de documento  ▼                                      │
        ┌──────────┐   inferencia calculada                │
        │          │   score ≥ 0.60 y nivel ≠ rojo          │
        │ RECIBIDO │──────────────────────────▶ PROCESADO  │
        │   gris   │                              verde     │
        └──────────┘         ┌──────────────────────┐      │
             │               │                      │      │
             │               │ score < 0.60         │      │
             │               │ ó nivel = rojo       │      │
             │               │ ó discrepancia       │      │
             │               ▼                      │      │
             │        ┌──────────┐                 │      │
             │        │          │ escalamiento    │      │
             └────────│ AUDITORÍA│◀────────────────┘      │
            rechazo  │ naranja  │                        │
            (motivo   └──────────┘                        │
            firmado)      │                                │
                          │ aprobación firmada             │
                          └───────────────────────────────▶┘
                                      ▲                     │
                                      │                     │
                            PROCESADO┘ (aprobado)
```

### 3.1 Tabla de transiciones

| # | Desde | Hacia | Disparador | Acción de interfaz | Firma |
|---|---|---|---|---|---|
| T1 | — | Recibido | alta de documento | `ingesta` → confirmación de alta | No |
| T2 | Recibido | Procesado | inferencia limpia | automática | No |
| T3 | Recibido | Auditoría | D1, D2 o D3 | automática | No |
| T4 | Procesado | Auditoría | escalamiento o reevaluación | `Reanalizar Lote` | No |
| T5 | Auditoría | Procesado | aprobación | `Firmar y aprobar` | **Sí** |
| T6 | Auditoría | Recibido | rechazo con motivo | `Firmar y rechazar` | **Sí** |
| T7 | Auditoría | Procesado | aprobación en lote asistida | `Aprobar N documento(s)` | **Sí** |

T6 no es un invento: el modal de rechazo del proyecto ya se titula literalmente *«Rechazar inferencia y devolver a triage»* (`auditoria/index.html:293`). El wireframe le da por fin un estado de destino a esa frase.

### 3.2 Qué se muta hoy y qué no

> **Hallazgo de consistencia:** en el código actual **ninguna acción cambia el estado de un documento**. Las cinco acciones de auditoría solo hacen `d.resuelto = true` (`auditoria/app.js:619, 651, 757`), un campo que únicamente saca el documento de `pendientes()`. El campo `estado` del listado es de solo lectura en las cinco pantallas.

La tabla anterior es por tanto una **especificación pendiente de implementar**, no una descripción del comportamiento vigente. Queda registrado como P1 en [`07-sprint2.md`](07-sprint2.md).

---

## 4. Criterio visual

Los tres estados se distinguen por color, fondo, borde, tinta y un punto. Los valores salen literalmente de `historial/styles.css:210-227` y de los tokens de `assets/css/styles.css`.

| Estado | Borde | Fondo | Tinta | Punto | Lectura |
|---|---|---|---|---|---|
| **Recibido** | `#CBD5E1` | `#F1F5F9` | `#475569` | `currentColor` | Neutro, sin acento cromático |
| **Procesado** | `var(--mts-verde-border)` `#B2E0C0` | `var(--mts-verde-bg)` `#ECF8EF` | `var(--mts-verde-ink)` `#1D7438` | idem | Resuelto |
| **Auditoría** | `var(--mts-naranja-border)` `#F8CB98` | `var(--mts-naranja-bg)` `#FFF4E8` | `var(--mts-naranja-ink)` `#A94F00` | idem | Pendiente de humano |

Relleno común: `padding: 3px 9px`, `border-radius: var(--radius-pill)`, `font-size: 11.5px`, `font-weight: 600`, punto de 6×6 px con `opacity: .7`.

### 4.1 Por qué estos tres colores

La elección no es decorativa, está justificada por el sistema de color del proyecto:

- **Verde = `--mts-verde`**, la misma familia que el nivel MTS verde. Refuerza «resuelto sin intervención».
- **Naranja = `--mts-naranja`**, la familia del nivel MTS naranja (Muy Urgente). Refuerza «requiere atención humana» sin llegar a rojo, reserving el rojo exclusivamente para el nivel MTS rojo (D1). Así el color nunca significa dos cosas: el rojo siempre es gravedad, el naranja siempre es proceso.
- **Gris neutro para Recibido**, porque el estado carece de valor MTS y por tanto no debe tomar un tono MTS. Se evita el error de teñir un estado sin severidad con un color de severidad.

### 4.2 La variante azul de «Recibido»

Existe `.estado-chip--recibido.estado-chip--alt` con los tokens azules (`--mts-azul-border` / `-bg` / `-ink`, `historial/styles.css:225`), activado por el campo `recibidoAzul` que hoy solo tiene `DOC-0004`.

**Supuesto a confirmar:** azul = alta validada automáticamente desde el HIS, frente a gris = alta manual pendiente de verificación. La existencia del campo indica que la distinción es intencionada, pero el código no la documenta en ningún sitio. Registrado como decisión abierta en [`07-sprint2.md`](07-sprint2.md).

### 4.3 Deuda de tokens

El color de estado está cableado en tres reglas de `historial/styles.css` y **no existe en la hoja común**: `.estado-chip` no está en `assets/css/styles.css`. El sistema compartido solo ofrece `.badge--{rojo|naranja|amarillo|verde|azul|gris|navy}` (`assets/css/styles.css:520-526`).

Consecuencia práctica: la vista de detalle nueva y cualquier pantalla futura deben **reimportar `.estado-chip` por su cuenta**. La recomendación es promoverlo a `styles.css` común en Sprint 2 con tokens semánticos `--estado-*-bg/border/ink`; queda como P2 en [`07-sprint2.md`](07-sprint2.md).

---

## 5. Contenido por estado

Qué se considera que el usuario puede hacer con un documento en cada estado:

| Estado | Acciones disponibles | Acciones bloqueadas |
|---|---|---|
| **Recibido** | Ver detalle, consultar ruta, reanalizar si hay inferencia pendiente | Aprobar, rechazar |
| **Procesado** | Ver detalle, copiar ruta, consultar inferencia, solicitar escalamiento a auditoría | Aprobar, rechazar (ya está resuelto) |
| **Auditoría** | Ver detalle, editar datos, **aprobar**, **rechazar con motivo**, aprobar en lote si cumple elegibilidad | — |

---

## 6. Iconografía

| Estado | Icono propuesto | Nota |
|---|---|---|
| Recibido | `i-inbox` | ya existe en el sprite, se usa en la ubicación del panel de auditoría |
| Procesado | `i-check` | ya existe, hoy usado en botones de aprobación |
| Auditoría | `i-shield-search` | ya existe, hoy usado en el estado de la inferencia |

Los tres existen ya en el sprite SVG, por lo que la propuesta no requiere dibujo nuevo. El chip actual **no lleva icono**, solo punto: mantenerlo sin icono conserva la densidad de la tabla y reservar el icono para el detalle, donde sí hay espacio.

---

## 7. Criterios de aceptación

Para dar por bueno este diseño:

1. Un documento nunca está en `Auditoría` sin al menos uno de los tres disparadores D1, D2, D3 asociados y visible.
2. Ningún documento puede saltar de `Recibido` a `Procesado` sin una inferencia calculada.
3. Toda transición hacia `Procesado` o `Recibido` desde `Auditoría` exige firma registrada.
4. Los tres estados son distinguibles sin leer el texto, por color y por punto.
5. Los tres estados se distinguen en modo de alto contraste y en escala de grises (el punto y la forma del chip deben bastar).
6. Ningún estado toma un color de la familia MTS que no le corresponde.

---

Ver también: [`01-listado.md`](01-listado.md) · [`03-panel-auditoria.md`](03-panel-auditoria.md) · [`06-auto-revision.md`](06-auto-revision.md) · [`07-sprint2.md`](07-sprint2.md)
