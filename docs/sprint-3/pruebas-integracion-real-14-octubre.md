# Pruebas de integración real MediFlow

Agregado por Edil: resultado parcial, no aprobación total de punta a punta.

## Resultado real

| Tramo | Resultado | Evidencia |
| --- | --- | --- |
| Perfil OCI y tres buckets | Acceso correcto | recibidos, procesados y auditoria_humana accesibles |
| OCI archivo original | Aprobado | Subida y descarga con comparación exacta de bytes |
| JSON OCI tres buckets | Aprobado | Tres pruebas reales de escritura y lectura exacta; objetos únicos de esas pruebas limpiados |
| Flutter HTTP → FastAPI → OCI → GET | Aprobado | Un test HTTP real opt-in, TXT sintético y mismo JSON recuperado |
| Cliente web GET → documento de Flutter | Aprobado | Cliente JavaScript y adaptador recuperaron el mismo ID real mediante HTTP |
| Foto PNG → FastAPI → OCI → Gemini | Falló | API devuelve 503; cadena de excepción LLMUnavailableError → ServerError, código 503 |
| Gemini directo con la misma PNG | Falló | Segunda llamada, sin nueva subida OCI; ServerError 503 |
| Recepción tras fallo de Gemini | Aprobado con combinación explícita | OCI real, proveedor Gemini simulado como no disponible; GET 200 recibido y foto idéntica |

Las dos llamadas Gemini usaron exclusivamente una imagen generada con texto artificial. No se usó el dataset clínico ni fotos del usuario. No se cambió modelo, clave ni configuración personal; no hubo reintentos automáticos.
El fallo 503 del proveedor no prueba una falla Pydantic, cuota agotada ni autenticación inválida. Se necesita disponibilidad del proveedor para evaluar el resultado real de extracción.
Referencia oficial de fallos transitorios: https://ai.google.dev/gemini-api/docs/troubleshooting

## Cambios explicados y código anterior conservado

- routes.py: conservar el bloque anterior comentado y guardar recepción antes de Gemini. La prueba detectó que un fallo dejaba un archivo sin JSON consultable.
- oci_client.py: conservar selección antigua de buckets comentada y consultar versiones antes de filtrar estado. Evita devolver recibidos antiguos como pendientes.
- Historial web: conservar la fuente mock comentada y conectarlo al GET real, con carga/error y actualización. Los mocks solo se usan con ?demo=1.
- Cliente web nuevo sin escritura ni IA; no introduce claves ni funcionalidades clínicas.
- Pruebas reales son opt-in; las suites habituales no llaman servicios reales.

## Pruebas automáticas

Backend/Laura después de las correcciones: 148 aprobadas, cuatro pruebas reales excluidas en la suite habitual.
OCI real: cuatro aprobadas (archivo y tres estados JSON).
Flutter HTTP real: una aprobada. Flutter analyze y suite completa registrados al finalizar esta revisión.
Web: diez pruebas locales aprobadas y prueba HTTP real del cliente/adaptador aprobada.
Las pruebas de cámara siguen siendo simuladas; no certifican hardware Android ni orientación física.
La interfaz web en navegador requiere aceptación manual; la prueba HTTP del cliente no equivale a haber operado todas sus pantallas.

## Evidencias y objetos

Evidencia Gemini y OCI mixto: C:/Users/leno/AppData/Local/Temp/MediFlow-live-integration-86d89e4f4a864e8a93fc117a02e943b9.
Evidencia Flutter/web HTTP: C:/Users/leno/AppData/Local/Temp/MediFlow-full-e2e.
El primer intento dejó la foto sintética DOC-CLIN-78AB7167040D49E18FA3DC5358B9C906 sin JSON, antes de la corrección.
La prueba mixta dejó DOC-CLIN-9216A101911F4B448B6D1B50DCF76EB4 con foto y JSON recibido, consultable.
El TXT sintético Flutter y su JSON también se conservan para evidencia; el ID consta en flutter-http.json.
Los JSON primitivos de prueba y el TXT de la prueba OCI original se borraron solo por sus nombres únicos creados en esa ejecución. No se tocaron otros objetos.
No se imprimieron claves ni datos clínicos reales en logs. La revisión del historial recupera documentos del bucket localmente, pero no los envía a Gemini.

## Pendientes de cierre

- Gemini disponible y una respuesta real de extracción validada contra el contrato.
- Pruebas clínicas de calidad y urgencia acordadas por Nicolás/Laura/Eliana; la estructura válida no demuestra exactitud clínica.
- Auditoría/aprobación conectadas, autenticación por documento y otras pantallas web siguen pendientes; no se sustituyeron por mocks presentados como realidad.
- No hay reprocesamiento idempotente; no insistir con reenvíos de la misma foto.
- No se declara lista para exposición pública con documentos reales.

Rama feature/s3-edil-resultados; sin commit ni push y main intacta. Servidores de prueba solo en loopback, distintos de los del usuario.


## Cierre de la verificación

Flutter analyze: sin problemas. Suite Flutter habitual: 130 aprobadas y una prueba HTTP real omitida por ser opt-in; esa prueba se ejecutó aparte y aprobó.
El resultado completo sigue bloqueado por una respuesta real válida de Gemini. No se declara aprobación total.
El arranque BAT informa ahora que el historial consulta la API y que las demás pantallas siguen siendo prototipos.
