# MediFlow — Modelo de Score de Confianza

**Responsable:** Laura Paiva

**Sprint:** Sprint 3

## 1. Objetivo

Definir un score operativo de confianza que permita identificar resultados ambiguos y derivarlos a revisión humana.

Este score no reemplaza `score_confianza_clasificacion`.

El campo `score_confianza_clasificacion` representa la confianza del LLM respecto al tipo documental. El score operativo incorpora además la completitud del resultado y señales críticas de ambigüedad.

## 2. Variables

### Confianza de clasificación

Valor entre 0.0 y 1.0 proveniente de:

`score_confianza_clasificacion`

### Completitud

Valor entre 0.0 y 1.0 que representa la proporción de información esperada que pudo recuperarse correctamente.

### Alerta crítica

Variable booleana que representa la existencia de una condición que requiere revisión humana, por ejemplo:

- información crítica ilegible;
- contradicción explícita;
- información insuficiente para procesar el documento con seguridad.

## 3. Fórmula inicial

Si existe una alerta crítica:

`score_operativo = 0.0`

En caso contrario:

`score_operativo = min(score_confianza_clasificacion, completitud)`

La lógica utiliza el componente más débil para evitar que una confianza alta en una dimensión compense artificialmente una deficiencia importante en otra.

## 4. Detección de ambigüedad

Un documento se considera ambiguo cuando:

`score_operativo < umbral`

El umbral será configurable y deberá ser validado contra los casos de prueba antes de fijarse como política del proyecto.

## 5. Restricciones

- El score siempre debe permanecer entre 0.0 y 1.0.
- Urgencia y ambigüedad son conceptos independientes.
- Un documento urgente y confiable puede continuar sin auditoría por ambigüedad.
- Una alerta crítica prevalece sobre el score numérico.
- El modelo inicial deberá validarse contra los casos Normal, Urgente y Ambiguo del dataset.

## 6. Interfaz de integración

El módulo de score no modifica directamente el estado del documento, el enrutamiento, OCI ni la respuesta del backend.

Su responsabilidad es exclusivamente calcular una señal cuantitativa de confianza y determinar si, según un umbral configurable, el resultado debe considerarse ambiguo.

### Entradas

`evaluar_confianza()` recibe:

- `score_clasificacion`: valor entre 0.0 y 1.0 proveniente de `score_confianza_clasificacion`.
- `criterios_cumplidos`: lista de valores booleanos que representa criterios de completitud previamente evaluados.
- `alerta_critica`: indicador booleano de una condición objetiva que obliga a revisión.
- `umbral`: valor configurable entre 0.0 y 1.0 utilizado para interpretar el score operativo.

### Salida

La función devuelve:

```python
{
    "completitud": float,
    "score_operativo": float,
    "es_ambiguo": bool,
}
```

Ejemplo:

```python
{
    "completitud": 0.75,
    "score_operativo": 0.75,
    "es_ambiguo": False,
}
```

## 7. Responsabilidades externas al módulo

El módulo no determina por sí solo qué campos son obligatorios para cada tipo documental.

La definición de los criterios que alimentan `criterios_cumplidos` debe mantenerse separada de la fórmula matemática y validarse según el contrato y las reglas del proyecto.

Tampoco debe utilizarse `requiere_auditoria_humana` como entrada directa para construir `alerta_critica`, ya que eso produciría una decisión circular: el resultado del enrutamiento estaría siendo utilizado para calcular la misma ambigüedad que debería contribuir a determinarlo.

Las señales de alerta crítica deben provenir de condiciones independientes y verificables, por ejemplo una dosis explícitamente marcada como `ILLEGIBLE`.

## 8. Integración futura con el pipeline

El flujo esperado es:

```text
Respuesta validada del LLM
        ↓
Obtener score_confianza_clasificacion
        ↓
Evaluar criterios de completitud
        ↓
Detectar señales críticas objetivas
        ↓
evaluar_confianza()
        ↓
completitud + score_operativo + es_ambiguo
        ↓
pipeline/orquestador decide estado y destino
```

El módulo de score no debe mover archivos, modificar OCI ni alterar directamente el JSON oficial.

## 9. Política de umbral

Para el MVP y Demo de MediFlow se adopta un umbral operativo de confianza de `0.70`.

La escala se interpreta entre `0.0` y `1.0`, donde un valor mayor representa mayor confianza.

La regla implementada es:

`score_operativo < 0.70` → ambiguo

`score_operativo >= 0.70` → no ambiguo por umbral

El valor `0.70` corresponde a una decisión operativa del MVP y no debe interpretarse como una probabilidad clínica de acierto.

El umbral se mantiene técnicamente configurable para permitir futuras pruebas y calibraciones con un conjunto de datos más amplio.

## 10. Estado de implementación v1

La primera versión del motor matemático de confianza se encuentra implementada y probada.

Incluye:

- cálculo de completitud;
- cálculo de score operativo;
- detección de ambigüedad mediante umbral configurable;
- tratamiento prioritario de alertas críticas;
- detección objetiva de dosis marcada como `ILLEGIBLE`;
- separación entre urgencia y ambigüedad;
- función integrada `evaluar_confianza()`;
- función `evaluar_confianza_con_dosis()` para el primer caso objetivo conectado al formato de MediFlow.

### Resultado de pruebas

`20 passed`

### Pendientes para integración

La integración definitiva con el pipeline depende de decisiones que deben mantenerse externas al motor matemático:

- definición de criterios de completitud por tipo documental;
- identificación de señales críticas adicionales que puedan obtenerse de forma objetiva;
- conexión del resultado `es_ambiguo` con el orquestador del sistema.
