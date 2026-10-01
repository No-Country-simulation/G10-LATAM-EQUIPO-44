enum DocumentType {
  pdf('PDF'),
  image('Imagen'),
  text('Texto');

  const DocumentType(this.label);

  final String label;
}

/// Metadatos de una selección local, conservados únicamente en memoria.
class SelectedDocument {
  const SelectedDocument({
    required this.name,
    required this.extension,
    required this.size,
    required this.type,
    this.path,
  });

  final String name;
  final String extension;
  final String? path;
  final int size;
  final DocumentType type;

  String get formattedSize {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    if (size < 1024 * 1024 * 1024) {
      return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(size / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
}
