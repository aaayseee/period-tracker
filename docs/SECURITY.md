# Güvenlik Modeli

## Korunan veriler

Uygulama şu hassas bilgileri işler:

- E-posta adresi
- Regl başlangıç ve bitiş tarihleri
- Semptomlar
- Kişisel notlar
- Döngü tahminleri

Parolanın kendisi saklanmaz. JSON yedeğine hesap, parola hash'i, salt veya session bilgisi eklenmez.

## Parola saklama

Kayıt sırasında:

1. 16 byte kriptografik rastgele salt üretilir.
2. Parola PBKDF2-HMAC-SHA256 ile hash'lenir.
3. Varsayılan iterasyon sayısı 310.000'dir.
4. Salt ve hash ayrı kolonlarda hex olarak saklanır.
5. Girişte hash'ler `hmac.compare_digest` ile sabit zamanlı karşılaştırılır.

Bu yaklaşım kişisel uygulama için makuldür. Yeni üretim projelerinde Argon2id de değerlendirilebilir.

## Session modeli

- Ham session token `secrets.token_urlsafe(32)` ile oluşturulur.
- Veritabanında yalnızca token'ın SHA-256 özeti tutulur.
- Ham token `luna_session` HttpOnly cookie içindedir.
- `SameSite=Strict` CSRF riskini azaltır.
- Varsayılan süre 30 gündür.
- Çıkış session satırını siler ve cookie'yi temizler.
- Süresi dolmuş session'lar yeni session oluşturulurken temizlenir.

Session süresi dolduğunda hesap ve döngü verileri silinmez.

## Cookie ayarları

Yerel HTTP geliştirmede:

```text
HttpOnly=true
SameSite=Strict
Secure=false
```

HTTPS production ortamında:

```powershell
$env:PERIOD_TRACKER_SECURE_COOKIE = "true"
```

`Secure=true` olmadan internet üzerinden yayın yapılmamalıdır.

## API koruması

Profil, regl kayıtları, tahmin, export ve restore endpoint'leri geçerli session ister. Session olmadan `401 Unauthorized` döner.

Kişisel veri endpoint'leri ayrıca `user` rolü ister ve her SQL sorgusunu oturumdaki `account_id` ile filtreler. Admin hesabı bu endpoint'lerde `403 Forbidden` alır. Admin endpoint'leri yalnızca hesap/davet metadatası seçer; sağlık tablolarını okumaz.

Admin hareketleri `admin_audit_logs` tablosuna yazılır. Audit servisi action başına izinli detay anahtarlarını allow-list ile sınırlar. Parola, kurtarma kodu, ham davet kodu, regl tarihi, semptom veya not kabul edilmez. Kayıtlar yönetim işlemiyle aynı transaction içinde yazılır; işlem geri alınırsa audit kaydı da geri alınır.

Kayıt davet koduyla sınırlandırılır. Ham davet kodu saklanmaz; SHA-256 özeti, son tarih, kullanım limiti ve iptal durumu tutulur. Hesap oluşturma ile davetin tüketimi aynı transaction içindedir.

Public endpoint'ler:

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/recover`
- `GET /api/auth/session`
- `POST /api/auth/logout`

SQL sorguları placeholder parametreleri kullanır; kullanıcı girdisi SQL metnine birleştirilmez.

## Mevcut tehdit modeli

Mevcut sürüm şu ortamı hedefler:

- Davetli, düşük trafikli küçük kullanıcı grubu
- Kişisel bilgisayar veya kontrol edilen sunucu
- Güvenilir yerel ağ ya da HTTPS
- Düşük istek hacmi

Auth koruması:

- Login: aynı IP+e-posta kovasında 15 dakikada 5 başarısız deneme
- Parola kurtarma: 30 dakikada 5 başarısız deneme
- Davetli kayıt: 60 dakikada 10 başarısız deneme
- Parola değiştirme: 15 dakikada 5 başarısız deneme
- Limit aşımında `429 Too Many Requests` ve `Retry-After` başlığı
- Başarılı işlem ilgili kovayı temizler; düz e-posta/IP yerine SHA-256 kova hash'i saklanır

Limit olayları SQLite'ta tutulduğu için backend yeniden başladığında kaybolmaz. Yüksek ölçekli veya çok instance'lı dağıtımda merkezi Redis tabanlı limiter gerekir.

Şunlara karşı production koruması henüz tam değildir:

- Dağıtık brute-force saldırıları
- Çalınmış cihaz
- Sunucu diskine erişebilen saldırgan
- Zararlı tarayıcı eklentileri
- Veritabanı dosyasının fiziksel kopyalanması
- Gelişmiş operasyonel izleme ve alarm

## Production kontrol listesi

- HTTPS zorunlu kıl — production Caddy katmanında yapılandırıldı; gerçek domain yayını bekliyor
- `PERIOD_TRACKER_SECURE_COOKIE=true` ayarla — production Compose katmanında zorunlu
- CORS origin listesini gerçek domain ile sınırla — `LUNA_DOMAIN` üzerinden ayarlanıyor
- Reverse proxy üzerinde HSTS, CSP, X-Content-Type-Options ve Referrer-Policy ekle — Caddyfile içinde yapılandırıldı
- Dağıtık saldırılar için reverse proxy/merkezi rate limiting ekle
- Audit loglar için saklama süresi ve dış izleme/uyarı politikası belirle
- Parola sıfırlama ve e-posta doğrulama tasarla
- SQLite/veritabanı dosyasını şifreli diskte tut
- Düzenli AES-256-GCM yedek servisi ve kontrollü restore CLI'ı mevcut; production'da off-site kopyayı ve periyodik gerçek restore tatbikatını işlet
- Uygulama loglarına sağlık verisi, parola veya cookie yazma
- Dependency ve güvenlik taramalarını CI'a ekle
- Secret'ları repository'ye koyma

## Kayıp parola

Hesap oluşturulurken 80-bit rastgele bir kurtarma kodu kullanıcıya bir kez gösterilir. Veritabanında kodun yalnızca SHA-256 hash'i saklanır.

- Kullanıcı kodu güvenli bir yerde saklamalıdır.
- Kod kullanılarak parola yenilendiğinde yeni bir kurtarma kodu üretilir.
- Ayarlardan yeni kod oluşturmak eski kodu geçersiz kılar.
- Parola değişikliği veya kurtarma tüm eski session'ları kapatır.
- Parola ve kurtarma kodu birlikte kaybedilirse otomatik hesap kurtarma mümkün değildir.

Production ortamında uygulama limiter'ına ek olarak reverse proxy seviyesinde genel istek limiti önerilir.

## Veritabanı ve yedek

Varsayılan dosya:

```text
backend/data/period_tracker.db
```

Bu dosyanın kopyası tüm kişisel sağlık verilerini içerebilir. Dosya paylaşılmamalı, bulut yedeği kullanılacaksa şifrelenmelidir.

JSON export profil ve regl kayıtlarını içerdiği için aynı hassasiyetle korunmalıdır.

JSON geri yükleme:

- Yalnızca geçerli session ile çalışır.
- Pydantic ile sürüm, alan, tarih aralığı, akış, belirti ve kayıt sayısı doğrulaması yapar.
- Aynı yedekte yinelenen başlangıç tarihlerini reddeder.
- Dışarıdan gelen kayıt kimliklerini kullanmaz.
- Hesap, parola, kurtarma kodu ve session tablolarını değiştirmez.
- Tek transaction kullanır; hata halinde tüm değişiklikleri geri alır.

JSON dosyası şifreli değildir. Paylaşılmamalı; bulut veya taşınabilir diskte saklanacaksa ayrıca şifrelenmelidir.

Tam SQLite yedekleri ayrı `luna-backups` volume'ünde AES-256-GCM ile korunur. Her snapshot SQLite online backup API'siyle alınır; şifrelemeden önce ve geri yüklemede bütünlük/foreign key kontrolü yapılır. Şifre anahtarı yalnız Git-ignored `.env.backup` dosyasından verilir. Bu sistem çalışan `luna-data` volume'ünü şifrelemez ve aynı hosttaki backup volume'ü tek başına felaket kurtarma sayılmaz. Ayrıntılar: [Otomatik şifreli veritabanı yedekleri](ENCRYPTED_BACKUPS.md).

## Güvenlik açığı bildirimi

Bu kişisel proje herkese açık bir güvenlik bildirim kanalı tanımlamaz. Bir sorun bulunursa önce uygulamayı internetten ayır, veritabanını yedekle, aktif session'ları temizle ve düzeltme doğrulanana kadar yeniden yayınlama.
