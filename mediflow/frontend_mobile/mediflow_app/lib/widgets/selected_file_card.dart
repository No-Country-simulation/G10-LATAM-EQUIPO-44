import 'package:flutter/material.dart';

import '../models/selected_document.dart';

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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 40, color: theme.colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              document.name,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            Text('Tipo: ${document.type.label}'),
            const SizedBox(height: 8),
            Text('Extensión: .${document.extension}'),
            const SizedBox(height: 8),
            Text('Tamaño: ${document.formattedSize}'),
            if (document.path case final path? when path.isNotEmpty) ...[
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Divider(),
              ),
              Text('Ruta disponible', style: theme.textTheme.labelLarge),
              const SizedBox(height: 4),
              SelectableText(path, style: theme.textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}
