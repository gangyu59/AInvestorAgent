from fastapi import APIRouter

# 不用 prefix，直接声明具体路径，避免二次叠加后路径跑偏
router = APIRouter(tags=["health"])

@router.get("/api/health")
def health_api():
    return {"status": "ok"}

@router.get("/health")
def health_plain():
    return {"status": "ok"}
