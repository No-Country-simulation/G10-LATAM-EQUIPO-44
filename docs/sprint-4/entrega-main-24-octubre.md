# Paquete Sprint 4 para main — 24/10/2026

Agregado por Edil. Paquete consolidado preparado desde
`integration/sprint-4-2026-10-23`, sobre
`b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e`. La referencia remota se actualizó
con fetch y `origin/main` coincide con esa base. Este informe prepara la
publicación: no equivale a haber hecho commit, merge o push.

## Contenido y procedencia

Se incluyen los cambios de las ramas disponibles de Brando (`5e8f503`),
Drazen (`d286de4`, que ya incluye el trabajo de Brando), Eliana (`2470587`)
y Laura (`820a7da`), junto con las correcciones locales de integración y el
frontend/documentación de Edil. Se conservan los informes originales y las
decisiones de conflictos. La referencia disponible de Nicolás para Sprint 4
apunta a la misma base; no se atribuyen cambios nuevos inexistentes.

El árbol preparado contiene API de revisión, persistencia OCI final/espejo,
panel de auditoría real, historial, protección de envíos inciertos, `cargado_por`
y cuentas propias de MediFlow. Tailscale aporta acceso privado/HTTPS; no autentica
usuarios de la aplicación. No se modificó la lógica Dart de Flutter en este cierre:
se incorporan su documentación y el helper de compilación de APK.

El manifiesto vigente es `paquete-main-24-octubre.json`. El manifiesto del 23/10
de 36 archivos se conserva únicamente como registro histórico; no describe el
paquete completo actual. Los informes históricos pueden citar números y estados
anteriores. Para usuarios, usar [usuarios-mediflow.md](usuarios-mediflow.md).

## Exclusiones verificadas

- `.env` y configuraciones locales de OCI.
- Claves privadas, PEM, KEY, tokens reales y contraseñas.
- Base SQLite de usuarios, sesiones y archivos auxiliares.
- Entornos virtuales, dependencias descargadas y cachés.
- APK compilados, logs, temporales, respaldos y patches de trabajo.

Se incluye `mediflow/.env.example` con valores de ejemplo y campos secretos
vacíos. Las contraseñas literales de las pruebas pertenecen exclusivamente a
cuentas sintéticas en bases temporales; no son credenciales del despliegue.
No se creó ninguna cuenta real ni una contraseña predeterminada.

## Verificación disponible

- Backend/data_ai/presentación: **532 pruebas y 29 subcasos aprobados**;
  seis pruebas externas excluidas y dos avisos de dependencias.
- Web: **185 pruebas aprobadas**, sin fallos ni omitidas.
- Flutter: última verificación disponible, **178 pruebas aprobadas**, dos
  externas omitidas y analyze sin problemas; sin cambios posteriores de lógica Dart.
- Login y logout comprobados visualmente con cuenta sintética, SQLite temporal
  y almacenamiento de documentos en memoria.
- Sin llamadas OCI/Gemini en la verificación de esta entrega.
- Los PDF y `.gitattributes` conservan el contenido de la base.

Los registros y capturas están referenciados en
`evidencias/mediflow-login-propio-24-octubre.json`. Las pruebas reales y la
aceptación en Android quedan para el equipo del despliegue por indicación del
usuario; no se presentan como ejecutadas. Los criterios documentales de Laura
mantienen su aprobación funcional pendiente y el perfil de urgencia de demo
conserva su alcance sintético.

## Recuperación en el otro equipo, después de publicar

Desde una copia limpia del mismo repositorio:

```powershell
git status -sb
# Si hay cambios propios, preservarlos antes de actualizar.
git fetch origin
git switch main
git pull --ff-only origin main
```

El pull solo podrá obtener este paquete cuando el commit esté publicado en
`origin/main`. No copiar el `.env`, la base de usuarios ni las credenciales de
esta PC por Git.

Con Python, Node, Flutter y Android SDK disponibles según el componente que se
quiera ejecutar, preparar el backend desde la raíz del repositorio:

```powershell
python -m venv mediflow\backend\.venv
.\mediflow\backend\.venv\Scripts\python.exe -m pip install -r mediflow\requirements.txt
if (-not (Test-Path -LiteralPath mediflow\.env)) {
    Copy-Item -LiteralPath mediflow\.env.example -Destination mediflow\.env
}
```

Copiar el ejemplo solo si no existe ya un `.env` local. Completarlo en ese
equipo con su configuración OCI y Gemini. Se conservan `OCI_CONFIG_PROFILE`
y los buckets `recibidos`, `procesados`, `auditoria_humana`. Ajustar
`MEDIFLOW_PUBLIC_ORIGIN` al origen HTTPS del equipo servidor nuevo.

Crear allí la primera cuenta de aplicación:

```powershell
Push-Location mediflow\backend
.\.venv\Scripts\python.exe -m app.auth.manage add-auditor edil
Pop-Location
.\iniciar_presentacion_local.bat
```

El comando pide y confirma la contraseña ocultándola. Configurar el acceso
privado de Tailscale Serve para ese equipo siguiendo
[presentacion-local-tailscale.md](presentacion-local-tailscale.md). Abrir
`https://SU-ORIGEN/web/login/index.html`.

Si cambia el origen del backend, compilar Flutter con el nuevo `API_BASE_URL`.
Los APK locales anteriores apuntan a esta PC y no se incluyen en el paquete.

## Paso Git pendiente

El paquete se prepara en el índice de la rama de integración. La propuesta es
un commit consolidado, después avanzar main mediante fast-forward si el remoto
sigue en la base y publicar sin force push. Antes de publicar se debe volver a
comprobar que el remoto no avanzó. Si avanzó, incorporar y verificar esos cambios
sin sobrescribirlos.

Commit propuesto: `feat(sprint4): consolidar auditoria humana y usuarios propios`.
La creación del commit y el push requieren la autorización del usuario; no se
ejecutan por aparecer como propuesta en este informe.
