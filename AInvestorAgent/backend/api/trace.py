from fastapi import APIRouter, HTTPException
from backend.storage import db, models

router = APIRouter(prefix="/trace", tags=["trace"])

@router.get("/{trace_id}")
def get_trace(trace_id: str):
    with db.session_scope() as s:
        rec = s.get(models.TraceRecord, trace_id)
        if not rec: raise HTTPException(404, "trace not found")
        return {"trace_id": rec.trace_id, "scene": rec.scene,
                "context": rec.context, "trace": rec.trace, "created_at": rec.created_at.isoformat()}

@router.get("/latest/{scene}")
def latest(scene: str):
    with db.session_scope() as s:
        rec = s.query(models.TraceRecord)\
               .filter(models.TraceRecord.scene==scene)\
               .order_by(models.TraceRecord.created_at.desc()).first()
        if not rec: raise HTTPException(404, "no record")
        return {"trace_id": rec.trace_id, "scene": rec.scene,
                "context": rec.context, "trace": rec.trace, "created_at": rec.created_at.isoformat()}
