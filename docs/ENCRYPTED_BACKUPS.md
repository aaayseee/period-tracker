# Otomatik Şifreli Veritabanı Yedekleri

Bu sistem, Luna'nın **tüm SQLite veritabanını** düzenli aralıklarla tutarlı bir snapshot olarak alır ve ayrı bir Docker volume'ünde şifreli biçimde saklar. Hesaplar, parola hash'leri, davetler, oturumlar, audit kayıtları, profiller ve sağlık verileri bu tam yedeğe dahildir.

Uygulama içindeki kullanıcı bazlı JSON dışa aktarma ile bu sistem farklı amaçlara hizmet eder:

- JSON yedeği bir kullanıcının profil ve regl geçmişini taşıması içindir; düz metindir.
- Şifreli SQLite yedeği sunucunun tamamını arıza, yanlış işlem veya disk kaybı sonrasında geri döndürmek içindir.

## Güvenlik ve dosya biçimi

- 256 bit rastgele anahtar ve AES-256-GCM kullanılır.
- Her dosya için ayrı 12 byte nonce üretilir.
- GCM etiketi hem gizlilik hem bütünlük sağlar. Yanlış anahtar veya değiştirilmiş dosya açılmaz.
- SQLite snapshot'ı, veritabanı çalışırken SQLite online backup API'siyle alınır.
- Snapshot şifrelenmeden önce, geri yüklenen dosya da yazılmadan önce `integrity_check` ve `foreign_key_check` ile doğrulanır.
- Yazım geçici dosyaya yapılır ve atomik ad değiştirme ile tamamlanır; yarım dosya geçerli yedek adına dönüşmez.
- Şifreli dosyalar `luna-...Z.luna-backup` adını kullanır. Dosya adı yalnızca UTC oluşturulma zamanını açık eder.

Şifreleme anahtarı repository'de, SQLite volume'ünde veya yedek volume'ünde tutulmaz. `.env.backup` Git tarafından yok sayılır.

> `.env.backup` kaybolursa yedekleri kurtarmanın arka kapısı yoktur. Dosyanın ayrı bir kopyasını parola yöneticisinde sakla. Anahtar ile şifreli yedekleri mümkünse aynı yerde tutma.

## Varsayılan politika

| Ayar | Varsayılan | Açıklama |
|---|---:|---|
| `PERIOD_TRACKER_BACKUP_INTERVAL_HOURS` | `24` | Yedekler arasındaki saat |
| `PERIOD_TRACKER_BACKUP_RETENTION_DAYS` | `30` | Bu yaştan eski dosyalar temizlenebilir |
| `PERIOD_TRACKER_BACKUP_MIN_FILES` | `3` | Yaşı ne olursa olsun korunacak en yeni dosya sayısı |

Servis başladığında ilk yedeği hemen alır; ilk 24 saatin dolmasını beklemez. Sonra zamanlamaya geçer. Temizleme, yeni ve doğrulanmış yedek oluşturulduktan sonra çalışır.

## Docker ile ilk kurulum

Komutları repository kökünde PowerShell terminalinde çalıştır.

### 1. Backup image'ını hazırla

```powershell
docker compose --profile backups build backup
```

### 2. Anahtar dosyasını üret

Bu komut anahtarı terminale yazdırmadan kökte `.env.backup` oluşturur ve mevcut dosyanın üzerine yazmayı reddeder:

```powershell
docker compose --profile backups run --rm --no-deps -v "${PWD}:/workspace" backup python -m app.backup_cli init-env --path /workspace/.env.backup
```

`.env.backup` dosyasının güvenli bir kopyasını parola yöneticine koy. Dosya içeriğini sohbet, ekran görüntüsü, Git commit'i veya ortak depolama üzerinden paylaşma.

### 3. Günlük servisi başlat

```powershell
docker compose --env-file .env.backup --profile backups up --build -d backup
```

Ana uygulama container'larını kapatmak gerekmez. `backup` servisi `luna-data` volume'ünü salt-okunur bağlar ve SQLite'ın online backup API'sini kullanır.

Durum ve log kontrolü:

```powershell
docker compose --env-file .env.backup --profile backups ps
docker compose --env-file .env.backup --profile backups logs --tail 50 backup
```

İlk işlemden sonra `backup` servisinin `healthy` olması beklenir.

## Günlük kullanım ve doğrulama

Şifreli yedekleri listele:

```powershell
docker compose --env-file .env.backup --profile backups exec backup python -m app.backup_cli list
```

Beklemeden yeni bir yedek oluştur:

```powershell
docker compose --env-file .env.backup --profile backups exec backup python -m app.backup_cli create
```

Listeden aldığın gerçek dosya adını kullanarak belirli bir yedeği şifre çözme, GCM doğrulaması ve SQLite kontrollerinden geçir:

```powershell
docker compose --env-file .env.backup --profile backups exec backup python -m app.backup_cli verify /app/backups/luna-YYYYMMDDTHHMMSS.ffffffZ.luna-backup
```

Sağlık kontrolü en yeni yedeğin iki zamanlama aralığı + 1 saatten genç olmasını, doğru anahtarla açılmasını ve geçerli SQLite olmasını ister.

## Başka diske veya buluta kopyalama

`luna-backups` named volume'ü uygulama verisinden ayrıdır ama varsayılan olarak aynı Docker hostunda bulunur. Bilgisayar veya sunucu diski tamamen kaybolursa iki volume de kaybolabilir. Bu nedenle şifreli dosyaları düzenli olarak başka bir fiziksel diske veya güvenilir bulut depolamaya kopyala.

Çalışan backup container'ından kökteki Git-ignored `backups/` klasörüne kopyalama:

```powershell
New-Item -ItemType Directory -Force backups
docker compose --env-file .env.backup --profile backups cp backup:/app/backups/. ./backups/
```

Bu dosyalar şifrelidir; yine de silinmeye ve fidye yazılımına karşı sürümlü/immutable depolama tercih edilir. `.env.backup` anahtarının ayrı kopyası parola yöneticisinde tutulmalıdır.

## Kontrollü geri yükleme

Geri yükleme tüm hesap ve sağlık verilerini seçilen zamana döndürür. Önce dosyayı doğrula, ardından uygulama ve backup servislerini durdur.

### 1. Dosyayı doğrula

```powershell
docker compose --env-file .env.backup --profile backups exec backup python -m app.backup_cli verify /app/backups/GERCEK_DOSYA_ADI.luna-backup
```

### 2. Yazma yapan servisleri durdur

```powershell
docker compose --env-file .env.backup --profile backups stop frontend backend backup
```

### 3. Recovery profilini tek seferlik çalıştır

```powershell
docker compose --env-file .env.backup --profile recovery run --rm recovery python -m app.backup_cli restore /app/backups/GERCEK_DOSYA_ADI.luna-backup --output /app/data/period_tracker.db --replace
```

`--replace` zorunlu ve bilinçli onaydır. Komut şunları sırasıyla yapar:

1. Yedeğin GCM kimlik doğrulamasını yapar.
2. SQLite bütünlük ve foreign key kontrollerini çalıştırır.
3. Mevcut veritabanını aynı volume içinde `period_tracker.pre-restore-...db` adıyla korur.
4. Yeni dosyayı geçici hedef üzerinden atomik olarak yerleştirir.
5. Yerleştirilen dosyayı yeniden doğrular.

### 4. Uygulamayı yeniden başlat ve kontrol et

```powershell
docker compose --env-file .env.backup --profile backups up -d backend frontend backup
docker compose --env-file .env.backup --profile backups ps
Invoke-RestMethod http://localhost:8080/health
```

Admin ve kişisel hesabınla giriş yaparak beklenen kayıtların tarihini kontrol et. Doğrulama tamamlanmadan `period_tracker.pre-restore-...db` güvenlik kopyasını silme.

## Yerel venv ile kullanım

Docker kullanmıyorsan backend bağımlılıklarını kurduktan sonra repository kökünden:

```powershell
$env:PYTHONPATH = "backend"
backend\.venv\Scripts\python.exe -m app.backup_cli init-env --path .env.backup
$env:PERIOD_TRACKER_BACKUP_KEY = (Get-Content .env.backup).Split("=", 2)[1].Trim()
$env:PERIOD_TRACKER_DB = "backend/data/period_tracker.db"
$env:PERIOD_TRACKER_BACKUP_DIR = "backups"
backend\.venv\Scripts\python.exe -m app.backup_cli create
backend\.venv\Scripts\python.exe -m app.backup_cli list
```

Bu PowerShell oturumunu kapattığında ortam değişkeni kaybolur. Anahtarın terminal geçmişine yazılmaması için değeri elle komuta ekleme.

## Anahtar kaybı, sızıntısı ve rotasyonu

- **Anahtar kaybı:** Eski yedekler geri döndürülemez. Yeni anahtar oluşturmak eski dosyaları açmaz.
- **Anahtar sızıntısı:** Anahtar ile erişilebilen tüm yedekleri etkilenmiş kabul et. Yeni anahtar üret, yeni yedek al ve eski yedekleri güvenli politikana göre kaldır. Eski yedekler gerektiği sürece eski anahtarı da ayrı ve açıkça etiketlenmiş biçimde koru.
- **Normal rotasyon:** Yeni `.env.backup` dosyasına geçmeden önce en az bir eski yedeğin eski anahtarla doğrulandığını ve iki anahtarın hangi dönemlere ait olduğunun kaydedildiğini kontrol et.

## Sınırlamalar

- Bu özellik çalışan veritabanı dosyasını şifrelemez; yalnızca oluşturulan yedekleri şifreler. Host diski için BitLocker/LUKS gibi disk şifreleme ayrıca kullanılmalıdır.
- Backup volume tek başına off-site yedek değildir.
- Restore testi gerçek verinin üzerine yapılmadan önce ayrı bir staging kopyasında denenebilir.
- Anahtar yönetimi şu anda harici KMS/HSM kullanmaz; küçük, kendi kendine barındırılan kurulum için dosya + parola yöneticisi modelidir.
