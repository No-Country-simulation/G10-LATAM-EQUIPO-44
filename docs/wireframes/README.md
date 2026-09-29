# Wireframes — MediFlow Clinical Portal

Especificación de wireframes del flujo documental: listado de documentos, estados, panel de
auditoría, acciones de revisión y navegación.


---

## Ver los wireframes

Abre [`html/index.html`](html/index.html) en el navegador. No hace falta servidor ni instalar nada.

Si prefieres servirlo, desde la raíz del proyecto:

```powershell
python -m http.server 8080
```

y entra en `http://localhost:8080/docs/wireframes/html/index.html`.

| Wireframe | Cubre | Documento |
|---|---|---|
| [`html/listado.html`](html/listado.html) | Puntos 1 y 2 | [`01-listado.md`](01-listado.md) |
| [`html/estados.html`](html/estados.html) | Punto 3 | [`02-estados.md`](02-estados.md) |
| [`html/panel-auditoria.html`](html/panel-auditoria.html) | Puntos 4 y 5 | [`03`](03-panel-auditoria.md) y [`04`](04-acciones.md) |
| [`html/detalle.html`](html/detalle.html) | Punto 6 | [`05-navegacion.md`](05-navegacion.md) |

## Los documentos

| # | Documento | Contenido |
|---|---|---|
| 01 | [Listado e información por documento](01-listado.md) | Las 7 columnas, justificadas una a una, y el contrato de datos |
| 02 | [Estados del documento](02-estados.md) | Criterios de los 3 estados, máquina de transiciones, valores de color |
| 03 | [Vista del panel de auditoría](03-panel-auditoria.md) | Las 4 bandas, la tarjeta y sus 4 zonas, los diálogos |
| 04 | [Acciones de revisión](04-acciones.md) | Las 5 acciones, su efecto, su riesgo y si exigen firma |
| 05 | [Navegación](05-navegacion.md) | Grafo, vista de detalle nueva, estados límite |
| 06 | [Auto-revisión](06-auto-revision.md) | 12 hallazgos de consistencia y su resolución |
| 07 | [Sprint 2](07-sprint2.md) | 5 decisiones abiertas, prioridades P0–P7, texto de la tarjeta |

---

## Resumen en cinco decisiones

1. **El listado es una tabla de 7 columnas**, no un grid de tarjetas. Todas ordenables, con
   ficha de paciente en la segunda columna y ruta de almacenamiento en la última.

2. **Tres estados, no más**: Recibido, Procesado y Auditoría. El ciclo se apoya en si hay
   inferencia calculada, si la confianza llega a 0.60 y si la gravedad es roja.

3. **Se elimina la competencia entre dos vocabularios de estado.** Los valores
   `critico` / `discrepancia` / `revision` del panel dejan de ser estados paralelos y pasan a ser
   **motivos de entrada** en Auditoría. Un documento puede tener varios a la vez.

4. **El score del modelo nunca se muestra como número.** Se ve una banda cualitativa, el
   estado frente al umbral y una barra con la marca del corte. El número se usa por dentro para
   ordenar y para decidir, no por fuera para interpretar.

5. **El detalle es una pantalla nueva** direccionable con `?doc=ID`, alcanzable desde el listado y
   desde la tarjeta de auditoría, que **reutiliza las zonas de la tarjeta** en vez de duplicar el
   marcado.

---

## Dos hallazgos que conviene mirar primero

1. **No existe ninguna vista de detalle.** Ninguna ruta, ningún handler de clic en las filas, los
   identificadores de documento no salen nunca a la URL.
2. **Conviven dos vocabularios de estado incomparables**, con identificadores que tampoco se
   corresponden (`DOC-0001` frente a `AUD-0001`).

Ninguno impide usar el proyecto. Los dos son precondición de cualquier trabajo sobre el detalle.
El análisis completo está en [`06-auto-revision.md`](06-auto-revision.md).

---

## Qué hay que decidir

Cinco cuestiones abiertas que bloquean el cierre de Sprint 2. Cada una lleva opciones y
recomendación en [`07-sprint2.md` §2](07-sprint2.md):

| # | Decisión |
|---|---|
| D1 | Qué significa la variante azul de «Recibido» |
| D2 | Si hace falta un estado terminal «Cerrado» |
| D3 | Qué estado tiene la franja de confianza entre 0.55 y 0.60 |
| D4 | Si el detalle permite decidir o solo leer |
| D5 | Si listado y panel tienen perfiles de usuario distintos |

---

## Convenciones de este paquete

- **Los Markdown son la fuente de verdad.** Si un wireframe visual y su documento discrepan,
  gana el documento.
- **Los colores son copia literal** de los tokens de `assets/css/styles.css`, duplicados en
  `html/styles.css` para que esta carpeta sea portable. Si cambia un token, hay que cambiarlo
  en los dos sitios.
- **Toda referencia al código lleva ruta y línea.** Si la línea deja de ser correcta, la
  referencia está caducada.
- **Los datos de ejemplo son marcadores genéricos.** No hay ningún dato clínico real.

