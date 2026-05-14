import httpx

from app.config import settings


async def code_to_session(code: str) -> dict:
    """
    微信登录凭证校验。未配置 appid/secret 时返回开发用假数据。
    文档: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
    """
    if not settings.wechat_appid or not settings.wechat_secret:
        return {"openid": f"dev_openid_{code[:16]}", "session_key": "dev", "unionid": None}

    url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={settings.wechat_appid}&secret={settings.wechat_secret}&js_code={code}&grant_type=authorization_code"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    if "errcode" in data and data["errcode"] != 0:
        raise ValueError(data.get("errmsg", "wechat error"))
    return data


async def oa_code_to_openid(code: str) -> dict:
    """公众号网页授权：用 code 换 openid。未配置 appid/secret 走 dev 桩。

    文档: https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Wechat_webpage_authorization.html
    """
    if not settings.wechat_oa_appid or not settings.wechat_oa_secret:
        return {"openid": f"dev_oa_{code[:24]}", "scope": "snsapi_base"}

    url = (
        "https://api.weixin.qq.com/sns/oauth2/access_token"
        f"?appid={settings.wechat_oa_appid}&secret={settings.wechat_oa_secret}"
        f"&code={code}&grant_type=authorization_code"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    if "errcode" in data and data["errcode"] != 0:
        raise ValueError(data.get("errmsg", "wechat oa error"))
    return data
