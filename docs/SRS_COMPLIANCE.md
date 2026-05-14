# SRS Uyumluluk Matrisi — UC-01 to UC-08

Bu belge, HIWALOY MVP implementasyonunun SRS (Software Requirements Specification) gereksinimlerine karşılık geldiğini kanıtlar.

---

## UC-01 — Kullanıcı Profili Yönetimi

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Kullanıcı boy, kilo, fit tercihi girer | `POST /api/v1/profile` form alanları | `backend/app/api/profile.py` |
| Fit tercihi: slim, regular, relaxed, oversize | `FitPreference` enum validation | `backend/app/schemas/profile.py` |
| Boy 50–300 cm, kilo 20–500 kg aralığı | FastAPI validation + Türkçe hata mesajları | `backend/app/api/profile.py` |
| Vücut fotoğrafı isteğe bağlı | `body_image: Optional[UploadFile]` | `backend/app/api/profile.py` |
| UUID ile profil kaydedilir | `User` SQLModel, UUID primary key | `backend/app/models/user.py` |
| Profil daha sonra getirilebilir | `GET /api/v1/profile/{user_id}` | `backend/app/api/profile.py` |
| Onboarding sayfası Turkish | Form labels, error messages all Turkish | `frontend/app/onboarding/page.tsx` |

**Kapsam dışı (MVP):** Profil güncelleme, çoklu profil, hesap yönetimi.

---

## UC-02 — Kıyafet Görseli Yükleme

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| JPEG/PNG yükleme | MIME magic bytes kontrolü | `backend/app/services/image_store.py` |
| Maksimum dosya boyutu | `MAX_UPLOAD_MB` (varsayılan 8MB) | `backend/app/config.py` |
| BMP ve desteklenmeyen formatlar reddedilir | `ImageValidationError` + 422 HTTP | `backend/app/services/image_store.py` |
| Görsel disk üzerinde güvenli saklanır | `./var/images/garment/` subfolder | `backend/app/services/image_store.py` |
| Görsel URL olarak ifşa edilmez | Yalnızca iç referans path kullanılır | `backend/app/api/analyze.py` |
| Türkçe hata mesajları | 422 detail her zaman Türkçe | `backend/app/services/image_store.py` |

---

## UC-03 — Vücut Analiz Ajansı

**Durum: Kısmi (MockAI deterministik, gerçek Gemini opsiyonel)**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Vücut oranları analizi | `analyze_body()` → `silhouette_type`, `fit_tendency` | `backend/app/ai/client.py` |
| Fotoğraf varsa görsel analiz | `RealGeminiClient._analyze_body_sync` | `backend/app/ai/client.py` |
| Fotoğraf yoksa düşük güven | `MockAIClient`: confidence 0.75→0.50 | `backend/app/ai/client.py` |
| Respectful, neutral dil | Prompt engineering + reviewed output | `backend/app/ai/client.py` |
| PNG ve JPEG doğru MIME | `_detect_mime()` magic bytes kontrolü | `backend/app/ai/client.py` |
| Güven skoru döndürülür | `confidence` alanı 0.0–1.0 | `backend/app/ai/client.py` |
| Belirsizlik açıklanır | `uncertainty_reason` alanı | `backend/app/ai/client.py` |

**Not:** `DEMO_MODE=true` durumunda `MockAIClient` deterministik sonuçlar döndürür. Gerçek görsel analiz için `GEMINI_API_KEY` gerekir.

---

## UC-04 — Kıyafet Analiz Ajansı

**Durum: Kısmi (MockAI deterministik, gerçek Gemini opsiyonel)**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Kıyafet kategorisi tespiti | `category`: shirt/jeans/dress/jacket/coat/other | `backend/app/ai/client.py` |
| Kesim tipi tespiti | `fit_type`: slim-cut/regular/relaxed/oversize | `backend/app/ai/client.py` |
| Kumaş ipuçları | `fabric_cues` alanı | `backend/app/ai/client.py` |
| Marka kalıp eğilimi | `brand_sizing_tendency` alanı | `backend/app/ai/client.py` |
| Mevcut bedenler | `available_sizes` listesi | `backend/app/ai/client.py` |
| Güven skoru ve belirsizlik | `confidence` + `uncertainty_reason` | `backend/app/ai/client.py` |

---

## UC-05 — Beden Öneri Ajansı

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Vücut + kıyafet + yorumları birleştirir | `recommendation_generator_node` | `backend/app/ai/nodes.py` |
| BMI tabanlı baz beden | `_size_from_bmi(bmi, height_cm)` | `backend/app/ai/nodes.py` |
| Fit tipi, kullanıcı tercihi, marka delta | `_FIT_TYPE_DELTA`, `_USER_PREF_DELTA`, `_BRAND_DELTA` | `backend/app/ai/nodes.py` |
| Güven skoru hesaplaması | Body×0.55 + garment×0.40 + review_boost | `backend/app/ai/nodes.py` |
| Türkçe açıklama (explanation_tr) | Marka notu ile birlikte | `backend/app/ai/nodes.py` |
| Belirsizlik metni (uncertainty_tr) | Vücut + kıyafet belirsizliği birleştirilir | `backend/app/ai/nodes.py` |
| Güven yüzdesi formatı (%NN) | `confidence_pct` alanı | `backend/app/ai/nodes.py` |

---

## UC-06 — Yorum Zekası (RAG)

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Kullanıcı yorumları vektör olarak saklanır | ChromaDB cosine space | `backend/app/services/review_service.py` |
| Kosinus benzerliği ile relevance filtreleme | `min_relevance=0.30` | `backend/app/services/review_service.py` |
| Jaccard deduplication | `_deduplicate(threshold=0.85)` | `backend/app/services/review_service.py` |
| Grounding invariant | Sadece `themes` metadata'sından | `backend/app/services/review_service.py` |
| `is_grounded=True` her insight'ta | Test: `TestGroundingInvariant` | `backend/tests/test_review_intelligence.py` |
| Demo modu in-memory seeding | `_make_demo_service()` + 5 örnek yorum | `backend/app/services/review_service.py` |
| ChromaDB yoksa graceful fallback | `get_review_service()` None döner | `backend/app/services/review_service.py` |
| Fallback insights gerçek community gibi sunulmaz | `is_fallback=True` + "Genel öneri:" prefix | `backend/app/ai/nodes.py` |

---

## UC-07 — Satın Alma Riski Ajansı

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Risk seviyesi: low/medium/high | `risk_evaluator_node` | `backend/app/ai/nodes.py` |
| Türkçe risk etiketi (risk_level_tr) | Düşük/Orta/Yüksek Risk | `backend/app/ai/nodes.py` |
| Spesifik risk faktörleri (risk_factors_tr) | Güven, kumaş, marka, fotoğraf eksikliği | `backend/app/ai/nodes.py` |
| Vücut fotoğrafı eksikliği risk faktörü | `"Vücut fotoğrafı yüklenmedi…"` | `backend/app/ai/nodes.py` |
| İnce kumaş risk faktörü | fabric_cues'da "ince" kontrolü | `backend/app/ai/nodes.py` |
| Marka uyarısı | küçük/büyük kalıplı marka tespiti | `backend/app/ai/nodes.py` |
| Topluluk uyarısı | review insights'tan "küçük/dar/büyük" | `backend/app/ai/nodes.py` |

---

## UC-08 — Analiz Geçmişi

**Durum: Tam Uyumlu**

| SRS Gereksinimi | Implementasyon | Dosya |
|-----------------|---------------|-------|
| Analiz sonuçları kaydedilir | `Analysis` SQLModel + PostgreSQL | `backend/app/models/analysis.py` |
| Kullanıcıya göre listeleme | `GET /api/v1/history/{user_id}` | `backend/app/api/history.py` |
| Analiz detayı getirme | `GET /api/v1/history/{user_id}/{analysis_id}` | `backend/app/api/history.py` |
| Kullanıcı izolasyonu | `analysis.user_id != user_id` kontrolü | `backend/app/api/history.py` |
| Türkçe 404 mesajı | `"Analiz kaydı bulunamadı."` | `backend/app/api/history.py` |
| History list UI | Discriminated union state machine | `frontend/app/history/page.tsx` |
| History detail UI | Full AI fields + Türkçe | `frontend/app/history/[id]/page.tsx` |
| Geçmişten detail navigasyon | `Link href={/history/${id}}` | `frontend/components/history-card.tsx` |

---

## LangGraph Pipeline Uyumluluğu

SRS gereksinimine göre zorunlu graph flow:

| SRS Node | Implementasyon | Bağlantı |
|----------|---------------|---------|
| Intent Validation | `intent_validator_node` | START → intent_validator |
| Body Analysis | `make_analyzer_node` (asyncio.gather) | intent_validator → analyzer |
| Garment Analysis | `make_analyzer_node` (asyncio.gather) | (paralel, aynı node) |
| Review Retrieval | `review_retriever_node` | analyzer → review_retriever |
| Recommendation Generation | `recommendation_generator_node` | review_retriever → recommendation_generator |
| Risk Evaluation | `risk_evaluator_node` | recommendation_generator → risk_evaluator |
| Turkish Formatting | `turkish_formatter_node` | risk_evaluator → turkish_formatter → END |

Body ve garment analizi `asyncio.gather` ile paralel çalışır — SRS'in "parallel execution" gereksinimi karşılanmıştır.

---

## Test Coverage

| Test Dosyası | Kapsam | Sayı |
|-------------|--------|------|
| `test_ai_client.py` | MIME detection, JSON parse | 14 |
| `test_review_intelligence.py` | RAG pipeline, grounding, dedup | 27 |
| `test_integration.py` | Tam UC akışı, hata yolları, CORS | 30 |
| `test_pipeline.py` | LangGraph node'ları, boyut hesabı | 21 |
| `test_profile.py` | UC-01 validation | 13 |
| `test_uploads.py` | UC-02 dosya yükleme | 10 |
| `test_history.py` | UC-08 history | 7 |
| `test_health.py` | Sağlık endpoint | 2 |
| **Toplam** | | **124** |
