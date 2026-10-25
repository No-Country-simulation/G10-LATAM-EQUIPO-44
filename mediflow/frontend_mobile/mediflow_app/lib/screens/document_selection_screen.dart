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
import '../design_system/app_colors.dart';

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
  // Agregado por Edil: un ID confirma que el servidor identificó este envío.
  // Consultarlo usa GET; repetir POST crearía otro documento, no lo reprocesaría.
  String? _trackedDocumentId;
  bool _checkingStatus = false;
  bool _confirmBeforeResend = false;
  bool _confirmingResend = false;
  String? _lookupError;

  // Antes: bool get _processing => _state == _TriageState.processing;
  // Agregado por Edil: también bloqueamos acciones mientras se consulta el ID.
  bool get _processing => _state == _TriageState.processing || _checkingStatus;

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
      _trackedDocumentId = null;
      _checkingStatus = false;
      _confirmBeforeResend = false;
      _lookupError = null;
    });
  }

  Future<void> _processDocument() async {
    final document = _document;
    if (document == null ||
        _processing ||
        _pickerOpen ||
        _confirmingResend ||
        _trackedDocumentId != null ||
        _state == _TriageState.success) {
      return;
    }
    // Agregado por Edil: un timeout o fallo de red no demuestra que el backend
    // rechazó el archivo. El usuario decide antes de crear un posible duplicado.
    if (_confirmBeforeResend) {
      _confirmingResend = true;
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('¿Enviar el documento de nuevo?'),
          content: const Text(
            'El servidor puede haber recibido el envío anterior, aunque no llegó '
            'su respuesta. Enviar de nuevo puede crear un documento duplicado. '
            'Revisa el historial antes de continuar.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Enviar de nuevo'),
            ),
          ],
        ),
      );
      _confirmingResend = false;
      if (!mounted || confirmed != true) return;
    }
    setState(() {
      _state = _TriageState.processing;
      _result = null;
      _error = null;
      _errorStatusCode = null;
      _lookupError = null;
      _confirmBeforeResend = false;
    });
    try {
      final result = await _api.sendDocument(document, analyze: _analyze);
      if (!mounted) return;
      setState(() {
        _result = result;
        _trackedDocumentId = result.documentoId;
        _state = _TriageState.success;
      });
    } on TriageApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _errorStatusCode = error.statusCode;
        _trackedDocumentId = error.documentId;
        _confirmBeforeResend = error.requestMayHaveBeenReceived;
        _state = _TriageState.error;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Ocurrió un error al procesar el documento.';
        _errorStatusCode = null;
        _confirmBeforeResend = true;
        _state = _TriageState.error;
      });
    }
  }

  Future<void> _consultDocument() async {
    final documentId = _trackedDocumentId;
    if (documentId == null || _processing || _pickerOpen) return;
    setState(() {
      _checkingStatus = true;
      _lookupError = null;
    });
    try {
      final result = await _api.getDocument(documentId);
      if (!mounted) return;
      setState(() {
        _result = result;
        _state = _TriageState.success;
        _error = null;
        _errorStatusCode = null;
      });
    } on TriageApiException catch (error) {
      if (mounted) setState(() => _lookupError = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => _lookupError = 'No se pudo consultar el documento.');
      }
    } finally {
      // Agregado por Edil: fallar al consultar no borra el resultado anterior
      // ni ofrece un POST nuevo para el mismo documento ya identificado.
      if (mounted) setState(() => _checkingStatus = false);
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
    } on DocumentEmptyException {
      if (mounted) {
        _showMessage('El archivo está vacío. Selecciona otro documento.');
      }
    } on DocumentTooLargeException {
      if (mounted) _showMessage('El archivo supera el tamaño máximo de 10 MB.');
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
                        // Agregado por Edil: icono de acción, no sustituto del logo.
                        Icon(
                          Icons.upload_file_outlined,
                          size: 48,
                          color: AppColors.primary,
                        ),
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
                  if (_state == _TriageState.processing)
                    const AppStatusPanel(
                      title: 'Procesando documento...',
                      loading: true,
                      message:
                          'Espera la respuesta del servidor. No necesitas enviarlo otra vez.',
                    ),
                  // Antes: se mostraba solo en estado success. Agregado por Edil:
                  // el resultado confirmado sigue visible si una consulta falla.
                  if (_result != null) TriageResultCard(result: _result!),
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
                  if (_trackedDocumentId != null) ...[
                    const SizedBox(height: AppSpacing.md),
                    if (_result == null) ...[
                      SelectableText('Documento: $_trackedDocumentId'),
                      const SizedBox(height: AppSpacing.sm),
                      const AppStatusPanel(
                        title: 'Consulta el envío identificado',
                        message:
                            'El servidor identificó este documento. Consulta su estado antes de realizar otro envío. La consulta no reinicia el análisis.',
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    if (_checkingStatus) ...[
                      const AppStatusPanel(
                        title: 'Consultando estado...',
                        message: 'Esta consulta no envía el archivo otra vez.',
                        loading: true,
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    if (_lookupError != null) ...[
                      AppStatusPanel(
                        title: 'No se pudo actualizar el estado',
                        message: _lookupError,
                        tone: AppStatusTone.warning,
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    AppButton(
                      label: _result == null
                          ? 'Consultar documento'
                          : 'Actualizar estado',
                      icon: Icons.refresh_rounded,
                      variant: AppButtonVariant.secondary,
                      onPressed: _processing || _pickerOpen
                          ? null
                          : _consultDocument,
                    ),
                  ],
                  // Agregado por Edil: conservar el envío original en comentarios
                  // y ocultarlo cuando ya hay un ID evita duplicados accidentales.
                  // Antes: if (_state != _TriageState.success) ...[
                  if (_state != _TriageState.success &&
                      _trackedDocumentId == null) ...[
                    if (_confirmBeforeResend) ...[
                      const SizedBox(height: AppSpacing.md),
                      const AppStatusPanel(
                        title: 'No se pudo confirmar la recepción',
                        message:
                            'El servidor puede haber recibido el documento. Un nuevo envío puede duplicarlo; revisa el historial antes de reintentar.',
                        tone: AppStatusTone.warning,
                      ),
                    ],
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
