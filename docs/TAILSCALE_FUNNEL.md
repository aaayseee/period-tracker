# Tailscale Funnel ile Ücretsiz Beta Paylaşımı

Bu yöntem Luna'yı domain veya VPS satın almadan, geçerli bir HTTPS adresiyle gerçek telefonda ve davet edilen birkaç kullanıcıyla denemek içindir. Uygulama ve SQLite veritabanı kendi bilgisayarında kalır.

> Bu bir production barındırma çözümü değildir. Bilgisayar, Docker Desktop ve Tailscale çalışır durumda olmalıdır. Bilgisayar uyur veya kapanırsa uygulama erişilemez olur.

## Güvenlik modeli

Funnel adresi internetten erişilebilir ve adresi bilen herkes giriş ekranını görebilir. Luna'nın davet kodu, parola, rate limit, hesap ayrımı ve admin kontrolleri çalışmaya devam eder; fakat şu kurallar korunmalıdır:

- Her arkadaş için ayrı ve kısa süreli bir davet kodu üret.
- Kullanılmayan davetleri admin panelinden iptal et.
- Admin ve kullanıcı hesaplarında benzersiz, güçlü parolalar kullan.
- Tailscale URL'sini herkese açık yerde paylaşma.
- Test bittiğinde Funnel'ı kapat.
- Şifreli veritabanı yedeğini bilgisayardan farklı güvenli bir konuma kopyala.

Funnel TLS'i Tailscale üzerinde sonlandırır ve isteği hosttaki `127.0.0.1:8080` adresine iletir. `compose.funnel.yaml`, tarayıcı HTTPS kullandığı için session cookie'sini `Secure` olarak ayarlar. Backend ve SQLite portları doğrudan internete açılmaz.

## 1. Tailscale kurulumu

Windows için Tailscale'ı resmi indirme sayfasından kur ve bir hesapla giriş yap:

<https://tailscale.com/download/windows>

Yeni bir PowerShell terminalinde doğrula:

```powershell
tailscale version
tailscale status
```

Funnel için Tailscale 1.38.3 veya üzeri, MagicDNS ve tailnet HTTPS gerekir. İlk Funnel komutu gerekli ayarları etkinleştirmek için tarayıcıda onay ekranı açabilir.

## 2. Luna'yı beta yapılandırmasıyla başlatma

Repository kökünde:

```powershell
docker compose `
  --env-file .env.backup `
  --profile backups `
  -f compose.yaml `
  -f compose.funnel.yaml `
  up --build -d
```

`.env.backup` henüz yoksa önce şifreli yedek rehberindeki anahtar oluşturma adımını uygula. Yedek container'ını kullanmadan yalnız uygulamayı başlatmak için:

```powershell
docker compose -f compose.yaml -f compose.funnel.yaml up --build -d
```

Yerel sağlık kontrolü:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
docker compose -f compose.yaml -f compose.funnel.yaml ps
```

Sağlık kontrolü `status: ok`, backend ve frontend ise `healthy` göstermelidir.

## 3. HTTPS Funnel'ı açma

```powershell
tailscale funnel --bg http://127.0.0.1:8080
tailscale funnel status
```

Komut şu biçimde bir adres gösterir:

```text
https://bilgisayar-adi.tailnet-adi.ts.net
```

Bu adres için ayrıca DNS, domain veya router port yönlendirmesi gerekmez. Tailscale bu özelliği hâlen beta olarak sunar ve bant genişliği sınırları uygular.

## 4. Gerçek telefon testi

Testi mümkünse telefonun Wi-Fi bağlantısını kapatıp mobil veri üzerinden yap:

1. Funnel URL'sini telefonda aç ve giriş ekranının geldiğini doğrula.
2. Admin panelinden yalnız o kişi için bir davet kodu üret.
3. Yeni kullanıcı kaydı oluştur ve kurtarma kodunu güvenli yere kaydet.
4. Regl kaydı ekle; takvimde regl, PMS ve ovülasyon işaretlerini kontrol et.
5. Sayfayı kapatıp yeniden aç; 30 günlük session'ın sürdüğünü doğrula.
6. Android Chrome'da **Uygulamayı yükle/Ana ekrana ekle**, iOS Safari'de **Paylaş → Ana Ekrana Ekle** ile PWA'yı kur.
7. Ana ekran ikonundan açıp giriş ve kayıt akışını tekrar kontrol et.
8. Bilgisayarı geçici olarak uyutarak çevrimdışı hata ekranını, yeniden uyandırarak bağlantının geri geldiğini kontrol et.

Telefon testi başarılı sayılmadan önce admin hesabı, kişisel hesap ve ikinci bir kullanıcı hesabının yalnız kendi yetkili ekranlarını gördüğü doğrulanmalıdır.

## 5. Funnel'ı kapatma

Bu bilgisayardaki tüm Funnel yapılandırmasını kapatmak için:

```powershell
tailscale funnel reset
tailscale funnel status
```

`reset`, aynı cihazdaki başka Funnel paylaşımlarını da temizler. Başka bir paylaşım kullanıyorsan önce `tailscale funnel status` çıktısını kontrol et.

Luna container'larını kapatmak için:

```powershell
docker compose -f compose.yaml -f compose.funnel.yaml down
```

Bu komut SQLite verisini silmez. `down -v` kullanma; `-v` kalıcı veritabanı volume'ünü siler.

## Sorun giderme

### Funnel komutu bulunamıyor

Tailscale kurulumundan sonra PowerShell'i kapatıp yeniden aç. Ardından `tailscale version` çalıştır.

### Funnel etkinleştirilemiyor

- Tailscale admin panelinde MagicDNS'in açık olduğunu doğrula.
- İlk komutun açtığı Funnel/HTTPS onayını tamamla.
- Tailscale istemcisini güncelle.
- `tailscale funnel status` ile eski yapılandırmayı kontrol et.

### Giriş başarılı görünüyor ama oturum açılmıyor

Uygulamayı mutlaka `https://...ts.net` adresinden aç ve backend'in beta Compose katmanıyla başladığını doğrula:

```powershell
docker compose -f compose.yaml -f compose.funnel.yaml exec backend `
  python -c "import os; print(os.getenv('PERIOD_TRACKER_SECURE_COOKIE'))"
```

Çıktı `true` olmalıdır. Eski HTTP localhost cookie'leri Funnel domain'ine taşınmaz; bu normaldir ve HTTPS adresinde yeniden giriş gerekir.

### Bilgisayar açıkken bağlantı kesiliyor

Windows güç ayarlarında test boyunca uyku modunu kapat. Docker Desktop ve Tailscale'ın çalıştığını, ardından yerel `http://127.0.0.1:8080/health` adresinin cevap verdiğini kontrol et.

## Sonraki karar

Beta testinde gerçek kullanım, veri miktarı ve erişilebilirlik ihtiyacı ölçülür. Bilgisayarın açık tutulması sürdürülebilir değilse iki dürüst seçenek vardır:

1. Mevcut FastAPI/SQLite mimarisini küçük bir ücretli VPS'e taşımak.
2. Sıfır maliyet önceliği ağır basıyorsa backend ve veritabanını Cloudflare Workers + D1 için ayrı bir dalda yeniden tasarlamak.

Uptime pingi, sahte trafik veya yapay CPU yükü bu projenin deployment yöntemleri arasında değildir.
