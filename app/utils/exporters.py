"""CSV/JSON export helpers (Faz 6). Pure functions, no DB/HTTP."""
import csv
import io

CSV_COLUMNS = ["id", "internship_id", "date", "day_number", "title", "raw_content", "ai_status", "duration_minutes", "start_time", "end_time", "created_at"]

__all__ = ["CSV_COLUMNS", "logs_to_csv_rows", "logs_to_jsonable"]

def logs_to_jsonable(log_dicts):
    return [dict(d) for d in (log_dicts or [])]

def logs_to_csv_rows(log_dicts):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for d in (log_dicts or []):
        w.writerow({c: d.get(c, "") if d.get(c, "") is not None else "" for c in CSV_COLUMNS})
    return buf.getvalue()
