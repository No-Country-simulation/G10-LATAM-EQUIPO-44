Información de Campos, Tipos y Obligatoriedad

*  **`status`** (String, Obligatorio): Estado general del procesamiento (ej. `"procesado"`, `"pendiente"`, `"ambiguo"`).
*  **`documento_id`** (String, Obligatorio): Identificador único del documento clínico ingresado.
*  **`clasificacion`** (Objeto, Obligatorio):
*   `tipo_documento` (String, Obligatorio): Categoría detectada (ej. Receta Médica, Informe de Diagnóstico, etc.).
*   `especialidad` (String, Opcional): Área médica asociada.
*   `nivel_prioridad` (String, Obligatorio): Rango de urgencia (`"Rutina"`, `"Urgente"`).
*   `score_confianza_clasificacion` (Float, Obligatorio): Valor decimal entre `0.0` y `1.0` que mide la certeza de la IA.
*  **`datos_extraidos`** (Objeto, Obligatorio):
*   `paciente` (Objeto): Contiene `nombre` (String) y `edad` (Integer).
*   `medico_solicitante` (Objeto): Contiene `nombre` (String) y `matricula` (String/Integer).
*   `estudio_realizado` (String, Opcional): Detalle del examen o procedimiento.
*   `diagnostico_principal` (String, Opcional): Descripción clínica del diagnóstico.
*   `cie10_sugerido` (String, Opcional): Código estandarizado de la CIE-10.
*  **`decision_enrutamiento`** (Objeto, Obligatorio):
*   `destino_principal` (String, Obligatorio): Cola o departamento de destino.
*   `requiere_auditoria_humana` (Boolean, Obligatorio): Bandera de control (`true` / `false`) para derivar a revisión manual en casos ambiguos.
*   `justificacion_enrutamiento` (String, Opcional): Motivo lógico de la decisión del agente.
*  **`notificacion_generada`** (Objeto, Opcional):
*   `canal` (String): Medio o grupo de destino de la alerta.
*   `mensaje` (String): Texto descriptivo de la advertencia.
*  **`almacenamiento_oci`** (Objeto, Obligatorio):
*   `bucket` (String, Obligatorio): Nombre del bucket en OCI Object Storage.
*   `ruta_objeto` (String, Obligatorio): Ruta virtual o prefijo donde se guardó el archivo procesado.
*   `status_backup` (String, Obligatorio): Resultado de la subida a la nube (ej. `"exito"`).