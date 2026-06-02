from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminRole, AdminUser, AdminWxBinding, Person
from app.security import decode_token

security = HTTPBearer(auto_error=False)


def get_current_admin(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db),
) -> AdminUser:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_token(creds.credentials)
        uid = int(payload["sub"])
    except (KeyError, ValueError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = db.get(AdminUser, uid)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户无效")
    return user


def brigade_filter_brigade_id(admin: AdminUser) -> Optional[int]:
    if admin.role == AdminRole.detachment:
        return None
    return admin.brigade_id


def require_detachment_admin(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
) -> AdminUser:
    if admin.role != AdminRole.detachment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅支队管理员可操作")
    return admin


def resolve_mp_admin(db: Session, person: Person) -> AdminUser | None:
    """小程序 openid 是否已绑定启用中的后台管理员账号。"""
    if not person.openid or person.openid.startswith("wxoa:"):
        return None
    return (
        db.query(AdminUser)
        .join(AdminWxBinding, AdminWxBinding.admin_user_id == AdminUser.id)
        .filter(
            AdminWxBinding.wx_openid == person.openid,
            AdminWxBinding.is_active.is_(True),
            AdminUser.is_active.is_(True),
        )
        .first()
    )


def get_current_person_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db),
) -> Person:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("typ") != "mp":
            raise ValueError("wrong type")
        pid = int(payload["sub"])
    except (KeyError, ValueError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    person = db.get(Person, pid)
    if not person:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户无效")
    return person


def get_current_mp_admin(
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
) -> AdminUser:
    admin = resolve_mp_admin(db, person)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="未绑定小程序管理权限，请在网站获取 8 位绑定码后完成绑定",
        )
    return admin
