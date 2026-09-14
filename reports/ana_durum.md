# Ana Durum - 2026-09-14

## Decision

- Faz 5 AI tamamlandi (2026-09-14, HEAD `5e29bc3`, aralik `5e50db1..5e29bc3`); siradaki gercek gelistirme Faz 6'dir; roadmap `backlog.md` ve `architecture.md` ile uyumludur.
- Bu dosya tek aktif durum, kanit, root-cause dersi ve risk ledger'idir.

## Evidence

- Son tam suite (2026-09-14): `python -m pytest -v` sonucu 147 passed; `python -m pytest tests/ai -q` sonucu 128 passed.
- Migration head `f5a13c9d7e21`; disposable SQLite DB'de `flask db upgrade`, `flask db current` (`f5a13c9d7e21 (head)`) ve `flask db check` (`No new upgrade operations detected`) PASS; cleanup tamamlandi.
- `python -m compileall app tests config.py run.py` exit 0; `git diff --check` clean; `git status --short` clean (task-7 raporu haric commit disi).
- Faz 5 commit araligi `5e50db1..5e29bc3` (13 commit).
- Tamamlanan Fix-2/3/4 plan ve tasarim kayitlari `docs/archive/faz4/` altindadir.

## Root-Cause Lessons

- Stajsiz stats erken donusu `_build_logs_per_month` metoduna liste verirken metot `.get()` destekleyen map bekliyordu. Bos veri sekli yardimci sozlesmesiyle ayni tutulmali ve bos-kullanici endpoint yolu test edilmelidir.
- Ownership yalniz route auth'una birakilamaz; her veri sorgusu kullanici kapsamiyla filtrelenmelidir.
- Model metadata ve migration head ayni default/nullability semantigini tasimalidir; drift disposable DB ile kontrol edilmelidir.
- Eager-load fallback'i hatayi yutuyorsa baglamli warning uretmeli; N+1 riski gorunmez hale gelmemelidir.

## Risks/Unknowns

- PostgreSQL runtime yok (`psql` bulunamadi); migration kaniti SQLite ile sinirlidir.
- Restart-sirasinda-calisan-is kaybi recovery ile sinirli: `PROCESSING` kalanlar startup/recovery taramasinda `PENDING`'e alinip yeniden kuyruga verilir.
- Bilincli ertelenen hardening ve urun davranislari `docs/kurallar.md` ile `backlog.md` icinde acikca sinirlidir.
