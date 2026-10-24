### 2. Información de Campos, Tipos y Obligatoriedad

* **`status`** (String, Obligatorio): Estado general del procesamiento. **Catálogo estricto permitido:**
* `"recibido"`
* `"procesado"`
* `"auditoria_humana"`
* **`cargado_por`** (String o null, compatible con documentos históricos): Identidad verificada del usuario que carga el archivo, asignada por el servidor. No identifica al médico del documento. No se acepta como texto libre ni se obtiene del LLM. Se devuelve null si la carga no tenía identidad autenticada o si el JSON histórico no contenía el campo.

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
* `justificacion_enrutamiento` (String, Obligatorio).


* **`notificacion_generada`** (Objeto, Opcional): Se incluye solo si el sistema debe generar una alerta (ej. casos urgentes).
* `canal` (String): Medio o grupo de destino de la alerta.
* `mensaje` (String): Texto descriptivo de la advertencia clínica.


* **`almacenamiento_oci`** (Objeto, Obligatorio):
* `bucket` (String, Obligatorio): Nombre del bucket en OCI Object Storage.
* `ruta_objeto` (String, Obligatorio): Ruta virtual o prefijo donde se guardó el archivo procesado.
* `status_backup` (String, Obligatorio): Resultado de la subida a la nube. **Catálogo estricto permitido:**
* `"exito"`
* `"fallo"`

### Agregado por Edil: cómo aplicamos esta corrección
Usamos los nombres de Eliana: `medicamentos_recetados`, `medicamento` y `dosis`.
La prioridad del contrato es Rutina o Urgente; no enviamos Pendiente como prioridad.
El esquema de Nicolás permite dosis null cuando no está escrita; no inventamos una dosis para llenar el campo.
La especialidad también puede ser null cuando no aparece en el documento.
El ejemplo conserva el contenido de Eliana; el bucket se ajustó a `recibidos` porque usamos tres buckets independientes: recibidos, procesados y auditoria_humana.
Un estado procesado no confirma un traslado de bucket ni una notificación. Esas acciones requieren implementación y comprobación aparte.

Agregado por Edil: aplicada la corrección de Eliana bcefff1; la justificación es obligatoria y coincide con Pydantic y las pruebas de Laura.

### Agregado por Edil: conexión de `cargado_por` (Sprint 4)

La propuesta original decía «profesional que carga la imagen» y lo marcaba obligatorio,
pero los JSON guardados y Pydantic no lo incluían. Ahora se registra el `login` del
principal autenticado en la recepción y se conserva al terminar el análisis. El
proveedor de identidad debe establecer ese principal dentro del servidor; enviar
un campo multipart con ese nombre no permite suplantarlo. La respuesta de Gemini
tampoco puede reemplazarlo. POST y GET usan el mismo campo público y el JSON
persistido conserva su valor. Los documentos anteriores se leen con null sin
reescribirlos. Un login identifica una cuenta; no certifica que sea profesional
sanitario ni concede permiso para aprobar documentos.
