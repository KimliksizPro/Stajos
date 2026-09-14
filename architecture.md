
# StajOS — Sadeleştirilmiş Mimari ve Geliştirme Planı (Solo Edition)

Bu dokuman StajOS'un teknik mimari kaynagidir. Aktif proje kurallari yalniz `docs/kurallar.md`, durum ve kanitlar `reports/ana_durum.md` icindedir.

---

## 1. MİMARİ PRENSİPLER VE YÜKSEK SEVİYE TASARIM

### 1.1. Temel Yaklaşım
*   **API-First:** Frontend veya Harici Agent'lar aynı REST API'yi tüketir. Backend HTML render etmez.
*   **Service Layer Pattern:** Controller'lar (Flask Blueprints) iş mantığı içermez. Sadece request'i alır, Service katmanına iletir ve response döner. MCP eklendiğinde doğrudan Service'leri çağıracaktır.
*   **Strict Separation of Concerns:** AI çıktısı ile Kullanıcı verisi asla aynı kolonda ezilmez.

### 1.2. Katmanlı Mimari Şeması

```text
[Client: Web / PWA]
          │
[External Agents / Harness] ──┐
          │                   │
    [Flask Blueprints (Controllers)] <── [MCP Server Adapter (V2)]
          │                   │
    [Service Layer (Business Logic & AI Orchestration)]
          │
    [Repository / SQLAlchemy ORM]
          │
    [Database (SQLite Dev / PostgreSQL Prod)]
```

---

## 2. TEKNOLOJİ STACK (Sadeleştirilmiş MVP)

*   **Backend Framework:** Python 3.11+ / Flask 3.x
*   **API & Serialization:** Marshmallow + Flask Blueprint (veya Flask-RESTX).
*   **Database:** SQLite (Local Dev için sıfır kurulum), PostgreSQL (Production).
*   **ORM:** SQLAlchemy 2.0.
*   **Migration:** Flask-Migrate (Alembic).
*   **Authentication:** JWT (Flask-JWT-Extended). Tek kullanıcı olacağın için API Key sistemi iptal edildi, her şey JWT üzerinden dönecek.
*   **Background Tasks (AI için):** Celery/Redis **iptal edildi**. Bunun yerine Python standart kütüphanesindeki `threading.Thread` veya basit bir arka plan worker kullanılacak.
*   **Export:** Standart kütüphane `csv`, PDF için `ReportLab` veya sadece JSON/Markdown export.

---

## 3. VERİ MODELİ (DATABASE SCHEMA)

Kurumsal güvenlik tabloları (`api_keys`, `audit_logs`) çıkarıldı. Multi-tenancy yerine "Single-Tenant" mantığına geçildi ancak mimari temizliği bozmamak için `user_id` ilişkileri korundu.

**1. `users`**
*   `id` (UUID, PK)
*   `email` (String, Unique)
*   `password_hash` (String)
*   `full_name` (String)
*   `created_at` (DateTime)

**2. `internships`**
*   `id` (UUID, PK)
*   `user_id` (FK -> users.id)
*   `company_name` (String)
*   `start_date` (Date)
*   `end_date` (Date)
*   `total_expected_days` (Integer)
*   `status` (Enum: ACTIVE, COMPLETED, PAUSED)

**3. `daily_logs`**
*   `id` (UUID, PK)
*   `internship_id` (FK -> internships.id)
*   `date` (Date, Unique per internship)
*   `day_number` (Integer - Otomatik hesaplanır)
*   `start_time` (Time, Nullable)
*   `end_time` (Time, Nullable)
*   `duration_minutes` (Integer - Hesaplanmış)
*   `title` (String)
*   `raw_content` (Text) - *ASLA DEĞİŞTİRİLMEZ.*
*   `ai_refined_content` (Text, Nullable)
*   `ai_status` (Enum: PENDING, REFINED, ACCEPTED, REJECTED, ERROR)
*   `created_at`, `updated_at` (DateTime)

**4. `log_sections`** (Opsiyonel ama yapısal bütünlük için duruyor)
*   `id` (UUID, PK)
*   `log_id` (FK -> daily_logs.id)
*   `section_type` (Enum: WHAT_I_DID, WHAT_I_LEARNED, PROBLEM, SOLUTION)
*   `raw_text` (Text)
*   `ai_refined_text` (Text, Nullable)

**5. `technologies`**
*   `id` (UUID, PK)
*   `name` (String, Unique)
*   `normalized_name` (String)

**6. `log_technologies`** (Many-to-Many)
*   `log_id` (FK)
*   `technology_id` (FK)

**7. `topics`** (Öğrenme Konuları - Ağaç Yapısı)
*   `id` (UUID, PK)
*   `user_id` (FK -> users.id)
*   `parent_id` (FK -> topics.id, Nullable)
*   `name` (String)
*   `description` (Text)
*   `first_seen_at` (Date)
*   `usage_count` (Integer)

**8. `log_topics`** (Many-to-Many)
*   `log_id` (FK)
*   `topic_id` (FK)
*   `is_ai_suggested` (Boolean)

**9. `tags`**
*   `id` (UUID, PK)
*   `user_id` (FK)
*   `name` (String)

**10. `log_tags`** (Many-to-Many)
*   `log_id` (FK)
*   `tag_id` (FK)

**11. `attachments`**
*   `id` (UUID, PK)
*   `log_id` (FK)
*   `file_path` (String)
*   `mime_type` (String)

*(Not: `api_keys` ve `audit_logs` tabloları tamamen silindi.)*

---

## 4. MODÜL SINIRLARI VE KLASÖR YAPISI

```text
stajos-backend/
│
├── app/
│   ├── __init__.py                 # create_app() factory function
│   ├── extensions.py               # db, jwt, migrate init
│   │
│   ├── api/                        # Controllers (Blueprints)
│   │   ├── v1/
│   │   │   ├── auth_routes.py
│   │   │   ├── internship_routes.py
│   │   │   ├── log_routes.py
│   │   │   ├── learning_routes.py
│   │   │   └── report_routes.py
│   │
│   ├── core/                       # Cross-cutting concerns
│   │   ├── security.py             # Hashing, JWT helpers
│   │   ├── exceptions.py           # Custom HTTP Errors
│   │   └── pagination.py           # Standardize pagination
│   │
│   ├── models/                     # SQLAlchemy Models
│   │   ├── user.py
│   │   ├── internship.py
│   │   ├── daily_log.py
│   │   ├── topic.py
│   │   └── ...
│   │
│   ├── services/                   # Business Logic (EN ÖNEMLİ KATMAN)
│   │   ├── log_service.py
│   │   ├── ai_service.py
│   │   ├── report_service.py
│   │   └── stats_service.py
│   │
│   ├── ai/                         # AI Providers & Prompts
│   │   ├── base_provider.py        # Interface
│   │   ├── openai_provider.py      # Veya local LLM provider
│   │   ├── prompts.py              # System prompts
│   │   └── parser.py               # AI çıktısını JSON'a çevirme
│   │
│   ├── mcp/                        # V2 için boş bırakılacak
│   │   ├── server.py
│   │   ├── tools.py
│   │   └── resources.py
│   │
│   └── utils/                      # Helpers
│       ├── date_calculator.py      # Hafta sonlarını atlayarak staj günü hesaplama
│       └── exporters.py            # JSON/CSV export logic
│
├── migrations/                     # Alembic
├── tests/                          # Pytest
├── config.py                       # Dev, Prod configs
├── requirements.txt
└── run.py                          # Entry point
```

---

## 5. API SÖZLEŞMELERİ (CONTRACTS)

### 5.1. Standart Response Formatı
```json
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "per_page": 20, "total": 145 },
  "errors": []
}
```

### 5.2. Kritik Endpointler (MVP)

**Auth**
*   `POST /api/v1/auth/register`
*   `POST /api/v1/auth/login` (Returns JWT Access + Refresh Token)

**Internships**
*   `POST /api/v1/internships`
*   `GET /api/v1/internships/active`

**Daily Logs**
*   `POST /api/v1/logs`
    *   *Payload:* `{ "raw_content": "...", "start_time": "09:00", "end_time": "17:00", "technologies": ["php", "git"] }`
    *   *Logic:* `date` backend'de atanır. `day_number` servis katmanında hesaplanır. AI analizi `threading.Thread` ile arka planda tetiklenir.
*   `GET /api/v1/logs` (Query params: `?start_date=...&tech=php&search=form&page=1`)
*   `GET /api/v1/logs/<uuid>`
*   `PUT /api/v1/logs/<uuid>/accept-ai`
*   `PUT /api/v1/logs/<uuid>/reject-ai`

**Learning & Topics**
*   `POST /api/v1/topics`
*   `GET /api/v1/topics/tree`
*   `GET /api/v1/topics/<uuid>/progress`

**Dashboard & Stats**
*   `GET /api/v1/dashboard/stats`
*   `GET /api/v1/timeline`

**Exports**
*   `GET /api/v1/export/json`
*   `GET /api/v1/export/csv`

---

## 6. GÜVENLİK VE YETKİLENDİRME (SOLO MODE)

### 6.1. Kimlik Doğrulama
*   Sadece JWT kullanılacak. Tek kullanıcı olduğun için API Key yönetimi, granüler izinler (`logs:read`, `logs:write` vs.) ve `@require_agent_permission` dekoratörleri **tamamen iptal edildi**.
*   Harici bir Agent çağrı yapacaksa, normal bir kullanıcı gibi login olup JWT alacak ve o JWT ile istek atacak.

### 6.2. Veri İzolasyonu
*   Sistemde tek kullanıcı olsan da, kod kalitesinin bozulmaması için her query `current_user.id` filtresiyle çekilmeye devam edilecek. Bu, ileride projeyi başkasına açmak istersen sıfır refactoring maliyeti demektir.

### 6.3. AI Güven İlkesi (Prompt Guardrails)
AI servisine gönderilen System Prompt'ta şu kurallar sabitlenmelidir:
1.  "Sadece sana verilen metne dayanarak çıkarım yap."
2.  "Metinde geçmeyen bir teknoloji veya konuyu uydurma."
3.  Çıktı formatı kesinlikle JSON olmalıdır.

---

## 7. İŞ MANTIKI VE ALGORİTMALAR

### 7.1. Otomatik Staj Günü Hesaplama
*Algoritma:*
1.  Stajın `start_date`'ini al.
2.  Bugünün tarihini al.
3.  Aradaki hafta sonlarını çıkar.
4.  Sıradaki iş gününü `day_number` olarak ata.
*Yer:* `services/log_service.py` -> `calculate_day_number(internship_id, target_date)`

### 7.2. Ham Veri vs AI Verisi Akışı (Celery Yerine Threading)
1.  Kullanıcı POST isteği atar. `raw_content` DB'ye yazılır. `ai_status = PENDING`.
2.  Bir `threading.Thread(target=process_ai, args=(log_id,)).start()` tetiklenir. (Request'i bloklamaz).
3.  Thread içinde AI provider'a istek atılır.
4.  Yanıt dönünce `ai_refined_content` yazılır, `ai_status = REFINED` yapılır.
5.  Frontend kullanıcıya sorar. Kabul edilirse `ACCEPTED`, reddedilirse `REJECTED`. Orijinal `raw_content` hep kalır.

### 7.3. Öğrenme Grafiği
Kullanıcı "PHP Form Validation" yazdığında sistem `topics` tablosunda bakar, yoksa oluşturur, `log_topics` ile bağlar ve `usage_count` artırır.

---

## 8. MCP HAZIRLIĞI (V2)

Controller'lar iş yapmayacağı için MCP entegrasyonu çok kolay olacak:
```python
# app/mcp/tools.py
from app.services.log_service import LogService

@mcp.tool()
def get_today_log(user_id: str) -> dict:
    return LogService.get_log_by_date(user_id, datetime.today())
```

---

## 9. MVP GELİŞTİRME PLANI

### Faz 1: Temel Altyapi - Tamamlandi
1.  Proje klasör yapısının kurulması (Application Factory).
2.  Config yönetimi (.env, SQLite ayarı).
3.  Database bağlantısı ve User modeli.
4.  Auth sisteminin (Register/Login/JWT) yazılması.
5.  Global Error Handler ve Standart Response formatı.

### Faz 2: Core Domain ✅ Tamamlandı (2026-09-14)
1.  `Internship` ve `DailyLog` modelleri — `app/models/internship.py`, `daily_log.py` + migration `5678faa6d0c4`
2.  Staj ve Günlük CRUD endpointleri — `POST /internships` + `GET /active` + `GET /<id>`, `POST /logs` + `GET /logs` + `GET /logs/<id>` (`strict_slashes=False`)
3.  `calculate_day_number` algoritması — `app/utils/date_calculator.py:24` hafta sonu atlayarak, `0` ve `weekend` 400 guard + `app/utils/validators.py`
4.  `duration_minutes` hesaplama mantığı — `calculate_duration_minutes` floor + `parse_time` merkezi, `raw_content` 50k limit, `IntegrityError->409` race guard

### Faz 3: Öğrenme Sistemi ✅ Tamamlandı (2026-09-14)
1.  `Technology`, `Topic`, `Tag` modelleri ve Many-to-Many ilişkileri — `app/models/topic.py`, `technology.py`, `tag.py` + `log_topics/log_technologies/log_tags` + migration `a2059b2bee86_faz3_learning` head
2.  Log oluştururken otomatik ilişkilendirme mantığı — `POST /logs` `technologies/tags/topics` auto-link (`get_or_create` + `normalized_name`, `usage_count` increment) — `app/services/log_service.py:29`, `topic_service.py:109`, `technology_service.py:20`, `tag_service.py:20`
3.  Topic ağaç yapısı endpointleri — `POST /api/v1/topics`, `GET /api/v1/topics/tree`, `GET /api/v1/topics/<id>/progress` + `GET /logs?tech=&tag=` filter — `app/api/v1/learning_routes.py:13` + `app/__init__.py:55`

### Faz 4: Arama, Filtreleme ve Timeline - Tamamlandi (2026-09-14)
1.  Log arama, filtreleme ve siralama endpointi tamamlandi.
2.  Takvim/Timeline GET endpointi tamamlandi.
3.  Dashboard istatistik endpointleri tamamlandi.
4.  Review/fix ve final dogrulama commit `cd99529` ile kapatildi; kanit `reports/ana_durum.md` icindedir.

### Faz 5: AI Entegrasyonu (Hafifletilmis) - Siradaki
1.  `AIProviderInterface` soyut sınıfı.
2.  OpenAI/LLM implementasyonu.
3.  `threading.Thread` ile asenkron AI çağrısı.
4.  Accept/Reject AI mekanizması.

### Faz 6: Export ve Son Rötuşlar
1.  JSON ve CSV export endpointleri.
2.  Swagger/OpenAPI dokümantasyonu.
3.  Gün hesaplama ve AI parser için Unit testler.

---

## 10. UYGULAMA NOTLARI

Kalici uygulama ve guvenlik invariants'lari `docs/kurallar.md` icindedir. Faz 5 AI akisinin teknik beklentileri 6.3 ve 7.2 bolumlerinde tanimlanmistir.
