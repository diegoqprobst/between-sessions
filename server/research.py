"""Sugerencias de foco para quien no llega con un plan de su terapeuta.
Busca en fuentes de salud pública con Exa y devuelve 2–4 focos concretos, cada uno con su fuente.
No diagnostica ni aconseja: describe qué suelen cuidar otras personas que trabajan en remoto."""
import httpx
from server import config, llm

EXA_URL = "https://api.exa.ai/search"
TRUSTED_DOMAINS = ["who.int", "nih.gov", "cdc.gov", "apa.org", "nhs.uk", "mayoclinic.org", "hbr.org"]
QUERY = ("what remote workers commonly protect for their mental health: sleep, work boundaries, "
         "isolation, screen time before bed, movement during the day")

def enabled() -> bool:
    """Necesita Exa para buscar y un modelo para resumir lo encontrado."""
    return bool(config.EXA_API_KEY) and llm.configured()

def search(query: str = QUERY, limit: int = 5) -> list[dict]:
    r = httpx.post(EXA_URL, headers={"x-api-key": config.EXA_API_KEY, "content-type": "application/json"},
                   json={"query": query, "numResults": limit, "type": "auto",
                         "includeDomains": TRUSTED_DOMAINS,
                         "contents": {"text": {"maxCharacters": 600}}}, timeout=25)
    r.raise_for_status()
    return r.json().get("results", [])

def sources(results: list[dict]) -> list[str]:
    """Dominios únicos, en orden de aparición, para citar la fuente sin exponer URLs largas."""
    out: list[str] = []
    for item in results:
        host = (item.get("url") or "").split("//")[-1].split("/")[0].removeprefix("www.")
        if host and host not in out:
            out.append(host)
    return out

def as_context(results: list[dict]) -> str:
    return "\n\n".join(f"[{i+1}] {r.get('title','')} ({r.get('url','')})\n{(r.get('text') or '')[:600]}"
                       for i, r in enumerate(results))

def format_reply(focos: list[str], fuentes: list[str]) -> str:
    """Mensaje final: opciones numeradas + cómo elegirlas. Pura, para poder probarla sin red."""
    if not focos:
        return ("No pude traer sugerencias ahora. Escríbeme tu propio plan así:\n"
                "plan: dormir 7h; cortar a las 6 | tarea: caminar 20 min")
    lineas = "\n".join(f"{i+1}. {f}" for i, f in enumerate(focos[:4]))
    cita = f"\nFuentes: {', '.join(fuentes[:3])}." if fuentes else ""
    return ("Esto es lo que suelen cuidar quienes trabajan en remoto. No es un diagnóstico ni un consejo clínico: "
            f"elige lo que te suene a ti.\n{lineas}{cita}\n\n"
            "Cuando lo tengas, mándame tu plan así:\nplan: dormir 7h; cortar a las 6 | tarea: caminar 20 min")

INSTRUCTIONS = ("Del material dado, extrae 3 focos que una persona que trabaja en remoto podría vigilar una semana. "
                "Uno por línea, sin numerar, máximo 8 palabras cada uno, en español, concretos y accionables "
                "(ej. 'cortar el trabajo a una hora fija'). No diagnostiques ni des consejo clínico. Solo las 3 líneas.")

def suggest() -> str:
    if not enabled():
        return format_reply([], [])
    try:
        results = search()
        res = llm.sync_client().chat.completions.create(
            model=llm.model_id(), max_tokens=200, temperature=0.3,
            messages=[{"role": "system", "content": INSTRUCTIONS},
                      {"role": "user", "content": as_context(results)}],
            extra_body=llm.provider_policy())
        content = llm.strip_thinking(res.choices[0].message.content)
        focos = [l.strip(" -•").strip() for l in content.splitlines() if l.strip()]
        return format_reply(focos, sources(results))
    except Exception:
        return format_reply([], [])
