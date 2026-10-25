import 'package:flutter/material.dart';
import '../models/selected_document.dart';
import '../design_system/app_colors.dart';
import '../design_system/app_spacing.dart';
import 'app_components.dart';

class SelectedFileCard extends StatelessWidget {
  const SelectedFileCard({super.key, required this.document});
  final SelectedDocument document;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final icon = switch (document.type) {
      DocumentType.pdf => Icons.picture_as_pdf_outlined,
      DocumentType.image => Icons.image_outlined,
      DocumentType.text => Icons.description_outlined,
    };
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Agregado por Edil: el archivo es el foco; metadatos y ruta se conservan.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
                ),
                child: Icon(icon, size: 28, color: AppColors.primary),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(document.name, style: theme.textTheme.titleMedium),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Tipo: ${document.type.label}'),
          const SizedBox(height: AppSpacing.xs),
          Text('Extensión: .${document.extension}'),
          const SizedBox(height: AppSpacing.xs),
          Text('Tamaño: ${document.formattedSize}'),
          if (document.path case final path? when path.isNotEmpty) ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Divider(),
            ),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text('Ruta disponible', style: theme.textTheme.labelLarge),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: SelectableText(path, style: theme.textTheme.bodySmall),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
