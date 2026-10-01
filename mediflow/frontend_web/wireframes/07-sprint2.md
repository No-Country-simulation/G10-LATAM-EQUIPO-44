# 07 — Entregable, decisiones abiertas y trabajo de Sprint 2

> Punto 8 de la lista: *«Guardar los wireframes como entregable individual listo para compartir y ajustar desde el Sprint 2»*.

---

## 1. Qué es este entregable

Un paquete de especificación de wireframes del flujo documental, cubriendo listado, estados, panel de auditoría, acciones de revisión y navegación, con una auto-revisión de consistencia y las decisiones que quedan abiertas.

**No es:** un incremento de código, una maqueta navegable de producción, ni una validación clínica. El código de las 5 pantallas queda intacto.

### 1.1 Trazabilidad con la lista

| Punto de la lista | Documento | Estado |
|---|---|---|
| 1 · Estructura del listado | [`01-listado.md`](01-listado.md) | Definido |
| 2 · Información básica por documento | [`01-listado.md`](01-listado.md) | Definido |
| 3 · Estados Recibido / Procesado / Auditoría | [`02-estados.md`](02-estados.md) | Definido con criterios |
| 4 · Vista del panel de auditoría | [`03-panel-auditoria.md`](03-panel-auditoria.md) | Definido |
| 5 · Acciones principales de revisión | [`04-acciones.md`](04-acciones.md) | Definido |
| 6 · Navegación listado ↔ detalle / auditoría | [`05-navegacion.md`](05-navegacion.md) | Definido, con vista nueva |
| 7 · Auto-revisión de consistencia | [`06-auto-revision.md`](06-auto-revision.md) | 12 hallazgos, 4 resueltos |
| 8 · Entregable listo para Sprint 2 | Este documento | Entregado |

---

## 2. Decisiones abiertas

Cinco cuestiones que **no** se pueden cerrar sin criterio de producto. Cada una lleva su recomendación, para que la decisión sea rápida.

### D1 · ¿Qué significa exactamente la variante azul de «Recibido»?

El campo `recibidoAzul` existe y solo lo tiene `DOC-0004`, y hay una regla CSS específica para él (`historial/styles.css:225`). El código nunca explica la intención.

| Opción | Descripción | Recomendación |
|---|---|---|
| A | Azul = alta automática validada desde HIS; gris = alta manual pendiente de verificar | **Recomendada.** Es la única lectura que explica por qué un estado sin gravedad tendría dos variantes |
| B | Azul = documento con inferencia ya calculada en segundo plano | Posible, pero entonces se solapa con `Procesado` |
| C | Es un residuo sin intención de diseño | Improbable: el campo y la regla existen ambos |

Bloqueante: define si la columna Estado necesita una leyenda de cuatro variantes en lugar de tres.

### D2 · ¿Debe existir un estado terminal «Cerrado»?

Hoy el ciclo va `Recibido → Procesado → Auditoría` y no tiene salida después de aprobar. Un documento aprobado sale de la cola, pero conceptualmente no está «procesado» hasta que el episodio termina.

| Opción | Descripción | Recomendación |
|---|---|---|
| A | Tres estados, y `Procesado` es terminal | **Recomendada para Sprint 2.** Mantiene el alcance de la lista y no añade un chip más |
| B | Añadir «Cerrado» como cuarto estado terminal | Más fiel al ciclo real, pero amplía el punto 3 más allá de lo que pedía la lista |

### D3 · ¿La franja de confianza 0.55–0.60 qué estado tiene?

`UMBRAL = 0.60` mete un documento en auditoría. `UMBRAL_RAPIDA = 0.55` permite aprobarlo en lote. Un score de 0.58 no cumple lo segundo, pero está por debajo del primero: **no es aprobable en lote y tampoco está claramente en auditoría.**

| Opción | Descripción | Recomendación |
|---|---|---|
| A | El rango 0.55–0.60 es «procesado con confianza limitada», fuera de ambas colas | **Recomendada.** Es la lectura más honesta: el documento no necesita humano, pero tampoco entra en aprobación asistida |
| B | Subir `UMBRAL_RAPIDA` a 0.60 para eliminar la franja | Simple, pero reduce la utilidad de la aprobación asistida justo en el rango limítrofe |
| C | Bajar `UMBRAL` a 0.55 para que la franja entre en auditoría | Aumenta la carga de trabajo del revisor en casos que el modelo resolvió razonablemente |

### D4 · ¿La vista de detalle es de lectura o también de decisión?

Este wireframe la define con ambas: muestra el ciclo de vida **y** ofrece Aprobar, Rechazar y Editar cuando el documento está en auditoría.

| Opción | Descripción | Recomendación |
|---|---|---|
| A | Lectura y decisión | **Recomendada.** Evita que el revisor tenga que saltar al panel para actuar, y es lo que hace que el detalle no sea un callejón sin salida |
| B | Solo lectura | Más simple, pero obliga a volver al panel para cualquier decisión |

### D5 · ¿Quién es el usuario del listado frente al del panel?

El listado parece pensado para recepción y guardia (densidad, ruta de almacenamiento, verificación). El panel, para el profesional revisor (confianza, discriminador, firma).

| Opción | Descripción | Recomendación |
|---|---|---|
| A | Dos perfiles con la misma navegación | **Recomendada.** Es lo que ya sugiere el código, y no exige cambios de arquitectura |
| B | Un único perfil indistinto | Oculta que las dos pantallas responden a preguntas distintas |

---

## 3. Trabajo de Sprint 2

Ordenado por prioridad. P0 es lo que desbloquea el resto.

### P0 · Vista de detalle

| Tarea | Tarea | Detalle |
|---|---|---|
| P0.1 | Crear `detalle/index.html` con el shell de 4 bandas | Plantilla de `assets/css/styles.css` |
| P0.2 | Resolver `?doc=` y pintar los estados vacío / inválido | Especificado en [`05` §5](05-navegacion.md) |
| P0.3 | Extraer `zonaVitales`, `zonaIA`, `zonaConfianza` a un módulo compartido | Ya existen como funciones en `auditoria/app.js:369-438`; mover sin reescribir |
| P0.4 | Volver la fila del listado clicable y navegable por teclado | Un `<a>` real en la celda del ID, no un `<tr>` con `role="link"` |
| P0.5 | Añadir la acción N1 «Ver detalle completo» a la tarjeta de auditoría | Se suma a las 3 existentes sin cambiar su layout |

### P1 · Consistencia del estado

| Tarea | Detalle |
|---|---|
| P1.1 | Implementar la máquina de 7 transiciones de [`02` §3.1](02-estados.md) |
| P1.2 | Unificar el vocabulario: `critico`/`discrepancia`/`revision` pasan a ser motivos |
| P1.3 | Propagar el estado desde el panel al listado, para que ambos reflejen la misma verdad |
| P1.4 | Unificar el catálogo MTS en 5 niveles y corregir el selector del modal de edición |
| P1.5 | Persistir `registro[]` y `eventos[]` en lugar de perderlos al recargar |

### P2 · Sistema visual

| Tarea | Detalle |
|---|---|
| P2.1 | Promover `.estado-chip` a `styles.css` con tokens `--estado-*-bg/border/ink` |
| P2.2 | Decidir el criterio de D1 y documentarlo en el código, no solo aquí |
| P2.3 | Corregir el badge `#navAuditTotal` para que lea de `pendientes().length` |

### P3 · Mejoras de listado

| Tarea | Detalle |
|---|---|
| P3.1 | Selección múltiple y acción masiva. **Requiere un estado terminal** (D2) para que la acción tenga destino |
| P3.2 | Exportación del listado filtrado |
| P3.3 | Columnas configurables |

### P4 · Seguridad de la aprobación en lote

| Tarea | Detalle |
|---|---|
| P4.1 | Cuarta barrera: exigir que el profesional revise la lista durante un mínimo de tiempo antes de habilitar el CTA |
| P4.2 | Registrar el lote como una anotación con el detalle de los N documentos, no N anotaciones sueltas |

### P5 · Limpieza de enlaces y acciones muertas

| Tarea | Detalle |
|---|---|
| P5.1 | «Nuevo Ingreso»: convertir el `<button data-nav>` en enlace real o cablearlo |
| P5.2 | Destino real para «Ver Registro de Auditoría Completo» |
| P5.3 | Enlazar o retirar Notificaciones, Señal HIS, Ayuda |
| P5.4 | Enlazar o retirar los 3 ítems del menú de usuario |
| P5.5 | Destino para Configuración y Soporte HIS del sidebar |
| P5.6 | Añadir `sincronizarNav()` a `auditoria/app.js` para igualarla a las otras 4 pantallas |

### P6 · Validación de datos en el modal de edición

| Tarea | Detalle |
|---|---|
| P6.1 | Avisar cuando un valor sale de `critLo`/`critHi`, sin bloquear la edición si está en `plausMin`/`plausMax` |
| P6.2 | Distinguir visualmente «fuera de rango de seguridad» de «plausible pero no óptimo» |

### P7 · Datos

| Tarea | Detalle |
|---|---|
| P7.1 | Al conectar el backend, los campos `edad` y `dni` dejarán ser `null` y el DNI volverá a mostrarse |
| P7.2 | Verificar que ningún dato clínico real llega a este repositorio |

---

## 4. Cómo ajustar este paquete en Sprint 2

| Quiero cambiar… | Dónde |
|---|---|
| Un color de estado | Los 3 valores de la tabla en [`02` §4](02-estados.md) **y** `historial/styles.css:224-227` |
| Las columnas del listado | La tabla en [`01` §2](01-listado.md) y `COLUMNAS` en `historial/app.js:73-81` |
| Los criterios de entrada en auditoría | La tabla de disparadores en [`02` §2.1](02-estados.md) y `UMBRAL` en `auditoria/app.js:38` |
| El contenido de la tarjeta | [`03` §5](03-panel-auditoria.md) y las funciones `zona*` de `auditoria/app.js:369-438` |
| Las acciones disponibles | La tabla de [`04` §1](04-acciones.md) y los `data-accion` de `auditoria/app.js:431-436` |
| La estructura del detalle | [`05` §4](05-navegacion.md) |
| Un wireframe visual | `html/*.html`, que son HTML plano y se editan sin herramientas |

**Regla de sincronía:** cada cambio de wireframe visual debe actualizar también su documento Markdown y la referencia a la línea del código. Un wireframe que contradice al documento vale menos que ningún wireframe.

---

## 5. Texto de la tarjeta de Trello

Listo para pegar en la tarjeta del tablero:

> **Wireframes del flujo documental — Sprint 1**
>
> **Qué contiene.** Paquete de wireframes y especificación de 8 documentos que cubren el listado de documentos, la información por documento, los estados Recibido/Procesado/Auditoría con sus criterios, el panel de auditoría, las acciones de revisión, la navegación listado-detalle, una auto-revisión de consistencia y las decisiones abiertas de Sprint 2.
>
> **Decisiones tomadas.** El listado es una tabla de 7 columnas. Se fija un ciclo de vida único de 3 estados, y los valores Críticos/Discrepancias/En revisión pasan a ser motivos de entrada en auditoría en lugar de estados paralelos. El score del modelo nunca se muestra como número: banda cualitativa y umbral visible. La vista de detalle será una pantalla nueva direccionable con `?doc=ID`, alcanzable desde el listado y desde la tarjeta de auditoría, y reutilizará las zonas de la tarjeta para no duplicar presentación.
>
> **Hallazgos de la auto-revisión.** 12, de los cuales 2 son críticos: no existe ninguna vista de detalle, y conviven dos vocabularios de estado incomparables. Ninguno bloquea Sprint 2, pero los dos son precondición de cualquier trabajo sobre el detalle.
>
> **Abierto a decisión de producto.** Qué significa la variante azul de «Recibido»; si hace falta un estado terminal «Cerrado»; qué ocurre con la franja de confianza entre 0.55 y 0.60; si el detalle permite decidir o solo leer; y si listado y panel tienen perfiles de usuario distintos.
>
> **Sin validación de otros roles.** La auto-revisión está completa y los criterios de aceptación de cada documento son verificables. No requiere firma de diseño, UX ni desarrollo para considerarse cerrado en Sprint 1.
>
> **No incluye.** No hay cambios en el código de las 5 pantallas. La accesibilidad y la validación clínica quedan fuera de alcance.

---

## 6. Lo que hay que hacer desde el tablero

1. Subir la carpeta `docs/wireframes/` como adjunto, comprimida.
2. Pegar el texto de §5 en la descripción de la tarjeta.
3. Resolver D1 a D5 y reflectirlos en los documentos correspondientes.
4. Crear una tarjeta por bloque de §3, con P0 primero.
5. Revisar visualmente `html/estados.html` y `html/detalle.html`, que son los dos que contienen decisiones de diseño nuevas.

---

Ver también: [`README.md`](README.md) · [`06-auto-revision.md`](06-auto-revision.md)
