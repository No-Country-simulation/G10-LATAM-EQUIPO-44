import 'package:flutter/material.dart';

import '../models/selected_document.dart';
import '../models/triage_result.dart';
import '../services/file_picker_service.dart';
import '../services/document_camera_service.dart';
import 'photo_review_screen.dart';
import '../services/triage_api_service.dart';
import '../widgets/selected_file_card.dart';
import '../widgets/triage_result_card.dart';
import '../widgets/app_components.dart';
import '../design_system/app_spacing.dart';

enum _TriageState { idle, processing, success, error }

class DocumentSelectionScreen extends StatefulWidget {
  const DocumentSelectionScreen({
    super.key,
    this.filePickerService,
    this.triageApiService,
    this.cameraService,
  });

  final FilePickerService? filePickerService;
  final TriageApiService? triageApiService;
  final DocumentCameraService? cameraService;

  @override
  State<DocumentSelectionScreen> createState() =>
      _DocumentSelectionScreenState();
}

class _DocumentSelectionScreenState extends State<DocumentSelectionScreen> {
  late final FilePickerService _service =
      widget.filePickerService ?? FilePickerService();
  late final DocumentCameraService _camera =
      widget.cameraService ?? DocumentCameraService();
  SelectedDocument? _document;
  bool _isCameraPhoto = false;
  bool _pickerOpen = false;
  // Agregado por Edil: consentimiento por archivo, nunca activado automáticamente.
  bool _analyze = false;
  late final TriageApiService _api =
      widget.triageApiService ?? TriageApiService();
  _TriageState _state = _TriageState.idle;
  TriageResult? _result;
  String? _error;
  int? _errorStatusCode;

  bool get _processing => _state == _TriageState.processing;

  void _setDocument(SelectedDocument? document, {bool cameraPhoto = false}) {
    setState(() {
      _document = document;
      _isCameraPhoto = cameraPhoto;
      _analyze =
          false; // Agregado por Edil: cambiar/quitar archivo revoca el consentimiento.
      _state = _TriageState.idle;
      _result = null;
      _error = null;
      _errorStatusCode = null;
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
      _errorStatusCode = null;
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
        _errorStatusCode = error.statusCode;
        _state = _TriageState.error;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Ocurrió un error al procesar el documento.';
        _errorStatusCode = null;
        _state = _TriageState.error;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    // Agregado por Edil: foto pendiente tras reinicio de Android, siempre con revision.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _camera.supported) _takePhoto(recover: true);
    });
  }

  Future<void> _takePhoto({bool recover = false}) async {
    if (_pickerOpen || _processing || !_camera.supported) return;
    setState(() => _pickerOpen = true);
    try {
      var photo = recover
          ? await _camera.recoverDocument()
          : await _camera.captureDocument();
      while (mounted && photo != null) {
        if (!mounted) return;
        final photoToReview = photo;
        final decision = await Navigator.of(context).push<PhotoReviewDecision>(
          MaterialPageRoute(
            builder: (_) => PhotoReviewScreen(document: photoToReview),
          ),
        );
        if (!mounted) return;
        if (decision == PhotoReviewDecision.confirm) {
          // Agregado por Edil: solo una foto confirmada reemplaza la seleccion.
          // Cambiar documento revoca el consentimiento Gemini anterior.
          _setDocument(photo, cameraPhoto: true);
          return;
        }
        if (decision != PhotoReviewDecision.retake) return;
        photo = await _camera.captureDocument();
      }
    } on DocumentCameraException catch (error) {
      if (mounted) _showMessage(error.message);
    } catch (_) {
      if (mounted) {
        _showMessage('No se pudo capturar la foto. Inténtalo de nuevo.');
      }
    } finally {
      if (mounted) setState(() => _pickerOpen = false);
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
    final document = _document;
    return Scaffold(
      appBar: AppBar(title: const Text('Seleccionar documento')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppSpacing.contentWidth,
            ),
            child: ListView(
              padding: EdgeInsets.all(
                MediaQuery.sizeOf(context).width < 400
                    ? AppSpacing.lg
                    : AppSpacing.xl,
              ),
              children: [
                const AppHeader(
                  title: 'Prepara tu documento',
                  subtitle:
                      'Selecciona un documento clínico desde tu dispositivo.',
                  eyebrow: 'INGRESO DE DOCUMENTOS',
                ),
                const SizedBox(height: AppSpacing.md),
                const Text('Formatos admitidos: PDF, JPG, JPEG, PNG y TXT.'),
                const SizedBox(height: AppSpacing.xl),
                if (document == null)
                  const AppCard(
                    child: Column(
                      children: [
                        Icon(Icons.file_open_outlined, size: 48),
                        SizedBox(height: AppSpacing.lg),
                        AppHeader(
                          title: 'Ningún archivo seleccionado',
                          subtitle:
                              'Busca un archivo guardado en tu dispositivo.',
                        ),
                      ],
                    ),
                  )
                else
                  SelectedFileCard(document: document),
                if (_isCameraPhoto && document?.bytes != null) ...[
                  const SizedBox(height: AppSpacing.md),
                  AppCard(
                    padding: AppSpacing.md,
                    child: SizedBox(
                      height: 160,
                      child: Image.memory(
                        document!.bytes!,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.xl),
                AppButton(
                  label: document == null
                      ? 'Buscar archivo'
                      : 'Cambiar archivo',
                  icon: Icons.folder_open_outlined,
                  onPressed: _pickerOpen || _processing
                      ? null
                      : _selectDocument,
                ),
                if (_camera.supported) ...[
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(
                    label: 'Tomar foto',
                    icon: Icons.camera_alt_outlined,
                    variant: AppButtonVariant.secondary,
                    onPressed: _pickerOpen || _processing
                        ? null
                        : () => _takePhoto(),
                  ),
                ],
                if (document != null) ...[
                  const SizedBox(height: AppSpacing.sm),
                  AppButton(
                    label: 'Quitar archivo',
                    icon: Icons.close_rounded,
                    variant: AppButtonVariant.text,
                    onPressed: _pickerOpen || _processing
                        ? null
                        : () => _setDocument(null),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  if (_processing)
                    const AppStatusPanel(
                      title: 'Procesando documento...',
                      loading: true,
                      message:
                          'Espera la respuesta del servidor. No necesitas enviarlo otra vez.',
                    ),
                  if (_state == _TriageState.success && _result != null)
                    TriageResultCard(result: _result!),
                  if (_state == _TriageState.error)
                    AppStatusPanel(
                      title: 'No se pudo completar el procesamiento',
                      message: _error!,
                      tone: AppStatusTone.error,
                    ),
                  if (_state == _TriageState.error && _errorStatusCode != null)
                    Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.sm),
                      child: Text('Código HTTP: $_errorStatusCode'),
                    ),
                  if (_state != _TriageState.success) ...[
                    const SizedBox(height: AppSpacing.lg),
                    // Agregado por Edil: solo cambia el contenedor; el consentimiento y callbacks se conservan.
                    AppCard(
                      padding: AppSpacing.xs,
                      child: CheckboxListTile(
                        value: _analyze,
                        onChanged: _processing || _pickerOpen
                            ? null
                            : (value) =>
                                  setState(() => _analyze = value ?? false),
                        title: const Text(
                          'Autorizo enviar este archivo a Google Gemini',
                        ),
                        subtitle: const Text(
                          'Su contenido se enviará a un proveedor externo y puede generar costes. '
                          'Confirma que tienes autorización para compartir este documento. Sin marcar, solo se guardará en OCI.',
                        ),
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    AppButton(
                      label: _state == _TriageState.error
                          ? 'Reintentar'
                          : 'Procesar documento',
                      icon: Icons.arrow_forward_rounded,
                      variant: AppButtonVariant.secondary,
                      onPressed: _pickerOpen || _processing
                          ? null
                          : _processDocument,
                    ),
                  ],
                ],
                const SizedBox(height: AppSpacing.xl),
                Text(
                  'La selección funciona sin conexión. Para procesar el documento necesitas conexión con el servidor.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
