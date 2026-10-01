# 04 — Acciones de revisión

> Punto 5 de la lista: *«Definir las acciones principales de revisión que aparezcan en la interfaz»*.
> Diálogos: [`html/panel-auditoria.html`](html/panel-auditoria.html)

---

## 1. Las cinco acciones de revisión

El panel expone **cinco** acciones. No son cinco botones intercambiables: cubren cuatro intenciones distintas y tienen umbrales de riesgo distintos.

| # | Acción | Dónde vive | Intención | Riesgo | Firma |
|---|---|---|---|---|---|
| A1 | **Editar datos** | Zona de confianza, tarjeta | Corregir lo que el modelo leyó mal | Bajo | No |
| A2 | **Rechazar** | Zona de confianza, tarjeta | Descartar la inferencia y devolver el caso a triaje | Medio | **Sí** |
| A3 | **Aprobar** | Zona de confianza, tarjeta | Ratificar la inferencia y sacarla de la cola | Medio | **Sí** |
| A4 | **Reanalizar Lote** | Barra de herramientas | Reejecutar el modelo sin tocar nada a mano | Bajo | No |
| A5 | **Aprobación Rápida Asistida** | Barra de herramientas | Aprobar en bloque lo que el modelo ya resolvió con confianza | Alto | **Sí** |

A esto se suma una acción de consulta, hoy sin destino real: **«Ver Registro de Auditoría Completo»** en el banner.

---

## 2. Acciones por tarjeta

Las tres comparten estructura: viven en la zona de confianza, a la derecha, y se lanzan con `data-accion` + `data-id` mediante delegación desde `#listaDocs` (`auditoria/app.js:868-875`).

| Atributo | Etiqueta | Icono | Clases | Abre |
|---|---|---|---|---|
| `data-accion="editar"` | Editar datos | `i-pencil` | `btn btn--sm` | `#modalEditar` |
| `data-accion="rechazar"` | Rechazar | `i-x` | `btn btn--sm btn--outline-rojo` | `#modalRechazar` |
| `data-accion="aprobar"` | Aprobar | `i-check` | `btn btn--sm` + `btn--aprobar-rojo` si nivel rojo | `#modalAprobar` |

### 2.1 El tono de «Aprobar» depende del nivel MTS

`pedirAprobar()` (`auditoria/app.js:574-606`) cambia el botón a `btn--aprobar-rojo` cuando `nivelMTS === "rojo"`. Consecuencias, todas verificables:

- El icono alterna entre `i-check` e `i-alert`.
- El título del diálogo pasa a insistir en que la sala no está valorada.
- Aparece la casilla de confirmación obligatoria `#chkRojo`.
- El botón de firma arranca **deshabilitado** y no se habilita hasta marcarla.

Decisión de seguridad-clínica acertada: **aprobar un caso rojo nunca es un clic accidental**, exige un acknowledgement explícito. El wireframe la mantiene como requisito, no como detalle de implementación.

### 2.2 «Editar datos» no es una acción de revisión

Aunque comparte la tarjeta, editar no revisa: corrige la entrada del modelo y fuerza una reevaluación. Por eso no exige firma — lo que se firma es la inferencia, y editar cambia la inferencia antes de que exista la decisión. Sí deja rastro: anotación `editado` y el distintivo *«Editado por humano»* en la cabecera de la tarjeta.

---

## 3. Acciones de la barra de herramientas

### 3.1 A4 · Reanalizar Lote

| Aspecto | Comportamiento |
|---|---|
| Efecto | `score` de cada pendiente pasa a `clamp(0.28, 0.93, score + (Math.random()*0.3 - 0.15))` (`auditoria/app.js:770-796`) |
| Latencia | 1 400 ms simulados, con `disabled` y `.is-loading` |
| Firma | No |
| Por qué no firma | Reejecutar el modelo no cambia ninguna decisión profesional |

Consecuencia de diseño: como el score se mueve, **un documento puede entrar o salir de los tres disparadores de auditoría** (ver [`02-estados.md` §2.1](02-estados.md)). Es la vía de la transición T4, escalamiento a auditoría.

### 3.2 A5 · Aprobación Rápida Asistida

| Aspecto | Comportamiento |
|---|---|
| Elegibilidad | `score >= UMBRAL_RAPIDA && nivelMTS !== "rojo"`, con `UMBRAL_RAPIDA = 0.55` (`auditoria/app.js:39, 799-801`) |
| Sin elegibles | Toast naranja, sin diálogo |
| Diálogo | `#modalRapida` con la lista de elegibles: paciente, ID y banda de confianza |
| Firma | **Sí**, un único gesto firmado cubre N documentos |
| CTA | «Aprobar N documento(s)», dinámico |

Es la única acción en lote del sistema, y por tanto la más peligrosa: firma N decisiones en un solo gesto. Tiene tres barreras — exclusión de casos rojos, umbral de confianza, y confirmation explícita de la lista. El wireframe mantiene las tres y propone una cuarta en [`07-sprint2.md` §P4](07-sprint2.md).

---

## 4. Acciones de los diálogos

### 4.1 A3 · Aprobar

| Campo | Comportamiento |
|---|---|
| Resumen | `dl` con documento, paciente, nivel MTS, ubicación, diagnóstico A y confianza (`auditoria/app.js:588-600`) |
| Confirmación obligatoria | `#chkRojo`, solo con nivel rojo |
| Firma | `#btnAprobarOk` → `anotar("aprobado")` + `d.resuelto = true` |
| Registra | Médico `Dr. M. Vance, MD`, firma `MED-99120-VANCE`, fecha y hora |

El resumen es la pieza de seguridad del diálogo: el profesional ratifica **sin releer la tarjeta**, sobre un resumen explícito de lo que aprueba.

### 4.2 A2 · Rechazar

| Campo | Comportamiento |
|---|---|
| Campo obligatorio | `#txtMotivo`, mínimo **10 caracteres**, contador en vivo |
| Validación | `#mRechazarError` visible y foco al campo si no se cumple |
| Firma | `#btnRechazarOk` → `anotar("rechazado")` + `d.resuelto = true` + `d.motivo` |

El motivo obligatorio es la razón de que exista el registro de auditoría: un rechazo sin explicación es indistinguible de un fallo.

### 4.3 A1 · Editar datos

| Campo | Comportamiento |
|---|---|
| Nivel MTS | `<select>` con 3 niveles: Rojo, Naranja, Amarillo |
| Ubicación | texto libre |
| Diagnóstico A / B | texto libre |
| Discriminador | área de texto |
| Signos vitales | un input por constante de `FILTROS_VITALES`, con `min`/`max`/`step` y validación de plausibilidad |
| Pupilas | `<select>` con 5 valores |
| Efecto | Reescribe campos, marca `editado = true`, ajusta `score` a `min(0.99, score + 0.05 + (subió ? 0.03 : 0))` |
| Si el nivel se vuelve **más urgente** | Fuerza `subio = true`, con incremento extra de confianza |

Que subir de gravedad **aumente** la confianza es intencional: confirmar que un caso es más grave es una validación fuerte del modelo. Ese mismo razonamiento justifica la transición T1 de la máquina de estados.

Dos problemas reales de este diálogo, detallados en [`06-auto-revision.md`](06-auto-revision.md):

- El selector de nivel ofrece 3 de los 5 niveles del catálogo (H9).
- La validación usa `plausMin`/`plausMax`, no `critLo`/`critHi`. Wide open: un valor plausible pero crítico, como SpO2 94, se acepta sin advertencia, cuando el rango clínico está a mano en la misma constante (H10).

### 4.4 A5 · Aprobación rápida

| Campo | Comportamiento |
|---|---|
| Lista | Un `<li>` por documento: `i-file-check`, paciente, ID y banda de confianza |
| CTA | «Aprobar N documento(s)» |
| Efecto | `anotar("aprobado")` + `d.resuelto = true` por cada uno |

---

## 5. Acciones globales de la pantalla

| Elemento | Efecto | Estado |
|---|---|---|
| `Escape` | Cierra el diálogo abierto | Implementado |
| Clic en el overlay | Cierra el diálogo | Implementado |
| `Tab` dentro del diálogo | Trampa de foco cíclica | Implementado |
| `Ctrl+K` / `Ctrl+F` | Foco en el buscador | Implementado |
| Notificaciones · Señal HIS · Ayuda | Toast informativo | **Sin efecto real** |
| «Ver Registro de Auditoría Completo» | `preventDefault` + toast con el recuento | **Sin destino** |
| Menú de usuario (3 ítems) | Cierran el menú | **Sin efecto** |
| `Configuración` y `Soporte HIS` del sidebar | `href="#"` | **Sin destino** |

---

## 6. Acciones de navegación que este wireframe añade

Ninguna existe hoy en el código. Se definen aquí porque el punto 5 pide que la interfaz muestre las acciones principales de revisión, y sin ellas el flujo se rompe:

| # | Acción | Dónde | Destino |
|---|---|---|---|
| N1 | **Ver detalle completo** | Zona de confianza de la tarjeta | `detalle/index.html?doc=…` |
| N2 | **Ver en el listado** | Detalle de un documento en auditoría | `historial/index.html?doc=…` |
| N3 | **Ir a la cola** | Detalle con nivel MTS asignado | `colas/index.html` |

Ver [`05-navegacion.md`](05-navegacion.md).

---

## 7. Criterios de aceptación

1. Cada una de las cinco acciones está disponible, es alcanzable por teclado y tiene etiqueta textual, nunca solo icono.
2. Ninguna acción de firma es ejecutable con un solo clic en un caso rojo.
3. Rechazar sin motivo no es posible: el diálogo lo bloquea y explica por qué.
4. Aprobar en lote muestra siempre la lista exacta de documentos afectados antes de firmar.
5. Aprobar en lote nunca incluye un caso de nivel rojo.
6. Editar datos nunca exige firma, pero siempre deja rastro visible.
7. Toda acción firmada deja anotación con médico, firma, fecha, hora y documento.
8. Toda acción de la barra se puede cancelar sin consecuencia si el resultado aún no está disponible.
9. Ninguna acción deja la interfaz en un estado intermedio: siempre hay una tarjeta que se retira, un diálogo que se cierra o un toast que confirma.

---

Ver también: [`02-estados.md`](02-estados.md) · [`03-panel-auditoria.md`](03-panel-auditoria.md) · [`05-navegacion.md`](05-navegacion.md) · [`06-auto-revision.md`](06-auto-revision.md)
