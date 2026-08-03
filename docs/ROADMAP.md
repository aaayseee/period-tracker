# Aşama Denetimi ve Yol Haritası

## Durum tanımları

- **Tamamlandı:** Kod, entegrasyon ve otomatik test mevcut.
- **MVP tamamlandı:** Temel kullanım çalışıyor; production veya ileri kullanım eksikleri var.
- **Kısmi:** İstenen davranışın yalnızca bir bölümü var.
- **Planlandı:** Henüz uygulanmadı.

## 1. Aşama — Veri Mimarisi ve API

| Beklenti | Durum | Kanıt ve not |
|---|---|---|
| Veritabanı şeması | Tamamlandı | `periods`, `profile`, `accounts`, `sessions` tabloları; indeksler ve constraint'ler `database.py` içinde |
| Regl başlangıç/bitiş tarihleri | Tamamlandı | `start_date`, opsiyonel `end_date`, tarih sırası kontrolü |
| Semptom ve notlar | Tamamlandı | Akış seviyesi, semptom JSON listesi ve 1000 karakterlik not |
| FastAPI iskeleti | Tamamlandı | Lifespan sırasında idempotent SQLite kurulumu, CORS ve health endpoint |
| Veritabanı bağlantısı | Tamamlandı | İstek başına açılıp kapanan `sqlite3.Connection`, row factory ve foreign key kontrolü |
| Tarihleri kaydetme/okuma | Tamamlandı | List, create, update ve delete endpoint'leri |
| Hesap/session | Tamamlandı | Kayıt, giriş, çıkış, session kontrolü ve korumalı veri uçları |
| Parola değiştirme/kurtarma | Tamamlandı | Parola değişimi, hash'li kurtarma kodu, kod rotasyonu ve eski session iptali |
| Veritabanı migration sistemi | Tamamlandı | Sıralı Python migration'ları, `schema_migrations`, otomatik başlangıç yükseltmesi ve rollback testleri |

Değerlendirme: 1. aşama kişisel MVP kapsamı için doğru şekilde tamamlandı. Mevcut SQLite şeması sürümlü migration sistemiyle güvenli şekilde evrilebilir.

## 2. Aşama — Tahminleme Algoritması

| Beklenti | Durum | Kanıt ve not |
|---|---|---|
| Geçmiş başlangıçlardan döngü hesabı | Tamamlandı | Ardışık başlangıç tarihleri arasındaki farkların ortalaması |
| Ortalama regl süresi | Tamamlandı | Tamamlanmış başlangıç/bitiş kayıtlarının inclusive gün ortalaması |
| Profil varsayımları | Tamamlandı | Geçmiş yetersizse onboarding değerleri kullanılıyor |
| Sonraki regl tahmini | Tamamlandı | Son başlangıç + kişisel ortalama döngü |
| Yumurtlama/doğurgan pencere | MVP tamamlandı | Takvim tabanlı yaklaşık hesap; tıbbi model değil |
| PMS penceresi | MVP tamamlandı | Tahmini reglden önceki 7 gün takvimde ayrı renkle gösteriliyor |
| API entegrasyonu | Tamamlandı | `GET /api/insights` |
| Normal döngü testi | Tamamlandı | API testinde 28 günlük düzenli döngü |
| Erken/geç ve düzensiz test | Tamamlandı | 27, 32 ve 29 günlük serinin ortalama/varyasyon testi |
| Aykırı veri testi | Tamamlandı | 15–60 gün dışındaki aralık ortalamadan çıkarılıyor |
| Güven seviyesi | Tamamlandı | Kayıt sayısına göre low/medium/high |

Değerlendirme: Temel istatistiksel algoritma ve API entegrasyonu sağlamdır. Klinik doğruluk, semptom tabanlı model veya olasılıksal güven aralığı kapsamda değildir.

## 3. Aşama — Frontend ve Görsellik

| Beklenti | Durum | Kanıt ve not |
|---|---|---|
| Sade, reklamsız arayüz | Tamamlandı | Mobil öncelikli responsive dashboard |
| Büyük takvim | Tamamlandı | Gerçek, tahmini ve doğurgan gün işaretleri |
| “Döngü başladı/bitti” işlemi | Tamamlandı | Dashboard'da aktif kaydı açan ve bugünün tarihiyle kapatan hızlı buton |
| React API bağlantısı | Tamamlandı | Merkezi `api.ts`, Vite proxy ve tipli modeller |
| Telefonda veri yazma | Tamamlandı | Form → korumalı POST → SQLite → dashboard yenileme |
| İlk kullanım onboarding | Tamamlandı | İsim, hesap, son tarih ve ortalama değerler |
| Daha önceki hesaba giriş | Tamamlandı | E-posta/parola, kalıcı session ve çıkış |
| Yedek alma | Tamamlandı | Profil ve kayıtların JSON export'u |
| JSON geri yükleme | Tamamlandı | Sürüm kontrollü doğrulama, atomik tamamen değiştirme ve güvenli birleştirme seçenekleri |
| Profil/kayıt düzenleme | Tamamlandı | Ayarlar modalı ve geçmiş kayıt düzenleme formu |

Değerlendirme: 3. aşama çalışır durumdadır. UI component testleri ve erişilebilirlik denetimi gelecekte eklenmelidir.

## 4. Aşama — PWA Dönüşümü

| Beklenti | Durum | Kanıt ve not |
|---|---|---|
| Web App Manifest | Tamamlandı | Ad, kısa ad, tema, standalone, dil ve ikon |
| Service Worker | MVP tamamlandı | Uygulama kabuğunda network-first cache |
| İkon ve uygulama adı | MVP tamamlandı | SVG ikon mevcut; production için PNG boyutları eksik |
| Telefona kurulum | Kısmi | HTTPS deployment yapıldığında kurulabilir; deployment henüz yok |
| Çevrimdışı arayüz | MVP tamamlandı | Daha önce yüklenen shell açılabilir |
| Çevrimdışı veri okuma/yazma | Planlandı | API cache, IndexedDB queue ve sync yok |
| Lighthouse/installability doğrulaması | Planlandı | Gerçek HTTPS ortamında yapılmalı |

Değerlendirme: Manifest ve Service Worker doğru temel parçaları sağlar; “tam offline-first ve production-ready PWA” aşaması henüz tamamlanmış sayılmaz.

## Genel sonuç

İlk üç aşama kişisel MVP hedefi için tamamlandı ve otomatik testlerle doğrulanıyor. Dördüncü aşamanın kod tabanı mevcut, ancak gerçek telefon/HTTPS kurulumu, production ikonları ve tam çevrimdışı veri senkronizasyonu eksik.

Bu nedenle doğru ifade:

> Luna çalışan, test edilmiş ve kurulabilir PWA temeline sahip kişisel bir MVP'dir; henüz production deployment ve offline-first aşamalarını tamamlamamıştır.

## Önceliklendirilmiş sonraki işler

### P0 — İnternete açmadan önce

1. HTTPS reverse proxy/deployment
2. Secure cookie ortam değişkeni
3. Gerçek domain CORS ayarı
4. Login rate limiting
5. Şifreli, geri yüklemesi test edilmiş yedek
6. Auth ve recovery endpoint'leri için rate limiting

### P1 — Sağlamlık

1. Backend router'larının dosyalara ayrılması
2. Frontend feature/component ayrımı
3. Merkezi loglama ve hata kodları
4. CI üzerinde test + frontend build
5. API integration ve component test kapsamı

### P2 — PWA kalitesi

1. PNG 192/512 ikonlar ve Apple touch icon
2. Offline fallback ekranı
3. Service Worker güncelleme bildirimi
4. Lighthouse denetimi
5. İstenirse şifreli IndexedDB ve offline sync

### P3 — Çok kullanıcılı ölçek gerekirse

1. PostgreSQL
2. Tablolarda `account_id`
3. SQLAlchemy/Alembic
4. Rate limit ve e-posta doğrulama
5. Birden fazla backend instance ve merkezi session store

## “Bitti” kabul kriteri

Kişisel yerel MVP şu anda bitmiş kabul edilebilir. Production-ready kabulü için P0 maddelerinin tamamı, gerçek telefonda HTTPS kurulum testi ve geri yükleme denemesi zorunludur.
