import os, json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GRAPH_PATH = Path("outputs/tkg.json")

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("OPENROUTER_MODEL")
API_KEY = os.environ["OPENROUTER_API_KEY"]

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def load_graph():
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(f"Missing graph file: {GRAPH_PATH}")
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

def retrieve_facts(graph, query: str, top_k: int = 10):
    """Retrieval خیلی ساده MVP: match روی نام nodeها و relationها"""
    q = query.lower().strip()

    nodes = graph["nodes"]
    edges = graph["edges"]

    # 1) نودهای مرتبط با query
    matched_nodes = [n for n in nodes if q in n["name"].lower()]
    matched_node_ids = {n["id"] for n in matched_nodes}

    # اگر هیچ match مستقیم نبود، یه روش ساده: کلمات query رو جدا کن
    if not matched_nodes:
        words = [w for w in q.split() if len(w) >= 4]
        for n in nodes:
            name_l = n["name"].lower()
            if any(w in name_l for w in words):
                matched_node_ids.add(n["id"])

    # 2) یال‌های مرتبط
    facts = []
    for e in edges:
        rel_l = e["relation"].lower()
        if (e["source"] in matched_node_ids) or (e["target"] in matched_node_ids) or any(w in rel_l for w in q.split()):
            facts.append(e)

    # محدود کردن برای MVP
    return facts[:top_k]

def edge_to_text(graph, edge):
    id_to_name = {n["id"]: n["name"] for n in graph["nodes"]}
    s = id_to_name.get(edge["source"], edge["source"])
    t = id_to_name.get(edge["target"], edge["target"])
    rel = edge["relation"]
    tm = edge.get("time", "")
    return f"[{tm}] {s} --{rel}--> {t}"

def summarize(query: str, facts_text: str):
    system = "You are a helpful assistant that writes short, clear background summaries grounded in provided facts."
    user = f"""
Query: {query}

Facts (do not invent anything beyond these):
{facts_text}

Write a short background summary (5-8 sentences). Mention dates if present.
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def main():
    graph = load_graph()

    query = input("Type your question/query: ").strip()
    facts = retrieve_facts(graph, query, top_k=12)

    if not facts:
        print("⚠️ No facts matched. Try a different query (e.g., a key entity name).")
        return

    facts_text = "\n".join(edge_to_text(graph, f) for f in facts)

    print("\n--- Retrieved facts ---")
    print(facts_text)

    print("\n--- Summary ---")
    summary = summarize(query, facts_text)
    print(summary)

if __name__ == "__main__":
    main()
