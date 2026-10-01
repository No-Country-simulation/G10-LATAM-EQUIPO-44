import 'package:file_picker/file_picker.dart';

import '../models/selected_document.dart';

class UnsupportedDocumentFormat implements Exception {
  const UnsupportedDocumentFormat();
}

class FileSelectionException implements Exception {
  const FileSelectionException();
}

class FilePickerService {
  FilePickerService({Future<PlatformFile?> Function()? pickFile})
    : _pickFile = pickFile ?? _openPicker;

  static const allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png', 'txt'];

  final Future<PlatformFile?> Function() _pickFile;

  static Future<PlatformFile?> _openPicker() => FilePicker.pickFile(
    type: FileType.custom,
    allowedExtensions: allowedExtensions,
    dialogTitle: 'Seleccionar documento',
  );

  /// No lee el contenido, no procesa y no envía el documento.
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

    return SelectedDocument(
      name: file.name,
      extension: extension,
      path: file.path,
      size: size,
      type: switch (extension) {
        'pdf' => DocumentType.pdf,
        'txt' => DocumentType.text,
        _ => DocumentType.image,
      },
    );
  }
}
