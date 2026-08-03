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

- Tek kullanıcı
- Kişisel bilgisayar veya kontrol edilen sunucu
- Güvenilir yerel ağ ya da HTTPS
- Düşük istek hacmi

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
- Login rate limiting ve geçici hesap kilidi ekle
- Parola sıfırlama ve e-posta doğrulama tasarla
- SQLite/veritabanı dosyasını şifreli diskte tut
- Düzenli şifreli yedek al ve geri yüklemeyi test et
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

Production ortamında kurtarma endpoint'i için rate limiting zorunludur.

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

## Güvenlik açığı bildirimi

Bu kişisel proje herkese açık bir güvenlik bildirim kanalı tanımlamaz. Bir sorun bulunursa önce uygulamayı internetten ayır, veritabanını yedekle, aktif session'ları temizle ve düzeltme doğrulanana kadar yeniden yayınlama.
