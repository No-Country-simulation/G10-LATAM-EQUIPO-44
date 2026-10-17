import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/design_system/app_colors.dart';
import 'package:mediflow_app/design_system/app_theme.dart';
import 'package:mediflow_app/models/triage_result.dart';
import 'package:mediflow_app/screens/home_screen.dart';
import 'package:mediflow_app/screens/document_selection_screen.dart';
import 'package:mediflow_app/widgets/triage_result_card.dart';
import 'helpers/triage_fixture.dart';

// Agregado por Edil: prueba de legibilidad, escala y presentación; sin servicios reales.
void main() {
  test('texto secundario y botones primarios mantienen contraste WCAG AA', () {
    double contrast(Color a, Color b) {
      final la = a.computeLuminance(), lb = b.computeLuminance();
      return ((la > lb ? la : lb) + .05) / ((la > lb ? lb : la) + .05);
    }

    expect(
      contrast(AppColors.primary, Colors.white),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      contrast(AppColors.secondaryText, AppColors.background),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      contrast(AppColors.clinicalBlue, AppColors.card),
      greaterThanOrEqualTo(4.5),
    );
  });
  for (final size in [const Size(320, 640), const Size(1100, 850)]) {
    for (final page in ['home', 'selection', 'audit', 'urgent']) {
      testWidgets('$page admite texto ampliado en $size', (tester) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        tester.platformDispatcher.textScaleFactorTestValue = 2;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
        final body = switch (page) {
          'home' => const HomeScreen(),
          'selection' => const DocumentSelectionScreen(),
          _ => Scaffold(
            body: SingleChildScrollView(
              child: TriageResultCard(
                result: TriageResult.fromJson(
                  triageFixture(
                    status: 'auditoria_humana',
                    priority: page == 'urgent' ? 'Urgente' : 'Rutina',
                  ),
                ),
              ),
            ),
          ),
        };
        await tester.pumpWidget(MaterialApp(theme: AppTheme.light, home: body));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.byType(BottomNavigationBar), findsNothing);
        expect(find.byType(NavigationBar), findsNothing);
        if (page == 'audit') {
          expect(
            find.textContaining('valor técnico provisional'),
            findsOneWidget,
          );
        }
      });
    }
  }
  // Capturas opcionales para revisión visual local, no archivos nuevos en Git.
  if (const bool.fromEnvironment('MEDIFLOW_CAPTURE_DESIGN')) {
    setUpAll(() async {
      final typography = FontLoader('Roboto')
        ..addFont(rootBundle.load('assets/fonts/Roboto-Regular.ttf'))
        ..addFont(rootBundle.load('assets/fonts/Roboto-Medium.ttf'))
        ..addFont(rootBundle.load('assets/fonts/Roboto-Bold.ttf'));
      await typography.load();
      await (FontLoader(
        'MaterialIcons',
      )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    });
    for (final page in ['home', 'selection', 'audit']) {
      testWidgets('captura visual $page', (tester) async {
        tester.view.physicalSize = page == 'home'
            ? const Size(1100, 850)
            : const Size(390, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final boundaryKey = GlobalKey();
        final body = switch (page) {
          'home' => const HomeScreen(),
          'selection' => const DocumentSelectionScreen(),
          _ => Scaffold(
            appBar: AppBar(title: const Text('Resultado del documento')),
            body: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: TriageResultCard(
                result: TriageResult.fromJson(
                  triageFixture(status: 'auditoria_humana'),
                ),
              ),
            ),
          ),
        };
        await tester.pumpWidget(
          RepaintBoundary(
            key: boundaryKey,
            child: MaterialApp(
              debugShowCheckedModeBanner: false,
              theme: AppTheme.light,
              home: body,
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.runAsync(() async {
          final boundary =
              boundaryKey.currentContext!.findRenderObject()
                  as RenderRepaintBoundary;
          final image = await boundary.toImage(pixelRatio: 1);
          final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
          final directory = await Directory(
            '${Directory.systemTemp.path}/mediflow-design-preview',
          ).create(recursive: true);
          await File(
            '${directory.path}/$page.png',
          ).writeAsBytes(bytes!.buffer.asUint8List());
          image.dispose();
        });
      });
    }
  }
}
