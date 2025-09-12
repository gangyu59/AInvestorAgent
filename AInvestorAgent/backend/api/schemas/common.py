# backend/api/schemas/common.py
from pydantic import BaseModel

class Msg(BaseModel):
    ok: bool = True
    message: str = "ok"
