# Integración local Sprint 4 — 23 de octubre de 2026

Agregado por Edil: combinar las entregas disponibles con el panel web local antes de publicar en main. Este informe distingue preparación de código, historia Git y pruebas con proveedores reales.

## Rama, base y preservación

- Raíz: `D:\Nocountru`; aplicación: `D:\Nocountru\mediflow`.
- Rama creada: `integration/sprint-4-2026-10-23`.
- Base, HEAD y main conservados: `b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e`.
- Antes de integrar había 12 archivos locales pendientes: cuatro rastreados modificados y ocho sin seguimiento. Se copiaron todos y se verificó SHA-256 antes de tocar Git.
- Respaldo completo: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-integracion-23oct-hsu1ebze`, con archivos originales, parches binarios, índice, manifiesto y hashes de las ramas recibidas. No borrarlo antes del cierre.
- Se conservaron los dos stashes, los respaldos y el worktree histórico. No se descartaron cambios locales.

## Entregas incorporadas a los archivos de la nueva rama

| Rama remota | Commit de referencia | Incorporación |
| --- | --- | --- |
| `feature/s4-brando-oci-review` | `5e8f503` | Persistencia y verificación de registros OCI, control condicional de duplicados y pruebas |
| `feature/s4-drazen-review-api` | `d286de4` | Incluye ya a Brando; tres endpoints HTTP, esquemas, errores y pruebas |
| `feature/s4-eliana-integracion` | `2470587` | Contrato y matriz, documentación/ejemplo `cargado_por`, validaciones compatibles |
| `feature/s4-laura-confianza` | `820a7da` | Documentación y pruebas de los perfiles existentes; sin sustituir fórmula ni umbral |
| Cambios locales de Edil | Respaldo previo de 12 archivos | Panel web preparado, pruebas, documentación; nuevo adaptador contra las rutas entregadas |

No se fusionó Brando dos veces: es ancestro de la rama de Drazen. Sus fuentes y pruebas quedan incluidas una sola vez.

Para respetar la restricción de no crear commits, se preparó la rama de Drazen mediante `merge --squash --no-commit` y se aplicaron los diffs de Eliana/Laura mediante tres vías, resolviendo conflictos. **No hay commits nuevos ni un merge de historia confirmado**: HEAD continúa en la base. Un futuro commit consolidado registrará el árbol preparado; los commits originales siguen en sus ramas y sus hashes completos están en `integracion-23-octubre.json`. No afirmar que las cuatro ramas ya son ancestros de main.

## Conflictos resueltos y criterios

1. **`backend/app/api/routes.py`:** conservar los tres endpoints reales de Drazen conectados a `OCIStorageManager` de Brando. Eliana incluía `/api/auditoria/revision` como simulación, con mensaje de éxito sin escritura y campos ajenos a la solicitud definitiva. Ese código se conservó comentado como referencia con explicación «Agregado por Edil»; no queda registrado como endpoint. Una regresión comprueba que no aparece en rutas públicas.
2. **`backend/app/models/schemas.py`:** conservar solicitud/respuesta de Drazen y las validaciones de Eliana. `expected_review_status` es obligatorio y vale `pendiente`; los campos adicionales de solicitud/registro se rechazan. El registro tiene seis campos, incluida observación explícita, que puede ser null al aprobar. Se conserva datetime con UTC validado y se exige sufijo Z para fechas recibidas como texto, evitando la unión `datetime | str` sin validar. Se agregaron pruebas para estas decisiones de compatibilidad.
3. **Panel preparado vs API disponible:** se agregó `review-http-adapter.js` para pendientes, decisión e historial reales, traduciendo los seis campos públicos a la interfaz interna de la vista. El POST envía exactamente `decision`, `reviewer_id`, `observacion`, `expected_review_status`; no agrega datos clínicos, prioridad ni identidad ficticia.
4. **Identificación:** el panel solicita `reviewer_id` explícito y exige observación al rechazar. El campo no acredita identidad; la autenticación/autorización del backend sigue pendiente. No se usa el médico del documento como auditor ni el valor de ejemplo `cargado_por` como identidad real.
5. **Aprobación del contrato:** integrar una implementación no sustituye la decisión del equipo. Por la última indicación recibida, las lecturas quedan conectadas y el POST deshabilitado por defecto. Después de aprobarlo podrá definirse `window.MEDIFLOW_REVIEW_CONTRACT_APPROVED = true` en la configuración de despliegue, antes de cargar el adaptador. No hay activación mediante query string. Las pruebas habilitan el POST solo en su fixture sintético local. El flag de frontend no es una medida de autorización del servidor.

Los bloques previos de la maqueta de auditoría permanecen conservados e inertes; sus firmas, niveles MTS y decisiones en memoria no se ejecutan.

## Verificación ejecutada

| Área | Resultado final |
| --- | --- |
| Backend + data_ai | **473 pruebas y 29 subcasos aprobados**; 6 pruebas de integración externa excluidas |
| Web | **141 pruebas aprobadas**, sin fallos ni omitidas |
| Sintaxis JavaScript | **6 comprobaciones aprobadas** |
| Flutter test | **178 aprobadas**, 2 pruebas reales opt-in omitidas |
| Flutter analyze | **Sin problemas**, código de salida 0 |

Se observaron dos advertencias de dependencias Python (google-genai y Starlette/httpx), sin fallos. No se actualizaron dependencias ni reglas clínicas.

La nueva prueba HTTP ejecuta el cliente JavaScript → FastAPI real → gestor de persistencia real de Brando → sustituto del SDK en memoria. Verifica aprobación, rechazo, historial, exclusión de pendientes, segunda decisión HTTP 409, solicitud inválida HTTP 422, ausencia del endpoint simulado y conservación íntegra del JSON/urgencia original. El servidor de prueba usa puerto local temporal, documentos sintéticos y se termina al cerrar la prueba.

**Esto no es una prueba contra OCI real.** No se enviaron documentos a OCI/Gemini ni se activaron las pruebas reales. Los informes de los compañeros que citan pruebas anteriores permanecen como evidencia histórica, no como ejecuciones repetidas en esta integración. Tampoco se afirma verificación visual nueva de escritorio/móvil o de APK/dispositivo físico.

Registros finales, fuera del repositorio:

- Backend: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-integracion-backend-verificado-_vpfcqq8\tests.log`.
- Web: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-integracion-web-final-u9c7_pq8\tests.log`.
- Flutter: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-integracion-flutter-49bf0041f6be4f9ca7901f1f212c589a\analyze.log` y `tests.log`.

Reproducción local sin proveedores:

```powershell
# Desde mediflow/backend, con las integraciones reales desactivadas:
$env:RUN_OCI_INTEGRATION = '0'
$env:OCI_RUN_INTEGRATION = '0'
.\.venv\Scripts\python.exe -m pytest tests ..\data_ai -m 'not integration' -q -p no:cacheprovider --basetemp <directorio-temporal-nuevo>
# Desde mediflow/frontend_web; requiere el Python del backend para su fixture HTTP:
node --test tests/*.test.js
# Desde mediflow/frontend_mobile/mediflow_app:
flutter analyze --no-pub
flutter test --no-pub --reporter expanded
```

## Seguridad y revisión final

No se detectaron claves privadas, valores secretos locales, tokens ni `.env` entre los archivos que se preparan. No se incluyen .pem/.key ni credenciales. Se conservan las reglas de .gitignore y la configuración OCI existente de tres buckets. Sin entradas Git sin fusionar ni marcadores de conflicto; JSON y sintaxis Python verificados.

Los únicos avisos de espacios finales conservados son saltos de línea Markdown de los informes originales `S4-Brando.md` y `S4-Drazen.md`; no son conflictos ni cambios de código. Se normalizaron los finales vacíos de dos archivos Python. La comprobación de espacios del código y demás archivos pasa, exceptuando esos dos documentos intencionadamente.

El manifiesto `integracion-23-octubre.json` enumera exactamente los archivos a incorporar y conserva los hashes de entrada finales. El informe `preparacion-base.md` anterior no se reescribió.

## Pendientes antes de publicar main

1. **`cargado_por`:** Eliana lo agregó al ejemplo JSON y lo documentó como obligatorio, pero su rama no incorpora el campo al modelo `TriageResponse` ni al formulario POST ni a los clientes. Se conserva la entrega y se identifica la inconsistencia; no se inventa un profesional ni se rompe la carga antigua exigiendo un dato inexistente. Si es obligatorio para el cierre, acordar procedencia, compatibilidad y propagación a persistencia/lecturas antes de declararlo implementado.
2. Confirmar aprobación/habilitación del contrato de decisiones. La API está integrada y probada localmente; su autorización de uso no se presume por existir una rama.
3. Autenticación y permisos: `reviewer_id` llega del cliente y no demuestra quién es la persona. Antes de exposición pública deben resolverse autorización y CORS para el entorno final.
4. Verificar integración contra OCI real, únicamente con autorización, datos sintéticos y configuración adecuada. La copia del registro final y su espejo no es una transacción atómica; mantener tratamiento conservador de respuestas inciertas y pruebas de recuperación.
5. Verificación visual en escritorio/móvil, cámara/APK y demostración final. El pipeline de demo de urgencia mantiene su alcance sintético; las pruebas no son validación clínica.

## Estado preparado y siguiente paso

Rama de integración con los archivos preparados para revisión, sin commits nuevos y sin push. Main continúa en la base original; no se publicó nada ni se eliminaron ramas.

Después de revisar/aprobar el manifiesto, la propuesta es un commit local consolidado para mantener dependencias y esquema compatibles en el mismo árbol. Estos comandos son **solo una propuesta** y requieren autorización; no se ejecutaron:

```powershell
git status -sb
git diff --cached --stat
git commit -m "feat(sprint4): integrar API y persistencia de auditoria con panel web"
# Solo tras autorización expresa para publicar la rama de integración:
git push -u origin integration/sprint-4-2026-10-23
```

No se propone push directo a main ni force push. La subida/fusión a main corresponde a una decisión posterior, una vez revisados los pendientes y el commit consolidado.
