import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  Check,
  Copy,
  ChevronLeft,
  ChevronRight,
  Download,
  Droplets,
  Heart,
  KeyRound,
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
  Upload,
  X
} from "lucide-react";
import { api } from "./api";
import type {
  AccountLoginPayload,
  AccountRegisterPayload,
  AdminInvite,
  AdminUser,
  AuthSession,
  BackupData,
  FlowLevel,
  Insights,
  Period,
  PeriodPayload,
  PasswordChangePayload,
  PasswordRecoveryPayload,
  Profile,
  ProfileUpdatePayload,
  RestoreMode
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
  const [mode, setMode] = useState<"register" | "login" | "recover">("register");
  const [form, setForm] = useState<AccountRegisterPayload>({
    name: "",
    email: "",
    password: "",
    invite_code: "",
    last_period_start: todayIso(),
    average_cycle_length: 28,
    average_period_length: 5
  });
  const [loginForm, setLoginForm] = useState<AccountLoginPayload>({
    email: "",
    password: ""
  });
  const [recoveryForm, setRecoveryForm] = useState<PasswordRecoveryPayload>({
    email: "",
    recovery_code: "",
    new_password: ""
  });
  const [recoveryCode, setRecoveryCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (mode === "register") {
        const result = await api.register(form);
        setRecoveryCode(result.recovery_code);
        setSaving(false);
        return;
      } else if (mode === "recover") {
        const result = await api.recoverPassword(recoveryForm);
        setRecoveryCode(result.recovery_code);
        setSaving(false);
        return;
      } else {
        await api.login(loginForm);
      }
      await onComplete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Oturum açılamadı.");
      setSaving(false);
    }
  };

  const switchMode = (nextMode: "register" | "login" | "recover") => {
    setMode(nextMode);
    setError("");
  };

  const copyRecoveryCode = async () => {
    await navigator.clipboard.writeText(recoveryCode);
    setCopied(true);
  };

  if (recoveryCode) {
    return (
      <section className="onboarding recovery-onboarding">
        <div className="onboarding-intro">
          <span className="onboarding-icon"><ShieldCheck size={27} /></span>
          <span className="eyebrow"><KeyRound size={13} /> HESAP KURTARMA</span>
          <h1>Kodunu güvenli bir yerde <em>sakla.</em></h1>
          <p>Parolanı unutursan hesabına yalnızca bu kodla yeniden erişebilirsin.</p>
        </div>
        <div className="onboarding-form recovery-card panel">
          <span className="eyebrow">YENİ KURTARMA KODUN</span>
          <h2>Bu kod yalnızca şimdi gösterilecek</h2>
          <p>Ekran görüntüsü alabilir veya çevrimdışı bir parola yöneticisine kaydedebilirsin.</p>
          <code className="recovery-code">{recoveryCode}</code>
          <button type="button" className="secondary-button full-width" onClick={copyRecoveryCode}>
            <Copy size={16} /> {copied ? "Kopyalandı" : "Kodu kopyala"}
          </button>
          <button type="button" className="primary-button full-width" onClick={onComplete}>
            <Check size={17} /> Kodu güvenle kaydettim
          </button>
          <p className="recovery-warning">Bu kodu kaybedersen ve parolanı unutursan hesabın otomatik olarak kurtarılamaz.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="onboarding">
      <div className="onboarding-intro">
        <span className="onboarding-icon"><MoonStar size={27} /></span>
        <span className="eyebrow"><Sparkles size={13} /> KİŞİSEL DÖNGÜ ALANIN</span>
        <h1>{mode === "register" ? <>Döngünü birlikte <em>tanıyalım.</em></> : mode === "login" ? <>Tekrar <em>hoş geldin.</em></> : <>Hesabını birlikte <em>kurtaralım.</em></>}</h1>
        <p>{mode === "register" ? "Birkaç temel bilgiyle takvimini ve ilk tahminlerini kişiselleştireceğiz." : mode === "login" ? "Hesabına giriş yaparak kaldığın yerden devam et." : "Kurtarma kodunla güvenli şekilde yeni bir parola belirle."}</p>
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
          <span className="eyebrow">{mode === "register" ? "HESABINI OLUŞTUR" : mode === "login" ? "GİRİŞ YAP" : "PAROLANI YENİLE"}</span>
          <h2>{mode === "register" ? "Merhaba, seni nasıl tanıyalım?" : mode === "login" ? "Kişisel takvimine dön" : "Kurtarma bilgilerini gir"}</h2>
          <p>{mode === "register" ? "Bilgilerin ilk kişisel tahminlerinin temelini oluşturur." : mode === "login" ? "Hesabını oluştururken kullandığın bilgileri gir." : "Kullanılan kurtarma kodu işlemden sonra yenilenecek."}</p>
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
              Davet kodu
              <input
                required
                autoComplete="off"
                placeholder="XXXXXX-XXXXXX-XXXXXX-XXXXXX"
                value={form.invite_code}
                onChange={(event) => setForm({ ...form, invite_code: event.target.value })}
              />
              <small>Bu kodu uygulama yöneticisinden alabilirsin.</small>
            </label>
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
        ) : mode === "login" ? (
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
          <button type="button" className="forgot-button" onClick={() => switchMode("recover")}>Parolamı unuttum</button>
          </div>
        ) : (
          <div className="login-fields recovery-fields">
            <label>
              E-posta
              <input
                required
                autoFocus
                type="email"
                autoComplete="email"
                placeholder="ayse@ornek.com"
                value={recoveryForm.email}
                onChange={(event) => setRecoveryForm({ ...recoveryForm, email: event.target.value })}
              />
            </label>
            <label>
              Kurtarma kodu
              <input
                required
                autoComplete="off"
                placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
                value={recoveryForm.recovery_code}
                onChange={(event) => setRecoveryForm({ ...recoveryForm, recovery_code: event.target.value })}
              />
            </label>
            <label>
              Yeni parola
              <input
                required
                type="password"
                minLength={8}
                autoComplete="new-password"
                placeholder="En az 8 karakter"
                value={recoveryForm.new_password}
                onChange={(event) => setRecoveryForm({ ...recoveryForm, new_password: event.target.value })}
              />
            </label>
            <button type="button" className="forgot-button" onClick={() => switchMode("login")}>Giriş ekranına dön</button>
          </div>
        )}

        {error && <p className="form-error">{error}</p>}
        <button className="primary-button full-width onboarding-submit" disabled={saving}>
          {saving ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
          {mode === "register" ? "Hesabımı ve takvimimi oluştur" : mode === "login" ? "Hesabıma giriş yap" : "Parolamı yenile"}
        </button>
        <p className="medical-caption">{mode === "register" ? "Tahminler yaklaşık bilgi sağlar ve tıbbi öneri değildir." : mode === "login" ? "Oturumun bu cihazda güvenli şekilde hatırlanır." : "Başarılı işlemden sonra yeni bir kurtarma kodu verilir."}</p>
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
  const pmsDates = useMemo(() => new Set(insights
    ? eachDate(insights.pms_window_start, insights.pms_window_end)
    : []), [insights]);
  const ovulationDate = insights?.ovulation_date ?? null;

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
            fertileDates.has(iso) ? "fertile-day" : "",
            pmsDates.has(iso) ? "pms-day" : "",
            iso === ovulationDate ? "ovulation-day" : ""
          ].filter(Boolean).join(" ");
          return <span className={classes} key={iso}>{day}</span>;
        })}
      </div>
      <div className="calendar-legend">
        <span><i className="dot period" /> Regl</span>
        <span><i className="dot predicted" /> Tahmini</span>
        <span><i className="dot fertile" /> Doğurgan dönem</span>
        <span><i className="dot ovulation" /> Ovülasyon</span>
        <span><i className="dot pms" /> PMS</span>
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
  onSaved,
  onRestored
}: {
  profile: Profile;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onRestored: () => Promise<void>;
}) {
  const [form, setForm] = useState<ProfileUpdatePayload>({
    name: profile.name,
    average_cycle_length: profile.average_cycle_length,
    average_period_length: profile.average_period_length
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [passwordForm, setPasswordForm] = useState<PasswordChangePayload>({
    current_password: "",
    new_password: ""
  });
  const [securitySaving, setSecuritySaving] = useState(false);
  const [securityError, setSecurityError] = useState("");
  const [securitySuccess, setSecuritySuccess] = useState("");
  const [settingsRecoveryCode, setSettingsRecoveryCode] = useState("");
  const [restoreBackup, setRestoreBackup] = useState<BackupData | null>(null);
  const [restoreFileName, setRestoreFileName] = useState("");
  const [restoreMode, setRestoreMode] = useState<RestoreMode>("replace");
  const [restoreSaving, setRestoreSaving] = useState(false);
  const [restoreError, setRestoreError] = useState("");
  const [restoreSuccess, setRestoreSuccess] = useState("");

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

  const submitPassword = async (event: FormEvent) => {
    event.preventDefault();
    setSecuritySaving(true);
    setSecurityError("");
    setSecuritySuccess("");
    try {
      await api.changePassword(passwordForm);
      setPasswordForm({ current_password: "", new_password: "" });
      setSecuritySuccess("Parolan değiştirildi; diğer açık oturumlar kapatıldı.");
    } catch (caught) {
      setSecurityError(caught instanceof Error ? caught.message : "Parola değiştirilemedi.");
    } finally {
      setSecuritySaving(false);
    }
  };

  const createRecoveryCode = async () => {
    if (window.confirm("Yeni kod oluşturulursa önceki kurtarma kodun geçersiz olacak. Devam edilsin mi?")) {
      setSecuritySaving(true);
      setSecurityError("");
      try {
        const result = await api.rotateRecoveryCode();
        setSettingsRecoveryCode(result.recovery_code);
      } catch (caught) {
        setSecurityError(caught instanceof Error ? caught.message : "Kurtarma kodu oluşturulamadı.");
      } finally {
        setSecuritySaving(false);
      }
    }
  };

  const selectBackup = async (file?: File) => {
    setRestoreBackup(null);
    setRestoreFileName("");
    setRestoreError("");
    setRestoreSuccess("");
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setRestoreError("Yedek dosyası en fazla 5 MB olabilir.");
      return;
    }

    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (
        typeof parsed !== "object" ||
        parsed === null ||
        typeof (parsed as { exported_at?: unknown }).exported_at !== "string" ||
        !Array.isArray((parsed as { periods?: unknown }).periods)
      ) {
        throw new Error("Bu dosya Luna JSON yedeği biçiminde değil.");
      }
      setRestoreBackup(parsed as BackupData);
      setRestoreFileName(file.name);
    } catch (caught) {
      setRestoreError(caught instanceof Error ? caught.message : "Yedek dosyası okunamadı.");
    }
  };

  const restoreData = async () => {
    if (!restoreBackup) return;
    const warning = restoreMode === "replace"
      ? "Mevcut profil ayarların ve tüm regl kayıtların yedekteki verilerle değiştirilecek. Bu işlem geri alınamaz. Devam edilsin mi?"
      : "Yalnızca mevcut olmayan tarihli kayıtlar eklenecek; mevcut profilin ve kayıtların korunacak. Devam edilsin mi?";
    if (!window.confirm(warning)) return;

    setRestoreSaving(true);
    setRestoreError("");
    setRestoreSuccess("");
    try {
      const result = await api.restoreBackup({ backup: restoreBackup, mode: restoreMode });
      await onRestored();
      const skipped = result.skipped_periods
        ? `, ${result.skipped_periods} mevcut kayıt atlandı`
        : "";
      setRestoreSuccess(
        `Geri yükleme tamamlandı: ${result.imported_periods} kayıt aktarıldı${skipped}. Toplam ${result.total_periods} kayıt var.`
      );
    } catch (caught) {
      setRestoreError(caught instanceof Error ? caught.message : "Yedek geri yüklenemedi.");
    } finally {
      setRestoreSaving(false);
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
        <div className="settings-divider" />
        <div className="data-section">
          <span className="eyebrow">VERİ YÖNETİMİ</span>
          <h3>JSON yedeğini geri yükle</h3>
          <p className="section-description">Luna'dan indirdiğin bir JSON yedeğini seç. Hesap, parola ve oturum bilgileri yedekten etkilenmez.</p>
          <label className="backup-file-picker">
            <input
              className="visually-hidden"
              type="file"
              accept="application/json,.json"
              onChange={(event) => void selectBackup(event.target.files?.[0])}
            />
            <Upload size={17} />
            <span>{restoreFileName || "JSON yedek dosyası seç"}</span>
          </label>
          {restoreBackup && (
            <>
              <div className="restore-mode" role="group" aria-label="Geri yükleme yöntemi">
                <button type="button" className={restoreMode === "replace" ? "active" : ""} onClick={() => setRestoreMode("replace")}>Tamamen değiştir</button>
                <button type="button" className={restoreMode === "merge" ? "active" : ""} onClick={() => setRestoreMode("merge")}>Kayıtları birleştir</button>
              </div>
              <p className="settings-hint restore-hint">
                {restoreMode === "replace"
                  ? "Profil ve tüm regl kayıtları yedekteki haliyle değiştirilir."
                  : "Mevcut profil korunur; yalnızca eksik başlangıç tarihleri eklenir."}
              </p>
              <button type="button" className="secondary-button full-width" onClick={restoreData} disabled={restoreSaving}>
                {restoreSaving ? <LoaderCircle className="spin" size={17} /> : <Upload size={16} />} Yedeği geri yükle
              </button>
            </>
          )}
          {restoreError && <p className="form-error restore-message">{restoreError}</p>}
          {restoreSuccess && <p className="form-success">{restoreSuccess}</p>}
        </div>
        <div className="settings-divider" />
        <div className="security-section">
          <span className="eyebrow">HESAP GÜVENLİĞİ</span>
          <h3>Parolanı değiştir</h3>
          <form onSubmit={submitPassword}>
            <div className="auth-credentials-grid">
              <label>Mevcut parola<input required type="password" minLength={8} autoComplete="current-password" value={passwordForm.current_password} onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })} /></label>
              <label>Yeni parola<input required type="password" minLength={8} autoComplete="new-password" value={passwordForm.new_password} onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })} /></label>
            </div>
            <button className="secondary-button full-width" type="submit" disabled={securitySaving}><KeyRound size={16} /> Parolayı değiştir</button>
          </form>
          <div className="recovery-settings">
            <strong>Kurtarma kodu</strong>
            <p>Parolanı unutursan hesabına bu kodla erişebilirsin. Yeni kod oluşturmak önceki kodu geçersiz kılar.</p>
            {settingsRecoveryCode && (
              <>
                <code className="recovery-code compact">{settingsRecoveryCode}</code>
                <button type="button" className="secondary-button full-width" onClick={async () => {
                  await navigator.clipboard.writeText(settingsRecoveryCode);
                  setSecuritySuccess("Kurtarma kodu panoya kopyalandı.");
                }}><Copy size={15} /> Kodu kopyala</button>
              </>
            )}
            <button type="button" className="secondary-button full-width" onClick={createRecoveryCode} disabled={securitySaving}>
              <ShieldCheck size={16} /> Yeni kurtarma kodu oluştur
            </button>
          </div>
          {securityError && <p className="form-error">{securityError}</p>}
          {securitySuccess && <p className="form-success">{securitySuccess}</p>}
        </div>
      </section>
    </div>
  );
}

function AdminDashboard({ session, onLogout }: { session: AuthSession; onLogout: () => Promise<void> }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [invites, setInvites] = useState<AdminInvite[]>([]);
  const [expiryDays, setExpiryDays] = useState(7);
  const [maxUses, setMaxUses] = useState(1);
  const [createdCode, setCreatedCode] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [adminError, setAdminError] = useState("");

  const loadAdminData = useCallback(async () => {
    const [userData, inviteData] = await Promise.all([
      api.getAdminUsers(),
      api.getAdminInvites()
    ]);
    setUsers(userData);
    setInvites(inviteData);
  }, []);

  useEffect(() => {
    loadAdminData().catch((caught) => {
      setAdminError(caught instanceof Error ? caught.message : "Yönetim verileri yüklenemedi.");
    });
  }, [loadAdminData]);

  const createInvite = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setAdminError("");
    setMessage("");
    try {
      const result = await api.createAdminInvite({ expiry_days: expiryDays, max_uses: maxUses });
      setCreatedCode(result.invite_code);
      setMessage("Davet oluşturuldu. Kod yalnızca bu ekranda bir kez gösterilir.");
      await loadAdminData();
    } catch (caught) {
      setAdminError(caught instanceof Error ? caught.message : "Davet oluşturulamadı.");
    } finally {
      setBusy(false);
    }
  };

  const toggleUser = async (user: AdminUser) => {
    setBusy(true);
    setAdminError("");
    try {
      await api.updateAdminUser(user.id, !user.is_active);
      await loadAdminData();
    } catch (caught) {
      setAdminError(caught instanceof Error ? caught.message : "Kullanıcı güncellenemedi.");
    } finally {
      setBusy(false);
    }
  };

  const revokeInvite = async (invite: AdminInvite) => {
    setBusy(true);
    setAdminError("");
    try {
      await api.revokeAdminInvite(invite.id);
      await loadAdminData();
    } catch (caught) {
      setAdminError(caught instanceof Error ? caught.message : "Davet iptal edilemedi.");
    } finally {
      setBusy(false);
    }
  };

  const changeAdminPassword = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setAdminError("");
    setMessage("");
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Yönetici parolası değiştirildi.");
    } catch (caught) {
      setAdminError(caught instanceof Error ? caught.message : "Parola değiştirilemedi.");
    } finally {
      setBusy(false);
    }
  };

  const createRecoveryCode = async () => {
    setBusy(true);
    setAdminError("");
    try {
      const result = await api.rotateRecoveryCode();
      setRecoveryCode(result.recovery_code);
      setMessage("Yeni kurtarma kodunu güvenli bir yerde sakla.");
    } catch (caught) {
      setAdminError(caught instanceof Error ? caught.message : "Kurtarma kodu oluşturulamadı.");
    } finally {
      setBusy(false);
    }
  };

  const userAccounts = users.filter((user) => user.role === "user");

  return (
    <section className="admin-dashboard">
      <div className="admin-heading">
        <div>
          <span className="eyebrow"><ShieldCheck size={14} /> YÖNETİCİ ALANI</span>
          <h1>Kullanıcı ve davet yönetimi</h1>
          <p>{session.email} · Sağlık verileri bu panelde gösterilmez.</p>
        </div>
        <button className="logout-button" onClick={onLogout}><LogOut size={15} /> Çıkış</button>
      </div>

      {adminError && <p className="form-error admin-message">{adminError}</p>}
      {message && <p className="form-success admin-message">{message}</p>}

      <div className="admin-grid">
        <section className="panel admin-card">
          <span className="eyebrow">YENİ DAVET</span>
          <h2>Kayıt kodu oluştur</h2>
          <form onSubmit={createInvite}>
            <div className="form-row">
              <label>Süre (gün)<input type="number" min={1} max={365} value={expiryDays} onChange={(event) => setExpiryDays(Number(event.target.value))} /></label>
              <label>Kullanım hakkı<input type="number" min={1} max={100} value={maxUses} onChange={(event) => setMaxUses(Number(event.target.value))} /></label>
            </div>
            <button className="primary-button full-width" disabled={busy}><Plus size={16} /> Davet oluştur</button>
          </form>
          {createdCode && (
            <div className="admin-code">
              <code className="recovery-code compact">{createdCode}</code>
              <button className="secondary-button full-width" onClick={async () => navigator.clipboard.writeText(createdCode)}><Copy size={15} /> Kodu kopyala</button>
            </div>
          )}
        </section>

        <section className="panel admin-card">
          <span className="eyebrow">HESAP GÜVENLİĞİ</span>
          <h2>Admin hesabı</h2>
          <form onSubmit={changeAdminPassword}>
            <label>Mevcut parola<input required type="password" minLength={8} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
            <label>Yeni parola<input required type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
            <button className="secondary-button full-width" disabled={busy}><KeyRound size={15} /> Parolayı değiştir</button>
          </form>
          {recoveryCode && <code className="recovery-code compact">{recoveryCode}</code>}
          <button className="secondary-button full-width" onClick={createRecoveryCode} disabled={busy}><ShieldCheck size={15} /> Yeni kurtarma kodu</button>
        </section>
      </div>

      <section className="panel admin-card admin-wide">
        <div className="section-heading"><div><span className="eyebrow">KULLANICILAR</span><h2>{userAccounts.length} kişisel hesap</h2></div></div>
        <div className="admin-list">
          {userAccounts.map((user) => (
            <article key={user.id} className="admin-row">
              <div><strong>{user.email}</strong><small>Oluşturulma: {new Date(user.created_at).toLocaleDateString("tr-TR")}</small></div>
              <button className={user.is_active ? "secondary-button" : "primary-button"} onClick={() => toggleUser(user)} disabled={busy}>{user.is_active ? "Devre dışı bırak" : "Etkinleştir"}</button>
            </article>
          ))}
          {!userAccounts.length && <p className="settings-hint">Henüz kişisel kullanıcı hesabı yok.</p>}
        </div>
      </section>

      <section className="panel admin-card admin-wide">
        <div className="section-heading"><div><span className="eyebrow">DAVETLER</span><h2>Davet geçmişi</h2></div></div>
        <div className="admin-list">
          {invites.map((invite) => {
            const unavailable = Boolean(invite.revoked_at) || invite.use_count >= invite.max_uses || new Date(invite.expires_at) <= new Date();
            return (
              <article key={invite.id} className="admin-row">
                <div><strong>Davet #{invite.id} · {invite.use_count}/{invite.max_uses} kullanım</strong><small>Son tarih: {new Date(invite.expires_at).toLocaleString("tr-TR")}{invite.revoked_at ? " · İptal edildi" : ""}</small></div>
                <button className="secondary-button" onClick={() => revokeInvite(invite)} disabled={busy || unavailable}>İptal et</button>
              </article>
            );
          })}
          {!invites.length && <p className="settings-hint">Henüz davet oluşturulmadı.</p>}
        </div>
      </section>
    </section>
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
      if (sessionData.role === "admin") {
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
        ) : session?.role === "admin" ? (
          <AdminDashboard session={session} onLogout={logout} />
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
      {profile && settingsOpen && <SettingsModal profile={profile} onClose={() => setSettingsOpen(false)} onSaved={async () => { setSettingsOpen(false); await loadData(); }} onRestored={loadData} />}
    </div>
  );
}
