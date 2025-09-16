# backend/api/routers/sim.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any
from backend.sim.paper import PaperSim, SimConfig

router = APIRouter(prefix="/sim", tags=["sim"])
_sim = PaperSim(SimConfig(tcost=0.001))

class StepReq(BaseModel):
    orders: List[Dict[str, Any]]
    rel_returns: Dict[str, float]

@router.post("/step")
def step(req: StepReq):
    out = _sim.step(req.orders, req.rel_returns)
    return {"ok": True, "data": out}

class RunReq(BaseModel):
    days: List[Dict[str, Any]]  # [{orders:[...], rel_returns:{...}}, ...]

@router.post("/run")
def run(req: RunReq):
    nav = []; turn = []
    for d in req.days:
        o = d.get("orders", []); r = d.get("rel_returns", {})
        out = _sim.step(o, r)
        nav.append(out["nav"]); turn.append(out["turnover"])
    return {"ok": True, "data": {"nav": nav, "turnover": turn}}
