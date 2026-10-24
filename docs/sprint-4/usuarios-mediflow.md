# Usuarios propios de MediFlow — 24/10/2026

Agregado por Edil. El usuario aclaró que Tailscale se utilizará exclusivamente
para acceder al servicio local desde otros equipos y autorizó un inicio de
sesión propio con usuario y contraseña.

## Separación de responsabilidades

- **Tailscale:** conexión privada y HTTPS hacia la PC que ejecuta el servicio.
- **MediFlow:** usuario, contraseña, sesión y permiso para aprobar o rechazar.
- **OCI/Gemini:** credenciales del backend, independientes de las cuentas humanas.

No se necesitan correos ni cuentas de Tailscale para definir auditores dentro
de la aplicación. Los headers de identidad de Tailscale ya no crean usuarios,
sesiones ni permisos. El proveedor anterior se conserva como referencia
inactiva; no está conectado al servidor de presentación.

El contrato de revisión conserva los cuatro campos de solicitud y seis de
persistencia. `reviewer_id` proviene de la sesión de MediFlow y debe coincidir
con la identidad verificada por el backend. `cargado_por` toma el usuario de
aplicación que cargó el archivo; las cargas sin sesión y los JSON históricos
mantienen null. No se cambió Flutter ni se agregó un login móvil en esta fase.

## Primera cuenta, en el equipo del despliegue

No se creó ninguna cuenta real ni contraseña predeterminada en esta PC. La
persona responsable establece la contraseña directamente en su terminal local.
Desde la carpeta `mediflow/backend` de la copia del proyecto en el equipo nuevo:

```powershell
.\.venv\Scripts\python.exe -m app.auth.manage add-auditor edil
```

El comando pide y confirma una contraseña de al menos 12 caracteres sin
mostrarla. No pasar contraseñas como argumentos ni pegarlas en el chat. El
usuario `edil` es una cuenta de MediFlow, no una cuenta Google, OCI o Tailscale.
Una cuenta existente no se sobrescribe al ejecutar nuevamente add-auditor.

Para agregar otros integrantes posteriormente:

```powershell
.\.venv\Scripts\python.exe -m app.auth.manage add-auditor otro_auditor
.\.venv\Scripts\python.exe -m app.auth.manage add-user usuario_sin_permiso_de_revision
```

Administración local:

```powershell
.\.venv\Scripts\python.exe -m app.auth.manage reset-password edil
.\.venv\Scripts\python.exe -m app.auth.manage disable-user otro_auditor
```

Cambiar la contraseña o deshabilitar una cuenta revoca sus sesiones. No hay
registro público de cuentas ni una API pública para concederse permiso de auditor.

## Configuración del equipo servidor

`mediflow/.env` continúa siendo el archivo de configuración local. El equipo
nuevo debe establecer su propio origen HTTPS, sin ruta ni barra final:

```dotenv
MEDIFLOW_PUBLIC_ORIGIN=https://NOMBRE-DEL-EQUIPO.SU-TAILNET.ts.net
# Opcional; vacío usa mediflow/.local/auth.sqlite3.
MEDIFLOW_AUTH_DB_FILE=
# Opcional; por defecto ocho horas. Rango permitido: 900 a 43200 segundos.
MEDIFLOW_SESSION_TTL_SECONDS=28800
```

`MEDIFLOW_AUTH_MODE` y `MEDIFLOW_REVIEWER_LOGINS` pertenecen a la implementación
anterior y ya no definen cuentas ni permisos. El modo anterior se dejó disabled
en la configuración local, conservando el origen HTTPS.

Los usuarios y sesiones viven en `mediflow/.local/auth.sqlite3`, excluido de Git.
Se almacenan hashes scrypt con sal para contraseñas y hashes SHA-256 para tokens
aleatorios de sesión. La base no contiene documentos clínicos. No copiarla al
directorio público de la web ni publicarla en Git; el código rechaza esa ubicación.
Cada equipo puede crear sus propias cuentas con el comando de administración.

## Acceso y cierre de sesión

Después de iniciar el servidor de presentación y conectar Serve al puerto local,
abrir en el navegador:

```text
https://SU-ORIGEN-HTTPS/web/login/index.html
```

Ingresar con la cuenta de MediFlow y su contraseña. El panel muestra el usuario
como solo lectura y ofrece cierre de sesión con confirmación. Los usuarios sin
permiso de auditor pueden tener sesión, pero no aprobar o rechazar documentos.
El backend reconsulta el estado y permiso de la cuenta en cada petición.

La sesión usa cookie HttpOnly, SameSite=Strict y Secure en HTTPS, sin tokens ni
contraseñas en localStorage/sessionStorage. En desarrollo se permite HTTP solo
en loopback. Login, logout y decisiones verifican el origen de la aplicación.
El inicio de sesión limita intentos fallidos por cuenta y dirección de conexión;
como el proxy local comparte una dirección, ese límite puede afectar a varios
usuarios simultáneamente. No se confía en X-Forwarded-For libre para evadirlo.

APIs implementadas:

- `POST /api/auth/login`: usuario/contraseña; crea una sesión propia.
- `GET /api/auth/session`: devuelve identidad y permiso, sin contraseña ni token.
- `POST /api/auth/logout`: revoca sesión y elimina cookie; responde 204.

La protección se aplica a las decisiones de revisión. Se conserva el acceso y
comportamiento de los endpoints de documentos y carga existentes; la red privada
sigue delimitando quién puede acceder al despliegue. Esta entrega no cambia los
contratos de triaje ni crea autenticación obligatoria para Flutter.

## Estado de entrega

La pantalla y el backend están implementados. La primera cuenta y su contraseña
quedan para el equipo del despliegue, como indicó el usuario. Las pruebas usan
únicamente cuentas sintéticas y bases temporales; no consumen OCI ni Gemini.
La aceptación de decisiones con OCI real continúa pendiente y se describe en
[aceptacion-revision-real.md](aceptacion-revision-real.md), utilizando ahora
usuarios de MediFlow en lugar de identidades de la red.

Verificación local del 24/10: **532 pruebas Python y 29 subcasos aprobados**,
seis pruebas externas excluidas; **185 pruebas JavaScript aprobadas**. Se
verificaron visualmente inicio de sesión, usuario mostrado en el panel y cierre
de sesión con una cuenta sintética y almacenamiento de documentos en memoria.
No se enviaron datos a OCI ni Gemini. Capturas y resultados en
`evidencias/mediflow-login-propio-24-octubre.json`.
