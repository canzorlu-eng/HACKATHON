# HIWALOY — Demo Sunum Senaryosu (3–5 Dakika)

**Hedef kitle:** Hackathon jüri üyeleri  
**Süre:** 3–5 dakika  
**Dil:** Türkçe  
**Ortam:** `DEMO_MODE=true` (MockAIClient + in-memory reviews, Gemini API gerekmez)

---

## Sunum Açılışı (~30 saniye)

> "Hepimiz çevrimiçi kıyafet alırken aynı soruyla karşılaştık: 'Bu bende nasıl duracak?'
> Marka tablolarına bakıyoruz, ama yine de yanlış beden geliyor.
> HIWALOY bu sorunu çözüyor.
> 'How It Will ACTUALLY Look On You' — kıyafet gerçekten sizde nasıl duracak?"

**[Tarayıcıda http://localhost:3000 açık olmalı]**

---

## 1. Ürün Vizyonu — Ana Sayfa (~30 saniye)

**[Ana sayfa göster]**

> "HIWALOY üç şeyi birleştiriyor:"

- **Vücut analizi** — boy, kilo, fit tercihi ve isteğe bağlı vücut fotoğrafı
- **Kıyafet analizi** — yüklenen görsel üzerinden Gemini multimodal AI
- **Topluluk verileri** — benzer kullanıcı yorumlarından elde edilen içgörüler

> "Sonuç: yüzde ile ifade edilen güven skoru, risk değerlendirmesi ve Türkçe açıklama."

---

## 2. Profil Oluşturma — Onboarding (~45 saniye)

**[/onboarding sayfasına git]**

> "Önce kullanıcı profili oluşturuyoruz. Bu bilgiler tek seferlik — her analizde kullanılıyor."

**Formu doldurun:**
- Boy: `175`
- Kilo: `70`
- Tercih Ettiğiniz Kesim: `Normal Kesim`
- Vücut fotoğrafı: isteğe bağlı, şimdi yüklemiyoruz

> "Vücut fotoğrafı eklemek güven skorunu artırıyor, ama zorunlu değil.
> Sistem fotoğraf olmadan da çalışıyor ve belirsizliği kullanıcıya açıkça bildiriyor."

**"Profil Oluştur" butonuna tıklayın**

> "Profil kaydedildi, şimdi analiz sayfasına yönlendirildik."

---

## 3. Kıyafet Analizi — Ana Demo (~90 saniye)

**[/analyze sayfasında, hazır bir kıyafet görseli yükleyin]**

> "Herhangi bir kıyafetin ekran görüntüsünü ya da fotoğrafını yükleyebilirsiniz —
> e-ticaret sitesinden aldığınız bir görsel bile çalışıyor."

**Görseli yükleyin, "Analizi Başlat" butonuna tıklayın**

> "Sistem şu an 6 adımlı LangGraph pipeline'ını çalıştırıyor:"

**[Progress bar adım adım ilerlerken açıklayın:]**
1. Giriş doğrulama
2. Vücut analizi — boy, kilo, fit tercihi değerlendirmesi
3. Kıyafet analizi — görsel üzerinden kesim, kumaş, kalıp tespiti
4. Topluluk verileri — benzer kıyafetler için kullanıcı yorumları
5. Beden önerisi hesaplama
6. Türkçe çıktı formatlaması

**[Sonuçlar göründüğünde:]**

> "İşte sonuç:"

- **Beden Önerisi:** [önerilen beden] — "BMI, kıyafetin kesimi ve marka kalıp eğilimi birlikte hesaplandı"
- **Güven Skoru:** [yüzde] — "Analiz ne kadar emin? Düşük ise nedenini açıklıyor"
- **Risk Değerlendirmesi:** [düşük/orta/yüksek risk] — "Satın almadan önce dikkat edilmesi gerekenler"
- **Topluluk Yorumları:** — "Bu tür kıyafetler için benzer kullanıcılardan elde edilen içgörüler"
- **Belirsizlik notu:** — "Sistem, emin olmadığı durumu kullanıcıya dürüstçe bildiriyor"

> "Sistemin en önemli özelliği bu son madde:
> Saçma bir kesinlikle 'M alın' demiyoruz.
> Belirsizliği açıklıyoruz. Bu, güven inşa eden bir tasarım kararı."

---

## 4. Geçmiş Analizler (~30 saniye)

**[/history sayfasına git]**

> "Tüm analizler kaydediliyor. Kullanıcı daha önce baktığı kıyafetlere geri dönebiliyor."

**Bir karta tıklayın**

> "Her analizin detay sayfası var — aynı beden önerisi, risk faktörleri ve topluluk yorumlarıyla."

---

## 5. Teknik Özet (~30 saniye)

> "Teknik tarafta:"

- **LangGraph** ile 6 düğümlü, sıralı ve deterministik bir AI pipeline
- **Gemini 1.5 Flash** multimodal analiz — vücut ve kıyafet görselleri için
- **ChromaDB** üzerinde RAG — gerçek kullanıcı yorumları vektör olarak saklanıyor
- **PostgreSQL** ile profil ve analiz geçmişi
- **DEMO_MODE** sayesinde API anahtarı olmadan da tam olarak çalışıyor
- **124 backend testi** — unit, integration, ve edge case coverage

---

## Kapanış (~15 saniye)

> "HIWALOY, 'bu bende nasıl duracak?' sorusuna yapay zekayla dürüst ve açıklanabilir bir cevap veriyor.
> Yanlış beden alımını azaltıyor, iade oranını düşürüyor, kullanıcı güvenini artırıyor.
> Sorularınız var mı?"

---

## Demo Hazırlık Kontrol Listesi

Sunumdan önce:
- [ ] `.\start-demo.ps1` (Windows) veya `./start-demo.sh` (macOS/Linux) ile stack başarıyla ayağa kalkıyor
- [ ] http://localhost:3000 açılıyor
- [ ] http://localhost:8000/api/v1/health `{"status":"ok"}` döndürüyor
- [ ] Yüklenecek bir kıyafet görseli hazır (JPEG veya PNG, max 8MB)
- [ ] Tarayıcı localStorage temiz (eski profil yoksa daha temiz demo)
- [ ] `.env` dosyasında `DEMO_MODE=true`

Yedek plan (backend çökmesi durumunda):
- Ekran görüntüleri `docs/screenshots/` klasöründe tutun
- API yanıtı JSON örneği `docs/sample_response.json` olarak kaydedin
