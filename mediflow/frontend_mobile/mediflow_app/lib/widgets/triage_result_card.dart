import 'package:flutter/material.dart';
import '../models/triage_result.dart';
import '../design_system/app_spacing.dart';
import 'app_components.dart';

// Agregado por Edil: cambia solo la presentación. No interpreta urgencia ni reglas.
class TriageResultCard extends StatelessWidget {
  const TriageResultCard({super.key, required this.result});
  final TriageResult result;
  @override
  Widget build(BuildContext context) {
    final title = result.status == 'procesado'
        ? 'Extracción completada.'
        : result.requiresHumanReview
        ? 'Requiere revisión humana.'
        : 'Documento recibido correctamente.';
    final tone = result.requiresHumanReview
        ? AppStatusTone.warning
        : result.status == 'procesado'
        ? AppStatusTone.success
        : AppStatusTone.information;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (result.isUrgent) ...[
            const AppStatusPanel(
              key: Key('urgent-alert'),
              tone: AppStatusTone.error,
              title: 'Prioridad urgente informada',
              message:
                  'Documento marcado como urgente por el servidor. Requiere atención del equipo responsable.',
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
          AppStatusPanel(title: title, tone: tone),
          const SizedBox(height: AppSpacing.lg),
          Text('Estado: ${result.status}'),
          if (result.status == 'recibido') ...[
            const SizedBox(height: AppSpacing.sm),
            const Text(
              'El servidor confirmó la recepción. El análisis clínico sigue pendiente.',
            ),
          ],
          const SizedBox(height: AppSpacing.sm),
          SelectableText('Documento: ${result.documentoId}'),
          if (result.isAnalyzed) ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Divider(),
            ),
            Text('Tipo: ${result.tipoDocumento}'),
            // Agregado por Edil: este dato del backend no equivale a exactitud
            // clínica, completitud de extracción ni decisión de auditoría.
            if (result.confianzaClasificacion case final confidence?) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Confianza de clasificación: ${(confidence * 100).toStringAsFixed(0)} %',
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Este valor describe la confianza del sistema en el tipo de documento; no mide la calidad de extracción ni la urgencia clínica.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: AppSpacing.sm),
            Text('Prioridad: ${result.prioridad}'),
            const SizedBox(height: AppSpacing.sm),
            Text('Destino: ${result.destino}'),
            const SizedBox(height: AppSpacing.sm),
            Text('Motivo: ${result.justificacion}'),
            const SizedBox(height: AppSpacing.lg),
            AppStatusPanel(
              tone: result.requiresHumanReview
                  ? AppStatusTone.warning
                  : AppStatusTone.information,
              title: 'Pendiente de validación clínica',
              message:
                  result.requiresHumanReview && result.prioridad == 'Rutina'
                  ? 'Rutina puede ser un valor técnico provisional. La revisión humana está pendiente; no confirma baja gravedad clínica.'
                  : 'La clasificación es una propuesta del sistema y no sustituye una revisión clínica.',
            ),
          ],
          if (result.message case final message?) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(message),
          ],
        ],
      ),
    );
  }
}
