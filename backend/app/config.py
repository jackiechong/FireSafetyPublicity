from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _default_sqlite_url() -> str:
    """固定到 backend/data/app.db，避免随启动目录不同连到另一份空库。"""
    data_dir = _BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = (data_dir / "app.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = _default_sqlite_url()
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # 微信小程序（正式环境在 .env 中配置）
    wechat_appid: str = ""
    wechat_secret: str = ""

    # 微信公众号「网页授权」(OAuth2)：用于不使用小程序的 H5 签到入口
    # - WECHAT_OA_APPID / WECHAT_OA_SECRET 留空时走开发桩，直接发放伪 openid，方便本地联调
    # - WECHAT_OA_REDIRECT_HOST：必须是公众号后台「网页授权域名」白名单中的 HTTPS 域名
    #   形如 https://fire.example.gov.cn；开发环境可不填，由 fallback 自动用 vite 前端 origin
    wechat_oa_appid: str = ""
    wechat_oa_secret: str = ""
    wechat_oa_redirect_host: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def resolve_sqlite_relative_to_backend(cls, v: str) -> str:
        """若 .env 里写 sqlite:///./data/app.db，仍按 backend 目录解析。"""
        if not isinstance(v, str) or not v.startswith("sqlite:///./"):
            return v
        rel = v.replace("sqlite:///./", "", 1)
        p = (_BACKEND_ROOT / rel).resolve()
        return f"sqlite:///{p.as_posix()}"


settings = Settings()
