# Design System visual de MediFlow

Agregado por Edil: actualización de presentación Medical Clean con Material 3. Conserva selección, cámara, consentimiento, navegación existente y procesamiento. No añade navegación inferior, funciones clínicas, endpoints ni reglas.

## Tokens y componentes

- lib/design_system/app_colors.dart: primario #087E8B, azul clínico #15324C, fondo #F5F9FC, blanco, éxito #16805D, advertencia #B86E09, error #C43D4B y texto secundario #597187.
- app_typography.dart: Roboto como alternativa compatible a Inter, con fuentes locales y licencia en assets/fonts. No descarga fuentes al iniciar.
- app_spacing.dart: espaciados 4, 8, 12, 16, 24 y 32; bordes 12 y 16; ancho de contenido máximo 720.
- app_theme.dart: tema Material 3, tipografía, tarjetas, botones, chips, checkbox y progreso.
- widgets/app_components.dart: AppButton, AppCard, AppHeader y AppStatusPanel. Los botones conservan los controles Material originales y sus callbacks.

## Estados visuales

Recepción: informativo en primario; no afirma análisis completo.
Procesamiento: indicador indeterminado y mensaje, sin porcentaje inventado.
Completado: verde; auditoría: ámbar y texto explícito; error: rojo y reintento existente.
Urgente: alerta roja basada en el valor del servidor. No transforma la propuesta en una decisión clínica validada.
Rutina con auditoría: se identifica como posible valor técnico provisional y se explica que no confirma baja gravedad.

## Pantallas

Home y selección usan encabezados y tarjetas comunes, contenedores centrados y listas desplazables. Se conservan nombres de acciones y navegación para mantener los flujos existentes.
Archivo, resultado y revisión de foto aplican el mismo tema. Los métodos de selección/procesamiento/captura se compararon con el respaldo anterior y no cambiaron.

## Accesibilidad y alcance

Botones de al menos 48 dp, estados con icono y texto, encabezados semánticos y anuncios de estado. Sin alturas fijas para tarjetas ni truncado de mensajes clínicos; se conserva escalado del sistema.
Pruebas a 320 y 1100 px con texto al doble de tamaño; contraste AA comprobado para botón primario, texto principal y secundario.
La revisión visual usa capturas temporales de inicio, selección y auditoría; no contiene pacientes ni datos reales.
Estas pruebas no equivalen a una certificación completa de accesibilidad ni a pruebas de hardware o servicios clínicos.

Rama feature/s3-edil-resultados. Sin commit ni push de este cambio visual.


## Verificación de esta entrega

- Flutter analyze: sin problemas.
- Suite completa Flutter: 125 pruebas aprobadas con capturas habilitadas (122 pruebas habituales y 3 capturas visuales).
- Se revisaron las capturas de inicio, selección y auditoría con Roboto e iconos Material reales.
- Una prueba de consentimiento se ajustó para desplazar la lista antes de leer el checkbox; se mantienen sus tres comprobaciones de autorización/revocación.
- Comparación con respaldo: métodos anteriores al build en selección y revisión de foto idénticos; servicios, modelos, contratos y endpoints no se modificaron por esta tarea.
- Respaldo previo: C:/Users/leno/AppData/Local/Temp/MediFlow-before-design-system-8029377d469a4d1787e2a5c0587f82e7.
