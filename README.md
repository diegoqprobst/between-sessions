# Between Sessions

**Mental health for remote workers, inside the tool they already live in.**

The agent that lives between therapy or coaching sessions. The session is documented locally: audio, transcript and note never leave the clinician's Mac (via [quinde-clinica-local](https://github.com/diegoqprobst/quinde-clinica-local)). Only the structured *plan* goes to the cloud, or the worker sets their own plan from the chat. During the week, an agent in **Slack DMs** (WhatsApp as a second door) accompanies the person, guided by Apple Watch signals: it asks one question when sleep, HRV or a logged mood justifies it, not on a schedule. The night before the next session, the clinician receives a one-page brief, and only after the person approves it. The employer sees nothing, ever.

> Built in one day at *Agents, Everywhere* (AI Tinkerers × OpenAI, Miami, Sept 12 2026). Every piece of data in this repo, the video and the post is synthetic. This tool *accompanies, records and summarizes for a clinician*. It does not detect or diagnose anything.

## Why the environment matters

- **Room → local.** Transcript and note never leave the Mac.
- **Cloud ← plan only.** A JSON of what to watch and the homework. Never what the patient said. See [`bridge/quinde_plan.py`](bridge/quinde_plan.py).
- **Slack DM = consent.** Nothing reaches the clinician until the worker approves that specific brief, in their own DM. `pausa`, `borrar`, `no compartas sueño` work from the same place. The employer sees nothing.
- **The Watch decides when to talk.** Triggers: sleep drop vs. the 14-day median, HRV drop, negative logged mood, 48 h of silence, homework day. At most one check-in per 20 h, never 22:00–08:00. See [`server/decide.py`](server/decide.py).
- **Room ← signal.** The therapist gets structure, not raw text. See [`server/agent/brief.py`](server/agent/brief.py).

Confidentiality *by control*, not by promise: who sees what is in the architecture.

## Architecture

```
Clinician's Mac (local)          FastAPI (Python)                       Trigger.dev (TypeScript)
Quinde: note → plan JSON         /plans   ← plan only                    evaluate-signals  cron */3h
bridge/quinde_plan.py ──────────▶/health  ← Health Auto Export (Watch)    checkin           waitpoint 6h
   any-llm on Ollama             /twilio  ← WhatsApp (optional)           nightly-brief     cron 18:00
                                 /decide /checkin /brief  ← orchestrator
                                 guard · agents · SQLite · Auth0 CIBA · mail

Slack Socket Mode (`server/slack_app.py`) ── private DMs only ──▶ same FastAPI flow
```

## How we used each partner

| Partner | What it does here | Where |
|---|---|---|
| **OpenAI** | Agents SDK for the check-in and brief agents (GPT-5.4 mini) | `server/agent/`, `server/llm.py` |
| **Google** | Cloud Run hosts the server; Gemini is a supported provider via its OpenAI-compatible endpoint | `deploy.sh`, `server/llm.py` |
| **OpenRouter** | Optional routing with a per-request privacy policy (`provider.data_collection: "deny"`, optional `zdr`) plus Llama Guard 4 as a dedicated guardrail. Present key wins; model ids are normalized per provider | `server/llm.py`, `server/guard.py` |
| **Ambiguous AI** | The clinician's side lives in their workspace. The agent is provisioned as a real coworker with its own identity and address (`between@…`), and it delivers the approved brief as a document it authored, plus a task to review it before the session. Email delivery stays the fallback | `server/workspace.py` |
| **Exa** | `sugerir` searches public-health sources (WHO, NIH, CDC, APA, NHS) so a worker without a clinician can pick a weekly focus, each option cited | `server/research.py` |
| **Auth0** | Asynchronous authorization (CIBA) as the stronger form of the same approval gate: a push to the worker's phone instead of a chat reply. Implemented and wired; **not exercised in this demo**, which uses the in-chat approval — see Honest status | `server/auth/ciba.py`, `server/app.py` (`/brief`) |
| **Trigger.dev** | 3-hourly signal evaluation, waitpoint tokens that pause a run until the patient replies, nightly brief | `orchestrator/src/trigger/` |
| **Mozilla.ai** | `any-llm` runs the local bridge on Ollama, so the clinical note is read on the therapist's own machine with the same call shape as the cloud | `bridge/quinde_plan.py` |
| **Google Cloud Run** | Hosts the FastAPI server | `Dockerfile`, `deploy.sh` |
| Slack (Bolt, Socket Mode) | Primary channel: DMs with the bot, where the remote worker already is | `server/slack_app.py`, `server/channels/slack.py` |
| Twilio (not a sponsor) | WhatsApp Sandbox as second channel, signature validation | `server/channels/twilio.py` |
| Health Auto Export (not a sponsor) | Pushes Apple Health JSON (sleep, HRV, resting HR, steps, State of Mind) to our endpoint | `server/signals/health.py` |

## Run it

```bash
uv sync && cp .env.example .env            # fill OPENAI_API_KEY, Slack and THERAPIST_EMAIL
uv run pytest                              # rules, normalizer, commands
uv run uvicorn server.app:app --port 8000  # terminal 1
```

0. Slack: create the app from `slack-manifest.yaml`, enable Socket Mode, create its app-level token with `connections:write`, install it, put `SLACK_BOT_TOKEN` (`xoxb-`) and `SLACK_APP_TOKEN` (`xapp-`) in `.env`, then run `uv run python -m server.slack_app` (terminal 2). The manifest subscribes only to `message.im`; it does not read channels.
1. The person DMs the bot `hola` (Slack) or texts the Sandbox number (WhatsApp), then their name. Optional: `sugerir` for cited suggestions, then `plan: dormir 7h; cortar a las 6 | tarea: caminar 20 min`.
2. Therapist publishes the plan from the local note: `uv run python bridge/quinde_plan.py fixtures/nota_quinde_ejemplo.json --next-session 2026-09-13` (or seed a synthetic week: `uv run python scripts/seed_week.py ana`).
3. Apple Watch data arrives via Health Auto Export → `POST /health/{token}`.
4. `cd orchestrator && npm i && npx trigger.dev@latest dev` and run `evaluate-signals` from the dashboard. The check-in lands in the Slack DM; the run waits up to 6 h for the reply.
5. `nightly-brief` (or `POST /brief` with `{"patient_id":1,"force":true}`) drafts the brief, asks the worker for approval (Auth0 push, or a Slack "sí" when Auth0 is not configured) and emails the clinician.

Every endpoint has a fixture: `fixtures/health_sample.json`, `fixtures/plan_ejemplo.json`, `scripts/twilio_inbound.sh`.

## What the patient controls

`pausa` / `reanudar` stop and resume everything. `borrar` deletes signals, conversations and briefs. `no compartas sueño` (or any signal) excludes it from the brief. Every brief needs an explicit approval; a denial sends the therapist only "the patient chose not to share this week".

## Honest status

What was exercised end to end on build day, in a real Slack workspace against local models: onboarding, Apple Watch signal ingestion, the trigger rules, a real check-in fired by a short night, `sugerir` with live Exa results, brief generation, the approval request, and delivery by email and as a document in the clinician's Ambiguous AI workspace, authored by the agent's own provisioned identity.

Written and tested by unit tests but **not exercised live**: Auth0 CIBA (needs a tenant with the CIBA grant and Guardian enrolled, so the demo uses the in-chat approval instead), Trigger.dev scheduling (the check-in was fired directly against the endpoint), and the WhatsApp channel (the code path is shared with Slack and its command parsing is tested, but the Twilio Sandbox was not used on the day).

We would rather say this than let a reader assume otherwise.

## Safety

Every inbound message passes two layers before any model sees it, and the layers cannot cancel each other out.

1. **A deterministic phrase net** for explicit ideation, in Spanish and English, with common idioms excluded (`me muero de sueño` is not ideation). It runs first and its verdict is final.
2. **A classifier** second: Llama Guard 3 locally, Llama Guard 4 on OpenRouter, or the active chat model using the same output format. It can only *add* risk, never remove it.

The net exists because we tested the classifier and it failed. `llama-guard3:1b` correctly flagged all three English phrasings of suicidal ideation and missed two of three in Spanish, including "ya no quiero seguir viviendo". Since the agent speaks Spanish to the person, shipping the classifier alone would have been a false promise. See `tests/test_guard.py`.

If neither layer can return a verdict, the message is not processed (fail closed). When risk fires, the agent replies with the 988 Suicide & Crisis Lifeline (US) / 911 and notifies the clinician per the plan consented at onboarding. No patient text is included in that notification.

## Path to production (what a hackathon cannot do in a day)

- WhatsApp via Twilio is not HIPAA-eligible; SMS is, on the same code path. The Sandbox's 24 h window means business-initiated messages outside it need approved templates.
- The agent is patient-owned: a consumer health app (FTC Health Breach Notification Rule, state consumer-health laws such as Washington's), not a HIPAA covered entity. A therapist-owned deployment needs BAAs (OpenAI: Enterprise + zero data retention).
- Baselines need ~14 days of real data; the demo seeds a synthetic week.
- Local guardrail (`any-guardrail` with Llama Guard / ShieldGemma) can replace the moderation endpoint where nothing may leave the device.

## Team

Diego Quinde, clinical psychologist and builder. Miami.
