# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import os, json

router = APIRouter(prefix="/qa", tags=["qa"])

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REPORT_DIR = os.path.join(PROJ, "reports")
JSONL = os.path.join(REPORT_DIR, "test_runs.jsonl")
LATEST = os.path.join(REPORT_DIR, "latest.json")
LAST_HTML = os.path.join(REPORT_DIR, "last_report.html")

@router.get("/test_runs")
def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.exists(JSONL):
        return []
    out = []
    with open(JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    out.reverse()
    return out[:limit]

@router.get("/latest")
def latest():
    if os.path.exists(LATEST):
        with open(LATEST, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="no latest")

@router.get("/last_report")
def last_report():
    # 返回静态报告路径，前端可跳转
    return {
        "exists": os.path.exists(LAST_HTML),
        "path": "/reports/last_report.html",
    }

# 在文件顶部已有 import 基础上继续用
import math

def _compute_score(factors: dict) -> float:
    w = {"value": 0.25, "quality": 0.20, "momentum": 0.35, "sentiment": 0.20}
    return 100.0 * sum(w[k] * float(factors[k]) for k in w)

@router.get("/snapshot")
def snapshot_diff():
    """
    返回回归快照（baseline）与当前计算（actual）的并排对比，便于可视化调试。
    """
    snap_file = os.path.join(PROJ, "backend", "tests", "regression", "snapshots", "scores_AAPL.json")
    # 当前“实际”值（与测试保持一致；后续可替换为真实接口）
    actual = {
        "symbol": "AAPL",
        "factors": {"value": 0.52, "quality": 0.61, "momentum": 0.55, "sentiment": 0.40},
    }
    actual["score"] = round(_compute_score(actual["factors"]), 6)
    actual["version_tag"] = "v1-baseline"

    baseline = None
    if os.path.exists(snap_file):
        with open(snap_file, "r", encoding="utf-8") as f:
            baseline = json.load(f)

    diff = {}
    if baseline:
        diff["score_delta"] = round(actual["score"] - float(baseline.get("score", 0)), 6)
        fk = set(actual["factors"].keys()) | set(baseline.get("factors", {}).keys())
        diff["factors_delta"] = {
            k: round(float(actual["factors"].get(k, 0)) - float(baseline.get("factors", {}).get(k, 0)), 6)
            for k in sorted(fk)
        }

    return {"baseline": baseline, "actual": actual, "diff": diff}
