# Ana Durum - 2026-09-14 (Faz 6 kapandi)

## Decision

- Faz 6 export/docs/testler tamamlandi (2026-09-14, HEAD `e9a4ba8`, aralik `342ac6c..e9a4ba8`); siradaki gercek gelistirme V2 MCP'dir; roadmap `backlog.md` ve `architecture.md` ile uyumludur.
- Bu dosya tek aktif durum, kanit, root-cause dersi ve risk ledger'idir.

## Evidence

- Son tam suite (2026-09-14): `python -m pytest -q` sonucu 164 passed, 0 failed (Faz 5 sonu 147 + 17 yeni: 2 exporter + 3 service + 6 API + 2 docs + 4 date-calculator).
- Migration degisikligi yok (read-only ozellik, model/metadata degismedi); migration head degismedi (`f5a13c9d7e21`).
- `python -m compileall -q app tests config.py run.py` exit 0; `git diff --check` clean; tracked diff bos (tum degisiklikler commitli).
- Faz 6 commit araligi `342ac6c..e9a4ba8` (6 commit: exporters, export-service, export-routes, docs-routes, date-calc testleri, review followup `e9a4ba8`).
- Faz 6 plani ve task raporlari: `docs/superpowers/plans/2026-09-14-faz6-export-docs-tests.md`, `task-{1..5}-report.md` (untracked, commit disi).
- Final branch review (2026-09-14): Ready to merge Yes, Critical bulgu yok; 4 Important followup ayni gun `e9a4ba8` ile kapatildi (try/except-pass kaldirma, olu eager-load temizligi, sessiz truncation -> `meta{total,limit,truncated}`, API-seviyesi IDOR testi).
- Onceki Faz 5 kaniti: `tests/ai` 128 passed; disposable SQLite DB'de `upgrade/current/check` PASS.
- Tamamlanan Fix-2/3/4 plan ve tasarim kayitlari `docs/archive/faz4/` altindadir.

## Root-Cause Lessons

- Stajsiz stats erken donusu `_build_logs_per_month` metoduna liste verirken metot `.get()` destekleyen map bekliyordu. Bos veri sekli yardimci sozlesmesiyle ayni tutulmali ve bos-kullanici endpoint yolu test edilmelidir.
- Ownership yalniz route auth'una birakilamaz; her veri sorgusu kullanici kapsamiyla filtrelenmelidir.
- Model metadata ve migration head ayni default/nullability semantigini tasimalidir; drift disposable DB ile kontrol edilmelidir.
- Eager-load fallback'i hatayi yutuyorsa baglamli warning uretmeli; N+1 riski gorunmez hale gelmemelidir.
- Read-only ozellikte eager-load kargo-kultu tasinmamali: `to_dict` iliski okumuyorsa `selectinload` olu koddur, sessiz `try/except: pass` ile birlesince gercek hatalari da gizler (Faz 6 review bulgusu 1-2, `e9a4ba8` ile kaldirildi).
- Limitli liste donen endpoint sessiz kirpmamali: `meta` icinde `limit` ve `truncated` bildirilmeli (Faz 6 review bulgusu 3).
- IDOR serviste test edilmis olsa bile HTTP katmaninda da test edilmeli; saldiri yuzeyi route'tur (Faz 6 review bulgusu 4).

## Risks/Unknowns

- PostgreSQL runtime yok (`psql` bulunamadi); migration kaniti SQLite ile sinirlidir.
- Restart-sirasinda-calisan-is kaybi recovery ile sinirli: `PROCESSING` kalanlar startup/recovery taramasinda `PENDING`'e alinip yeniden kuyruga verilir.
- Bilincli ertelenen hardening ve urun davranislari `docs/kurallar.md` ile `backlog.md` icinde acikca sinirlidir.
- Faz 6 review Minor takipleri acik (merge-blocker degil): CSV formula injection sanitize, Excel BOM/charset, OpenAPI spec-drift guard testi, Swagger CDN SRI/vendoring (`docs_routes.py`).
