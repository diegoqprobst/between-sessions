from agents import Agent, Runner
from server import config
from server import llm

INSTRUCTIONS = """Redactas, para un psicólogo, el brief de una página previo a la sesión con su paciente. Español, sobrio, sin diagnosticar.
Formato exacto en markdown, en este orden y con estos títulos:
## Riesgo  (solo si hubo bandera; si no, escribe "Sin señales de riesgo esta semana.")
## Sueño  (tendencia en palabras, con el o los días más cortos)
## Tarea  (usa el estado ya resuelto que se te da; no lo contradigas)
## Ánimo  (trayectoria y los 2–3 momentos de caída, con fecha)
## Quiere tratar  (en palabras del paciente; si no dijo nada, "No indicó temas.")
Devuelve markdown plano, SIN envolverlo en bloques de código. Usa solo los datos dados. No inventes. Si una señal está excluida por el paciente, no la menciones y no expliques por qué.
"""

def _instructions() -> str:
    return ("/no_think\n" + INSTRUCTIONS) if llm.is_local() else INSTRUCTIONS

_agent = Agent(name="brief", instructions=_instructions(), model=llm.model_id(),
               model_settings=llm.model_settings())

EXCLUDE_MAP = {"sueño": ("sleep_h",), "sleep": ("sleep_h",), "ánimo": ("mood_valence", "mood_labels"),
               "animo": ("mood_valence", "mood_labels"), "corazón": ("hrv_ms", "resting_hr"), "hrv": ("hrv_ms",)}

def strip_fences(text: str) -> str:
    """Los modelos devuelven el markdown envuelto en ```markdown … ```. El brief se manda
    por correo y se pinta en el panel, así que las marcas sobran."""
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    while lines and not lines[-1].strip().startswith("```"):
        break
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()

def homework_summary(checkins: list[dict]) -> str:
    """Resuelve la tarea a UN estado. Pasar los check-ins crudos hacía que el modelo
    escribiera 'no completó la tarea' y en la frase siguiente que sí la hizo."""
    answered = [c for c in checkins if c.get("homework_done") is not None]
    if not answered:
        return "No se habló de la tarea esta semana."
    done = sum(1 for c in answered if c["homework_done"])
    notes = " ".join(c.get("note") or "" for c in answered if c.get("note"))
    if done == len(answered):
        return f"La hizo, según los {len(answered)} check-ins en que se habló. {notes}"
    if done == 0:
        return f"No la hizo en ninguno de los {len(answered)} check-ins en que se habló. {notes}"
    return f"Parcial: la hizo en {done} de {len(answered)} check-ins. {notes}"

def compose(patient: dict, plan: dict | None, signals: list[dict], checkins: list[dict], excluded: list[str]) -> str:
    drop = {k for e in excluded for k in EXCLUDE_MAP.get(e.strip().lower(), ())}
    clean = [{k: v for k, v in s.items() if k not in drop and k not in ("id", "patient_id")} for s in signals]
    risk = any(c.get("risk_flag") for c in checkins)
    data = (f"Paciente: {patient.get('name')}. Sesión previa: {plan.get('session_date') if plan else '?'}. "
            f"Plan — vigilar: {', '.join(plan.get('watch', [])) if plan else '-'}; tarea: {plan.get('homework') if plan else '-'}.\n"
            f"Hubo bandera de riesgo: {'sí' if risk else 'no'}.\n"
            f"Estado de la tarea (ya resuelto, úsalo tal cual en la sección Tarea): {homework_summary(checkins)}\n"
            f"Señales diarias: {clean}\n"
            f"Check-ins: {[{k: c.get(k) for k in ('at','trigger','mood_1_5','homework_done','note','wants_to_discuss')} for c in checkins]}")
    return strip_fences(Runner.run_sync(_agent, data).final_output)
