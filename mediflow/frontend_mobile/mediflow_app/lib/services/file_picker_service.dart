import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';

import '../models/selected_document.dart';

class UnsupportedDocumentFormat implements Exception {
  const UnsupportedDocumentFormat();
}

class FileSelectionException implements Exception {
  const FileSelectionException();
}

// Agregado por Edil: la pantalla puede explicar por separado un archivo vacío
// y uno demasiado grande, sin presentarlos como un fallo del servidor.
class DocumentEmptyException implements Exception {
  const DocumentEmptyException();
}

class DocumentTooLargeException implements Exception {
  const DocumentTooLargeException();
}

class FilePickerService {
  FilePickerService({Future<PlatformFile?> Function()? pickFile})
    : _pickFile = pickFile ?? _openPicker;

  static const allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png', 'txt'];
  // Agregado por Edil: el selector usa el mismo límite de 10 MiB que la cámara.
  static const maxFileBytes = 10 * 1024 * 1024;

  final Future<PlatformFile?> Function() _pickFile;

  static Future<PlatformFile?> _openPicker() => FilePicker.pickFile(
    type: FileType.custom,
    allowedExtensions: allowedExtensions,
    dialogTitle: 'Seleccionar documento',
  );

  /// Conserva bytes solo si no hay ruta local. No procesa ni envía el documento.
  /// Android limita el selector a archivos locales en MainActivity.
  Future<SelectedDocument?> pickDocument() async {
    final file = await _pickFile();
    if (file == null) return null;

    final extension = (file.extension ?? '').toLowerCase();
    if (!allowedExtensions.contains(extension)) {
      throw const UnsupportedDocumentFormat();
    }

    final size = file.lengthSync() ?? await file.length();
    if (size == null || size < 0) throw const FileSelectionException();

    // Agregado por Edil: revisamos el tamaño anunciado antes de cargar bytes.
    // Así evitamos leer un archivo grande que ya sabemos que no se enviará.
    _validateSize(size);
    final hasLocalPath = file.path != null && file.path!.isNotEmpty;
    Uint8List? selectedBytes;
    var selectedSize = size;
    if (!hasLocalPath) {
      selectedBytes = await file.readAsBytes();
      // Agregado por Edil: algunos proveedores informan un tamaño incorrecto.
      // Para la copia en memoria mandan los bytes reales, no los metadatos.
      _validateSize(selectedBytes.length);
      selectedSize = selectedBytes.length;
    }

    return SelectedDocument(
      name: file.name,
      extension: extension,
      path: file.path,
      // Código anterior conservado como referencia:
      // bytes: file.path == null || file.path!.isEmpty
      //     ? await file.readAsBytes()
      //     : null,
      // size: size,
      // Agregado por Edil: guardamos solo contenido y tamaño ya comprobados.
      bytes: selectedBytes,
      size: selectedSize,
      type: switch (extension) {
        'pdf' => DocumentType.pdf,
        'txt' => DocumentType.text,
        _ => DocumentType.image,
      },
    );
  }

  static void _validateSize(int size) {
    if (size == 0) throw const DocumentEmptyException();
    if (size > maxFileBytes) throw const DocumentTooLargeException();
  }
}
