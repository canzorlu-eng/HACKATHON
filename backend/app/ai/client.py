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
            "category": "shirt",
            "fit_type": "regular",
            "cut_notes": "Regular kesim kıyafet.",
            "fabric_cues": "Orta ağırlıklı kumaş.",
            "brand_sizing_tendency": "standart",
            "available_sizes": ["XS", "S", "M", "L", "XL"],
            "confidence": 0.80,
            "uncertainty_reason": "Marka bilgisi görsel üzerinde görünmüyor.",
        }


# ---------------------------------------------------------------------------
# Real Gemini client
# ---------------------------------------------------------------------------

_BODY_PROMPT = """\
Analyze body proportions for clothing fit prediction.
User: height={height_cm}cm, weight={weight_kg}kg, fit_preference={fit_preference}
{image_note}

Return ONLY valid JSON with this exact schema — no markdown fences:
{{
  "silhouette_type": "string — e.g. ince-uzun, standart, atletik",
  "fit_tendency": "dar taraflı|standart|geniş taraflı",
  "proportional_notes": "brief neutral description",
  "shoulder_width_estimate": "dar|standart|geniş",
  "torso_length_estimate": "kısa|standart|uzun",
  "confidence": 0.0-1.0,
  "uncertainty_reason": "what limits confidence"
}}
Be respectful and neutral. Focus on fit characteristics only — no attractiveness judgements."""

_GARMENT_PROMPT = """\
Analyze this garment image for fit and sizing characteristics.

Return ONLY valid JSON with this exact schema — no markdown fences:
{{
  "category": "shirt|jeans|dress|jacket|coat|other",
  "fit_type": "slim-cut|regular|relaxed|oversize",
  "cut_notes": "observable cut details",
  "fabric_cues": "visible weight and texture clues",
  "brand_sizing_tendency": "küçük kalıplı|standart|büyük kalıplı",
  "available_sizes": ["XS","S","M","L","XL"],
  "confidence": 0.0-1.0,
  "uncertainty_reason": "what limits confidence"
}}"""


class RealGeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model_name = model
        self._genai = genai

    def _make_model(self):
        return self._genai.GenerativeModel(self._model_name)

    def _parse(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)

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
            parts.append({"mime_type": "image/jpeg", "data": image_bytes})
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

    def _analyze_garment_sync(self, image_bytes) -> dict:
        model = self._make_model()
        parts: list = []
        if image_bytes:
            parts.append({"mime_type": "image/jpeg", "data": image_bytes})
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
    """Returns RealGeminiClient if GEMINI_API_KEY is set, otherwise MockAIClient."""
    from app.config import get_settings
    s = get_settings()
    if s.gemini_api_key:
        model = s.gemini_model or "gemini-1.5-flash"
        return RealGeminiClient(s.gemini_api_key, model)
    logger.warning("GEMINI_API_KEY not set — using MockAIClient (demo mode)")
    return MockAIClient()
