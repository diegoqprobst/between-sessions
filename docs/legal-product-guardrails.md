# Guardrails de producto y legales — antes de un piloto real

> No es asesoría legal. Este documento fija requisitos de producto para revisión por un abogado de privacidad/salud digital antes de lanzar fuera de datos sintéticos en EE. UU.

## Posicionamiento obligatorio

- Between Sessions es una herramienta de bienestar general que acompaña, registra y resume; no diagnostica, trata, monitoriza una enfermedad ni sustituye atención profesional o emergencias.
- No usar lenguaje de enfermedad, umbrales clínicos, "riesgo" automatizado, diagnóstico, tratamiento ni recomendaciones de manejo médico en UI, marketing, retos o notificaciones.
- Los retos son opcionales y de baja intensidad. No prescribir ejercicio, hidratación, sueño, dieta, medicación o atención clínica.
- La UI debe mostrar siempre el acceso a ayuda de emergencia y una indicación clara de que la app no es un servicio de emergencia. La ruta y el contenido exactos requieren revisión por jurisdicción.

## Controles que deben existir antes de conectar datos reales

1. Consentimiento granular y revocable por cada fuente (salud, Slack, voz, video) y por cada finalidad (acompañar, resumen para clínico, investigación). Nada preseleccionado.
2. Minimización: almacenar solo la señal agregada necesaria; cámara y audio apagados por defecto. La voz no se graba ni se envía hasta que el usuario confirme. Video no entra al MVP.
3. Controles visibles: pausar, borrar, exportar y excluir una señal; cumplirlos de verdad en almacenamiento, colas, backups y proveedores.
4. Prohibición técnica y contractual de acceso del empleador a datos individuales, conversaciones, grabaciones, señales o inferencias. No usar Slack corporativo como canal si el employer puede retener/administrar el contenido sin un acuerdo y una explicación clara al usuario.
5. Cifrado en tránsito y reposo, control de acceso por usuario, registros de acceso, retención limitada, borrado verificable, gestión de incidentes y pruebas de seguridad.
6. Inventario de proveedores, DPA/contratos, evaluación de transferencia de datos, y no usar datos de salud para entrenamiento, anuncios, profiling o venta sin consentimiento explícito y asesoramiento legal.
7. Evaluación separada para menores, ubicaciones fuera de EE. UU. y leyes estatales de datos de salud. Bloquear el servicio para grupos/regiones no aprobados.

## Muro empleador–empleado

La empresa puede patrocinar el beneficio y ofrecer recursos generales, pero no es destinataria de información individual. Si se ofrece reporting organizacional, debe ser voluntario, agregado, con un umbral mínimo de cohorte aprobado por abogado, sin texto libre, sin timestamps individuales y sin posibilidad de identificar, clasificar, penalizar o gestionar el desempeño de una persona. El backend debe separar identidades, permisos y almacenamiento del programa corporativo del espacio personal del usuario.

## HIPAA y notificación de brechas

HIPAA no se resuelve con un disclaimer. Si la app crea, recibe, mantiene o transmite PHI para un proveedor/entidad cubierta, puede actuar como business associate y requerir BAA, salvaguardas y procesos HIPAA. Si es una app de consumo no cubierta por HIPAA, la FTC Health Breach Notification Rule puede aplicar, especialmente al combinar wearable y entradas del usuario.

## Puerta de lanzamiento

No lanzar con datos reales hasta completar: abogado de salud digital, mapa de datos, clasificación HIPAA/FTC/estatal, aviso de privacidad y términos coherentes con la implementación, DPIA/assessment de riesgo, plan de incidentes, evaluación de proveedores, pruebas de borrado y revisión de seguridad.
