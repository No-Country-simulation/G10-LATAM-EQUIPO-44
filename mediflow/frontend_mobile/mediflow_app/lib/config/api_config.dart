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
  static const requestTimeout = Duration(seconds: 30);

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
}
