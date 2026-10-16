# Integración de todas las ramas disponibles — 15 de octubre de 2026

Agregado por Edil: el usuario pidió incorporar las ramas a main. Este documento
actualiza los informes anteriores: integración Git no significa aceptación
clínica ni conexión automática de todos los módulos al pipeline.

## Punto de partida y preservación

- main y origin/main estaban en e56794b, sin cambios locales.
- Se ejecutó git fetch origin antes de comparar las ramas.
- Respaldo local: backup/main-antes-integracion-ramas-2026-10-15.
- No se aplicaron ni eliminaron los dos stashes existentes ni otros worktrees.
- No se hizo push. Las referencias remotas no se modifican por estos merges.

## Ramas incorporadas

| Rama | Entrega | Decisión de integración |
| --- | --- | --- |
| feature/s3-score-confianza | Laura, e9c7834 | Merge normal: módulo, 20 pruebas y documentación nuevos. |
| Sprint-2-Nico | Entrega hasta b07e86a | Merge con estrategia ours: prompt, esquema, reglas y cliente ya incorporados y adaptados en bfa9378/7a4a28e. No restaurar un cliente paralelo ni retirar la protección de pruebas reales. Originales en docs/integration/entregas-originales/Sprint-2-Nico y en Git. |
| correccion_conexion_OCI | Eliana, 2bf041f | Merge con estrategia ours: conservar la guía ya incorporada con aclaraciones de rutas, perfil y tres buckets. Original en docs/integration/entregas-originales/correccion_conexion_OCI y Git. |
| feature/S2-triage-oci | Drazen, c839a90 | Merge con estrategia ours: carga de mediflow/.env ya cubierta por environment.py y OCISettings; no activar otro Settings con múltiples rutas y otras opciones de proveedor. config.py original preservado como texto en entregas-originales/drazen/config-c839a90.py.txt y en Git. |
| feature/S3-implementacion_get | Drazen, 2d8bb03 | Merge con estrategia ours: GET, JSON y pruebas incorporados en 18158b0 con correcciones de errores, paginación y persistencia. Originales de rutas/cliente conservados como texto y en Git. |
| feature/contratoJSON | Eliana, 0cc8424/bcefff1 | Merge con estrategia ours: medicamentos y justificación obligatoria ya adoptados; conservar ejemplo compatible con tres buckets, sin volver al bucket anterior. |
| feature/validacion-salida-llm | Laura, f9003ad | Merge con estrategia ours: siete pruebas y documentación ya adoptadas; Nicolás trasladó las pruebas a data_ai/test. No duplicarlas en la ubicación anterior. |

La estrategia ours registra los commits originales como antecesores sin sustituir
el árbol actual por versiones antiguas. Estas seis ramas no aportaron cambios de
archivos en este turno porque sus entregas útiles ya estaban adaptadas. Se deja
esta decisión explícita para no presentar un merge de historial como código nuevo.

Las demás ramas remotas ya eran antecesoras de main: Mediaflow_flutter, develop,
Sprint-3-01-Nico, integration/sprints-1-2 y sprint2-s2-06.

## Correcciones posteriores explicadas en el código

1. Detector: buscar el catálogo en rules/, donde está el archivo entregado.
   La ruta anterior permanece comentada.
2. Pruebas trasladadas: corregir rutas a backend/data_ai y agregar conftest para
   ejecutar conjuntamente imports originales y de paquete, sin instalar módulos.
3. Adaptador: permitir imports como paquete y como script. Import anterior comentado.
4. Score: una alerta crítica obliga a revisión aunque el umbral sea cero;
   conservar la fórmula original y validar el umbral antes de combinar la alerta.
5. Rechazar booleanos como score/completitud/umbral: True no debe aceptarse como 1.
6. Seis regresiones nuevas prueban catálogo, import de paquete y casos límite.

## Pruebas

Backend y toda data_ai: 190 aprobadas, 21 subcasos aprobados, cuatro pruebas reales
OCI excluidas. Dos advertencias de deprecación de dependencias, sin fallos.
Web: diez aprobadas. Sin cambios Flutter en esta integración; la auditoría del
mismo día ejecutó 130 pruebas Flutter aprobadas, una optativa omitida y analyze
sin problemas. No se repitió esa suite sin cambios en Flutter.

Comando conjunto desde mediflow/backend (usar un --basetemp nuevo si el temporal
predeterminado de pytest tiene permisos de otro usuario):

    .\.venv\Scripts\python.exe -m pytest tests ..\data_ai -m "not integration" -q -p no:cacheprovider

No se llamaron servicios reales OCI/Gemini ni se enviaron documentos.

## Pendientes funcionales que los merges no resuelven

- El pipeline aún llama Gemini directamente: no invoca el detector ni el score.
- Acordar campos aplicables/críticos, umbral y persistencia de señales sin cambiar
  unilateralmente el contrato. El módulo de score recibe criterios; no los define.
- Resolver la discrepancia del README de Nicolás que dice no requerir adaptador,
  aunque el archivo sigue entregado; se conserva hasta acuerdo del equipo.
- No hay aprobación/corrección humana persistida desde la web.
- Sigue pendiente una respuesta real exitosa de Gemini y aceptación manual de cámara.
- Sin autorización por documento, no exponer GET con documentos clínicos reales.
- No se declara validación clínica ni integración funcional total por fusionar ramas.
