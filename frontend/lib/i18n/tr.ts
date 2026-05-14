export const tr = {
  app: {
    name: "HIWALOY",
    tagline: "Üzerinizde Nasıl Duracağını Görün",
  },
  landing: {
    badge: "AI destekli beden ve uyum analizi",
    title: "Kıyafetin sizde gerçekten nasıl duracağını alışveriş öncesi anlayın.",
    subtitle:
      "HIWALOY, vücut özelliklerinizi, kıyafet bilgilerini ve kullanıcı yorumlarını birleştirerek açıklanabilir beden önerileri ve satın alma riski analizi sunar.",
    phaseNote: "Bu sürüm yalnızca temel altyapıyı içerir. AI özellikleri sonraki fazlarda devreye alınacaktır.",
  },
  common: {
    loading: "Yükleniyor…",
    error: "Bir hata oluştu. Lütfen tekrar deneyin.",
    retry: "Tekrar Dene",
  },
  health: {
    ok: "Sistem çalışıyor",
    unreachable: "Servise ulaşılamıyor",
  },
  nav: {
    home: "Ana Sayfa",
    analyze: "Analiz",
    history: "Geçmiş",
    newProfile: "Profil Oluştur",
  },
  onboarding: {
    title: "Profil Oluştur",
    subtitle: "Doğru beden önerisi için ölçülerinizi girin.",
    heightLabel: "Boy (cm)",
    weightLabel: "Kilo (kg)",
    fitLabel: "Tercih Ettiğiniz Kesim",
    fitOptions: {
      slim: "Dar Kesim",
      regular: "Normal Kesim",
      relaxed: "Rahat Kesim",
      oversize: "Oversize",
    },
    bodyImageLabel: "Vücut Fotoğrafı (isteğe bağlı)",
    bodyImageHint: "Fotoğraf eklenmesi öneri doğruluğunu artırır.",
    submit: "Profil Oluştur",
    success: "Profiliniz oluşturuldu.",
    errors: {
      heightRange: "Boy 50–300 cm arasında olmalıdır.",
      weightRange: "Kilo 20–500 kg arasında olmalıdır.",
    },
  },
  analyze: {
    title: "Kıyafet Analizi",
    subtitle: "Kıyafet görselini yükleyin, AI beden önerinizi hazırlasın.",
    upload: "Görsel Yükle",
    uploadHint: "JPEG veya PNG, maks 8 MB",
    noProfile: "Önce profilinizi oluşturun.",
    goToProfile: "Profile Git",
    start: "Analizi Başlat",
    steps: {
      validating: "Giriş doğrulanıyor…",
      analyzing: "Beden ve kıyafet analiz ediliyor…",
      retrieving: "Kullanıcı yorumları inceleniyor…",
      generating: "Beden önerisi hazırlanıyor…",
      evaluating: "Risk değerlendirmesi yapılıyor…",
      formatting: "Sonuçlar hazırlanıyor…",
    },
    done: "Analiz tamamlandı",
  },
  recommendation: {
    title: "Beden Önerisi",
    confidence: "Güven Skoru",
    explanation: "Açıklama",
    uncertainty: "Belirsizlik",
  },
  risk: {
    title: "Risk Değerlendirmesi",
    low: "Düşük Risk",
    medium: "Orta Risk",
    high: "Yüksek Risk",
    factors: "Risk Faktörleri",
    noFactors: "Belirgin bir risk faktörü tespit edilmedi.",
  },
  community: {
    title: "Topluluk Yorumları",
    empty: "Henüz yeterli kullanıcı yorumu bulunmuyor.",
  },
  history: {
    title: "Geçmiş Analizler",
    empty: "Henüz analiz yapılmamış.",
    size: "Beden",
    risk: "Risk",
    date: "Tarih",
  },
} as const;

export type Translations = typeof tr;
