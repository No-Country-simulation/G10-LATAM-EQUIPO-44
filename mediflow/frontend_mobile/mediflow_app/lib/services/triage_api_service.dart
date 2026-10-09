import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../config/api_config.dart';
import '../models/selected_document.dart';
import '../models/triage_result.dart';

class TriageApiException implements Exception {
  const TriageApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

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

  Future<TriageResult> sendDocument(SelectedDocument document) async {
    http.Client? client;
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
      return await _send(client, endpoint, document).timeout(_timeout);
    } on TriageApiException {
      rethrow;
    } on TimeoutException {
      throw const TriageApiException(
        'El servidor tardó demasiado en responder.',
      );
    } on FileSystemException {
      throw const TriageApiException(
        'El archivo seleccionado ya no está disponible.',
      );
    } on SocketException {
      throw const TriageApiException('No se pudo conectar con el servidor.');
    } on HandshakeException {
      throw const TriageApiException(
        'No se pudo establecer una conexión segura con el servidor.',
      );
    } on http.ClientException {
      throw const TriageApiException('No se pudo conectar con el servidor.');
    } on FormatException {
      throw const TriageApiException(
        'El servidor devolvió una respuesta inválida.',
      );
    } catch (_) {
      throw const TriageApiException(
        'Ocurrió un error al procesar el documento.',
      );
    } finally {
      if (client != null) {
        _activeClients.remove(client);
        // Cerrar el transporte cancela la petición también cuando vence el timeout.
        client.close();
      }
    }
  }

  Future<TriageResult> _send(
    http.Client client,
    Uri endpoint,
    SelectedDocument document,
  ) async {
    final part = await _filePart(document);
    if (!_activeClients.contains(client)) {
      throw const TriageApiException('El envío fue cancelado.');
    }
    final request = http.MultipartRequest('POST', endpoint)
      ..followRedirects = false
      ..headers['Accept'] = 'application/json'
      ..files.add(part);
    // MultipartRequest genera Content-Type y boundary; no se fijan manualmente.
    final response = await http.Response.fromStream(await client.send(request));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw TriageApiException(
        _httpError(response.statusCode),
        statusCode: response.statusCode,
      );
    }
    if (response.statusCode == 204 && response.bodyBytes.isEmpty) {
      return TriageResult.fromJson({});
    }
    final json = jsonDecode(utf8.decode(response.bodyBytes));
    if (json is! Map<String, dynamic>) throw const FormatException();
    return TriageResult.fromJson(json);
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
      return await http.MultipartFile.fromPath(
        ApiConfig.fileFieldName,
        path,
        filename: document.name,
        contentType: contentType,
      );
    } on ArgumentError {
      throw const TriageApiException(
        'El archivo seleccionado ya no está disponible.',
      );
    }
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
