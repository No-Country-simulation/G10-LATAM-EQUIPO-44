import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../config/api_config.dart';
import '../models/selected_document.dart';
import '../models/triage_result.dart';

class TriageApiException implements Exception {
  // Agregado por Edil: conservar el ID confirmado por el backend para consultar,
  // sin confundir un fallo del análisis con un archivo que nunca llegó.
  const TriageApiException(
    this.message, {
    this.statusCode,
    this.documentId,
    this.requestMayHaveBeenReceived = false,
  });

  final String message;
  final int? statusCode;
  final String? documentId;
  final bool requestMayHaveBeenReceived;

  @override
  String toString() => message;
}

class TriageApiService {
  TriageApiService({
    http.Client Function()? clientFactory,
    String? baseUrl,
    Duration timeout = ApiConfig.requestTimeout,
  }) : _clientFactory = clientFactory ?? http.Client.new,
       _baseUrl = baseUrl ?? ApiConfig.baseUrl,
       _timeout = timeout;

  final http.Client Function() _clientFactory;
  final String _baseUrl;
  final Duration _timeout;
  final Set<http.Client> _activeClients = {};

  // Agregado por Edil: IA opt-in; el valor por defecto conserva recepción sin Gemini.
  Future<TriageResult> sendDocument(
    SelectedDocument document, {
    bool analyze = false,
  }) async {
    http.Client? client;
    String? acknowledgedDocumentId;
    var requestStarted = false;
    try {
      final Uri endpoint;
      try {
        endpoint = ApiConfig.triageUri(url: _baseUrl);
      } on FormatException {
        throw const TriageApiException(
          'La dirección del servidor no está configurada correctamente.',
        );
      }
      client = _clientFactory();
      _activeClients.add(client);
      // Incluye preparación, envío, cabeceras y lectura del cuerpo completo.
      // Agregado por Edil: antes no se conservaba el ID recibido en cabeceras.
      // return await _send(client, endpoint, document, analyze).timeout(_timeout);
      return await _send(
        client,
        endpoint,
        document,
        analyze,
        onDocumentId: (id) => acknowledgedDocumentId = id,
        onRequestStarted: () => requestStarted = true,
      ).timeout(_timeout);
    } on TriageApiException {
      rethrow;
    } on TimeoutException {
      throw TriageApiException(
        'El servidor tardó demasiado en responder.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } on FileSystemException {
      throw TriageApiException(
        'El archivo seleccionado ya no está disponible.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } on SocketException {
      throw TriageApiException(
        'No se pudo conectar con el servidor.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } on HandshakeException {
      throw TriageApiException(
        'No se pudo establecer una conexión segura con el servidor.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } on http.ClientException {
      throw TriageApiException(
        'No se pudo conectar con el servidor.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } on FormatException {
      throw TriageApiException(
        'El servidor devolvió una respuesta inválida.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } catch (_) {
      // Agregado por Edil: también un fallo de transporte inesperado puede
      // llegar después de las cabeceras. No perder el ID ni habilitar otro POST.
      throw TriageApiException(
        'Ocurrió un error al procesar el documento.',
        documentId: acknowledgedDocumentId,
        requestMayHaveBeenReceived: requestStarted,
      );
    } finally {
      if (client != null) {
        _activeClients.remove(client);
        // Cerrar el transporte cancela la petición también cuando vence el timeout.
        client.close();
      }
    }
  }

  // Agregado por Edil: usar el GET existente para consultar sin repetir POST ni IA.
  Future<TriageResult> getDocument(String documentId) async {
    http.Client? client;
    try {
      final Uri endpoint;
      try {
        endpoint = ApiConfig.documentUri(documentId, url: _baseUrl);
      } on FormatException {
        throw const TriageApiException(
          'El identificador o la dirección del servidor no son válidos.',
        );
      }
      client = _clientFactory();
      _activeClients.add(client);
      final request = http.Request('GET', endpoint)
        ..followRedirects = false
        ..headers['Accept'] = 'application/json';
      final response = await (() async => http.Response.fromStream(
        await client!.send(request),
      ))().timeout(_timeout);
      return _readResult(response, expectedId: documentId);
    } on TriageApiException {
      rethrow;
    } on TimeoutException {
      throw const TriageApiException(
        'La consulta tardó demasiado en responder.',
      );
    } on SocketException {
      throw const TriageApiException('No se pudo conectar con el servidor.');
    } on HandshakeException {
      throw const TriageApiException(
        'No se pudo establecer una conexión segura con el servidor.',
      );
    } on http.ClientException {
      throw const TriageApiException('No se pudo conectar con el servidor.');
    } catch (_) {
      throw const TriageApiException('No se pudo consultar el documento.');
    } finally {
      if (client != null) {
        _activeClients.remove(client);
        client.close();
      }
    }
  }

  Future<TriageResult> _send(
    http.Client client,
    Uri endpoint,
    SelectedDocument document,
    bool analyze, {
    required void Function(String?) onDocumentId,
    required void Function() onRequestStarted,
  }) async {
    final part = await _filePart(document);
    if (!_activeClients.contains(client)) {
      throw const TriageApiException('El envío fue cancelado.');
    }
    final request = http.MultipartRequest('POST', endpoint)
      ..followRedirects = false
      ..headers['Accept'] = 'application/json'
      // Agregado por Edil: solo true tras consentimiento del usuario para este archivo.
      ..fields['analyze'] = analyze.toString()
      ..files.add(part);
    // MultipartRequest genera Content-Type y boundary; no se fijan manualmente.
    // Agregado por Edil: antes se leían cabeceras/cuerpo juntos y se perdía el ID.
    // final response = await http.Response.fromStream(await client.send(request));
    onRequestStarted();
    final streamed = await client.send(request);
    onDocumentId(_headerDocumentId(streamed.headers));
    final response = await http.Response.fromStream(streamed);
    return _readResult(response, isSubmission: true);
  }

  TriageResult _readResult(
    http.Response response, {
    String? expectedId,
    bool isSubmission = false,
  }) {
    var documentId = _headerDocumentId(response.headers);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw TriageApiException(
        expectedId != null && response.statusCode == 404
            ? 'No se encontró un resultado guardado para este documento. Conserva su ID para consultar al equipo.'
            : _serverError(response),
        statusCode: response.statusCode,
        documentId: isSubmission ? documentId : expectedId,
        requestMayHaveBeenReceived:
            isSubmission &&
            (documentId != null ||
                response.statusCode == 408 ||
                response.statusCode >= 500),
      );
    }
    try {
      if (response.statusCode == 204 && response.bodyBytes.isEmpty) {
        // Agregado por Edil: sin JSON no se puede confirmar el resultado.
        throw const FormatException();
      }
      final json = jsonDecode(utf8.decode(response.bodyBytes));
      if (json is! Map<String, dynamic>) throw const FormatException();
      documentId ??= _safeDocumentId(json['documento_id']);
      final result = TriageResult.fromJson(json);
      result.validateForDisplay();
      if (_safeDocumentId(result.documentoId) == null ||
          (expectedId != null && result.documentoId != expectedId) ||
          (documentId != null && result.documentoId != documentId)) {
        throw const FormatException();
      }
      // Agregado por Edil: recibido solo confirma recepción; la pantalla lo distingue.
      return result;
    } on FormatException {
      throw TriageApiException(
        'El servidor devolvió una respuesta inválida.',
        statusCode: response.statusCode,
        documentId: isSubmission ? documentId : expectedId,
        requestMayHaveBeenReceived: isSubmission,
      );
    }
  }

  // Agregado por Edil: nunca utilizar cabeceras arbitrarias como rutas o IDs visibles.
  static String? _safeDocumentId(Object? value) =>
      value is String && RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(value)
      ? value
      : null;

  static String? _headerDocumentId(Map<String, String> headers) {
    for (final entry in headers.entries) {
      if (entry.key.toLowerCase() == 'x-document-id') {
        return _safeDocumentId(entry.value);
      }
    }
    return null;
  }

  void _validateFileSize(int size) {
    if (size <= 0) throw const TriageApiException('El archivo está vacío.');
    if (size > ApiConfig.maxFileBytes) {
      throw const TriageApiException('El archivo supera el límite de 10 MiB.');
    }
  }

  Future<http.MultipartFile> _filePart(SelectedDocument document) async {
    final mimeType = switch (document.extension.toLowerCase()) {
      'pdf' => 'application/pdf',
      'jpg' || 'jpeg' => 'image/jpeg',
      'png' => 'image/png',
      'txt' => 'text/plain',
      _ => throw const TriageApiException('Formato de archivo no permitido.'),
    };
    final contentType = MediaType.parse(mimeType);
    if (document.bytes case final bytes?) {
      // Agregado por Edil: comprobar bytes reales, no solo los metadatos del selector.
      _validateFileSize(bytes.length);
      return http.MultipartFile.fromBytes(
        ApiConfig.fileFieldName,
        bytes,
        filename: document.name,
        contentType: contentType,
      );
    }
    final path = document.path;
    if (path == null || path.trim().isEmpty || path.contains('\u0000')) {
      throw const TriageApiException(
        'El archivo seleccionado ya no está disponible.',
      );
    }
    try {
      if (await FileSystemEntity.type(path) != FileSystemEntityType.file) {
        throw const FileSystemException();
      }
      final part = await http.MultipartFile.fromPath(
        ApiConfig.fileFieldName,
        path,
        filename: document.name,
        contentType: contentType,
      );
      _validateFileSize(part.length);
      return part;
    } on ArgumentError {
      throw const TriageApiException(
        'El archivo seleccionado ya no está disponible.',
      );
    }
  }

  // Agregado por Edil: solo mensajes controlados del backend; nunca texto arbitrario,
  // trazas del proveedor o contenido clínico devuelto en un error.
  String _serverError(http.Response response) {
    const allowed = <(int, String)>{
      // Agregado por Edil: error controlado de la copia verificada, conservando el ID.
      (
        503,
        'No se pudo verificar la copia OCI. El documento original sigue recibido.',
      ),
      (404, 'Documento no encontrado.'),
      (502, 'El JSON almacenado en OCI es inválido.'),
      (
        502,
        'El documento almacenado en OCI no cumple el contrato oficial de datos.',
      ),
      (500, 'No se pudo almacenar el documento en OCI.'),
      // Agregado por Edil: distinguir fallo JSON de la subida original ya completada.
      (
        503,
        'No se pudo guardar el resultado JSON en OCI. El documento original sigue recibido.',
      ),
      (503, 'El análisis IA no está configurado.'),
      (502, 'No se pudo autenticar el servicio de análisis.'),
      (429, 'El servicio de análisis alcanzó su límite de solicitudes.'),
      (504, 'El servicio de análisis agotó el tiempo de espera.'),
      (503, 'El servicio de análisis no está disponible.'),
      (502, 'El servicio de análisis devolvió una respuesta inválida.'),
      (422, 'El documento no puede analizarse en su formato actual.'),
      (500, 'No se pudo completar el análisis.'),
    };
    try {
      final payload = jsonDecode(utf8.decode(response.bodyBytes));
      if (payload is Map<String, dynamic> && payload['detail'] is String) {
        final detail = payload['detail'] as String;
        if (allowed.contains((response.statusCode, detail))) return detail;
      }
    } catch (_) {
      // Mantener el mensaje seguro anterior si el error no cumple nuestro contrato.
    }
    return _httpError(response.statusCode);
  }

  String _httpError(int code) => switch (code) {
    400 || 422 => 'El servidor rechazó el documento.',
    401 || 403 => 'No tienes autorización para enviar documentos al servidor.',
    404 => 'No se encontró el servicio de procesamiento.',
    408 || 504 => 'El servidor tardó demasiado en responder.',
    413 => 'El archivo supera el tamaño permitido por el servidor.',
    429 => 'El servidor recibió demasiadas solicitudes. Inténtalo más tarde.',
    >= 500 => 'El servidor no está disponible. Inténtalo más tarde.',
    _ => 'El servidor no pudo completar la solicitud.',
  };

  /// Cancela el transporte al salir de la pantalla, sin reintentar automáticamente.
  /// El backend podría haber recibido el archivo antes de la cancelación.
  void cancelPendingRequests() {
    for (final client in _activeClients) {
      client.close();
    }
    _activeClients.clear();
  }
}
