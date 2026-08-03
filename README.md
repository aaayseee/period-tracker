# Luna — Kişisel Döngü Takibi

Luna; store zorunluluğu olmadan tarayıcıdan kullanılabilen ve telefona PWA olarak kurulabilen, tek kişilik döngü takip uygulamasıdır. Regl kayıtları, belirtiler, kişisel notlar ve hesap bilgileri kendi SQLite veritabanında tutulur.

> Tahminler yalnızca geçmiş tarihlerden üretilen yaklaşık bilgilerdir. Tıbbi tanı veya doğum kontrol yöntemi değildir.

## Proje durumu

Uygulama yerel kullanım için çalışan bir MVP'dir:

- E-posta/parola ile hesap oluşturma ve giriş
- Parola değiştirme ve tek kullanımlık gösterilen kurtarma kodu
- PBKDF2 ile tuzlanmış parola hash'i
- 30 günlük, sunucu tarafında doğrulanan HttpOnly oturum
- Regl başlangıç/bitiş tarihi, akış, belirti ve not kaydı
- Tek dokunuşla “Reglim başladı / bitti” akışı
- Profil ayarlarını ve geçmiş kayıtları düzenleme
- Kayıt listeleme, güncelleme ve silme API'leri
- Ortalama döngü ve regl süresi hesabı
- Sonraki regl, yumurtlama ve doğurganlık dönemi tahmini
- Takvimde ayrı ovülasyon günü ve 7 günlük PMS penceresi
- Takvim, geçmiş kayıtlar, JSON yedek alma ve geri yükleme
- Sürümlü, transaction destekli SQLite migration sistemi
- Docker Compose ile tek komutluk, kalıcı verili kurulum
- Caddy ile otomatik sertifika yenilemeli HTTPS deployment altyapısı
- Responsive React arayüzü
- Manifest, ikon ve Service Worker içeren PWA kabuğu

Üretim ortamına internet üzerinden açılmadan önce yapılması gerekenler [Yol Haritası](docs/ROADMAP.md) belgesinde açıkça listelenmiştir.

## Kullanılan teknolojiler

| Katman | Teknoloji | Sorumluluk |
|---|---|---|
| Frontend | React + TypeScript + Vite | Arayüz, takvim ve API iletişimi |
| UI ikonları | Lucide React | Uygulama ikonografisi |
| Backend | Python + FastAPI | REST API, doğrulama ve oturum yönetimi |
| Veri doğrulama | Pydantic | İstek/yanıt şemaları |
| Veritabanı | SQLite | Profil, hesap, session ve döngü kayıtları |
| Migration | Yerel Python migration runner | Sıralı şema yükseltme, geçmiş ve rollback |
| Container | Docker Compose + Nginx | Production build, reverse proxy ve kalıcı SQLite volume |
| HTTPS edge | Caddy 2 | TLS sertifikası, HTTP yönlendirmesi ve güvenlik header'ları |
| Test | Pytest + FastAPI TestClient | API, auth ve tahmin algoritması testleri |
| PWA | Web App Manifest + Service Worker | Kurulabilir uygulama kabuğu |

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
docker compose --env-file .env.production -f compose.yaml -f compose.production.yaml up --build -d
```

Domain DNS kayıtları ile sunucu/VPS hazırlığı dahil tam süreç: [HTTPS deployment](docs/DEPLOYMENT.md).

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

1. http://localhost:5173 adresini aç.
2. Yeni kullanıcıysan **İlk kez kullanıyorum** bölümünü seç.
3. İsim, e-posta, en az 8 karakterlik parola, son regl tarihi ve ortalamaları gir.
4. Gösterilen kurtarma kodunu parola yöneticisi gibi güvenli bir yerde sakla.
5. Daha önce hesap oluşturduysan **Hesabım var** bölümünden giriş yap; parolanı unuttuysan kurtarma kodunu kullan.
6. **Reglim başladı** ile hızlı aktif kayıt aç veya **Yeni kayıt** ile ayrıntıları gir.
7. Geçmiş kayıtlardaki kalem ikonuyla düzenleme yap; **Ayarlar** bölümünden profil, parola ve kurtarma kodunu yönet.

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

Backend ayarları ortam değişkenleriyle değiştirilebilir:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `PERIOD_TRACKER_DB` | `backend/data/period_tracker.db` | SQLite dosyasının yolu |
| `PERIOD_TRACKER_SESSION_DAYS` | `30` | Session geçerlilik süresi; 1–365 gün |
| `PERIOD_TRACKER_SECURE_COOKIE` | `false` | HTTPS üretiminde `true` olmalı |
| `PERIOD_TRACKER_CORS_ORIGINS` | localhost adresleri | Virgülle ayrılmış izinli frontend origin'leri |

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

Geri yükleme hesap e-postasını, parolayı, kurtarma kodunu ve oturumları değiştirmez. SQLite dosyasını doğrudan kopyalamadan önce backend'i durdurmak güvenli bir yedek alınmasını sağlar. Ayrıntılar: [JSON yedekleme ve geri yükleme](docs/BACKUP.md).

## Proje yapısı

```text
period-tracker/
├── backend/
│   ├── app/
│   │   ├── auth.py        # Parola ve session işlemleri
│   │   ├── database.py    # SQLite bağlantısı ve şema kurulumu
│   │   ├── main.py        # FastAPI uygulaması ve endpoint'ler
│   │   ├── schemas.py     # Pydantic veri sözleşmeleri
│   │   └── services.py    # Tahmin algoritması ve dönüşümler
│   ├── tests/             # API, auth ve algoritma testleri
│   ├── Dockerfile
│   ├── requirements.txt   # Production bağımlılıkları
│   └── requirements-dev.txt
├── frontend/
│   ├── public/            # Manifest, Service Worker ve ikon
│   ├── src/               # React uygulaması, stiller, API ve tipler
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── compose.yaml
├── compose.production.yaml
├── deploy/
│   └── Caddyfile
└── docs/
```

## PWA olarak telefona kurma

Yerel geliştirmede `localhost` güvenli bağlam kabul edilir. Gerçek telefondan kurulum için uygulamanın HTTPS üzerinden erişilebilir olması gerekir.

- Android/Chrome: Menü → **Ana ekrana ekle** veya **Uygulamayı yükle**
- iPhone/Safari: Paylaş → **Ana Ekrana Ekle**

Mevcut Service Worker uygulama kabuğunu önbelleğe alır; API verilerini çevrimdışı yazıp sonradan senkronize etmez. Ayrıntılar: [PWA ve çevrimdışı davranış](docs/PWA.md).

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
- [JSON yedekleme ve geri yükleme](docs/BACKUP.md)
- [Veritabanı migration sistemi](docs/MIGRATIONS.md)
- [Docker kurulumu](docs/DOCKER.md)
- [HTTPS deployment](docs/DEPLOYMENT.md)
- [Aşama denetimi ve yol haritası](docs/ROADMAP.md)

## Lisans ve kullanım

Bu proje kişisel kullanım için geliştirilmiştir. Sağlıkla ilgili olağandışı veya endişe verici durumlarda bir sağlık profesyoneline başvur.
