import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/models/triage_result.dart';
import 'package:mediflow_app/widgets/triage_result_card.dart';

import 'helpers/triage_fixture.dart';

const _confidenceExplanation =
    'Este valor describe la confianza del sistema en el tipo de documento; '
    'no mide la calidad de extracción ni la urgencia clínica.';

Future<void> _showResult(WidgetTester tester, TriageResult result) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(child: TriageResultCard(result: result)),
      ),
    ),
  );
}

// Agregado por Edil: mostramos solo el score existente de clasificación.
// Estas pruebas no crean un score operativo ni deciden el enrutamiento.
void main() {
  group('lectura de confianza de clasificación', () {
    for (final score in <num>[0, 1, 0.8]) {
      test('conserva el valor válido $score sin aplicar un umbral', () {
        final json = triageFixture();
        json['clasificacion']['score_confianza_clasificacion'] = score;

        expect(
          TriageResult.fromJson(json).confianzaClasificacion,
          score.toDouble(),
        );
      });
    }

    final invalidScores = <String, Object?>{
      'nulo': null,
      'texto': '0.8',
      'booleano': true,
      'NaN': double.nan,
      'infinito': double.infinity,
      'infinito negativo': double.negativeInfinity,
      'negativo': -0.1,
      'mayor que uno': 1.1,
    };
    for (final entry in invalidScores.entries) {
      test('no interpreta como confianza un valor ${entry.key}', () {
        final json = triageFixture();
        json['clasificacion']['score_confianza_clasificacion'] = entry.value;

        expect(TriageResult.fromJson(json).confianzaClasificacion, isNull);
      });
    }

    test('un documento recibido no tiene confianza de análisis disponible', () {
      final result = TriageResult.fromJson(triageFixture(status: 'recibido'));

      expect(result.confianzaClasificacion, isNull);
    });

    test('la ausencia del campo no inventa un porcentaje', () {
      final json = triageFixture();
      (json['clasificacion'] as Map<String, dynamic>).remove(
        'score_confianza_clasificacion',
      );

      expect(TriageResult.fromJson(json).confianzaClasificacion, isNull);
    });
  });

  testWidgets('resultado procesado explica el alcance de su confianza', (
    tester,
  ) async {
    final result = TriageResult.fromJson(triageFixture());
    result.validateForDisplay();
    await _showResult(tester, result);

    expect(find.text('Confianza de clasificación: 80 %'), findsOneWidget);
    expect(find.text(_confidenceExplanation), findsOneWidget);
    expect(find.text('Extracción completada.'), findsOneWidget);
  });

  // Agregado por Edil: confianza, urgencia y revisión son señales independientes.
  testWidgets('la confianza coexiste con urgencia y revisión humana', (
    tester,
  ) async {
    final result = TriageResult.fromJson(
      triageFixture(status: 'auditoria_humana', priority: 'Urgente'),
    );
    result.validateForDisplay();
    await _showResult(tester, result);

    expect(find.text('Confianza de clasificación: 80 %'), findsOneWidget);
    expect(find.text(_confidenceExplanation), findsOneWidget);
    expect(find.byKey(const Key('urgent-alert')), findsOneWidget);
    expect(find.text('Requiere revisión humana.'), findsOneWidget);
    expect(find.text('Prioridad: Urgente'), findsOneWidget);
  });

  testWidgets('recibido no presenta un score como análisis completado', (
    tester,
  ) async {
    final result = TriageResult.fromJson(triageFixture(status: 'recibido'));
    result.validateForDisplay();
    await _showResult(tester, result);

    expect(find.textContaining('Confianza de clasificación:'), findsNothing);
    expect(find.text(_confidenceExplanation), findsNothing);
    expect(find.text('Documento recibido correctamente.'), findsOneWidget);
    expect(find.byKey(const Key('urgent-alert')), findsNothing);
  });
}
