"""
Drive the HIWALOY pipeline like a real user would.

Picks two distinct personas, creates profiles, uploads a fake-but-valid
garment PNG, and prints exactly what the 6-node LangGraph pipeline returns
in Turkish — verbatim.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:8000/api/v1"
# 8-byte PNG signature + 64 bytes of padding — passes the magic-byte validator.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# ---------- HTTP helpers ----------

def post_form(path: str, fields: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def post_analyze(user_id: str, png: bytes) -> dict:
    boundary = "----TRYSYSTEM"
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="user_id"\r\n\r\n',
        user_id.encode() + b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="garment_image"; filename="garment.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        png,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + "/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


# ---------- Pretty printer ----------

def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def section(label: str) -> None:
    print()
    print(f"--- {label} ---")


def run_persona(name: str, profile: dict) -> dict:
    banner(f"Persona: {name}")
    print(f"  Inputs (girdiler): {profile}")

    section("[1] POST /api/v1/profile")
    p = post_form("/profile", profile)
    print(f"  user_id        = {p['user_id']}")
    print(f"  has_body_image = {p['has_body_image']}")

    section("[2] POST /api/v1/analyze (garment_image: dummy PNG)")
    a = post_analyze(p["user_id"], PNG)
    print(f"  analysis_id        = {a['analysis_id']}")
    print(f"  garment_image_ref  = {a['garment_image_ref']}")

    section("[3] Pipeline output (Turkish, verbatim from final formatter node)")
    rec  = a.get("recommended_size")
    pct  = a.get("confidence_pct")
    risk = a.get("risk_level_tr")
    expl = a.get("explanation_tr") or ""
    unc  = a.get("uncertainty_tr") or ""
    factors = a.get("risk_factors_tr") or []
    insights = a.get("community_insights_tr") or []

    print(f"  Önerilen Beden     : {rec}")
    print(f"  Güven Skoru        : {pct}")
    print(f"  Risk Seviyesi      : {risk}")
    print(f"  Açıklama           : {expl}")
    print(f"  Belirsizlik notu   : {unc}")
    if factors:
        print("  Risk Faktörleri    :")
        for f in factors:
            print(f"     - {f}")
    print("  Topluluk İçgörüleri:")
    for ins in insights:
        print(f"     • {ins}")
    return a


def main() -> int:
    personas = [
        ("Cem · uzun ve zayıf",  {"height_cm": 188, "weight_kg": 70, "fit_preference": "slim"}),
        ("Aslı · ortalama, oversize sever", {"height_cm": 165, "weight_kg": 62, "fit_preference": "oversize"}),
    ]
    results = []
    for name, profile in personas:
        results.append(run_persona(name, profile))

    banner("Yan yana karşılaştırma")
    print(f"  {'Persona':<32} {'Beden':<8} {'Güven':<8} {'Risk':<14}")
    for (name, profile), r in zip(personas, results):
        print(
            f"  {name:<32} "
            f"{r.get('recommended_size') or '—':<8} "
            f"{r.get('confidence_pct') or '—':<8} "
            f"{r.get('risk_level_tr') or '—':<14}"
        )
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
