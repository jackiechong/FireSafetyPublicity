"""小程序端：管理员绑定（绑定码）与现场创建培训。"""

from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import brigade_filter_brigade_id, get_current_mp_admin, get_current_person_token
from app.models import AdminRole, AdminUser, AdminWxBindCode, AdminWxBinding, Brigade, District, Organization, Person
from app.models import TrainingAttendance, TrainingSession
from app.routers.admin import _attendance_org_id, _build_quick_training_out, _org_type_name, create_training_quick
from app.routers.admin import _ensure_training_access
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
        .join(AdminWxBinding, AdminWxBinding.admin_user_id == AdminUser.id)
        .filter(
            AdminWxBinding.wx_openid == person.openid,
            AdminWxBinding.is_active.is_(True),
            AdminUser.is_active.is_(True),
        )
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

    binding = db.query(AdminWxBinding).filter(AdminWxBinding.wx_openid == person.openid).first()
    if binding and binding.is_active and binding.admin_user_id != admin.id:
        row.failed_attempts += 1
        db.commit()
        raise HTTPException(400, "该微信已绑定其他管理员账号")

    if binding:
        binding.admin_user_id = admin.id
        binding.person_id = person.id
        binding.is_active = True
        binding.bound_at = datetime.utcnow()
    else:
        db.add(AdminWxBinding(admin_user_id=admin.id, wx_openid=person.openid, person_id=person.id, bound_at=datetime.utcnow()))
    if not admin.wx_openid:
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
    if district_id == 0:
        return _mp_admin_stats_types_citywide(admin, db, start, end)
    return stats_types_by_district(admin, db, district_id, start, end)


@router.get("/stats/orgs-by-district", response_model=List[StatsOrgInDistrictItem])
def mp_admin_stats_orgs_by_district(
    district_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    if district_id == 0:
        return _mp_admin_stats_orgs_citywide(admin, db, start, end)
    return stats_orgs_by_district(admin, db, district_id, start, end)


def _mp_admin_stats_types_citywide(
    admin: AdminUser,
    db: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[StatsTypeInDistrictItem]:
    bid = brigade_filter_brigade_id(admin)
    q_orgs = db.query(Organization)
    if bid is not None:
        q_orgs = q_orgs.filter(Organization.brigade_id == bid)
    orgs = q_orgs.all()
    org_type_by_id = {o.id: o.org_type for o in orgs}
    att_org_id = _attendance_org_id()
    counts: dict[str, int] = {}
    for org in orgs:
        label = _org_type_name(org.org_type, db)
        counts[label] = counts.get(label, 0) + 1

    q = (
        db.query(
            att_org_id,
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0),
            func.count(func.distinct(TrainingAttendance.person_id)),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .filter(att_org_id.in_(list(org_type_by_id.keys()) or [-1]))
        .group_by(att_org_id)
    )
    if start:
        q = q.filter(TrainingSession.start_at >= start)
    if end:
        q = q.filter(TrainingSession.start_at < end)

    totals: dict[str, dict[str, int]] = {
        label: {"total_minutes": 0, "person_count": 0, "organization_count": count}
        for label, count in counts.items()
    }
    for oid, minutes, persons in q.all():
        label = _org_type_name(org_type_by_id.get(oid), db)
        if label not in totals:
            totals[label] = {"total_minutes": 0, "person_count": 0, "organization_count": 0}
        totals[label]["total_minutes"] += int(minutes or 0)
        totals[label]["person_count"] += int(persons or 0)

    return [
        StatsTypeInDistrictItem(
            org_type=label,
            org_type_name=label,
            total_minutes=values["total_minutes"],
            person_count=values["person_count"],
            organization_count=values["organization_count"],
        )
        for label, values in sorted(totals.items(), key=lambda item: item[0])
    ]


def _mp_admin_stats_orgs_citywide(
    admin: AdminUser,
    db: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[StatsOrgInDistrictItem]:
    bid = brigade_filter_brigade_id(admin)
    att_org_id = _attendance_org_id()
    sub_mins = (
        db.query(
            att_org_id.label("oid"),
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0).label("tm"),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .group_by(att_org_id)
    )
    if start:
        sub_mins = sub_mins.filter(TrainingSession.start_at >= start)
    if end:
        sub_mins = sub_mins.filter(TrainingSession.start_at < end)
    sub_mins = sub_mins.subquery()

    sub_pc = (
        db.query(
            att_org_id.label("oid"),
            func.count(func.distinct(TrainingAttendance.person_id)).label("pc"),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .group_by(att_org_id)
    )
    if start:
        sub_pc = sub_pc.filter(TrainingSession.start_at >= start)
    if end:
        sub_pc = sub_pc.filter(TrainingSession.start_at < end)
    sub_pc = sub_pc.subquery()

    q = (
        db.query(
            Organization.id,
            Organization.name,
            func.coalesce(sub_mins.c.tm, 0),
            func.coalesce(sub_pc.c.pc, 0),
        )
        .select_from(Organization)
        .outerjoin(sub_mins, sub_mins.c.oid == Organization.id)
        .outerjoin(sub_pc, sub_pc.c.oid == Organization.id)
    )
    if bid is not None:
        q = q.filter(Organization.brigade_id == bid)
    rows = q.order_by(func.coalesce(sub_mins.c.tm, 0).desc(), Organization.name).limit(500).all()
    return [
        StatsOrgInDistrictItem(
            organization_id=row[0],
            organization_name=row[1],
            total_minutes=int(row[2] or 0),
            person_count=int(row[3] or 0),
        )
        for row in rows
    ]


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
        .join(Organization, Organization.id == _attendance_org_id())
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
    return [MpOrgListItem(id=o.id, name=o.name, org_type=str(o.org_type)) for o in rows]


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


@router.delete("/trainings/{session_id}", status_code=204)
def mp_admin_delete_training(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_mp_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    _ensure_training_access(sess, admin)
    db.delete(sess)
    db.commit()
