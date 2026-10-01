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

  test('acepta tamaño cero y ruta no disponible', () async {
    final service = FilePickerService(
      pickFile: () async =>
          StubPlatformFile(name: 'vacio.txt', bytes: 0, localPath: null),
    );
    final document = await service.pickDocument();
    expect(document?.size, 0);
    expect(document?.formattedSize, '0 B');
    expect(document?.path, isNull);
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
