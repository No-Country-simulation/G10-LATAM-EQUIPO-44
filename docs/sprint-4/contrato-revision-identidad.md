# Contrato de revisión e identidad — 24/10/2026

> **Actualización posterior del 24/10:** el usuario aclaró que Tailscale será
> solo el acceso de red y autorizó usuarios/contraseñas propios de MediFlow.
> La autenticación descrita con Tailscale en el registro siguiente quedó
> sustituida. Implementación, creación de cuentas y configuración vigentes:
> [usuarios-mediflow.md](usuarios-mediflow.md). El contrato de revisión se conserva.

Agregado por Edil. El usuario autorizó avanzar con la aprobación del contrato
de revisión existente. No se añadieron endpoints ni una segunda versión del
registro OCI. No se hicieron commits, push ni cambios en main.

## Estado real

| Punto | Implementación | Falta para uso real |
| --- | --- | --- |
| Contrato HTTP de Drazen/Eliana | Aprobado para habilitación en la presentación; conserva solicitud de cuatro campos y registro de seis | Aceptación de persistencia contra OCI |
| `cargado_por` | Cuenta verificada del cargador, persistida en recepción y análisis y recuperada por GET | Las cargas por un Uvicorn directo sin proveedor de identidad siguen devolviendo null |
| Identidad del auditor | Tailscale Serve → principal interno → backend; formulario de solo lectura | Definir las cuentas concretas que serán auditoras |
| Permiso para decidir | Lista explícita externa, vacía por defecto; cuenta sin permiso recibe 403 | El usuario indicó que todavía no dispone de esas cuentas |
| Aceptación frontend–OCI | Secuencia local con gestor real y SDK en memoria aprobada | Caso sintético real de dos documentos, todavía NO EJECUTADO |

## Solicitud y persistencia

`POST /api/documents/{document_id}/review` conserva exactamente estos campos:

```json
{
  "decision": "aprobado",
  "reviewer_id": "<login autenticado>",
  "observacion": null,
  "expected_review_status": "pendiente"
}
```

`decision` admite `aprobado` o `rechazado`. El rechazo exige observación no vacía.
`reviewer_id` debe coincidir con la identidad canónica comprobada en el servidor;
escribir un nombre en una petición no autentica. El backend persiste su principal,
no un valor libre del navegador. Falta de identidad: 401; falta de permiso,
suplantación o origen no autorizado: 403, antes de consultar OCI.

La respuesta 200 y el registro persistido mantienen seis campos:
`documento_id`, `review_id`, `review_status`, `reviewer_id`, `observacion`,
`reviewed_at`. El servidor genera ID y fecha UTC-Z. Otra decisión final devuelve
409. Se conserva la prioridad y el análisis original; aprobar no mueve por sí
solo el documento a otro bucket ni certifica seguridad clínica.

Se conservan `GET /api/reviews/pending`, GET individual y GET del historial.
El prototipo comentado `/api/auditoria/revision` continúa sin registrarse.

## Identidad y configuración

La presentación escucha exclusivamente en `127.0.0.1:8787`. Tailscale Serve es
el proxy de confianza y añade `Tailscale-User-Login`. Solo el wrapper de
presentación interpreta ese header, en modo explícito, con peer TCP loopback y
Host del origen configurado. Uvicorn usa `proxy_headers=False` para conservar
el peer original. Un Uvicorn directo de `app.main` no acepta headers enviados
por el cliente como prueba de identidad. Equipos con tags que no aporten
identidad de usuario no pueden decidir.

El administrador local y el daemon Tailscale forman parte de la frontera de
confianza. No exponer este listener en LAN ni reutilizar el modo proxy en un
servidor público. La seguridad de lectura de la presentación sigue dependiendo
de las reglas existentes de la tailnet; no se implantó un login clínico general.

Configuración local en `mediflow/.env`, ya protegido por Git:

```dotenv
MEDIFLOW_AUTH_MODE=tailscale
MEDIFLOW_PUBLIC_ORIGIN=https://desktop-2amsjb6.tailf48a22.ts.net
MEDIFLOW_REVIEWER_LOGINS=
```

La lista actual está vacía, por instrucción del usuario que aún no tiene las
cuentas. Cuando las defina, se completará con sus logins exactos separados por
coma y se reiniciará el servidor. No se concede permiso automáticamente a los
miembros de la red, ni se reutilizan credenciales OCI como identidad humana.

El BAT de presentación añade `--enable-approved-reviews` tras esta aprobación.
El flag habilita el contrato, pero jamás omite identidad, lista de auditores ni
validación de origen. Sin la identidad configurada, ese modo no inicia.

Las escrituras de revisión exigen `Origin` exactamente igual al origen HTTPS
autorizado. Se rechaza `Origin: null`, origen ajeno, ausencia de Origin o
`Sec-Fetch-Site: cross-site`. Esto evita que el CORS general existente se tome
por una protección contra solicitudes desde otra web. El código no cambia la
conexión Flutter ni añade secretos al JavaScript.

Tailscale documenta sus headers y la eliminación de headers de identidad
aportados por el cliente: [identidad de Serve](https://tailscale.com/docs/features/tailscale-serve#identity-headers).

## Semántica de `cargado_por`

Es el login de quien subió el archivo, distinto del profesional extraído y del
auditor que revisa. Se obtiene del principal de la petición, no del documento,
Gemini ni un formulario. Se conserva aunque Gemini falle y se recupere la
recepción por GET. El análisis no puede sustituirlo. El campo es nullable para
documentos históricos y cargas sin autenticación; no se inventan autores ni se
reescriben los JSON históricos. La proyección clínica enviada a Gemini no añade
esta identidad al prompt ni al esquema de extracción.

## Verificación de esta entrega

- Python: 507 pruebas y 29 subcasos aprobados; seis pruebas externas excluidas.
- Web: 149 pruebas aprobadas, incluida secuencia HTTP con FastAPI y gestor de
  Brando, usando exclusivamente un SDK en memoria.
- Casos nuevos: identidad ausente, cuenta sin permiso, suplantación, origen
  ajeno, headers duplicados, peer no confiable, identidad por petición y
  propagación del cargador en POST/GET y fallo de IA.
- HTTPS privado: salud, HTML y OpenAPI 200; identidad disponible; permiso falso
  con lista vacía; intento de revisión rechazado con 403.
- Inspección visual: identidad sintética `test-auditor` de solo lectura; ningún
  envío realizado desde esa inspección. Captura en
  `evidencias/edil-s4-identidad-sintetica.jpg`.
- Sin peticiones de documentos a OCI, sin escrituras OCI y sin Gemini en esta
  verificación. No se repitieron pruebas Flutter: no se modificó su código.

La aceptación externa queda descrita en
[aceptacion-revision-real.md](aceptacion-revision-real.md). Requiere cuentas de
auditor autorizadas y autorización del caso de seis objetos nuevos. Una prueba
sintética local no se presenta como validación clínica ni aceptación OCI.
