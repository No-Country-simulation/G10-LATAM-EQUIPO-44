import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

// Agregado por Edil: prueba opt-in de transporte Flutter -> FastAPI -> OCI -> GET.
// No usa cámara real, datos de pacientes ni Gemini. Crea un documento sintético único.
void main() {
  const enabled = bool.fromEnvironment('RUN_MEDIFLOW_HTTP_INTEGRATION');
  const baseUrl = String.fromEnvironment(
    'MEDIFLOW_LIVE_API',
    defaultValue: 'http://127.0.0.1:8127',
  );
  test(
    'Flutter envia documento sintetico y recupera el mismo JSON por HTTP real',
    () async {
      final bytes = Uint8List.fromList(
        utf8.encode(
          'Documento sintetico de prueba de transporte MediFlow. Sin datos clinicos.',
        ),
      );
      final service = TriageApiService(baseUrl: baseUrl);
      final result = await service.sendDocument(
        SelectedDocument(
          name: 'integracion_flutter_sintetica.txt',
          extension: 'txt',
          size: bytes.length,
          type: DocumentType.text,
          bytes: bytes,
        ),
        analyze: false,
      );
      expect(result.status, 'recibido');
      expect(result.documentoId, startsWith('DOC-CLIN-'));
      final response = await http.get(
        Uri.parse('$baseUrl/api/documents/${result.documentoId}'),
      );
      expect(response.statusCode, 200);
      expect(jsonDecode(utf8.decode(response.bodyBytes)), result.rawData);
      final directory = await Directory(
        '${Directory.systemTemp.path}/MediFlow-full-e2e',
      ).create(recursive: true);
      await File('${directory.path}/flutter-http.json').writeAsString(
        jsonEncode({
          'synthetic': true,
          'document_id': result.documentoId,
          'status': result.status,
          'get_matches_post': true,
          'api_origin': baseUrl,
        }),
      );
    },
    skip: !enabled,
  );
}
