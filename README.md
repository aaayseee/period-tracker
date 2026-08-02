# Luna — Kişisel Döngü Takibi

Store gerektirmeden telefona kurulabilen, kişisel kullanıma yönelik bir PWA. Arayüz React/TypeScript, API FastAPI ve veriler SQLite üzerinde çalışır.

## Yerel geliştirme

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API `http://localhost:8000`, dokümantasyon `http://localhost:8000/docs` adresinde açılır.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Arayüz `http://localhost:5173` adresinde açılır. Geliştirme sunucusu `/api` isteklerini backend'e yönlendirir.

## Testler

```powershell
cd backend
python -m pytest

cd ../frontend
npm run build
```

## Gizlilik notu

SQLite veritabanı varsayılan olarak `backend/data/period_tracker.db` konumunda saklanır. Uygulamayı internete açarken HTTPS ve kimlik doğrulama eklenmeden yayınlanmamalıdır.

