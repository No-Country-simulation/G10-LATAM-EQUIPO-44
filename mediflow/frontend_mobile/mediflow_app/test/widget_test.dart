import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/app.dart';
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/services/file_picker_service.dart';
import 'package:mediflow_app/widgets/selected_file_card.dart';

import 'helpers/stub_platform_file.dart';

Future<void> tapText(WidgetTester tester, String text) async {
  final finder = find.text(text);
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      180,
      scrollable: find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first,
    );
  }
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> openSelection(
  WidgetTester tester,
  FilePickerService service,
) async {
  await tester.pumpWidget(MediFlowApp(filePickerService: service));
  await tapText(tester, 'Seleccionar documento');
}

void main() {
  testWidgets('navega, selecciona, conserva, reemplaza, quita y vuelve', (
    tester,
  ) async {
    final responses = <PlatformFile?>[
      StubPlatformFile(name: 'informe.pdf'),
      null,
      StubPlatformFile(name: 'no_permitido.exe'),
      StubPlatformFile(name: 'imagen.png', bytes: 1024, localPath: null),
    ];
    final service = FilePickerService(
      pickFile: () async => responses.removeAt(0),
    );
    await tester.pumpWidget(MediFlowApp(filePickerService: service));
    expect(find.text('MediFlow'), findsOneWidget);
    expect(find.text('Triaje de documentos clínicos'), findsOneWidget);
    await tapText(tester, 'Seleccionar documento');
    expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
    expect(find.text('Continuar'), findsNothing);

    await tapText(tester, 'Buscar archivo');
    expect(find.text('informe.pdf'), findsOneWidget);
    expect(find.text('Tipo: PDF'), findsOneWidget);
    expect(find.text('Extensión: .pdf'), findsOneWidget);
    expect(find.text('Tamaño: 1.5 KB'), findsOneWidget);
    expect(find.text('Ruta disponible'), findsOneWidget);

    await tapText(tester, 'Cambiar archivo');
    expect(find.text('informe.pdf'), findsOneWidget);
    expect(find.byType(SnackBar), findsNothing);

    await tapText(tester, 'Cambiar archivo');
    expect(find.text('Formato de archivo no permitido.'), findsOneWidget);
    expect(find.text('informe.pdf'), findsOneWidget);
    await tester.pumpAndSettle(const Duration(seconds: 5));

    await tapText(tester, 'Cambiar archivo');
    expect(find.text('informe.pdf'), findsNothing);
    expect(find.text('imagen.png'), findsOneWidget);
    expect(find.text('Tipo: Imagen'), findsOneWidget);
    expect(find.text('Ruta disponible'), findsNothing);

    await tapText(tester, 'Continuar');
    expect(
      find.text(
        'Documento listo para procesar. La integración estará disponible en el Sprint 2.',
      ),
      findsOneWidget,
    );
    await tester.pumpAndSettle(const Duration(seconds: 5));
    await tapText(tester, 'Quitar archivo');
    expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
    expect(find.byType(SelectedFileCard), findsNothing);
    expect(find.text('Continuar'), findsNothing);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(find.text('Triaje de documentos clínicos'), findsOneWidget);
  });

  testWidgets('cancelar sin selección no muestra error', (tester) async {
    await openSelection(tester, FilePickerService(pickFile: () async => null));
    await tapText(tester, 'Buscar archivo');
    expect(find.text('Ningún archivo seleccionado'), findsOneWidget);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('un error del sistema conserva el archivo y permite reintentar', (
    tester,
  ) async {
    var calls = 0;
    final service = FilePickerService(
      pickFile: () async {
        calls++;
        if (calls == 2) throw PlatformException(code: 'permission_denied');
        return StubPlatformFile(name: 'nota.txt');
      },
    );
    await openSelection(tester, service);
    await tapText(tester, 'Buscar archivo');
    await tapText(tester, 'Cambiar archivo');
    expect(find.text('nota.txt'), findsOneWidget);
    expect(
      find.text('No se pudo seleccionar el archivo. Inténtalo de nuevo.'),
      findsOneWidget,
    );
    await tester.pumpAndSettle(const Duration(seconds: 5));
    await tapText(tester, 'Cambiar archivo');
    expect(calls, 3);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'evita aperturas dobles y tolera salir antes de recibir resultado',
    (tester) async {
      final pending = Completer<PlatformFile?>();
      var calls = 0;
      await openSelection(
        tester,
        FilePickerService(
          pickFile: () {
            calls++;
            return pending.future;
          },
        ),
      );
      await tapText(tester, 'Buscar archivo');
      final button = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Buscar archivo'),
      );
      expect(button.onPressed, isNull);
      expect(calls, 1);
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      pending.complete(StubPlatformFile(name: 'tarde.pdf'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('MediFlow'), findsOneWidget);
    },
  );

  for (final size in [const Size(320, 640), const Size(640, 320)]) {
    testWidgets('pantallas adaptables con texto grande en $size', (
      tester,
    ) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      tester.platformDispatcher.textScaleFactorTestValue = 1.5;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await openSelection(
        tester,
        FilePickerService(
          pickFile: () async => StubPlatformFile(
            name: 'informe_clinico_con_un_nombre_muy_largo_de_prueba.pdf',
          ),
        ),
      );
      await tapText(tester, 'Buscar archivo');
      await tapText(tester, 'Continuar');
      expect(tester.takeException(), isNull);
    });
  }

  for (final type in DocumentType.values) {
    testWidgets('muestra el icono correspondiente a ${type.label}', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SelectedFileCard(
              document: SelectedDocument(
                name: 'archivo',
                extension: 'txt',
                size: 0,
                type: type,
              ),
            ),
          ),
        ),
      );
      expect(
        find.byIcon(switch (type) {
          DocumentType.pdf => Icons.picture_as_pdf_outlined,
          DocumentType.image => Icons.image_outlined,
          DocumentType.text => Icons.description_outlined,
        }),
        findsOneWidget,
      );
    });
  }
}
