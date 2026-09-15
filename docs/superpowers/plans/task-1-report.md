# Task 1 Report: Exporter pure helpers (CSV/JSON)

Plan: `docs/superpowers/plans/2026-09-14-faz6-export-docs-tests.md` — Task 1 only, exact values verbatim.

## Ne implemente edildi
- `app/utils/exporters.py:1-2` placeholder (`__all__ = []`) → pure stdlib helper'lar (`csv`, `io`; DB/HTTP yok):
  - `CSV_COLUMNS` (11 kolon, sabit sıra)
  - `logs_to_csv_rows(log_dicts) -> str` (header + satırlar, quoting stdlib csv, None→`""`, `extrasaction="ignore"`)
  - `logs_to_jsonable(log_dicts)` (shallow copy listesi)
- `tests/test_exporters_unit.py` oluşturuldu (2 test: kolon stabilitesi, virgül/tırnak/yeni-satır escaping + header satırı).
- Planın Step 1 ve Step 3 kod blokları verbatim yazıldı; başka dosyaya dokunulmadı.

## Test sonuçları
Komut: `python -m pytest tests/test_exporters_unit.py -v`

### RED (Step 2, implementasyon öncesi — beklenen FAIL)
```
ERROR collecting tests/test_exporters_unit.py
ImportError while importing test module 'tests/test_exporters_unit.py'.
tests\test_exporters_unit.py:2: in <module>
    from app.utils.exporters import CSV_COLUMNS, logs_to_csv_rows
E   ImportError: cannot import name 'CSV_COLUMNS' from 'app.utils.exporters' (app/utils/exporters.py)
1 error during collection
```
Değerlendirme: Planın beklediği ImportError/cannot import name ile birebir uyumlu.

### GREEN (Step 4, implementasyon sonrası — PASS)
```
tests/test_exporters_unit.py::test_csv_columns_stable PASSED [ 50%]
tests/test_exporters_unit.py::test_logs_to_csv_rows_escapes_commas_and_quotes PASSED [100%]
2 passed in 0.02s
```

## Değişen dosyalar
- `app/utils/exporters.py` (modified: 2 satır → 20 satır)
- `tests/test_exporters_unit.py` (created: 10 satır)
- Commit: `git add app/utils/exporters.py tests/test_exporters_unit.py && git commit -m "feat: add export csv/json helpers"`
- SHA: `342ac6c7a33e72ff6cdbb597e7a52d32182bb864`

## Self-review
- Verbatim kontrolü: test ve implementasyon planın kod bloklarıyla aynı (CSV_COLUMNS sırası, docstring, `lineterminator="\n"`, None→`""` handling dahil).
- Kapsam: sadece 2 dosya; `git diff --stat HEAD~1 HEAD` → 2 files, 28 insertions, 2 deletions; ilgisiz refactor yok.
- `git diff --check HEAD~1 HEAD` temiz (whitespace hatası yok; sadece LF→CRLF autocrlf warning'i var, hata değil).
- `git status --short` → sadece untracked plan dosyası (`docs/superpowers/plans/2026-09-14-faz6-export-docs-tests.md`, bu task'ın üretimi değil, commit dışı bırakıldı).
- Global constraints: secret/commit'e konmadı, DB/HTTP bağımlılığı yok, en küçük değişiklik.

## Concerns
- Yok. Sonraki task'lar (ExportService, routes) bu fonksiyonlara dayanabilir.
