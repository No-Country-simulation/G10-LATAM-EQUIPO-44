import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mediflow_app/app.dart';
import 'package:mediflow_app/services/file_picker_service.dart';
import 'package:mediflow_app/services/triage_api_service.dart';

import 'helpers/stub_platform_file.dart';
import 'helpers/triage_fixture.dart';

Future<void> press(
  WidgetTester tester,
  String label, {
  bool settle = true,
}) async {
  final finder = find.text(label);
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      160,
      scrollable: find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first,
    );
  }
  await tester.ensureVisible(finder);
  await tester.pump();
  await tester.tap(finder);
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
  }
}

Future<void> ready(
  WidgetTester tester,
  TriageApiService api, {
  FilePickerService? picker,
}) async {
  await tester.pumpWidget(
    MediFlowApp(
      triageApiService: api,
      filePickerService:
          picker ??
          FilePickerService(
            pickFile: () async =>
                StubPlatformFile(name: 'nota.txt', localPath: null),
          ),
    ),
  );
  await press(tester, 'Seleccionar documento');
  await press(tester, 'Buscar archivo');
}

void main() {
  // Agregado por Edil: análisis solo tras autorización explícita para el archivo seleccionado.
  for (final status in ['procesado', 'auditoria_humana']) {
    testWidgets('representa resultado autorizado $status del pipeline', (
      tester,
    ) async {
      await ready(
        tester,
        TriageApiService(
          clientFactory: () => MockClient((request) async {
            expect(request.body, contains('name="analyze"'));
            expect(request.body, contains('true'));
            return http.Response(
              jsonEncode(triageFixture(status: status, priority: 'Urgente')),
              201,
              // Agregado por Edil: FastAPI devuelve JSON UTF-8, también en los mocks.
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }),
        ),
      );
      await press(tester, 'Autorizo enviar este archivo a Google Gemini');
      await press(tester, 'Procesar documento');
      expect(
        find.text(
          status == 'procesado'
              ? 'Extracción completada.'
              : 'Requiere revisión humana.',
        ),
        findsOneWidget,
      );
      expect(find.text('Prioridad: Urgente'), findsOneWidget);
      expect(find.text('Tipo: Receta médica'), findsOneWidget);
    });
  }
  testWidgets('cambiar documento revoca consentimiento Gemini', (tester) async {
    await ready(
      tester,
      TriageApiService(
        clientFactory: () => MockClient(
          (_) async => http.Response(
            '{"status":"recibido","documento_id":"DOC-TEST"}',
            200,
          ),
        ),
      ),
    );
    // Agregado por Edil: el consentimiento puede estar fuera de pantalla en el diseño responsive.
    await tester.scrollUntilVisible(
      find.byType(CheckboxListTile),
      160,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isFalse,
    );
    await press(tester, 'Autorizo enviar este archivo a Google Gemini');
    // Agregado por Edil: el consentimiento puede estar fuera de pantalla en el diseño responsive.
    await tester.scrollUntilVisible(
      find.byType(CheckboxListTile),
      160,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isTrue,
    );
    await press(tester, 'Cambiar archivo');
    // Agregado por Edil: el consentimiento puede estar fuera de pantalla en el diseño responsive.
    await tester.scrollUntilVisible(
      find.byType(CheckboxListTile),
      160,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
      isFalse,
    );
  });
  testWidgets('acepta 201 con contrato anidado de recepción del backend', (
    tester,
  ) async {
    await ready(
      tester,
      TriageApiService(
        clientFactory: () => MockClient((request) async {
          expect(request.url.path, '/api/triage');
          expect(request.method, 'POST');
          return http.Response(
            '{"status":"recibido","documento_id":"DOC-API-201",'
            '"clasificacion":{"tipo_documento":"Pendiente de procesamiento"},'
            '"datos_extraidos":{"paciente":{"nombre":null,"edad":null}},'
            '"decision_enrutamiento":{"requiere_auditoria_humana":false},'
            '"notificacion_generada":null,'
            '"almacenamiento_oci":{"bucket":"recibidos","ruta_objeto":"DOC-API-201.txt","status_backup":"exito"}}',
            201,
          );
        }),
      ),
    );
    await press(tester, 'Procesar documento');
    expect(find.text('Documento: DOC-API-201'), findsOneWidget);
    expect(find.text('Estado: recibido'), findsOneWidget);
    expect(
      find.textContaining('El análisis clínico sigue pendiente.'),
      findsOneWidget,
    );
  });

  testWidgets(
    'procesando bloquea acciones y evita doble envío; éxito no reenvía',
    (tester) async {
      final response = Completer<http.Response>();
      var calls = 0;
      await ready(
        tester,
        TriageApiService(
          clientFactory: () => MockClient((_) {
            calls++;
            return response.future;
          }),
        ),
      );
      // Agregado por Edil: el consentimiento hace más larga la lista; el botón
      // puede no haberse construido todavía. Se conservan todas las aserciones.
      if (find.text('Procesar documento').evaluate().isEmpty) {
        await tester.scrollUntilVisible(
          find.text('Procesar documento'),
          160,
          scrollable: find
              .descendant(
                of: find.byType(ListView),
                matching: find.byType(Scrollable),
              )
              .first,
        );
      }
      await tester.ensureVisible(find.text('Procesar documento'));
      await tester.pump();
      final send = tester
          .widget<OutlinedButton>(
            find.widgetWithText(OutlinedButton, 'Procesar documento'),
          )
          .onPressed!;
      send();
      send();
      await tester.pump();
      expect(calls, 1);
      expect(find.text('Procesando documento...'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Procesar documento'),
            )
            .onPressed,
        isNull,
      );
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Cambiar archivo'),
            )
            .onPressed,
        isNull,
      );
      expect(
        tester
            .widget<TextButton>(
              find.widgetWithText(TextButton, 'Quitar archivo'),
            )
            .onPressed,
        isNull,
      );
      response.complete(
        http.Response('{"status":"recibido","documento_id":"DOC-2"}', 200),
      );
      await tester.pumpAndSettle();
      expect(find.text('Documento recibido correctamente.'), findsOneWidget);
      expect(find.text('Estado: recibido'), findsOneWidget);
      expect(find.text('Documento: DOC-2'), findsOneWidget);
      expect(find.text('Procesar documento'), findsNothing);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(calls, 1);
      await press(tester, 'Quitar archivo');
      expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
      expect(find.text('Documento recibido correctamente.'), findsNothing);
    },
  );

  for (final scenario in [
    '400',
    '500',
    'sin conexión',
    'timeout',
    'JSON inválido',
  ]) {
    testWidgets(
      '$scenario muestra error y permite reintentar sin perder archivo',
      (tester) async {
        var calls = 0;
        final lateResponse = Completer<http.Response>();
        final api = TriageApiService(
          clientFactory: () => MockClient((_) async {
            calls++;
            if (calls > 1) {
              return http.Response(
                '{"status":"recibido","documento_id":"DOC-RETRY"}',
                200,
              );
            }
            // Agregado por Edil: HTTP 200 sin contrato también debe mostrar error.
            if (scenario == 'JSON inválido') {
              return http.Response('{}', 200);
            }
            if (scenario == 'sin conexión') {
              throw const SocketException('no network');
            }
            if (scenario == 'timeout') return lateResponse.future;
            return http.Response(
              'detalle técnico privado',
              int.parse(scenario),
            );
          }),
        );
        await ready(tester, api);
        await press(
          tester,
          'Procesar documento',
          settle: scenario != 'timeout',
        );
        if (scenario == 'timeout') {
          await tester.pump(const Duration(seconds: 31));
          await tester.pumpAndSettle();
        }
        final message = switch (scenario) {
          'JSON inválido' => 'El servidor devolvió una respuesta inválida.',
          '400' => 'El servidor rechazó el documento.',
          '500' => 'El servidor no está disponible. Inténtalo más tarde.',
          'sin conexión' => 'No se pudo conectar con el servidor.',
          _ => 'El servidor tardó demasiado en responder.',
        };
        expect(find.text(message), findsOneWidget);
        if (scenario == '500') {
          expect(find.text('Código HTTP: 500'), findsOneWidget);
        }
        expect(find.text('detalle técnico privado'), findsNothing);
        expect(find.text('nota.txt'), findsOneWidget);
        await press(tester, 'Reintentar');
        expect(calls, 2);
        expect(find.text('Documento recibido correctamente.'), findsOneWidget);
        expect(find.text(message), findsNothing);
        lateResponse.complete(
          http.Response('{"status":"recibido","documento_id":"DOC-TEST"}', 200),
        );
      },
    );
  }

  testWidgets(
    'cancelar conserva resultado; cambiar archivo reinicia el estado',
    (tester) async {
      var pickCalls = 0;
      await ready(
        tester,
        TriageApiService(
          clientFactory: () => MockClient(
            (_) async => http.Response(
              '{"status":"recibido","documento_id":"DOC-TEST"}',
              200,
            ),
          ),
        ),
        picker: FilePickerService(
          pickFile: () async {
            pickCalls++;
            if (pickCalls == 2) return null;
            return StubPlatformFile(
              name: pickCalls == 1 ? 'nota.txt' : 'imagen.png',
              localPath: null,
            );
          },
        ),
      );
      await press(tester, 'Procesar documento');
      await press(tester, 'Cambiar archivo');
      expect(find.text('Documento recibido correctamente.'), findsOneWidget);
      await press(tester, 'Cambiar archivo');
      expect(find.text('imagen.png'), findsOneWidget);
      expect(find.text('Documento recibido correctamente.'), findsNothing);
      expect(find.text('Procesar documento'), findsOneWidget);
    },
  );

  testWidgets('salir durante envío no actualiza una pantalla destruida', (
    tester,
  ) async {
    final response = Completer<http.Response>();
    await ready(
      tester,
      TriageApiService(clientFactory: () => MockClient((_) => response.future)),
    );
    await press(tester, 'Procesar documento', settle: false);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    response.complete(
      http.Response('{"status":"recibido","documento_id":"DOC-TEST"}', 200),
    );
    await tester.pumpAndSettle();
    expect(find.text('MediFlow'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
