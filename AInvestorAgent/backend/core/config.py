# backend/core/config.py
from __future__ import annotations

from functools import lru_cache

# --- 兼容导入：优先 v2，失败再回退到 v1 ---
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
    _V2 = True
except Exception:
    # Pydantic v1 回退
    from pydantic import BaseSettings  # type: ignore
    _V2 = False


class Settings(BaseSettings):
    # 保留你原有字段与默认值
    ALPHAVANTAGE_KEY: str = "OSQ403SM4KEOHQSQ"
    DB_URL: str | None = None

    if _V2:
        # v2 写法
        model_config = SettingsConfigDict(
            env_file=".env",
            extra="ignore",
        )
    else:
        # v1 写法
        class Config:
            env_file = ".env"
            extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
