import 'package:flutter/foundation.dart';

class ApiConfig {
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: kDebugMode ? 'http://10.0.2.2:8000' : '',
  );
  static const fileFieldName = 'file';
  static const requestTimeout = Duration(seconds: 30);

  static Uri triageUri({String url = baseUrl, bool allowHttp = kDebugMode}) {
    final base = Uri.tryParse(url.trim());
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
}
