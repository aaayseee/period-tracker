# API Sözleşmesi

## Genel bilgiler

- Geliştirme base URL: `http://127.0.0.1:8000`
- OpenAPI/Swagger: `/docs`
- Veri biçimi: JSON
- Tarih biçimi: `YYYY-MM-DD`
- Tarih-saat: ISO 8601

Frontend geliştirme sunucusu `/api` isteklerini backend'e proxy eder. Tarayıcı kodu doğrudan port 8000 kullanmaz.

## Kimlik doğrulama

Başarılı kayıt veya giriş yanıtı `luna_session` adlı HttpOnly cookie oluşturur. Tarayıcı sonraki aynı-origin isteklerinde cookie'yi otomatik gönderir.

Korumalı endpoint'ler geçersiz veya eksik session için:

```json
{
  "detail": "Bu islem icin giris yapmalisin."
}
```

ve `401 Unauthorized` döndürür.

## Auth endpoint'leri

### `POST /api/auth/register`

Tek yerel hesabı, profili, ilk regl kaydını ve session'ı oluşturur.

```json
{
  "name": "Ayşe",
  "email": "ayse@example.com",
  "password": "en-az-8-karakter",
  "last_period_start": "2026-07-10",
  "average_cycle_length": 28,
  "average_period_length": 5
}
```

Başarılı yanıt:

```json
{
  "email": "ayse@example.com"
}
```

Zaten hesap varsa `409 Conflict` döner.

### `POST /api/auth/login`

```json
{
  "email": "ayse@example.com",
  "password": "en-az-8-karakter"
}
```

Başarılı giriş yeni session üretir. Hatalı bilgiler `401` döndürür.

### `GET /api/auth/session`

Geçerli session varsa:

```json
{
  "email": "ayse@example.com"
}
```

Oturum yoksa `null` döner. Bu endpoint public'tir.

### `POST /api/auth/logout`

Mevcut session'ı veritabanından siler, cookie'yi temizler ve `204 No Content` döner.

## Profil endpoint'leri

### `GET /api/profile`

Korumalıdır. Kişisel başlangıç ayarlarını döndürür:

```json
{
  "name": "Ayşe",
  "average_cycle_length": 28,
  "average_period_length": 5,
  "created_at": "2026-08-03T10:00:00",
  "updated_at": "2026-08-03T10:00:00"
}
```

### `PUT /api/profile`

Korumalıdır. Profil varsayımlarını ve verilen son regl başlangıcını günceller. İstek kayıt payload'ıyla aynı profil alanlarını kullanır; parola/e-posta istemez.

## Regl kayıtları

### `GET /api/periods`

Korumalıdır. Kayıtları en yeni başlangıç tarihi önce olacak şekilde döndürür.

### `POST /api/periods`

```json
{
  "start_date": "2026-08-01",
  "end_date": "2026-08-05",
  "flow": "medium",
  "symptoms": ["Kramp", "Yorgunluk"],
  "notes": "Kişisel not"
}
```

Kurallar:

- `flow`: `light`, `medium` veya `heavy`
- `end_date` opsiyoneldir.
- Bitiş başlangıçtan önce olamaz.
- Kayıt süresi 15 günden uzun olamaz.
- Semptom listesi en fazla 12 öğedir.
- Not en fazla 1000 karakterdir.
- Aynı başlangıç tarihi iki kez eklenemez.

Başarılı yanıt `201 Created` ve oluşturulan kayıttır.

### `PUT /api/periods/{period_id}`

Mevcut kaydı tam payload ile günceller. Kayıt yoksa `404` döner.

### `DELETE /api/periods/{period_id}`

Kaydı siler ve `204 No Content` döner.

## Tahmin ve yedek

### `GET /api/insights`

Opsiyonel `today=YYYY-MM-DD` parametresi test ve deterministik hesaplama için kullanılabilir.

```json
{
  "average_cycle_length": 28,
  "average_period_length": 5,
  "cycle_variation": 2,
  "next_period_start": "2026-08-29",
  "next_period_end": "2026-09-02",
  "ovulation_date": "2026-08-15",
  "fertile_window_start": "2026-08-10",
  "fertile_window_end": "2026-08-16",
  "days_until_next_period": 26,
  "completed_cycles": 4,
  "confidence": "medium",
  "is_estimate": false
}
```

### `GET /api/export`

Profil ve tüm regl kayıtlarını JSON olarak döndürür. Auth hesabı, parola hash'i ve session token'ları dışa aktarılmaz.

## Sağlık kontrolü

### `GET /health`

Public endpoint:

```json
{
  "status": "ok"
}
```

## Hata biçimi

İş kuralı hataları:

```json
{
  "detail": "Açıklayıcı hata mesajı"
}
```

Pydantic alan doğrulama hataları `422 Unprocessable Entity` ve alan bazlı `detail` listesi döndürür.

## Komut satırından örnek

Cookie'yi PowerShell web session içinde saklayarak hesap oluşturma:

```powershell
$body = @{
  name = "Ayşe"
  email = "ayse@example.com"
  password = "guvenli-parola"
  last_period_start = "2026-07-10"
  average_cycle_length = 28
  average_period_length = 5
} | ConvertTo-Json

Invoke-WebRequest -SessionVariable luna -Method Post -Uri http://127.0.0.1:8000/api/auth/register -ContentType "application/json" -Body $body
Invoke-RestMethod -WebSession $luna -Uri http://127.0.0.1:8000/api/insights
```
