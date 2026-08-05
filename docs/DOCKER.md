# Docker ile Kurulum

Bu kurulum Luna'yı iki temel servis ve üç isteğe bağlı profille çalıştırır:

- `frontend`: React production build'ini sunan Nginx; hosta açılan tek servis.
- `backend`: FastAPI, migration runner, SQLite ve bildirim API'leri; yalnız Compose iç ağında.
- `backup`: yalnız `backups` profiliyle başlayan, günlük AES-256-GCM şifreli SQLite snapshot servisi.
- `notifications`: yalnız `notifications` profiliyle başlayan Web Push zamanlayıcısı.
- `recovery`: yalnız kontrollü tam veritabanı geri yüklemede kullanılan tek seferlik araç servisi.

SQLite dosyası `luna-data` named volume'ünde tutulur. Container yeniden oluşturulsa veya `docker compose down` çalıştırılsa bile veriler korunur.

## Gereksinimler

- Docker Desktop
- `env_file.required` desteği bulunan güncel Docker Compose (bu kurulum 5.1.1 ile doğrulandı)
- İlk image build'i için internet bağlantısı

Kontrol:

```powershell
docker --version
docker compose version
docker info
```

`docker info` hata veriyorsa Docker Desktop motoru henüz çalışmıyordur.

## İlk çalıştırma

Repository kökünde:

```powershell
docker compose up --build -d
```

Tek komut şunları yapar:

1. Python runtime image'ını ve yalnız production bağımlılıklarını kurar.
2. React'i Node build aşamasında derler.
3. Derlenmiş dosyaları küçük Nginx image'ına kopyalar.
4. Kalıcı SQLite volume'ünü oluşturur.
5. Backend'i başlatır ve bekleyen migration'ları uygular.
6. Backend healthcheck başarılı olduğunda frontend'i başlatır.

Bu komut yalnız temel ackend ve rontend servislerini açar; profile bağlı servisler aşağıdaki komutlarla etkinleştirilir.

Uygulama:

```text
http://localhost:8080
```

Sağlık kontrolü:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

## İsteğe bağlı profiller

### Şifreli yedek

`.env.backup` oluşturulduktan sonra:

```powershell
docker compose --env-file .env.backup --profile backups up --build -d backup
```

Ayrıntılar: [Otomatik şifreli veritabanı yedekleri](ENCRYPTED_BACKUPS.md).

### Web Push zamanlayıcısı

`.env.notifications` oluşturulduktan sonra:

```powershell
docker compose --profile notifications up --build -d backend frontend notifications
```

`compose.yaml`, varsa kökteki `.env.notifications` dosyasını hem backend hem scheduler container'ına otomatik yükler. `--env-file .env.notifications` yazmak gerekmez. Anahtar üretimi ve telefon testi: [Web Push bildirimleri](NOTIFICATIONS.md).

### Tam geri yükleme aracı

`recovery` sürekli çalışan bir servis değildir. Yalnız doğrulanmış `.luna-backup` dosyasını geri yüklerken [şifreli yedek rehberindeki](ENCRYPTED_BACKUPS.md) kontrollü komutla çalıştırılır.

## Container durumları ve loglar

```powershell
docker compose ps
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

Temel kurulumda `frontend` ve `backend` servislerinin `healthy` olması beklenir. Etkinleştirildiyse `backup` ve `notifications` servisleri de `healthy` olmalıdır; tek seferlik `recovery` normal durumda çalışmaz.

## Durdurma ve yeniden başlatma

```powershell
docker compose stop
docker compose start
```

Container'ları kaldırıp veriyi korumak için:

```powershell
docker compose down
```

Uygulama kodunu güncelledikten sonra yalnız temel servisler için:

```powershell
docker compose up --build -d
```

Yedek ve bildirim profilleri de kullanılıyorsa ilgili anahtar dosyaları hazırken:

```powershell
docker compose --env-file .env.backup --profile backups --profile notifications up --build -d
```

Migration'lar backend başlangıcında otomatik çalışır. Bildirim anahtarları `.env.notifications` üzerinden yeniden yüklenir.

## Veri kalıcılığı

Compose volume adı:

```text
luna-period-tracker_luna-data
```

Kontrol:

```powershell
docker volume inspect luna-period-tracker_luna-data
```

Veritabanı container içinde:

```text
/app/data/period_tracker.db
```

Önemli uyarı:

```powershell
docker compose down -v
```

`-v` seçeneği named volume'ü ve içindeki SQLite verisini siler. Bu komutu yalnızca verileri bilinçli olarak tamamen sıfırlamak istediğinde kullan.

Kullanıcı bazlı taşınabilir yedek için uygulamadaki **Yedekle** düğmesini kullan. Tüm sunucuyu kapsayan otomatik, şifreli ve doğrulanmış yedek servisi için [şifreli yedek rehberini](ENCRYPTED_BACKUPS.md) izle. Veritabanı `luna-data`, şifreli dosyalar ayrı `luna-backups` named volume'ünde tutulur.

## Portu değiştirme

Kökte `.env.example` dosyasını `.env` olarak kopyala:

```powershell
Copy-Item .env.example .env
```

`.env`:

```dotenv
LUNA_PORT=8090
PERIOD_TRACKER_SESSION_DAYS=30
PERIOD_TRACKER_SECURE_COOKIE=false
```

Yeniden başlat:

```powershell
docker compose up -d
```

Uygulama artık `http://localhost:8090` adresindedir.

## Migration komutları

```powershell
docker compose exec backend python -m app.migrations status
docker compose exec backend python -m app.migrations upgrade
```

Normalde manuel `upgrade` gerekmez; backend bunu başlangıçta yapar.

## Image güvenlik özellikleri

- Backend root olmayan `luna` kullanıcısıyla çalışır.
- Backend portu hosta publish edilmez.
- Yalnız runtime Python paketleri production image'ına kurulur.
- Frontend multi-stage build kullanır; Node ve kaynak kod production Nginx katmanına taşınmaz.
- Nginx temel güvenlik header'larını ekler.
- API ve frontend aynı origin üzerinden sunulduğu için session cookie akışı korunur.

## Yerel HTTP ve PWA sınırı

Bu Compose kurulumu yerelde HTTP kullanır. `localhost` tarayıcılar tarafından güvenli bağlam kabul edildiği için masaüstünde PWA geliştirme/testi yapılabilir. Başka bir telefondan IP adresiyle erişim gerçek PWA kurulumu ve güvenli cookie için yeterli değildir.

Gerçek telefon kurulumu için HTTPS ve `PERIOD_TRACKER_SECURE_COOKIE=true` gerekir. Domain/VPS olmadan beta kullanımında [Tailscale Funnel](TAILSCALE_FUNNEL.md), kalıcı yayın için production Compose ve [Caddy deployment](DEPLOYMENT.md) kullanılır.

## Sorun giderme

### Docker API bağlantı hatası

```text
failed to connect to the docker API
```

Docker Desktop'ı aç, motor tamamen başlayana kadar bekle ve `docker info` çalıştır.

### Port kullanımda

`.env` dosyasında `LUNA_PORT` değerini değiştir veya mevcut 8080 portunu kullanan uygulamayı kapat.

### Backend unhealthy

```powershell
docker compose logs backend
docker compose run --rm backend python -m app.migrations status
```

Migration hatası varsa veritabanını silme; önce logu ve [migration belgesini](MIGRATIONS.md) incele.

### “Bildirim servisi sunucuda henüz yapılandırılmadı”

```powershell
docker compose --profile notifications exec backend python -c "from app.notifications import notifications_configured; print(notifications_configured())"
docker compose --profile notifications logs --tail 100 backend notifications
```

İlk komut `True` yazmalıdır. Değilse kökte `.env.notifications` bulunduğunu doğrula ve servisleri yeniden oluştur:

```powershell
docker compose --profile notifications up -d --force-recreate backend notifications
```

### Temiz image build

Cache kaynaklı bir problemden şüpheleniliyorsa:

```powershell
docker compose build --no-cache
docker compose up -d
```

Bu işlem named volume'ü silmez.
