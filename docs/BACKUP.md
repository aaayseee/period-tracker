# Kullanıcı JSON Yedekleme ve Geri Yükleme

Luna, profil ayarlarını ve regl geçmişini taşınabilir bir JSON dosyasına aktarabilir ve aynı biçimde geri yükleyebilir.

Bu belge kullanıcı bazlı, düz metin JSON akışını açıklar. Sunucudaki tüm hesapları ve veritabanını kapsayan AES-256-GCM korumalı otomatik yedekler için [Otomatik şifreli veritabanı yedekleri](ENCRYPTED_BACKUPS.md) belgesini kullan.

## Yedek alma

Dashboard'daki **Yedekle** düğmesi `luna-yedek-YYYY-MM-DD.json` isimli dosyayı indirir.

Yedekte bulunanlar:

- Profil adı
- Başlangıç ortalama döngü ve regl süreleri
- Regl başlangıç/bitiş tarihleri
- Akış seviyesi, belirtiler ve notlar
- Kayıt zaman damgaları
- `schema_version` ve dışa aktarma zamanı

Yedekte bulunmayanlar:

- Hesap e-postası
- Parola hash'i ve salt
- Kurtarma kodu
- Session cookie veya session kayıtları

## Geri yükleme

1. **Ayarlar → Veri Yönetimi** bölümünü aç.
2. Luna'dan indirilmiş `.json` dosyasını seç.
3. Geri yükleme yöntemini belirle.
4. Uyarıyı okuyup işlemi onayla.

### Tamamen değiştir

Mevcut profil ve regl kayıtları kaldırılır, yedekteki profil ve kayıtlar uygulanır. Bu seçenek yedek alındığı andaki duruma dönmek içindir. Hesap ve giriş bilgileri korunur.

### Kayıtları birleştir

Mevcut profil korunur. Başlangıç tarihi mevcut olmayan yedek kayıtları eklenir; aynı başlangıç tarihine sahip kayıtlar atlanır. İki cihazdan alınmış geçmişleri bir araya getirmek için daha güvenli seçenektir.

## Doğrulama ve atomiklik

- Desteklenen biçim sürümü: `1`
- En fazla dosya boyutu arayüzde: 5 MB
- En fazla regl kaydı: 5000
- Başlangıç/bitiş sırası ve en fazla 15 günlük regl süresi kontrol edilir.
- Akış seviyesi, belirtiler ve not uzunluğu normal API kurallarıyla doğrulanır.
- Aynı yedekte yinelenen başlangıç tarihleri reddedilir.
- Yedekteki `id` değerleri kullanılmaz; yeni yerel kimlikler üretilir.
- Veritabanı yazımı tek transaction içinde yapılır. Bir hata oluşursa hiçbir kısmi değişiklik kalmaz.

## Sürüm uyumluluğu

`schema_version`, gelecekte yedek yapısı değiştiğinde kontrollü dönüşüm yapılabilmesi içindir. İlk sürümde oluşturulan ve bu alanı içermeyen Luna yedekleri sürüm `1` kabul edilir.

Desteklenmeyen daha yeni bir sürüm içe aktarılmaya çalışılırsa API `422 Unprocessable Entity` döndürür.

## Güvenlik

JSON dosyası düz metindir ve sağlık verisi içerir. Dosyayı herkese açık bir repository'ye ekleme, mesajlaşma uygulamalarında paylaşma veya şifrelenmemiş ortak depolamada tutma. Uzun süreli arşiv için şifreli disk ya da şifreli arşiv kullan.

Önemli bir geri yüklemeden önce mevcut durumun yeni bir yedeğini almak geri dönüş noktası sağlar.
