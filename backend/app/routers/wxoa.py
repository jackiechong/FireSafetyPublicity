"""微信公众号「网页授权」(OAuth2) 登录入口。

流程（生产）：
  1. 本场培训二维码：用户在微信内打开 `https://<host>/api/wxoa/login?session_id=N`
  2. 通用入口（先登录再自选活动场次）：`https://<host>/api/wxoa/login?next=/h5/checkin`（next 需 urlencode）
  3. 后端 302 跳转到 `https://open.weixin.qq.com/connect/oauth2/authorize?...`
  4. 微信回调到 `https://<host>/api/wxoa/callback?code=...&state=...`
  5. 后端用 code 换 openid，find/create `Person`（openid 前缀 `wxoa:`），签发 JWT
  6. 302 跳到 H5：`/h5/checkin?token=...&session_id=N`；无 session_id 时进入 `/h5/checkin` 由页面拉活动场次列表
     （首次未填资料则跳 `/h5/bind`）

开发模式（未配置 WECHAT_OA_APPID/SECRET）：
  - 跳过微信，`/login` 直接 302 到 `/callback?code=DEV...` 走桩；
  - 重定向均使用相对 URL，浏览器会自动续到当前 origin（dev 是 vite 5173；生产是公网域名）。
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Person
from app.security import create_access_token
from app.wechat import oa_code_to_openid

router = APIRouter(prefix="/api/wxoa", tags=["wxoa"])


# 在 Person.openid 字段前缀这个值用于和小程序的 openid 区分开
OA_OPENID_PREFIX = "wxoa:"

# state 在 WeChat OAuth 中限制 128 字节，用 HMAC 签名的紧凑串而不是 JWT
STATE_TTL_SEC = 600


def _make_state(next_path: str, session_id: int) -> str:
    payload = json.dumps([next_path or "", int(session_id or 0), int(time.time())], separators=(",", ":"))
    sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
    blob = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{blob}.{sig}"


def _read_state(token: str) -> tuple[str, int]:
    try:
        blob, sig = token.split(".", 1)
        padded = blob + "=" * (-len(blob) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        expected = hmac.new(
            settings.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad sig")
        next_path, session_id, ts = json.loads(payload)
        if time.time() - int(ts) > STATE_TTL_SEC:
            raise ValueError("expired")
        np = next_path if isinstance(next_path, str) and next_path.startswith("/") else "/h5/checkin"
        return np, int(session_id or 0)
    except Exception:
        raise HTTPException(400, "登录状态无效或已过期，请重新扫码")


def _profile_complete(p: Person) -> bool:
    return bool(p.name and p.phone and p.district_id and p.organization_id)


def _public_callback_host(req: Request) -> str:
    """生产用 env，开发兜底用 Origin/Referer 推断前端域名。"""
    host = (settings.wechat_oa_redirect_host or "").strip().rstrip("/")
    if host:
        return host
    for header in ("origin", "referer"):
        val = req.headers.get(header)
        if not val:
            continue
        try:
            parsed = urllib.parse.urlparse(val)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
    return f"{req.url.scheme}://{req.url.netloc}"


@router.get("/login")
def wxoa_login(
    req: Request,
    session_id: int = Query(0, description="可选：扫码即签到的培训 id"),
    next: Optional[str] = Query("/h5/checkin", description="授权后跳转到的 H5 路径"),
):
    next_path = (next or "/h5/checkin").strip()
    if not next_path.startswith("/"):
        next_path = "/h5/checkin"
    state = _make_state(next_path, session_id)
    state_q = urllib.parse.quote(state, safe="")

    # 开发桩：跳过微信，直接走 callback；用相对 URL，浏览器在原 origin 上继续
    if not settings.wechat_oa_appid or not settings.wechat_oa_secret:
        fake_code = f"DEV{int(session_id or 0)}"
        return RedirectResponse(
            url=f"/api/wxoa/callback?code={fake_code}&state={state_q}",
            status_code=302,
        )

    callback_url = f"{_public_callback_host(req)}/api/wxoa/callback"
    encoded_redirect = urllib.parse.quote(callback_url, safe="")
    wx_url = (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={settings.wechat_oa_appid}"
        f"&redirect_uri={encoded_redirect}"
        f"&response_type=code&scope=snsapi_base"
        f"&state={state_q}#wechat_redirect"
    )
    return RedirectResponse(url=wx_url, status_code=302)


@router.get("/callback")
async def wxoa_callback(
    code: str = Query(""),
    state: str = Query(""),
    db: Session = Depends(get_db),
):
    if not code or not state:
        raise HTTPException(400, "缺少 code 或 state")
    next_path, session_id = _read_state(state)

    try:
        wx = await oa_code_to_openid(code)
        openid = wx.get("openid")
        if not openid:
            raise ValueError("微信未返回 openid")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"微信授权失败: {e!s}")

    full_openid = f"{OA_OPENID_PREFIX}{openid}"
    person = db.query(Person).filter(Person.openid == full_openid).first()
    if not person:
        person = Person(openid=full_openid)
        db.add(person)
        db.commit()
        db.refresh(person)

    token = create_access_token(person.id, {"typ": "mp"})

    target_path = next_path if _profile_complete(person) else "/h5/bind"
    parts = [f"token={urllib.parse.quote(token, safe='')}"]
    if session_id:
        parts.append(f"session_id={session_id}")
    sep = "&" if "?" in target_path else "?"
    target_url = f"{target_path}{sep}{'&'.join(parts)}"
    # 相对 URL：浏览器自动续到当前 origin（生产=公网域名，开发=vite 5173）
    return RedirectResponse(url=target_url, status_code=302)
