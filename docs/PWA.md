# PWA ve Çevrimdışı Davranış

## Mevcut PWA bileşenleri

Luna aşağıdaki temel PWA parçalarına sahiptir:

- `frontend/public/manifest.webmanifest`
- `frontend/public/sw.js`
- `frontend/public/luna-icon.svg`
- HTML içinde manifest, theme color ve Apple touch icon bağlantıları
- Production modunda Service Worker kaydı
- Mobil uyumlu ve standalone görünümü destekleyen arayüz

## Manifest ayarları

| Alan | Değer |
|---|---|
| Uygulama adı | Luna — Döngü Takibi |
| Kısa ad | Luna |
| Başlangıç yolu | `/` |
| Görünüm | `standalone` |
| Tema | `#a34c61` |
| Dil | `tr` |
| İkon | SVG kaynak, PNG 192/512, maskable 512 ve Apple touch 180 |

## Service Worker stratejisi

Uygulama kabuğu için ağ-öncelikli yaklaşım kullanılır:

1. Tarayıcı kaynağı ağdan ister.
2. Başarılı yanıt cache'e yazılır.
3. Ağ başarısızsa cache yanıtı kullanılır.
4. Navigation için son çare olarak cache'teki `/` döndürülür.

İlk kurulumda şu dosyalar önbelleğe alınır:

- `/`
- `/manifest.webmanifest`
- `/luna-icon.svg`

Vite'ın oluşturduğu JS/CSS dosyaları ilk başarılı isteklerinden sonra cache'e girer.

## Bilinçli çevrimdışı sınırı

`/api/` istekleri Service Worker tarafından yakalanmaz. Bunun nedeni eski veya hassas sağlık verilerinin kontrolsüz biçimde Cache Storage'a yazılmasını önlemektir.

Sonuç:

- Daha önce yüklenen uygulama arayüzü çevrimdışı açılabilir.
- Backend'e erişim yoksa hesap, takvim ve tahmin verileri yüklenemez.
- Çevrimdışıyken yeni kayıt eklenemez.
- Çevrimdışı yazma kuyruğu ve sonradan senkronizasyon yoktur.

Bu nedenle mevcut sürüm “kurulabilir PWA”dır; “tamamen offline-first uygulama” değildir.

## Yerel geliştirmede test

Service Worker yalnızca production derlemesinde kaydedilir. Test için:

```powershell
cd frontend
npm.cmd run build
npm.cmd run preview
```

Tarayıcı geliştirici araçlarında:

1. Application → Manifest bölümünü kontrol et.
2. Application → Service Workers bölümünde worker'ın aktif olduğunu doğrula.
3. Cache Storage altında `luna-shell-v1` cache'ini kontrol et.
4. Network'ü Offline yapıp uygulama kabuğunun açıldığını doğrula.

API'nin çevrimdışı çalışmaması mevcut tasarımda beklenen davranıştır.

## Telefona kurulum

### Android / Chrome

1. Uygulamayı HTTPS adresinden aç.
2. Tarayıcı menüsünden **Uygulamayı yükle** veya **Ana ekrana ekle** seç.
3. Luna ikonu ana ekrana eklenir.

### iOS / Safari

1. HTTPS adresini Safari'de aç.
2. Paylaş düğmesine bas.
3. **Ana Ekrana Ekle** seç.

iOS'ta otomatik kurulum istemi yerine paylaş menüsü kullanılır.

## Güvenli bağlam gereksinimi

Service Worker ve kurulabilirlik için:

- `localhost` geliştirme sırasında güvenli kabul edilir.
- Telefon veya başka cihaz üzerinden erişimde HTTPS gerekir.
- Yerel ağdaki düz `http://192.168.x.x` adresi PWA özelliklerini tam sağlamaz.

Domain, DNS, Caddy ve production Compose adımları için [HTTPS deployment rehberine](DEPLOYMENT.md) bak.

## Production için eksikler

- 192x192 ve 512x512 PNG ikonlar eklendi
- 512x512 maskable ikon ve iOS için 180x180 PNG apple-touch-icon eklendi
- Bağlantı kurulamadığında özel `offline.html` ekranı eklendi
- Cache sürümünün release sürecinde otomatik artırılması
- Offline fallback ekranı
- Güncelleme bulunduğunda kullanıcıya yenileme bildirimi
- Lighthouse PWA denetimi
- Gerçek domain/VPS üzerinde HTTPS ve telefon kurulum doğrulaması
- İstenirse şifreli IndexedDB + offline mutation queue + çatışma çözümü

## Tam offline-first tasarım önerisi

Offline kayıt gerçekten istenirse:

1. Son başarılı profil ve kayıtlar IndexedDB'de şifreli saklanır.
2. Çevrimdışı POST/PUT/DELETE işlemleri benzersiz id ile kuyruğa yazılır.
3. Bağlantı geldiğinde kuyruk sırayla API'ye gönderilir.
4. Sunucu ve cihaz sürümleri için `updated_at` veya revision alanı kullanılır.
5. Çakışma durumunda kullanıcıya seçim sunulur.
6. Çıkışta cihaz cache'i ve şifre anahtarı temizlenir.

Sağlık verisi olduğu için sıradan cache-first yaklaşımı yerine açık bir veri güvenliği modeli kurulmalıdır.
