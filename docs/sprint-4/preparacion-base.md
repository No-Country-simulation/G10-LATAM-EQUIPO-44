# S4-07 Fase 1 — Preparación de la base

Fecha de revisión: 17 de octubre de 2026, America/La_Paz.

Agregado por Edil: este informe verifica la versión existente antes de comenzar Sprint 4. No introduce funcionalidades, contratos, reglas clínicas ni nuevas llamadas a proveedores externos.

## Resultado

Sprint 3 ya está consolidado en la copia revisada y es una base técnica apta para iniciar Sprint 4. No quedan cambios de módulos del Sprint 3 pendientes de commit. Esta conclusión corresponde a inspección y pruebas locales; no equivale a validación clínica ni a una nueva verificación en OCI/Gemini.

| Dato | Valor verificado |
| --- | --- |
| Raíz Git real | `D:\Nocountru` |
| Directorio de aplicación | `D:\Nocountru\mediflow` |
| Rama activa, conservada | `main` |
| HEAD y main local | `b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e` |
| Referencia local origin/main | El mismo commit; divergencia `0 / 0` |
| Estado antes de la revisión | Limpio; sin archivos modificados, preparados ni sin seguimiento |
| Cambio generado por esta fase | Únicamente `docs/sprint-4/preparacion-base.md`, sin preparar |

No se hizo fetch ni se consultó GitHub durante esta fase; la comparación con origin/main usa la referencia local existente. Una actualización remota posterior deberá revisarse antes de publicar. No se modificaron ramas, commits, remotos ni el área preparada.

## Comprobación de entregas

La asignación siguiente describe responsabilidad funcional; no atribuye toda la autoría de archivos compartidos a una persona.

| Responsable | Código y evidencia presentes | Límite que se conserva |
| --- | --- | --- |
| Nicolás | `mediflow/data_ai/synthetic_demo_rules.py`, `backend/app/services/triage_pipeline.py`, pruebas `test_synthetic_demo_urgency.py` y `test_document_source_evidence.py`; el orquestador invoca el detector y la política de demo | Las cuatro reglas experimentales del dataset se habilitan solo con `synthetic_demo_v1`. No convertirlas en reglas clínicas generales |
| Laura | `mediflow/data_ai/confidence_profiles.py`, `rules/confidence_profiles_mvp.json`, `backend/tests/test_confidence_profiles.py`; seis perfiles y selección desde el orquestador | Criterios provisionales; fórmula y umbral 0.70 conservados. No afirmar que confianza equivale a exactitud o seguridad clínica |
| Drazen | `backend/app/api/routes.py`: POST `/api/triage`, GET `/api/documents` y GET `/api/documents/{document_id}`; `core/oci_client.py` para persistencia/recuperación; `tests/test_documents_api.py` | Las lecturas reales de buckets no se ejecutaron en esta fase |
| Brando | `backend/app/core/oci_transfer.py`: copia nativa, espera, lectura y comparación SHA-256; protección por ETag y pruebas de transferencia | Persistir el JSON y copiar el documento no constituyen una transacción atómica |
| Eliana | `backend/app/core/orquestador.py`, pipeline y `backend/tests/test_eliana_integration.py`; informes y trazas de escenarios anteriores | Se conserva prioridad Urgente y cualquier solicitud previa de revisión humana. Las evidencias reales anteriores no son una nueva ejecución |
| Flor | `frontend_web/src/historial/app.js`, `assets/js/documents-api.js`, `document-detail.js` y sus pruebas | Historial/detalle conectados a GET; el panel de auditoría con aprobación/rechazo persistente aún no está integrado |
| Edil | `frontend_mobile/mediflow_app/lib/`: selección, consentimiento, cámara, servicio HTTP, resultado y recuperación `getDocument`; suites de flujo, cámara y recuperación | Dispositivo físico, APK y conectividad real requieren comprobación posterior |

Los seis tipos configurados son: Receta Médica, Informe de Laboratorio, Informe de Estudio por Imágenes, Orden / Solicitud de Procedimiento, Epicrisis / Informe de Alta y Certificado Médico. No se modificó el catálogo ni el contrato JSON.

## Revisión de archivos, seguridad y conflictos

- Se inspeccionaron los 284 archivos rastreados. No se detectaron nombres sensibles rastreados ni patrones de claves privadas, claves de API Google o tokens GitHub. También se compararon en memoria los valores secretos locales configurados, sin imprimirlos: no hubo coincidencias en archivos rastreados.
- `mediflow/.env` existe localmente, está ignorado y no está rastreado. Tampoco está rastreado `mediflow/backend/.env`. `.gitignore` protege `.env`, `*.pem`, `*.key` y `.oci/`. Los archivos `.env.example` no son secretos ni se excluyen por ser ejemplos.
- No se detectaron archivos temporales nuevos ni archivos sin seguimiento al iniciar. Las cachés locales no forman parte del paquete. La caché ignorada `backend/.pytest_cache` no pudo listarse por permisos; no se eliminó ni se utilizó, y pytest se ejecutó sin su proveedor de caché.
- Sin entradas sin fusionar ni marcadores de conflicto en los archivos rastreados. `git diff --check` y `git diff --cached --check` aprobaron.
- Los seis PDF del dataset coinciden byte por byte con HEAD y admiten lectura estricta. `.gitattributes` conserva `*.pdf -text`.
- Las evidencias ya versionadas del cierre anterior se conservan como históricas. La captura de Flor corresponde al caso sintético MF_004 autorizado; contiene datos sintéticos de apariencia clínica y debe seguir identificándose como tal. Los JSON contienen identificadores, hashes y rutas técnicas, no claves. Los parches históricos son referencias: no aplicarlos otra vez. El parche de Flor conserva sus dos espacios finales originales.
- No se eliminaron respaldos, worktrees, archivos originales ni entregas. No se alteraron backend, data_ai, web o Flutter durante esta fase.

La búsqueda de patrones y valores conocidos reduce el riesgo de publicar secretos; no demuestra la ausencia universal de información sensible. Repetir la revisión ante cualquier cambio posterior.

## Pruebas ejecutadas en esta fase

| Área | Resultado |
| --- | --- |
| Backend + data_ai | **363 pruebas y 21 subcasos aprobados**; 5 pruebas de integración excluidas |
| Web | **40 pruebas aprobadas**, sin fallos ni omitidas |
| Sintaxis JavaScript | **3 comprobaciones aprobadas** |
| Flutter test | **178 pruebas aprobadas**, 2 pruebas HTTP reales opt-in omitidas |
| Flutter analyze | **Sin problemas**, salida 0 |

Backend mostró dos avisos de dependencias: deprecación interna de google-genai con Python y compatibilidad futura Starlette/httpx. No causaron fallos; no se actualizaron dependencias como parte de esta fase.

Comandos usados desde los directorios indicados:

```powershell
# D:\Nocountru\mediflow\backend
# Ejecutado con RUN_OCI_INTEGRATION=0 y OCI_RUN_INTEGRATION=0 en el proceso hijo.
.\.venv\Scripts\python.exe -m pytest tests ..\data_ai -m 'not integration' -q -p no:cacheprovider --basetemp <directorio-temporal-nuevo>

# D:\Nocountru\mediflow\frontend_web
node --test tests/documents-api.test.js tests/documents-mock.test.js tests/document-detail.test.js
node --check src/historial/app.js
node --check src/assets/js/documents-api.js
node --check src/assets/js/document-detail.js

# D:\Nocountru\mediflow\frontend_mobile\mediflow_app
flutter analyze --no-pub
flutter test --no-pub --reporter expanded
```

Registros locales de esta ejecución, fuera del repositorio:

- Backend/data_ai: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-base-backend-ign_xee4\tests.log`.
- Web: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-base-web-ltd64nze\tests.log`.
- Flutter: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-base-flutter-b37eb50b0fcd404f935a53d8c08a64a3\analyze.log` y `tests.log`.

La ejecución inicial del envoltorio de web no pudo imprimir un símbolo Unicode en la consola, después de que Node terminara correctamente. Se leyó el registro con UTF-8 y se completaron las tres comprobaciones de sintaxis; no fue un fallo de las pruebas web.

No ejecutado: llamadas reales a Gemini/OCI, las cinco pruebas backend marcadas integration, las dos pruebas Flutter opt-in, prueba física de cámara, APK ni demostración contra servicios reales. No se activaron flags de integración ni se enviaron documentos a proveedores.

## Base correcta y plan exacto de commits

Base del Sprint 4: **main en `b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e`**, no develop ni el worktree histórico de Sprints 1–2. Rama propuesta: `feature/s4-edil-auditoria-web`, según el alcance S4-07.

| Grupo | Archivos pendientes | Acción propuesta |
| --- | --- | --- |
| Nicolás / Laura | Ninguno | No repetir commits ya consolidados |
| Drazen / Brando / Eliana | Ninguno | No repetir commits ya consolidados |
| Flor / Edil Flutter | Ninguno | No repetir commits ya consolidados |
| Preparación S4-07 | `docs/sprint-4/preparacion-base.md` | Un commit documental después de autorización |

No corresponde crear otra integración del Sprint 3: sus ocho commits ya están en main. El siguiente bloque es una propuesta, **no ejecutada**. Requiere autorización separada para modificar Git y publicar. Si aparecen otros archivos o cambia HEAD, detenerse y volver a revisar.

```powershell
Set-Location -LiteralPath 'D:\Nocountru'
if ((git branch --show-current).Trim() -ne 'main') { throw 'Revisar rama actual' }
if ((git rev-parse HEAD).Trim() -ne 'b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e') { throw 'La base cambió; volver a auditar' }
git status --short --untracked-files=all
# Continuar solo si el único pendiente es docs/sprint-4/preparacion-base.md.
git switch -c feature/s4-edil-auditoria-web
if ($LASTEXITCODE -ne 0) { throw 'No se creó la rama' }
git add -- docs/sprint-4/preparacion-base.md
if ($LASTEXITCODE -ne 0) { throw 'Falló la preparación del informe' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Revisar errores del índice' }
$prepared = @(git diff --cached --name-only)
if ($prepared.Count -ne 1 -or $prepared[0] -ne 'docs/sprint-4/preparacion-base.md') { throw 'Hay otros archivos preparados' }
git commit -m "docs(sprint4): verificar base consolidada de Sprint 3"
if ($LASTEXITCODE -ne 0) { throw 'Falló el commit' }
git status -sb
# Solo con autorización de publicación:
git push -u origin feature/s4-edil-auditoria-web
```

Antes del push debe verificarse si main remoto cambió y acordarse cómo incorporar novedades. No se propone force push, push directo a main ni merge automático. La futura revisión/PR corresponde a otra fase y requiere autorización.

## Riesgos y pendientes para Sprint 4

1. Aprobar con el equipo el contrato de auditoría persistente antes de crear acciones conectadas Aprobar/Rechazar. Hoy solo están POST de triage y GET de documentos; no inventar rutas ni campos de revisión.
2. El panel web de auditoría conserva datos de maqueta, niveles MTS, identidad de profesional y umbrales de demostración. No presentarlos como información del backend ni reutilizarlos como reglas clínicas.
3. Ratificar los criterios provisionales de confianza, calibrar el umbral existente y mantener las reglas experimentales en el perfil de demo. Las pruebas sintéticas no son validación clínica.
4. Revisar autenticación, permisos y CORS para el entorno final; no declarar lista una exposición pública por aprobar suites locales.
5. Documentar idempotencia y recuperación ante fallos parciales entre copia de objeto y persistencia del JSON.
6. Probar dispositivo físico, conectividad, cámara y APK con una API accesible y configuración adecuada. Las pruebas locales y evidencias históricas no sustituyen estas comprobaciones.

## Cierre de la fase

**Preparado para comenzar Sprint 4 desde la base verificada.** No quedan cambios funcionales del Sprint 3 por consolidar en esta copia. El único archivo nuevo es este informe. Se espera autorización antes de crear la rama, preparar archivos, confirmar commits o publicar.
