# 06 — Auto-revisión de consistencia

> Punto 7 de la lista: *«Realizar una auto-revisión de consistencia y completar los wireframes sin depender de validación de otros roles»*.

Este documento no espera validación de diseño, UX ni desarrollo. Cada hueco se resolvió o se dejó explícito como decisión abierta en [`07-sprint2.md`](07-sprint2.md).

**Método.** Barrido de los 5 `app.js` y los 5 `index.html` buscando: identificadores muertos, vocabularios paralelos, catálogos divergentes, contadores estáticos, acciones sin efecto y enlaces sin destino. Cada hallazgo se verificó contra el archivo antes de anotarse. Ninguno se deduced de una suposición.

**Resumen: 12 hallazgos. 4 se resuelven dentro de estos wireframes, 3 se resuelven reescribiendo la especificación, 5 quedan diferidos.**

---

## 1. Tabla de hallazgos

| # | Severidad | Hallazgo | Resolución | Dónde |
|---|---|---|---|---|
| H1 | **Crítica** | No existe vista de detalle; ningún clic en fila o tarjeta abre nada; `data-doc` es un identificador inerte | **Resuelto en el wireframe.** Se diseña la pantalla direccionable con `?doc=ID` | [`05-navegacion.md`](05-navegacion.md) |
| H2 | **Crítica** | Dos vocabularios de estado incomparables: `recibido/procesado/auditoria` frente a `critico/discrepancia/revision` | **Resuelto en la especificación.** Ciclo de vida único de 3 estados; el segundo vocabulario degrada a motivos | [`02-estados.md` §2.2](02-estados.md) |
| H3 | **Alta** | Ningún estado puede cambiar: las acciones solo hacen `d.resuelto = true`; `estado` es de solo lectura en las 5 pantallas | **Especificado, pendiente de implementar.** 7 transiciones con disparadores | [`02-estados.md` §3](02-estados.md) |
| H4 | **Alta** | Botón «Nuevo Ingreso» muerto en las 5 pantallas: es un `<button data-nav="ingesta">` sin listener | Diferido. No afecta al alcance de estos wireframes | [`07-sprint2.md` §P5](07-sprint2.md) |
| H5 | **Alta** | `.estado-chip` no existe en la hoja común; el color está cableado en 3 reglas de `historial/styles.css` | Especificado: promover a `styles.css` con tokens semánticos | [`02-estados.md` §4.3](02-estados.md) |
| H6 | **Media** | El badge `#navAuditTotal` miente: marca 4 en `resultado`, `ingesta` y `colas` (y 5 estático en `historial`) frente a los 5 documentos reales | Diferido, con criterio definido: la fuente de verdad es `pendientes().length` | [`07-sprint2.md` §P5](07-sprint2.md) |
| H7 | **Media** | `registro[]` es volátil e invisible; el enlace «Ver Registro de Auditoría Completo» apunta a un ancla inexistente y muestra un toast | **Resuelto en el wireframe.** El detalle incluye el registro filtrado por documento | [`05-navegacion.md` §4.3](05-navegacion.md) |
| H8 | **Media** | 3 acciones decorativas del topbar (Notificaciones, Señal HIS, Ayuda) y 3 ítems del menú de usuario solo muestran un toast o cierran el menú | Diferido, son de alcance transversal | [`07-sprint2.md` §P5](07-sprint2.md) |
| H9 | **Media** | **Catálogo MTS divergente**: `historial` define 5 niveles (rojo, naranja, amarillo, verde, azul), `auditoria` solo 3. El selector de nivel del modal de edición no puede asignar verde ni azul | **Resuelto en la especificación.** El catálogo canónico es el de 5 niveles | [`01-listado.md` §4.2](01-listado.md) |
| H10 | **Media** | El modal de edición valida con `plausMin`/`plausMax`, no con `critLo`/`critHi`: un SpO2 de 94 se acepta sin advertencia, cuando el rango clínico está en la misma constante | Diferido, con criterio definido: avisar de lo crítico sin bloquear lo plausible | [`07-sprint2.md` §P6](07-sprint2.md) |
| H11 | **Baja** | `auditoria/app.js` no tiene `sincronizarNav()`; depende del `is-active` fijo en el HTML, mientras las otras 4 pantallas lo calculan | Diferido | [`07-sprint2.md` §P5](07-sprint2.md) |
| H12 | **Baja** | `d.edad` es `null` en los 5 registros, así que el DNI nunca se renderiza y siempre sale «Edad y DNI reservados» | Diferido: es consecuencia de la neutralización de datos, no un defecto | [`07-sprint2.md` §P7](07-sprint2.md) |

---

## 2. Detalle de los cuatro hallazgos resueltos

### H1 · Vista de detalle

Resuelto en [`05-navegacion.md`](05-navegacion.md): pantalla `detalle/index.html?doc=ID`, alcanzable desde el listado y desde la tarjeta de auditoría, con migas de pan, estado vacío para `doc` ausente o inválido, y reutilización de las zonas de la tarjeta para no duplicar presentación.

### H2 · Vocabularios de estado

Resuelto en [`02-estados.md` §2.2](02-estados.md). El cambio es de interpretación, no de comportamiento: las cuatro pestañas del panel siguen filtrando igual, pero ahora lo hacen **sobre una verdad única**. Un documento en `Auditoría` por confianza baja y un documento en `Auditoría` por gravedad dejan de ser categorías que compiten y pasan a ser dos motivos del mismo estado.

### H7 · Registro de auditoría

Resuelto en [`05-navegacion.md` §4.3](05-navegacion.md). El detalle incluye una sección de registro filtrada por documento, lo que da destino real a un enlace que hoy no lleva a ninguna parte y convierte un array volátil en un artefacto de trazabilidad. La sección de historial de estados cumple la misma función para el ciclo de vida.

### H9 · Catálogo MTS

Resuelto en [`01-listado.md` §4.2](01-listado.md). Se fija el catálogo de 5 niveles como canónico, porque es el que tiene tiempos objetivo completos y el que usa el listado. El de 3 niveles de auditoría es un subconjunto por gravedad, útil para ordenar, pero insuficiente como catálogo editable.

---

## 3. Verificaciones que sí pasan

Como contraste, esto es lo que se comprobó y **resultó coherente**, para que no haya que reverificarlo en Sprint 2:

| Verificación | Resultado |
|---|---|
| Sintaxis de los 5 `app.js` | Correcta |
| Identificadores referenciados por JS que no existen en el DOM | Ninguno |
| Iconos SVG usados y no definidos en el sprite | Ninguno |
| Enlaces del sidebar a carpetas existentes | Los 5 correctos |
| Accentúa la tabla de estados y su orden | Coherente con `ESTADOS` |
| Accentúa niveles MTS y tiempos objetivo | Coherente con `MTS` |
| Foco atrapado en los diálogos | Implementado en los 4 |
| Bloqueo de scroll con `body.is-locked` | Implementado |
| `aria-sort` en columnas ordenables | Implementado |
| Filtros del listado reflejados en la URL | Implementado |

---

## 4. Coherencia interna de estos wireframes

Comprobación cruzada de los 7 documentos:

| Relación | Estado |
|---|---|
| Los 3 estados de [`02`](02-estados.md) son los mismos que pinta el listado | Consistente |
| Los 3 disparadores de auditoría de [`02` §2.1](02-estados.md) justifican las 3 pestañas de [`03` §4.1](03-panel-auditoria.md) | Consistente, 1:1 |
| Las 5 acciones de [`04`](04-acciones.md) coinciden con las que están implementadas | Consistente |
| Las 7 transiciones de [`02` §3.1](02-estados.md) tienen todas una acción de interfaz o son automáticas | Consistente |
| Las 5 acciones de navegación de [`05` §3](05-navegacion.md) están declaradas en [`04` §6](04-acciones.md) | Consistente |
| El score no se muestra en ningún documento | Consistente |
| Los 12 hallazgos aparecen en [`07-sprint2.md`](07-sprint2.md) | Consistente |

---

## 5. Lo que este documento NO hace

- **No valida la accesibilidad.** No hay auditoría WCAG ni prueba con lector de pantalla. Los requisitos de teclado y foco están declarados en los criterios de aceptación, pero no están verificados.
- **No valida el diseño clínico.** Que un nivel MTS sea el adecuado para un caso concreto es materia de un profesional, no de este documento. Aquí solo se documenta la estructura de la regla.
- **No corrige el código.** Los 12 hallazgos quedan especificados, no implementados. Esa es la frontera acordada: este entregable es documentación.
- **No decide las 5 cuestiones abiertas** de [`07-sprint2.md`](07-sprint2.md), que necesitan criterio de producto.

---

Ver también: [`07-sprint2.md`](07-sprint2.md) · [`README.md`](README.md)
