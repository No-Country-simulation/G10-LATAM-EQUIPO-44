import 'package:flutter/material.dart';

import '../services/file_picker_service.dart';
import 'document_selection_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, this.filePickerService});

  final FilePickerService? filePickerService;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('MediFlow')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Icon(
                      Icons.health_and_safety_outlined,
                      size: 48,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Triaje de documentos clínicos',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Selecciona un documento clínico para iniciar su procesamiento.',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 28),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Documentos admitidos',
                          style: theme.textTheme.titleMedium,
                        ),
                        const SizedBox(height: 16),
                        const Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            Chip(
                              avatar: Icon(Icons.picture_as_pdf_outlined),
                              label: Text('PDF'),
                            ),
                            Chip(
                              avatar: Icon(Icons.image_outlined),
                              label: Text('Imagen'),
                            ),
                            Chip(
                              avatar: Icon(Icons.description_outlined),
                              label: Text('Texto'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        const Text('PDF, JPG, JPEG, PNG y TXT'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => DocumentSelectionScreen(
                        filePickerService: filePickerService,
                      ),
                    ),
                  ),
                  icon: const Icon(Icons.add_rounded),
                  label: const Text('Seleccionar documento'),
                ),
                const SizedBox(height: 24),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.phonelink_lock_outlined,
                      color: theme.colorScheme.primary,
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'Selección local y sin conexión..',
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
