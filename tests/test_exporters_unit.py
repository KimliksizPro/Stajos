# tests/test_exporters_unit.py
from app.utils.exporters import CSV_COLUMNS, logs_to_csv_rows

def test_csv_columns_stable():
    assert CSV_COLUMNS == ["id", "internship_id", "date", "day_number", "title", "raw_content", "ai_status", "duration_minutes", "start_time", "end_time", "created_at"]

def test_logs_to_csv_rows_escapes_commas_and_quotes():
    rows = logs_to_csv_rows([{"id": "1", "internship_id": "i1", "date": "2024-01-02", "day_number": 1, "title": 'a,"b', "raw_content": "x\ny", "ai_status": "PENDING", "duration_minutes": 60, "start_time": "09:00", "end_time": "10:00", "created_at": "2024-01-02T00:00:00"}])
    assert '"a,""b"' in rows
    assert rows.splitlines()[0] == ",".join(CSV_COLUMNS)
