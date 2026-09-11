# Between Sessions — diseño

**Fecha:** 11 sep 2026 · **Evento:** Agents, Everywhere (AI Tinkerers × OpenAI), Miami, 12 sep 2026
**Autor:** Diego Quinde · **Estado:** aprobado en conversación, pendiente de revisión escrita

## 1. Idea en una línea

El agente que vive *entre* sesiones de terapia. La sesión se documenta en local con
[quinde-clinica-local](https://github.com/diegoqprobst/quinde-clinica-local); del plan de esa
nota salen objetivos a vigilar y una tarea; un agente de bolsillo acompaña la semana por WhatsApp
guiado por las señales del Apple Watch, y la víspera de la siguiente sesión el terapeuta recibe
un brief de una página que el paciente aprobó desde su celular.

## 2. Por qué el entorno importa (tesis para los jueces)

- **Sala → local.** Audio, transcripción y nota nunca salen de la Mac del terapeuta.
- **Nube ← solo el plan.** Sube un JSON estructurado (qué vigilar, qué tarea), nunca lo que dijo
  el paciente.
- **Bolsillo = consentimiento.** El paciente entra con Google (Auth0), elige qué comparte y
  aprueba con un push cada envío al terapeuta (Auth0 CIBA). Puede pausar, borrar o excluir
  señales desde el mismo chat.
- **Watch decide cuándo hablar.** El check-in se dispara por señal (sueño, HRV, ánimo registrado,
  silencio), no por horario. Un chatbox no puede hacerlo.
- **Sala ← señal.** Al terapeuta baja evidencia estructurada, no texto crudo.

Confidencialidad **por control**, no por promesa: quién ve qué está en la arquitectura.

## 3. Alcance del sábado

**Núcleo (no se recorta):** WhatsApp (Twilio Sandbox) · señales del Watch (Health Auto Export
REST) · plan desde Quinde (puente) · check-in por señal con waitpoint · guardrail de riesgo ·
brief con aprobación CIBA enviado por correo.

**Orden de recorte si aprieta:** 1) maquetación bonita del brief → 2) lectura de Gmail vía
`connector_gmail` → 3) guardrail local con any-guardrail (fallback: OpenAI moderation).

**Fuera de alcance:** app iOS, EHR, multi-terapeuta, panel web (CopilotKit solo si sobra tiempo),
producción HIPAA (ver §10).

## 4. Arquitectura

```
┌─ Mac del terapeuta (local) ─────────────┐     ┌─ Cloud Run (Python · FastAPI) ─────────────┐
│ Quinde: audio → nota C-SOAP (JSON)      │     │ /twilio/webhook   ← WhatsApp entrante       │
│ bridge/quinde_plan.py                   │────▶│ /health/{token}   ← Health Auto Export POST │
│   P(plan) → any-llm(Ollama) → plan.json │     │ /plans            ← puente (API key)        │
└─────────────────────────────────────────┘     │ /decide /checkin /brief ← Trigger.dev       │
                                                │ agent/  (OpenAI Agents SDK, Python)         │
┌─ iPhone / Watch ────────┐   POST JSON         │ guard/  (any-guardrail → fallback moderation)│
│ Health Auto Export      │────────────────────▶│ store/  SQLite                              │
└─────────────────────────┘                     │ auth/   Auth0 login · Token Vault · CIBA    │
                                                └───────────────▲───────────────┬────────────┘
┌─ WhatsApp (Twilio Sandbox) ─┐  webhook / REST                 │ HTTP           │ Twilio REST
│ paciente ◀──────────────────┼─────────────────────────────────┼────────────────┘
└─────────────────────────────┘                                 │
                                       ┌─ Trigger.dev (TypeScript, orquestación) ─┐
                                       │ evaluate  cron */3h → /decide → /checkin │
                                       │           wait.forToken (6h) ← respuesta │
                                       │ brief     cron víspera → /brief → CIBA   │
                                       └──────────────────────────────────────────┘
```

**Regla de lenguajes:** toda la lógica (modelo, guardrail, datos, Twilio, Auth0) en Python.
Trigger.dev solo programa, espera y reintenta; llama al servidor por HTTP.

## 5. Componentes

### 5.1 `bridge/` (local, Python)
- `quinde_plan.py <ruta contenido_nota.json>`: lee la nota de Quinde (`paciente`, `fecha`,
  `sesion_num`, `riesgo`, `animo`, `adherencia`, `secciones[]`), toma la sección `letra == "P"`,
  y con any-llm sobre Ollama (`qwen3:14b`, JSON Schema) produce `plan.json`. Lo publica con
  `POST /plans` (header `X-Therapist-Key`).
- Nunca envía `secciones` C/S/O/A. Solo el plan estructurado y metadatos de sesión.

### 5.2 `server/` (Cloud Run, FastAPI)
- `store/`: SQLite. Tablas `patients`, `plans`, `signals`, `checkins`, `briefs`, `consents`.
- `auth/`: Auth0 Universal Login (conexión Google), Token Vault para el token de Gmail,
  CIBA (`/bc-authorize` + polling) para aprobar el brief.
- `channels/twilio.py`: validación de firma, envío por REST, parseo de comandos
  (`pausa`, `reanudar`, `borrar`, `no compartas <señal>`).
- `signals/health.py`: normaliza el POST de Health Auto Export a filas diarias:
  `sleep_h`, `hrv_ms`, `resting_hr`, `steps`, `mood` (de `stateOfMind`).
- `guard/`: `any_guardrail` (Llama Guard / ShieldGemma) con categorías de autolesión →
  si no está disponible, `openai.moderations`. Falla cerrado: sin veredicto, no llega al modelo.
- `agent/`: OpenAI Agents SDK (Python). Dos agentes con herramientas:
  - `checkin_agent`: compone **una** pregunta (≤ 2 líneas) anclada al plan y al disparador;
    cierra en ≤ 2 turnos; extrae `{mood_1_5, homework_done, note, wants_to_discuss}`.
  - `brief_agent`: redacta el brief (§7) desde señales + check-ins de la semana.
- `decide.py`: reglas de disparo (§6). Sin LLM.

### 5.3 `orchestrator/` (Trigger.dev, TypeScript)
- `evaluate.ts` — schedule `0 */3 * * *`: `POST /decide` → por cada paciente disparado,
  `POST /checkin` (devuelve `waitpoint_token`) → `wait.forToken(token, {timeout: "6h"})`.
  El webhook de Twilio completa el token vía API de Trigger.dev. Timeout = no insistir.
- `brief.ts` — schedule diario 18:00 America/New_York: `POST /brief` para pacientes con sesión
  mañana → el servidor lanza CIBA → si aprueba, envía correo.

### 5.4 `fixtures/` y `scripts/`
- `health_sample.json` (una semana sintética, con una noche de sueño corto y un `stateOfMind`
  negativo), `nota_quinde_ejemplo.json` (copiada de `quinde/ejemplo/contenido_nota.json`),
  `twilio_inbound.sh` (curl que simula el webhook), `seed_week.py` (siembra la semana del demo).

## 6. Contratos de datos

```jsonc
// plan.json (puente → /plans)
{ "patient_ref": "ana", "session_num": 3, "session_date": "2026-09-05",
  "next_session_date": "2026-09-12",
  "watch": ["sueño nocturno", "ansiedad anticipatoria antes de dormir"],
  "homework": "Respiración 4-7-8 y bitácora nocturna",
  "next_focus": "Revisar adherencia y rutina de sueño",
  "risk_baseline": "none" }

// signal (fila diaria normalizada)
{ "patient_id": 1, "date": "2026-09-08", "sleep_h": 5.1, "hrv_ms": 38, "resting_hr": 64,
  "steps": 4200, "mood": { "valence": -0.6, "labels": ["ansioso"] } }

// checkin (resultado)
{ "patient_id": 1, "at": "...", "trigger": "sleep_drop", "question": "...",
  "mood_1_5": 2, "homework_done": false, "note": "…", "wants_to_discuss": "…",
  "risk_flag": false }
```

**Reglas de disparo (`decide.py`):** `sleep_h < baseline − 1.5` · `hrv_ms < 0.8 × baseline` ·
`mood.valence ≤ −0.5` · sin señal ≥ 48 h · día de tarea (cada 2 días). Baseline = mediana de
los 14 días previos; si hay < 3 días, no se disparan sueño/HRV. **Anti-spam:** máximo un
check-in por 20 h y nunca entre 22:00 y 08:00 hora del paciente.

## 7. El brief (víspera de sesión)

Una página, en este orden: 1) **bandera de riesgo** si la hubo; 2) tendencia de sueño;
3) tarea hecha o no y cómo fue; 4) trayectoria del ánimo con los 2–3 momentos de caída;
5) lo que el paciente quiere tratar, en sus palabras. Envío por correo al terapeuta
(Gmail API con token del Token Vault; fallback SMTP). Solo tras aprobación CIBA.

## 8. Fallos y límites conocidos

| Situación | Comportamiento |
|---|---|
| Sin señal del Watch | El agente pregunta igual, sin contexto fisiológico |
| Sin respuesta en 6 h | El waitpoint expira; no se insiste; se registra `no_reply` |
| Guardrail caído | Falla cerrado: respuesta fija + aviso interno; el modelo no ve el mensaje |
| Riesgo detectado | Mensaje con línea 988 (EE. UU.) / 911; aviso al terapeuta según consentimiento inicial |
| Ventana de 24 h del Sandbox | Fuera de ventana solo hay 3 plantillas fijas. En el demo el paciente abre la ventana; en producción, plantillas aprobadas o SMS (mismo canal Twilio). Se dice en el video |
| Rechazo CIBA o timeout | El brief no se envía; el terapeuta recibe solo "el paciente no aprobó compartir" |
| Comandos del paciente | `pausa` detiene disparos; `borrar` elimina señales y check-ins; `no compartas sueño` excluye la señal del brief |

## 9. Pruebas

- Cada endpoint tiene un fixture y un `curl` en `scripts/`. Pruebas unitarias en `decide.py`
  (reglas puras) y en `signals/health.py` (normalización).
- `scripts/seed_week.py` siembra la semana del demo de punta a punta.
- Prueba manual del video: Health POST → cron manual → WhatsApp real en el teléfono de Diego →
  respuesta → brief → push CIBA en el celular → correo recibido.

## 10. Lenguaje, legal y mercado (EE. UU.)

- **Verbos:** "acompaña", "registra", "resume para el terapeuta". Nunca "detecta", "diagnostica".
- **Datos:** 100 % sintéticos en repo, video y post. Nota en README.
- **HIPAA:** no aplica al demo. El agente es del paciente (app de consumidor → regla FTC de
  brechas de salud y leyes estatales, no HIPAA). WhatsApp vía Twilio no es elegible HIPAA; SMS
  sí. OpenAI exige Enterprise + ZDR para BAA. Se documenta como "camino a producción".
- **Riesgo:** 988 en EE. UU.; plan de aviso consentido al alta.
- **Competencia:** Mentalyc y Upheal (nota), Blueprint (medición entre sesiones). Diferencia:
  sala local + Watch decide cuándo hablar + aprobación por push.

## 11. Sponsors y dónde vive cada uno

| Sponsor | Uso | Archivo |
|---|---|---|
| OpenAI | Agents SDK (check-in y brief), `connector_gmail` opcional | `server/agent/` |
| Auth0 | Login Google, Token Vault (Gmail), CIBA (aprobar brief) | `server/auth/` |
| Trigger.dev | cron, waitpoints, reintentos | `orchestrator/` |
| Mozilla.ai | any-guardrail (riesgo), any-llm (puente local con Ollama) | `server/guard/`, `bridge/` |
| Google Cloud Run | hosting del servidor | `Dockerfile`, `deploy.sh` |
| Twilio (no sponsor) | WhatsApp Sandbox | `server/channels/twilio.py` |
| Health Auto Export (no sponsor) | señales del Watch | `server/signals/health.py` |

## 12. Entregables del sábado

Título · descripción · repo público (este) · video 2 min · post etiquetando sponsors.
README en inglés con sección "How we used each partner" y "Path to production".
