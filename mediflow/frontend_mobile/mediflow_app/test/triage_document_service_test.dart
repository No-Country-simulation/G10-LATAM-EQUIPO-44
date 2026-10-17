// Agregado por Edil: recuperar el mismo ID sin subir de nuevo el documento.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mediflow_app/config/api_config.dart';
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

import 'helpers/triage_fixture.dart';

SelectedDocument _document(Uint8List bytes) => SelectedDocument(
  name: 'nota.txt',
  extension: 'txt',
  size: 1,
  type: DocumentType.text,
  bytes: bytes,
);

Map<String, dynamic> _fixture(String id) =>
    triageFixture()..['documento_id'] = id;

void main() {
  test(
    'GET conserva prefijo y no envía archivo ni orden de análisis',
    () async {
      final service = TriageApiService(
        baseUrl: 'https://backend.example.test/prefix/',
        clientFactory: () => MockClient((request) async {
          expect(request.method, 'GET');
          expect(request.url.path, '/prefix/api/documents/DOC-TEST');
          expect(request.body, isEmpty);
          expect(request.url.query, isEmpty);
          expect(request.followRedirects, isFalse);
          return http.Response(
            jsonEncode(_fixture('DOC-TEST')),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      expect((await service.getDocument('DOC-TEST')).documentoId, 'DOC-TEST');
    },
  );

  for (final id in ['../otro', 'DOC/OTRO', '', 'https://otro.test', 'DOC\nX']) {
    test('GET rechaza ID inseguro antes de abrir cliente: $id', () async {
      var opened = false;
      final service = TriageApiService(
        clientFactory: () {
          opened = true;
          throw StateError('No debe abrir cliente');
        },
      );
      await expectLater(
        service.getDocument(id),
        throwsA(isA<TriageApiException>()),
      );
      expect(opened, isFalse);
    });
  }

  test('GET rechaza una respuesta de otro documento', () async {
    final service = TriageApiService(
      clientFactory: () => MockClient(
        (_) async => http.Response(
          jsonEncode(_fixture('OTRO')),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      ),
    );
    await expectLater(
      service.getDocument('DOC-TEST'),
      throwsA(
        isA<TriageApiException>().having(
          (e) => e.message,
          'mensaje',
          contains('respuesta inválida'),
        ),
      ),
    );
  });

  test('POST fallido conserva cabecera ID válida y estado HTTP', () async {
    final service = TriageApiService(
      clientFactory: () => MockClient(
        (_) async =>
            http.Response('{}', 503, headers: {'X-Document-ID': 'DOC-TEST'}),
      ),
    );
    await expectLater(
      service.sendDocument(_document(Uint8List.fromList([65]))),
      throwsA(
        isA<TriageApiException>()
            .having((e) => e.documentId, 'ID', 'DOC-TEST')
            .having((e) => e.statusCode, 'HTTP', 503)
            .having(
              (e) => e.requestMayHaveBeenReceived,
              'recepción posible',
              isTrue,
            ),
      ),
    );
  });

  test('POST ignora cabecera ID insegura', () async {
    final service = TriageApiService(
      clientFactory: () => MockClient(
        (_) async =>
            http.Response('{}', 503, headers: {'x-document-id': '../secret'}),
      ),
    );
    await expectLater(
      service.sendDocument(_document(Uint8List.fromList([65]))),
      throwsA(
        isA<TriageApiException>().having((e) => e.documentId, 'ID', isNull),
      ),
    );
  });

  test('GET 404 conserva ID y no muestra detalles privados', () async {
    final service = TriageApiService(
      clientFactory: () => MockClient(
        (_) async => http.Response('{"detail":"dato privado"}', 404),
      ),
    );
    await expectLater(
      service.getDocument('DOC-TEST'),
      throwsA(
        isA<TriageApiException>()
            .having((e) => e.documentId, 'ID', 'DOC-TEST')
            .having((e) => e.message, 'mensaje', isNot(contains('privado'))),
      ),
    );
  });

  test('GET timeout cierra transporte y no reintenta', () async {
    var calls = 0;
    final client = _SlowClient(() => calls++);
    final service = TriageApiService(
      timeout: const Duration(milliseconds: 10),
      clientFactory: () => client,
    );
    await expectLater(
      service.getDocument('DOC-TEST'),
      throwsA(isA<TriageApiException>()),
    );
    expect(client.closed, isTrue);
    expect(calls, 1);
  });

  test(
    'POST conserva ID si llegan cabeceras pero el cuerpo agota el tiempo',
    () async {
      final body = StreamController<List<int>>();
      addTearDown(() => body.close());
      final client = _HeaderClient(body.stream);
      final service = TriageApiService(
        timeout: const Duration(milliseconds: 20),
        clientFactory: () => client,
      );
      await expectLater(
        service.sendDocument(_document(Uint8List.fromList([65]))),
        throwsA(
          isA<TriageApiException>()
              .having(
                (e) => e.documentId,
                'ID confirmado en cabecera',
                'DOC-HEADER',
              )
              .having(
                (e) => e.requestMayHaveBeenReceived,
                'recepción posible',
                isTrue,
              ),
        ),
      );
      expect(client.closed, isTrue);
    },
  );

  // Agregado por Edil: estos errores tampoco deben habilitar otro POST silencioso.
  test('POST conserva ID ante error inesperado del cuerpo', () async {
    final client = _HeaderClient(
      Stream<List<int>>.error(StateError('detalle privado')),
    );
    final service = TriageApiService(clientFactory: () => client);
    await expectLater(
      service.sendDocument(_document(Uint8List.fromList([65]))),
      throwsA(
        isA<TriageApiException>()
            .having((e) => e.documentId, 'ID confirmado', 'DOC-HEADER')
            .having(
              (e) => e.requestMayHaveBeenReceived,
              'recepción posible',
              isTrue,
            )
            .having(
              (e) => e.message,
              'mensaje seguro',
              isNot(contains('privado')),
            ),
      ),
    );
    expect(client.closed, isTrue);
  });

  test('HTTP 408 sin ID requiere confirmar antes de repetir POST', () async {
    final service = TriageApiService(
      clientFactory: () => MockClient((_) async => http.Response('{}', 408)),
    );
    await expectLater(
      service.sendDocument(_document(Uint8List.fromList([65]))),
      throwsA(
        isA<TriageApiException>()
            .having((e) => e.documentId, 'sin ID', isNull)
            .having(
              (e) => e.requestMayHaveBeenReceived,
              'recepción incierta',
              isTrue,
            ),
      ),
    );
  });

  for (final size in [0, ApiConfig.maxFileBytes + 1]) {
    test(
      'POST valida tamaño real $size sin enviar aunque metadata diga 1',
      () async {
        var calls = 0;
        final service = TriageApiService(
          clientFactory: () => MockClient((_) async {
            calls++;
            return http.Response('{}', 201);
          }),
        );
        await expectLater(
          service.sendDocument(_document(Uint8List(size))),
          throwsA(
            isA<TriageApiException>().having(
              (e) => e.requestMayHaveBeenReceived,
              'no enviado',
              isFalse,
            ),
          ),
        );
        expect(calls, 0);
      },
    );
  }
}

class _SlowClient extends http.BaseClient {
  _SlowClient(this.onSend);
  final void Function() onSend;
  bool closed = false;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    onSend();
    return Completer<http.StreamedResponse>().future;
  }

  @override
  void close() => closed = true;
}

class _HeaderClient extends http.BaseClient {
  _HeaderClient(this.body);
  final Stream<List<int>> body;
  bool closed = false;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async =>
      http.StreamedResponse(
        body,
        503,
        headers: {'x-document-id': 'DOC-HEADER'},
      );
  @override
  void close() => closed = true;
}
