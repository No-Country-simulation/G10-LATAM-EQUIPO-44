import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
// Agregado por Edil: antes la consulta usaba http.get directamente. Ahora
// comprobamos getDocument, el mismo servicio que utiliza la pantalla.
// import 'package:http/http.dart' as http;
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

// Agregado por Edil: prueba opt-in de transporte Flutter -> FastAPI -> OCI -> GET.
// La primera prueba no usa Gemini. La segunda requiere otra autorización
// explícita por flag; ambas usan solo documentos sintéticos, nunca cámara real.
void main() {
  const enabled = bool.fromEnvironment('RUN_MEDIFLOW_HTTP_INTEGRATION');
  // Agregado por Edil: separar los flags evita consumir cuota al ejecutar la
  // suite habitual o al comprobar únicamente recepción y recuperación OCI.
  const analysisEnabled = bool.fromEnvironment(
    'RUN_MEDIFLOW_GEMINI_INTEGRATION',
  );
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
      // Agregado por Edil: conservar la comprobación anterior como referencia.
      // final response = await http.get(
      //   Uri.parse('$baseUrl/api/documents/${result.documentoId}'),
      // );
      // expect(response.statusCode, 200);
      // expect(jsonDecode(utf8.decode(response.bodyBytes)), result.rawData);
      final recovered = await service.getDocument(result.documentoId!);
      expect(recovered.rawData, result.rawData);
      await _recordEvidence('flutter-http.json', {
        'synthetic': true,
        'document_id': result.documentoId,
        'status': result.status,
        'get_matches_post': true,
        'gemini_requested': false,
        'api_origin': baseUrl,
      });
    },
    skip: !enabled,
  );

  // Agregado por Edil: aceptación del transporte real de la app con un único
  // POST autorizado. No se fuerza una clasificación, urgencia ni confianza:
  // esos valores deben proceder del backend y superar su contrato actual.
  test(
    'Flutter analiza un TXT sintetico y recupera el resultado real por ID',
    () async {
      final bytes = Uint8List.fromList(
        utf8.encode(
          'DOCUMENTO COMPLETAMENTE SINTETICO PARA PROBAR SOFTWARE. '
          'No corresponde a una persona real.\n'
          'Informe de laboratorio.\n'
          'Paciente: Persona Ficticia de Prueba. Edad: 30.\n'
          'Medico solicitante: Profesional Ficticio. Matricula: TEST-000.\n'
          'Estudio realizado: hemograma de control.\n'
          'Motivo escrito: control programado. No se consignan diagnosticos, '
          'medicamentos ni codigos CIE-10.\n'
          'Fin de los datos artificiales de prueba.\n',
        ),
      );
      final service = TriageApiService(baseUrl: baseUrl);
      try {
        final result = await service.sendDocument(
          SelectedDocument(
            name: 'aceptacion_edil_sintetica.txt',
            extension: 'txt',
            size: bytes.length,
            type: DocumentType.text,
            bytes: bytes,
          ),
          analyze: true,
        );
        expect(result.isAnalyzed, isTrue);
        expect(result.confianzaClasificacion, isNotNull);
        final recovered = await service.getDocument(result.documentoId!);
        expect(recovered.rawData, result.rawData);
        await _recordEvidence('flutter-analysis.json', {
          'synthetic': true,
          'document_id': result.documentoId,
          'status': result.status,
          'priority': result.prioridad,
          'classification_confidence': result.confianzaClasificacion,
          'requires_human_review': result.requiresHumanReview,
          'get_matches_post': true,
          'gemini_requested': true,
          'api_origin': baseUrl,
        });
      } on TriageApiException catch (error) {
        // Agregado por Edil: si Gemini/OCI fallan, registrar el código y consultar
        // el ID recibido; nunca reenviar automáticamente ni declarar éxito.
        String? recoveredStatus;
        if (error.documentId case final id?) {
          try {
            recoveredStatus = (await service.getDocument(id)).status;
          } on TriageApiException {
            // El fallo original sigue siendo el resultado de esta aceptación.
          }
        }
        await _recordEvidence('flutter-analysis.json', {
          'synthetic': true,
          'document_id': error.documentId,
          'http_status': error.statusCode,
          'recovered_status': recoveredStatus,
          'analysis_completed': false,
          'gemini_requested': true,
          'api_origin': baseUrl,
        });
        rethrow;
      }
    },
    skip: !enabled || !analysisEnabled,
    timeout: const Timeout(Duration(minutes: 3)),
  );
}

// Agregado por Edil: la evidencia contiene solo metadatos técnicos; nunca
// guarda la respuesta clínica completa, claves ni mensajes crudos del SDK.
Future<void> _recordEvidence(String name, Map<String, Object?> evidence) async {
  const configuredDirectory = String.fromEnvironment('MEDIFLOW_EVIDENCE_DIR');
  final directory = await Directory(
    configuredDirectory.isEmpty
        ? '${Directory.systemTemp.path}/MediFlow-full-e2e'
        : configuredDirectory,
  ).create(recursive: true);
  await File('${directory.path}/$name').writeAsString(
    const JsonEncoder.withIndent('  ').convert({
      ...evidence,
      'executed_at_utc': DateTime.now().toUtc().toIso8601String(),
    }),
  );
}
