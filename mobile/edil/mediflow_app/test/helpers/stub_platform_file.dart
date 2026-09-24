import 'package:file_picker/file_picker.dart';

/// Simula metadatos del selector sin leer archivos ni invocar Android.
final class StubPlatformFile extends PlatformFile {
  StubPlatformFile({
    required this.name,
    this.bytes = 1536,
    this.localPath = '/storage/emulated/0/Download/documento.pdf',
    this.cachedSize = true,
  });

  @override
  final String name;
  final int? bytes;
  final String? localPath;
  final bool cachedSize;

  @override
  Uri get uri => localPath == null
      ? Uri.parse('content://local.documents/document/1')
      : Uri.file(localPath!);

  @override
  String? get path => localPath;

  @override
  int? lengthSync() => cachedSize ? bytes : null;

  @override
  Future<int?> length() async => bytes;

  // Fallar si la aplicación intenta leer el contenido del documento.
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw StateError('Acceso inesperado: ${invocation.memberName}');
}
