from pydantic import BaseModel
from agents import Agent, Runner
from server import config
from server import llm

class Turn(BaseModel):
    reply: str
    done: bool
    mood_1_5: int | None = None
    homework_done: bool | None = None
    note: str = ""
    wants_to_discuss: str = ""

TRIGGER_TEXT = {
    "sleep_drop": "anoche durmió bastante menos que su promedio",
    "hrv_drop": "su cuerpo muestra más estrés que de costumbre (variabilidad cardíaca baja)",
    "low_mood": "registró un estado de ánimo negativo en su reloj",
    "silence": "hace dos días que no llega ninguna señal",
    "homework_day": "es día de revisar la tarea acordada con su terapeuta",
    "spontaneous": "escribió por su cuenta",
}

INSTRUCTIONS = """Eres el acompañante entre sesiones de un paciente de psicoterapia. Escribes por WhatsApp, en español, cálido y breve.
Reglas duras:
- Una sola pregunta por mensaje, máximo dos líneas. Nada de listas ni de consejos clínicos.
- No diagnosticas ni interpretas. Acompañas, registras, y preparas un resumen para su terapeuta, que el paciente aprueba.
- Anclas la pregunta al plan de la sesión (qué vigilar, la tarea) y al motivo del contacto.
- Cierras en máximo dos turnos del paciente: agradeces y dices que lo tendrás en cuenta para el resumen.
- Cuando cierras (done=true), extraes: mood_1_5 (1 muy mal, 5 muy bien), homework_done si se habló de la tarea, note (una frase objetiva), wants_to_discuss (lo que quiere tratar en sesión, en sus palabras, o vacío).
"""

_agent = Agent(name="checkin", instructions=INSTRUCTIONS, output_type=Turn, model=llm.model_id(),
               model_settings=llm.model_settings())

def _context(patient: dict, plan: dict | None, trigger: str, today: dict | None) -> str:
    watch = ", ".join(plan.get("watch", [])) if plan else "sin plan cargado"
    homework = plan.get("homework") if plan else "ninguna"
    signal = ""
    if today:
        signal = f"Señales de hoy: sueño {today.get('sleep_h')} h, HRV {today.get('hrv_ms')} ms, ánimo {today.get('mood_valence')}."
    return (f"Paciente: {patient.get('name') or patient.get('ref')}. Motivo del contacto: {TRIGGER_TEXT.get(trigger, trigger)}.\n"
            f"Plan de la sesión — vigilar: {watch}. Tarea: {homework}.\n{signal}")

def open_question(patient: dict, plan: dict | None, trigger: str, today: dict | None) -> str:
    prompt = _context(patient, plan, trigger, today) + "\nEscribe el primer mensaje: saluda por su nombre y haz UNA pregunta. done=false."
    return Runner.run_sync(_agent, prompt).final_output.reply

def turn(patient: dict, plan: dict | None, trigger: str, history: list[dict], force_close: bool) -> Turn:
    convo = "\n".join(f"{'Paciente' if m['direction']=='in' else 'Tú'}: {m['body']}" for m in history)
    tail = "Cierra ahora (done=true) y extrae los campos." if force_close else "Responde. Si ya tienes lo esencial, cierra (done=true) y extrae los campos."
    prompt = _context(patient, plan, trigger, None) + f"\nConversación hasta ahora:\n{convo}\n{tail}"
    return Runner.run_sync(_agent, prompt).final_output
