"""小程序端：管理员绑定（绑定码）与现场创建培训。"""

from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import brigade_filter_brigade_id, get_current_mp_admin, get_current_person_token
from app.models import AdminRole, AdminUser, AdminWxBindCode, Brigade, District, Organization, Person
from app.models import TrainingAttendance, TrainingSession
from app.routers.admin import _build_quick_training_out, create_training_quick
from app.routers.admin import stats_by_district, stats_orgs_by_district, stats_persons_by_organization, stats_types_by_district
from app.schemas import (
    DistrictOut,
    MpAdminMeOut,
    MpOrgListItem,
    MpWxBindIn,
    MpWxBindOut,
    QuickTrainingCreate,
    QuickTrainingOut,
    StatsDistrictItem,
    StatsOrgInDistrictItem,
    StatsPersonItem,
    StatsPersonTrainingItem,
    StatsTypeInDistrictItem,
    TrainingSessionPatch,
    TrainingSessionOut,
)
from app.training_activity import deactivate_expired_sessions

router = APIRouter(prefix="/api/mp/admin", tags=["mp-admin"])

BIND_CODE_TTL_MINUTES = 15


def _brigade_name(db: Session, brigade_id: Optional[int]) -> Optional[str]:
    if not brigade_id:
        return None
    b = db.get(Brigade, brigade_id)
    return b.name if b else None


@router.post("/wx-bind", response_model=MpWxBindOut)
def mp_wx_bind(
    body: MpWxBindIn,
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    if not person.openid or person.openid.startswith("wxoa:"):
        raise HTTPException(400, "请使用微信小程序登录后再绑定")

    existing = (
        db.query(AdminUser)
        .filter(AdminUser.wx_openid == person.openid, AdminUser.is_active.is_(True))
        .first()
    )
    if existing:
        return MpWxBindOut(
            admin_username=existing.username,
            admin_role=existing.role.value,
            admin_brigade_name=_brigade_name(db, existing.brigade_id),
        )

    code = body.code.strip()
    row = db.query(AdminWxBindCode).filter(AdminWxBindCode.code == code).first()
    if not row:
        raise HTTPException(400, "绑定码无效或已过期，请在网站重新生成")
    if row.failed_attempts >= 5:
        raise HTTPException(400, "输入错误次数过多，请在网站重新生成绑定码")
    if row.used_at is not None or row.expires_at <= datetime.utcnow():
        row.failed_attempts += 1
        db.commit()
        raise HTTPException(400, "绑定码无效或已过期，请在网站重新生成")

    admin = db.get(AdminUser, row.admin_user_id)
    if not admin or not admin.is_active:
        row.failed_attempts += 1
        db.commit()
        raise HTTPException(400, "目标管理员账号不可用")

    other = (
        db.query(AdminUser)
        .filter(AdminUser.wx_openid == person.openid, AdminUser.id != admin.id)
        .first()
    )
    if other:
        row.failed_attempts += 1
        db.commit()
        raise HTTPException(400, "该微信已绑定其他管理员账号")

    if admin.wx_openid and admin.wx_openid != person.openid:
        row.failed_attempts += 1
        db.commit()
        raise HTTPException(400, "该管理员账号已绑定其他微信，请先在网站解除绑定")

    admin.wx_openid = person.openid
    admin.wx_bound_at = datetime.utcnow()
    row.used_at = datetime.utcnow()
    db.commit()
    db.refresh(admin)

    return MpWxBindOut(
        admin_username=admin.username,
        admin_role=admin.role.value,
        admin_brigade_name=_brigade_name(db, admin.brigade_id),
    )


@router.get("/me", response_model=MpAdminMeOut)
def mp_admin_me(
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    return MpAdminMeOut(
        admin_username=admin.username,
        admin_role=admin.role.value,
        admin_brigade_id=admin.brigade_id,
        admin_brigade_name=_brigade_name(db, admin.brigade_id),
    )


@router.get("/districts", response_model=List[DistrictOut])
def mp_admin_districts(
    _: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    return db.query(District).order_by(District.id).all()


@router.get("/stats/by-district", response_model=List[StatsDistrictItem])
def mp_admin_stats_by_district(
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    return stats_by_district(admin, db, start, end)


@router.get("/stats/types-by-district", response_model=List[StatsTypeInDistrictItem])
def mp_admin_stats_types_by_district(
    district_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    return stats_types_by_district(admin, db, district_id, start, end)


@router.get("/stats/orgs-by-district", response_model=List[StatsOrgInDistrictItem])
def mp_admin_stats_orgs_by_district(
    district_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    return stats_orgs_by_district(admin, db, district_id, start, end)


@router.get("/stats/persons-by-organization", response_model=List[StatsPersonItem])
def mp_admin_stats_persons_by_organization(
    organization_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    return stats_persons_by_organization(admin, db, organization_id, start, end)


@router.get("/stats/person-trainings", response_model=List[StatsPersonTrainingItem])
def mp_admin_stats_person_trainings(
    person_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "人员不存在")
    q = (
        db.query(TrainingAttendance, TrainingSession, Organization, District)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == TrainingSession.organization_id)
        .join(District, District.id == Organization.district_id)
        .filter(TrainingAttendance.person_id == person_id)
    )
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    if start:
        q = q.filter(TrainingSession.start_at >= start)
    if end:
        q = q.filter(TrainingSession.start_at < end)
    rows = q.order_by(TrainingSession.start_at.desc()).limit(200).all()
    return [
        StatsPersonTrainingItem(
            session_id=s.id,
            title=s.title,
            start_at=s.start_at,
            duration_minutes=int(a.duration_minutes or 0),
            organization_name=o.name,
            district_name=d.name,
            location=s.location,
        )
        for a, s, o, d in rows
    ]


@router.get("/organizations", response_model=List[MpOrgListItem])
def mp_admin_organizations(
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    district_id: int = Query(..., ge=1),
    q: str = Query(""),
):
    query = db.query(Organization).filter(Organization.district_id == district_id)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        query = query.filter(Organization.brigade_id == bid)
    if q.strip():
        query = query.filter(Organization.name.like(f"%{q.strip()}%"))
    rows = query.order_by(Organization.name).limit(100).all()
    return [MpOrgListItem(id=o.id, name=o.name, org_type=o.org_type.value) for o in rows]


@router.get("/trainings", response_model=List[TrainingSessionOut])
def mp_admin_list_trainings(
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    deactivate_expired_sessions(db)
    q = db.query(TrainingSession)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    return q.order_by(TrainingSession.start_at.desc()).limit(200).all()


@router.post("/trainings/quick", response_model=QuickTrainingOut)
def mp_admin_create_training_quick(
    body: QuickTrainingCreate,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    return create_training_quick(body, admin, db)


@router.get("/trainings/{session_id}/qrcode-info", response_model=QuickTrainingOut)
def mp_admin_training_qrcode(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权访问该培训")
    return _build_quick_training_out(sess, db)


@router.patch("/trainings/{session_id}", response_model=TrainingSessionOut)
def mp_admin_patch_training(
    session_id: int,
    body: TrainingSessionPatch,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作该培训")
    data = body.model_dump(exclude_unset=True)
    if "is_active" in data:
        sess.is_active = bool(data["is_active"])
        if not sess.is_active:
            sess.end_at = datetime.utcnow()
    db.commit()
    db.refresh(sess)
    return sess
