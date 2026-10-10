### 2. Información de Campos, Tipos y Obligatoriedad

* **`status`** (String, Obligatorio): Estado general del procesamiento. **Catálogo estricto permitido:**
* `"recibido"`
* `"procesado"`
* `"auditoria_humana"`


* **`documento_id`** (String, Obligatorio): Identificador único del documento clínico ingresado.
* **`clasificacion`** (Objeto, Obligatorio):
* `tipo_documento` (String, Obligatorio): Categoría detectada (ej. Receta Médica, Informe de Diagnóstico, Orden de Procedimiento).
* `especialidad` (String, Opcional): Área médica o unidad asociada.
* `nivel_prioridad` (String, Obligatorio): Rango de urgencia clínica. **Catálogo estricto permitido:**
* `"Rutina"`
* `"Urgente"`


* `score_confianza_clasificacion` (Float, Obligatorio): Valor decimal entre `0.0` y `1.0` que mide la certeza de la extracción.


* **`datos_extraidos`** (Objeto, Obligatorio):
* `paciente` (Objeto, Obligatorio): Contiene `nombre` (String, Opcional) y `edad` (Integer, Opcional). *(Se permiten nulos si el documento es ilegible).*
* `medico_solicitante` (Objeto, Obligatorio): Contiene `nombre` (String, Opcional) y `matricula` (String, Opcional).
* `estudio_realizado` (String, Opcional): Detalle del examen, procedimiento o laboratorio.
* `diagnostico_principal` (String, Opcional): Descripción clínica del diagnóstico o hallazgo.
* `cie10_sugerido` (String, Opcional): Código estandarizado de la CIE-10.
* **`medicamentos_recetados`** (Array de Objetos, Opcional): Lista de fármacos extraídos. Si existen, cada objeto debe contener:
* `medicamento` (String, Obligatorio): Nombre del fármaco.
* `dosis` (String, Obligatorio): Cantidad, frecuencia, duración o vía de administración.




* **`decision_enrutamiento`** (Objeto, Obligatorio):
* `destino_principal` (String, Obligatorio): Cola, departamento o sistema de destino.
* `requiere_auditoria_humana` (Boolean, Obligatorio): Bandera de control (`true` / `false`) para derivar a revisión manual por riesgos clínicos, ambigüedades o datos faltantes.
* `justificacion_enrutamiento` (String, Opcional): Motivo lógico de la decisión. *(Opcional en el esquema para evitar caídas del servidor en documentos simples, pero altamente recomendado como directriz en el Prompt de IA).*


* **`notificacion_generada`** (Objeto, Opcional): Se incluye solo si el sistema debe generar una alerta (ej. casos urgentes).
* `canal` (String): Medio o grupo de destino de la alerta.
* `mensaje` (String): Texto descriptivo de la advertencia clínica.


* **`almacenamiento_oci`** (Objeto, Obligatorio):
* `bucket` (String, Obligatorio): Nombre del bucket en OCI Object Storage.
* `ruta_objeto` (String, Obligatorio): Ruta virtual o prefijo donde se guardó el archivo procesado.
* `status_backup` (String, Obligatorio): Resultado de la subida a la nube. **Catálogo estricto permitido:**
* `"exito"`
* `"fallo"`