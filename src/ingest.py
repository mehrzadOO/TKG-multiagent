from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/events")
OUT_PATH = Path("outputs/timeline_sample.jsonl")

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    event_name = "financial_crisis"
    event_dir = DATA_DIR / event_name

    if not event_dir.exists():
        raise FileNotFoundError(f"Event folder not found: {event_dir}")

    tsv_path = event_dir / "annotator1.tsv"
    if not tsv_path.exists():
        raise FileNotFoundError(f"TSV not found: {tsv_path}")

    df = pd.read_csv(tsv_path, sep="\t")

    needed = {"Date", "Update", "Background"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in TSV: {missing}. Found: {list(df.columns)}")

    df = df.head(5)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            rec = {
                "event": event_name,
                "date": str(row["Date"]).strip(),
                "update": str(row["Update"]).strip(),
                "background": str(row["Background"]).strip(),
                "source": "annotator1",
            }
            f.write(pd.Series(rec).to_json(force_ascii=False) + "\n")

    print(f"Wrote {len(df)} records to {OUT_PATH}")

if __name__ == "__main__":
    main()
