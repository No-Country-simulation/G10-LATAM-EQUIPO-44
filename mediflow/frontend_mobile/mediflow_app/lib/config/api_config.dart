import 'package:flutter/foundation.dart';

class ApiConfig {
  static const _configuredUrl = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_configuredUrl.isNotEmpty) return _configuredUrl;
    if (!kDebugMode) return '';
    return defaultTargetPlatform == TargetPlatform.android
        ? 'http://10.0.2.2:8000'
        : 'http://127.0.0.1:8000';
  }

  static const fileFieldName = 'file';
  // Agregado por Edil: mismo límite de 10 MiB que acepta el backend.
  static const maxFileBytes = 10 * 1024 * 1024;
  // Agregado por Edil: contempla almacenamiento OCI más análisis autorizado.
  // Agregado por Edil: 120 s de Gemini más margen para subir y persistir en OCI.
  static const requestTimeout = Duration(seconds: 180);

  static Uri triageUri({String? url, bool allowHttp = kDebugMode}) {
    final base = Uri.tryParse((url ?? baseUrl).trim());
    if (base == null ||
        !base.hasAuthority ||
        base.host.isEmpty ||
        !['http', 'https'].contains(base.scheme) ||
        base.userInfo.isNotEmpty ||
        base.hasQuery ||
        base.hasFragment ||
        (!allowHttp && base.scheme != 'https')) {
      throw const FormatException('API_BASE_URL no válida.');
    }
    final prefix = base.path.replaceFirst(RegExp(r'/+$'), '');
    return base.replace(path: '$prefix/api/triage');
  }

  // Agregado por Edil: consultar un documento ya recibido nunca vuelve a subirlo.
  static Uri documentUri(
    String documentId, {
    String? url,
    bool allowHttp = kDebugMode,
  }) {
    if (!RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(documentId)) {
      throw const FormatException('Identificador de documento no válido.');
    }
    final triage = triageUri(url: url, allowHttp: allowHttp);
    final prefix = triage.path.substring(
      0,
      triage.path.length - '/triage'.length,
    );
    return triage.replace(path: '$prefix/documents/$documentId');
  }
}
