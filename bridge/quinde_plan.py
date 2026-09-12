"""Lee la nota C-SOAP de Quinde y publica SOLO el plan estructurado. Corre en la Mac del terapeuta."""
import argparse, json, os, sys
import httpx
from pydantic import BaseModel
from any_llm import completion

class Plan(BaseModel):
    patient_ref: str
    session_num: int | None = None
    session_date: str
    next_session_date: str
    watch: list[str]
    homework: str
    next_focus: str
    risk_baseline: str = "none"

class Extract(BaseModel):
    watch: list[str]
    homework: str
    next_focus: str
    session_date: str

PROMPT = """Eres asistente de un psicólogo. A partir de la sección PLAN de una nota clínica, extrae en JSON:
- watch: 2 a 4 cosas concretas a vigilar durante la semana (frases cortas)
- homework: la tarea acordada, en una frase
- next_focus: qué se revisará en la próxima sesión
- session_date: la fecha de la sesión en formato YYYY-MM-DD (la fecha dada es '{fecha}')
No incluyas nada que el paciente haya dicho literalmente. Solo el plan. Responde solo JSON con esas cuatro claves.
Sección PLAN:
{plan}
"""

def extract(prompt: str, model: str) -> dict:
    messages = [{"role": "user", "content": prompt}]
    try:
        res = completion(model=model, provider="ollama", messages=messages, response_format=Extract)
    except Exception:
        res = completion(model=model, provider="ollama", messages=messages, response_format={"type": "json_object"})
    content = res.choices[0].message.content
    return Extract.model_validate_json(content).model_dump()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nota"); ap.add_argument("--next-session", required=True)
    ap.add_argument("--server", default=os.environ.get("SERVER", "http://localhost:8000"))
    ap.add_argument("--key", default=os.environ.get("THERAPIST_KEY", "dev-therapist-key"))
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3:14b"))
    ap.add_argument("--dry-run", action="store_true", help="no publica; solo imprime el plan")
    a = ap.parse_args()
    note = json.load(open(a.nota))
    plan_section = next(s for s in note["secciones"] if s.get("letra") == "P")
    prompt = PROMPT.format(fecha=note.get("fecha", ""), plan="\n".join(plan_section["contenido"]))
    data = extract(prompt, a.model)
    plan = Plan(patient_ref=note["paciente"].strip().lower(), session_num=note.get("sesion_num"),
                next_session_date=a.next_session,
                risk_baseline="none" if str(note.get("riesgo", "")).lower().startswith("ning") else "flagged", **data)
    print(plan.model_dump_json(indent=2))
    if a.dry_run:
        return 0
    r = httpx.post(f"{a.server}/plans", json=plan.model_dump(), headers={"x-therapist-key": a.key}, timeout=30)
    print(r.status_code, r.text)
    return 0 if r.status_code == 200 else 1

if __name__ == "__main__":
    sys.exit(main())
