# StajOS — Proje Kuralları

> Bu doküman StajOS projesinin kalıcı kurallarını ve çalışma prensiplerini tanımlar.
> `architecture.md` single source of truth kalır, burası günlük geliştirme kurallarını özetler.

---

## 1. Proje Felsefesi

- **Solo / Personal Use:** Tek kullanıcı. Multi-tenant, API Key, granüler permission, `audit_logs` yok.
- **Sadeleştirilmiş Stack:** Redis/Celery yok, background işler `threading.Thread` ile.
- **API-First:** Backend HTML render etmez, frontend ve harici agent'lar aynı REST API’yi tüketir.
- **Service Layer Pattern:** Controller (Blueprint) iş mantığı içermez, sadece `request → Service → response`.
- **Strict Separation:** `raw_content` asla ezilmez, AI çıktısı ayrı kolonda (`ai_refined_content`).

## 2. Mimari Kurallar

```
[Client / PWA] ──┐
[External Agent] ─┤
              [Flask Blueprints (Controllers)] <── [MCP Adapter V2]
                        │
              [Service Layer]
                        │
              [Repository / SQLAlchemy ORM]
                        │
              [DB: SQLite (dev) / PostgreSQL (prod)]
```

- Factory pattern: `app/__init__.py:create_app()` + `app/extensions.py` (circular import yasağı).
- Tüm query’ler `current_user.id` filtresiyle yazılır (ileride başkasına açmak sıfır maliyet).
- Klasör yapısı `architecture.md:4` ile birebir aynı kalır.

## 3. Teknoloji Stack

- Python 3.11+ / Flask 3.x / SQLAlchemy 2.0 / Flask-Migrate / Marshmallow
- Auth: **sadece JWT** (Access 1 saat, Refresh 30 gün). API Key sistemi iptal.
- DB: SQLite dev (`stajos_dev.db` - `BASE_DIR` absolute path), PostgreSQL prod.
- Export: `csv` stdlib, PDF `ReportLab` (Faz 6).

## 4. Kodlama Kuralları

- Dil: Kod ve commit İngilizce, API hata mesajları kontrollü Türkçe/İngilizce karışımına izin var ama response envelope sabit.
- Response formatı (`architecture.md:5.1`):
  ```json
  { "success": true/false, "data": {}, "meta": { "page":1,"per_page":20,"total":145 }, "errors": [] }
  ```
- Helper: `app/core/response.py` `success_response` / `error_response` kullanılacak (DRY) — `app/__init__.py:29-58` JWT handler’lar ve `auth_routes.py` dahil her yerde helper zorunlu, manuel `jsonify({"success":..})` yasak (Faz 2 fix).
- Hata hiyerarşisi: `AppError → BadRequest(400), Unauthorized(401), Forbidden(403), NotFound(404), Conflict(409), Validation(422)`. Tüm hatalar `register_error_handlers`’dan geçer. `IntegrityError` → `ConflictError(409)` ile sarılır (Faz 2 race guard).
- JWT hataları (missing/invalid/expired/revoked) hepsi `401` döner, standart envelope ile.
- Pagination: `meta: {page, per_page, total}` - fazladan `pages` eklenmez. Sanitization tek kaynak `app/core/pagination.py:get_pagination_params` (service içinde tekrar `int()` yapılmaz).
- Blueprint routing: `strict_slashes=False` + `route("", ...)` kullanılır, `route("/")` ile `308` redirect yasak (`architecture.md:5.2` slashsız contract).
- Import: `extensions.py` üzerinden `db, jwt, migrate` import edilir, doğrudan `app` import edilmez. `app/utils/validators.py:14` `parse_date/parse_time/today_utc/normalize_name` ve `app/utils/time.py:11` `utcnow/iso_or_none` merkezi kullanılır — service içinde duplicate `_parse_date/_utcnow/_normalize` yasak (Faz 2-3 DRY). `normalize_name` tek kaynak: `(name or "").strip().lower()` (Faz 3).
- Validasyon: `raw_content` max 50000, `topic.description` max 5000, `topic.name`/`technology.name`/`tag.name` strip zorunlu + `normalized_name` ile case-insensitive unique DB’de korunur (`Tag`/`Topic`: `user_id+parent_id+normalized_name`, `Technology`: global `normalized_name`), `day_number==0` ve `is_weekend` 400, gelecek tarih `>today_utc()` 400, `ilike` aramalarda `%_ \` escape `escape="\\"` zorunlu.
- Tip ipucu ve docstring: yeni servis/fonksiyonlarda type hint zorunlu değil ama tercih edilir.
- Dosya sonu newline, `__all__ = []` placeholder’larda bulunur.

## 5. Güvenlik Yaklaşımı (Solo Mode)

> Faz 1+2 code-review’de unanimous karar: **ağır güvenlik hardening personal use için gereksiz.**

- **Uygulanmaz:** rate limiting (`Flask-Limiter`), timing-attack mitigation (dummy hash), refresh token revocation/blocklist, scrypt method pin, CORS hardening.
- **Uygulanır:** Werkzeug `generate_password_hash/check_password_hash`, email `lower().strip()`, `full_name.strip()`, `topic/technology/tag` `normalize_name` (`lower().strip()`), şifre min 6 (personal use), 401/409 mesajları jenerik, `.env` gitignore, `SECRET_KEY` dev fallback prod’da `validate()` ile engellenir. Faz 2: `raw_content` 50k limit, `IntegrityError` race -> `409`, `ilike` escape, `future date` + `weekend` 400, `Authorization` header ile `strict_slashes=False` 308 engeli. Faz 3: `link_to_log` ownership (`Topic` `user_id` + `DailyLog`→`Internship.user_id` çift doğrulama), `topics`/`tags` case-insensitive unique DB’de (`normalized_name`) korunur, `description` 5000 limit.
- Prod’a çıkmadan `ProductionConfig.validate()` mutlaka çalışır (`DATABASE_URL`, `SECRET_KEY`>=32, `JWT_SECRET_KEY`>=32 ve default değil — `config.py:43-46` Faz 2 hardening).

## 6. Veri & Veritabanı Kuralları

- `users`: `id` UUID(v4) String(36) PK, `email` unique+index, `password_hash`, `full_name`, `created_at` UTC (`timezone=True`, `utcnow()` `app/utils/time.py`).
- `internships`: `id` UUID, `user_id` FK `users.id ondelete=CASCADE` index, `company_name`, `start_date/end_date` Date, `total_expected_days` Integer>0, `status` Enum ACTIVE/COMPLETED/PAUSED, `created_at/updated_at` UTC. `daily_logs`: `id` UUID, `internship_id` FK `ondelete=CASCADE`, `date` + `day_number` (>=1, 0 yasak, hafta sonu 400), `start_time/end_time` Time nullable, `duration_minutes` Integer (floor), `title` 255, `raw_content` Text (max 50000, asla ezilmez), `ai_refined_content` nullable, `ai_status` PENDING→ERROR, `UniqueConstraint(internship_id,date)` (Faz 2).
- `topics`: `id` UUID, `user_id` FK `users.id ondelete=CASCADE` index, `parent_id` FK `topics.id ondelete=CASCADE` nullable (self-ref ağaç), `name` 255 + `normalized_name` 255 not null, `description` Text nullable (max 5000), `first_seen_at` Date `today_utc()`, `usage_count` Integer default 0, `UniqueConstraint(user_id,parent_id,normalized_name)` + M2M `log_topics(log_id,topic_id)` `is_ai_suggested` Boolean `server_default=0` (Faz 3). `technologies`: `id` UUID, `name` 100, `normalized_name` 100 unique+index (global), M2M `log_technologies(log_id,technology_id)` `ondelete=CASCADE`. `tags`: `id` UUID, `user_id` FK `ondelete=CASCADE`, `name` 100 + `normalized_name` 100, `UniqueConstraint(user_id,normalized_name)`, M2M `log_tags(log_id,tag_id)` `ondelete=CASCADE` (Faz 3).
- `migrations/versions/*.py` **commitlenir** (`.gitignore`’da ignore yok). Faz 3 head `a2059b2bee86_faz3_learning` (`70a5135->5678faa->a2059`).
- `Flask-Migrate` tek kaynak, `db.create_all()` sadece test’te. `flask db upgrade` Faz bitiminde zorunlu (drift `flask db check` ile tespit).
- Tarih/saat UTC saklanır (`§10.3`). `app/utils/time.py:utcnow()` tek kaynak, `_utcnow` duplicate yasak.
- Validasyon DB+Service çift katman: `total_expected_days>0`, `start_date<=end_date`, `day_number>0`, `duration end>start` service’te + `CHECK` mümkünse DB’de.
- `app/utils/validators.py:parse_date` (YYYY-MM-DD strict) + `normalize_name` tek kaynak, `app/utils/time.py:iso_or_none` `to_dict` DRY helper, `app/utils/date_calculator.py:calculate_day_number` hafta sonu atlar, `calculate_duration_minutes` floor. Bulk `log_*` linklerde `flush` per-item + tek `commit` (Faz 3), `exceptions.py` `error_response` helper tek kaynak (manuel `jsonify` yasak).
- N+1 için `joinedload/selectinload` kullanılacak (Faz 2’den itibaren) — `get_logs` `selectinload(DailyLog.technologies/tags/topics)` + `query.distinct().count()` distinct-aware `total` (`log_service.py:337`) ile Faz 3’te düzeltildi (`get_log_by_id` tek query ownership check’e indirildi).
- `Technology` global (`normalized_name` unique), `Tag`/`Topic` user-scoped (`user_id+normalized_name`) ayrımı korunur; `link_to_log` `user_id` ownership zorunlu, `TechnologyService.normalize`/`TagService.normalize` -> `validators.normalize_name` tek kaynak (Faz 3).
- `Blueprint routing`: Faz 3’ten itibaren tüm route’lar `strict_slashes=False` zorunlu — `auth_routes.py` (register/login/me/refresh) + `internship_routes.py` (`/active`, `/<id>`) + `log_routes.py` (`/<id>`) + `learning_routes.py` (`/topics`, `/tree`, `/<id>/progress`) dahil (Faz 3 fix: `app/__init__.py:18` global `url_map.strict_slashes=False` + per-route `strict_slashes=False`).
- SQLite `timezone=True` naive düşer, prod PG `TIMESTAMPTZ` - fark bilinçli kabul.

## 7. Test Kuralları

- `tests/conftest.py` fixture’ları (`app`, `client`) merkezi, her test dosyasında tekrar tanımlanmaz.
- `TestingConfig` `sqlite:///:memory:` + `db.create_all/drop_all`.
- Yeni endpoint → en az happy + 401/400/409 edge testi.
- `pytest -v` Faz 1’de 2 test, Faz 2’den sonra coverage hedefi eklenebilir.

## 8. Çalışma Akışı

- Faz bazlı ilerleme: `architecture.md:9` Faz 1-6 sırası bozulmaz.
- Branch: `Faz N` bitince review agent’larla kontrol, onay sonrası commit.
- Commit öncesi kontroller: `python3 -m py_compile`, `pytest`, `flask db migrate` dry-run.
- `run.py` sadece `app.config["DEBUG"]` kullanır, hardcoded `debug=True` yasak.
- `.env` dosyası commitlenmez, `.env.example` güncel tutulur.

## 9. Kritik Yasaklar

1. Controller içinde business logic yazmak.
2. `raw_content`’i AI çıktısıyla ezmek.
3. `migrations/versions/*.py`’yi gitignore’lamak.
4. `ProductionConfig` validasyonunu atlamak.
5. `db` veya `jwt`’yi `extensions.py` dışından oluşturmak.
6. `stajos_dev.db`’yi commitlemek.

## 10. Dokümanlar

- `architecture.md` — mimari SSOT
- `docs/kurallar.md` — bu dosya
- `docs/agents.md` — ajan tanımları ve kullanım kuralları

> Yeni kural eklenirse buraya yazılır ve ilgili ajan prompt’una eklenir.
