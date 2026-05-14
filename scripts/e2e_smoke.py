"""Quick end-to-end smoke test against a running backend (DEMO_MODE)."""

import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _form(path: str, fields: dict) -> dict:
    """POST form-urlencoded fields (FastAPI Form(...) endpoints)."""
    import urllib.parse
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _multipart_analyze(user_id: str, png: bytes) -> dict:
    boundary = "----HIWALOYSMOKE"
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="user_id"\r\n\r\n')
    parts.append(user_id.encode() + b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        b'Content-Disposition: form-data; name="garment_image"; filename="t.png"\r\n'
    )
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(png)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + "/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def main() -> int:
    print("[1/4] POST /profile")
    p = _form("/profile", {
        "height_cm": 175,
        "weight_kg": 70,
        "fit_preference": "regular",
    })
    uid = p["user_id"]
    print("   user_id:", uid)
    assert uuid.UUID(uid)
    assert p["height_cm"] == 175

    print("[2/4] POST /analyze")
    a = _multipart_analyze(uid, PNG)
    aid = a["analysis_id"]
    print("   analysis_id:", aid)
    print("   recommended_size:", a.get("recommended_size"))
    print("   confidence_pct:", a.get("confidence_pct"))
    print("   risk_level_tr:", a.get("risk_level_tr"))
    print("   explanation_tr:", (a.get("explanation_tr") or "")[:120])
    print("   uncertainty_tr:", (a.get("uncertainty_tr") or "")[:120])
    print("   community_insights_tr:",
          (a.get("community_insights_tr") or [None])[:1])
    assert a["recommended_size"] is not None, "no size recommendation"
    assert a["explanation_tr"], "explanation_tr empty"
    assert a["risk_level_tr"], "risk_level_tr empty"

    print("[3/4] GET /history/{uid}")
    with urllib.request.urlopen(BASE + f"/history/{uid}", timeout=15) as r:
        hist = json.loads(r.read())
    items = hist["items"]
    print("   entries:", hist["total"])
    assert any(e["analysis_id"] == aid for e in items), "analysis not in history"

    print("[4/4] GET /history/{uid}/{aid}")
    with urllib.request.urlopen(BASE + f"/history/{uid}/{aid}", timeout=15) as r:
        detail = json.loads(r.read())
    print("   recommended_size:", detail.get("recommended_size"))
    assert detail["recommended_size"] == a["recommended_size"]

    print("\nE2E_OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
        sys.exit(2)
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        sys.exit(3)
