# Task 2 Raporu: ExportService (ownership + fetch)

## Yapılan İş
- `app/services/export_service.py` oluşturuldu: `ExportService.get_export_dicts(user_id, internship_id=None) -> list[dict]`.
- Sahiplik: verilen `internship_id` istek yapan kullanıcıya ait değilse `NotFoundError` (404, 403 sızıntısı yok).
- `internship_id` verilmezse kullanıcının tüm stajlarındaki loglar tarih sırasıyla, en fazla 1000 satır döner; stajı olmayan kullanıcıya boş liste.
- Salt okunur: `raw_content` dahil `DailyLog.to_dict()` üzerinden okur, yazma yok.
- Test dosyası `tests/test_export_service.py` plan metni birebir (verbatim) yazıldı.

## RED + GREEN Kanıtı
- RED: `python -m pytest tests/test_export_service.py -v` → collection ERROR, `ModuleNotFoundError: No module named 'app.services.export_service'` (beklenen FAIL).
- GREEN: `python -m pytest tests/test_export_service.py tests/test_exporters_unit.py -v` → **4 passed** (2 export_service + 2 exporters_unit).

## Dosyalar
- `app/services/export_service.py` (yeni, 37 satır)
- `tests/test_export_service.py` (yeni, 33 satır)

## Self-Review
- Plan Task 2 Step 1 ve Step 3 kod blokları verbatim uygulandı (dosya başı `# ...` yorum satırları dahil).
- Global kısıtlar: iş mantığı service layer'da, `raw_content` yazılmıyor, en küçük değişiklik (2 yeni dosya, mevcut dosyaya dokunulmadı).
- `git diff --check` temiz, `git show --stat HEAD` yalnızca 2 dosya (70 insertion).
- Sahiplik kontrolü `Internship.query.filter_by(user_id=...)` üzerinden; yabancı stajda `NotFoundError` doğrulanıyor (test PASS).

## Endişeler
- `from app.extensions import db` importu planda verbatim olduğu için duruyor ancak implementasyonda kullanılmıyor (ölü import; lint uyarısı verebilir — plan sadakati için değiştirilmedi).
