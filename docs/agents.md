# StajOS — Ajanlar (Agents)

> Bu doküman projede kullanılan alt ajanları (sub-agents) ve kullanım kurallarını tanımlar.
> `architecture.md:8` MCP hazırlığı ile uyumludur — servisler ajanlar tarafından doğrudan çağrılabilir.

---

## 1. Ajan Felsefesi

- Controller’lar iş yapmaz, tüm iş `Service Layer`’da. Ajanlar `mcp/tools.py` üzerinden servisleri çağırır.
- Ajanlar JWT ile authenticate olur (normal kullanıcı gibi `POST /api/v1/auth/login` → Bearer token).
- Solo mode: permission sistemi yok, her JWT tüm `current_user` verisine erişir.

## 2. Faz 1 Review Ajanları

Faz 1’de 4 paralel code-review ajanı kullanıldı. Kararlar `docs/kurallar.md:5`’e işlendi.

| Ajan | Odak | İncelediği Dosyalar |
|------|------|---------------------|
| **Auth & Security** | JWT, password hashing, timing, rate limit, secret yönetimi | `auth_service.py`, `auth_routes.py`, `security.py`, `user.py`, `config.py` |
| **Architecture & API** | Klasör yapısı, factory, response contract `§5.1`, blueprint yapısı | `app/__init__.py`, `exceptions.py`, `pagination.py`, `migrations/*` |
| **DB & Config** | Model ↔ spec uyumu, migration, `.env` race, UTC | `user.py`, `config.py`, `extensions.py`, `migrations/env.py` |
| **Style & Quality** | DRY, tekrara düşme, import, whitespace bug | Tüm `app/*`, `tests/*`, `run.py` |

**Verdict:** Fonksiyonel ama prod block’ları vardı → infra fix ajanlarıyla düzeltildi (personal use hardening’leri atlandı).

## 2.1 Faz 2 Review Ajanları (2026-09-14)

Faz 2 Core Domain sonrası 4 paralel review ajanı çalıştı — `internships` + `daily_logs` domaini incelendi.

| Ajan | Odak | Bulgular (kritik) |
|------|------|-------------------|
| **Auth & Security** | `@jwt_required` coverage, IDOR, `raw_content` limit, `IntegrityError` race, `ilike` escape, `day_number=0` | `day_number=0` hafta sonu 0 validasyon yok, `IntegrityError` race 500, `raw_content` limitsiz, `ilike` wildcard |
| **Architecture & API** | Factory, blueprint `strict_slashes`, `tech` contract, `response envelope` | **CRITICAL:** trailing slash `308` (`/api/v1/internships` -> redirect), `auth_routes.py` `jsonify` bypass, `tech` filtresi eksik, `day_number=0` |
| **DB & Config** | Model↔spec, migration drift, `ondelete`, UTC, N+1 | **CRITICAL:** DB drift (`5678faa6d0c4` uygulanmamış), FK `ondelete` tutarsız, N+1 `joinedload` yok, `validate()` zayıf |
| **Style & Quality** | DRY `_parse_date`/`_utcnow`, `to_dict`, `__all__` | **HIGH:** `_parse_date` 2x duplicate, `_utcnow` 3x duplicate, `response envelope` tekrar, `uuid` unused |

**Verdict (Faz 2):** Fonksiyonel ama contract/DRY/data-quality fixleri gerekli → 4 fix ajanıyla düzeltildi (solo hardening atlandı).

## 2.2 Faz 3 Review Ajanları (2026-09-14)

Faz 3 Learning sonrası 4 paralel review ajanı çalıştı — `topics` + `technologies` + `tags` + `log_*` M2M incelendi.

| Ajan | Odak | Bulgular (kritik) |
|------|------|-------------------|
| **Auth & Security** | `@jwt_required` coverage, IDOR `parent_id`/`link_to_log`, `normalized_name` bypass, `description` DoS | **HIGH:** `link_to_log` `user_id` ownership eksik `topic_service.py:208`, DB `UniqueConstraint` case-sensitive bypass (`Python` vs `python`), `description` limitsiz |
| **Architecture & API** | Factory, `strict_slashes`, `response envelope`, `distinct count`, N+1 | **HIGH:** `topic` `normalized_name` DB koruması yok, `mcp/tools.py` missing, `get_log_by_id` N+1, `query.count()` distinct hatası `log_service.py:340` |
| **DB & Config** | Model↔spec, migration drift, `ondelete`, `server_default`, UTC, `load_dotenv` | **CRITICAL:** `internships.user_id` FK `ondelete` drift `5678faa6d0c4:31`, ghost `075cea2` pyc kalıntısı, `log_topics.is_ai_suggested` `server_default` yok `a2059b2bee86:75` |
| **Style & Quality** | DRY `normalize`/`isoformat`, `__all__`, `to_dict`, unused import, bulk commit | **HIGH:** `exceptions.py:52` envelope 5x duplicate, `normalize()` 2x duplicate `technology/tag`, `Optional`/`datetime` unused, commit-per-loop |

**Verdict (Faz 3):** Fonksiyonel ama `normalized_name`/ownership/`strict_slashes`/`server_default` fixleri gerekli → 4 fix ajanıyla düzeltildi (solo hardening atlandı).

## 3. Fix Ajanları (Post-Review)

Review sonrası 4 fix ajanı paralel çalıştı:

| Ajan | Görev | Faz |
|------|-------|-----|
| **Infra Fix** | `.gitignore`, `ProductionConfig.validate()`, `load_dotenv` sırası, `run.py` debug | Faz 1 |
| **API Contract Fix** | `AppError.errors` ignored, duplicate JWT handler unify (401), `pagination` `pages` kaldırma | Faz 1 |
| **Data Quality Fix** | `full_name` whitespace bypass, validasyon sırası, `app_context` import hack, `silent=True` | Faz 1 |
| **Structure Fix** | `tests/conftest.py`, `app/core/response.py`, placeholder `__all__` | Faz 1 |
| **Infra Fix (Faz 2)** | `flask db upgrade` drift, `load_dotenv` tekilleştirme (`config.py:6` sil), `ProductionConfig.validate()` length>=32, `internship.user_id ondelete=CASCADE` | Faz 2 |
| **API Contract Fix (Faz 2)** | trailing slash `308` (`route="" strict_slashes=False` + `app.url_map.strict_slashes=False`), `auth_routes.py` + `app/__init__.py` -> `success_response/error_response`, pagination duplicate kaldır, `tech` TODO | Faz 2 |
| **Data Quality Fix (Faz 2)** | `day_number==0`+`is_weekend` 400, gelecek tarih guard, `raw_content` 50k limit, `IntegrityError->409` race, `ilike` escape `\\` | Faz 2 |
| **Structure Fix (Faz 2)** | `app/utils/validators.py` `parse_date/parse_time/today_utc` merkez, `app/utils/time.py` `utcnow` merkez, unused `uuid` temizle, `__all__` + type hint | Faz 2 |
| **Infra Fix (Faz 3)** | `5678faa6d0c4:31` FK `ondelete=CASCADE` fix, `a2059b2bee86:75` `is_ai_suggested` `server_default=0`, `load_dotenv(BASE_DIR/".env")` `app/__init__.py:7`, `mcp/tools.py` + `resources.py` placeholder, `__pycache__` temizlik | Faz 3 |
| **API Contract Fix (Faz 3)** | `internship_routes.py:36,44` + `log_routes.py:85` + `auth_routes.py:10` `strict_slashes=False`, `query.distinct().count()` `log_service.py:337`, `exceptions.py:50` `error_response` DRY, `TechnologyService.normalize`/`TagService.normalize` tek kaynak | Faz 3 |
| **Data Quality Fix (Faz 3)** | `topic.normalized_name` `app/models/topic.py:29` + `uq_topics_user_parent_normalized`, `technology.name unique` kaldır `technology.py:26`, `description` 5000 limit, `link_to_log(user_id)` ownership `topic_service.py:267`, `get_or_create` helper + FK `IntegrityError` ayırt | Faz 3 |
| **Structure Fix (Faz 3)** | `validators.py:61` `normalize_name` merkez, `time.py:15` `iso_or_none`, `__all__` `log_routes/response/exceptions`, unused `Optional/datetime` sil, bulk `flush`+single `commit`, `to_dict()->dict` type hint | Faz 3 |

## 4. Planlanan/Tamamlanan Ajanlar (Faz 2+ ve V2)

### Faz 2 — Core Domain ✅ Tamamlandı (2026-09-14)
- `LogService Agent` — `calculate_day_number` (hafta sonu atlayarak), `duration_minutes` + `daily_logs` CRUD — done `app/utils/date_calculator.py`, `app/services/log_service.py`, `app/models/daily_log.py`
- `Internship Agent` — `POST /internships`, `GET /internships/active` + `GET /<id>` — done `app/services/internship_service.py`, `app/models/internship.py`
- Migration `5678faa6d0c4_faz2_core_domain` head, verify `pytest -v` 2 passed

### Faz 3 — Learning ✅ Tamamlandı (2026-09-14)
- `Topic Agent` — ağaç `parent_id` self-FK, `normalized_name` `UniqueConstraint(user_id,parent_id,normalized_name)`, `usage_count`, `get_tree`/`get_progress`/`get_or_create` — done `app/models/topic.py:26`, `app/services/topic_service.py:26`, `app/api/v1/learning_routes.py:13`
- `Technology/Tag Agent` — many-to-many `log_technologies`/`log_tags`, `normalized_name` global/user-scoped `get_or_create` + `link_to_log` bulk `flush` — done `app/models/technology.py:26`, `tag.py:26`, `app/services/technology_service.py:20`, `tag_service.py:20`
- `Learning API Agent` — `POST /topics` + `GET /tree` + `GET /<id>/progress` + `POST /logs` `technologies/tags/topics` auto-link + `GET /logs?tech=&tag=` filter — done `app/api/v1/learning_routes.py` + `log_routes.py:25,62`
- Migration `a2059b2bee86_faz3_learning` head (`70a5135->5678faa->a2059`), `topics/technologies/tags/log_topics/log_technologies/log_tags` + `is_ai_suggested server_default=0`, `ondelete=CASCADE`, verify `pytest -v` 2 passed + `py_compile` OK + `flask db check` clean

### Faz 5 — AI (Hafifletilmiş)
- `AI Provider Agent` — `AIProviderInterface`, `OpenAIProvider`, `threading.Thread` async, `ai_status: PENDING→REFINED→ACCEPTED/REJECTED/ERROR`, `try-except → ERROR`

### V2 — MCP
```python
# app/mcp/tools.py (architecture.md:8 örneği)
from app.services.log_service import LogService

@mcp.tool()
def get_today_log(user_id: str) -> dict:
    return LogService.get_log_by_date(user_id, datetime.today())

@mcp.tool()
def search_logs(query: str) -> list:
    return LogService.search(query, tech="php")
```
- `mcp/server.py`, `tools.py`, `resources.py` Faz 5 sonrası doldurulacak.

## 5. Ajan Çalıştırma Kuralları

1. **Paralel çalıştırma:** Bağımsız görevler `Task` ile aynı anda tetiklenir.
2. **Security hardening atla:** Solo use olduğu için `kurallar.md:5`’e göre rate limit / revocation / timing mitigation eklenmez.
3. **Doğrulama zorunlu:** Her ajan sonrası `pytest -v` + `python3 -m py_compile` + `flask db` dry-run.
4. **Dil:** Ajan prompt’ları ve kod İngilizce, kullanıcıya özet Türkçe.
5. **Dosya referansı:** Ajan raporlarında `file_path:line_number` formatı kullanılır.

## 6. Yeni Ajan Ekleme

Yeni ajan eklerken:

1. Buraya tabloya ekle (ad, odak, dosyalar).
2. Prompt’ta `architecture.md` ilgili bölümünü referans ver.
3. Çıktısı `Issues (critical/high/medium/low) + What's good + Fix suggestions` formatında olmalı.
4. Fix ajanları doğrudan `Read/Edit/Write` ile uygular, sadece raporlamaz.

---

> İlgili SSOT: `architecture.md:1-2,8,10` + `docs/kurallar.md`
