# S4-Laura — Matriz de confianza y validación de casos ambiguos

## 1. Objetivo

Validar técnicamente las reglas provisionales de confianza de MediFlow por tipo
documental y preparar casos completos y ambiguos para el MVP.

Esta validación es técnica. No constituye aprobación clínica o funcional de los
criterios documentales.

---

## 2. Conceptos utilizados

### Estado de cada criterio

- PRESENTE: el criterio corresponde y existe un valor estructuralmente utilizable.
- AUSENTE: el criterio corresponde, pero no contiene un valor utilizable.
- NO_APLICABLE: el criterio no corresponde al tipo documental y se excluye del cálculo.
- NO_VERIFICABLE: el criterio es relevante pero MediFlow no puede comprobarlo
  con el contrato o la información disponible.

### Completitud

Representa la proporción de criterios exigidos y evaluables que se encuentran
presentes.

### Score de confianza de clasificación

`score_confianza_clasificacion` representa la confianza del modelo respecto del
tipo documental. No representa probabilidad de exactitud clínica.

### Score operativo

MediFlow combina la confianza de clasificación con la completitud:

score_operativo = min(score_confianza_clasificacion, completitud)

Para el MVP:

- score_operativo < 0.70 → ambiguo por umbral
- score_operativo >= 0.70 → no ambiguo por umbral

Un score >= 0.70 no elimina bloqueos por criterios esenciales ausentes o no
verificables ni alertas críticas.

---

## 3. Matriz provisional por tipo documental

| Tipo documental | Criterios esenciales verificables | No aplicable | No verificable actualmente |
|---|---|---|---|
| Receta Médica | Paciente, medicamento, profesional | Diagnóstico | Ninguno del perfil; dosis ILLEGIBLE se maneja como alerta crítica |
| Informe de Laboratorio | Paciente, estudio | Diagnóstico | Resultados, unidades, rangos y fecha |
| Informe de Estudio por Imágenes | Paciente, estudio | Diagnóstico | Hallazgos y conclusión |
| Orden / Solicitud de Procedimiento | Paciente | Diagnóstico | Procedimiento solicitado e indicación |
| Epicrisis / Informe de Alta | Paciente | Diagnóstico | Evolución, alta y seguimiento |
| Certificado Médico | Paciente, profesional | Diagnóstico | Motivo, período y firma |

Los criterios son provisionales y están pendientes de ratificación funcional.

---

## 4. Línea base de pruebas

### Perfiles de confianza

Comando:

pytest tests/test_confidence_profiles.py -v

Resultado:

35 passed

### Score, umbral y orquestador

Se probaron:

- score de confianza;
- completitud;
- frontera 0.70;
- dosis ILLEGIBLE;
- separación entre urgencia y ambigüedad;
- tipos documentales desconocidos;
- conservación de revisiones previas;
- integración con el orquestador.

Resultado:

56 passed

---

## 5. Casos sintéticos para Demo

### Caso A — Receta completa con confianza suficiente

Configuración sintética:

- Tipo: Receta Médica
- Paciente: PRESENTE
- Medicamento: PRESENTE
- Profesional: PRESENTE
- Diagnóstico: NO_APLICABLE
- score_confianza_clasificacion: 0.95
- completitud: 1.00
- score_operativo: 0.95

Resultado esperado y obtenido:

- es_ambiguo: false
- status: procesado
- requiere_auditoria_humana: false
- destino: Cola_Farmacia

### Caso B — Receta con dosis ilegible

Configuración sintética:

- Tipo: Receta Médica
- score_confianza_clasificacion: 0.95
- dosis: ILLEGIBLE

La dosis ilegible genera una alerta crítica, por lo que un score alto de
clasificación no permite procesamiento automático.

Resultado esperado y obtenido:

- score_operativo: 0.0
- es_ambiguo: true
- status: auditoria_humana
- requiere_auditoria_humana: true
- destino: Cola_Revision_Humana

### Evidencia de prueba

Comando:

`pytest tests/test_s4_laura_confianza.py -v`

Resultado:

`2 passed`

---

## 6. Casos límite validados

Se agregaron pruebas específicas de Sprint 4 para los siguientes escenarios:

| Caso | Resultado esperado |
|---|---|
| Receta sin medicamentos | AUSENTE → bloqueo → auditoría humana |
| Informe de laboratorio sin estudio | AUSENTE → bloqueo → ambiguo |
| Tipo documental no reconocido | tipo_registrado AUSENTE → auditoría humana |
| Dosis ILLEGIBLE | alerta crítica → score operativo 0 → auditoría humana |
| Score exactamente 0.70 | no ambiguo por umbral |
| Urgente + score 0.69 | auditoría humana conservando prioridad Urgente |

Además se verificaron los seis perfiles documentales y los estados:

- PRESENTE
- AUSENTE
- NO_APLICABLE
- NO_VERIFICABLE

Resultado de la suite propia de Sprint 4:

`31 passed`

Estas pruebas validan el comportamiento técnico de la configuración provisional.
No constituyen aprobación clínica de los criterios documentales.
## 7. Regresión conjunta

Se ejecutó una regresión conjunta sobre:

- pruebas propias de Sprint 4;
- perfiles de confianza;
- score de confianza;
- frontera del umbral 0.70;
- integración del umbral;
- orquestador.

Resultado:

`122 passed in 0.42s`

La regresión confirma que los casos agregados para Sprint 4 son compatibles
con la implementación consolidada del Sprint 3.
---

## 8. Matriz de revisión de criterios

Las siguientes decisiones representan la configuración técnica provisional del
MVP. No constituyen requisitos clínicos ni aprobación funcional definitiva.

| Tipo | Criterio | Razón técnica | Evidencia / prueba | Decisión provisional | Aprobación funcional |
|---|---|---|---|---|---|
| Receta Médica | Paciente | Configurado como criterio esencial verificable | Matriz por tipo + paciente ausente | PRESENTE cumple; AUSENTE bloquea | Pendiente |
| Receta Médica | Medicamentos | El perfil exige lista no vacía y nombre utilizable | Receta sin medicamentos | AUSENTE bloquea | Pendiente |
| Receta Médica | Profesional | Configurado como esencial verificable | Matriz por tipo | PRESENTE cumple; AUSENTE bloquea | Pendiente sobre rol del profesional |
| Receta Médica | Diagnóstico | No se exige en el perfil mínimo actual | Matriz por tipo | NO_APLICABLE; fuera del denominador | Pendiente |
| Receta Médica | Dosis ILLEGIBLE | Alerta crítica existente del modelo de confianza | Caso sintético ambiguo | Auditoría humana | Política técnica MVP vigente |

| Informe de Laboratorio | Paciente | Configurado como esencial verificable | Matriz + paciente ausente | AUSENTE bloquea | Pendiente |
| Informe de Laboratorio | Estudio realizado | Identifica el examen en el contrato actual | Informe sin estudio | AUSENTE bloquea | Pendiente |
| Informe de Laboratorio | Diagnóstico | No exigido en el mínimo provisional | Matriz por tipo | NO_APLICABLE | Pendiente |
| Informe de Laboratorio | Resultados, unidades, rangos y fecha | El contrato actual no dispone de campos suficientes para comprobarlos | Matriz por tipo | NO_VERIFICABLE; revisión humana | Pendiente |

| Informe de Imágenes | Paciente | Configurado como esencial verificable | Matriz + paciente ausente | AUSENTE bloquea | Pendiente |
| Informe de Imágenes | Estudio realizado | Campo verificable disponible | Matriz por tipo | PRESENTE cumple; AUSENTE bloquea | Pendiente |
| Informe de Imágenes | Diagnóstico | No exigido universalmente en el perfil actual | Matriz por tipo | NO_APLICABLE | Pendiente |
| Informe de Imágenes | Hallazgos / conclusión | No existe representación estructurada suficiente en el contrato | Matriz por tipo | NO_VERIFICABLE; revisión humana | Pendiente |

| Orden / Solicitud | Paciente | Configurado como esencial verificable | Matriz + paciente ausente | AUSENTE bloquea | Pendiente |
| Orden / Solicitud | Diagnóstico | No exigido en el mínimo provisional | Matriz por tipo | NO_APLICABLE | Pendiente |
| Orden / Solicitud | Procedimiento solicitado / indicación | No está representado inequívocamente en el contrato | Matriz por tipo | NO_VERIFICABLE; revisión humana | Pendiente |

| Epicrisis / Alta | Paciente | Configurado como esencial verificable | Matriz + paciente ausente | AUSENTE bloquea | Pendiente |
| Epicrisis / Alta | Diagnóstico | No exigido en la política provisional actual | Matriz por tipo | NO_APLICABLE | Pendiente |
| Epicrisis / Alta | Evolución, alta y seguimiento | El contrato no permite verificar estos componentes de forma estructurada | Matriz por tipo | NO_VERIFICABLE; revisión humana | Pendiente |

| Certificado Médico | Paciente | Configurado como esencial verificable | Matriz + paciente ausente | AUSENTE bloquea | Pendiente |
| Certificado Médico | Profesional | Configurado provisionalmente como esencial | Matriz por tipo | PRESENTE cumple; AUSENTE bloquea | Pendiente sobre rol emisor/firmante |
| Certificado Médico | Diagnóstico | No se exige universalmente | Matriz por tipo | NO_APLICABLE | Pendiente |
| Certificado Médico | Motivo, período y firma | No existen campos suficientes para comprobarlos | Matriz por tipo | NO_VERIFICABLE; revisión humana | Pendiente |

---

## 9. Checklist de cierre técnico

- [x] Se revisaron los seis tipos documentales configurados.
- [x] Se validó PRESENTE.
- [x] Se validó AUSENTE.
- [x] Se validó NO_APLICABLE y su exclusión del denominador.
- [x] Se validó NO_VERIFICABLE y su bloqueo cuando el criterio es esencial.
- [x] Se probó receta sin medicamentos.
- [x] Se probó informe sin dato esencial.
- [x] Se probó tipo documental no reconocido.
- [x] Se probó dosis ILLEGIBLE.
- [x] Se verificó la frontera exacta 0.70.
- [x] Se verificó Urgente + baja confianza sin pérdida de prioridad.
- [x] Se preparó caso sintético con confianza suficiente.
- [x] Se preparó caso sintético ambiguo para auditoría humana.
- [x] Se ejecutó regresión conjunta: 122 passed.
- [ ] Aprobación funcional de los criterios documentales.
- [ ] Coordinación para commit, push y PR.
