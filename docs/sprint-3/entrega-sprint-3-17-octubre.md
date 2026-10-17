# Entrega consolidada Sprint 3 — revisión del 17 de octubre de 2026

Preparación local; ningún commit, push, merge ni cambio de rama ejecutado. Agregado por Edil: este informe conserva las entregas existentes y distingue evidencia sintética de validación clínica.

## Estado y preservación

Rama revisada: `cierre/edil-sprint-3-2026-10-16`. HEAD y main local: `47701cb991c9e720587863f1f1b69120482ea963`. No se hizo fetch: no se afirma igualdad con main remoto actual.

Se encontraron 56 archivos pendientes: 38 rastreados modificados/agregados y 18 sin seguimiento; 31 estaban preparados en el índice. Se respaldaron los 56 archivos con SHA-256, índice y parches binarios en `C:\Users\leno\AppData\Local\Temp\MediFlow-sprint3-git-review-17oct-pmtnas6f`. El respaldo temporal debe conservarse hasta terminar el cierre.

Cuatro archivos tienen versiones distintas entre índice y carpeta de trabajo: `guia-verificacion-json-oci.md`, `orquestador.py`, `test_synthetic_demo_urgency.py` y `criterios_por_tipo_propuesta_s3_02_1.md`. No confirmar directamente el índice actual: dejaría fuera correcciones y módulos nuevos. El plan incorpora las versiones finales completas, sin duplicar el orquestador compartido.

Se recuperaron cinco evidencias de la carpeta indicada por el usuario, sin alterar los originales: Laura (regresión demo) y Flor (GET, captura, verificación, parche). Las copias conservan su SHA-256. El parche de Flor es histórico, solo enumera cuatro archivos y no reemplaza la implementación actual de siete archivos; no se aplicó. La captura muestra datos del caso sintético MF_004 autorizado, no credenciales. Con estas copias y los tres documentos de preparación hay **64 archivos propuestos**. La lista exacta y los hashes de los 61 archivos de entrada están en `plan-commits-sprint-3-17-octubre.json`.

## Coexistencia y responsabilidades funcionales

- Nicolás: perfil explícito `synthetic_demo_v1`, transcripción interna de la misma llamada Gemini para conservar señales de PDF/imágenes, reglas experimentales ya existentes del dataset, evaluador y trazas. El perfil general conserva su comportamiento; las reglas de demo no son validación clínica ni se activan por defecto.
- Laura: perfiles configurables por tipo; estados presente, ausente, no aplicable y no verificable; tipo desconocido y faltantes esenciales llevan a revisión. Se reutilizan fórmula y umbral 0.70. La demo conserva compatibilidad con los cuatro criterios anteriores sin cancelar revisiones previas. Los mínimos provisionales requieren ratificación del equipo.
- Eliana: orquestación compartida y 18 pruebas adicionales de integración, informe y evidencias de tres casos reales previos. No hay modificación unilateral del contrato público.
- Drazen/Brando, con apoyo OCI de Edil: verificador de persistencia, copia nativa OCI, espera de trabajo, lectura y comparación del JSON; escenarios procesado/auditoría y manejo de errores. El verificador utiliza una estructura sintética fija, sin Gemini: no confundirlo con análisis LLM completo.
- Flor: detalle web mediante GET individual, carga/error/reintento, protección de respuestas tardías y pruebas. En modo demo se identifica el origen de datos. La aprobación humana sigue fuera del alcance de este GET.
- Edil: implementación Flutter preexistente; pendientes previos de README y pruebas HTTP opt-in, más documentación y evidencias de cierre. No se modificó ningún archivo Flutter en esta preparación.

La asignación indica responsabilidad funcional, no prueba de autoría individual. El orquestador y sus dependencias Nico/Laura se confirman juntos para conservar imports y comportamiento coherentes. No se reescribieron funcionalidades durante esta revisión.

## Verificación acumulada

| área | Resultado actual |
| --- | --- |
| Backend y data_ai | 363 pruebas + 21 subcasos aprobados; 5 pruebas integration excluidas |
| Frontend web | 40 pruebas aprobadas; 3 comprobaciones de sintaxis aprobadas |
| Flutter | 178 pruebas aprobadas; 2 pruebas reales opt-in omitidas |
| Flutter analyze | Sin problemas |
| Conflictos / diff check | Sin entradas sin fusionar ni marcadores; índice y trabajo sin errores de espacios |
| PDF | Los 6 PDF coinciden byte a byte con HEAD e índice; lectura estricta válida |
| Secretos | Sin coincidencias detectadas en archivos pendientes ni versiones preparadas; .env, claves y configuración OCI están ignorados |

Los 267 tests del cierre de Eliana pertenecían a una selección anterior: no se suman a los 363 actuales porque hay solapamiento. Se observaron dos avisos de dependencias de Python, sin fallos. Se conserva `.gitattributes` con `*.pdf -text`; no hay cambios del dataset que incorporar.

No se repitieron llamadas reales a OCI/Gemini. Los informes reales anteriores se conservan como evidencia histórica: Laura 9/9 en perfil demo; Eliana tres escenarios completos; Flor GET de lectura sobre un caso almacenado. Esto no garantiza cuota/disponibilidad futura ni seguridad clínica.

## Plan de commits, todavía sin ejecutar

| Orden | Responsabilidad | Archivos | Mensaje |
| --- | --- | ---: | --- |
| 01 | Transversal | 1 | chore(dataset): preservar PDF como binarios |
| 02 | Nicolas, Laura, Eliana (orquestacion compartida) | 14 | feat(triage): consolidar perfiles de confianza y demo sintetica |
| 03 | Nicolas | 12 | test(data-ai): registrar evaluacion del dataset y urgencia demo |
| 04 | Drazen, Brando, Edil (apoyo OCI) | 10 | test(oci): verificar persistencia y recuperacion Sprint 3 |
| 05 | Flor | 11 | feat(web): consultar detalle individual con estados y pruebas |
| 06 | Eliana | 6 | test(integracion): consolidar cierre del pipeline Sprint 3 |
| 07 | Edil | 7 | test(flutter): documentar cierre y verificacion HTTP existente |
| 08 | Entrega transversal | 3 | docs(sprint3): agregar auditoria y plan de cierre consolidado |

El JSON del plan enumera cada archivo exactamente una vez. El último commit incluye este informe, el plan y el resumen de auditoría. No usar `git add .`; no aplicar parches históricos ni incluir `.env`.

## Comandos propuestos para después de autorizar los commits

Agregado por Edil durante la ejecución autorizada: el parche histórico `flor-s3-cambios.patch` contiene dos líneas de contexto con espacios finales. Se conservan sus bytes y SHA-256 como evidencia; solo ese archivo se excluye del control de espacios. Los archivos de código y demás documentos mantienen la comprobación estricta.

Ejecutar desde PowerShell. El bloque se detiene ante un estado distinto al auditado. No ejecutado durante esta preparación. No incluye push ni merge.

```powershell
Set-Location -LiteralPath 'D:\Nocountru'
$plan = Get-Content -LiteralPath 'docs/sprint-3/plan-commits-sprint-3-17-octubre.json' -Raw | ConvertFrom-Json
if ((git rev-parse HEAD).Trim() -ne $plan.base_commit) { throw 'HEAD cambió; volver a revisar' }
if ((git branch --show-current).Trim() -ne $plan.current_branch) { throw 'Rama distinta; volver a revisar' }
if (git ls-files -u) { throw 'Hay conflictos pendientes' }
foreach ($entry in $plan.input_sha256.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.Value) { throw "Cambió el archivo $($entry.Name)" }
}
$allPlannedPaths = @($plan.commits | ForEach-Object { $_.files })
$pending = @((git diff --name-only HEAD); (git ls-files --others --exclude-standard)) | Sort-Object -Unique
if (@(Compare-Object ($allPlannedPaths | Sort-Object) $pending).Count -ne 0) { throw 'La lista pendiente cambió; volver a auditar' }
# Agregado por Edil: respaldo adicional del índice antes de repartirlo.
$stageBackup = Join-Path $env:TEMP ('MediFlow-s3-index-' + [guid]::NewGuid().ToString('N') + '.patch')
git diff --cached --binary --output=$stageBackup
if ($LASTEXITCODE -ne 0) { throw 'No se pudo respaldar el índice' }
git switch -c $plan.proposed_branch
if ($LASTEXITCODE -ne 0) { throw 'No se creó la rama de cierre' }
# Solo quita la preparación; conserva todos los archivos y modificaciones.
$stagedPaths = @(git diff --cached --name-only)
if ($stagedPaths.Count -gt 0) { git restore --staged -- $stagedPaths }
if ($LASTEXITCODE -ne 0) { throw 'No se pudo repartir el índice' }
foreach ($item in $plan.commits) {
    git add -- $item.files
    if ($LASTEXITCODE -ne 0) { throw 'Falló git add' }
    git diff --cached --check -- . ':(exclude)docs/sprint-3/evidencias/flor-s3-cambios.patch'
    if ($LASTEXITCODE -ne 0) { throw 'Revisar errores del índice' }
    $staged = @(git diff --cached --name-only)
    if (@(Compare-Object ($item.files | Sort-Object) ($staged | Sort-Object)).Count -ne 0) { throw 'Archivos preparados distintos al grupo previsto' }
    git diff --cached --stat
    git commit -m $item.message
    if ($LASTEXITCODE -ne 0) { throw 'Falló el commit; revisar antes de continuar' }
}
git status -sb
git --no-pager log --oneline -8
```

## Pendientes funcionales para Sprint 4 y final

1. Ratificar los criterios documentales provisionales y calibrar el umbral 0.70 contra el dataset; mantener las reglas experimentales de urgencia en demo hasta validación correspondiente. El score no mide exactitud ni seguridad clínica.
2. Completar aprobación/rechazo humano conectado y persistido; la consulta de detalle es de lectura. Definir la visualización autorizada del documento original.
3. Resolver recuperación ante copia/JSON parcialmente completados e idempotencia de reprocesamientos; la secuencia OCI no es una transacción atómica.
4. Completar autenticación/permisos y revisar CORS para el entorno de entrega; hoy el escenario verificado es una demo sintética restringida.
5. Completar evidencia de cámara/dispositivo físico y paquete instalable/video de demo conforme al plan final. Las pruebas automatizadas de Flutter no sustituyen esa evidencia.

## Recomendación

Se puede autorizar la creación de la rama y los commits locales del plan, conservando los respaldos. La comprobación final debe repetirse si cambia cualquier archivo. No cerrar como validación clínica ni declarar nuevas pruebas reales que no se ejecutaron. Main, rama activa, versiones originales e índice se mantienen sin alteraciones por esta preparación; solo se agregaron evidencias y documentación de entrega.
