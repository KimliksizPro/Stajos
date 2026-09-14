# Ana Durum - 2026-09-14

## Decision

- Faz 4 tamamlandi ve commit `cd99529` ile kapatildi.
- Siradaki gercek gelistirme Faz 5 AI'dir; roadmap `backlog.md` ve `architecture.md` ile uyumludur.
- Bu dosya tek aktif durum, kanit, root-cause dersi ve risk ledger'idir.

## Evidence

- Son tam suite: `python -m pytest -v` sonucu 19 passed.
- Son manuel API kontrolu: 13/13 PASS; log filtre/siralama, timeline, stats, 401, IDOR ve response envelope kapsandi.
- Disposable SQLite DB'de `upgrade`, `current` ve `check` PASS; cleanup tamamlandi.
- `py_compile`, `compileall` ve import smoke PASS.
- Tamamlanan Fix-2/3/4 plan ve tasarim kayitlari `docs/archive/faz4/` altindadir.

## Root-Cause Lessons

- Stajsiz stats erken donusu `_build_logs_per_month` metoduna liste verirken metot `.get()` destekleyen map bekliyordu. Bos veri sekli yardimci sozlesmesiyle ayni tutulmali ve bos-kullanici endpoint yolu test edilmelidir.
- Ownership yalniz route auth'una birakilamaz; her veri sorgusu kullanici kapsamiyla filtrelenmelidir.
- Model metadata ve migration head ayni default/nullability semantigini tasimalidir; drift disposable DB ile kontrol edilmelidir.
- Eager-load fallback'i hatayi yutuyorsa baglamli warning uretmeli; N+1 riski gorunmez hale gelmemelidir.

## Risks/Unknowns

- PostgreSQL dogrulanmadi; migration kaniti SQLite ile sinirlidir.
- Faz 5 background thread yaklasimi process restart, hata gozlemlenebilirligi ve uygulama context'i acisindan tasarim karari gerektirir.
- Bilincli ertelenen hardening ve urun davranislari `docs/kurallar.md` ile `backlog.md` icinde acikca sinirlidir.
