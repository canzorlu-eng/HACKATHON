"""
Unit tests for AI client helpers: _detect_mime and _parse.

No network calls. Tests the pure functions directly.
"""

import json
import pytest

from app.ai.client import _detect_mime, RealGeminiClient


# ---------------------------------------------------------------------------
# _detect_mime tests
# ---------------------------------------------------------------------------

PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 16
EMPTY = b""
SHORT = b"\x89PNG"  # truncated — less than 8 bytes


class TestDetectMime:
    def test_png_magic_returns_png(self):
        assert _detect_mime(PNG_MAGIC) == "image/png"

    def test_jpeg_bytes_return_jpeg(self):
        assert _detect_mime(JPEG_MAGIC) == "image/jpeg"

    def test_empty_bytes_defaults_to_jpeg(self):
        assert _detect_mime(EMPTY) == "image/jpeg"

    def test_truncated_png_header_returns_jpeg(self):
        # Only 4 bytes — cannot match the 8-byte PNG signature
        assert _detect_mime(SHORT) == "image/jpeg"

    def test_garbage_bytes_defaults_to_jpeg(self):
        assert _detect_mime(b"\x00\x01\x02\x03") == "image/jpeg"

    def test_png_detection_is_not_fooled_by_jpeg_prefix(self):
        # JPEG magic with PNG bytes after — should NOT be png
        mixed = JPEG_MAGIC + PNG_MAGIC
        assert _detect_mime(mixed) == "image/jpeg"


# ---------------------------------------------------------------------------
# RealGeminiClient._parse tests (no API key / model required)
# ---------------------------------------------------------------------------

def _make_parser():
    """Instantiate RealGeminiClient with a fake key to test _parse only."""
    # Patch generativeai import to avoid real SDK init
    import types, sys
    fake_genai = types.ModuleType("google.generativeai")
    fake_genai.configure = lambda **_: None
    fake_genai.GenerativeModel = lambda *a, **kw: None
    fake_genai.GenerationConfig = lambda **kw: None
    sys.modules.setdefault("google", types.ModuleType("google"))
    sys.modules["google.generativeai"] = fake_genai

    client = RealGeminiClient.__new__(RealGeminiClient)
    return client


class TestParse:
    def setup_method(self):
        self.parser = _make_parser()

    def test_clean_json_parses(self):
        raw = '{"key": "value"}'
        result = self.parser._parse(raw)
        assert result == {"key": "value"}

    def test_json_with_leading_whitespace(self):
        raw = '  \n{"key": "value"}  '
        result = self.parser._parse(raw)
        assert result == {"key": "value"}

    def test_fenced_json_block_parses(self):
        raw = "```json\n{\"size\": \"M\"}\n```"
        result = self.parser._parse(raw)
        assert result == {"size": "M"}

    def test_fenced_block_without_language_tag(self):
        raw = "```\n{\"size\": \"M\"}\n```"
        result = self.parser._parse(raw)
        assert result == {"size": "M"}

    def test_fenced_block_trailing_fence_stripped(self):
        payload = {"recommended_size": "L", "confidence": 0.8}
        raw = f"```json\n{json.dumps(payload)}\n```"
        result = self.parser._parse(raw)
        assert result["recommended_size"] == "L"
        assert result["confidence"] == pytest.approx(0.8)

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            self.parser._parse("not json at all")

    def test_nested_object_round_trips(self):
        payload = {"a": {"b": [1, 2, 3]}, "c": True}
        raw = json.dumps(payload)
        assert self.parser._parse(raw) == payload

    def test_fenced_block_with_extra_whitespace_inside(self):
        raw = "```json\n\n  {\"x\": 1}\n\n```"
        result = self.parser._parse(raw)
        assert result == {"x": 1}
