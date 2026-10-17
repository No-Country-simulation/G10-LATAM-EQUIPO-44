# MediFlow — S3-01.5 | Entrega técnica a Eliana

**Alcance:** detector heurístico experimental de señales de urgencia clínica y prioridad documental. No está validado para decisiones asistenciales autónomas.

## Ubicación sugerida

- `mediflow/data_ai/urgency_detector.py`
- `mediflow/data_ai/rules/urgency_catalog_v1_1.json`
- `mediflow/data_ai/tests/test_urgency_scenarios.py` (o carpeta de pruebas acordada)

**Importante:** el detector entregado usa por defecto un catálogo situado junto al archivo Python. Para respetar la estructura propuesta, invocar `detect_urgency(..., catalog_path=...)` con la ruta de `rules/urgency_catalog_v1_1.json` o ajustar `DEFAULT_CATALOG` antes de integrarlo. No se ha conectado al backend.

## API

```python
from pathlib import Path
from urgency_detector import detect_urgency

base = Path(__file__).resolve().parent
result = detect_urgency(
    {'texto_extraido': 'Paciente con plan suicida actual.', 'cie10_sugerido': ''},
    catalog_path=base / 'rules' / 'urgency_catalog_v1_1.json'
)
```

Entrada: `str` o `dict` con campos textuales reconocidos (`texto`, `texto_extraido`, `contenido`, `diagnostico_principal`, `observaciones`, `hallazgos`, `resumen_clinico`, `motivo_consulta`); códigos opcionales mediante `codes` o `cie10_sugerido`, `codigos_cie10`, `cie10`.

Salida: `catalog_version`, `clinical_alert` (`none_detected`, `possible_urgent_assessment`, `possible_emergency`), `document_priority` (`routine`, `indeterminate`, `priority_review`), `requires_human_review`, `matches`, `limitations`.

## Integración propuesta

El contrato actual de Gemini (`mediflow/data_ai/schemas/mediflow_schema.json`) declara `additionalProperties: false`. Por tanto **no insertar campos nuevos en el JSON de Gemini** sin acordar primero un cambio de contrato. Ejecutar el detector tras la extracción y antes de decidir qué alertas muestra o almacena el backend; conservar el resultado como objeto separado hasta acordar su persistencia. No modificar automáticamente `nivel_prioridad`, `status` o `destino_principal`.

El detector analiza solo campos reconocidos; si el JSON real contiene texto en otros campos, el equipo integrador debe pasar el texto clínico explícitamente. Evitar incorporar datos identificatorios o metadatos administrativos como evidencia clínica.

## Pruebas

Desde la carpeta de entrega:

```bash
python -m unittest -v test_urgency_scenarios
```

21 escenarios sintéticos y 3 comprobaciones técnicas; **24/24 expectativas satisfechas** en esta versión (ver `results.txt`). Se corrigieron **expectativas de pruebas**, no las reglas: violencia con peligro actual -> `possible_urgent_assessment` + `priority_review`; antecedente histórico de infarto -> `indeterminate` documental. La batería no mide sensibilidad, especificidad ni seguridad clínica.

## Pendientes antes de integración operativa

1. Acordar con Eliana dónde invocar el detector y dónde persistir las alertas.
2. Validar reglas clínicas y psicosociales con profesionales responsables; definir respuesta ante riesgo inminente, protección de menores y seguimiento.
3. Ampliar pruebas adversariales de negaciones, temporalidad, sospechas, códigos y texto sin contexto; evaluar falsos negativos.
4. Definir versión de CIE-10 y política de auditoría, trazabilidad, protección de datos y revisión humana.
5. Evitar desplegar el detector como mecanismo único de triaje o priorización asistencial.

## Decisión de arquitectura

No se entrega ni requiere `urgency_json_adapter.py`. El pipeline puede llamar directamente a `detect_urgency` una vez acordada su interfaz. El módulo no ejecuta llamadas a Gemini ni altera el contrato existente.
