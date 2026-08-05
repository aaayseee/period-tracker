# Web Push Bildirimleri

Luna, uygulama kapalıyken de çalışan standart Web Push bildirimlerini destekler. Kullanıcılar bildirimleri kendi hesaplarında ve kendi cihazlarında açıkça etkinleştirir.

## Hatırlatma türleri

- **Yaklaşan regl:** Tahmini regl başlangıcından 0–7 gün önce gönderilir; varsayılan 2 gündür.
- **PMS başlangıcı:** Tahmini PMS penceresinin ilk gününde gönderilir ve tercihlerden kapatılabilir.
- **Test bildirimi:** Kurulumun tamamlandığını anında doğrular.

Bildirim metinleri kilit ekranında kesin tarih, semptom, not veya hesap e-postası göstermez. Tahminlerin tıbbi tanı veya doğum kontrol yöntemi olmadığı uygulama içinde belirtilmeye devam eder.

## Mimari

```text
Ana ekrandaki Luna PWA
        │ kullanıcı izni + PushSubscription
        ▼
FastAPI /api/notifications/*
        │ hesap sahipli abonelik ve tercihler
        ▼
SQLite notification_* tabloları
        ▲
Docker notifications scheduler (5 dakikada bir)
        │ VAPID imzalı Web Push
        ▼
Tarayıcı/işletim sistemi push servisi → Service Worker → Bildirim
```

Scheduler her kullanıcının IANA saat dilimini ve seçtiği yerel saati kullanır. Aynı hatırlatma `notification_deliveries` benzersiz anahtarı sayesinde yalnızca bir kez gönderilir. Süresi dolmuş push abonelikleri 404/410 yanıtında otomatik temizlenir.

## VAPID anahtarlarını oluşturma

Anahtarlar bir kurulumda yalnızca bir kez üretilmelidir. `mailto:` adresi Luna giriş hesabı olmak zorunda değildir; push sağlayıcılarının gerektiğinde kurulum sahibiyle iletişim kurabilmesi için erişebildiğin gerçek bir adres kullanılması önerilir.

Windows PowerShell:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.notification_cli init-env `
  --output ..\.env.notifications `
  --subject mailto:sen@example.com
cd ..
```

Linux/macOS veya production VPS:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.notification_cli init-env \
  --output ../.env.notifications \
  --subject mailto:sen@example.com
cd ..
```

`.env.notifications` Git tarafından yok sayılır ve şunları içerir:

- `PERIOD_TRACKER_VAPID_PRIVATE_KEY`: Sunucudan dışarı çıkarılmaması gereken imza anahtarı
- `PERIOD_TRACKER_VAPID_PUBLIC_KEY`: PWA aboneliği oluştururken tarayıcıya verilen açık anahtar
- `PERIOD_TRACKER_VAPID_SUBJECT`: Push sağlayıcıları için `mailto:` veya HTTPS iletişim URI'si
- `PERIOD_TRACKER_NOTIFICATION_INTERVAL_SECONDS`: Scheduler kontrol aralığı; varsayılan 300 saniye

Özel anahtarı kaybetmek mevcut cihaz aboneliklerini geçersiz hale getirir. Dosyayı parola yöneticisi veya şifreli yedekle güvenli biçimde sakla; repository'ye commit etme.

## Docker ile çalıştırma

`compose.yaml`, kökte mevcutsa `.env.notifications` dosyasını backend ve bildirim zamanlayıcısı için otomatik yükler. Normal yeniden oluşturmalarda ayrıca `--env-file .env.notifications` yazmak gerekmez.

Yerel/beta kurulumunda:

```powershell
docker compose `
  --env-file .env.backup `
  --profile backups `
  --profile notifications `
  -f compose.yaml `
  -f compose.funnel.yaml `
  up --build -d
```

Production Caddy katmanında bildirim zamanlayıcısını açmak için `--profile notifications` seçeneği eklenir; aynı `.env.notifications` dosyası otomatik yüklenir.

Kontroller:

```powershell
docker compose --profile notifications ps
docker compose --profile notifications logs notifications
docker compose --profile notifications exec notifications `
  python -m app.notification_cli send-once
```

## Telefonda etkinleştirme

1. Luna'yı HTTPS adresinden ana ekrana kur.
2. Luna'yı tarayıcı sekmesinden değil ana ekran ikonundan aç.
3. Kişisel hesapla giriş yap.
4. **Ayarlar → Hatırlatıcılar → Bu cihazda bildirimleri aç** düğmesine bas.
5. İşletim sisteminin izin penceresinde **İzin Ver** seç.
6. Luna otomatik test bildirimi gönderir.
7. Regl hatırlatma günü, PMS seçimi ve bildirim saatini kaydet.

iPhone/iPad Web Push için iOS/iPadOS 16.4 veya üzeri ve ana ekrana kurulmuş web uygulaması gerekir. İzin isteği yalnız kullanıcının doğrudan düğmeye basmasıyla gösterilebilir. Apple Developer hesabı gerekmez.

Aynı hesap birden fazla telefonda kullanılabilir. Bildirim izni ve `push_subscriptions` satırı cihaz bazındadır; bir cihazdaki **Bu cihazdaki bildirimleri kapat** işlemi diğer cihaz aboneliklerini silmez. Hatırlatma saati, PMS seçimi ve kaç gün önce uyarılacağı hesap genelindedir.

iPhone ana ekran PWA kurulumu, izin akışı ve gerçek test bildirimi Tailscale Funnel HTTPS adresinde başarıyla doğrulandı. Android Chrome aynı standart Web Push akışını kullanır; uygulama kurulup her Android cihazda izin ayrıca verilmelidir. Android için fiziksel cihaz testi ayrıca önerilir.

## API

Tüm uçlar yalnız `user` rolündeki oturumlara açıktır:

- `GET /api/notifications/config`
- `PUT /api/notifications/preferences`
- `POST /api/notifications/subscriptions`
- `POST /api/notifications/unsubscribe`
- `POST /api/notifications/test`

Cihaz endpoint'i ile `p256dh`/`auth` abonelik anahtarları hesapla ilişkilendirilerek SQLite'ta saklanır. Kurulum geneli VAPID özel anahtarı yalnız `.env.notifications` dosyasındadır; veritabanına yazılmaz ve admin panelinde gösterilmez. Admin paneli cihaz aboneliklerini veya sağlık verilerini göstermez.

## Sorun giderme

### Bildirim düğmesi görünmüyor veya desteklenmiyor

- Uygulamayı `https://...` adresinden aç.
- iPhone'da Luna'yı ana ekrana eklediğini ve ikonundan açtığını doğrula.
- Uygulamayı ana ekrandan silip yeniden kurduysan bu cihazda bildirimleri tekrar etkinleştir.
- PWA'yı tamamen kapatıp yeniden açarak güncel Service Worker'ın yüklenmesini sağla.

### İzin daha önce reddedildi

iPhone'da **Ayarlar → Bildirimler → Luna**, Android'de **Ayarlar → Uygulamalar → Luna → Bildirimler** yolundan izni aç. Tarayıcı izin durumunu kodla zorla değiştirmek mümkün değildir.

### Test bildirimi gönderilmiyor

```powershell
docker compose --profile notifications ps
docker compose --profile notifications logs --tail 100 notifications backend
```

Backend ve notifications servisleri `healthy` olmalı. Bilgisayar, Docker Desktop, Tailscale ve Funnel çalışır durumda olmalıdır.

### Bilgisayar kapalı veya uykudaysa

Scheduler çalışamayacağı için hatırlatma gönderilmez. Mevcut beta mimarisinde kaçırılan gün için geriye dönük bildirim gönderilmez. Gerçek 7/24 hatırlatmalar için backend ve scheduler sürekli açık bir sunucuya taşınmalıdır.
