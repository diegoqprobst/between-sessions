# Contrato frontend ↔ backend

**Reparto:** Codex hace el panel (`web/`). Claude hace el servidor (`server/`). Nadie toca la carpeta del otro.

## Decisión de stack (sin build, a propósito)

| Decisión | Qué | Por qué |
|---|---|---|
| **Sin npm, sin build** | Un `web/index.html` servido por el mismo FastAPI en `/panel` | No hay segundo servidor, no hay CORS, no hay `npm run build` que falle a las 15:20. Se despliega en el mismo contenedor de Cloud Run |
| **CSS** | Tailwind por CDN (`<script src="https://cdn.tailwindcss.com">`) | Cero configuración, y ya sabemos que carga |
| **JS** | Vanilla + `fetch`. Sin React, sin bundler | La página es de solo lectura; un framework no aporta nada en 2 horas |
| **Gráficas** | Chart.js por CDN, o SVG a mano | Solo hay una gráfica: sueño de 14 días. Si Chart.js da guerra, una línea en SVG sirve igual |
| **Estado** | Ninguno. La página lee y pinta | Toda la escritura pasa por Slack, nunca por el panel |

**Regla de oro:** el panel es **de solo lectura**. Nadie aprueba ni comparte nada desde aquí. La aprobación vive en el push del celular y en el DM de Slack, porque esa es la tesis del proyecto.

## Cómo levantar

```bash
uv run uvicorn server.app:app --port 8000 --reload
uv run python scripts/seed_week.py diego   # datos sintéticos; el paciente debe existir (un 'hola' por Slack o el simulador)
open http://localhost:8000/panel
```

Sin base de datos sembrada el panel se ve vacío: eso es correcto, no es un bug.

## Endpoints (todos `GET`, todos JSON, sin auth en el demo)

### `GET /api/patients`
```json
{"patients": [{"id": 1, "name": "Diego", "ref": "diego", "channel": "slack",
               "consent": {"paused": 0, "excluded_signals": [], "awaiting_brief": null}}]}
```
`channel` es `"slack"` o `"whatsapp"`. **No se expone el teléfono ni el id de Slack**, a propósito.

### `GET /api/patients/{id}`
Lo anterior más `plan`:
```json
{"id": 1, "name": "Diego", "channel": "slack", "consent": {...},
 "plan": {"session_num": 3, "session_date": "2026-09-05", "next_session_date": "2026-09-13",
          "watch": ["sueño nocturno", "ansiedad anticipatoria antes de dormir"],
          "homework": "Respiración 4-7-8 y bitácora nocturna",
          "next_focus": "Revisar adherencia y explorar rutina de sueño", "risk_baseline": "none"}}
```
`plan` puede ser `null` si el paciente aún no tiene plan.

### `GET /api/patients/{id}/signals?days=14`
```json
{"days": 14, "signals": [{"date": "2026-09-06", "sleep_h": 7.2, "hrv_ms": 52.0,
                          "resting_hr": 58.0, "steps": 6200.0,
                          "mood_valence": null, "mood_labels": null}]}
```
Orden ascendente por fecha. **Cualquier campo puede venir `null`**: el Watch no manda todo todos los días. `mood_valence` va de −1 a 1; `mood_labels` es lista o `null`.

### `GET /api/patients/{id}/checkins?days=7`
```json
{"days": 7, "checkins": [{"at": "2026-09-12T15:46:57+00:00", "trigger": "sleep_drop",
                          "mood_1_5": 2, "homework_done": 0, "risk_flag": 0, "status": "done",
                          "note": "Semana de entregas; cortó tarde tres noches.",
                          "wants_to_discuss": "cómo poner límites sin culpa"}]}
```
`trigger` ∈ `sleep_drop · hrv_drop · low_mood · silence · homework_day · spontaneous`.
`status` ∈ `done · risk · no_reply`. `homework_done` y `risk_flag` son 0/1/`null`.

### `GET /api/patients/{id}/brief`
```json
{"at": "...", "content": "## Riesgo\nSin señales de riesgo esta semana.\n## Sueño\n...",
 "approved": false, "sent": false}
```
`content` es markdown con cinco secciones fijas: Riesgo, Sueño, Tarea, Ánimo, Quiere tratar.
**404 si todavía no hay brief** — la página debe tratarlo como estado vacío, no como error.

## Qué debería mostrar el panel (prioridad para el video)

1. **Riesgo arriba del todo**, si algún check-in trae `risk_flag: 1`. Si no, una línea sobria.
2. **Sueño de 14 días**, con el día corto marcado. Es la señal que dispara el demo.
3. **El plan**: qué se vigila y la tarea.
4. **Los check-ins**: qué disparó cada uno, ánimo, tarea sí o no, y qué quiere tratar.
5. **El brief** en markdown, con su estado de aprobación bien visible: "esperando aprobación del paciente" es el momento que vende el proyecto.
6. **Señales excluidas**: si `consent.excluded_signals` trae algo, decir "el paciente excluyó X de este resumen". Si `paused` es 1, decirlo.

## Dónde poner el archivo

`web/index.html`. El servidor ya lo sirve en `/panel`. Si necesitas otro endpoint, pídemelo en vez de leer la base de datos directamente.
