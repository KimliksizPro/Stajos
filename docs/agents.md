# StajOS Ajan Rehberi

Bu dosya uygulama gecmisi degil, pratik calisma rehberidir.

## Baslangic

1. Once tek aktif kural kaynagi `docs/kurallar.md` dosyasini oku.
2. Teknik baglam icin `architecture.md`, guncel is icin `backlog.md`, kanit ve riskler icin `reports/ana_durum.md` kullan.
3. Istegin OWNS ve DO-NOT-TOUCH sinirlarini belirle; belirsiz kapsamda kisa bir soru sor.

## Uygulama

1. En kucuk dogru degisikligi yap; gereksiz refactor, yeni abstraction veya uyumluluk katmani ekleme.
2. Kullanicinin ya da baska ajanin degisikliklerini geri alma, ezme veya temizleme.
3. Is mantigini service layer'da tut; API, auth, ownership ve veri invariants'larini `docs/kurallar.md` uyarinca koru.
4. Secret, token, `.env`, credential veya gercek kullanici verisini kod, test, log ya da commit'e koyma.
5. Migration gerekiyorsa migration dosyasini uret ve kaynakla birlikte teslim et. Dogrulamayi disposable DB'de `upgrade/current/check` ile yap; production DB'de destructive downgrade calistirma.
6. Birbirinden bagimsiz, ortak dosya veya sirali bagimlilik tasimayan isleri paralel yurut. Ortak state kullanan isleri sirala.

## Dogrulama

1. Degisikligi hedefli testlerle, sonra uygulanabilir tam suite ile dogrula.
2. Basari iddiasindan once komutun gercek cikisini kontrol et; calistirilmayan testi PASS diye raporlama.
3. Dokuman veya kod tesliminde `git status --short`, `git diff --stat` ve `git diff --check` ile kapsam ve whitespace kontrolu yap.
4. Migration kanitinda kullanilan DB turunu belirt; SQLite sonucu PostgreSQL kaniti sayilmaz.

## Raporlama

1. Kullaniciya Turkce ve kisa rapor ver.
2. Bulgulari ve degisiklikleri `dosya:satir` formatinda referansla.
3. Kaniti calistirilan komut ve sonucuyla, riskleri ise acik ve somut olarak yaz.
4. Commit veya push yalniz kullanici acikca isterse yap.

Tamamlanmis plan ve tasarimlar `docs/archive/` altinda tarihsel kayittir; aktif talimat olarak uygulanmaz.
