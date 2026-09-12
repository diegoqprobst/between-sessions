# Entrega

## Título
Between Sessions — mental health for remote workers, inside the tool they already live in

## Descripción (portal)
Most agents wait in a chat window. Between Sessions lives where a remote worker's week actually happens: a private Slack DM, guided by an Apple Watch and bounded by a plan agreed with a therapist or coach. The session stays local on the clinician's Mac; only a structured plan goes to the cloud. A short night, an HRV drop, a logged low mood, 48 hours of silence or a homework day can prompt one short check-in — never on a schedule, never at night. The worker controls sharing and approves every one-page brief before it reaches the clinician. The employer sees nothing. Synthetic data only.

## Video (2:00)
0:00 Título + "Los agentes esperan en un chat. Este vive en el DM de Slack donde transcurre la semana laboral remota."
0:10 Sala: Quinde local → puente → "solo esto sube" (plan JSON en pantalla).
0:35 Trabajo: Watch → señal de sueño corto → Trigger.dev dispara → pregunta por DM de Slack → dos respuestas → cierre.
1:15 Control: 'no compartas sueño' + push de Auth0 en el celular → aprobar → correo con el brief.
1:45 Tesis: "Confidencialidad por control: quién ve qué está en la arquitectura." Partners y qué hizo cada uno.

Antes de grabar: correr el puente una vez para calentar Ollama; `scripts/seed_week.py ana`; bot de Slack conectado por Socket Mode y DM abierto.

## Post
Built today at #AgentsEverywhere (@aitinkerers × @OpenAI, Miami): Between Sessions — the agent that lives *between* therapy sessions.
The session stays local. Only the plan goes up. An Apple Watch decides when to ask, a private Slack DM is where it asks, and the worker approves with a push what the clinician gets to see. The employer sees nothing.
Thanks @auth0 (consent + CIBA push), @triggerdotdev (waitpoints), @mozilla_ai (any-llm), and @OpenAI (agents and moderation). Repo + 2-min demo: <link>
