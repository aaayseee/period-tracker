# Docker ile Kurulum

Bu kurulum Luna'yı iki container ile çalıştırır:

- `frontend`: React production build'ini sunan Nginx; hosta açılan tek servis.
- `backend`: FastAPI, migration runner ve SQLite erişimi; yalnız Compose iç ağında.

SQLite dosyası `luna-data` named volume'ünde tutulur. Container yeniden oluşturulsa veya `docker compose down` çalıştırılsa bile veriler korunur.

## Gereksinimler

- Docker Desktop
- Docker Compose v2 veya üzeri
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

Uygulama:

```text
http://localhost:8080
```

Sağlık kontrolü:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

## Container durumları ve loglar

```powershell
docker compose ps
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

Her iki servisin de `healthy` olması beklenir.

## Durdurma ve yeniden başlatma

```powershell
docker compose stop
docker compose start
```

Container'ları kaldırıp veriyi korumak için:

```powershell
docker compose down
```

Uygulama kodunu güncelledikten sonra:

```powershell
docker compose up --build -d
```

Migration'lar backend başlangıcında otomatik çalışır.

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

Normal yedek için uygulamadaki **Yedekle** düğmesini kullan. Docker seviyesinde bakım öncesinde container'ları durdurup volume yedeği almak da mümkündür; JSON yedeği farklı kurulumlara taşımak için daha pratiktir.

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

Gerçek telefon kurulumu için sonraki aşamada HTTPS, gerçek domain ve `PERIOD_TRACKER_SECURE_COOKIE=true` yapılandırılmalıdır.

Hazır production Compose ve Caddy yapılandırmasının kullanımı [HTTPS deployment rehberinde](DEPLOYMENT.md) açıklanır.

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

### Temiz image build

Cache kaynaklı bir problemden şüpheleniliyorsa:

```powershell
docker compose build --no-cache
docker compose up -d
```

Bu işlem named volume'ü silmez.
