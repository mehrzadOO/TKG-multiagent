import json
from pathlib import Path

IN_PATH = Path("outputs/tkg_raw.jsonl")
OUT_PATH = Path("outputs/tkg.json")

def norm(s: str) -> str:
    return " ".join(s.strip().split())

def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(f"Missing input: {IN_PATH}")

    nodes = {}
    edges = []

    with IN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            date = rec.get("date", "")
            event = rec.get("event", "")
            source = rec.get("source", "")

            # --- Nodes ---
            for ent in rec.get("entities", []):
                name = norm(ent.get("name", ""))
                if not name:
                    continue
                if name not in nodes:
                    nodes[name] = {
                        "id": f"n{len(nodes)+1}",
                        "name": name,
                        "type": ent.get("type", "UNKNOWN"),
                    }

            # --- Edges ---
            for rel in rec.get("relations", []):
                head = norm(rel.get("head", ""))
                tail = norm(rel.get("tail", ""))
                relation = norm(rel.get("relation", ""))
                time = rel.get("time", date)

                if not head or not tail or not relation:
                    continue

                if head not in nodes:
                    nodes[head] = {
                        "id": f"n{len(nodes)+1}",
                        "name": head,
                        "type": "UNKNOWN",
                    }

                if tail not in nodes:
                    nodes[tail] = {
                        "id": f"n{len(nodes)+1}",
                        "name": tail,
                        "type": "UNKNOWN",
                    }

                edges.append({
                    "source": nodes[head]["id"],
                    "target": nodes[tail]["id"],
                    "relation": relation,
                    "time": time,
                    "event": event,
                    "provenance": source,
                })

    graph = {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Graph built successfully")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
