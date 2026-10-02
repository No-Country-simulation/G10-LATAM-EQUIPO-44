import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mediflow_app/config/api_config.dart';
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/models/triage_result.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

SelectedDocument document({
  String? path,
  Uint8List? bytes,
  String extension = 'txt',
}) => SelectedDocument(
  name: 'prueba.$extension',
  extension: extension,
  path: path,
  bytes: bytes,
  size: bytes?.length ?? 0,
  type: DocumentType.text,
);

TypeMatcher<TriageApiException> failure(String message) =>
    isA<TriageApiException>().having(
      (error) => error.message,
      'mensaje',
      message,
    );

class TrackingClient extends http.BaseClient {
  TrackingClient(this.onSend);
  final Future<http.StreamedResponse> Function(http.BaseRequest) onSend;
  bool closed = false;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      onSend(request);

  @override
  void close() => closed = true;
}

void main() {
  final payload = Uint8List.fromList(
    utf8.encode('Documento sintetico de prueba'),
  );

  test(
    'envía POST multipart con nombre, MIME y contenido desde bytes',
    () async {
      var calls = 0;
      final service = TriageApiService(
        baseUrl: 'https://backend.example.test/',
        clientFactory: () => MockClient((request) async {
          calls++;
          expect(request.method, 'POST');
          expect(
            request.url.toString(),
            'https://backend.example.test/api/triage',
          );
          expect(
            request.headers['content-type'],
            startsWith('multipart/form-data; boundary='),
          );
          expect(request.headers['accept'], 'application/json');
          expect(request.followRedirects, isFalse);
          expect(request.body, contains('name="${ApiConfig.fileFieldName}"'));
          expect(request.body, contains('filename="prueba.txt"'));
          expect(request.body, contains('content-type: text/plain'));
          expect(request.body, contains(utf8.decode(payload)));
          return http.Response.bytes(
            utf8.encode(
              jsonEncode({
                'status': 'recibido',
                'documento_id': 'DOC-1',
                'message': 'Recepción correcta',
                'futuro': {'campo': true},
              }),
            ),
            201,
          );
        }),
      );
      final result = await service.sendDocument(document(bytes: payload));
      expect(calls, 1);
      expect(result.status, 'recibido');
      expect(result.documentoId, 'DOC-1');
      expect(result.message, 'Recepción correcta');
      expect(result.rawData['futuro'], {'campo': true});
    },
  );

  test('envía el archivo desde disco sin volver a abrir el picker', () async {
    final parent = await Directory(
      'build/test-fixtures',
    ).create(recursive: true);
    final folder = await parent.createTemp('triage_');
    addTearDown(() => folder.delete(recursive: true));
    final file = await File('${folder.path}/prueba.txt').writeAsBytes(payload);
    final service = TriageApiService(
      clientFactory: () => MockClient((request) async {
        expect(request.body, contains(utf8.decode(payload)));
        return http.Response('{}', 200);
      }),
    );
    await service.sendDocument(document(path: file.absolute.path));
  });

  for (final entry in {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'txt': 'text/plain',
  }.entries) {
    test('usa MIME correcto para ${entry.key}', () async {
      final service = TriageApiService(
        clientFactory: () => MockClient((request) async {
          expect(request.body, contains('content-type: ${entry.value}'));
          return http.Response('{}', 202);
        }),
      );
      await service.sendDocument(
        document(bytes: payload, extension: entry.key),
      );
    });
  }

  for (final code in [200, 201, 202, 204]) {
    test('acepta HTTP $code sin exigir campos clínicos', () async {
      final service = TriageApiService(
        clientFactory: () => MockClient(
          (_) async => http.Response(code == 204 ? '' : '{}', code),
        ),
      );
      final result = await service.sendDocument(document(bytes: payload));
      expect(result.status, isNull);
      expect(result.rawData, isEmpty);
    });
  }

  for (final entry in {
    400: 'El servidor rechazó el documento.',
    401: 'No tienes autorización para enviar documentos al servidor.',
    403: 'No tienes autorización para enviar documentos al servidor.',
    404: 'No se encontró el servicio de procesamiento.',
    413: 'El archivo supera el tamaño permitido por el servidor.',
    422: 'El servidor rechazó el documento.',
    429: 'El servidor recibió demasiadas solicitudes. Inténtalo más tarde.',
    500: 'El servidor no está disponible. Inténtalo más tarde.',
    503: 'El servidor no está disponible. Inténtalo más tarde.',
    504: 'El servidor tardó demasiado en responder.',
    307: 'El servidor no pudo completar la solicitud.',
  }.entries) {
    test(
      'HTTP ${entry.key} se traduce sin exponer el cuerpo de error',
      () async {
        final service = TriageApiService(
          clientFactory: () => MockClient(
            (_) async =>
                http.Response('contenido que no debe mostrarse', entry.key),
          ),
        );
        await expectLater(
          service.sendDocument(document(bytes: payload)),
          throwsA(
            failure(
              entry.value,
            ).having((e) => e.statusCode, 'código', entry.key),
          ),
        );
      },
    );
  }

  for (final body in ['no es JSON', '[]', 'null', '"texto"', '']) {
    test('rechaza respuesta inválida: $body', () async {
      final service = TriageApiService(
        clientFactory: () => MockClient((_) async => http.Response(body, 200)),
      );
      await expectLater(
        service.sendDocument(document(bytes: payload)),
        throwsA(failure('El servidor devolvió una respuesta inválida.')),
      );
    });
  }

  for (final path in [
    null,
    '',
    '\u0000',
    'build/no-existe-sprint-2.txt',
    'build',
  ]) {
    test('no envía una ruta no disponible: $path', () async {
      var calls = 0;
      final service = TriageApiService(
        clientFactory: () => MockClient((_) async {
          calls++;
          return http.Response('{}', 200);
        }),
      );
      await expectLater(
        service.sendDocument(document(path: path)),
        throwsA(failure('El archivo seleccionado ya no está disponible.')),
      );
      expect(calls, 0);
    });
  }

  for (final error in [
    const SocketException('detalle privado'),
    http.ClientException('detalle privado'),
  ]) {
    test('maneja desconexión ${error.runtimeType}', () async {
      final service = TriageApiService(
        clientFactory: () => MockClient((_) async => throw error),
      );
      await expectLater(
        service.sendDocument(document(bytes: payload)),
        throwsA(failure('No se pudo conectar con el servidor.')),
      );
    });
  }

  test('maneja errores inesperados sin mostrar información técnica', () async {
    final service = TriageApiService(
      clientFactory: () => throw StateError('privado'),
    );
    await expectLater(
      service.sendDocument(document(bytes: payload)),
      throwsA(failure('Ocurrió un error al procesar el documento.')),
    );
  });

  test(
    'timeout al esperar cabeceras cierra transporte y permite reintentar',
    () async {
      final pending = Completer<http.StreamedResponse>();
      final client = TrackingClient((_) => pending.future);
      var count = 0;
      final service = TriageApiService(
        timeout: const Duration(milliseconds: 30),
        clientFactory: () => count++ == 0
            ? client
            : MockClient((_) async => http.Response('{}', 200)),
      );
      await expectLater(
        service.sendDocument(document(bytes: payload)),
        throwsA(failure('El servidor tardó demasiado en responder.')),
      );
      expect(client.closed, isTrue);
      pending.complete(
        http.StreamedResponse(Stream.value(utf8.encode('{}')), 200),
      );
      expect(
        await service.sendDocument(document(bytes: payload)),
        isA<TriageResult>(),
      );
    },
  );

  test('timeout también cubre cuerpo de respuesta que nunca termina', () async {
    final stream = StreamController<List<int>>();
    final client = TrackingClient(
      (_) async => http.StreamedResponse(stream.stream, 200),
    );
    final service = TriageApiService(
      clientFactory: () => client,
      timeout: const Duration(milliseconds: 30),
    );
    await expectLater(
      service.sendDocument(document(bytes: payload)),
      throwsA(failure('El servidor tardó demasiado en responder.')),
    );
    expect(client.closed, isTrue);
    await stream.close();
  });

  test('cancelar cierra transporte activo', () async {
    final pending = Completer<http.StreamedResponse>();
    final started = Completer<void>();
    final client = TrackingClient((_) {
      started.complete();
      return pending.future;
    });
    final service = TriageApiService(clientFactory: () => client);
    final future = service.sendDocument(document(bytes: payload));
    await started.future;
    service.cancelPendingRequests();
    expect(client.closed, isTrue);
    pending.completeError(http.ClientException('closed'));
    await expectLater(future, throwsA(isA<TriageApiException>()));
  });
}
