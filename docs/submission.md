# Entrega

## Título
Between Sessions — the agent that lives between therapy sessions

## Descripción (portal)
Most agents wait in a chat window. Between Sessions lives where therapy actually happens: in the room, and in the week between rooms. The session is documented locally (audio never leaves the therapist's Mac); only a structured plan goes to the cloud. During the week a WhatsApp agent accompanies the patient, but the Apple Watch decides when it speaks: a short night, a drop in HRV, a logged low mood. The night before the next session the therapist receives a one-page brief the patient approved with a push on their phone. Confidentiality by control: who sees what is in the architecture. Built for patients and their therapists. Synthetic data only.

## Video (2:00)
0:00 Título + "Los agentes esperan en un chat. Este vive entre sesiones de terapia."
0:10 Sala: Quinde local → puente → "solo esto sube" (plan JSON en pantalla).
0:35 Bolsillo: Watch → señal de sueño corto → Trigger.dev dispara → pregunta en WhatsApp → dos respuestas → cierre.
1:15 Control: 'no compartas sueño' + push de Auth0 en el celular → aprobar → correo con el brief.
1:45 Tesis: "Confidencialidad por control: quién ve qué está en la arquitectura." Partners y qué hizo cada uno.

Antes de grabar: correr el puente una vez para calentar Ollama; `scripts/seed_week.py ana`; ventana de WhatsApp abierta (el paciente escribió hoy).

## Post
Built today at #AgentsEverywhere (@aitinkerers × @OpenAI, Miami): Between Sessions — the agent that lives *between* therapy sessions.
The session stays local. Only the plan goes up. An Apple Watch decides when to ask, WhatsApp is where it asks, and the patient approves with a push what the therapist gets to see.
Thanks @auth0 (consent + CIBA push), @triggerdotdev (waitpoints), @mozilla_ai (any-llm), @googlecloud (Cloud Run). Repo + 2-min demo: <link>
