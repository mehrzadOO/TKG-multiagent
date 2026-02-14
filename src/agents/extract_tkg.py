import os, json, time
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI
from jsonschema import validate, ValidationError

load_dotenv()

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("OPENROUTER_MODEL")  # همون مدلی که OK داد
API_KEY = os.environ["OPENROUTER_API_KEY"]

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- JSON Schemas (برای fail handling / validation) ---
ENTITIES_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                },
                "required": ["name", "type"],
            },
        }
    },
    "required": ["entities"],
}

RELATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "head": {"type": "string"},
                    "relation": {"type": "string"},
                    "tail": {"type": "string"},
                },
                "required": ["head", "relation", "tail"],
            },
        }
    },
    "required": ["relations"],
}

def _call_llm(system: str, user: str) -> str:
    print("calling LLM...")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    print("got response")
    return resp.choices[0].message.content.strip()

def _robust_json_parse(text: str) -> Any:
    # بعضی مدل‌ها دور JSON متن اضافه می‌نویسن؛ ما JSON بین { } رو بیرون می‌کشیم
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)

def run_agent_with_retry(system: str, user: str, schema: Dict[str, Any], retries: int = 2) -> Dict[str, Any]:
    last_err = None
    for attempt in range(retries + 1):
        try:
            raw = _call_llm(system, user)
            data = _robust_json_parse(raw)
            validate(instance=data, schema=schema)
            return data
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)
            time.sleep(0.8)  # کمی مکث
    raise ValueError(f"LLM output invalid after retries. Last error: {last_err}")

# -------- Agents --------

def agent_ner(update: str, background: str) -> List[Dict[str, str]]:
    system = "You extract named entities. Return ONLY valid JSON."
    user = f"""
Extract important named entities from the text (organizations, people, locations, key concepts).
Return JSON exactly in this format:
{{"entities":[{{"name":"...","type":"ORG|PERSON|GPE|EVENT|CONCEPT"}}]}}

TEXT:
UPDATE: {update}
BACKGROUND: {background}
"""
    out = run_agent_with_retry(system, user, ENTITIES_SCHEMA)
    return out["entities"]

def agent_relations(update: str, background: str, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
    system = "You extract factual relations as triples. Return ONLY valid JSON."
    ents = [e["name"] for e in entities][:25]
    user = f"""
Given the text and the entity list, extract 5-12 factual relations as triples.
Return JSON exactly in this format:
{{"relations":[{{"head":"...","relation":"...","tail":"..."}}, ...]}}

Entity list (use these names when possible):
{ents}

TEXT:
UPDATE: {update}
BACKGROUND: {background}
"""
    out = run_agent_with_retry(system, user, RELATIONS_SCHEMA)
    return out["relations"]

def orchestrate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    # Orchestrator: ترتیب اجرای agentها + هندل حداقلی failها
    update = record["update"]
    background = record["background"]
    date = record["date"]

    entities = agent_ner(update, background)
    relations = agent_relations(update, background, entities)

    # time: در این دیتاست تاریخ داریم؛ فقط attach می‌کنیم
    for r in relations:
        r["time"] = date

    return {
        "event": record["event"],
        "date": date,
        "entities": entities,
        "relations": relations,
        "source": record.get("source", ""),
    }
