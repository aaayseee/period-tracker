# PWA ve Çevrimdışı Davranış

## Mevcut PWA bileşenleri

Luna aşağıdaki PWA parçalarına sahiptir:

- `frontend/public/manifest.webmanifest`
- `frontend/public/sw.js`
- `frontend/public/offline.html`, `offline.css` ve `offline.js`
- `frontend/public/luna-icon.svg`
- 192×192, 512×512, maskable 512×512 ve opak 180×180 Apple touch PNG ikonları
- HTML içinde manifest, theme color ve Apple touch icon bağlantıları
- Production derlemesinde Service Worker kaydı
- Mobil uyumlu ve standalone görünümü destekleyen arayüz
- Web Push için `push` ve `notificationclick` olayları

## Manifest ayarları

| Alan | Değer |
|---|---|
| Uygulama adı | Luna — Döngü Takibi |
| Kısa ad | Luna |
| Başlangıç yolu | `/` |
| Görünüm | `standalone` |
| Arka plan | `#fcf9f7` |
| Tema | `#a34c61` |
| Dil | `tr` |
| İkonlar | PNG 192/512 `any`, PNG 512 `maskable`, Apple touch 180 |

İkon URL'lerinde sürüm sorgusu kullanılır. Bunun amacı iOS ve PWA önbelleğinin eski, hatalı şeffaf ikonları yeniden kullanmasını önlemektir. iOS mevcut ana ekran ikonunu her zaman otomatik yenilemez; ikon değişikliğinde Luna'yı ana ekrandan silip Safari üzerinden yeniden eklemek gerekebilir.

## Service Worker stratejisi

Güncel cache adı `luna-shell-v4` değeridir. Strateji istek türüne göre ayrılır:

### Önceden cache'lenen dosyalar

Service Worker kurulurken şunlar cache'e alınır:

- `/offline.html`, `/offline.css`, `/offline.js`
- `/manifest.webmanifest`
- `/luna-icon.svg`
- Sürümlü PNG uygulama ikonları ve Apple touch icon

### Sayfa gezinmeleri

Navigation isteklerinde ağ önceliklidir:

1. Sayfa ağdan istenir.
2. Ağ erişilemezse `/offline.html` gösterilir.

Ana uygulama HTML'i çevrimdışı veri kullanımı için cache'lenmez. Bu nedenle bağlantı yokken eski sağlık verileri yerine açık bir çevrimdışı hata ekranı gösterilir.

### Statik dosyalar

Navigation ve `/api` dışındaki GET isteklerinde cache önceliklidir:

1. Eşleşen cache yanıtı varsa kullanılır.
2. Yoksa kaynak ağdan alınır.
3. Başarılı yanıt runtime cache'e yazılır.

Aktivasyon sırasında `luna-shell-v4` dışındaki eski Luna cache'leri temizlenir.

### API istekleri

`/api/` istekleri Service Worker tarafından yakalanmaz. Böylece eski veya hassas sağlık verileri kontrolsüz biçimde Cache Storage'a yazılmaz.

Sonuç:

- Bağlantı yokken özel çevrimdışı ekranı açılır.
- Backend'e erişim yoksa hesap, takvim ve tahmin verileri yüklenmez.
- Çevrimdışıyken kayıt ekleme, düzenleme veya silme yapılamaz.
- Çevrimdışı yazma kuyruğu ve sonradan senkronizasyon yoktur.

Mevcut sürüm kurulabilir bir PWA'dır; tam offline-first uygulama değildir.

## Yerel geliştirmede test

Service Worker yalnız production derlemesinde kaydedilir. Test için:

```powershell
cd frontend
npm.cmd run build
npm.cmd run preview
```

Tarayıcı geliştirici araçlarında:

1. Application → Manifest bölümünde ikonları ve `standalone` görünümü kontrol et.
2. Application → Service Workers bölümünde worker'ın aktif olduğunu doğrula.
3. Cache Storage altında `luna-shell-v4` cache'ini kontrol et.
4. Network'ü Offline yapıp `/offline.html` ekranının açıldığını doğrula.
5. Network'ü tekrar Online yapıp uygulamanın normal giriş ekranına döndüğünü kontrol et.

API'nin çevrimdışı çalışmaması mevcut tasarımda beklenen davranıştır.

## Telefona kurulum

### Android / Chrome

1. Uygulamayı HTTPS adresinden aç.
2. Tarayıcı menüsünden **Uygulamayı yükle** veya **Ana ekrana ekle** seç.
3. Luna'yı ana ekran ikonundan aç.
4. Bildirim kullanılacaksa kişisel hesapla giriş yapıp **Ayarlar → Hatırlatıcılar → Bu cihazda bildirimleri aç** seç.

Android launcher uygulama ikonunu cihaz temasına göre daire veya squircle maskesiyle gösterebilir. Maskable ikon bu davranış için eklenmiştir.

### iOS / Safari

1. HTTPS adresini Safari'de aç.
2. Paylaş düğmesine bas.
3. **Ana Ekrana Ekle** seç.
4. Kurulum ekranında **Open as Web App** seçeneğini açık bırak.
5. Luna'yı ana ekran ikonundan aç.

iOS'ta otomatik kurulum istemi yerine paylaş menüsü kullanılır. Luna'nın iPhone üzerinde ana ekrana kurulması, oturumun sürmesi ve gerçek Web Push test bildirimi başarıyla doğrulanmıştır. Uygulamayı ana ekrandan silip yeniden kurmak cihaz push aboneliğini kaldırabileceği için bildirim izni tekrar verilmelidir.

## Güvenli bağlam gereksinimi

Service Worker, kurulum ve Web Push için:

- `localhost` geliştirme sırasında güvenli kabul edilir.
- Telefon veya başka cihaz üzerinden erişimde HTTPS gerekir.
- Yerel ağdaki düz `http://192.168.x.x` adresi tam PWA ve güvenli cookie akışı için yeterli değildir.

Domain/VPS olmadan gerçek telefon testi [Tailscale Funnel rehberiyle](TAILSCALE_FUNNEL.md), kalıcı domain ve Caddy kurulumu [HTTPS deployment rehberiyle](DEPLOYMENT.md) açıklanır.

## Web Push bildirimleri

Service Worker `push` olayında hassas tarih veya sağlık ayrıntısı içermeyen bildirimi gösterir. `notificationclick`, açık Luna penceresini odaklar veya yeni pencere açar.

Bildirim izni ve aboneliği cihaz bazındadır. Aynı hesap iPhone ve Android gibi birden fazla cihazda ayrı ayrı etkinleştirilebilir; bir cihazdaki aboneliği kapatmak diğer cihaz aboneliklerini silmez. Hatırlatma saati, PMS seçimi ve kaç gün önce uyarılacağı hesap genelinde ortaktır.

VAPID anahtarları, Docker scheduler, API'ler, gizlilik yaklaşımı ve sorun giderme için [Web Push bildirimleri rehberine](NOTIFICATIONS.md) bak.

## Production ve ileri PWA işleri

Tamamlanmamış ileri işler:

- Release sürecinde cache sürümünün otomatik artırılması
- Yeni sürüm bulunduğunda kullanıcıya uygulama içi yenileme bildirimi
- Lighthouse PWA/erişilebilirlik denetimi
- Gerçek domain/VPS üzerinde kalıcı 7/24 HTTPS işletimi
- Android üzerinde ayrıca fiziksel kurulum ve bildirim testi
- İstenirse şifreli IndexedDB, offline mutation queue ve çatışma çözümü

## Tam offline-first tasarım önerisi

Offline kayıt gerçekten istenirse:

1. Son başarılı profil ve kayıtlar IndexedDB'de şifreli saklanır.
2. Çevrimdışı POST/PUT/DELETE işlemleri benzersiz id ile kuyruğa yazılır.
3. Bağlantı geldiğinde kuyruk sırayla API'ye gönderilir.
4. Sunucu ve cihaz sürümleri için `updated_at` veya revision alanı kullanılır.
5. Çakışma durumunda kullanıcıya seçim sunulur.
6. Çıkışta cihaz cache'i ve şifre anahtarı temizlenir.

Sağlık verisi olduğu için sıradan cache-first yaklaşımı yerine açık bir veri güvenliği modeli kurulmalıdır.