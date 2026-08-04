# Veritabanı Migration Sistemi

Luna, doğrudan `sqlite3` kullandığı için ORM bağımlılığı eklemeden çalışan küçük bir migration runner içerir. Sistem Alembic ile aynı temel sorunu çözer: şema değişikliklerini sürümlü, sıralı ve yalnızca bir kez uygulanır hale getirir.

## Dosya yapısı

```text
backend/app/migrations/
├── __init__.py                 # Registry, runner, durum modeli
├── __main__.py                # Komut satırı arayüzü
└── versions/
    ├── v0001_initial.py        # İlk tablolar ve indeksler
    ├── v0002_recovery_code.py  # recovery_code_hash sütunu
    ├── v0003_multi_user.py     # hesap sahipliği, roller ve davetler
    ├── v0004_auth_rate_limits.py # kalıcı auth rate limit olayları
    └── v0005_admin_audit_logs.py # güvenli yönetim hareketleri
```

Uygulanan migration'lar SQLite içindeki `schema_migrations` tablosuna kaydedilir:

| Alan | Anlamı |
|---|---|
| `version` | Sıralı ve benzersiz migration numarası |
| `name` | Değişmeyen açıklayıcı isim |
| `applied_at` | Uygulanma zamanı |

SQLite `PRAGMA user_version` değeri de son başarılı sürümle güncellenir. Ana geçmiş kaynağı `schema_migrations` tablosudur.

## Çalışma biçimi

FastAPI başlarken `init_database()` çağrılır:

1. `schema_migrations` tablosu yoksa oluşturulur.
2. Kod içindeki migration registry doğrulanır; sürümler 1'den başlayarak kesintisiz ve sıralı olmalıdır.
3. Veritabanındaki uygulanmış sürümlerin kodda bulunduğu ve isimlerinin değişmediği kontrol edilir.
4. Legacy tablolar varsa zorunlu sütunların uyumlu olduğu doğrulanır.
5. Her eksik migration için `BEGIN IMMEDIATE` transaction açılır.
6. Şema değişikliği ve migration geçmiş kaydı aynı transaction içinde yazılır.
7. Başarılıysa commit, herhangi bir hata oluşursa rollback yapılır ve backend başlamaz.

Backend'in hatalı veya yarım yükseltilmiş şemayla hizmet vermemesi bilinçli bir güvenlik davranışıdır.

## Komutlar

Backend klasöründen:

```powershell
.\.venv\Scripts\python.exe -m app.migrations status
```

Örnek çıktı:

```text
Database: C:\...\backend\data\period_tracker.db
[x] 0001 initial_schema (2026-08-03 14:30:00)
[x] 0002 add_recovery_code_hash (2026-08-03 14:30:00)
[x] 0003 multi_user_accounts_and_invites (2026-08-03 14:31:00)
[x] 0004 auth_rate_limit_events (2026-08-04 10:00:00)
[x] 0005 admin_audit_logs (2026-08-04 11:00:00)
Latest version: 0005
```

Bekleyen migration'ları manuel uygulamak için:

```powershell
.\.venv\Scripts\python.exe -m app.migrations upgrade
```

`PERIOD_TRACKER_DB` tanımlıysa komutlar aynı özel veritabanı yolunu kullanır.

## Yeni migration ekleme

Örnek olarak altıncı migration:

```python
# backend/app/migrations/versions/v0006_example.py
import sqlite3

VERSION = 6
NAME = "add_example_column"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE profile ADD COLUMN example TEXT"
    )
```

Ardından modül `backend/app/migrations/__init__.py` içindeki `MIGRATIONS` tuple'ına eklenir. Şu kurallar zorunludur:

- Sürüm numarası son sürümün tam olarak bir fazlası olmalıdır.
- İsim benzersiz ve daha sonra değiştirilmeyecek olmalıdır.
- SQL parametreleri gerektiğinde placeholder kullanmalıdır.
- Migration kendi başına `commit` veya `rollback` çağırmamalıdır; transaction runner'a aittir.
- Daha önce yayınlanmış migration dosyası değiştirilmemelidir. Yeni düzeltme yeni sürüm olarak eklenmelidir.
- Migration için temiz kurulum, eski şemadan yükseltme ve gerekiyorsa veri dönüşümü testi yazılmalıdır.

## Mevcut veritabanlarının uyumluluğu

Migration sistemi eklenmeden önce oluşturulan Luna veritabanlarında `schema_migrations` tablosu bulunmaz. İlk açılışta:

- `0001`, var olan tabloları `CREATE ... IF NOT EXISTS` ile korur.
- `0002`, `recovery_code_hash` sütunu zaten varsa tekrar eklemez.
- `0003`, singleton hesabı `user` rolünde korur; profil ve tüm regl kayıtlarını aynı hesabın `account_id` değeriyle ilişkilendirir, ardından admin/davet desteğini ekler.
- `0004`, düz e-posta veya IP saklamayan kalıcı auth rate limit olay tablosunu ve indekslerini ekler.
- `0005`, sağlık verisi içermeyen admin audit tablosunu ve sorgu indekslerini ekler.
- Hesap kimliği, profil, session ve regl kayıt içerikleri silinmez.
- Beş migration başarıyla geçmişe kaydedilir.

Bu geçiş otomatik testte gerçek bir legacy şema ve örnek hesap verisiyle doğrulanır.

## Rollback politikası

Tek bir migration çalışırken hata oluşursa o migration'ın tüm değişiklikleri otomatik rollback edilir. Bilinçli bir `downgrade` komutu yoktur; SQLite'ta sütun/tablo geri alma işlemleri veri kaybı riski taşıdığı için otomatik geri sürüm yerine şu süreç kullanılır:

1. Uygulamayı durdur.
2. Hata logunu incele.
3. Gerekirse migration öncesi SQLite/JSON yedeğini geri yükle.
4. Hatalı migration yayınlanmadıysa düzelt; yayınlandıysa yeni ileri migration oluştur.
5. Testleri çalıştırıp tekrar `upgrade` uygula.

## Neden Alembic değil?

Mevcut uygulama SQLAlchemy kullanmıyor ve tek SQLite veritabanıyla çalışıyor. Yalnızca migration için SQLAlchemy + Alembic eklemek kurulum ve bakım yükünü artırırdı. Yerel runner mevcut kapsam için daha küçük ve test edilebilir bir çözümdür.

Uygulama PostgreSQL ve SQLAlchemy'ye geçtiğinde migration geçmişi Alembic revision'larına taşınmalıdır. Bu geçiş yolu [Mimari ve Ölçeklenebilirlik](ARCHITECTURE.md) belgesinde açıklanır.
