Map<String, dynamic> triageFixture({
  String status = 'procesado',
  String priority = 'Rutina',
}) => {
  'status': status,
  'documento_id': 'DOC-PIPELINE',
  'clasificacion': {
    'tipo_documento': 'Receta médica',
    'especialidad': null,
    'nivel_prioridad': priority,
    'score_confianza_clasificacion': 0.8,
  },
  'datos_extraidos': {
    'paciente': {'nombre': null, 'edad': null},
    'medico_solicitante': {'nombre': null, 'matricula': null},
    'estudio_realizado': null,
    'diagnostico_principal': null,
    'cie10_sugerido': null,
    'medicamentos_recetados': [],
  },
  'decision_enrutamiento': {
    'requiere_auditoria_humana': status == 'auditoria_humana',
    'destino_principal': status == 'auditoria_humana'
        ? 'Cola_Revision_Humana'
        : 'Cola_Farmacia',
    'justificacion_enrutamiento': 'Resultado sintético para pruebas.',
  },
  'notificacion_generada': null,
  'almacenamiento_oci': {
    'bucket': 'recibidos',
    'ruta_objeto': 'demo.txt',
    'status_backup': 'exito',
  },
};
