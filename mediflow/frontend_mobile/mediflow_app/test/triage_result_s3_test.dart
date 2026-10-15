import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/models/triage_result.dart';
import 'package:mediflow_app/widgets/triage_result_card.dart';
import 'helpers/triage_fixture.dart';

// Agregado por Edil: probar respuestas del contrato, no una llamada real a Gemini.
void main() {
  for (final status in ['procesado', 'auditoria_humana']) {
    for (final priority in ['Rutina', 'Urgente']) {
      testWidgets('muestra resultado $status con prioridad $priority', (
        tester,
      ) async {
        final result = TriageResult.fromJson(
          triageFixture(status: status, priority: priority),
        );
        result.validateForDisplay();
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: TriageResultCard(result: result),
              ),
            ),
          ),
        );
        expect(
          find.byKey(const Key('urgent-alert')),
          priority == 'Urgente' ? findsOneWidget : findsNothing,
        );
        expect(find.text('Prioridad: $priority'), findsOneWidget);
        expect(
          find.text(
            status == 'auditoria_humana'
                ? 'Requiere revisión humana.'
                : 'Extracción completada.',
          ),
          findsOneWidget,
        );
      });
    }
  }
  testWidgets('recibido no afirma análisis ni muestra alerta', (tester) async {
    final result = TriageResult.fromJson({
      'status': 'recibido',
      'documento_id': 'DOC-TEST',
    });
    result.validateForDisplay();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: TriageResultCard(result: result)),
      ),
    );
    expect(find.byKey(const Key('urgent-alert')), findsNothing);
    expect(find.text('Documento recibido correctamente.'), findsOneWidget);
  });
  for (final mutate in <void Function(Map<String, dynamic>)>[
    (j) => j['status'] = 'ambiguo',
    (j) => j['documento_id'] = 123,
    (j) => j.remove('clasificacion'),
    (j) => j['clasificacion']['nivel_prioridad'] = 'Pendiente',
    (j) => j['clasificacion']['score_confianza_clasificacion'] = 1.5,
    (j) => j['decision_enrutamiento']['requiere_auditoria_humana'] = true,
    (j) => j['almacenamiento_oci'] = {},
  ]) {
    test('rechaza contrato malformado o contradictorio', () {
      final json = triageFixture();
      mutate(json);
      expect(
        () => TriageResult.fromJson(json).validateForDisplay(),
        throwsFormatException,
      );
    });
  }
}
