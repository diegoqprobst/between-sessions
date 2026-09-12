from agents import Agent, Runner
from server import config
from server import llm

INSTRUCTIONS = """Redactas, para un psicólogo, el brief de una página previo a la sesión con su paciente. Español, sobrio, sin diagnosticar.
Formato exacto en markdown, en este orden y con estos títulos:
## Riesgo  (solo si hubo bandera; si no, escribe "Sin señales de riesgo esta semana.")
## Sueño  (tendencia en palabras, con el o los días más cortos)
## Tarea  (hecha o no, y cómo le fue, según los check-ins)
## Ánimo  (trayectoria y los 2–3 momentos de caída, con fecha)
## Quiere tratar  (en palabras del paciente; si no dijo nada, "No indicó temas.")
Usa solo los datos dados. No inventes. Si una señal está excluida por el paciente, no la menciones y no expliques por qué.
"""

def _instructions() -> str:
    return ("/no_think\n" + INSTRUCTIONS) if llm.is_local() else INSTRUCTIONS

_agent = Agent(name="brief", instructions=_instructions(), model=llm.model_id(),
               model_settings=llm.model_settings())

EXCLUDE_MAP = {"sueño": ("sleep_h",), "sleep": ("sleep_h",), "ánimo": ("mood_valence", "mood_labels"),
               "animo": ("mood_valence", "mood_labels"), "corazón": ("hrv_ms", "resting_hr"), "hrv": ("hrv_ms",)}

def compose(patient: dict, plan: dict | None, signals: list[dict], checkins: list[dict], excluded: list[str]) -> str:
    drop = {k for e in excluded for k in EXCLUDE_MAP.get(e.strip().lower(), ())}
    clean = [{k: v for k, v in s.items() if k not in drop and k not in ("id", "patient_id")} for s in signals]
    risk = any(c.get("risk_flag") for c in checkins)
    data = (f"Paciente: {patient.get('name')}. Sesión previa: {plan.get('session_date') if plan else '?'}. "
            f"Plan — vigilar: {', '.join(plan.get('watch', [])) if plan else '-'}; tarea: {plan.get('homework') if plan else '-'}.\n"
            f"Hubo bandera de riesgo: {'sí' if risk else 'no'}.\nSeñales diarias: {clean}\n"
            f"Check-ins: {[{k: c.get(k) for k in ('at','trigger','mood_1_5','homework_done','note','wants_to_discuss')} for c in checkins]}")
    return Runner.run_sync(_agent, data).final_output
