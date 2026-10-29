"""Smoke-check итоговой SQLite-базы."""

import argparse
import json
import sqlite3
from pathlib import Path


def inspect_database(db_path):
    with sqlite3.connect(db_path) as conn:
        quotes = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        tag_links = conn.execute("SELECT COUNT(*) FROM quote_tags").fetchone()[0]
        empty = conn.execute(
            """
            SELECT COUNT(*) FROM quotes
            WHERE quote IS NULL OR TRIM(quote) = ''
               OR author IS NULL OR TRIM(author) = ''
               OR born_date IS NULL OR TRIM(born_date) = ''
               OR biography IS NULL OR TRIM(biography) = ''
            """
        ).fetchone()[0]

    return {
        "quotes": quotes,
        "tag_links": tag_links,
        "total_rows": quotes + tag_links,
        "empty_required_share": empty / quotes if quotes else 1.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/crawl.db")
    parser.add_argument("--baseline", default="quality/baseline_summary.json")
    parser.add_argument("--output", default="quality/current_summary.json")
    args = parser.parse_args()

    current = inspect_database(args.db)
    baseline_path = Path(args.baseline)
    warnings = []

    if baseline_path.exists():
        previous = json.loads(baseline_path.read_text(encoding="utf-8"))
        previous_rows = previous.get("total_rows", 0)
        if previous_rows and current["total_rows"] < previous_rows * 0.8:
            warnings.append("число строк уменьшилось более чем на 20%")
    else:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if current["empty_required_share"] > 0.05:
        warnings.append("доля пустых обязательных полей превышает 5%")

    current["warnings"] = warnings
    Path(args.output).write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
