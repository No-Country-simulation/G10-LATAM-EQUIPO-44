import 'package:flutter/material.dart';

import '../models/selected_document.dart';
import '../services/file_picker_service.dart';
import '../widgets/selected_file_card.dart';

class DocumentSelectionScreen extends StatefulWidget {
  const DocumentSelectionScreen({super.key, this.filePickerService});

  final FilePickerService? filePickerService;

  @override
  State<DocumentSelectionScreen> createState() =>
      _DocumentSelectionScreenState();
}

class _DocumentSelectionScreenState extends State<DocumentSelectionScreen> {
  late final FilePickerService _service =
      widget.filePickerService ?? FilePickerService();
  SelectedDocument? _document;
  bool _pickerOpen = false;

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _selectDocument() async {
    if (_pickerOpen) return;
    setState(() => _pickerOpen = true);
    try {
      final document = await _service.pickDocument();
      if (!mounted || document == null) return;
      setState(() => _document = document);
    } on UnsupportedDocumentFormat {
      if (mounted) _showMessage('Formato de archivo no permitido.');
    } catch (_) {
      if (mounted) {
        _showMessage('No se pudo seleccionar el archivo. Inténtalo de nuevo.');
      }
    } finally {
      if (mounted) setState(() => _pickerOpen = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final document = _document;
    return Scaffold(
      appBar: AppBar(title: const Text('Seleccionar documento')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text(
                  'Selecciona un documento clínico desde tu dispositivo.',
                  style: theme.textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                const Text('Formatos admitidos: PDF, JPG, JPEG, PNG y TXT.'),
                const SizedBox(height: 28),
                if (document == null)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 40,
                      ),
                      child: Column(
                        children: [
                          Icon(
                            Icons.file_open_outlined,
                            size: 56,
                            color: theme.colorScheme.primary,
                          ),
                          const SizedBox(height: 20),
                          Text(
                            'Ningún archivo seleccionado',
                            textAlign: TextAlign.center,
                            style: theme.textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Busca un archivo guardado en tu dispositivo.',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  SelectedFileCard(document: document),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: _pickerOpen ? null : _selectDocument,
                  icon: const Icon(Icons.folder_open_outlined),
                  label: Text(
                    document == null ? 'Buscar archivo' : 'Cambiar archivo',
                  ),
                ),
                if (document != null) ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _pickerOpen
                        ? null
                        : () => setState(() => _document = null),
                    icon: const Icon(Icons.close_rounded),
                    label: const Text('Quitar archivo'),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: _pickerOpen
                        ? null
                        : () => _showMessage(
                            'Documento listo para procesar. La integración '
                            'estará disponible en el Sprint 2.',
                          ),
                    icon: const Icon(Icons.arrow_forward_rounded),
                    label: const Text('Continuar'),
                  ),
                ],
                const SizedBox(height: 24),
                const Text(
                  'Solo selección local. No se envían ni se procesan archivos.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
