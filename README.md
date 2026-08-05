# Luna — Kişisel Döngü Takibi

Luna; store zorunluluğu olmadan tarayıcıdan kullanılabilen, telefona PWA olarak kurulabilen ve davet ettiğin kişilerin ayrı hesaplarla kullanabildiği kendi kendine barındırılan bir döngü takip uygulamasıdır. Her kullanıcının regl kayıtları, belirtileri, kişisel notları ve tahminleri aynı SQLite veritabanında hesap bazında kesin olarak ayrılır.

> Tahminler yalnızca geçmiş tarihlerden üretilen yaklaşık bilgilerdir. Tıbbi tanı veya doğum kontrol yöntemi değildir.

## Proje durumu

Uygulama yerel kullanım için çalışan bir MVP'dir:

- Davet koduyla e-posta/parola hesabı oluşturma ve mevcut hesaba giriş
- Ayrı yönetici hesabı, davet üretme/iptal etme ve kullanıcı etkinleştirme/pasifleştirme paneli
- Sağlık verisi içermeyen, allow-list kontrollü admin audit kayıtları
- Profil, regl, PMS, ovülasyon, yedek ve tahmin verilerinde hesap bazlı veri izolasyonu
- Parola değiştirme ve tek kullanımlık gösterilen kurtarma kodu
- PBKDF2 ile tuzlanmış parola hash'i
- Login, kurtarma ve kayıt uçlarında kalıcı SQLite rate limiting
- 30 günlük, sunucu tarafında doğrulanan HttpOnly oturum
- Regl başlangıç/bitiş tarihi, akış, belirti ve not kaydı
- Tek dokunuşla “Reglim başladı / bitti” akışı
- Profil ayarlarını ve geçmiş kayıtları düzenleme
- Kayıt listeleme, güncelleme ve silme API'leri
- Ortalama döngü ve regl süresi hesabı
- Sonraki regl, yumurtlama ve doğurganlık dönemi tahmini
- Takvimde ayrı ovülasyon günü ve 7 günlük PMS penceresi
- Takvim, geçmiş kayıtlar, JSON yedek alma ve geri yükleme
- Tüm SQLite veritabanı için günlük AES-256-GCM şifreli yedek ve kontrollü geri yükleme
- Sürümlü, transaction destekli SQLite migration sistemi
- Docker Compose ile tek komutluk, kalıcı verili kurulum
- Caddy ile otomatik sertifika yenilemeli HTTPS deployment altyapısı
- Responsive React arayüzü
- Manifest, ikon ve Service Worker içeren PWA kabuğu
- Kullanıcı izinli Web Push, PMS ve yaklaşan regl hatırlatmaları; iPhone kurulu PWA üzerinde gerçek bildirim testi tamamlandı

Üretim ortamına internet üzerinden açılmadan önce yapılması gerekenler [Yol Haritası](docs/ROADMAP.md) belgesinde açıkça listelenmiştir.

## Kullanılan teknolojiler

| Katman | Teknoloji | Sorumluluk |
|---|---|---|
| Frontend | React + TypeScript + Vite | Arayüz, takvim ve API iletişimi |
| UI ikonları | Lucide React | Uygulama ikonografisi |
| Backend | Python + FastAPI | REST API, doğrulama ve oturum yönetimi |
| Veri doğrulama | Pydantic | İstek/yanıt şemaları |
| Veritabanı | SQLite | Profil, hesap, session ve döngü kayıtları |
| Migration | Yerel Python migration runner | Sıralı şema yükseltme, geçmiş ve hata halinde transaction rollback |
| Yedek şifreleme | cryptography + AES-256-GCM | Tam SQLite snapshot gizliliği ve bütünlüğü |
| Container | Docker Compose + Nginx | Production build, reverse proxy ve kalıcı SQLite volume |
| HTTPS edge | Caddy 2 | TLS sertifikası, HTTP yönlendirmesi ve güvenlik header'ları |
| Test | Pytest + FastAPI TestClient | API, auth ve tahmin algoritması testleri |
| PWA | Web App Manifest + Service Worker | Kurulabilir uygulama kabuğu |
| Bildirim | Web Push + VAPID + pywebpush | Hesap/cihaz bazlı PMS ve regl hatırlatmaları |

## Gereksinimler

En kolay kurulum için:

- Docker Desktop ve Docker Compose

Docker kullanmadan geliştirmek için:

- Python 3.9 veya üzeri
- Node.js 20 veya üzeri
- npm
- Windows PowerShell veya uyumlu bir terminal

Sürüm kontrolü:

```powershell
python --version
node --version
npm.cmd --version
```

PowerShell yürütme politikası nedeniyle `npm` komutu engellenirse Windows'ta `npm.cmd` kullan.

## Docker ile tek komutla kurulum

Docker Desktop'ın çalıştığından emin ol, repository kökünde şu komutu çalıştır:

```powershell
docker compose up --build -d
```

Bu temel komut `backend` ve `frontend` servislerini başlatır. Günlük şifreli yedek ve zamanlanmış Web Push için sırasıyla `backups` ve `notifications` profilleri ayrıca etkinleştirilir; anahtar üretimi ve tam komutlar aşağıdaki teknik belgelerdedir.

İlk yönetici hesabını ayrı olarak oluştur. Bu hesap yalnızca kullanıcı ve davet yönetimi içindir; kişisel döngü takibi için kullanılmaz:

```powershell
docker compose exec backend python -m app.admin_cli create
```

Komut e-posta ve parolayı etkileşimli olarak sorar ve kurtarma kodunu yalnızca bir kez gösterir. Ardından `http://localhost:8080` adresinde admin hesabıyla giriş yap, davet kodu üret ve kişisel hesabını bu kodla oluştur. Arkadaşlarına da ayrı davet kodları gönderebilirsin.

Ardından uygulamayı http://localhost:8080 adresinde aç. SQLite verisi `luna-period-tracker_luna-data` named volume'ünde kalıcı tutulur.

```powershell
docker compose ps
docker compose logs -f
docker compose down
```

`docker compose down` container'ları kapatır fakat veriyi korur. **`docker compose down -v` volume'ü ve tüm uygulama verilerini siler.** Ayrıntılı kullanım ve sorun giderme: [Docker kurulumu](docs/DOCKER.md).

Gerçek domain üzerinden HTTPS yayını için `.env.production.example` dosyasını doldurup production Compose katmanını kullan:

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production --env-file .env.backup --profile backups --profile notifications -f compose.yaml -f compose.production.yaml up --build -d
```

Bu komuttan önce `.env.notifications` ve `.env.backup` anahtar dosyaları hazırlanmalıdır. `compose.yaml`, `.env.notifications` dosyasını backend ve scheduler için otomatik yükler. Domain DNS kayıtları ile sunucu/VPS hazırlığı dahil tam süreç: [HTTPS deployment](docs/DEPLOYMENT.md).

Domain veya VPS satın almadan gerçek telefonda beta testi için [Tailscale Funnel rehberini](docs/TAILSCALE_FUNNEL.md) kullan. Bildirim anahtarları, scheduler ve telefon izin akışı [Web Push bildirimleri](docs/NOTIFICATIONS.md) belgesindedir.

## İlk kurulum

Projeyi aç:

```powershell
cd C:\Users\ayseu\Desktop\period-tracker
```

### 1. Backend sanal ortamını oluştur

Sanal ortam Python paketlerini bilgisayardaki diğer projelerden ayırır. Bu adım ilk kurulumda bir kez yapılır:

```powershell
cd backend
python -m venv .venv
```

İki kullanım yöntemi vardır.

#### Önerilen yöntem: aktive etmeden çalıştır

PowerShell izinlerinden etkilenmez:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

#### Alternatif yöntem: sanal ortamı aktive et

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

`Activate.ps1` engellenirse yalnızca açık terminal için izin ver:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Terminal başında `(.venv)` görünmesi ortamın aktif olduğunu gösterir. Çıkmak için:

```powershell
deactivate
```

Backend çalıştığında:

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Sağlık kontrolü: http://127.0.0.1:8000/health

Bekleyen veritabanı migration'ları backend başlangıcında otomatik uygulanır. Manuel durum kontrolü ve yükseltme:

```powershell
cd C:\Users\ayseu\Desktop\period-tracker\backend
.\.venv\Scripts\python.exe -m app.migrations status
.\.venv\Scripts\python.exe -m app.migrations upgrade
```

Yerel geliştirmede ilk yönetici hesabını oluşturmak için backend klasöründe:

```powershell
.\.venv\Scripts\python.exe -m app.admin_cli create
```

Migration çalıştırmadan önce önemli veriler için JSON veya SQLite dosya yedeği almak önerilir. Ayrıntılar: [Veritabanı migration sistemi](docs/MIGRATIONS.md).

### 2. Frontend bağımlılıklarını kur

İkinci bir PowerShell terminali aç:

```powershell
cd C:\Users\ayseu\Desktop\period-tracker\frontend
npm.cmd install
npm.cmd run dev
```

Uygulama http://localhost:5173 adresinde açılır. Vite, `/api` isteklerini otomatik olarak `127.0.0.1:8000` adresine yönlendirir. Uygulamanın çalışması için iki terminal de açık olmalıdır.

## İlk kullanım

1. Admin hesabıyla giriş yap ve **Davet oluştur** bölümünden bir kod üret.
2. Admin hesabından çık. Kişisel takip hesabı admin hesabından ayrı olmalıdır.
3. **İlk kez kullanıyorum** bölümünde isim, e-posta, parola, davet kodu, son regl tarihi ve ortalamaları gir.
4. Gösterilen kurtarma kodunu parola yöneticisi gibi güvenli bir yerde sakla.
5. Daha önce hesap oluşturduysan **Hesabım var** bölümünden giriş yap; parolanı unuttuysan kurtarma kodunu kullan.
6. **Reglim başladı** ile hızlı aktif kayıt aç veya **Yeni kayıt** ile ayrıntıları gir.
7. Arkadaşların için admin panelinden ayrı kodlar üret. Her hesap yalnızca kendi takvimini, tahminlerini ve yedeğini görür.

Oturum varsayılan olarak 30 gün geçerlidir. Süre dolduğunda hesap veya döngü verileri silinmez; yalnızca yeniden giriş gerekir.

## Test ve doğrulama

Backend testleri:

```powershell
cd C:\Users\ayseu\Desktop\period-tracker\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend tip kontrolü ve üretim derlemesi:

```powershell
cd C:\Users\ayseu\Desktop\period-tracker\frontend
npm.cmd run build
```

Üretim çıktısını yerelde önizlemek için:

```powershell
npm.cmd run preview
```

## Yapılandırma

Backend, yedek ve bildirim servislerinin ayarları ortam değişkenleriyle değiştirilebilir:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `PERIOD_TRACKER_DB` | `backend/data/period_tracker.db` | SQLite dosyasının yolu |
| `PERIOD_TRACKER_SESSION_DAYS` | `30` | Session geçerlilik süresi; 1–365 gün |
| `PERIOD_TRACKER_SECURE_COOKIE` | `false` | HTTPS üretiminde `true` olmalı |
| `PERIOD_TRACKER_CORS_ORIGINS` | localhost adresleri | Virgülle ayrılmış izinli frontend origin'leri |
| `PERIOD_TRACKER_LOGIN_ATTEMPTS` | `5` | Login penceresinde izin verilen başarısız deneme |
| `PERIOD_TRACKER_LOGIN_WINDOW_SECONDS` | `900` | Login rate limit penceresi |
| `PERIOD_TRACKER_RECOVERY_ATTEMPTS` | `5` | Kurtarma penceresinde izin verilen başarısız deneme |
| `PERIOD_TRACKER_RECOVERY_WINDOW_SECONDS` | `1800` | Kurtarma rate limit penceresi |
| `PERIOD_TRACKER_REGISTER_ATTEMPTS` | `10` | Kayıt penceresinde izin verilen başarısız deneme |
| `PERIOD_TRACKER_REGISTER_WINDOW_SECONDS` | `3600` | Kayıt rate limit penceresi |
| `PERIOD_TRACKER_BACKUP_INTERVAL_HOURS` | `24` | Şifreli tam yedekler arasındaki süre |
| `PERIOD_TRACKER_BACKUP_RETENTION_DAYS` | `30` | Şifreli yedek saklama süresi |
| `PERIOD_TRACKER_BACKUP_MIN_FILES` | `3` | Her durumda korunacak en yeni yedek sayısı |
| `PERIOD_TRACKER_VAPID_PUBLIC_KEY` | boş | PWA aboneliğinde kullanılan açık VAPID anahtarı |
| `PERIOD_TRACKER_VAPID_PRIVATE_KEY` | boş | Yalnız sunucuda tutulacak VAPID imza anahtarı |
| `PERIOD_TRACKER_VAPID_SUBJECT` | boş | `mailto:` veya HTTPS iletişim URI'si |
| `PERIOD_TRACKER_NOTIFICATION_INTERVAL_SECONDS` | `300` | Bildirim scheduler kontrol aralığı |

PowerShell örneği:

```powershell
$env:PERIOD_TRACKER_SESSION_DAYS = "60"
$env:PERIOD_TRACKER_SECURE_COOKIE = "true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app
```

## Veriler ve yedekleme

Varsayılan veritabanı:

```text
backend/data/period_tracker.db
```

Dashboard'daki **Yedekle** düğmesi profil ve regl kayıtlarını sürüm bilgili JSON dosyası olarak indirir. Geri yüklemek için **Ayarlar → Veri Yönetimi** bölümünden dosyayı seç:

- **Tamamen değiştir:** Mevcut profil ve regl kayıtlarını yedekteki haliyle değiştirir.
- **Kayıtları birleştir:** Mevcut profil ve kayıtları korur, yalnızca eksik başlangıç tarihlerini ekler.

JSON geri yükleme hesap e-postasını, parolayı, kurtarma kodunu ve oturumları değiştirmez. Ayrıntılar: [Kullanıcı JSON yedekleme ve geri yükleme](docs/BACKUP.md).

Sunucunun tamamı için isteğe bağlı `backup` Docker profili, SQLite online backup API'siyle günlük snapshot alır; AES-256-GCM ile şifreler, bütünlüğünü doğrular ve ayrı `luna-backups` volume'ünde saklar. Anahtar Git-ignored `.env.backup` dosyasındadır. Kurulum, off-site kopya ve kontrollü restore adımları: [Otomatik şifreli veritabanı yedekleri](docs/ENCRYPTED_BACKUPS.md).

Admin paneli sağlık verilerini göstermez. Veritabanının tamamına sunucu yöneticisi olarak erişmen gerekirse yerel kurulumda `backend/data/period_tracker.db`, Docker kurulumunda ise `luna-data` named volume kullanılır. Ham SQLite erişimi tüm kullanıcıların hassas verilerine erişim sağladığından yalnızca bakım/yedekleme amacıyla kullanılmalıdır.

## Proje yapısı

```text
period-tracker/
├── backend/
│   ├── app/
│   │   ├── auth.py             # Parola ve session işlemleri
│   │   ├── audit.py            # Güvenli admin hareket kayıtları
│   │   ├── backup_cli.py       # Şifreli snapshot, doğrulama ve restore CLI'ı
│   │   ├── database.py         # SQLite bağlantısı ve migration başlangıcı
│   │   ├── migrations/         # v0001-v0006 sıralı şema yükseltmeleri
│   │   ├── main.py             # FastAPI uygulaması ve endpoint'ler
│   │   ├── notification_cli.py # VAPID anahtarı, scheduler ve sağlık CLI'ı
│   │   ├── notifications.py    # Web Push gönderimi ve teslim tekilleştirme
│   │   ├── rate_limit.py       # Kalıcı auth deneme sınırları
│   │   ├── schemas.py          # Pydantic veri sözleşmeleri
│   │   └── services.py         # Tahmin algoritması ve dönüşümler
│   ├── tests/                  # API, auth, migration, bildirim ve algoritma testleri
│   ├── Dockerfile
│   ├── requirements.txt        # Production bağımlılıkları
│   └── requirements-dev.txt
├── frontend/
│   ├── public/                 # Manifest, Service Worker, offline ekranı ve ikonlar
│   ├── src/                    # React uygulaması, stiller, API ve tipler
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── compose.yaml                # Temel servisler ve isteğe bağlı profiller
├── compose.funnel.yaml         # Tailscale Funnel beta katmanı
├── compose.production.yaml     # Caddy production katmanı
├── deploy/
│   └── Caddyfile
└── docs/
```

## PWA olarak telefona kurma

Yerel geliştirmede `localhost` güvenli bağlam kabul edilir. Gerçek telefondan kurulum için uygulamanın HTTPS üzerinden erişilebilir olması gerekir.

- Android/Chrome: Menü → **Ana ekrana ekle** veya **Uygulamayı yükle**
- iPhone/Safari: Paylaş → **Ana Ekrana Ekle**; kurulum ekranında **Open as Web App** açık

Manifest 192×192, 512×512 ve maskable PNG ikonları; iOS için opak 180×180 Apple touch icon içerir. Service Worker bağlantı yokken özel çevrimdışı ekranını gösterir ve Web Push olaylarını işler. Bildirim izni her cihazda ayrı verilir; tercihler hesap genelinde, abonelikler cihaz bazında tutulur. API verilerini çevrimdışı yazıp sonradan senkronize etmez. Ayrıntılar: [PWA ve çevrimdışı davranış](docs/PWA.md).

## Sorun giderme

### “API bağlantısı kurulamadı”

Backend terminalinin açık olduğunu kontrol et:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Yanıt `{"status":"ok"}` olmalıdır.

### `npm.ps1 cannot be loaded`

```powershell
npm.cmd install
npm.cmd run dev
```

### Port kullanımda

```powershell
netstat -ano | Select-String ":8000|:5173"
```

İlgili eski geliştirme sürecini kapat veya uygulamayı farklı portta çalıştır.

### Veritabanını sıfırlama

`backend/data/period_tracker.db` hesap ve döngü verilerini içerir. Silmek geri alınamaz; önce mutlaka yedekle. Normal geliştirme sırasında veritabanını sıfırlamak gerekmez.

## Teknik belgeler

- [Mimari ve ölçeklenebilirlik](docs/ARCHITECTURE.md)
- [API sözleşmesi](docs/API.md)
- [PWA ve çevrimdışı davranış](docs/PWA.md)
- [Güvenlik modeli](docs/SECURITY.md)
- [Çok kullanıcılı işletim ve admin hesabı](docs/MULTI_USER.md)
- [Kullanıcı JSON yedekleme ve geri yükleme](docs/BACKUP.md)
- [Otomatik şifreli veritabanı yedekleri](docs/ENCRYPTED_BACKUPS.md)
- [Veritabanı migration sistemi](docs/MIGRATIONS.md)
- [Docker kurulumu](docs/DOCKER.md)
- [HTTPS deployment](docs/DEPLOYMENT.md)
- [Tailscale Funnel ile ücretsiz beta paylaşımı](docs/TAILSCALE_FUNNEL.md)
- [Web Push bildirimleri](docs/NOTIFICATIONS.md)
- [Aşama denetimi ve yol haritası](docs/ROADMAP.md)

## Lisans ve kullanım

Bu proje kişisel kullanım için geliştirilmiştir. Sağlıkla ilgili olağandışı veya endişe verici durumlarda bir sağlık profesyoneline başvur.
