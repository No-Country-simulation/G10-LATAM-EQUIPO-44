import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mediflow_app/models/selected_document.dart';
import 'package:mediflow_app/services/file_picker_service.dart';

import 'helpers/stub_platform_file.dart';

void main() {
  for (final entry in {
    'pdf': DocumentType.pdf,
    'jpg': DocumentType.image,
    'jpeg': DocumentType.image,
    'png': DocumentType.image,
    'txt': DocumentType.text,
    'PDF': DocumentType.pdf,
    'JpEg': DocumentType.image,
  }.entries) {
    test(
      'acepta ${entry.key} y devuelve metadatos sin leer contenido',
      () async {
        final file = StubPlatformFile(name: 'documento.${entry.key}');
        final service = FilePickerService(pickFile: () async => file);
        final document = await service.pickDocument();

        expect(document?.name, file.name);
        expect(document?.extension, entry.key.toLowerCase());
        expect(document?.type, entry.value);
        expect(document?.size, 1536);
        expect(document?.path, file.localPath);
      },
    );
  }

  for (final name in [
    'archivo.exe',
    'archivo.pdf.zip',
    'sin_extension',
    '.pdf',
  ]) {
    test('rechaza $name aunque lo devuelva el selector', () async {
      final service = FilePickerService(
        pickFile: () async => StubPlatformFile(name: name),
      );
      await expectLater(
        service.pickDocument(),
        throwsA(isA<UnsupportedDocumentFormat>()),
      );
    });
  }

  test('cancelar devuelve null', () async {
    final service = FilePickerService(pickFile: () async => null);
    expect(await service.pickDocument(), isNull);
  });

  // Prueba anterior conservada como referencia:
  // test('acepta tamaño cero y ruta no disponible', ...)
  // expect(document?.size, 0);
  // expect(document?.formattedSize, '0 B');
  // Agregado por Edil: un archivo vacío no puede procesarse; ahora se rechaza
  // al seleccionar para no trasladar ese error al backend ni al usuario tarde.
  for (final path in <String?>[null, '/local/documento.txt']) {
    test('rechaza tamaño cero antes de leer bytes con ruta $path', () async {
      final file = _MeasuredPlatformFile(
        metadataLength: 0,
        actualLength: 0,
        localPath: path,
      );
      final service = FilePickerService(pickFile: () async => file);

      await expectLater(
        service.pickDocument(),
        throwsA(isA<DocumentEmptyException>()),
      );
      expect(file.readCalls, 0);
    });

    test('rechaza más de 10 MiB antes de leer con ruta $path', () async {
      final file = _MeasuredPlatformFile(
        metadataLength: FilePickerService.maxFileBytes + 1,
        actualLength: FilePickerService.maxFileBytes + 1,
        localPath: path,
      );
      final service = FilePickerService(pickFile: () async => file);

      await expectLater(
        service.pickDocument(),
        throwsA(isA<DocumentTooLargeException>()),
      );
      expect(file.readCalls, 0);
    });

    test('acepta exactamente 10 MiB con ruta $path', () async {
      final file = _MeasuredPlatformFile(
        metadataLength: FilePickerService.maxFileBytes,
        actualLength: FilePickerService.maxFileBytes,
        localPath: path,
      );
      final service = FilePickerService(pickFile: () async => file);

      final document = await service.pickDocument();

      expect(document?.size, FilePickerService.maxFileBytes);
      expect(file.readCalls, path == null ? 1 : 0);
      expect(document?.bytes?.length, path == null ? document?.size : null);
    });
  }

  // Agregado por Edil: estos casos comprueban el contenido real que entrega un
  // proveedor sin ruta, incluso cuando su tamaño anunciado parece aceptable.
  test(
    'rechaza bytes vacíos aunque los metadatos anuncien contenido',
    () async {
      final file = _MeasuredPlatformFile(metadataLength: 100, actualLength: 0);
      final service = FilePickerService(pickFile: () async => file);

      await expectLater(
        service.pickDocument(),
        throwsA(isA<DocumentEmptyException>()),
      );
      expect(file.readCalls, 1);
    },
  );

  test(
    'rechaza bytes reales excesivos aunque el tamaño anunciado sea menor',
    () async {
      final file = _MeasuredPlatformFile(
        metadataLength: 100,
        actualLength: FilePickerService.maxFileBytes + 1,
      );
      final service = FilePickerService(pickFile: () async => file);

      await expectLater(
        service.pickDocument(),
        throwsA(isA<DocumentTooLargeException>()),
      );
      expect(file.readCalls, 1);
    },
  );

  test('conserva el tamaño real de los bytes cuando no existe ruta', () async {
    final file = _MeasuredPlatformFile(metadataLength: 100, actualLength: 500);
    final service = FilePickerService(pickFile: () async => file);

    final document = await service.pickDocument();

    expect(document?.size, 500);
    expect(document?.bytes?.length, 500);
    expect(document?.path, isNull);
    expect(file.readCalls, 1);
  });

  test(
    'consulta el tamaño cuando no viene en los metadatos iniciales',
    () async {
      final service = FilePickerService(
        pickFile: () async =>
            StubPlatformFile(name: 'archivo.pdf', cachedSize: false),
      );
      expect((await service.pickDocument())?.size, 1536);
    },
  );

  test('no inventa un tamaño cuando no se puede obtener', () async {
    final service = FilePickerService(
      pickFile: () async => StubPlatformFile(name: 'archivo.pdf', bytes: null),
    );
    await expectLater(
      service.pickDocument(),
      throwsA(isA<FileSelectionException>()),
    );
  });

  test('propaga un fallo del selector para que la UI lo maneje', () async {
    final service = FilePickerService(
      pickFile: () async => throw PlatformException(code: 'unavailable'),
    );
    await expectLater(
      service.pickDocument(),
      throwsA(isA<PlatformException>()),
    );
  });

  test('formatea tamaños pequeños y grandes', () {
    for (final entry in {
      12: '12 B',
      1024: '1.0 KB',
      1468006: '1.4 MB',
      1073741824: '1.0 GB',
    }.entries) {
      final document = SelectedDocument(
        name: 'archivo.pdf',
        extension: 'pdf',
        size: entry.key,
        type: DocumentType.pdf,
      );
      expect(document.formattedSize, entry.value);
    }
  });
}

// Agregado por Edil: permite demostrar que un rechazo temprano no leyó el
// documento y que los bytes pueden diferir de los metadatos del selector.
final class _MeasuredPlatformFile extends PlatformFile {
  _MeasuredPlatformFile({
    required this.metadataLength,
    required this.actualLength,
    this.localPath,
  });

  final int metadataLength;
  final int actualLength;
  final String? localPath;
  int readCalls = 0;

  @override
  String get name => 'documento.txt';

  @override
  String? get path => localPath;

  @override
  Uri get uri => localPath == null
      ? Uri.parse('content://local.documents/document/1')
      : Uri.file(localPath!);

  @override
  int? lengthSync() => metadataLength;

  @override
  Future<int?> length() async => metadataLength;

  @override
  Future<Uint8List> readAsBytes() async {
    readCalls += 1;
    return Uint8List(actualLength);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw StateError('Acceso inesperado: ${invocation.memberName}');
}
