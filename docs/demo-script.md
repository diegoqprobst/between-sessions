# Guion de grabación

**Antes de empezar**
- Terminal a la izquierda, Slack a la derecha en el DM con *Between Sessions*.
- Calienta el modelo (si no, la primera respuesta tarda el doble):
  `uv run python -c "from server import store; from server.agent import checkin as c; c.open_question(store.get_patient(1), store.latest_plan(1), 'sleep_drop', None)"`
- Limpia para poder repetir:
  `sqlite3 between.sqlite "delete from checkins; delete from briefs; update patients set pending_trigger=null, turns=0, awaiting_brief=0;"`
- Graba con `cmd+shift+5`. Las esperas del modelo (30–45 s) se cortan al editar.

---

## 1 · La sala es local (0:10)
> "La sesión se documenta en mi Mac. A la nube sube solo el plan."

```bash
uv run python bridge/quinde_plan.py fixtures/nota_quinde_ejemplo.json --next-session 2026-09-13
```

Señala en pantalla: sube `watch` y `homework`. No sube nada de lo que dijo la persona.

## 2 · El reloj manda la semana (0:30)
> "El Apple Watch envía sueño, variabilidad cardíaca y ánimo."

```bash
uv run python scripts/seed_week.py diego
```

La última línea es la clave: `decide` devuelve `sleep_drop`. **Nadie programó esto: lo decidió una noche corta.**

## 3 · El check-in llega a Slack (0:50)
```bash
curl -s -X POST localhost:8000/checkin -H "x-therapist-key: dev-therapist-key" \
  -H 'content-type: application/json' -d '{"patient_id":1,"trigger":"sleep_drop"}'
```

Cambia a Slack: llega **una** pregunta, anclada al plan. Responde algo real
("dormí fatal, tenía una entrega y me acosté a las dos"). El agente cierra en dos turnos.

## 4 · El control es de la persona (1:15)
En Slack, escribe: `no compartas sueño`
> "Puedo excluir una señal, pausarlo o borrarlo todo. Es mío, no de mi empresa."

## 5 · El brief, solo con permiso (1:30)
```bash
curl -s -X POST localhost:8000/brief -H "x-therapist-key: dev-therapist-key" \
  -H 'content-type: application/json' -d '{"patient_id":1,"force":true}'
```

En Slack llega "¿Lo envío?". Responde `sí`. Abre el correo: el brief está ahí.
> "El terapeuta recibe señal estructurada. Nunca lo que dije."

## 6 · Cierre (1:45)
> "Confidencialidad por control: quién ve qué está en la arquitectura.
> La sala es local, a la nube sube solo el plan, y nada sale sin que yo lo apruebe."

Menciona los partners y qué hizo cada uno: Agents SDK de OpenAI, Exa para las sugerencias
citadas, Slack como canal, Mozilla any-llm para el puente local, Trigger.dev para la
orquestación, Cloud Run para el despliegue.

---

## Si algo falla en cámara
- **El bot no responde:** `pgrep -f server.slack_app` y si no está, `uv run python -m server.slack_app`.
- **`decide` devuelve vacío:** hubo check-in en las últimas 20 h. Limpia con el comando de arriba.
- **Tarda mucho:** el modelo se enfrió. Corta la espera al editar; es un producto asíncrono.
