# Hata Logları - 2026-09-14

## Decision
- Faz-4 final doğrulama PASS ile kapandı; stajsız kullanıcı stats P1 hatası kapalı.
- Backlog'daki sıradaki açık iş aynen: `Commit: Faz4 review + fix sonrası tek commit`.

## Files Changed
- Yalnız `backlog.md` ve üç `reports/` ledger dosyası güncellendi.
- Uygulama, test, migration, doküman ve diğer dosyalara dokunulmadı.

## Evidence
- İlk final manuel turu 12/13 FAIL verdi. Kök neden: stats erken dönüşündeki `[]`, `_build_logs_per_month` içindeki map `.get()` çağrısıyla uyumsuzdu.
- P1 TDD RED: `AttributeError: 'list' object has no attribute 'get'`; minimal `[]` → `{}` düzeltmesiyle hedefli 5 passed, üretici tam suite 19 passed.
- Taze final otomatik: 19 passed; `py_compile`, `compileall` ve import smoke PASS; geçici SQLite upgrade/current/check PASS, temp DB cleanup tamamlandı.
- Taze manuel: 13/13 PASS; logs filtre/sıralama, timeline, stats, 401, IDOR ve response envelope doğrulandı.

## Risks/Unknowns
- PostgreSQL doğrulanmadı; SQLite sonucu sağlayıcı farklarını kapsamaz.
