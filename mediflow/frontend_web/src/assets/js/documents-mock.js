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
        estudio_realizado: null, diagnostico_principal: null, cie10_sugerido: null
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
    document("DOC-DEMO-004", "auditoria_humana", "Documento ambiguo", "Pendiente", true)
  ];
  function toRow(doc) {
    if (!doc || typeof doc.documento_id !== "string" || !doc.clasificacion || !doc.almacenamiento_oci) {
      throw new Error("Documento incompatible con el contrato MediFlow");
    }
    const priority = doc.status === "recibido" ? "pendiente" :
      doc.clasificacion.nivel_prioridad === "Urgente" ? "urgente" :
      doc.clasificacion.nivel_prioridad === "Rutina" ? "rutina" : "pendiente";
    return {
      id: doc.documento_id,
      paciente: doc.datos_extraidos?.paciente?.nombre || "Sin información",
      dni: "No informado", ingreso: "Ejemplo de demostración",
      tipo: doc.clasificacion.tipo_documento,
      prioridad: priority,
      estado: doc.status === "auditoria_humana" ? "auditoria" : doc.status,
      fecha: null,
      ruta: doc.almacenamiento_oci.bucket + "/" + doc.almacenamiento_oci.ruta_objeto,
      documento: doc
    };
  }
  const api = { documents: documents, toRow: toRow };
  root.MediFlowDocuments = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
