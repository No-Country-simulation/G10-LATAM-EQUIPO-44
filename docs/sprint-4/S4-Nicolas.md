# S4-04 — Regresión del detector y material de demostración

**Proyecto:** MediFlow  
**Rama prevista:** `feature/s4-nicolas-urgencia`  
**Perfil de evaluación:** `synthetic_demo_v1`  
**Corte del informe:** 24 de octubre de 2026  
**Estado:** avance documentado; integración HTTP + OCI y regresión integral de 9 documentos pendientes.

## 1. Objetivo y alcance

Según `S4_Nicolas_tareas.pdf`, verificar regresión del detector en 9 casos sintéticos (5 normales y 4 urgentes), adversariales, aislamiento de perfiles, matriz de esperado/obtenido y dos demos reproducibles. Las etiquetas esperadas se toman de `data_ai/dataset/dataset_master.csv` del ZIP de repositorio previamente compartido; **no se alteran**. El ZIP corresponde a una copia del 17/10; está pendiente confirmación por Edil de que sea exactamente la base consolidada Sprint 3.

## 2. Ambiente y procedimientos

- Mac local: Python 3.13.17 y `.venv`; backend FastAPI ejecutado y Swagger accesible (información reportada por el ejecutor).
- Gemini: clave validada; `gemini-3.6-flash` generó extracciones multimodales reales de MF_005 y MF_008.
- Perfil: `TRIAGE_RULES_PROFILE=synthetic_demo_v1` fijado explícitamente; no es criterio clínico general.
- OCI: SDK y credenciales locales funcionales, región `sa-santiago-1`; Object Storage accesible; no hay permisos sobre los buckets del equipo. No hay prueba HTTP + OCI exitosa.
- Metadatos OCI de las pruebas controladas y Gemini/orquestador son **simulados** y solo satisfacen el contrato `TriageResponse`.

## 3. Resultados automatizados

- `backend/tests/test_synthetic_demo_urgency.py`: **30/30 PASS** (según salida local reportada).
- `backend/tests/test_s4_nicolas_regression.py`: **8/8 PASS** (según salida local reportada).
- **38/38 PASS** para estas suites. Archivos locales reportados: `docs/sprint-4/regresion_orquestador_s4.txt` y `resultado_pytest_local.txt`.
- Adversariales cubiertos: negación, mención histórica, formulación equivalente, unidad discordante, literal `ILLEGIBLE`, urgente + auditoría, aislamiento de `general` y nombre de archivo sin activación de demo. `ILLEGIBLE` es una prueba **textual**, no una imagen realmente borrosa.

Comando reproducible desde `mediflow/`:

```bash
PYTHONPATH=backend:. python -m pytest -q backend/tests/test_synthetic_demo_urgency.py backend/tests/test_s4_nicolas_regression.py
```

No se ejecutaron estas suites en la generación de este informe: se documentan las ejecuciones locales proporcionadas.

## 4. Matriz de regresión

Consultar **`matriz_regresion_S4_04.csv`**. Cada fila conserva prioridad, destino y revisión esperados de `dataset_master.csv` y consigna lo realmente observado, su modalidad y la ausencia de verificación integral con OCI.

| Caso | Prioridad esperada | Prioridad obtenida | Destino observado | Evidencia | Estado del nivel probado |
|---|---|---|---|---|---|
| MF_004 | URGENT | Urgente | No verificado | regla sobre TXT local | PASS parcial |
| MF_008 | URGENT | Urgente | Cola_Revision_Humana | Gemini + orquestador | PASS sin OCI |
| MF_009 | URGENT | Urgente | No verificado | regla sobre PDF extraído localmente | PASS parcial |
| MF_011 | URGENT | Urgente | No verificado | regla sobre PDF extraído localmente | PASS parcial |
| MF_001 | ROUTINE | Rutina | Cola_Farmacia | datos estructurados manuales | PASS controlado |
| MF_005 | ROUTINE | Rutina | Cola_Historia_Clinica | Gemini + orquestador | PASS sin OCI |
| MF_006 | ROUTINE | Rutina | Cola_Historia_Clinica | datos estructurados manuales | PASS controlado |
| MF_007 | ROUTINE | Rutina | Cola_Historia_Clinica | datos estructurados manuales | PASS controlado |
| MF_012 | ROUTINE | Rutina | Cola_Historia_Clinica | datos estructurados manuales | PASS controlado |

**Lectura correcta:** no existe evidencia de 9/9 pruebas integrales. La matriz indica PASS únicamente para el nivel de prueba realizado. No se han demostrado resultados finales de destino/revisión para MF_004, MF_009 y MF_011 en el archivo original por cadena completa.

**MF_008, divergencia documentada:** expectativa inicial del dataset `EMERGENCIA_MEDICA`, auditoría `False`; ejecución real `Cola_Revision_Humana`, auditoría `True`. La prioridad final fue Urgente (PASS en prioridad). La divergencia de destino/auditoría requiere evaluación con el equipo; no debe reescribirse la expectativa ni declararse coincidencia integral de todos los campos. No se identificó en la salida la regla concreta que disparó la elevación.

## 5. Dos demostraciones reproducibles

Las demos recomendadas emplean los **JPG originales 100 % sintéticos** previamente probados y muestran la integración real Gemini + orquestador, pero no OCI. Script adjunto `demo_s4.py` (colocar en raíz `mediflow/`).

**Preparación**: desde raíz `mediflow/`, activar `.venv`, disponer de SDK/paquetes del proyecto, claves fuera del repositorio, y verificar autorización del envío de documentos sintéticos a Google. En la terminal de prueba:

```bash
export TRIAGE_RULES_PROFILE=synthetic_demo_v1
export GEMINI_MODEL=gemini-3.6-flash
# GEMINI_API_KEY debe estar definida localmente; nunca imprimirla ni incluirla en Git.
PYTHONPATH=backend:. python demo_s4.py MF_005
PYTHONPATH=backend:. python demo_s4.py MF_008
```

- **Demo normal MF_005**: mostrar archivo, Gemini Rutina, salida final Rutina, `Cola_Historia_Clinica`, auditoría `False`, estado `procesado`.
- **Demo urgente MF_008**: mostrar archivo, salida final Urgente y auditoría `True` con `Cola_Revision_Humana`, estado `auditoria_humana`. En la ejecución observada Gemini dio inicialmente Rutina; no se garantiza que repita exactamente esa prioridad en cada nueva generación.

**Cautelas:** llamadas remotas con consumo de cuota, posible HTTP 503 por sobrecarga y variabilidad de respuesta. Una nueva ejecución puede fallar o arrojar resultados distintos. El script retorna salida no exitosa si la prioridad final difiere de la esperada; no produce capturas ni datos identificatorios de pacientes.

## 6. Riesgos, limitaciones y pendientes

1. Los 9 documentos cuentan con evidencias de distinto nivel; no se dispone de regresión extremo a extremo 9/9.
2. OCI: permisos sobre buckets del equipo y API HTTP integrada aún pendientes. La autenticación local OCI no demuestra persistencia de documentos en buckets compartidos.
3. `ILLEGIBLE` textual no demuestra desempeño sobre imágenes borrosas o ilegibles. Falta adversarial multimodal real.
4. El perfil `synthetic_demo_v1` no equivale a validez clínica; no introducir reglas o umbrales sin acuerdo.
5. No hay estimación formal de tasas de falsos positivos/negativos: en las ejecuciones integradas MF_005 y MF_008 no se observó discrepancia de **prioridad final**, pero no se extrapola a otras entradas. En MF_008 sí existe discrepancia de destino y revisión frente al dataset.
6. Ningún nombre de archivo debe activar reglas demo automáticamente; las pruebas de aislamiento incluidas aprobaron según reporte local.
7. La base Sprint 3 consolidada debe confirmarse con Edil. No realizar commits, push, merge o cambios del contrato/criterios sin coordinación.

## 7. Evidencias y entrega

**Referencias locales reportadas:** `docs/sprint-4/resultado_mf001.txt`, `resultado_mf005.txt`, `resultado_mf008.txt`, `matriz_extraccion_reglas.csv`, `regresion_orquestador_s4.txt`, `resultado_pytest_local.txt`. Estos archivos **no se adjuntaron a esta sesión**; su existencia y contenido se basan en la comunicación del ejecutor. Adjuntar al PR/entrega verificando su presencia.

**Nuevos entregables preparados:** `S4-Nicolas.md`, `matriz_regresion_S4_04.csv`, `demo_s4.py`. Se recomienda documentar hash de commit base y versión de dependencias antes de cerrar entrega, sin exponer secretos.

**Estado de entrega:** informe y demos preparados para revisión; pruebas HTTP/OCI y confirmación de base siguen pendientes. El PDF original fijó entrega para el 22/10/2026, por lo que esta revisión del 24/10/2026 es posterior al plazo indicado.
