# MediFlow — Validación de salida estructurada del LLM

**Responsable:** Laura Paiva
**Sprint:** Sprint 2
**Tarea:** S2-02 — Validar la salida estructurada del LLM

## 1. Objetivo

Comprobar que la salida generada por el LLM pueda ser interpretada como JSON y cumpla las reglas estructurales y de consistencia definidas por el contrato activo de MediFlow.

La validación reutiliza el validador oficial del backend y no implementa un contrato paralelo.

## 2. Alcance

La validación cubre la salida clínica del LLM:

- clasificacion
- datos_extraidos
- decision_enrutamiento

Los campos documento_id, almacenamiento_oci, notificacion_generada y el estado final son completados o derivados posteriormente por el backend.

## 3. Casos de prueba

| ID | Caso | Resultado esperado |
|---|---|---|
| VAL-001 | JSON completo y válido | Aceptar |
| VAL-002 | JSON mal formado | Rechazar |
| VAL-003 | Falta justificacion_enrutamiento | Rechazar |
| VAL-004 | Tipo de dato incorrecto | Rechazar |
| VAL-005 | score_confianza_clasificacion fuera de 0–1 | Rechazar |
| VAL-006 | requiere_auditoria_humana con tipo incorrecto | Rechazar |
| VAL-007 | Auditoría humana y destino inconsistentes | Rechazar |

## 4. Criterio de consistencia de enrutamiento

Cuando `requiere_auditoria_humana = true`, el destino debe corresponder a `Cola_Revision_Humana`.

Una respuesta puede cumplir individualmente con los tipos de datos y aun ser rechazada si sus campos son lógicamente contradictorios.

## 5. Resultado

Los siete casos fueron ejecutados mediante pytest y aprobaron correctamente.

Resultado esperado:

`7 passed`

## 6. Límites

Estas pruebas validan estructura, tipos, rango y consistencia lógica básica.

No validan todavía:

- exactitud clínica de la extracción;
- calibración del score de confianza;
- umbral para determinar ambigüedad;
- calidad clínica de la justificación;
- desempeño real del LLM sobre todos los documentos del dataset.

Esos puntos corresponden a etapas posteriores del proyecto.