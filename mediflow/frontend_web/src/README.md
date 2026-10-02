# clinicaFRONT

Prototipo navegable del front de una clinica de urgencias. Cinco pantallas HTML
independientes que comparten design tokens, hoja de estilos comun y la misma
navegacion lateral.

Es un prototipo **sin datos precargados**: los arrays de datos de cada pantalla
estan vacios a proposito y son el punto de sustitucion cuando se conecte el
backend.

## Como ejecutarlo

No hay build, ni `package.json`, ni dependencias. Es HTML5/CSS3/JavaScript
vanilla, asi que basta con servir la carpeta:

```bash
python -m http.server 8080
```

Y abrir <http://localhost:8080/>.

> Abrir `index.html` con doble clic tambien funciona, pero usar un servidor
> evita las restricciones de `file://` sobre algunos recursos.

No hay `index.html` en la raiz: entra directamente por `ingesta/`, que es la
pantalla de arranque del flujo.

## Pantallas

| Ruta              | Pantalla      | Que hace                                                                  |
| ----------------- | ------------- | ------------------------------------------------------------------------- |
| `ingesta/`        | Ingesta       | Alta de ingreso: captura del paciente, nivel MTS, motivo, constantes.     |
| `resultado/`      | Resultado     | Resultados de un episodio: KPIs, signos vitales, tabla de estudios, alertas y trazabilidad. |
| `colas/`          | Colas         | Tablero Kanban de triaje por nivel, con censo y detalle de cada tarjeta.  |
| `auditoria/`      | Auditoria     | Bandeja de registros con panel de auditoria y detalle de la accion.       |
| `historial/`      | Historial     | Consulta de documentos clinicos con trazabilidad de la ruta.              |

El flujo previsto es `ingesta -> colas -> resultado`, con `auditoria` e
`historial` como pantallas laterales accesibles desde el menu.

## Estructura

```
clinicaFRONT/
├── assets/
│   └── css/
│       └── styles.css          Tokens de diseño, layout y componentes comunes
├── ingesta/                    Pantalla de alta
│   ├── index.html
│   ├── app.js
│   └── styles.css              Reglas específicas de la pantalla
├── resultado/                  Pantalla de resultados
├── colas/                      Tablero Kanban
├── auditoria/                  Bandeja de auditoría
├── historial/                  Consulta de documentos
└── docs/
    └── wireframes/             Especificación funcional y visual
        ├── README.md
        ├── 01-listado.md … 07-sprint2.md
        └── html/               Maquetas navegables
```

### Convenciones

- **Tres archivos por pantalla**: `index.html`, `app.js` y `styles.css`. El
  `app.js` se incluye como ultimo elemento antes de `</body>`, sin
  `type="module"`.
- **`assets/css/styles.css` es la fuente commun.** Cada pantalla enlaza esa
  hoja y añade encima solo lo suyo en su `styles.css` propio.
- **Los tokens van en `:root`** en `assets/css/styles.css`. Cambiar un token
  reestiliza las cinco pantallas a la vez; no se hardcodean colores.
- **Rutas relativas entre pantallas** (`../colas/index.html`), porque las
  carpetas se sirven tal cual, sin raiz virtual.
- **SVG en un `<symbol>` sprite** definido al inicio de cada `index.html`, con
  `icon(nombre)` en el JS para insertarlos.
- **Atributo `data-nav`** en cada enlace de la barra lateral para marcar la
  pantalla activa, sincronizado por JS.

## Estado de los datos

Las pantallas arrancan vacias a proposito, para no implorar datos reales de
pacientes en el repositorio.

| Pantalla  | Variable / bloque                    | Estado            |
| --------- | ------------------------------------ | ----------------- |
| Colas     | `patients`                           | `[]`              |
| Resultado | `pacientes`, `data`, `pendientes`   | `[]`              |
| Resultado | `alertas`, `traza`, `signos`         | `{}`              |
| Ingesta   | `data`, `motivos`, `constantes`…     | Tablas de referencia del sistema (MTS, motivos, prioridades). No son pacientes. |
| Auditoria | Registros `AUD-0001`…`AUD-0005`     | Marcadores de posicion, con campos de relleno. |
| Historial | Registros `DOC-0001`…`DOC-0004`     | Marcadores de posicion, con campos de relleno. |

Al conectar el backend hay que respetar los contratos de cada bloque, que estan
documentados como comentario en el `app.js` de la pantalla correspondiente.

Las pantallas manejan el estado vacio de forma explicita: `Colas` muestra
`Sin pacientes en esta columna` y un censo de 0, y `Resultado` muestra
`Sin episodio cargado` y desactiva el selector de paciente. El badge de cola
refleja 0 en toda la aplicacion.

## Documentacion funcional

`docs/wireframes/` recoge la especificacion del trabajo pendiente, en ocho
documentos mas cinco maquetas navegables. Ver su
[README](docs/wireframes/README.md) para el indice y el alcance.

La maqueta `html/detalle.html` es solo especificacion visual: la vista de
detalle todavia no esta implementada como pantalla real.

## Estado actual

- Las cinco pantallas son navegables entre si y funcionan sin errores con los
  datos vacios.
- Auditoria e Historial son prototipos de interfaz: los registros son
  marcadores de posicion, no datos reales.
- No hay pruebas automatizadas ni validacion visual en este repositorio.