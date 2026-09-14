# StajOS — Backlog (2026-09-14)

> Faz4 orkestrasyon durum kaydı. Personal use proje — ağır güvenlik hardening atlanır (`docs/kurallar.md:60`).

## Yapılanlar

### Faz 1-3 (önceden tamam)
- Faz 1: Auth + factory + response envelope + JWT 401 standard
- Faz 2: `internships` + `daily_logs`, `calculate_day_number`, migration `5678faa6d0c4`
- Faz 3: `topics` ağaç + `technologies/tags` M2M + auto-link, migration `a2059b2bee86` head

### Faz 4 — Implementasyon (tamam, doğrulandı)
- [x] Timeline: `app/services/timeline_service.py:26` `get_timeline` (calendar `year/month` + range `start/end`, `is_weekend`, `day_number`) + `app/api/v1/timeline_routes.py:14` `GET /api/v1/timeline` + `app/__init__.py:56,61` register
- [x] Stats: `app/services/stats_service.py:22` `get_dashboard_stats` (total_logs/days/duration, logs_per_month 6ay, top_tech/topics, recent 5) + `app/api/v1/dashboard_routes.py:12` `GET /api/v1/dashboard/stats`
- [x] Search/Filter: `app/services/log_service.py:252` `get_logs(topic,sort,order)` — topic join user-scoped + `sort=date|day_number` + `distinct()` + `app/api/v1/log_routes.py:70` passthrough
- [x] Doğrulama: `py_compile` OK, `pytest -v` 2 passed, manuel test OK (timeline 30 gün + meta, stats filtered/all, logs `topic+tech+search` total 3 + sort asc `[1,2,3]`, 401/404 IDOR/`strict_slashes` 308 yok)

### Faz 4 — Review (4 ajan tamam)
- [x] Auth & Security: H1 timeline range sınırsız DoS, H2 flat pagination yok, M1 search limitsiz, M2 `log_service.py:49` yanlış kolon (`Topic.name` → `normalized_name`), M3 sort sessiz fallback
- [x] Architecture & API: validasyon DRY (route vs service 4x parse), `_find_or_create_topic` index bypass, range branching karışık, `stats_service.py:184` `db.engine` deprecated, `selectinload` silent pass, `health:66` strict_slashes eksik
- [x] DB & Config: `topic.py:12` `server_default` eksik (drift), CHECK yok (service-only), tech/tag rollback batch siler, topic per-loop commit (2N), `log_service.py:393` distinct fragil, `get_log_by_id` 2 sorgu
- [x] Style & Quality: `topic_service.py:74,133` manuel lower (normalize_name kullan), topic per-loop commit, unused import (`timeline:13 db`, `stats:6 timedelta`, `log:7 date,time`), `pagination.py:1` `__all__` eksik, `internship.py:50` manuel isoformat, `User.to_dict` yok

## Yapılacaklar (hafif fix — solo, sırayla max 2 agent)

Fix ajanları rate-limit yüzünden çalışmadı (`Rate limit exceeded`) — tekrar gönderilecek.

- [x] Fix-1 Data Quality (hafif):
  - `LogService.get_logs` normalized topic lookup ve `_find_or_create_topic` delegasyonu testle doğrulandı.
  - `TopicService.create_topic/get_or_create` ortak `normalize_name()` kullanıyor.
  - Timeline tarihleri tek kez parse ediliyor; inclusive 366 gün kabul, 367 gün `BadRequestError`.
  - Topic bulk akışı helper'ları `commit=False` ile flush ediyor, döngü sonunda tek commit yapıyor; hata halinde rollback atomiklik testiyle doğrulandı.
  - Kanıt: `python -m pytest -v tests\test_fix1_data_quality.py` → 5 passed.
- [x] Fix-2 API Contract (hafif):
  - Health slash sözleşmesi ve mevcut `strict_slashes=False` davranışı endpoint + route introspection testiyle korundu; üretim değişikliği yapılmadı.
  - Stats sözleşmesi ve mevcut `db.session.get_bind()` kullanımı testle korundu; `db.engine` fallback olmadığı doğrulandı, üretim değişikliği yapılmadı.
  - Timeline `s_date/e_date` ile her dolu tarihi tek kez parse edip sıralama ve service çağrısında aynı nesneleri kullanıyor; 366 kabul/367 ret korunuyor.
  - Kanıt: Fix-2 RED 2 passed/2 failed (timeline 4 parse çağrısı; stats boş-kullanıcı yolundaki kapsam dışı mevcut hata), GREEN `python -m pytest -v tests\\test_fix2_api_contract.py` → 4 passed; sınır testleri → 2 passed; tam suite → 11 passed; `py_compile` ve `compileall` exit 0.
- [x] P1 Bug — stajsız kullanıcı dashboard stats `AttributeError` (Fix-2 kapsamı dışında, Fix-2'yi yeniden açmaz):
  - Kök neden: `app/services/stats_service.py` stajsız erken dönüşte `_build_logs_per_month` metoduna liste gönderiyordu; metot `.get()` destekleyen map bekliyordu.
  - Düzeltme: Erken dönüş boş map gönderiyor; gerçek endpoint stajsız kullanıcı için mevcut envelope ile zero/boş stats ve 200 döndürüyor.
  - Kanıt: RED gerçek endpoint testi `AttributeError: 'list' object has no attribute 'get'`; GREEN hedefli + Fix-2 5 passed, tam suite 19 passed; `py_compile` ve `compileall` exit 0. Faz-4 final doğrulama bağımsız rerun bekliyor.
- [x] Fix-3 Structure (hafif):
  - `pagination.py` public API tanımlandı; `User.to_dict()` güvenli alanları merkezileştirdi ve auth endpoint alan sözleşmeleri korundu.
  - Nullable internship/stats serialization `iso_or_none` kullanıyor; zorunlu timeline tarihleri doğrudan `.isoformat()` kullanmaya devam ediyor.
  - Stats/timeline/log eager-load fallback'ları hatayı yutmaya devam ederken bağlamlı WARNING üretiyor; sahip olunan dosyalardaki doğrulanmış unused importlar kaldırıldı.
  - Kanıt: İlk RED → 1 passed, 5 failed; bağımsız doğrulama düzeltmesi RED → 5 passed, 1 failed (`internship_service.py` unused `datetime`); GREEN Fix-3 → 6 passed; tam suite → 17 passed; `py_compile`, `compileall` ve import smoke exit 0.
- [x] Fix-4 Infra/DB (hafif):
  - `log_topics.is_ai_suggested` model metadata'sina `server_default=db.text("0")` eklendi; mevcut head migration `a2059b2bee86` ile drift kapatildi, yeni migration olusturulmadi.
  - Kanit: RED beklenen `server_default is not None` assertion'inda 1 failed; GREEN hedefli test 1 passed, Fix-1 + Fix-4 6 passed, tam suite 18 passed; `py_compile` ve `compileall` exit 0.
  - Gecici `%TEMP%` SQLite DB'de heads/history/upgrade/current/check/downgrade `5678faa6d0c4`/upgrade/current/check dongusu basarili ve dosya temizlendi; PostgreSQL dogrulanmadi.
  - Opsiyonel `total_expected_days>0` ve `day_number>0` CHECK constraint'leri kapsam disi olarak atlandi.
- [x] Final doğrulama: `py_compile` + `pytest -v` + manuel (timeline/stats/logs/401/IDOR) + `flask db check`
  - İlk final turu: manuel 12/13 FAIL; kök neden stajsız stats erken dönüşünde `_build_logs_per_month` metoduna `[]` verilmesi ve metodun `.get()` destekleyen map beklemesiydi.
  - P1 TDD: RED `AttributeError: 'list' object has no attribute 'get'`; minimal düzeltme `[]` → `{}`; hedefli testler 5 passed, üretici tam suite 19 passed.
  - Taze final otomatik: tam suite 19 passed; `py_compile`, `compileall` ve import smoke PASS; geçici SQLite DB'de upgrade/current/check PASS, ardından cleanup tamamlandı.
  - Taze manuel: 13/13 PASS; logs filtre/sıralama, timeline, stats, 401, IDOR ve response envelope sözleşmeleri doğrulandı.
  - Residual risk: PostgreSQL doğrulanmadı.
- [x] Commit: Faz4 `review + fix` sonrası tek commit

## Atlananlar (solo personal use — bilinçli)
- rate limit / Flask-Limiter, timing mitigation, token revocation/blocklist
- search `len<=200` zorunlu limit, timeline zorunlu pagination (366 cap yeterli)
- sort/order 400 strict (sessiz fallback tolere)
- timeline meta dokümantasyon, test determinism (`today` inject)

## Sonraki Fazlar
- Faz 5: AI (`AIProviderInterface`, `threading.Thread`, `accept/reject-ai`)
- Faz 6: Export JSON/CSV + Swagger + unit test (gün hesaplama, AI parser)
- V2: MCP (`mcp/server.py`, `tools.py` doldur)
