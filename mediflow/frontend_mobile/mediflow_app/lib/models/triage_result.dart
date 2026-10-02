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

  static String? _asText(Object? value) {
    if (value is! String && value is! num) return null;
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }
}
