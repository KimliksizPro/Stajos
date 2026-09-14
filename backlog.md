# StajOS Backlog

## Tamamlanan

- Faz 1: Application factory, config, User, JWT auth, global error handling ve standart response envelope.
- Faz 2: Internship/DailyLog domaini, gun ve sure hesaplama, CRUD ve migration `5678faa6d0c4`.
- Faz 3: Topic agaci, Technology/Tag iliskileri, otomatik linkleme ve migration `a2059b2bee86`.
- Faz 4: Arama/filtreleme/siralama, timeline ve dashboard stats tamamlandi; review bulgulari Fix-1/2/3/4 ve stajsiz stats P1 duzeltmesiyle kapatildi.
- Faz 4 commit'i `cd99529` (`feat: complete phase 4 review and fixes`) olarak tamamlandi.
- Tarihli dogrulama kaniti ve kalan riskler: `reports/ana_durum.md`.
- Tamamlanan Fix-2/3/4 tasarim ve planlari: `docs/archive/faz4/`.

## Siradaki: Faz 5 AI

- `AIProviderInterface` ve provider implementasyonu.
- AI cagrisi icin hafif background calisma modeli.
- `PENDING -> REFINED -> ACCEPTED/REJECTED/ERROR` durum akisi.
- Accept/reject endpointleri; hata halinde `ERROR`, her durumda `raw_content` degismezligi.
- Prompt guardrails ve yapisal JSON parse/validation.

## Sonraki

- Faz 6: JSON/CSV export, Swagger/OpenAPI ve eksik unit testler.
- V2: MCP server, tools ve resources implementasyonu.

## Bilincli Ertelenenler

- Solo MVP hardening sinirlari `docs/kurallar.md` icinde tanimlidir.
- Search icin ek `len <= 200` siniri, timeline pagination, strict sort/order reddi ve `today` injection simdilik ertelendi.
- PostgreSQL migration dogrulamasi uygun disposable ortam saglanana kadar acik risktir.
