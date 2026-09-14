# StajOS Proje Kurallari

> Projenin tek aktif kural kaynagi bu dosyadir. Teknik mimari `architecture.md`,
> guncel durum ve tarihli kanitlar `reports/ana_durum.md` icindedir.

## Mimari ve API

- Is mantigi service layer'da kalir; Blueprint/controller yalniz request, service ve response akisini yonetir.
- Tum API yanitlari `success`, `data`, `meta`, `errors` alanli standart envelope kullanir.
- Kimlik dogrulama JWT ile yapilir. Korumali endpoint ve servis sorgularinda ownership `current_user.id` ile dogrulanir; IDOR'a izin verilmez.
- `raw_content` degismez kullanici verisidir. AI ciktisi yalniz `ai_refined_content` gibi ayri alanlara yazilir.
- Tarih ve saatler UTC saklanir ve merkezi zaman yardimcilari kullanilir.
- Liste ve iliski yuklemelerinde N+1 olusturulmaz; uygun `joinedload` veya `selectinload` kullanilir.

### API ve Veri Invariants

- Route'lar slash farkinda `308` uretmez; `strict_slashes=False` davranisi korunur.
- JWT/auth hatalari standart envelope ile `401`, `IntegrityError` kaynakli catismalar `409` doner.
- Ad tabanli uniqueness case-insensitive korunur; kullanici aramasinda `%`, `_` ve `\\` wildcard karakterleri escape edilir.
- Gelecek tarihli veya hafta sonuna denk gelen gunluk girdileri reddedilir.

## Veri, Guvenlik ve Migration

- Inputlar service sinirinda dogrulanir ve limitlenir. Mevcut sinirlar korunur: `raw_content` en fazla 50000, topic `description` en fazla 5000; tarih, sure ve ad alanlarinin mevcut validasyonlari gevsetilmez.
- Production baslangicinda secret/config dogrulamasi zorunludur. `SECRET_KEY` ve `JWT_SECRET_KEY` guclu, default olmayan degerler olmadan production calismaz; secret ve `.env` commit edilmez.
- Migration dosyalari uygulama degisikligiyle birlikte commit edilir; `migrations/versions/**` ignore edilmez.
- Migration dogrulamasi disposable veritabaninda `flask db upgrade`, `flask db current` ve `flask db check` ile yapilir.
- Production veya korunmasi gereken herhangi bir veritabaninda destructive downgrade calistirilmaz. Downgrade testi yalniz acikca disposable veritabaninda yapilir.

## Bilincli Ertelenen Hardening

Solo/personal-use MVP icin su maddeler ertelenmistir: rate limiting, dummy-hash timing mitigation, refresh-token revocation/blocklist ve ek CORS hardening. Bu liste diger auth, ownership, input validation, secret veya veri-butunlugu kontrollerini atlama izni vermez.

## Degisiklik ve Kanit

- En kucuk dogru degisikligi yap; kullanicinin veya baska ajanin ilgisiz degisikliklerini geri alma.
- Davranis degisikligi testle kanitlanir. Sayisal test sonuclari aktif kural degil, tarihli `reports/ana_durum.md` kanitidir.
- Yeni kalici bir kural yalniz bu dosyaya eklenir; diger belgeler buraya link verir, kurali kopyalamaz.
