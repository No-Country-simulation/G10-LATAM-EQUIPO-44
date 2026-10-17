import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mediflow_app/app.dart';
import 'package:mediflow_app/services/file_picker_service.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

import 'helpers/stub_platform_file.dart';
import 'helpers/triage_fixture.dart';

// Agregado por Edil: verificamos transporte y decisiones de la pantalla con un
// servidor simulado. Estas pruebas no llaman a OCI, Gemini ni a una cámara real.
Future<void> _press(WidgetTester tester, String label) async {
  final finder = find.text(label);
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      200,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(finder);
  await tester.pump();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> _ready(
  WidgetTester tester,
  Future<http.Response> Function(http.Request) handler, {
  FilePickerService? picker,
}) async {
  tester.view.physicalSize = const Size(1000, 2200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MediFlowApp(
      triageApiService: TriageApiService(
        baseUrl: 'http://localhost:8000',
        clientFactory: () => MockClient(handler),
      ),
      filePickerService:
          picker ??
          FilePickerService(
            pickFile: () async =>
                StubPlatformFile(name: 'sintetico.txt', localPath: null),
          ),
    ),
  );
  await _press(tester, 'Seleccionar documento');
  await _press(tester, 'Buscar archivo');
}

http.Response _json(Object payload, int status, {String? documentId}) =>
    http.Response(
      jsonEncode(payload),
      status,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'X-Document-Id': ?documentId,
      },
    );

void main() {
  testWidgets('POST fallido con ID permite GET sin otro envío', (tester) async {
    var postCalls = 0;
    var getCalls = 0;
    await _ready(tester, (request) async {
      if (request.method == 'POST') {
        postCalls++;
        return _json(
          {'detail': 'El servicio de análisis no está disponible.'},
          503,
          documentId: 'DOC-RECOVERY',
        );
      }
      getCalls++;
      expect(request.url.path, '/api/documents/DOC-RECOVERY');
      return _json({'status': 'recibido', 'documento_id': 'DOC-RECOVERY'}, 200);
    });
    await _press(tester, 'Autorizo enviar este archivo a Google Gemini');
    await _press(tester, 'Procesar documento');
    expect(find.text('Documento: DOC-RECOVERY'), findsOneWidget);
    expect(find.text('Reintentar'), findsNothing);
    expect(find.byType(CheckboxListTile), findsNothing);
    await _press(tester, 'Consultar documento');
    expect(find.text('Estado: recibido'), findsOneWidget);
    expect(
      find.textContaining('El análisis clínico sigue pendiente.'),
      findsOneWidget,
    );
    expect(find.text('Extracción completada.'), findsNothing);
    expect(find.text('Actualizar estado'), findsOneWidget);
    expect(postCalls, 1);
    expect(getCalls, 1);
  });

  testWidgets('fallar al actualizar conserva resultado y urgencia anteriores', (
    tester,
  ) async {
    var posts = 0;
    var gets = 0;
    await _ready(tester, (request) async {
      if (request.method == 'POST') {
        posts++;
        return _json(triageFixture(priority: 'Urgente'), 201);
      }
      gets++;
      return _json({'detail': 'No disponible'}, 500);
    });
    await _press(tester, 'Procesar documento');
    await _press(tester, 'Actualizar estado');
    expect(find.text('No se pudo actualizar el estado'), findsOneWidget);
    expect(find.text('Extracción completada.'), findsOneWidget);
    expect(find.byKey(const Key('urgent-alert')), findsOneWidget);
    expect(find.text('Documento: DOC-PIPELINE'), findsOneWidget);
    expect(find.text('Reintentar'), findsNothing);
    expect(posts, 1);
    expect(gets, 1);
  });

  testWidgets('GET puede mostrar el resultado posterior sin repetir POST', (
    tester,
  ) async {
    var posts = 0;
    await _ready(tester, (request) async {
      if (request.method == 'POST') {
        posts++;
        return _json({
          'status': 'recibido',
          'documento_id': 'DOC-PIPELINE',
        }, 201);
      }
      return _json(
        triageFixture(status: 'auditoria_humana', priority: 'Urgente'),
        200,
      );
    });
    await _press(tester, 'Procesar documento');
    expect(find.text('Estado: recibido'), findsOneWidget);
    await _press(tester, 'Actualizar estado');
    expect(find.text('Requiere revisión humana.'), findsOneWidget);
    expect(find.text('Estado: recibido'), findsNothing);
    expect(find.byKey(const Key('urgent-alert')), findsOneWidget);
    expect(posts, 1);
  });

  testWidgets('timeout sin ID exige confirmar un posible envío duplicado', (
    tester,
  ) async {
    var posts = 0;
    await _ready(tester, (request) async {
      expect(request.method, 'POST');
      posts++;
      if (posts == 1) throw TimeoutException('simulado');
      return _json({'status': 'recibido', 'documento_id': 'DOC-RETRY'}, 201);
    });
    await _press(tester, 'Procesar documento');
    expect(find.text('No se pudo confirmar la recepción'), findsOneWidget);
    await _press(tester, 'Reintentar');
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.textContaining('documento duplicado'), findsOneWidget);
    expect(posts, 1);
    await _press(tester, 'Cancelar');
    expect(posts, 1);
    expect(find.text('sintetico.txt'), findsOneWidget);
    await _press(tester, 'Reintentar');
    await _press(tester, 'Enviar de nuevo');
    expect(posts, 2);
    expect(find.text('Documento: DOC-RETRY'), findsOneWidget);
    expect(find.text('No se pudo confirmar la recepción'), findsNothing);
  });

  testWidgets('GET fallido conserva ID y nunca ofrece otro POST', (
    tester,
  ) async {
    var posts = 0;
    await _ready(tester, (request) async {
      if (request.method == 'POST') {
        posts++;
        return _json({}, 503, documentId: 'DOC-RECOVERY');
      }
      return _json({'detail': 'No encontrado'}, 404);
    });
    await _press(tester, 'Procesar documento');
    await _press(tester, 'Consultar documento');
    expect(find.text('Documento: DOC-RECOVERY'), findsOneWidget);
    expect(find.text('No se pudo actualizar el estado'), findsOneWidget);
    expect(find.text('Consultar documento'), findsOneWidget);
    expect(find.text('Reintentar'), findsNothing);
    expect(posts, 1);
  });

  testWidgets('cambiar archivo reinicia ID y consentimiento', (tester) async {
    await _ready(tester, (request) async {
      return _json({}, 503, documentId: 'DOC-RECOVERY');
    });
    await _press(tester, 'Autorizo enviar este archivo a Google Gemini');
    await _press(tester, 'Procesar documento');
    expect(find.text('Consultar documento'), findsOneWidget);
    await _press(tester, 'Cambiar archivo');
    expect(find.text('Documento: DOC-RECOVERY'), findsNothing);
    expect(find.text('Consultar documento'), findsNothing);
    expect(find.text('Procesar documento'), findsOneWidget);
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isFalse,
    );
  });

  for (final invalid in [
    (0, 'El archivo está vacío. Selecciona otro documento.'),
    (
      FilePickerService.maxFileBytes + 1,
      'El archivo supera el tamaño máximo de 10 MB.',
    ),
  ]) {
    testWidgets('selector informa límite local ${invalid.$1}', (tester) async {
      var posts = 0;
      await _ready(
        tester,
        (request) async {
          posts++;
          return _json({}, 500);
        },
        picker: FilePickerService(
          pickFile: () async => StubPlatformFile(
            name: 'sintetico.txt',
            localPath: null,
            bytes: invalid.$1,
          ),
        ),
      );
      expect(find.text(invalid.$2), findsOneWidget);
      expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
      expect(posts, 0);
    });
  }
}
