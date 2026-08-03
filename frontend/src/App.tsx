import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  Droplets,
  Heart,
  LogOut,
  LoaderCircle,
  LockKeyhole,
  MoonStar,
  Pencil,
  Plus,
  Settings,
  ShieldCheck,
  Sparkles,
  Trash2,
  X
} from "lucide-react";
import { api } from "./api";
import type {
  AccountLoginPayload,
  AccountRegisterPayload,
  AuthSession,
  FlowLevel,
  Insights,
  Period,
  PeriodPayload,
  Profile,
  ProfileUpdatePayload
} from "./types";

const MONTHS = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
];
const WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
const SYMPTOMS = ["Kramp", "Baş ağrısı", "Şişkinlik", "Yorgunluk", "Hassasiyet", "Bel ağrısı"];
const DATE_FORMAT = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long" });
const FULL_DATE_FORMAT = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" });

const toLocalDate = (value: string) => new Date(`${value}T12:00:00`);
const formatDate = (value: string) => DATE_FORMAT.format(toLocalDate(value));
const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

function eachDate(start: string, end: string): string[] {
  const dates: string[] = [];
  const current = toLocalDate(start);
  const finish = toLocalDate(end);
  while (current <= finish) {
    dates.push(`${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`);
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

function Onboarding({ onComplete }: { onComplete: () => Promise<void> }) {
  const [mode, setMode] = useState<"register" | "login">("register");
  const [form, setForm] = useState<AccountRegisterPayload>({
    name: "",
    email: "",
    password: "",
    last_period_start: todayIso(),
    average_cycle_length: 28,
    average_period_length: 5
  });
  const [loginForm, setLoginForm] = useState<AccountLoginPayload>({
    email: "",
    password: ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (mode === "register") {
        await api.register(form);
      } else {
        await api.login(loginForm);
      }
      await onComplete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Oturum açılamadı.");
      setSaving(false);
    }
  };

  const switchMode = (nextMode: "register" | "login") => {
    setMode(nextMode);
    setError("");
  };

  return (
    <section className="onboarding">
      <div className="onboarding-intro">
        <span className="onboarding-icon"><MoonStar size={27} /></span>
        <span className="eyebrow"><Sparkles size={13} /> KİŞİSEL DÖNGÜ ALANIN</span>
        <h1>{mode === "register" ? <>Döngünü birlikte <em>tanıyalım.</em></> : <>Tekrar <em>hoş geldin.</em></>}</h1>
        <p>{mode === "register" ? "Birkaç temel bilgiyle takvimini ve ilk tahminlerini kişiselleştireceğiz." : "Hesabına giriş yaparak kaldığın yerden devam et."}</p>
        <div className="privacy-note">
          <ShieldCheck size={20} />
          <div><strong>Verilerin senin kontrolünde</strong><span>Parolan güvenli şekilde hash’lenir; hiçbir zaman düz metin saklanmaz.</span></div>
        </div>
      </div>

      <form className="onboarding-form panel" onSubmit={submit}>
        <div className="auth-tabs" role="tablist" aria-label="Hesap işlemleri">
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>İlk kez kullanıyorum</button>
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>Hesabım var</button>
        </div>
        <div className="onboarding-title">
          <span className="eyebrow">{mode === "register" ? "HESABINI OLUŞTUR" : "GİRİŞ YAP"}</span>
          <h2>{mode === "register" ? "Merhaba, seni nasıl tanıyalım?" : "Kişisel takvimine dön"}</h2>
          <p>{mode === "register" ? "Bilgilerin ilk kişisel tahminlerinin temelini oluşturur." : "Hesabını oluştururken kullandığın bilgileri gir."}</p>
        </div>

        {mode === "register" ? (
          <>
            <label>
              İsmin
              <input
                required
                autoFocus
                maxLength={60}
                placeholder="Örn. Ayşe"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <div className="auth-credentials-grid">
              <label>
                E-posta
                <input
                  required
                  type="email"
                  autoComplete="email"
                  placeholder="ayse@ornek.com"
                  value={form.email}
                  onChange={(event) => setForm({ ...form, email: event.target.value })}
                />
              </label>
              <label>
                Parola
                <input
                  required
                  type="password"
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="En az 8 karakter"
                  value={form.password}
                  onChange={(event) => setForm({ ...form, password: event.target.value })}
                />
              </label>
            </div>
            <label>
              Son regl başlangıç tarihin
              <input
                required
                type="date"
                max={todayIso()}
                value={form.last_period_start}
                onChange={(event) => setForm({ ...form, last_period_start: event.target.value })}
              />
              <small>Kanamanın başladığı ilk günü seç.</small>
            </label>
            <div className="onboarding-number-grid">
              <label>
                Ortalama döngün
                <div className="number-input">
                  <input
                    required
                    type="number"
                    min={15}
                    max={60}
                    value={form.average_cycle_length}
                    onChange={(event) => setForm({ ...form, average_cycle_length: Number(event.target.value) })}
                  />
                  <span>gün</span>
                </div>
                <small>Genellikle 21–35 gün arasıdır.</small>
              </label>
              <label>
                Regl süren
                <div className="number-input">
                  <input
                    required
                    type="number"
                    min={1}
                    max={15}
                    value={form.average_period_length}
                    onChange={(event) => setForm({ ...form, average_period_length: Number(event.target.value) })}
                  />
                  <span>gün</span>
                </div>
                <small>Kanamanın sürdüğü gün sayısı.</small>
              </label>
            </div>
          </>
        ) : (
          <div className="login-fields">
          <label>
            E-posta
            <input
              required
              autoFocus
              type="email"
              autoComplete="email"
              placeholder="ayse@ornek.com"
              value={loginForm.email}
              onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })}
            />
          </label>
          <label>
            Parola
            <input
              required
              type="password"
              minLength={8}
              autoComplete="current-password"
              placeholder="Parolan"
              value={loginForm.password}
              onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
            />
          </label>
          </div>
        )}

        {error && <p className="form-error">{error}</p>}
        <button className="primary-button full-width onboarding-submit" disabled={saving}>
          {saving ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
          {mode === "register" ? "Hesabımı ve takvimimi oluştur" : "Hesabıma giriş yap"}
        </button>
        <p className="medical-caption">{mode === "register" ? "Tahminler yaklaşık bilgi sağlar ve tıbbi öneri değildir." : "Oturumun bu cihazda güvenli şekilde hatırlanır."}</p>
      </form>
    </section>
  );
}

function Calendar({ periods, insights }: { periods: Period[]; insights: Insights | null }) {
  const now = new Date();
  const [viewDate, setViewDate] = useState(new Date(now.getFullYear(), now.getMonth(), 1));
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const periodDates = useMemo(() => new Set(periods.flatMap((period) =>
    eachDate(period.start_date, period.end_date ?? period.start_date)
  )), [periods]);
  const predictedDates = useMemo(() => new Set(insights
    ? eachDate(insights.next_period_start, insights.next_period_end)
    : []), [insights]);
  const fertileDates = useMemo(() => new Set(insights
    ? eachDate(insights.fertile_window_start, insights.fertile_window_end)
    : []), [insights]);

  const cells = Array.from({ length: firstWeekday + daysInMonth }, (_, index) => {
    if (index < firstWeekday) return null;
    return index - firstWeekday + 1;
  });

  const shiftMonth = (amount: number) => setViewDate(new Date(year, month + amount, 1));

  return (
    <section className="calendar-card panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">TAKVİM</span>
          <h2>{MONTHS[month]} {year}</h2>
        </div>
        <div className="calendar-controls">
          <button className="icon-button" onClick={() => shiftMonth(-1)} aria-label="Önceki ay"><ChevronLeft size={19} /></button>
          <button className="icon-button" onClick={() => shiftMonth(1)} aria-label="Sonraki ay"><ChevronRight size={19} /></button>
        </div>
      </div>
      <div className="calendar-grid weekday-row">
        {WEEKDAYS.map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="calendar-grid days-grid">
        {cells.map((day, index) => {
          if (!day) return <span key={`empty-${index}`} />;
          const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const classes = [
            "calendar-day",
            iso === todayIso() ? "today" : "",
            periodDates.has(iso) ? "period-day" : "",
            !periodDates.has(iso) && predictedDates.has(iso) ? "predicted-day" : "",
            fertileDates.has(iso) ? "fertile-day" : ""
          ].filter(Boolean).join(" ");
          return <span className={classes} key={iso}>{day}</span>;
        })}
      </div>
      <div className="calendar-legend">
        <span><i className="dot period" /> Regl</span>
        <span><i className="dot predicted" /> Tahmini</span>
        <span><i className="dot fertile" /> Doğurgan dönem</span>
      </div>
    </section>
  );
}

function PeriodModal({
  period,
  onClose,
  onSaved
}: {
  period?: Period;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<PeriodPayload>({
    start_date: period?.start_date ?? todayIso(),
    end_date: period?.end_date ?? null,
    flow: period?.flow ?? "medium",
    symptoms: period?.symptoms ?? [],
    notes: period?.notes ?? ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggleSymptom = (symptom: string) => setForm((current) => ({
    ...current,
    symptoms: current.symptoms.includes(symptom)
      ? current.symptoms.filter((item) => item !== symptom)
      : [...current.symptoms, symptom]
  }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (period) {
        await api.updatePeriod(period.id, form);
      } else {
        await api.createPeriod(form);
      }
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Kayıt eklenemedi.");
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-header">
          <div><span className="eyebrow">{period ? "KAYDI DÜZENLE" : "YENİ KAYIT"}</span><h2 id="modal-title">{period ? "Regl bilgilerini güncelle" : "Regl bilgilerini ekle"}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Kapat"><X size={20} /></button>
        </div>
        <form onSubmit={submit}>
          <div className="form-row">
            <label>Başlangıç tarihi<input required type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} /></label>
            <label>Bitiş tarihi <small>(opsiyonel)</small><input type="date" min={form.start_date} value={form.end_date ?? ""} onChange={(event) => setForm({ ...form, end_date: event.target.value || null })} /></label>
          </div>
          <fieldset>
            <legend>Akış yoğunluğu</legend>
            <div className="segmented-control">
              {(["light", "medium", "heavy"] as FlowLevel[]).map((flow) => (
                <button type="button" key={flow} className={form.flow === flow ? "active" : ""} onClick={() => setForm({ ...form, flow })}>
                  {{ light: "Hafif", medium: "Orta", heavy: "Yoğun" }[flow]}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Belirtiler</legend>
            <div className="symptom-list">
              {SYMPTOMS.map((symptom) => <button type="button" key={symptom} className={form.symptoms.includes(symptom) ? "selected" : ""} onClick={() => toggleSymptom(symptom)}>{symptom}</button>)}
            </div>
          </fieldset>
          <label>Not<textarea placeholder="Bugün nasıl hissediyorsun?" rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button full-width" type="submit" disabled={saving}>
            {saving ? <LoaderCircle className="spin" size={18} /> : period ? <Check size={18} /> : <Plus size={18} />} {period ? "Değişiklikleri kaydet" : "Kaydı ekle"}
          </button>
        </form>
      </section>
    </div>
  );
}

function SettingsModal({
  profile,
  onClose,
  onSaved
}: {
  profile: Profile;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [form, setForm] = useState<ProfileUpdatePayload>({
    name: profile.name,
    average_cycle_length: profile.average_cycle_length,
    average_period_length: profile.average_period_length
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.updateProfile(form);
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Ayarlar kaydedilemedi.");
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modal settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="modal-header">
          <div><span className="eyebrow">KİŞİSEL AYARLAR</span><h2 id="settings-title">Profilini güncelle</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Kapat"><X size={20} /></button>
        </div>
        <form onSubmit={submit}>
          <label>İsmin<input required maxLength={60} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <div className="onboarding-number-grid">
            <label>
              Ortalama döngün
              <div className="number-input">
                <input required type="number" min={15} max={60} value={form.average_cycle_length} onChange={(event) => setForm({ ...form, average_cycle_length: Number(event.target.value) })} />
                <span>gün</span>
              </div>
            </label>
            <label>
              Ortalama regl süren
              <div className="number-input">
                <input required type="number" min={1} max={15} value={form.average_period_length} onChange={(event) => setForm({ ...form, average_period_length: Number(event.target.value) })} />
                <span>gün</span>
              </div>
            </label>
          </div>
          <p className="settings-hint">Bu değerler, gerçek geçmiş kayıtların oluşana kadar tahminlerde başlangıç değeri olarak kullanılır.</p>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button full-width" type="submit" disabled={saving}>
            {saving ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />} Ayarları kaydet
          </button>
        </form>
      </section>
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPeriod, setEditingPeriod] = useState<Period | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [quickSaving, setQuickSaving] = useState(false);
  const [quickError, setQuickError] = useState("");

  const loadData = useCallback(async () => {
    setError("");
    try {
      const sessionData = await api.getSession();
      setSession(sessionData);
      if (!sessionData) {
        setProfile(null);
        setPeriods([]);
        setInsights(null);
        return;
      }
      const [profileData, periodData, insightData] = await Promise.all([
        api.getProfile(),
        api.getPeriods(),
        api.getInsights()
      ]);
      setProfile(profileData);
      setPeriods(periodData);
      setInsights(insightData);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Veriler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const activePeriod = periods.find((period) => period.end_date === null) ?? null;

  const quickPeriodAction = async () => {
    setQuickSaving(true);
    setQuickError("");
    try {
      if (activePeriod) {
        await api.updatePeriod(activePeriod.id, {
          start_date: activePeriod.start_date,
          end_date: todayIso(),
          flow: activePeriod.flow,
          symptoms: activePeriod.symptoms,
          notes: activePeriod.notes
        });
      } else {
        await api.createPeriod({
          start_date: todayIso(),
          end_date: null,
          flow: "medium",
          symptoms: [],
          notes: ""
        });
      }
      await loadData();
    } catch (caught) {
      setQuickError(caught instanceof Error ? caught.message : "İşlem tamamlanamadı.");
    } finally {
      setQuickSaving(false);
    }
  };

  const logout = async () => {
    await api.logout();
    setSession(null);
    setProfile(null);
    setPeriods([]);
    setInsights(null);
    setModalOpen(false);
    setEditingPeriod(null);
    setSettingsOpen(false);
  };

  const removePeriod = async (period: Period) => {
    if (!window.confirm(`${FULL_DATE_FORMAT.format(toLocalDate(period.start_date))} kaydını silmek istiyor musun?`)) return;
    await api.deletePeriod(period.id);
    await loadData();
  };

  const downloadBackup = async () => {
    const response = await fetch(api.exportUrl);
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `luna-yedek-${todayIso()}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Luna ana sayfa"><span className="brand-icon"><MoonStar size={20} /></span><span>Luna</span></a>
        <div className="privacy-pill" title={session?.email}><LockKeyhole size={14} /> {profile ? profile.name + " · özel oturum" : "Verilerin sana özel"}</div>
        {profile && <button className="settings-button" onClick={() => setSettingsOpen(true)}><Settings size={15} /> Ayarlar</button>}
        {profile && <button className="logout-button" onClick={logout}><LogOut size={15} /> Çıkış</button>}
        {profile && <button className="primary-button desktop-add" onClick={() => setModalOpen(true)}><Plus size={18} /> Yeni kayıt</button>}
      </header>

      <main id="top">
        {loading ? (
          <div className="loading-state"><LoaderCircle className="spin" /><span>Döngün hazırlanıyor…</span></div>
        ) : error ? (
          <div className="empty-state"><MoonStar size={32} /><h2>API bağlantısı kurulamadı</h2><p>{error} Backend'in çalıştığından emin olup tekrar deneyebilirsin.</p><button className="primary-button" onClick={loadData}>Tekrar dene</button></div>
        ) : !profile ? (
          <Onboarding onComplete={loadData} />
        ) : (
          <>
            <section className="hero">
              <div className="hero-copy">
                <span className="eyebrow"><Sparkles size={13} /> BUGÜNÜN ÖZETİ</span>
                <h1>Merhaba {profile.name}, <em>kendine iyi bak.</em></h1>
                <p>Döngünü kendi ritminde, sakin ve güvenli bir alanda takip et.</p>
                <div className="hero-actions">
                  <button className={activePeriod ? "quick-period-button active" : "quick-period-button"} onClick={quickPeriodAction} disabled={quickSaving}>
                    {quickSaving ? <LoaderCircle className="spin" size={17} /> : activePeriod ? <Check size={17} /> : <Droplets size={17} />}
                    {activePeriod ? "Reglim bitti" : "Reglim başladı"}
                  </button>
                  <button className="secondary-button" onClick={() => setModalOpen(true)}><Plus size={16} /> Detaylı kayıt</button>
                </div>
                {activePeriod && <span className="active-period-note">{formatDate(activePeriod.start_date)} tarihinde başlayan aktif kayıt var.</span>}
                {quickError && <span className="quick-error">{quickError}</span>}
              </div>
              <div className="countdown-card">
                <div className="orb"><span>{insights?.days_until_next_period ?? "—"}</span><small>GÜN</small></div>
                <div><span className="muted">Tahmini sonraki regl</span><strong>{insights ? formatDate(insights.next_period_start) : "—"}</strong><small>{insights?.is_estimate ? "Yeni kayıtlarla tahmin gelişecek" : "Geçmiş döngülerine göre"}</small></div>
              </div>
            </section>

            <section className="stats-grid">
              <article className="stat-card panel rose"><span className="stat-icon"><Droplets size={19} /></span><div><small>ORTALAMA DÖNGÜ</small><strong>{insights?.average_cycle_length} <em>gün</em></strong></div></article>
              <article className="stat-card panel plum"><span className="stat-icon"><CalendarDays size={19} /></span><div><small>ORTALAMA REGL</small><strong>{insights?.average_period_length} <em>gün</em></strong></div></article>
              <article className="stat-card panel green"><span className="stat-icon"><Heart size={19} /></span><div><small>DOĞURGAN DÖNEM</small><strong className="date-value">{insights ? `${formatDate(insights.fertile_window_start)} – ${formatDate(insights.fertile_window_end)}` : "—"}</strong></div></article>
            </section>

            <div className="content-grid">
              <Calendar periods={periods} insights={insights} />
              <aside className="side-column">
                <section className="panel history-card">
                  <div className="section-heading"><div><span className="eyebrow">GEÇMİŞ</span><h2>Son kayıtlar</h2></div><button className="text-button" onClick={downloadBackup}><Download size={16} /> Yedekle</button></div>
                  {periods.length === 0 ? (
                    <div className="no-records"><Droplets size={26} /><strong>Henüz kayıt yok</strong><p>İlk regl tarihini eklediğinde tahminler burada oluşacak.</p></div>
                  ) : (
                    <div className="record-list">
                      {periods.slice(0, 5).map((period) => (
                        <article className="record" key={period.id}>
                          <span className="record-mark" />
                          <div className="record-content"><strong>{formatDate(period.start_date)}{period.end_date ? ` – ${formatDate(period.end_date)}` : " – devam ediyor"}</strong><small>{period.symptoms.length ? period.symptoms.join(" · ") : "Belirti eklenmedi"}</small></div>
                          <div className="record-actions">
                            <button className="edit-button" onClick={() => setEditingPeriod(period)} aria-label="Kaydı düzenle"><Pencil size={15} /></button>
                            <button className="delete-button" onClick={() => removePeriod(period)} aria-label="Kaydı sil"><Trash2 size={16} /></button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
                <section className="info-card">
                  <Sparkles size={20} />
                  <div><strong>Küçük bir hatırlatma</strong><p>Tahminler geçmiş kayıtlarına dayanır; tıbbi tanı veya doğum kontrol yöntemi değildir.</p></div>
                </section>
              </aside>
            </div>
          </>
        )}
      </main>

      {profile && <button className="mobile-fab" onClick={() => setModalOpen(true)} aria-label="Yeni kayıt ekle"><Plus size={23} /></button>}
      {profile && modalOpen && <PeriodModal onClose={() => setModalOpen(false)} onSaved={async () => { setModalOpen(false); await loadData(); }} />}
      {profile && editingPeriod && <PeriodModal period={editingPeriod} onClose={() => setEditingPeriod(null)} onSaved={async () => { setEditingPeriod(null); await loadData(); }} />}
      {profile && settingsOpen && <SettingsModal profile={profile} onClose={() => setSettingsOpen(false)} onSaved={async () => { setSettingsOpen(false); await loadData(); }} />}
    </div>
  );
}
