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
} as const;

export type Translations = typeof tr;
