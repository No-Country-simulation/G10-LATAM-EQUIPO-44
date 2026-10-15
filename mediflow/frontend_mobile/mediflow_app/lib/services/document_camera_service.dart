import 'dart:io';
import 'package:image_picker/image_picker.dart';
import '../models/selected_document.dart';

class DocumentCameraException implements Exception {
  const DocumentCameraException(this.message);
  final String message;
}

// Agregado por Edil: captura local; nunca envia fotos a OCI ni Gemini.
class DocumentCameraService {
  DocumentCameraService({
    Future<XFile?> Function()? capture,
    Future<List<XFile>> Function()? recover,
    bool? supported,
  }) : _capture = capture ?? _takePhoto,
       _recover = recover ?? _lostPhotos,
       supported = supported ?? Platform.isAndroid;

  final Future<XFile?> Function() _capture;
  final Future<List<XFile>> Function() _recover;
  final bool supported;
  static const maxBytes = 10 * 1024 * 1024;

  static Future<XFile?> _takePhoto() => ImagePicker().pickImage(
    source: ImageSource.camera,
    preferredCameraDevice: CameraDevice.rear,
    maxWidth: 2400,
    maxHeight: 2400,
    imageQuality: 90,
    requestFullMetadata: false,
  );

  // Agregado por Edil: Android puede cerrar la app mientras la camara esta abierta.
  // Una foto recuperada vuelve a revision; nunca se confirma ni envia sola.
  static Future<List<XFile>> _lostPhotos() async {
    final lost = await ImagePicker().retrieveLostData();
    if (lost.exception != null) {
      throw const DocumentCameraException(
        'No se pudo recuperar la foto anterior.',
      );
    }
    return lost.files ?? [];
  }

  Future<SelectedDocument?> captureDocument() async {
    if (!supported) return null;
    try {
      final file = await _capture();
      return file == null ? null : await _document(file);
    } on DocumentCameraException {
      rethrow;
    } catch (_) {
      throw const DocumentCameraException(
        'No se pudo abrir la camara. Revisa su disponibilidad y permisos.',
      );
    }
  }

  Future<SelectedDocument?> recoverDocument() async {
    if (!supported) return null;
    try {
      final files = await _recover();
      return files.isEmpty ? null : await _document(files.first);
    } on DocumentCameraException {
      rethrow;
    } catch (_) {
      throw const DocumentCameraException(
        'No se pudo recuperar la foto anterior.',
      );
    }
  }

  Future<SelectedDocument> _document(XFile file) async {
    final size = await file.length();
    if (size == 0 || size > maxBytes) {
      throw const DocumentCameraException(
        'La foto esta vacia o supera 10 MB. Repite la captura.',
      );
    }
    final bytes = await file.readAsBytes();
    if (bytes.isEmpty || bytes.length > maxBytes) {
      throw const DocumentCameraException(
        'La foto supera el limite permitido.',
      );
    }
    final jpeg = bytes.length >= 2 && bytes[0] == 0xff && bytes[1] == 0xd8;
    final png =
        bytes.length >= 8 &&
        List.generate(8, (i) => bytes[i]).join(',') ==
            '137,80,78,71,13,10,26,10';
    if (!jpeg && !png) {
      throw const DocumentCameraException(
        'La camara no devolvio una imagen JPG o PNG valida.',
      );
    }
    final extension = jpeg ? 'jpg' : 'png';
    // Agregado por Edil: nombre neutro, sin paciente ni etiquetas clinicas.
    return SelectedDocument(
      name: 'documento_${DateTime.now().microsecondsSinceEpoch}.$extension',
      extension: extension,
      size: bytes.length,
      type: DocumentType.image,
      bytes: bytes,
    );
  }
}
