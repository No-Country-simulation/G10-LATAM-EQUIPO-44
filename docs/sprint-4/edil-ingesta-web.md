# Ingesta web conectada al backend

Agregado por Edil: el formulario de archivos utiliza el endpoint existente; no cambia el contrato, el detector de urgencias ni las decisiones de revisión.

## Uso

1. Abre `https://desktop-edilanti.tailf48a22.ts.net:10000/ingesta/index.html` (si el servidor publica `src/` como raíz).
2. En **Subir y analizar documento**, selecciona un PDF, JPG, JPEG, PNG o TXT, no vacío y de hasta 10 MiB.
3. Lee y marca el consentimiento de envío, almacenamiento en OCI y análisis con Gemini.
4. Pulsa **Enviar y analizar** una sola vez. Espera el resultado; la operación puede durar hasta tres minutos antes del timeout del navegador.
5. Se muestran el ID, estado y, cuando existe análisis, tipo, prioridad orientativa, confianza de clasificación y necesidad de revisión humana. Una recepción pendiente no se presenta como análisis completado.
6. **Consultar recepción** ejecuta GET individual cuando se conoce el ID. Una consulta fallida conserva el resultado previo. También puedes abrir **Ver historial**.
7. Usa **Nueva carga** para otro documento. Si hubo una solicitud anterior, se exige confirmar que revisaste el historial para evitar duplicados.

La fila muestra nombre y ojo. El ojo abre el original almacenado en OCI mediante `GET /api/documents/{id}/original`, no un archivo local. Requiere sesión de MediFlow: autor autenticado o auditor. Las cargas anónimas solo pueden ser abiertas por un auditor. No se publican URLs de OCI ni se envían claves al navegador. Si no se conoce el ID, el ojo no se ofrece: consulta el historial o recupera la recepción. Tras recargar, el enlace sigue disponible si se guardó el ID.

El formulario MTS original sigue disponible en una sección de demostración plegada: sus controles no guardan ingresos reales ni forman parte de la carga de documentos.

## Configuración y transporte

La única selección de servidor sigue en `mediflow/frontend_web/src/assets/js/api-config.js`: localhost/127.0.0.1 usan `http://127.0.0.1:8001`; el despliegue público usa `https://desktop-edilanti.tailf48a22.ts.net:8443`.

El nuevo cliente envía exactamente `POST /api/triage` con multipart `file` y `analyze=true`. No añade un segundo `/api`. El navegador genera Content-Type y su boundary. Envía `credentials: include` para conservar la sesión existente, sin leer cookies HttpOnly, claves ni tokens.

El backend desplegado debe permitir CORS con credenciales desde el origen web `https://desktop-edilanti.tailf48a22.ts.net:10000` y exponer `X-Document-ID` (ya declarado en el backend inspeccionado). La autenticación existente y sus restricciones de origen se conservan; este cambio no implementa ni sustituye el login. El backend actual permite cargas sin identidad y entonces `cargado_por` permanece null.

## Fallos y duplicados

No hay reintentos automáticos ni sustitución por mocks. Un fallo de red, timeout, 5xx o cuota puede ocurrir después de que OCI haya recibido el archivo: se bloquea el reenvío y se invita a consultar el historial. Cuando el backend devuelve `X-Document-ID`, se habilita la recuperación mediante GET, sin volver a subir el archivo.

En sessionStorage se guarda el bloqueo, ID y metadatos locales (nombre y tamaño), nunca los bytes del archivo, texto clínico ni resultado. Un nombre puede contener información personal: evita nombres sensibles en archivos de demostración. El bloqueo se conserva al recargar esa pestaña si el almacenamiento está disponible. Si el navegador lo bloquea, la protección dura hasta cerrar/recargar la página. No hay garantía de idempotencia entre pestañas/equipos: el backend no ofrece una clave de idempotencia en el contrato actual. Nueva carga es una salida manual confirmada, no una comprobación del servidor.

## Verificación

Desde `mediflow/frontend_web`: `node --test tests/*.test.js`.

Resultado local de esta entrega: **221 pruebas aprobadas, 0 fallidas**, incluidas 25 pruebas nuevas de ingesta. Las pruebas HTTP locales utilizan servicios sintéticos; no prueban conectividad con el Funnel público ni consumen OCI/Gemini. También pasaron la comprobación de sintaxis de los dos módulos nuevos y `git diff --check`. Se actualizó una expectativa antigua de autenticación de `same-origin` a `include`, conforme al cliente que ya existía, sin cambiar el login.

Pruebas nuevas: URL pública/local, multipart, consentimiento, tipos/tamaño/vacío, errores HTTP, timeout/red, respuesta inválida, doble envío, recuperación y conservación de resultado, bloqueo tras recarga y texto de IA mostrado sin interpretar HTML. Las respuestas simuladas existen únicamente en pruebas.

La prueba real con OCI/Gemini debe hacerse en el equipo desplegado con un documento sintético autorizado. En Network verifica `POST https://desktop-edilanti.tailf48a22.ts.net:8443/api/triage`, multipart `analyze=true` y HTTP 201; luego GET individual y aparición en historial/auditoría según el resultado. Un 429/5xx no debe mostrarse como éxito. No se ejecutan llamadas externas como parte de las pruebas automatizadas.


## Corrección de timeout de fotos

Gemini usaba 30 s por defecto; ahora usa 120 s, configurable con `GEMINI_TIMEOUT_SECONDS`. El SDK recibe 120000 ms y mantiene un solo intento. Flutter pasa de 90 a 180 s; la web ya esperaba 180 s. Se conserva el formato multimedia nativo y no se cambia el modelo, cuota ni reglas clínicas. Esto corrige los límites demasiado cortos, pero no garantiza disponibilidad o latencia de Gemini. Referencia del SDK: https://googleapis.github.io/python-genai/.

Reinicia el backend para cargar el `.env`. Si ejecutas el servidor en otro equipo, establece allí `GEMINI_TIMEOUT_SECONDS=120` en `mediflow/.env` (las variables exportadas siguen teniendo prioridad). El APK instalado conserva 90 s hasta recompilar y reinstalar con la URL de backend correcta. No se ha ejecutado una prueba real de fotos ni se ha recompilado un APK en esta corrección.

La ruta nueva del original no altera el JSON de triage ni hace nuevas llamadas a Gemini. Lee como máximo 10 MiB del bucket y objeto registrados en el JSON validado, comprueba acceso, envía tipo MIME permitido y cabeceras no-store/nosniff/sandbox. Un usuario sin sesión recibe 401; otra cuenta sin permiso recibe 403. El login web acepta puertos HTTPS distintos del mismo host de Funnel y sigue rechazando otro host/protocolo.

Verificación final de esta corrección: backend/data_ai **704 pruebas + 29 subcasos aprobados**, 6 pruebas externas excluidas; web **221 aprobadas**; Flutter **187 aprobadas y 2 omitidas**; `flutter analyze` sin incidencias. Las dependencias Python emiten dos advertencias de deprecación existentes. El backend permite CORS con credenciales desde localhost/127.0.0.1:10000, además del origen HTTPS público existente. Para login configura `MEDIFLOW_PUBLIC_ORIGIN` con el origen de la web que uses, no con el de la API. No se realizaron llamadas reales a Gemini u OCI, commits ni push.
