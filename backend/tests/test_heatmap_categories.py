"""Per-category heatmap region tests for _compute_risk_heatmap."""

from app.ai.nodes import _compute_risk_heatmap


def _heatmap(category: str, *, fit_type="regular", brand="standart",
             shoulder="standart", fabric="Pamuklu",
             height_cm=175, weight_kg=70, has_body_image=True):
    return _compute_risk_heatmap(
        body={"shoulder_width_estimate": shoulder},
        garment={
            "category": category,
            "fit_type": fit_type,
            "brand_sizing_tendency": brand,
            "fabric_cues": fabric,
        },
        has_body_image=has_body_image,
        height_cm=height_cm,
        weight_kg=weight_kg,
    )


# ---------------------------------------------------------------------------
# Region set per category
# ---------------------------------------------------------------------------

def test_shirt_returns_upper_body_regions():
    out = _heatmap("shirt")
    regions = [r["region"] for r in out]
    assert regions == ["omuz", "kol", "bel"]


def test_tshirt_falls_back_to_upper_body_regions():
    out = _heatmap("tshirt")
    regions = [r["region"] for r in out]
    assert regions == ["omuz", "kol", "bel"]


def test_jacket_uses_upper_body_regions():
    out = _heatmap("jacket")
    regions = [r["region"] for r in out]
    assert regions == ["omuz", "kol", "bel"]


def test_jeans_returns_lower_body_regions():
    out = _heatmap("jeans", fit_type="slim-cut")
    regions = [r["region"] for r in out]
    assert regions == ["bel", "kalca", "bacak"]


def test_dress_returns_full_silhouette_regions():
    out = _heatmap("dress")
    regions = [r["region"] for r in out]
    assert regions == ["omuz", "bel", "kalca"]


def test_unknown_category_falls_back_to_upper_body():
    out = _heatmap("scarf")  # not in dispatch
    regions = [r["region"] for r in out]
    assert regions == ["omuz", "kol", "bel"]


# ---------------------------------------------------------------------------
# All region dicts carry the required keys
# ---------------------------------------------------------------------------

def test_every_region_has_label_status_reason():
    for cat in ("shirt", "jeans", "dress"):
        for r in _heatmap(cat):
            assert set(r.keys()) >= {"region", "label_tr", "status", "reason_tr"}
            assert r["status"] in ("low", "medium", "high")
            assert r["label_tr"]
            assert r["reason_tr"]


# ---------------------------------------------------------------------------
# Body-image cap still applies — no HIGH status without a body image
# ---------------------------------------------------------------------------

def test_jeans_high_status_capped_to_medium_without_body_image():
    # slim-cut + küçük kalıplı + high BMI should produce a HIGH on the
    # kalca region; without a body image it must cap to MEDIUM.
    out = _heatmap(
        "jeans", fit_type="slim-cut", brand="küçük kalıplı",
        fabric="Sert denim, esnek değil",
        height_cm=170, weight_kg=85, has_body_image=False,
    )
    statuses = {r["region"]: r["status"] for r in out}
    assert statuses["kalca"] != "high"
