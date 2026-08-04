# Çok kullanıcılı işletim ve admin hesabı

Luna tek bir deployment adresinden birden fazla kişiye hizmet verir. Her kişi kendi e-posta/parola hesabını açar, PWA'yı telefonuna kurar ve yalnızca kendi sağlık verilerini görür. Kayıt herkese açık değildir; admin tarafından üretilen davet kodu gerekir.

## Hesap türleri

### Admin hesabı

Admin hesabı yalnızca operasyon içindir:

- davet kodu üretir ve iptal eder;
- kullanıcı e-postası, rolü, oluşturulma tarihi ve aktiflik durumunu görür;
- kişisel kullanıcıyı geçici olarak devre dışı bırakır veya yeniden etkinleştirir;
- kendi parolasını ve kurtarma kodunu yönetir.

Admin API'si profil, regl, semptom, not, PMS, ovülasyon, tahmin veya JSON yedek içeriği döndürmez. Admin hesabıyla kişisel takip endpoint'lerine erişim `403 Forbidden` ile reddedilir.

### Kişisel kullanıcı hesabı

Kişisel kullanıcı yalnızca kendi profilini, dönem kayıtlarını, tahminlerini ve JSON yedeğini yönetir. Admin hesabından farklı bir e-posta kullanılmalıdır. Migration öncesindeki mevcut hesap otomatik olarak `user` rolünde korunur; verileri silinmez.

## İlk admin hesabını oluşturma

Docker kurulumu:

```powershell
docker compose exec backend python -m app.admin_cli create
```

venv ile yerel kurulum:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.admin_cli create
```

Komut e-posta ve parolayı terminalde sorar. Parola komut satırı argümanında veya environment variable içinde tutulmaz. Oluşturulan kurtarma kodu yalnızca bir kez gösterilir.

Admin hesabı oluşturmak otomatik olarak kişisel profil veya regl kaydı oluşturmaz. Aynı kişinin hem admin hem kişisel kullanım yapması için iki ayrı e-posta hesabı gerekir.

## Kullanıcı davet etme

1. Uygulamada admin hesabıyla giriş yap.
2. Davetin geçerlilik gününü ve kullanım sayısını seç.
3. **Davet oluştur** düğmesine bas.
4. Bir kez gösterilen kodu güvenli kanaldan kullanıcıya gönder.
5. Kullanıcı **İlk kez kullanıyorum** ekranında kodu ve kişisel başlangıç bilgilerini girer.

Ham davet kodu veritabanına kaydedilmez; SHA-256 özeti saklanır. Süresi dolan, kullanım limiti biten veya iptal edilen kod kayıt için kullanılamaz. Tek kişiye verilen kodlarda `max_uses=1` önerilir.

## Veri izolasyonu

`profile` ve `periods` tablolarındaki her satır bir `account_id` sahibine bağlıdır. Profil, dönem CRUD, tahmin, dışa aktarma ve geri yükleme sorguları oturumdaki hesap kimliğiyle filtrelenir. Dönem benzersizliği `(account_id, start_date)` üzerindedir; iki kullanıcı aynı tarihi sorunsuz kaydedebilir.

Bir kullanıcı başka hesaba ait dönem kimliğini tahmin etse bile güncelleme ve silme sorgusu sahiplik filtresi nedeniyle `404` döner. `replace` türü JSON geri yükleme yalnızca aktif kullanıcının satırlarını siler; başka kullanıcıların kayıtlarına dokunmaz.

Bu izolasyon API seviyesindedir. Sunucuya veya SQLite dosyasına yönetici erişimi olan kişi teknik olarak veritabanındaki tüm verilere ulaşabilir. Bu nedenle sunucu, SSH erişimi, volume yedekleri ve dosya izinleri güvenilir kişilerle sınırlandırılmalıdır.

## Kullanıcıyı devre dışı bırakma

Admin panelindeki **Devre dışı bırak** işlemi hesabı silmez. Kullanıcının mevcut tüm session kayıtları iptal edilir ve yeni girişleri reddedilir. Profil ve sağlık verileri veritabanında korunur. **Etkinleştir** sonrasında kullanıcı yeniden giriş yapabilir.

## Oturum süresi

Varsayılan session süresi 30 gündür. Bu süre hesabın veya sağlık verilerinin ömrü değildir. Süre sonunda yalnızca cookie/session geçersiz olur ve kullanıcı yeniden giriş yapar. `PERIOD_TRACKER_SESSION_DAYS` ile 1–365 gün arasında değiştirilebilir.

## Üretim kontrol listesi

- Admin ve kişisel hesaplarda farklı, güçlü parolalar kullan.
- Admin kurtarma kodunu çevrimdışı parola yöneticisinde sakla.
- Davetleri mümkünse tek kullanımlık ve kısa süreli oluştur.
- `PERIOD_TRACKER_SECURE_COOKIE=true` ve HTTPS kullan.
- SQLite volume'ünü düzenli ve şifreli olarak yedekle.
- `docker compose down -v` komutunun tüm kalıcı veriyi sildiğini unutma.
- Uygulama ve SSH erişim loglarını izle; uygulama içi rate limiting'e ek olarak production reverse proxy limitlerini değerlendir.
