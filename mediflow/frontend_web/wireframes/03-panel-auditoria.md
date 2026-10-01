# 03 — Vista del panel de auditoría

> Punto 4 de la lista: *«Diseñar la vista del panel de auditoría»*.
> Wireframe visual: [`html/panel-auditoria.html`](html/panel-auditoria.html)
> Pantalla real: [`auditoria/`](../../auditoria/index.html)

---

## 1. Propósito y usuario

**Qué es.** La cola de supervisión humana sobre la inferencia diagnóstica. Recibe los documentos que el modelo ha detenido y permite que un profesional confirme, corrija o rechace la inferencia, dejando siempre constancia firmada.

**Quién.** Un profesional clínico durante su turno, con carga de trabajo limitada y presión de tiempo. No es un usuario que explora: es un usuario que **descarta y avanza** lo más rápido posible sin perder la seguridad clínica.

**Restricción que manda sobre el diseño.** El coste de un falso negativo es un paciente sin valoración. El coste de un falso positivo es tiempo de un profesional. El diseño se sesga de forma deliberada hacia el primero: por eso los casos rojos exigen acknowledgement explícito, por eso el rechazo exige motivo escrito y por eso la aprobación en lote excluye los rojos.

---

## 2. Estructura de la pantalla

Cuatro bandas, de arriba abajo:

| # | Banda | Contenido | Responde a |
|---|---|---|---|
| 1 | Banner de estado | 5 KPIs, insignia de alerta, latencia | ¿Cuánto trabajo hay y es urgente? |
| 2 | Barra de herramientas | 4 pestañas con contador, Reanalizar, Aprobación Rápida, protocolo | ¿Cómo filtro y qué hago con el lote? |
| 3 | Lista de tarjetas | Un documento por tarjeta, 4 zonas | ¿Qué dice el modelo sobre este caso? |
| 4 | Diálogos | Aprobar, Rechazar, Editar, Rápida | ¿Confirmo mi decisión? |

El orden es deliberado: **estado agregado → control del lote → detalle individual → confirmación.** Se lee de lo general a lo particular y se decide de lo particular a lo agregado.

---

## 3. Banner de estado

Cinco indicadores, derivados de los pendientes reales (no de constantes fijas):

| KPI | Definición | Uso |
|---|---|---|
| Pendientes | `pendientes().length` | Tamaño de la cola |
| Bajo umbral | `score < UMBRAL` (0.60) | Volumen de D2 |
| Críticos | `nivelMTS === "rojo"` | Volumen de D1, el único que puede justificar interrupting el resto |
| Discrepancias | discriminador robusto | Volumen de D3 |
| En revisión | documentos ya tocados por un profesional | Trabajo ya hecho, para no repetirlo |

**Insignia de alerta** binaria, con solo dos literales: «CONFIANZA SOBRE UMBRAL» o «NIVEL DE CONFIANZA BAJO».

**Latencia** de inferencia en ms, o guion si no hay dato.

> **Por qué los KPIs son el primer elemento y no un adorno.** El triaje MTS exige saber primero si hay un rojo. Con cinco números arriba, el profesional decide en dos segundos si entra por urgencia o por rutina. Sin ellos, tendría que recorrer tarjetas para descubrirlo.

---

## 4. Barra de herramientas

### 4.1 Las cuatro pestañas

| Pestaña | Filtro |
|---|---|
| Todos | Sin filtro |
| Críticos | Motivo **D1** (gravedad) |
| Discrepancias | Motivo **D3** |
| En revisión | Motivo **D2** (confianza bajo umbral) |

Cada una lleva contador. El orden es por severidad decreciente: lo que más puede doler es lo primero.

> **Reinterpretación necesaria.** Hoy estas pestañas filtran por el campo `estado` de la tarjeta, con valores `critico` / `discrepancia` / `revision` que son un vocabulario paralelo al del listado y no se corresponden con él (ver [`02-estados.md` §2.2](02-estados.md)). Este wireframe las reinterpreta como **filtros por motivo de entrada en auditoría**, lo que las hace coherentes con el ciclo de vida único sin cambiar su comportamiento observable.

### 4.2 Acciones de lote

`Reanalizar Lote` y `Aprobación Rápida Asistida`, a la derecha, con el protocolo declarado a la derecha del conjunto: «MTS v5.2».

Aprobación Rápida se muestra **deshabilitada con texto explicativo** cuando no hay elegibles, en lugar de mantenerse activa y fallar al pulsarla. Detalle en [`04-acciones.md` §3.2](04-acciones.md).

---

## 5. Anatomía de la tarjeta

Cuatro zonas. El orden es el orden de lectura del razonamiento clínico: primero quién es y qué nivel tiene, después qué se midió, después qué dice el modelo, y por último cuánto se confía en ello y qué se puede hacer.

### Zona A · Identificación

| Elemento | Campo | Notas |
|---|---|---|
| Badge MTS | `nivelMTS`, `mtsSufijo` | «Color Nivel N (min min) – Base» |
| ID | `id` | `.doc-id` |
| Distintivo | `editado` | «Editado por humano», solo si `editado === true` |
| Ubicación | `ubicacion` | con `i-inbox` |
| Paciente | `paciente` | |
| Edad y DNI | `edad`, `dni` | Si `edad === null`, muestra «Edad y DNI reservados» |
| Temporizador | `espera`, `maxEspera` | «Espera: mm / max min máx» |
| Aviso de retraso | `espera > maxEspera` | `.audit-card__timer--late` + «TIEMPO AGOTADO: mm min de retraso» |
| Origen | `origen` | alineado a la derecha |

**El temporizador es el elemento de diseño más importante de la tarjeta.** Convierte el objetivo temporal del protocolo MTS en un contador visible, y al superarlo añade un mensaje explícito. Responde a la pregunta que un profesional en turno se hace constantemente: «¿debería haber atendido ya este caso?». Es la traducción visual de los `min` de cada nivel MTS en [`01-listado.md` §4.2](01-listado.md).

### Zona B · Signos vitales

Rejilla de constantes de `FILTROS_VITALES` (`auditoria/app.js:54-64`), cada una con valor, unidad y referencia de rango.

**Dos niveles de señalización, y la diferencia importa:**

| Clase | Condición | Significado |
|---|---|---|
| `vital--crit` | Fuera de `critLo`/`critHi` | Fuera del rango de seguridad: salta a la vista |
| `vital--mal` | `crit === true` o `mal === true` | Marcado como clínicamente anormal por el modelo |

Conjunto variable según el documento: si hay Glasgow, se muestra `[PA, FC, SpO2, FR, T, Glasgow, Pupilas]`; si no, `[PA, FC, SpO2, FR, T, GLUC]`.

Debajo, una nota de dos fuentes alternativas según el documento: `<strong>Antecedentes:</strong> {antecedentes}` o, si no existe, `<strong>Episodio:</strong> {nota}`.

### Zona C · Inferencia del modelo

| Elemento | Contenido |
|---|---|
| Estado de la inferencia | `estadoIA`, con `i-shield-search` |
| Diagnóstico A · alerta | `diagA` |
| Separador | «vs» |
| Diagnóstico B · alternativo | `diagB` |
| Razonamiento discriminador | `discriminador` |
| Advertencia | `advertencia`, teñida con la familia de color del nivel MTS |

El par A/B con separador no es decoración: **el valor del modelo está en el contraste entre las dos hipótesis, no en la primera.** Un modelo que solo devuelve un diagnóstico no aporta información accionable. Mostrar ambas, con el razonamiento que las separa, es lo que permite al humano detectar un error de razonamiento y no solo un error de resultado.

### Zona D · Confianza y acciones

| Elemento | Contenido |
|---|---|
| Banda de confianza | «Confianza baja / media / alta» |
| Estado frente al umbral | «Por debajo del umbral» / «En zona de revisión» / «Sobre el umbral» |
| Barra | Relleno proporcional al score, con marcador de posición |
| Escala | «Baja / Media / Alta» |
| Nota de corte | «Umbral de corte aplicado en validación» |
| Acciones | Editar datos · Rechazar · Aprobar |

**El score no se muestra como número.** Es una decisión explícita del proyecto, documentada en el propio código (`auditoria/app.js:253-254`): el score se usa internamente para el ancho de la barra, el orden y el umbral, pero el profesional ve una **banda cualitativa** más el estado frente al umbral. Un número invites a reinterpretarlo como probabilidad; una banda con un umbral explícito invita a decidir.

**El marcador en la barra materializa el umbral**: la posición del corte es visible, de modo que «media» y «sobre el umbral» no son la misma cosa. Es lo que permite entender por qué un documento está en la cola.

### 5.1 Orden de la lista

`visibles()` (`auditoria/app.js:288-308`) ordena por urgencia de nivel MTS y, a igualdad, por score **ascendente**: primero lo más grave y, dentro de la misma gravedad, lo que menos confianza tiene. Es decir, **lo que más necesita intervención sube.**

---

## 6. Diálogos

Cuatro, todos con trampa de foco cíclica, cierre por `Escape`, cierre por clic en el overlay, y `body.is-locked` al abrirse.

| Diálogo | Campos | Exige |
|---|---|---|
| `#modalAprobar` | Resumen `dl` de 6 campos + hora; casilla si nivel rojo | Firma, y casilla si rojo |
| `#modalRechazar` | Motivo con contador y mínimo de 10 caracteres | Firma y motivo |
| `#modalEditar` | Nivel, ubicación, diagnósticos, discriminador, vitales | Guardar y recalcular |
| `#modalRapida` | Lista de elegibles | Firma del lote |

El foco inicial se coloca siempre en el campo de mayor riesgo: la casilla de confirmación en `#modalAprobar` con nivel rojo, el campo de motivo en `#modalRechazar`. No en el botón de firmar, para que una pulsación de `Enter` no ejecute la acción por inercia.

Detalle campo a campo en [`04-acciones.md` §4](04-acciones.md).

---

## 7. Criterios de aceptación

1. Los cinco KPIs son visibles sin desplazamiento y reflejan datos reales, no constantes fijas.
2. Si hay algún caso rojo, la insignia de alerta y el KPI «Críticos» lo hacen evidente antes de leer una sola tarjeta.
3. La lista está ordenada por necesidad de intervención, no por orden de llegada ni alfabético.
4. Toda tarjeta muestra las cuatro zonas sin conexión de red ni interacción adicional.
5. El score nunca aparece como número, en ninguna zona.
6. El umbral es visible tanto en la barra como en el texto del estado.
7. Superar el tiempo máximo produce un aviso explícito, no solo un cambio de color.
8. Los valores fuera de rango se distinguen de los marcados como anormales.
9. Ningún caso rojo puede aprobarse sin marcar la casilla de confirmación.
10. Un rechazo exige motivo escrito de al menos 10 caracteres.
11. Aprobar en lote muestra la lista exacta antes de firmar y excluye los casos rojos.
12. Toda tarjeta ofrece un enlace al detalle completo del documento (acción N1 de [`04-acciones.md` §6](04-acciones.md)).

---

Ver también: [`02-estados.md`](02-estados.md) · [`04-acciones.md`](04-acciones.md) · [`05-navegacion.md`](05-navegacion.md) · [`06-auto-revision.md`](06-auto-revision.md)
