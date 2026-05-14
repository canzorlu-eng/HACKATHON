# HIWALOY — Bilinen Sınırlamalar ve MVP Kapsamı

Bu belge, HIWALOY MVP'nin gerçek yeteneklerini ve sınırlarını dürüstçe açıklar. Jüriler, teknik değerlendirmeciler ve gelecekteki geliştiriciler için yazılmıştır. Hiçbir şey abartılmamıştır.

---

## 1. Beden Öneri Algoritması Deterministiktir — Öğrenmez

**Gerçek durum:**  
Beden tavsiyesi, basit bir BMI hesabına ve önceden tanımlı delta değerlerine dayanan **deterministik bir formüldür**. Gerçek kullanıcı satın alma verilerinden öğrenilmiş bir model değildir.

**Formül:**
```
baz_beden = bmi_tablosuna_göre(bmi, height_cm)
delta = fit_type_delta + brand_delta - user_pref_delta + body_tendency_delta
önerilen_beden = baz_beden + delta
```

**Bu ne anlama geliyor:**
- Aynı girdilerle her zaman aynı beden çıkar
- "XS vs S" sınırı keyfi bir BMI eşiğine dayanır, istatistiksel olarak doğrulanmamıştır
- Farklı ülke beden standartları, ürün kategorisi farklılıkları, yaş grubu etkileri dikkate alınmamıştır

**Ne zaman gerçek olur:**  
Gerçek kullanıcı satın alma ve iade verilerinden eğitilmiş bir model gerektirir.

---

## 2. Gemini Analizi Nitel Tahminden İbarettir

**Gerçek durum:**  
Gemini 1.5 Flash, bir vücut fotoğrafından veya kıyafet görselinden **tahmini niteliksel değerler** üretir. Gerçek ölçümler almaz.

**`analyze_body()` çıktıları gerçekte şunu ifade eder:**
- `silhouette_type: "standart"` → Model bu etiketi makul buluyor, ölçmüyor
- `fit_tendency: "standart"` → LLM çıkarımı, görsel veya demografik ipuçlarından
- `shoulder_width_estimate: "standart"` → Tahmin, hassas ölçüm değil
- `confidence: 0.75` → Modelin belirsizliği, kalibre edilmiş bir güven değil

**`analyze_garment()` için:**
- `category: "shirt"` → Görsel sınıflandırma, yüksek doğruluklu
- `fit_type: "regular"` → Görsel çıkarım, güvenilirlik değişkendir
- `brand_sizing_tendency: "standart"` → Markayı tanımadıkça tahmin, gerçek veri değil

**Sonuç:** Gemini analizi, gerçek ölçüm yerine geçemez. Eksik veya yanlış görsellerle çıktılar güvenilmez olabilir.

---

## 3. Review Intelligence — Veri Sınırlıdır

**Gerçek durum:**  
RAG pipeline ChromaDB üzerinde çalışır ve vektör benzerliğiyle ilgili yorumları getirir. Ancak:

- **Demo modunda** 5 adet elle yazılmış Türkçe örnek yorumla çalışır
- **Üretim modunda** gerçek kullanıcı yorumlarının toplanması, temizlenmesi ve embed edilmesi gerekir — bu yapılmamıştır
- ChromaDB'de yorum yoksa sistem `_FALLBACK_INSIGHTS` kullanır ("Genel öneri:" prefix'iyle) — bunlar gerçek topluluk verisi değildir
- Benzerlik eşiği (0.30) optimize edilmemiştir — farklı veri setlerinde ayar gerekebilir

**Kullanıcıya dürüst bildirim:** Fallback durumunda çıktı "Kullanıcılar belirtiyor" değil "Genel öneri" veya "Genel bilgi" olarak etiketlenir.

---

## 4. Gerçek Zamanlı Scraping Yoktur

**Gerçek durum:**  
Sistem e-ticaret sitelerinden gerçek zamanlı fiyat, stok, veya yorum çekmez. Yorum verisi önceden hazırlanmış ve embed edilmiş olmalıdır.

**Kapsam dışı:** Canlı web scraping, ürün veritabanı entegrasyonu, barkod/QR okuma.

---

## 5. Görsel Analiz Sınırlamaları

**Beden analizi:**
- Serbest duruş, tam cephe fotoğrafı ideal durumdur
- Karanlık ortam, kalabalık arka plan güveni düşürür
- Model bu durumları `uncertainty_reason` alanıyla bildirir

**Kıyafet analizi:**
- Kıyafetin açık bir şekilde görünmesi gerekir
- Manken üzerindeki kıyafetler daha iyi tanınır
- Model üstüne yıkılmış veya katlı kıyafetleri yanlış kategorize edebilir
- Markanın görsel üzerinde görünmemesi durumunda `brand_sizing_tendency: "standart"` varsayılır

---

## 6. Güven Skoru Kalibre Edilmemiştir

**Gerçek durum:**  
`confidence_score` değeri gerçek tahmin doğruluğuyla korelasyon gösterecek şekilde kalibre edilmemiştir. Üretim formülü:

```python
confidence = body_conf * 0.55 + garment_conf * 0.40 + review_boost
```

Bu ağırlıklar sezgisel olarak belirlenmiştir, gerçek doğruluk verisinden öğrenilmemiştir. Kullanıcıya yüksek güven skoru garantisi verilemez.

---

## 7. Kapsamın Dışındakiler (MVP'de Yok)

Aşağıdakiler bilinçli olarak kapsam dışı bırakılmıştır:

| Özellik | Neden kapsam dışı |
|---------|------------------|
| Sanal deneme (virtual try-on) | Gerçek zamanlı 3D rendering gerektirir — hackathon kapsamı değil |
| Gerçekçi kumaş simülasyonu | GPU-intensive, haftalarca geliştirme ister |
| Ürün arama / katalog entegrasyonu | E-ticaret API bağlantısı gerektirir |
| Kullanıcı hesabı (giriş/şifre) | Kimlik doğrulama sistemi kurulmamıştır |
| Profil güncelleme | Sadece oluşturma implementedir |
| Fotoğraf silme / GDPR | Veri yaşam döngüsü yönetimi MVP kapsamında değil |
| Çoklu beden çizelgesi (US/EU/UK) | Tek bir genel beden skalası kullanılmaktadır |
| Mobil uygulama | Responsive web, native app değil |

---

## 8. Altyapı Sınırlamaları

- **Kimlik doğrulama yoktur:** API endpoint'leri herkese açıktır. UUID tahmin edilemez olsa da gerçek yetkilendirme sistemi kurulmamıştır.
- **Rate limiting yoktur:** `/analyze` endpoint üretim için koruma gerektirmektedir.
- **Görsel temizleme çalışmamaktadır:** `IMAGE_RETENTION_HOURS` ayarı var ama arka plan temizleme görevi kurulmamıştır.
- **`NEXT_PUBLIC_API_BASE_URL` build-time sabitlenir:** Backend adresi değiştiğinde frontend yeniden build gerektirir.

---

## Özet Değerlendirme

HIWALOY MVP aşağıdakileri başarıyla göstermektedir:
- ✓ Uçtan uca, açıklanabilir bir AI-first pipeline
- ✓ LangGraph ile modüler ve deterministik akış
- ✓ Multimodal Gemini entegrasyonu (DEMO_MODE=false ile)
- ✓ ChromaDB RAG + grounding invariant
- ✓ Turkish-first kullanıcı deneyimi
- ✓ Güven skoru ve risk ayrıştırması

Üretim için şunlar gereklidir:
- ✗ Gerçek satın alma verisinden öğrenen model
- ✗ Büyük, doğrulanmış yorum veri seti
- ✗ Kimlik doğrulama ve yetkilendirme
- ✗ Ölçeğe göre optimize edilmiş pipeline
