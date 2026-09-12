# AGENTS.md — contexto de trabajo para Codex / cualquier agente

Lee primero: `docs/superpowers/specs/2026-09-11-between-sessions-design.md` (qué y por qué) y
`docs/superpowers/plans/2026-09-12-between-sessions.md` (cómo, tarea por tarea, con código y horario).
Este archivo es el resumen operativo: estado real, cómo correr, qué falta, y trampas conocidas.

## Qué es

**Between Sessions**: el agente que vive entre sesiones de terapia. Hackathon *Agents, Everywhere*
(AI Tinkerers × OpenAI, Miami, 12 sep 2026). Entrega a las 16:00: repo público, descripción, video de 2 min, post.

- La sesión se documenta en local con Quinde (`~/Terapias`, repo `quinde-clinica-local`). **No se toca ese repo.**
- El puente `bridge/quinde_plan.py` lee la nota C-SOAP (JSON) y sube **solo el plan** (qué vigilar, tarea, fechas).
- Encuadre final (12 sep, tarde): **salud mental del trabajador remoto**. Canal principal **Slack DMs** (`server/slack_app.py`, Socket Mode, `uv run python -m server.slack_app`); WhatsApp es el segundo canal. El id de paciente lleva prefijo (`slack:U…` o `whatsapp:+…`) y `server/channels/__init__.py` enruta la respuesta. Comando `plan: a; b | tarea: c` para plan propio sin terapeuta.
- El Apple Watch (Health Auto Export → `POST /health/{token}`) decide cuándo hablar.
- La víspera de la sesión, el brief de una página va al terapeuta **solo si el paciente aprueba** (push Auth0 CIBA, o "sí" por WhatsApp si Auth0 no está configurado).
- Tesis: confidencialidad por control. Sala local, nube solo plan, bolsillo con consentimiento, al terapeuta solo señal.

## Reglas duras

- Datos 100 % sintéticos en repo, video y post. Nada real de pacientes ni de clientes.
- Verbos permitidos: acompaña, registra, resume para el terapeuta. Prohibidos: detecta, diagnostica.
- Guardrail falla cerrado: sin veredicto, el mensaje no llega al modelo.
- Toda la lógica en Python (`server/`). `orchestrator/` (Trigger.dev, TS) solo programa, espera y reintenta por HTTP.
- Commits pequeños y frecuentes; el historial es parte de la entrega.

## Estado real (12 sep, mediodía)

**Hecho y probado sin credenciales:**
- `uv run pytest` → 17 tests verdes (reglas de disparo, normalizador de Salud, comandos, parser de Llama Guard).
- Servidor levanta con rutas: `/health`, `/health/{token}`, `/twilio/webhook`, `/plans`, `/decide`, `/checkin`, `/brief`.
- Recorrido local (Twilio en modo impresión): alta por WhatsApp → nombre → siembra de señales → plan → `decide` devuelve `sleep_drop` hoy → comandos `pausa`, `no compartas sueño`.
- Puente con Ollama (`qwen3:14b`, ~90 s la primera vez por carga del modelo) extrae el plan correcto de `fixtures/nota_quinde_ejemplo.json`.

**Escrito pero NO probado (necesita credenciales en `.env`):**
- Llamadas al modelo (OpenRouter → `openai/gpt-5.4-mini`) en `server/agent/checkin.py` y `server/agent/brief.py`.
- Guardrail Llama Guard 4 por OpenRouter (`server/guard.py`).
- Envío real por WhatsApp (Twilio Sandbox) y validación de firma.
- Trigger.dev (`orchestrator/`): falta `npx trigger.dev@latest login` e `init` con el project ref; el endpoint REST para completar waitpoints desde Python (`server/trigger_client.py`) está escrito según docs, sin verificar.
- Auth0 CIBA (`server/auth/ciba.py`): requiere app con grant CIBA, Guardian push y `auth0_sub` del paciente en la BD.
- Correo SMTP (`server/mail.py`): sin `SMTP_USER/PASS` imprime en consola.
- Cloud Run: proyecto `between-sessions-2026` creado y fijado en gcloud; **sin cuenta de facturación vinculada**, así que las APIs no están activadas. Alternativa válida para el demo: servidor local + ngrok.

## Cómo correr

```bash
uv sync                                    # Python 3.12 fijado con uv
uv run pytest -q
cp .env.example .env                       # rellenar: OPENROUTER_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PUBLIC_URL (ngrok), THERAPIST_EMAIL
uv run uvicorn server.app:app --port 8000 --reload          # terminal 1
ngrok http --url=TU-DOMINIO.ngrok-free.app 8000             # terminal 2
# Twilio Console → Messaging → Try it out → WhatsApp Sandbox → "When a message comes in" = https://TU-DOMINIO/twilio/webhook
```

Pruebas locales sin Twilio real: `TWILIO_VALIDATE=0` en `.env` y `scripts/twilio_inbound.sh "+13055550100" "hola"`.
Si `TWILIO_ACCOUNT_SID` está vacío, `wa.send` imprime en consola en vez de enviar.

Flujo mínimo de prueba:
1. WhatsApp: "hola" → bienvenida; "Ana" → confirmación (crea `ref=ana`).
2. `uv run python scripts/seed_week.py ana` → sube 7 días (desplazados para que la noche corta sea HOY) + plan (sesión hace 6 días, próxima mañana) + `decide` → debe devolver `sleep_drop`.
3. `curl -X POST localhost:8000/checkin -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' -d '{"patient_id":1,"trigger":"sleep_drop"}'` → una pregunta al WhatsApp; responder; cierra en ≤ 2 turnos; ver `sqlite3 between.sqlite "select * from checkins"`.
4. `curl -X POST localhost:8000/brief -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' -d '{"patient_id":1,"force":true}'` → sin Auth0: WhatsApp "¿Lo envío?" → "sí" → correo (o impresión en consola).
5. Puente real: `uv run python bridge/quinde_plan.py fixtures/nota_quinde_ejemplo.json --next-session 2026-09-13` (añade `--dry-run` para no publicar).
6. Trigger.dev: `cd orchestrator && cp .env.example .env` (TRIGGER_PROJECT_REF, SERVER_URL=ngrok, THERAPIST_KEY) `&& npx trigger.dev@latest dev` → en el dashboard, Test → `evaluate-signals`. Copiar la secret key del entorno dev a `TRIGGER_SECRET_KEY` del `.env` del servidor.

## Variables de entorno (`.env.example` tiene todas)

`EXA_API_KEY` (comando `sugerir`, opcional) · `SLACK_BOT_TOKEN` (xoxb) · `SLACK_APP_TOKEN` (xapp, Socket Mode) · `OPENROUTER_API_KEY` (principal) · `OPENROUTER_DATA_COLLECTION=deny` · `OPENROUTER_ZDR=0` · `OPENAI_API_KEY` (alternativa; con `FORCE_OPENAI=1` fuerza OpenAI directo) · `OPENAI_MODEL` · `GUARD_MODEL` · `TWILIO_*` · `PUBLIC_URL` · `THERAPIST_KEY` · `THERAPIST_EMAIL` · `DB_PATH` · `PATIENT_TZ` · `AUTH0_*` · `TRIGGER_SECRET_KEY` · `TRIGGER_API_URL` · `SMTP_*` · `OLLAMA_MODEL`.

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `server/app.py` | Rutas FastAPI y máquina de estados de la conversación (`handle_inbound`) |
| `server/store.py` | SQLite: `patients`, `plans`, `signals`, `checkins`, `briefs`, `messages` |
| `server/decide.py` | Reglas puras: `sleep_drop`, `hrv_drop`, `low_mood`, `silence`, `homework_day`; anti-spam 20 h; silencio 22–08 |
| `server/signals/health.py` | Health Auto Export JSON → filas diarias |
| `server/guard.py` | Llama Guard 4 (OpenRouter) o moderación OpenAI; falla cerrado; S11 = autolesión → protocolo 988 |
| `server/llm.py` | Cliente OpenRouter/OpenAI, política de privacidad por solicitud, configuración del Agents SDK |
| `server/agent/checkin.py` | Agente de check-in: una pregunta, cierre en ≤ 2 turnos, extracción `Turn` |
| `server/agent/brief.py` | Agente del brief (5 secciones fijas), respeta señales excluidas |
| `server/channels/twilio.py` | Envío, firma, comandos (`pausa`, `reanudar`, `borrar`, `no compartas X`) |
| `server/auth/ciba.py` | Auth0 `/bc-authorize` + polling `/oauth/token` |
| `server/trigger_client.py` | Completar waitpoint token por REST |
| `server/mail.py` | SMTP al terapeuta |
| `bridge/quinde_plan.py` | Local: nota Quinde → plan (any-llm + Ollama) → `POST /plans` |
| `orchestrator/src/trigger/*.ts` | `evaluate-signals` (cron 3 h → `checkin` con waitpoint 6 h), `nightly-brief` (18:00 NY) |
| `scripts/seed_week.py`, `fixtures/*` | Semana sintética, plan de ejemplo, nota de ejemplo, simulador de webhook |
| `Dockerfile`, `deploy.sh` | Cloud Run (requiere billing) |
| `README.md`, `docs/submission.md` | Entrega: descripción, tabla de partners, guion del video, post |

## Añadido el 12 sep (tarde)

- `server/research.py` + comando `sugerir`: busca en dominios de salud pública con Exa y propone 3 focos citados, para quien no llega con plan de terapeuta. Sin `EXA_API_KEY` cae elegantemente a "escríbeme tu plan".
- `llm.model_id()` normaliza el id del modelo según el destino: OpenRouter exige prefijo (`openai/gpt-5-mini`), OpenAI directo lo rechaza. El mismo `.env` sirve para ambos; no vuelvas a poner el prefijo a mano.
- Codex arregló `conversations_open` en `server/channels/slack.py`: sin eso los check-ins programados no podían abrir el DM.

## Proveedor de modelo (12 sep, tarde — IMPORTANTE)

Los créditos del evento son de **Codex, no de API**. Los de OpenRouter los robaron. Así que:

- `server/llm.py` resuelve el proveedor por clave presente: **OpenRouter → Gemini → OpenAI**. `FORCE_PROVIDER` lo fija a mano.
- **Decisión final (12 sep): TODO LOCAL.** `LOCAL_FIRST=1` (por defecto) manda sobre cualquier clave: agente, brief y guardrail corren en Ollama. Es la tesis llevada al final. `LOCAL_FIRST=0` devuelve el mando a la nube si hace falta para grabar.
- **Latencia local medida:** primera llamada ~155 s (carga del modelo), luego 30–45 s por turno con `qwen3:14b`. Calienta el modelo antes de grabar. `/no_think` va inyectado en las instrucciones cuando el proveedor es local.
- **El guardrail local falla en español.** `llama-guard3:1b` acierta las tres frases de ideación en inglés y falla dos de tres en español ("ya no quiero seguir viviendo" → safe). Por eso `guard.py` tiene una **red determinista de frases** que corre ANTES y cuyo veredicto el modelo no puede desdecir. Si tocas el guardrail, no quites esa red.
- Alternativa si hiciera falta: Gemini. Clave gratis en aistudio.google.com, sin tarjeta; endpoint compatible con OpenAI, así que el Agents SDK no cambia. `GEMINI_API_KEY=` en `.env` y ya. Google es patrocinador (Cloud Run).
- `model_id()` normaliza el nombre del modelo al proveedor activo; **deja `OPENAI_MODEL` vacío** salvo que quieras forzar uno.
- El guardrail sigue al proveedor: Llama Guard 4 si hay OpenRouter, si no el propio modelo de chat con el mismo formato de salida (`safe` / `unsafe\nS11`), parseado por la misma función probada. Sin ninguna clave no hay veredicto y el agente calla.
- **El puente sigue en Ollama a propósito**: que la nota clínica se lea en la máquina del terapeuta ES la tesis, no una limitación.

## Pendientes, en orden

1. Rellenar `.env` y probar el flujo mínimo (arriba). Arreglar lo que rompa en las llamadas al modelo: es lo no probado.
2. Verificar que `openai/gpt-5.4-mini` con `provider.data_collection=deny` enruta (si OpenRouter responde "no providers", poner `OPENROUTER_DATA_COLLECTION=allow` y documentarlo).
3. Trigger.dev: login, init, `dev`, correr `evaluate-signals`, confirmar que el waitpoint se completa al responder por WhatsApp.
4. Auth0 (si hay tiempo): tenant, app con grant CIBA, Guardian, `auth0_sub` en la BD. Si no, queda el "sí" por WhatsApp (ya funciona y se dice en el video).
5. SMTP con contraseña de aplicación de Gmail para que el brief llegue por correo.
6. Cloud Run solo si aparece cuenta de facturación (créditos del evento). Si no, ngrok.
7. Grabar el video siguiendo `docs/submission.md`; publicar repo con `gh repo create between-sessions --public --source=. --push`.

## Trampas conocidas

- **Sandbox de WhatsApp:** el paciente debe haber escrito en las últimas 24 h para recibir texto libre; fuera de ventana solo hay 3 plantillas. La sesión del sandbox caduca a los 3 días (`join <código>` de nuevo).
- **`decide` no dispara** si: hora local fuera de 08–22 (`PATIENT_TZ`), hubo check-in en las últimas 20 h, el paciente está en pausa, no tiene `ref`, o tiene un `pending_trigger` abierto. Para repetir en pruebas: `sqlite3 between.sqlite "delete from checkins; update patients set pending_trigger=null, pending_token=null, turns=0"`.
- **Baseline de sueño/HRV** necesita ≥ 3 días previos; el fixture trae 6.
- **Ollama:** primera llamada ~90 s (carga de modelo); correr el puente una vez antes de grabar. `--model qwen3:4b` no es más rápido en frío.
- **any-llm `response_format`** con Pydantic puede no estar soportado en la versión instalada; el puente ya cae a `json_object`.
- **Agents SDK vía OpenRouter** usa `chat_completions` (no Responses API); `output_type` se traduce a `response_format` json_schema. Si un modelo no soporta structured outputs, cambiar `OPENAI_MODEL`.
- **Trigger.dev waitpoint REST** (`/api/v1/waitpoints/tokens/{id}/complete`) no se ha verificado; si falla, completar desde una task TS que reciba el resultado por `tasks.trigger`.
- **CIBA** requiere que el `binding_message` tenga ≤ 64 caracteres y solo ciertos símbolos; ya se recorta.
