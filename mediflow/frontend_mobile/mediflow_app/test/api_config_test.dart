import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/config/api_config.dart';
import 'package:mediflow_app/models/triage_result.dart';

void main() {
  test('centraliza URL, campo y timeout', () {
    expect(
      ApiConfig.triageUri(url: 'http://10.0.2.2:8000///').toString(),
      'http://10.0.2.2:8000/api/triage',
    );
    expect(
      ApiConfig.triageUri(url: 'https://backend.example.test/prefix/').path,
      '/prefix/api/triage',
    );
    expect(ApiConfig.fileFieldName, 'file');
    expect(ApiConfig.requestTimeout, const Duration(seconds: 30));
  });
  for (final url in [
    '',
    'sin-esquema',
    'file:///tmp',
    'https://',
    'https://user:secret@example.test',
    'https://example.test?token=secret',
    'https://example.test#fragment',
  ]) {
    test('rechaza configuración inválida $url', () {
      expect(() => ApiConfig.triageUri(url: url), throwsFormatException);
    });
  }
  test('fuera de debug requiere HTTPS explícito', () {
    expect(
      () => ApiConfig.triageUri(url: 'http://10.0.2.2:8000', allowHttp: false),
      throwsFormatException,
    );
    expect(
      ApiConfig.triageUri(
        url: 'https://backend.example.test',
        allowHttp: false,
      ).scheme,
      'https',
    );
  });
  test(
    'modelo tolera campos ausentes o tipos no definitivos y conserva rawData',
    () {
      final input = <String, dynamic>{
        'status': [],
        'documento_id': 42,
        'message': {},
        'nuevo_campo': {'sin_contrato': true},
      };
      final result = TriageResult.fromJson(input);
      expect(result.status, isNull);
      expect(result.documentoId, '42');
      expect(result.message, isNull);
      expect(result.rawData, input);
      expect(() => result.rawData['otro'] = true, throwsUnsupportedError);
    },
  );
}
