/* Sprint 2: datos sintéticos con el contrato de MediFlow. No llama al backend. */
(function (root) {
  "use strict";
  function document(id, status, type, priority, review) {
    const bucket = status === "recibido" ? "recibidos" : review ? "auditoria_humana" : "procesados";
    return {
      status: status,
      documento_id: id,
      clasificacion: {
        tipo_documento: type, especialidad: "General",
        nivel_prioridad: priority, score_confianza_clasificacion: review ? 0.3 : 0.9
      },
      datos_extraidos: {
        paciente: { nombre: "Paciente de prueba", edad: null },
        medico_solicitante: { nombre: null, matricula: null },
        // Agregado por Edil: usamos medicamentos_recetados, como lo definió Eliana.
        estudio_realizado: null, diagnostico_principal: null, cie10_sugerido: null, medicamentos_recetados: []
      },
      decision_enrutamiento: {
        destino_principal: review ? "Cola_Revision_Humana" : "Cola_Procesamiento_Inicial",
        requiere_auditoria_humana: review,
        justificacion_enrutamiento: "Ejemplo sintético para demostración de interfaz."
      },
      notificacion_generada: null,
      almacenamiento_oci: { bucket: bucket, ruta_objeto: id + ".pdf", status_backup: "exito" }
    };
  }
  const documents = [
    document("DOC-DEMO-001", "recibido", "Pendiente de procesamiento", "Rutina", false),
    document("DOC-DEMO-002", "procesado", "Receta médica", "Rutina", false),
    document("DOC-DEMO-003", "procesado", "Informe de laboratorio", "Urgente", false),
    document("DOC-DEMO-004", "auditoria_humana", "Documento ambiguo", "Rutina", true)
  ];
  const toRow = (typeof module !== "undefined" ? require("./documents-api.js") : root.MediFlowDocumentsApi).toRow;
  const api = { documents: documents, toRow: toRow };
  root.MediFlowDocuments = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
