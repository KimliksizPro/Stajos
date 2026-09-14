# Faz 5 AI Entegrasyonu Tasarimi

## Amac ve Kapsam

Faz 5, gunluk kaydinin ham metnini request'i bloklamadan OpenAI uyumlu bir servisle iyilestirir. AI; iyilestirilmis metin ile teknoloji, konu ve etiket onerileri uretir. Kullanici bu sonucu kabul veya reddeder; `raw_content` her durumda degismez kalir.

Kapsam; provider soyutlamasi, kati cikti dogrulamasi, sinirli background executor, startup recovery, durum gecisleri ve accept/reject endpointleridir. Kalici harici kuyruk, streaming, otomatik retry/backoff ve AI tarafindan yeni topic hiyerarsisi olusturma bu fazin disindadir.

## Mimari

### Provider ve Yapilandirma

- `AIProviderInterface`, ham metin alip JSON'a donusturulebilir bir provider cevabi donduren sozlesmedir.
- OpenAI uyumlu implementasyon `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` ve `AI_TIMEOUT_SECONDS` ayarlarini kullanir.
- `AI_ENABLED` kapaliyken yeni loglar normal olusur ancak background gorev kuyruga alinmaz. Acikken gerekli provider ayarlari uygulama baslangicinda dogrulanir.
- Provider ve executor application factory tarafindan olusturulur ve `app.extensions` icinde tutulur. Testler fake provider ile inline/fake executor enjekte eder.

### Cikti Sozlesmesi ve Guardrail'ler

System prompt su degismez kurallari icerir:

1. Yalniz verilen `raw_content` metnine dayan.
2. Metinde bulunmayan teknoloji veya konuyu uydurma.
3. Yalniz kesin JSON dondur.

Beklenen cikti:

```json
{
  "refined_content": "Duzeltilmis gunluk metni",
  "technologies": ["Python"],
  "topics": ["API Gelistirme"],
  "tags": ["backend"]
}
```

Parser; top-level nesneyi, tam alan listesini, alan tiplerini, bos olmayan ve uzunlugu sinirli metni, string listelerini ve normalize edildikten sonraki tekrarli degerleri dogrular. Markdown fence, ek aciklama, eksik/fazla alan veya gecersiz JSON reddedilir. Prompt guardrail'i tek basina guvenlik siniri sayilmaz; provider cevabi guvenilmeyen girdidir.

### Kalici Veri

`AIStatus` enum'u atomik claim icin `PROCESSING` degerini kazanir. `DailyLog` mevcut `ai_refined_content` alanini kullanir; uc nullable JSON alani ve bir nullable zaman alani kazanir:

- `ai_suggested_technologies`
- `ai_suggested_topics`
- `ai_suggested_tags`
- `ai_processing_started_at`

JSON alanlari AI onerilerini `REFINED` asamasinda iliskileri degistirmeden saklar. Zaman alani stale `PROCESSING` kayitlarin recovery sirasinda bulunmasini saglar. Yeni Alembic migration'i enum ve dort alani ekler. `raw_content` hicbir AI veya accept/reject akisi tarafindan yazilmaz.

### Background Isleme

- Yeni log once commit edilir ve `PENDING` durumunda kalir; ardindan yalniz `log_id` sinirli `ThreadPoolExecutor`'a verilir.
- Worker request'e ait ORM nesnesi veya session tasimaz. Kendi Flask application context'ini acar, kaydi ID ile tekrar yukler, commit/rollback yapar ve session'i temizler.
- Worker, tek SQL `UPDATE ... WHERE ai_status = PENDING` islemiyle kaydi `PROCESSING` durumuna alarak claim eder. Claim basarisizsa provider'i cagirmadan cikar. Basarida iyilestirilmis metin ve oneriler atomik olarak yazilir, durum `REFINED` olur. Provider, timeout veya parser hatasinda durum `ERROR` olur.
- Hata ayrintisi secret veya kullanici verisi sizdirmadan application logger'a yazilir. API'ye provider cevabi veya credential donulmez.
- Executor sabit sayida worker kullanir. Queue submission hatasi loglanir ve kayit `PENDING` kalir; startup recovery tekrar deneyebilir.

### Startup Recovery

Uygulama acilisinda, migration ve tablolar hazir olduktan sonra, halen `PENDING` olan log ID'leri sinirli batch'ler halinde ayni executor'a verilir. Recovery idempotenttir: birden fazla process ayni ID'yi gorebilse de atomik `PENDING -> PROCESSING` claim'i provider'in yalniz bir worker tarafindan cagirilmasini saglar. Process crash sonrasi `PROCESSING` kalan kayitlar `ai_processing_started_at` suresi `AI_STALE_AFTER_SECONDS` degerini astiysa tekrar `PENDING` yapilip submit edilir.

Testing config recovery'yi varsayilan olarak kapatir; recovery testleri bunu acikca etkinlestirir. Startup recovery request yolunu bloklayacak provider cagrisi yapmaz, yalniz gorev submit eder.

## Durum Makinesi

Izin verilen gecisler:

- `PENDING -> PROCESSING`: Worker kaydi atomik olarak claim etti.
- `PROCESSING -> REFINED`: Gecerli provider sonucu kalici yazildi.
- `PROCESSING -> ERROR`: Provider, timeout veya parser hatasi olustu.
- `REFINED -> ACCEPTED`: Kayit sahibi AI sonucunu kabul etti.
- `REFINED -> REJECTED`: Kayit sahibi AI sonucunu reddetti.

Diger tum gecisler `409 Conflict` dondurur. Ayni accept/reject istegini tekrar etmek de `409` sonucudur; sessiz idempotency uygulanmaz.

## Accept ve Reject

- `PUT /api/v1/logs/<uuid>/accept-ai` ve `PUT /api/v1/logs/<uuid>/reject-ai` JWT gerektirir.
- Servis sorgulari logu internship owner'i ile kapsamlar; baska kullanicinin kaydi `404` olarak gizlenir.
- Accept yalniz `REFINED` kayitta calisir. `ai_refined_content` ayri alanda kalir; `raw_content` uzerine kopyalanmaz.
- Accept, onerilen technology ve tag adlarini mevcut case-insensitive get-or-create servisleriyle loga baglar. Topic icin mevcut topic bulunur ve baglanir; AI tarafindan parent bilgisi gelmedigi icin bulunmayan topic otomatik olusturulmaz.
- AI tarafindan eklenen topic baglantilarinda `is_ai_suggested=True` korunur. Mevcut manuel iliskiler silinmez ve usage counter davranisi mevcut servis sozlesmesini izler.
- Reject yalniz durumu `REJECTED` yapar; mevcut veya onerilen iliskileri degistirmez. Oneri JSON'u denetim ve goruntuleme icin saklanir.
- Iki endpoint de standart response envelope icinde guncel `DailyLog` verisini dondurur.

## API Gorunurlugu

`DailyLog.to_dict()` mevcut AI alanlarina ek olarak uc oneri listesini dondurur. Boylece frontend `REFINED` sonucu kabul etmeden once hem metni hem iliski onerilerini gosterebilir. Provider ham cevabi API modeline eklenmez.

## Hata Davranisi

- Provider veya parser hatasi request sonucunu geriye donuk degistirmez; log daha once basariyla olusmustur.
- Worker hatasi kaydi `ERROR` yapar ve yapilandirilmis log uretir.
- Accept/reject icin bulunamayan veya sahip olunmayan kayit `404`, gecersiz durum gecisi `409`, auth hatasi standart envelope ile `401` dondurur.
- DB yazma hatasinda session rollback edilir; kismi AI metni veya kismi iliski kabulü commit edilmez.

## Test Stratejisi

- Provider: OpenAI uyumlu istemci ayarlari, timeout ve hata esleme fake istemciyle test edilir; gercek ag cagrisi yapilmaz.
- Parser: gecerli JSON, malformed/fenced JSON, eksik/fazla alan, yanlis tip, bos/uzun metin ve duplicate liste degerleri kapsanir.
- Worker: `PENDING -> PROCESSING -> REFINED/ERROR`, app context, session temizligi, duplicate claim ve `raw_content` degismezligi test edilir.
- Recovery: startup'ta yalniz `PENDING` ID'lerin submit edildigi ve testing default'unun recovery calistirmadigi test edilir.
- API: JWT, ownership, `REFINED -> ACCEPTED/REJECTED`, gecersiz gecislerde `409`, AI iliski baglama ve response envelope kapsanir.
- Regression: mevcut tam pytest suite calistirilir. Migration disposable SQLite veritabaninda `upgrade`, `current` ve `check` ile dogrulanir; bu PostgreSQL kaniti sayilmaz.

## Kabul Kriterleri

- Log olusturma AI ag gecikmesini beklemeden cevap verir.
- Basarili AI islemi atomik claim sonrasinda dogrulanmis metin ve onerileri saklayip kaydi `REFINED` yapar.
- Her provider/parser hatasi kaydi `ERROR` yapar; `raw_content` aynen kalir.
- Startup recovery eski `PENDING` kayitlari yeniden submit eder.
- Yalniz kayit sahibi ve yalniz `REFINED` durumunda accept/reject yapabilir.
- Accept onerileri belirtilen kurallarla baglar; reject iliskileri degistirmez.
- Tum hedefli testler, tam suite ve migration kontrolleri gecer.
