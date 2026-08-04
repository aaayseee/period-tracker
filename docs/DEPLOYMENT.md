# HTTPS Deployment

Luna'nın production deployment katmanı Docker Compose, Nginx ve Caddy kullanır. Caddy dış dünyaya açılan tek servistir; TLS sertifikasını otomatik alır/yeniler ve HTTP isteklerini HTTPS'e yönlendirir.

## Mimari

```text
Telefon / tarayıcı
        │
        │ HTTPS :443
        ▼
      Caddy
        │ Compose iç ağı / HTTP
        ▼
      Nginx
       ├── React PWA
       └── /api → FastAPI → SQLite volume
```

Hosta açık production portları:

- `80/tcp`: ACME doğrulaması ve HTTPS yönlendirmesi
- `443/tcp`: HTTPS
- `443/udp`: HTTP/3
- `22/tcp`: Yalnız sunucu yönetimi için SSH

FastAPI hosta publish edilmez. Nginx tanılama portu yalnız `127.0.0.1:8080` üzerinde kalır.

## Gerekli bilgiler

Gerçek yayına geçmeden önce şunlar gerekir:

1. Bir domain veya kullanabileceğin subdomain
2. Public IPv4 adresli Linux VPS/sunucu
3. Sunucuya SSH erişimi
4. DNS yönetim paneline erişim
5. Sunucuda Docker Engine ve Docker Compose

İnternete açık sunucuda Docker'ı dağıtımın resmi `apt` repository'sinden kur. Docker'ın yayınlanan container portlarının bazı firewall kurallarını atlayabildiğini unutma; yalnız Compose dosyasında bilinçli olarak publish edilen 80/443 ve localhost tanılama portu kullanılmalıdır.

Ev internetindeki bilgisayara yayın yapılacaksa CGNAT, değişken IP ve router port yönlendirmesi sorunları olabilir. Kişisel sağlık verisi için güncel ve yalnız bu işe ayrılmış küçük bir VPS daha öngörülebilir seçenektir.

## DNS hazırlığı

Örnek domain:

```text
luna.example.com
```

DNS panelinde:

- `A` kaydı → VPS'in public IPv4 adresi
- IPv6 gerçekten yapılandırıldıysa `AAAA` kaydı → VPS IPv6 adresi

Yanlış bir `AAAA` kaydı sertifika ve erişim sorunlarına yol açabilir; IPv6 hazır değilse ekleme.

PowerShell ile kontrol:

```powershell
Resolve-DnsName luna.example.com -Type A
Resolve-DnsName luna.example.com -Type AAAA
```

DNS sonucu VPS adresini göstermeden Caddy'yi production domain ile başlatma.

## Sunucu güvenlik hazırlığı

Ubuntu/Debian örneğinde firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
sudo ufw status
```

SSH anahtar tabanlı giriş kullan; parola ile root girişini kapat. İşletim sistemi ve Docker güvenlik güncellemelerini düzenli uygula.

## Repository ve ortam dosyası

Sunucuda repository'yi klonla:

```bash
git clone <repository-url> period-tracker
cd period-tracker
cp .env.production.example .env.production
```

`.env.production` dosyasını düzenle:

```dotenv
LUNA_DOMAIN=luna.example.com
ACME_EMAIL=you@example.com
LUNA_PORT=8080
PERIOD_TRACKER_SESSION_DAYS=30
```

`.env.production` Git tarafından yok sayılır. Gerçek domain/e-posta değerlerini repository'ye commit etme.

Şifreli tam yedek anahtarı ayrı `.env.backup` dosyasında tutulur. Yeni ve boş bir production kurulumuysa [şifreli yedek rehberindeki](ENCRYPTED_BACKUPS.md) `init-env` komutuyla sunucuda üret. Mevcut yerel hesapları taşıyacaksan aşağıdaki veri taşıma bölümünü izle ve mevcut anahtarı güvenli SSH kanalıyla aktar. İki dosya da Git dışında kalmalıdır.

## Production başlatma

```bash
docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile backups \
  -f compose.yaml \
  -f compose.production.yaml \
  up --build -d
```

Bu komut:

1. Backend ve frontend image'larını oluşturur.
2. SQLite ve Caddy sertifika volume'lerini hazırlar.
3. Migration'ları uygular.
4. Backend ve frontend healthcheck'lerini bekler.
5. Caddy'yi 80/443 üzerinde başlatır.
6. Domain doğru yönleniyorsa public TLS sertifikasını otomatik alır.
7. İlk şifreli tam yedeği hemen alır, ardından günlük zamanlamaya geçer.

Durum ve loglar:

```bash
docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile backups \
  -f compose.yaml \
  -f compose.production.yaml \
  ps

docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile backups \
  -f compose.yaml \
  -f compose.production.yaml \
  logs -f caddy
```

`backend`, `frontend` ve `backup` servislerinin `healthy`, `caddy` servisinin `Up` olması beklenir.

## Mevcut yerel hesapları production'a taşıma

Bu akış admin hesabını, kişisel hesabını, arkadaş hesaplarını, davetleri, regl kayıtlarını ve ayarları birlikte taşır. Production backend'i ilk kez başlatmadan önce uygulanması en temiz yöntemdir.

### Yerel bilgisayarda

Güncel bir şifreli yedek al ve host klasörüne çıkar:

```powershell
docker compose --env-file .env.backup --profile backups exec backup python -m app.backup_cli create
New-Item -ItemType Directory -Force backups
docker compose --env-file .env.backup --profile backups cp backup:/app/backups/. ./backups/
```

Listeden en yeni `.luna-backup` dosyasını seç. Repository kodunu normal Git akışıyla; seçilen şifreli dosyayı ve `.env.backup` dosyasını ise SSH/SCP ile sunucuya aktar. Anahtar içeriğini mesajlaşma uygulamasına yapıştırma.

### Production sunucusunda

Repository kökünde `.env.production`, `.env.backup` ve `backups/SECILEN_YEDEK.luna-backup` hazırken önce recovery image'ını oluştur:

```bash
docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile recovery \
  -f compose.yaml \
  -f compose.production.yaml \
  build recovery
```

Yedeği salt-okunur host klasöründen yeni `luna-data` volume'üne doğrulayarak geri yükle:

```bash
docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile recovery \
  -f compose.yaml \
  -f compose.production.yaml \
  run --rm --no-deps \
  -v "$PWD/backups:/import:ro" \
  recovery python -m app.backup_cli restore \
  /import/SECILEN_YEDEK.luna-backup \
  --output /app/data/period_tracker.db
```

Komut var olan bir veritabanını sessizce ezmez. Hedef daha önce oluşturulduysa dur ve mevcut verinin ne olduğunu doğrula; doğrudan `--replace` ekleme. Başarılı restore sonrasında normal production başlatma komutunu çalıştır.

## Doğrulama

```bash
curl -I http://luna.example.com
curl -I https://luna.example.com
curl https://luna.example.com/health
```

Beklenenler:

- HTTP yanıtı HTTPS adresine `308` yönlendirmesi yapar.
- HTTPS sertifikası tarayıcı tarafından güvenilir görünür.
- `/health` yanıtı `{"status":"ok"}` olur.
- `Strict-Transport-Security` ve `Content-Security-Policy` header'ları bulunur.
- Kayıt/giriş sonrası `luna_session` cookie'sinde `Secure`, `HttpOnly` ve `SameSite=Strict` bulunur.

## Production güvenlik ayarları

`compose.production.yaml` otomatik olarak:

- `PERIOD_TRACKER_SECURE_COOKIE=true` kullanır.
- CORS origin'ini yalnız `https://LUNA_DOMAIN` ile sınırlar.
- Backend portunu dışarı açmaz.

`deploy/Caddyfile`:

- HTTP'yi HTTPS'e yönlendirir.
- TLS sertifikasını otomatik yönetir.
- HSTS, CSP, frame, referrer ve MIME güvenlik header'larını ekler.
- Gzip/Zstandard sıkıştırması uygular.
- `Server` response header'ını kaldırır.

## Sertifika ve veri volume'leri

```text
luna-period-tracker_luna-data     # SQLite sağlık verisi
luna-period-tracker_luna-backups  # AES-256-GCM korumalı tam yedekler
luna-period-tracker_caddy-data    # TLS private key ve sertifikalar
luna-period-tracker_caddy-config  # Caddy çalışma yapılandırması
```

Caddy data volume'ü sertifika/private key içerir ve cache olarak görülmemelidir. Şu komutu production sunucusunda dikkatsizce kullanma:

```bash
docker compose down -v
```

Bu komut SQLite ve Caddy volume'lerini silebilir.

## Güncelleme

Önce uygulamadan JSON yedeği al. Ardından:

```bash
git pull --ff-only
docker compose \
  --env-file .env.production \
  --env-file .env.backup \
  --profile backups \
  -f compose.yaml \
  -f compose.production.yaml \
  up --build -d
```

Named volume korunur, bekleyen migration'lar backend başlangıcında uygulanır.

## Geri alma

Kod güncellemesi sorun çıkarırsa:

1. Caddy/backend loglarını incele.
2. Veritabanı migration'ı uygulanmadıysa önceki Git commit'ine dönüp image'ı yeniden oluştur.
3. Migration uygulanmışsa eski kodu doğrudan çalıştırma; [migration geri alma politikasını](MIGRATIONS.md) izle.
4. Veri bozulması varsa deployment öncesi JSON/SQLite yedeğini geri yükle.

## Caddy yapılandırmasını kontrol etme

```bash
docker run --rm \
  -e LUNA_DOMAIN=luna.example.com \
  -e ACME_EMAIL=you@example.com \
  -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.4-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

## Bu repository'de doğrulananlar

- Base ve production Compose dosyaları birlikte parse edildi.
- Caddyfile resmî Caddy `2.11.4-alpine` image'ıyla doğrulandı.
- Localhost üzerinde gerçek TLS terminasyonu çalıştırıldı.
- HTTP → HTTPS `308` yönlendirmesi doğrulandı.
- HTTPS üzerinden `/health` `200` yanıtı alındı.
- HSTS ve CSP header'ları doğrulandı.
- Secure cookie davranışı otomatik API testiyle kapsandı.

Public sertifika alma işlemi yalnız gerçek domain DNS'i gerçek sunucuya yönlendirildiğinde tamamlanabilir.
