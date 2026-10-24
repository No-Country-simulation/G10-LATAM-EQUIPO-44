// Agregado por Edil: los campos nuevos se conservan sin cambiar lógica Flutter.
// Fixtures sintéticos, sin cámara, servicios externos ni credenciales.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/models/triage_result.dart';

const _kinds = <String>[
  'Receta Médica',
  'Informe de Laboratorio',
  'Informe de Estudio por Imágenes',
  'Orden / Solicitud de Procedimiento',
  'Epicrisis / Informe de Alta',
  'Certificado Médico',
];

const _addedFields = <String>[
  'profesional_emisor',
  'resultados_laboratorio',
  'hallazgos',
  'conclusion',
  'procedimiento_solicitado',
  'indicacion_solicitud',
  'resumen_evolucion',
  'indicacion_alta',
  'destino_alta',
  'seguimiento',
  'contenido_certificacion',
  'periodo_certificado',
];

Map<String, dynamic> _document(
  String kind, {
  bool review = false,
  bool urgent = false,
}) => <String, dynamic>{
  'documento_id': 'DOC-SYNTHETIC-COMPAT',
  'status': review ? 'auditoria_humana' : 'procesado',
  'cargado_por': 'auditor-sintetico',
  'clasificacion': <String, dynamic>{
    'tipo_documento': kind,
    'especialidad': null,
    'nivel_prioridad': urgent ? 'Urgente' : 'Rutina',
    'score_confianza_clasificacion': 0.95,
  },
  'datos_extraidos': <String, dynamic>{
    'paciente': <String, dynamic>{'nombre': 'Persona ficticia', 'edad': null},
    'medico_solicitante': <String, dynamic>{'nombre': null, 'matricula': null},
    'profesional_emisor': <String, dynamic>{
      'nombre': 'Emisor ficticio',
      'matricula': null,
    },
    'estudio_realizado': 'Estudio sintético',
    'diagnostico_principal': null,
    'cie10_sugerido': null,
    'medicamentos_recetados': kind == 'Receta Médica'
        ? <Map<String, dynamic>>[
            {'medicamento': 'Medicación sintética', 'dosis': null},
          ]
        : <Map<String, dynamic>>[],
    'resultados_laboratorio': kind == 'Informe de Laboratorio'
        ? <Map<String, dynamic>>[
            {
              'examen': 'Examen sintético',
              'valor': 'Negativo',
              'unidad': null,
              'rango_referencia': null,
            },
          ]
        : <Map<String, dynamic>>[],
    'hallazgos': null,
    'conclusion': kind == 'Informe de Estudio por Imágenes'
        ? 'Conclusión documental ficticia.'
        : null,
    'procedimiento_solicitado': kind == 'Orden / Solicitud de Procedimiento'
        ? 'Procedimiento ficticio'
        : null,
    'indicacion_solicitud': null,
    'resumen_evolucion': kind == 'Epicrisis / Informe de Alta'
        ? 'Resumen ficticio'
        : null,
    'indicacion_alta': kind == 'Epicrisis / Informe de Alta'
        ? 'Cierre documental ficticio'
        : null,
    'destino_alta': null,
    'seguimiento': null,
    'contenido_certificacion': kind == 'Certificado Médico'
        ? 'Certificación ficticia'
        : null,
    'periodo_certificado': null,
  },
  'decision_enrutamiento': <String, dynamic>{
    'destino_principal': review
        ? 'Cola_Revision_Humana'
        : 'Cola_Historia_Clinica',
    'requiere_auditoria_humana': review,
    'justificacion_enrutamiento':
        'Compatibilidad de contrato con datos sintéticos.',
  },
  'notificacion_generada': null,
  'almacenamiento_oci': <String, dynamic>{
    'bucket': review ? 'auditoria_humana' : 'procesados',
    'ruta_objeto': 'DOC-SYNTHETIC-COMPAT.txt',
    'status_backup': 'exito',
  },
};

void main() {
  for (final kind in _kinds) {
    test('acepta y conserva datos aditivos de $kind', () {
      final json = _document(kind);
      final before = jsonDecode(jsonEncode(json));
      final result = TriageResult.fromJson(json);

      expect(result.validateForDisplay, returnsNormally);
      expect(result.tipoDocumento, kind);
      expect(result.rawData, equals(before));
      expect(json, equals(before));
      final data = result.rawData['datos_extraidos'] as Map<String, dynamic>;
      for (final field in _addedFields) {
        expect(data.containsKey(field), isTrue);
      }
    });
  }

  test('el JSON histórico sigue siendo legible sin inventar campos', () {
    final json = _document('Informe de Laboratorio');
    json.remove('cargado_por');
    final data = json['datos_extraidos'] as Map<String, dynamic>;
    for (final field in _addedFields) {
      data.remove(field);
    }
    final before = jsonDecode(jsonEncode(json));
    final result = TriageResult.fromJson(json);

    expect(result.validateForDisplay, returnsNormally);
    expect(result.rawData, equals(before));
    for (final field in _addedFields) {
      expect(
        (result.rawData['datos_extraidos'] as Map<String, dynamic>).containsKey(
          field,
        ),
        isFalse,
      );
    }
  });

  for (final review in <bool>[false, true]) {
    test('los campos nuevos conservan Urgente y revisión=$review', () {
      final result = TriageResult.fromJson(
        _document(
          'Informe de Estudio por Imágenes',
          review: review,
          urgent: true,
        ),
      );

      expect(result.validateForDisplay, returnsNormally);
      expect(result.isUrgent, isTrue);
      expect(result.requiresHumanReview, review);
      expect(result.confianzaClasificacion, 0.95);
      final data = result.rawData['datos_extraidos'] as Map<String, dynamic>;
      expect(data['conclusion'], 'Conclusión documental ficticia.');
    });
  }
}
