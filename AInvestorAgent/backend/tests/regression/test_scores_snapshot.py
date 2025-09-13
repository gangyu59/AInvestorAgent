# -*- coding: utf-8 -*-
import json, os

SNAP_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
SNAP_FILE = os.path.join(SNAP_DIR, "scores_AAPL.json")

def compute_score(factors: dict) -> float:
    w = {"value": 0.25, "quality": 0.20, "momentum": 0.35, "sentiment": 0.20}
    return 100.0 * sum(w[k] * float(factors[k]) for k in w)

def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol

def test_scores_snapshot(monkeypatch=None):
    actual = {
        "symbol": "AAPL",
        "factors": {"value": 0.52, "quality": 0.61, "momentum": 0.55, "sentiment": 0.40},
    }
    actual["score"] = round(compute_score(actual["factors"]), 6)  # 52.45
    actual["version_tag"] = "v1-baseline"

    # === 若要求更新基线：先写入，直接返回（避免先触发断言） ===
    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        os.makedirs(SNAP_DIR, exist_ok=True)
        with open(SNAP_FILE, "w", encoding="utf-8") as f:
            json.dump(actual, f, ensure_ascii=False, indent=2)
        assert True
        return

    # === 首次无快照：创建并通过 ===
    if not os.path.exists(SNAP_FILE):
        os.makedirs(SNAP_DIR, exist_ok=True)
        with open(SNAP_FILE, "w", encoding="utf-8") as f:
            json.dump(actual, f, ensure_ascii=False, indent=2)
        assert True
        return

    # === 正常比较 ===
    with open(SNAP_FILE, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    assert set(baseline["factors"]) == set(actual["factors"])
    assert approx(float(baseline["score"]), float(actual["score"]), tol=1e-6), \
        f"score changed: baseline={baseline['score']} actual={actual['score']}"
    for k in actual["factors"]:
        assert approx(float(baseline["factors"][k]), float(actual["factors"][k]), tol=1e-6), \
            f"factor {k} changed: baseline={baseline['factors'][k]} actual={actual['factors'][k]}"
