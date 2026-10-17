# Cámara de documentos en Android

Agregado por Edil: una entrada adicional para el mismo flujo de documentos. No cambia el contrato, la clasificación clínica ni los servicios OCI/Gemini.

## Uso

1. Abrir Seleccionar documento en Android y pulsar Tomar foto.
2. Fotografiar todo el documento, con buena iluminación, sin sombras ni reflejos.
3. Revisar y ampliar la imagen. Usar esta foto confirma; Repetir foto vuelve a la cámara; Cancelar conserva la selección anterior.
4. La pantalla muestra la foto confirmada. El envío solo empieza al pulsar Procesar documento.
5. El consentimiento Gemini permanece desmarcado al confirmar una foto nueva. Sin consentimiento solo se solicita almacenamiento OCI.

Se usa image_picker 1.2.4 y la aplicación de cámara del dispositivo. No solicitamos acceso general a la galería ni al micrófono. Android no requiere declarar CAMERA para este uso mediante el plugin; dispositivos sin cámara pueden seguir seleccionando archivos.

## Límites y recuperación

- Solicita cámara trasera, dimensiones máximas 2400 × 2400 y calidad 90. El plugin hace el ajuste; se debe comprobar orientación y legibilidad en el dispositivo real.
- Acepta JPG o PNG, hasta 10 MiB. No elimina información clínica ni asegura que una foto comprimida siga siendo legible: el usuario debe revisarla.
- La foto aceptada queda en memoria; el plugin puede dejar su captura temporal en la caché privada de la app. No se guarda en la galería ni se promete borrado inmediato.
- Si Android reinicia la actividad, al volver a Seleccionar documento recupera la captura pendiente y exige revisión otra vez. Nunca la envía sola.
- Windows conserva el selector de archivos; no se añadió webcam. iOS no se habilitó ni se presenta como probado.
- No hay recorte automático, corrección de perspectiva ni OCR local. La calidad de análisis de recetas fotografiadas requiere evaluación sintética con el modelo real.

## Verificación manual pendiente

Ejecutar Flutter en un Android físico o emulador con cámara configurada. Probar cancelar, repetir, orientación horizontal/vertical, buena y mala iluminación, captura grande, ausencia de cámara/permisos, regreso a la pantalla y reinicio de actividad por falta de memoria.

Para la evaluación real de extracción, usar solo recetas sintéticas, confirmar el consentimiento por archivo y comparar el resultado con el texto original. Una prueba local con cámara simulada no certifica hardware, orientación ni lectura clínica.

Referencia oficial: https://pub.dev/packages/image_picker


## Resultado de la verificación local

- Flutter analyze: sin problemas.
- Flutter test: 113 pruebas aprobadas, incluidas 14 de cámara con datos sintéticos.
- git diff --check: sin errores de formato.
- Compilación APK debug: se intentó y se interrumpió durante Gradle; no se certifica como completada.
- No se ha probado la cámara física ni la orientación en un Android real, ni la extracción real de una receta fotografiada.
- Rama feature/s3-edil-resultados, sin commit ni push. Main y la configuración de credenciales no se modifican.
