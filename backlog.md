# StajOS Backlog

## Tamamlanan

- Faz 1: Application factory, config, User, JWT auth, global error handling ve standart response envelope.
- Faz 2: Internship/DailyLog domaini, gun ve sure hesaplama, CRUD ve migration `5678faa6d0c4`.
- Faz 3: Topic agaci, Technology/Tag iliskileri, otomatik linkleme ve migration `a2059b2bee86`.
- Faz 4: Arama/filtreleme/siralama, timeline ve dashboard stats tamamlandi; review bulgulari Fix-1/2/3/4 ve stajsiz stats P1 duzeltmesiyle kapatildi.
- Faz 4 commit'i `cd99529` (`feat: complete phase 4 review and fixes`) olarak tamamlandi.
- Tarihli dogrulama kaniti ve kalan riskler: `reports/ana_durum.md`.
- Tamamlanan Fix-2/3/4 tasarim ve planlari: `docs/archive/faz4/`.
- Faz 5: AI entegrasyonu tamamlandi (2026-09-14): provider/parser/worker/recovery/submission/accept-reject + migration `f5a13c9d7e21` head.
- Faz 5 kanit (2026-09-14): `tests/ai` 128 passed, tam suite 147 passed; disposable SQLite DB'de `upgrade/current/check` PASS; commit araligi `5e50db1..5e29bc3` (HEAD `5e29bc3`).
- Faz 6: Export/docs/testler tamamlandi (2026-09-14): `ExportService` + `GET /api/v1/export/json|csv`, `GET /api/v1/openapi.json|docs`, `date_calculator` unit testleri; migration yok (read-only, model degisikligi yok).
- Faz 6 kanit (2026-09-14): tam suite 164 passed (147 + 17 yeni); `compileall` exit 0; `git diff --check` clean; commit araligi `342ac6c..e9a4ba8` (HEAD `e9a4ba8`, review followup dahil 6 commit).
- Faz 6 plani: `docs/superpowers/plans/2026-09-14-faz6-export-docs-tests.md`.

## Siradaki: V2 MCP

- MCP server, tools ve resources implementasyonu.

## Sonraki

- V2: MCP server, tools ve resources implementasyonu.

## Bilincli Ertelenenler

- Solo MVP hardening sinirlari `docs/kurallar.md` icinde tanimlidir.
- Search icin ek `len <= 200` siniri, timeline pagination, strict sort/order reddi ve `today` injection simdilik ertelendi.
- PostgreSQL migration dogrulamasi uygun disposable ortam saglanana kadar acik risktir.
