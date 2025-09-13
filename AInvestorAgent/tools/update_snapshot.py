# tools/update_snapshot.py
import json, os, hashlib
SNAP = os.path.join("AInvestorAgent","backend","tests","regression","snapshots","scores_AAPL.json")
actual = {
  "symbol": "AAPL",
  "factors": {"value": 0.52, "quality": 0.61, "momentum": 0.55, "sentiment": 0.40},
  "score": 100 * (0.25*0.52 + 0.20*0.61 + 0.35*0.55 + 0.20*0.40),
  "version_tag": "v1-baseline-updated"
}
os.makedirs(os.path.dirname(SNAP), exist_ok=True)
with open(SNAP, "w", encoding="utf-8") as f:
    json.dump(actual, f, ensure_ascii=False, indent=2)
print("[ok] snapshot updated:", SNAP)
