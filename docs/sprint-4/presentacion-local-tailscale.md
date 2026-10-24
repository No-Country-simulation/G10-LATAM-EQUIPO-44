# Presentación local de MediFlow con Tailscale

Agregado por Edil — 24/10/2026. La PC ejecuta el backend y la web; el teléfono entra por una red privada Tailscale. OCI y Gemini siguen siendo servicios externos y necesitan conexión cuando se utilicen.

## Estado comprobado

- Tailscale instalado, versión local `1.102.2`, conectado y sin avisos de salud.
- Nombre de la PC: `desktop-2amsjb6.tailf48a22.ts.net`.
- Antes de preparar esta guía, `tailscale serve status --json` devolvía `{}`: ningún servicio compartido.
- Solo había URLs de desarrollo: `127.0.0.1:8000` para web/Windows y `10.0.2.2:8000` para emulador. No se encontró URL HTTPS configurada del backend.
- Nuevo servidor local preparado: `127.0.0.1:8787`, web bajo `/web/` y API existente bajo `/api/`. No altera endpoints de negocio, buckets ni contratos.

Tailscale Serve puede publicar ese puerto dentro de la tailnet y gestionar HTTPS. El acceso queda sujeto a las reglas de acceso de la tailnet; los dispositivos deben estar conectados y autorizados. [Documentación oficial de Serve](https://tailscale.com/docs/features/tailscale-serve).

## 1. Iniciar MediFlow en la PC

Desde `D:\Nocountru`:

```powershell
.\iniciar_presentacion_local.bat
```

El BAT utiliza el entorno Python existente y escucha exclusivamente en loopback. No inicia Tailscale, no instala paquetes, no cambia Git ni envía documentos. La web sirve únicamente `mediflow/frontend_web/src`, nunca la raíz del repositorio o `.env`.

Pruebas locales sin documentos:

- Salud: `http://127.0.0.1:8787/`.
- Swagger: `http://127.0.0.1:8787/docs`.
- Panel: `http://127.0.0.1:8787/web/auditoria/index.html`.

Abrir el panel real sí consulta pendientes a través del backend y puede leer OCI. No confundirlo con el servidor sintético de `tests/support/review-api-server.py --web`.

El servidor inyecta `MEDIFLOW_API_BASE_URL=window.location.origin` en los HTML públicos. Así, web y API utilizan el mismo origen HTTPS cuando se accede desde el teléfono. El cliente remoto no intenta llamar a su propio localhost.

**Actualización autorizada del 24/10:** el contrato está aprobado y el BAT añade
`--enable-approved-reviews`. Tailscale se usa únicamente para acceder al servicio.
Los auditores ingresan con usuario y contraseña propios de MediFlow en
`/web/login/index.html`; no se necesitan cuentas ni correos de Tailscale para
definir sus permisos. El backend exige sesión, permiso de auditor y origen
autorizado antes de registrar una decisión. La primera cuenta se creará en el
equipo del despliegue mediante el comando de administración, sin contraseña
predeterminada. `cargado_por` toma el usuario de MediFlow autenticado en la carga;
las cargas anónimas y los JSON históricos usan null.

Configuración y creación de cuentas: [usuarios de MediFlow](usuarios-mediflow.md).
La aceptación con OCI real sigue [preparada, no ejecutada](aceptacion-revision-real.md).

## 2. Activar el acceso privado, después de autorización

Comando preparado, no considerar ejecutado solo por aparecer en esta guía:

```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve --bg --https=443 http://127.0.0.1:8787
& 'C:\Program Files\Tailscale\tailscale.exe' serve status
```

La primera activación puede exigir que el administrador habilite HTTPS/MagicDNS mediante el consentimiento indicado por Tailscale. La sesión o aprobación administrativa debe completarla el usuario. [Referencia oficial del comando Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).

Serve fue activado con autorización del usuario el 24/10/2026. Salud, HTML del
panel y OpenAPI respondieron HTTP 200 por HTTPS con validación TLS normal.
No se ejecutaron solicitudes de documentos en esa verificación.
Evidencia: `evidencias/edil-s4-tailscale-24-octubre.json`.

URLs de la presentación:

| Uso | URL |
| --- | --- |
| Web de auditoría | `https://desktop-2amsjb6.tailf48a22.ts.net/web/auditoria/index.html` |
| Historial web | `https://desktop-2amsjb6.tailf48a22.ts.net/web/historial/index.html` |
| API base para Flutter | `https://desktop-2amsjb6.tailf48a22.ts.net` |
| Swagger | `https://desktop-2amsjb6.tailf48a22.ts.net/docs` |

La PC debe seguir encendida y conectada durante la presentación. No se activa Funnel, no se publica en internet abierto y no se modifica el router. Compartir el puerto incluye la API: usar exclusivamente datos sintéticos y dispositivos de confianza conforme a las reglas de la tailnet. La red privada no convierte `reviewer_id` en una identidad autenticada ni sustituye permisos de la aplicación.

Para finalizar el proxy de este puerto, preservando otros posibles servicios:

```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve --https=443 off
```

Detener el servidor local con Ctrl+C en la terminal que lo inició. No usar `serve reset` para limpiar otros servicios.

## 3. APK de presentación

Compilación reproducible desde la carpeta Flutter:

```powershell
.\tool\build_edil_apk.ps1 -Target Tailnet -ApiBaseUrl 'https://desktop-2amsjb6.tailf48a22.ts.net'
```

Artefacto: `mediflow/frontend_mobile/mediflow_app/build/edil-s4/mediflow-s4-tailnet.apk`. Es un **APK debug para presentación**, no una distribución de tienda. El teléfono debe estar conectado a la tailnet. No contiene claves OCI/Gemini; el backend conserva las credenciales en la PC.

Se conserva también una alternativa USB para pruebas sin Tailscale:

```powershell
.\tool\build_edil_apk.ps1 -Target Usb
# Con el teléfono autorizado por USB y el backend habitual en 127.0.0.1:8000:
adb reverse tcp:8000 tcp:8000
adb install -r build/edil-s4/mediflow-s4-usb.apk
```

Si se usa únicamente el servidor de presentación del BAT en el puerto 8787,
la alternativa USB es `adb reverse tcp:8000 tcp:8787`: el teléfono mantiene su
URL `127.0.0.1:8000` y ADB la conecta al puerto 8787 de la PC.

La compilación y verificación de firma no equivalen a pruebas físicas. El usuario indicó que las realizará después. La versión Release exige HTTPS real y una firma de distribución propia; el proyecto mantiene firma debug en release y el helper se niega a presentarla como distribución final.

## 4. Guion breve

1. Comprobar Tailscale conectado en PC/teléfono y abrir salud/Swagger por HTTPS.
2. Abrir el panel y el historial. Mostrar que vienen del backend y distinguir estado del análisis de revisión humana.
3. En Flutter seleccionar TXT/PDF/imagen sintéticos o capturar una receta ficticia. Revisar y confirmar la foto; comprobar consentimiento por archivo.
4. Enviar una sola vez; mostrar recepción o resultado real según lo que responda la API. Actualizar por ID, sin nuevo POST.
5. Mostrar Urgente y revisión humana como dimensiones independientes. No presentar confianza de clasificación como seguridad clínica.
6. Aprobar/rechazar solo si el equipo aprobó y habilitó el contrato; comprobar historial persistido y exclusión de pendientes. Si sigue bloqueado, explicarlo y usar la demostración sintética local claramente rotulada.
7. Probar una desconexión controlada y recuperación sin duplicar envíos. Registrar capturas y resultado, sin datos ni claves reales.

## Dependencias

- Equipo: aprobación del contrato de decisiones; autenticación/permisos para la exposición prevista.
- Eliana/backend: decidir y completar `cargado_por` si sigue siendo obligatorio.
- Usuario: autorizar el acceso privado, completar cualquier consentimiento de HTTPS y probar teléfono/cámara/conectividad.
- Infraestructura: disponibilidad de OCI/Gemini y permisos para pruebas reales; Tailscale no los sustituye.

No se hicieron commits ni push. El estado de activación efectivo se registra en `S4-Edil.md` y sus evidencias; esta guía por sí sola no demuestra que Serve esté activo.
