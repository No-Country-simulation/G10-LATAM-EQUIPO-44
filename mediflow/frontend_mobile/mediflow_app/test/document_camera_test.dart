import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mediflow_app/app.dart';
import 'package:mediflow_app/services/document_camera_service.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

// Agregado por Edil: imagen sintetica, sin documentos clinicos ni camara real.
final photoBytes = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
);
XFile photo() => XFile.fromData(photoBytes, name: 'foto.png');
DocumentCameraService camera({
  Future<XFile?> Function()? capture,
  Future<List<XFile>> Function()? recover,
  bool supported = true,
}) => DocumentCameraService(
  supported: supported,
  capture: capture ?? () async => photo(),
  recover: recover ?? () async => [],
);

Future<void> press(WidgetTester tester, String text) async {
  final target = find.text(text);
  if (target.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      target,
      150,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(target);
  await tester.pump();
  // Agregado por Edil: el decodificador de imagen usa el motor nativo, no el reloj simulado.
  await tester.runAsync(() async {
    await tester.tap(target);
    for (var frame = 0; frame < 4; frame++) {
      await tester.pump();
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
  });
  await tester.pumpAndSettle();
}

Future<void> open(
  WidgetTester tester,
  DocumentCameraService service, {
  TriageApiService? api,
}) async {
  await tester.pumpWidget(
    MediFlowApp(cameraService: service, triageApiService: api),
  );
  await press(tester, 'Seleccionar documento');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('captura local valida y nombre neutro sin ruta privada', () async {
    final result = await camera().captureDocument();
    expect(result!.extension, 'png');
    expect(result.bytes, photoBytes);
    expect(result.path, isNull);
    expect(result.name, startsWith('documento_'));
  });
  test('cancelar la camara devuelve null', () async {
    expect(await camera(capture: () async => null).captureDocument(), isNull);
  });
  test('plataforma no soportada no invoca camara ni recuperacion', () async {
    final service = camera(
      supported: false,
      capture: () => throw StateError('no invocar'),
      recover: () => throw StateError('no invocar'),
    );
    expect(await service.captureDocument(), isNull);
    expect(await service.recoverDocument(), isNull);
  });
  test('error de permisos no expone detalles del plugin', () async {
    final service = camera(
      capture: () async => throw PlatformException(
        code: 'camera_access_denied',
        message: 'detalle privado',
      ),
    );
    await expectLater(
      service.captureDocument(),
      throwsA(
        isA<DocumentCameraException>().having(
          (e) => e.message,
          'mensaje',
          isNot(contains('privado')),
        ),
      ),
    );
  });
  for (final data in [
    Uint8List(0),
    Uint8List(DocumentCameraService.maxBytes + 1),
    Uint8List.fromList([1, 2, 3]),
  ]) {
    test('rechaza captura vacia, grande o con formato incorrecto', () async {
      await expectLater(
        camera(capture: () async => XFile.fromData(data)).captureDocument(),
        throwsA(isA<DocumentCameraException>()),
      );
    });
  }
  test('recupera foto pendiente local', () async {
    final result = await camera(
      recover: () async => [photo()],
    ).recoverDocument();
    expect(result!.bytes, photoBytes);
  });
  testWidgets(
    'confirmar no envia; procesar usa multipart sin consentimiento automatico',
    (tester) async {
      var calls = 0;
      await open(
        tester,
        camera(),
        api: TriageApiService(
          clientFactory: () => MockClient((request) async {
            calls++;
            // El multipart contiene bytes de imagen, no un documento UTF-8.
            final multipart = latin1.decode(request.bodyBytes);
            expect(multipart, contains('content-type: image/png'));
            expect(multipart, contains('false'));
            return http.Response(
              '{"status":"recibido","documento_id":"DOC-PHOTO"}',
              201,
            );
          }),
        ),
      );
      await press(tester, 'Tomar foto');
      expect(find.text('Revisar foto'), findsOneWidget);
      expect(calls, 0);
      await press(tester, 'Usar esta foto');
      expect(find.text('Revisar foto'), findsNothing);
      expect(calls, 0);
      await tester.scrollUntilVisible(
        find.byType(CheckboxListTile),
        150,
        scrollable: find.byType(Scrollable).first,
      );
      expect(
        tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
        isFalse,
      );
      await press(tester, 'Procesar documento');
      expect(calls, 1);
      await tester.scrollUntilVisible(
        find.text('Documento: DOC-PHOTO'),
        -120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Documento: DOC-PHOTO'), findsOneWidget);
    },
  );
  testWidgets('cancelar revision conserva seleccion anterior', (tester) async {
    await open(tester, camera());
    await press(tester, 'Tomar foto');
    await press(tester, 'Usar esta foto');
    await press(tester, 'Autorizo enviar este archivo a Google Gemini');
    await press(tester, 'Tomar foto');
    await press(tester, 'Cancelar');
    await tester.scrollUntilVisible(
      find.byType(CheckboxListTile),
      150,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isTrue,
    );
    expect(find.text('Ningún archivo seleccionado'), findsNothing);
  });
  testWidgets('repetir captura y confirmar revoca consentimiento anterior', (
    tester,
  ) async {
    var captures = 0;
    await open(
      tester,
      camera(
        capture: () async {
          captures++;
          return photo();
        },
      ),
    );
    await press(tester, 'Tomar foto');
    await press(tester, 'Usar esta foto');
    await press(tester, 'Autorizo enviar este archivo a Google Gemini');
    await press(tester, 'Tomar foto');
    await press(tester, 'Repetir foto');
    await press(tester, 'Usar esta foto');
    expect(captures, 3);
    await tester.scrollUntilVisible(
      find.byType(CheckboxListTile),
      150,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isFalse,
    );
  });
  testWidgets('foto recuperada requiere revision y confirmacion', (
    tester,
  ) async {
    await open(tester, camera(recover: () async => [photo()]));
    expect(find.text('Revisar foto'), findsOneWidget);
    await press(tester, 'Cancelar');
    expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
  });
  testWidgets('Windows conserva selector sin boton de camara', (tester) async {
    await open(tester, camera(supported: false));
    expect(find.text('Tomar foto'), findsNothing);
    expect(find.text('Buscar archivo'), findsOneWidget);
  });
  testWidgets('no abre otra captura mientras espera la camara', (tester) async {
    final pending = Completer<XFile?>();
    var captures = 0;
    await open(
      tester,
      camera(
        capture: () {
          captures++;
          return pending.future;
        },
      ),
    );
    await tester.tap(find.text('Tomar foto'));
    await tester.pump();
    final button = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Tomar foto'),
    );
    expect(button.onPressed, isNull);
    pending.complete(null);
    await tester.pumpAndSettle();
    expect(captures, 1);
  });
}
