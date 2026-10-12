import 'package:flutter/material.dart';

import '../models/selected_document.dart';
import '../models/triage_result.dart';
import '../services/file_picker_service.dart';
import '../services/triage_api_service.dart';
import '../widgets/selected_file_card.dart';

enum _TriageState { idle, processing, success, error }

class DocumentSelectionScreen extends StatefulWidget {
  const DocumentSelectionScreen({
    super.key,
    this.filePickerService,
    this.triageApiService,
  });

  final FilePickerService? filePickerService;
  final TriageApiService? triageApiService;

  @override
  State<DocumentSelectionScreen> createState() =>
      _DocumentSelectionScreenState();
}

class _DocumentSelectionScreenState extends State<DocumentSelectionScreen> {
  late final FilePickerService _service =
      widget.filePickerService ?? FilePickerService();
  SelectedDocument? _document;
  bool _pickerOpen = false;
  // Agregado por Edil: consentimiento por archivo, nunca activado automáticamente.
  bool _analyze = false;
  late final TriageApiService _api =
      widget.triageApiService ?? TriageApiService();
  _TriageState _state = _TriageState.idle;
  TriageResult? _result;
  String? _error;

  bool get _processing => _state == _TriageState.processing;

  void _setDocument(SelectedDocument? document) {
    setState(() {
      _document = document;
      _analyze = false; // Agregado por Edil: cambiar/quitar archivo revoca el consentimiento.
      _state = _TriageState.idle;
      _result = null;
      _error = null;
    });
  }

  Future<void> _processDocument() async {
    final document = _document;
    if (document == null ||
        _processing ||
        _pickerOpen ||
        _state == _TriageState.success) {
      return;
    }
    setState(() {
      _state = _TriageState.processing;
      _result = null;
      _error = null;
    });
    try {
      final result = await _api.sendDocument(document, analyze: _analyze);
      if (!mounted) return;
      setState(() {
        _result = result;
        _state = _TriageState.success;
      });
    } on TriageApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _state = _TriageState.error;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Ocurrió un error al procesar el documento.';
        _state = _TriageState.error;
      });
    }
  }

  @override
  void dispose() {
    _api.cancelPendingRequests();
    super.dispose();
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _selectDocument() async {
    if (_pickerOpen || _processing) return;
    setState(() => _pickerOpen = true);
    try {
      final document = await _service.pickDocument();
      if (!mounted || document == null) return;
      _setDocument(document);
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
                  onPressed: _pickerOpen || _processing
                      ? null
                      : _selectDocument,
                  icon: const Icon(Icons.folder_open_outlined),
                  label: Text(
                    document == null ? 'Buscar archivo' : 'Cambiar archivo',
                  ),
                ),
                if (document != null) ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _pickerOpen || _processing
                        ? null
                        : () => _setDocument(null),
                    icon: const Icon(Icons.close_rounded),
                    label: const Text('Quitar archivo'),
                  ),
                  const SizedBox(height: 16),
                  if (_processing)
                    Semantics(
                      liveRegion: true,
                      child: const Column(
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 12),
                          Text('Procesando documento...'),
                          SizedBox(height: 16),
                        ],
                      ),
                    ),
                  if (_state == _TriageState.success && _result != null)
                    Semantics(
                      liveRegion: true,
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.check_circle_outline,
                                color: theme.colorScheme.primary,
                              ),
                              const SizedBox(height: 12),
                              Text(
                                // Agregado por Edil: distingue recepción, extracción y revisión.
                                _result!.status == 'procesado'
                                    ? 'Extracción completada.'
                                    : _result!.status == 'auditoria_humana'
                                        ? 'Requiere revisión humana.'
                                        : 'Documento recibido correctamente.',
                                style: theme.textTheme.titleMedium,
                              ),
                              if (_result!.status case final status?) ...[
                                const SizedBox(height: 8),
                                Text('Estado: $status'),
                              ],
                              if (_result!.status == 'recibido') ...[
                                const SizedBox(height: 8),
                                const Text(
                                  'El servidor confirmó la recepción. '
                                  'El análisis clínico sigue pendiente.',
                                ),
                              ],
                              if (_result!.documentoId case final id?) ...[
                                const SizedBox(height: 8),
                                Text('Documento: $id'),
                              ],
                              // Agregado por Edil: resultado básico de Sprint 2; no diagnóstico final.
                              if (_result!.status != 'recibido' &&
                                  _result!.tipoDocumento != null) ...[
                                const SizedBox(height: 8),
                                Text('Tipo: ${_result!.tipoDocumento}'),
                              ],
                              if (_result!.status != 'recibido' &&
                                  _result!.prioridad != null) ...[
                                const SizedBox(height: 8),
                                Text('Prioridad: ${_result!.prioridad}'),
                              ],
                              if (_result!.message case final message?) ...[
                                const SizedBox(height: 8),
                                Text(message),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  if (_state == _TriageState.error)
                    Semantics(
                      liveRegion: true,
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Text(
                          _error!,
                          style: TextStyle(color: theme.colorScheme.error),
                        ),
                      ),
                    ),
                  // Agregado por Edil: identifica payload/destino y exige autorización humana.
                  if (_state != _TriageState.success)
                    CheckboxListTile(
                      value: _analyze,
                      onChanged: _processing || _pickerOpen
                          ? null
                          : (value) => setState(() => _analyze = value ?? false),
                      title: const Text('Autorizo enviar este archivo a Google Gemini'),
                      subtitle: const Text(
                        'Su contenido se enviará a un proveedor externo y puede generar costes. '
                        'Confirma que tienes autorización para compartir este documento. '
                        'Sin marcar, solo se guardará en OCI.',
                      ),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  if (_state != _TriageState.success)
                    OutlinedButton.icon(
                      onPressed: _pickerOpen || _processing
                          ? null
                          : _processDocument,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      label: Text(
                        _state == _TriageState.error
                            ? 'Reintentar'
                            : 'Procesar documento',
                      ),
                    ),
                ],
                const SizedBox(height: 24),
                const Text(
                  'La selección funciona sin conexión. Para procesar el documento '
                  'necesitas conexión con el servidor.',
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
