"""
AI client abstraction.

RealGeminiClient  — calls the real Gemini multimodal API.
MockAIClient      — deterministic stub used in tests and when no API key is set.

get_ai_client()   — FastAPI dependency; returns Mock when GEMINI_API_KEY is empty.
"""

import json
import logging
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


def _detect_mime(image_bytes: bytes) -> str:
    """Return the correct MIME type from magic bytes. Defaults to image/jpeg."""
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/jpeg"


@runtime_checkable
class AIClient(Protocol):
    async def analyze_body(
        self,
        image_bytes: Optional[bytes],
        height_cm: int,
        weight_kg: int,
        fit_preference: str,
    ) -> dict: ...

    async def analyze_garment(self, image_bytes: Optional[bytes]) -> dict: ...

    async def stylist_pick(
        self,
        query: str,
        profile: dict,
        history: list[dict],
        shortlist: list[dict],
    ) -> dict: ...

    async def compose_narrative(
        self,
        profile: dict,
        body_analysis: dict,
        garment_analysis: dict,
        recommendation: dict,
        risk_evaluation: dict,
        review_stats: dict,
    ) -> dict: ...


# ---------------------------------------------------------------------------
# Mock client — fully deterministic, no network calls
# ---------------------------------------------------------------------------

class MockAIClient:
    """Fixed-response stub — used in tests and when GEMINI_API_KEY is absent."""

    async def analyze_body(
        self,
        image_bytes: Optional[bytes],
        height_cm: int,
        weight_kg: int,
        fit_preference: str,
    ) -> dict:
        has_image = image_bytes is not None and len(image_bytes) > 0
        return {
            "silhouette_type": "standart",
            "fit_tendency": "standart",
            "proportional_notes": "Standart vücut oranları tespit edildi.",
            "shoulder_width_estimate": "standart",
            "torso_length_estimate": "standart",
            "confidence": 0.75 if has_image else 0.50,
            "uncertainty_reason": (
                "Görüntü analiz edildi."
                if has_image
                else "Vücut fotoğrafı yüklenmedi; yalnızca profil bilgileri kullanıldı."
            ),
        }

    async def analyze_garment(self, image_bytes: Optional[bytes]) -> dict:
        return {
            "is_garment": True,
            "category": "shirt",
            "fit_type": "regular",
            "cut_notes": "Regular kesim kıyafet.",
            "fabric_cues": "Orta ağırlıklı kumaş.",
            "brand_sizing_tendency": "standart",
            "available_sizes": ["XS", "S", "M", "L", "XL"],
            "confidence": 0.80,
            "uncertainty_reason": "Marka bilgisi görsel üzerinde görünmüyor.",
        }

    async def stylist_pick(
        self,
        query: str,
        profile: dict,
        history: list[dict],
        shortlist: list[dict],
    ) -> dict:
        """Deterministic stub: return the first 3 items with a grounded reason."""
        picks = []
        for item in shortlist[:3]:
            reason = (
                f"{item['category'].capitalize()} kategorisinde "
                f"{item['fit_type']} kesim — profil tercihinle uyumlu."
            )
            warning = None
            tend = item.get("brand_sizing_tendency")
            if tend == "küçük kalıplı":
                warning = "Marka küçük kalıplı — bir beden büyük almayı değerlendir."
            elif tend == "büyük kalıplı":
                warning = "Marka büyük kalıplı — bir beden küçük almayı değerlendir."
            picks.append({
                "garment_id": item["id"],
                "reason_tr": reason,
                "fit_warning_tr": warning,
            })
        note = (
            f"Bütçen ve {profile.get('fit_preference','regular')} kesim tercihine göre "
            f"{len(picks)} ürün hazırladım."
        )
        return {
            "is_fashion_request": True,
            "picks": picks,
            "stylist_note_tr": note,
            "uncertainty_tr": None,
        }

    async def compose_narrative(
        self,
        profile: dict,
        body_analysis: dict,
        garment_analysis: dict,
        recommendation: dict,
        risk_evaluation: dict,
        review_stats: dict,
    ) -> dict:
        """Deterministic templated narrative for demo mode + tests."""
        height = profile.get("height_cm") or "-"
        weight = profile.get("weight_kg") or "-"
        fit_pref = profile.get("fit_preference") or "regular"
        size = recommendation.get("recommended_size") or "-"
        risk_tr = risk_evaluation.get("risk_level_tr") or "Orta Risk"
        has_image = bool(profile.get("has_body_image"))

        fit_type = garment_analysis.get("fit_type", "regular")

        if has_image:
            shoulder = body_analysis.get("shoulder_width_estimate", "standart")
            body_part_note = (
                f"Omuz genişliğin {shoulder} olduğu için {fit_type} kesim "
                f"sende daha dengeli durabilir."
            )
        else:
            # No photo → anchor on numbers + flag the limitation.
            body_part_note = (
                f"Vücut fotoğrafı paylaşılmadığı için tahmin yalnızca boy "
                f"ve kilo verisine dayanıyor; {fit_type} kesim profil "
                f"tercihine ({fit_pref}) uyumlu görünüyor."
            )

        # Stat-flavored sentence pulled from real aggregated review counts.
        total = review_stats.get("total_relevant", 0)
        stat_note = ""
        if total >= 2:
            up = review_stats.get("resized_up_pct", 0)
            down = review_stats.get("resized_down_pct", 0)
            fits = review_stats.get("fits_true_pct", 0)
            if up >= 25:
                stat_note = (
                    f"Benzer ürünleri inceleyen {total} kullanıcının "
                    f"%{up}'i bir beden büyük tercih etti."
                )
            elif down >= 25:
                stat_note = (
                    f"Benzer ürünleri inceleyen {total} kullanıcının "
                    f"%{down}'i bir beden küçük tercih etti."
                )
            else:
                stat_note = (
                    f"Benzer ürünleri inceleyen {total} kullanıcının "
                    f"%{fits}'i beden konusunda sorun yaşamadı."
                )

        narrative = (
            f"Boy {height} cm ve kilo {weight} kg profilinle {fit_pref} kesim "
            f"tercihini birleştirdiğimde, bu ürün için {size} bedeni öneriyorum. "
            f"{body_part_note}"
        )
        if stat_note:
            narrative += f" {stat_note}"
        narrative += f" Genel risk değerlendirmesi: {risk_tr.lower()}."
        return {"detailed_explanation_tr": narrative}


# ---------------------------------------------------------------------------
# Real Gemini client
# ---------------------------------------------------------------------------

_BODY_PROMPT = """\
Analyze body proportions for clothing fit prediction.
User: height={height_cm}cm, weight={weight_kg}kg, fit_preference={fit_preference}
{image_note}

Return ONLY valid JSON with this exact schema — no markdown fences:
{{
  "silhouette_type": "Turkish string — e.g. ince-uzun, standart, atletik",
  "fit_tendency": "dar taraflı|standart|geniş taraflı",
  "proportional_notes": "brief neutral Turkish description",
  "shoulder_width_estimate": "dar|standart|geniş",
  "torso_length_estimate": "kısa|standart|uzun",
  "confidence": 0.0-1.0,
  "uncertainty_reason": "Turkish one-sentence reason for the confidence value"
}}
LANGUAGE: every string value in the JSON MUST be in Turkish. Do not include any English words.
Be respectful and neutral. Focus on fit characteristics only — no attractiveness judgements."""

_NARRATIVE_PROMPT = """\
You are HIWALOY's analysis narrator. Given the structured pipeline outputs
below, write a 3-4 sentence Turkish detailed explanation that is concrete,
useful, and grounded in the data you receive.

USER PROFILE: {profile_json}
BODY ANALYSIS: {body_json}
GARMENT ANALYSIS: {garment_json}
RECOMMENDATION: {recommendation_json}
RISK EVALUATION: {risk_json}
REVIEW STATS (real aggregate from retrieved reviews — never invent numbers):
{stats_json}

WRITE A NARRATIVE that MUST contain ALL of these elements:

1. EITHER a specific body-part observation OR a measurement-anchored note,
   choose based on USER PROFILE.has_body_image:

   1a. If has_body_image is TRUE, you MAY reference ONE body part observed
       in the body analysis fields (silhouette_type / shoulder_width_estimate
       / torso_length_estimate / fit_tendency). Use the actual Turkish body
       part — e.g. "omuz genişliğin", "kol boyun", "bel oranı", "boy-bacak oranı".

   1b. If has_body_image is FALSE, you MUST NOT claim any specific body-part
       observation. Do not mention shoulder, torso, kol, omuz, gövde, silüet,
       or any visible feature — there is no photo to support such a claim.
       Instead, anchor the sentence on the provided NUMBERS: height_cm,
       weight_kg, BMI, fit_preference. ALSO explicitly note that no body
       photo was provided ("vücut fotoğrafı paylaşılmadığı için …" or similar).

2. ONE statistic taken EXACTLY from REVIEW STATS:
   - If `resized_up_pct` >= 25: "Benzer ürünleri inceleyen {{total}} kullanıcının
     %{{resized_up_pct}}'i bir beden büyük aldı." (or similar phrasing)
   - Else if `resized_down_pct` >= 25: "...bir beden küçük tercih etti."
   - Else if `fits_true_pct` is meaningful: "...%{{fits_true_pct}}'i beden
     konusunda sorun yaşamadı."
   - Else (review stats empty / total_relevant < 2): skip the stat sentence
     entirely — DO NOT invent any percentage.
   You MUST use the exact numbers from the input; do not approximate, do not
   round, do not fabricate. If a number is 0 or missing, do not write it.

3. ONE concrete reason for the recommended size that ties the body
   observation to the garment's fit_type, fabric_cues, or
   brand_sizing_tendency. Cite the actual size from RECOMMENDATION.

4. End with the overall risk level in Turkish (Düşük Risk / Orta Risk /
   Yüksek Risk) and a short reason if available.

STYLE: Turkish only, no abstract feelings ("enerjine uyuyor" YASAK), no
markdown, no bullet points. Just plain prose. 3-4 sentences total.

OUTPUT JSON ONLY: {{"detailed_explanation_tr": "..."}}
"""


_STYLIST_PROMPT = """\
You are HIWALOY's AI personal-shopping stylist. The user has a body profile,
recent analysis history, and a request. You will pick EXACTLY 3 items from
the provided product list — no other products may be referenced or invented.

USER PROFILE:
- height_cm: {height_cm}
- weight_kg: {weight_kg}
- fit_preference: {fit_preference}

RECENT ANALYSES (most recent first, may be empty):
{history_summary}

USER REQUEST (Turkish, free text):
{query}

AVAILABLE PRODUCT LIST (the only items you may suggest):
{catalog_json}

STEP 1 — scope gate (do this FIRST):
  Is the user's request asking for a clothing / outfit / fashion suggestion
  (a garment to wear, a kombin idea, a style recommendation)?
  If NO — e.g. they ask for code, math, a translation, news, a recipe, a
  general chatbot answer, or anything unrelated to clothing — return ONLY:
    {{"is_fashion_request": false, "picks": [],
      "stylist_note_tr": "", "uncertainty_tr": null}}
  and STOP. Do NOT invent fashion-flavoured filler. Do NOT pick items.

STEP 2 — selection (only if is_fashion_request is true):
  Return JSON matching:
  {{
    "is_fashion_request": true,
    "picks": [
      {{"garment_id": "g###", "reason_tr": "...", "fit_warning_tr": "..." | null}},
      {{"garment_id": "g###", "reason_tr": "...", "fit_warning_tr": "..." | null}},
      {{"garment_id": "g###", "reason_tr": "...", "fit_warning_tr": "..." | null}}
    ],
    "stylist_note_tr": "...",
    "uncertainty_tr": "..." | null
  }}

RULES (apply to STEP 2 only):
1. Pick exactly 3 distinct items from the list above by their `id`. No invented IDs.
2. Each `reason_tr` MUST be Turkish, concrete, and reference the user's body
   profile, fit_preference, fabric, or category — never abstract feelings.
3. If the brand_sizing_tendency is "küçük kalıplı" or "büyük kalıplı", add a
   short Turkish `fit_warning_tr`. Otherwise leave it null.
4. `stylist_note_tr` is a 1-2 sentence Turkish wrap-up.
5. `uncertainty_tr` non-empty only when relevant constraints couldn't be honored.

OUTPUT: ONLY valid JSON, no markdown fences.
LANGUAGE: every prose string MUST be in Turkish."""


_GARMENT_PROMPT = """\
Analyze this garment image for fit and sizing characteristics.

STEP 1 — gate check (do this FIRST):
  Is this image actually a wearable garment / clothing item (shirt, jeans,
  dress, jacket, coat, sweater, hoodie, skirt, trousers, etc.)?
  If NO — i.e. the image is a screenshot, document, exam question, food,
  scenery, an unrelated object, or a person with no clothing focus —
  return ONLY this JSON and stop:
    {{"is_garment": false, "confidence": 0.0,
      "uncertainty_reason": "Görsel bir kıyafet içermiyor."}}
  Do NOT invent garment details for a non-garment image.

STEP 2 — full analysis (only if is_garment is true):
  Return ONLY valid JSON with this exact schema — no markdown fences:
  {{
    "is_garment": true,
    "category": "shirt|jeans|dress|jacket|coat|other",
    "fit_type": "slim-cut|regular|relaxed|oversize",
    "cut_notes": "Turkish observable cut details",
    "fabric_cues": "Turkish visible weight and texture clues",
    "brand_sizing_tendency": "küçük kalıplı|standart|büyük kalıplı",
    "available_sizes": ["XS","S","M","L","XL"],
    "confidence": 0.0-1.0,
    "uncertainty_reason": "Turkish one-sentence reason for the confidence value"
  }}
LANGUAGE: every prose string value (cut_notes, fabric_cues, uncertainty_reason) MUST be in Turkish.
Keep `category` and `fit_type` as the English tokens above — they are enum keys, not user-facing text."""


class RealGeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite") -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model_name = model
        self._genai = genai

    def _make_model(self):
        return self._genai.GenerativeModel(self._model_name)

    def _parse(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            # Strip opening fence (```json or ```)
            text = text[3:]
            if text.startswith("json"):
                text = text[4:]
            # Strip closing fence if present
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text.strip())

    async def analyze_body(
        self,
        image_bytes: Optional[bytes],
        height_cm: int,
        weight_kg: int,
        fit_preference: str,
    ) -> dict:
        import asyncio
        return await asyncio.to_thread(
            self._analyze_body_sync, image_bytes, height_cm, weight_kg, fit_preference
        )

    def _analyze_body_sync(self, image_bytes, height_cm, weight_kg, fit_preference) -> dict:
        model = self._make_model()
        image_note = "A body image is provided." if image_bytes else "No body image — use profile data only; lower confidence."
        prompt = _BODY_PROMPT.format(
            height_cm=height_cm,
            weight_kg=weight_kg,
            fit_preference=fit_preference,
            image_note=image_note,
        )
        parts: list = []
        if image_bytes:
            parts.append({"mime_type": _detect_mime(image_bytes), "data": image_bytes})
        parts.append(prompt)
        response = model.generate_content(
            parts,
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return self._parse(response.text)

    async def analyze_garment(self, image_bytes: Optional[bytes]) -> dict:
        import asyncio
        return await asyncio.to_thread(self._analyze_garment_sync, image_bytes)

    async def stylist_pick(
        self,
        query: str,
        profile: dict,
        history: list[dict],
        shortlist: list[dict],
    ) -> dict:
        import asyncio
        return await asyncio.to_thread(
            self._stylist_pick_sync, query, profile, history, shortlist
        )

    async def compose_narrative(
        self,
        profile: dict,
        body_analysis: dict,
        garment_analysis: dict,
        recommendation: dict,
        risk_evaluation: dict,
        review_stats: dict,
    ) -> dict:
        import asyncio
        return await asyncio.to_thread(
            self._compose_narrative_sync,
            profile, body_analysis, garment_analysis,
            recommendation, risk_evaluation, review_stats,
        )

    def _compose_narrative_sync(
        self,
        profile: dict,
        body_analysis: dict,
        garment_analysis: dict,
        recommendation: dict,
        risk_evaluation: dict,
        review_stats: dict,
    ) -> dict:
        model = self._make_model()
        prompt = _NARRATIVE_PROMPT.format(
            profile_json=json.dumps(profile, ensure_ascii=False),
            body_json=json.dumps(body_analysis, ensure_ascii=False),
            garment_json=json.dumps(garment_analysis, ensure_ascii=False),
            recommendation_json=json.dumps(recommendation, ensure_ascii=False),
            risk_json=json.dumps(risk_evaluation, ensure_ascii=False),
            stats_json=json.dumps(review_stats, ensure_ascii=False),
        )
        response = model.generate_content(
            [prompt],
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.25,
            ),
        )
        return self._parse(response.text)

    def _stylist_pick_sync(
        self,
        query: str,
        profile: dict,
        history: list[dict],
        shortlist: list[dict],
    ) -> dict:
        model = self._make_model()
        prompt = _STYLIST_PROMPT.format(
            height_cm=profile.get("height_cm"),
            weight_kg=profile.get("weight_kg"),
            fit_preference=profile.get("fit_preference"),
            history_summary=json.dumps(history, ensure_ascii=False),
            query=query,
            catalog_json=json.dumps(shortlist, ensure_ascii=False),
        )
        response = model.generate_content(
            [prompt],
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return self._parse(response.text)

    def _analyze_garment_sync(self, image_bytes) -> dict:
        model = self._make_model()
        parts: list = []
        if image_bytes:
            parts.append({"mime_type": _detect_mime(image_bytes), "data": image_bytes})
        parts.append(_GARMENT_PROMPT)
        response = model.generate_content(
            parts,
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return self._parse(response.text)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_ai_client() -> AIClient:
    """Returns RealGeminiClient if GEMINI_API_KEY is set, otherwise MockAIClient.
    Always returns MockAIClient when DEMO_MODE=true."""
    from app.config import get_settings
    s = get_settings()
    if s.demo_mode:
        logger.info("DEMO_MODE=true — using MockAIClient (deterministic demo)")
        return MockAIClient()
    if s.gemini_api_key:
        model = s.gemini_model or "gemini-3.1-flash-lite"
        return RealGeminiClient(s.gemini_api_key, model)
    logger.warning("GEMINI_API_KEY not set — using MockAIClient")
    return MockAIClient()
