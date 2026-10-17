/// Contrato mínimo del Sprint 2. No interpreta datos clínicos.
class TriageResult {
  TriageResult.fromJson(Map<String, dynamic> json)
    : status = _asText(json['status']),
      documentoId = _asText(json['documento_id']),
      message = _asText(json['message']),
      rawData = Map.unmodifiable(json);

  final String? status;
  final String? documentoId;
  final String? message;
  final Map<String, dynamic> rawData;

  // Agregado por Edil: lectura básica del contrato; conserva rawData y el modelo original.
  Map<String, dynamic> get _classification =>
      rawData['clasificacion'] is Map<String, dynamic>
      ? rawData['clasificacion'] as Map<String, dynamic>
      : {};
  String? get tipoDocumento => _asText(_classification['tipo_documento']);
  String? get prioridad => _asText(_classification['nivel_prioridad']);

  // Agregado por Edil: mostrar únicamente la confianza de clasificación que
  // ya existe en el contrato. No calcular confianza de extracción ni un umbral.
  // Un documento recibido aún no tiene un análisis que presentar al usuario.
  double? get confianzaClasificacion {
    if (!isAnalyzed) return null;
    final value = _classification['score_confianza_clasificacion'];
    if (value is! num || !value.isFinite || value < 0 || value > 1) {
      return null;
    }
    return value.toDouble();
  }

  // Agregado por Edil: la urgencia viene del backend, no del nombre del archivo.
  bool get isAnalyzed => status == 'procesado' || status == 'auditoria_humana';
  bool get isUrgent => isAnalyzed && prioridad == 'Urgente';
  bool get requiresHumanReview => status == 'auditoria_humana';
  Map<String, dynamic> get _routing =>
      rawData['decision_enrutamiento'] is Map<String, dynamic>
      ? rawData['decision_enrutamiento'] as Map<String, dynamic>
      : {};
  String? get destino => _asText(_routing['destino_principal']);
  String? get justificacion => _asText(_routing['justificacion_enrutamiento']);

  // Agregado por Edil: un HTTP exitoso con JSON vacío no es un procesamiento exitoso.
  // Conservamos fromJson para lectores anteriores; el transporte exige este control.
  void validateForDisplay() {
    if (!{'recibido', 'procesado', 'auditoria_humana'}.contains(status) ||
        rawData['documento_id'] is! String ||
        documentoId == null) {
      throw const FormatException('Respuesta sin identidad o estado válido.');
    }
    if (!isAnalyzed) return;
    if (rawData['clasificacion'] is! Map<String, dynamic> ||
        rawData['datos_extraidos'] is! Map<String, dynamic> ||
        rawData['decision_enrutamiento'] is! Map<String, dynamic> ||
        rawData['almacenamiento_oci'] is! Map<String, dynamic> ||
        _classification['tipo_documento'] is! String ||
        tipoDocumento == null ||
        !{'Rutina', 'Urgente'}.contains(prioridad) ||
        _routing['requiere_auditoria_humana'] is! bool ||
        destino == null ||
        justificacion == null) {
      throw const FormatException('Análisis incompleto.');
    }
    final review = _routing['requiere_auditoria_humana'];
    if (review != requiresHumanReview ||
        review != (destino == 'Cola_Revision_Humana')) {
      throw const FormatException('Estado y revisión contradictorios.');
    }
    final confidence = _classification['score_confianza_clasificacion'];
    if (confidence is! num ||
        !confidence.isFinite ||
        confidence < 0 ||
        confidence > 1) {
      throw const FormatException('Confianza inválida.');
    }
    final storage = rawData['almacenamiento_oci'] as Map<String, dynamic>;
    for (final key in ['bucket', 'ruta_objeto', 'status_backup']) {
      if (storage[key] is! String || _asText(storage[key]) == null) {
        throw const FormatException('Almacenamiento incompleto.');
      }
    }
  }

  static String? _asText(Object? value) {
    if (value is! String && value is! num) return null;
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }
}
