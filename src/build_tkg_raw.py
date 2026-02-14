import json
from pathlib import Path
from src.agents.extract_tkg import orchestrate_record

IN_PATH = Path("outputs/timeline_sample.jsonl")
OUT_PATH = Path("outputs/tkg_raw.jsonl")
LOG_PATH = Path("outputs/tkg_failures.log")

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0

    with IN_PATH.open("r", encoding="utf-8") as fin, \
         OUT_PATH.open("w", encoding="utf-8") as fout, \
         LOG_PATH.open("w", encoding="utf-8") as flog:

        for i, line in enumerate(fin, start=1):
            record = json.loads(line)
            try:
                out = orchestrate_record(record)
                fout.write(json.dumps(out, ensure_ascii=False) + "\n")
                ok += 1
                print(f"✅ {i}: ok")
            except Exception as e:
                fail += 1
                flog.write(f"Record {i} failed: {e}\n")
                print(f"❌ {i}: failed (logged)")

    print(f"\nDONE. ok={ok}, fail={fail}")
    print(f"Output: {OUT_PATH}")
    print(f"Failures: {LOG_PATH}")

if __name__ == "__main__":
    main()
