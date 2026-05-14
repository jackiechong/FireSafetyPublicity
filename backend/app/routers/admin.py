from datetime import datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import brigade_filter_brigade_id, get_current_admin, require_detachment_admin
from app.models import (
    AdminRole,
    AdminUser,
    Brigade,
    District,
    Organization,
    OrgType,
    Person,
    TrainingAttendance,
    TrainingSession,
)
from app.schemas import (
    AdminAccountCreate,
    AdminAccountOut,
    AdminAccountUpdate,
    AdminLogin,
    AdminPasswordReset,
    AdminUserOut,
    AttendanceAdd,
    BrigadeOut,
    DistrictOut,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    QuickTrainingCreate,
    QuickTrainingOut,
    StatsDistrictItem,
    StatsOrgInDistrictItem,
    StatsPersonItem,
    StatsSearchItem,
    SuggestItem,
    Token,
    TrainingSessionCreate,
    TrainingSessionOut,
    TrainingSessionPatch,
)
from app.config import settings
from app.security import create_access_token, hash_password, verify_password
from app.training_activity import deactivate_expired_sessions

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=Token)
def admin_login(body: AdminLogin, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token(
        user.id,
        {"role": user.role.value, "brigade_id": user.brigade_id},
    )
    return Token(access_token=token)


@router.get("/me", response_model=AdminUserOut)
def admin_me(admin: Annotated[AdminUser, Depends(get_current_admin)]):
    return admin


@router.get("/brigades", response_model=List[BrigadeOut])
def list_brigades(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    q = db.query(Brigade)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(Brigade.id == bid)
    return q.order_by(Brigade.id).all()


@router.get("/districts", response_model=List[DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.query(District).order_by(District.id).all()


def _org_query(admin: AdminUser, db: Session):
    q = db.query(Organization)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(Organization.brigade_id == bid)
    return q


@router.get("/organizations", response_model=List[OrganizationOut])
def list_organizations(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    brigade_id: Optional[int] = None,
    district_id: Optional[int] = None,
    q: Optional[str] = None,
):
    query = _org_query(admin, db)
    if brigade_id is not None:
        if brigade_filter_brigade_id(admin) is not None and brigade_id != brigade_filter_brigade_id(admin):
            raise HTTPException(403, "无权查看该大队")
        query = query.filter(Organization.brigade_id == brigade_id)
    if district_id is not None:
        query = query.filter(Organization.district_id == district_id)
    if q:
        like = f"%{q}%"
        query = query.filter(Organization.name.like(like))
    return query.order_by(Organization.id.desc()).limit(500).all()


@router.get("/organizations/suggest", response_model=List[SuggestItem])
def suggest_organizations(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    keyword: str = Query("", alias="q"),
    limit: int = Query(20, ge=1, le=50),
):
    query = _org_query(admin, db).join(District, Organization.district_id == District.id)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter(Organization.name.like(like))
    rows = query.with_entities(
        Organization.id,
        Organization.name,
        Organization.org_type,
        District.name,
    ).order_by(Organization.name).limit(limit).all()
    return [
        SuggestItem(id=r[0], name=r[1], org_type=r[2], district_name=r[3])
        for r in rows
    ]


@router.post("/organizations", response_model=OrganizationOut)
def create_organization(
    body: OrganizationCreate,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    if admin.role == AdminRole.brigade and body.brigade_id != admin.brigade_id:
        raise HTTPException(403, "只能在本大队下创建单位")
    o = Organization(**body.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.patch("/organizations/{org_id}", response_model=OrganizationOut)
def update_organization(
    org_id: int,
    body: OrganizationUpdate,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    o = db.get(Organization, org_id)
    if not o:
        raise HTTPException(404, "不存在")
    if admin.role == AdminRole.brigade and o.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作")
    data = body.model_dump(exclude_unset=True)
    if admin.role == AdminRole.brigade and "brigade_id" in data and data["brigade_id"] != admin.brigade_id:
        raise HTTPException(403, "不能修改所属大队")
    for k, v in data.items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(
    org_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    o = db.get(Organization, org_id)
    if not o:
        raise HTTPException(404, "不存在")
    if admin.role == AdminRole.brigade and o.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作")
    db.delete(o)
    db.commit()


@router.get("/trainings", response_model=List[TrainingSessionOut])
def list_trainings(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    brigade_id: Optional[int] = None,
    organization_id: Optional[int] = None,
):
    deactivate_expired_sessions(db)
    q = db.query(TrainingSession)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    elif brigade_id is not None:
        q = q.filter(TrainingSession.brigade_id == brigade_id)
    if organization_id is not None:
        q = q.filter(TrainingSession.organization_id == organization_id)
    return q.order_by(TrainingSession.start_at.desc()).limit(500).all()


@router.post("/trainings", response_model=TrainingSessionOut)
def create_training(
    body: TrainingSessionCreate,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    if admin.role == AdminRole.brigade and body.brigade_id != admin.brigade_id:
        raise HTTPException(403, "只能在本大队下创建培训")
    org = db.get(Organization, body.organization_id)
    if not org or org.brigade_id != body.brigade_id:
        raise HTTPException(400, "单位与大队不匹配")
    data = body.model_dump()
    if data.get("end_at") is None and data.get("start_at") is not None:
        data["end_at"] = data["start_at"] + timedelta(minutes=int(data.get("duration_minutes") or 0))
    t = TrainingSession(**data)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/trainings/{session_id}", response_model=TrainingSessionOut)
def patch_training(
    session_id: int,
    body: TrainingSessionPatch,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    deactivate_expired_sessions(db)
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return sess
    if "is_active" in data:
        sess.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(sess)
    return sess


def _build_quick_training_out(s: TrainingSession, db: Session) -> QuickTrainingOut:
    org = db.get(Organization, s.organization_id)
    brigade = db.get(Brigade, s.brigade_id)
    cnt = db.query(TrainingAttendance).filter(TrainingAttendance.session_id == s.id).count()
    # 配置了公众号网页授权域名时，直接生成可在微信内点开的完整 URL
    # 未配置时退化为旧的 session_id=N，让前端 / 小程序自行拼接
    oa_host = (settings.wechat_oa_redirect_host or "").strip().rstrip("/")
    if oa_host:
        from urllib.parse import quote

        qr_payload = f"{oa_host}/api/wxoa/login?session_id={s.id}"
        portal_login_url = f"{oa_host}/api/wxoa/login?next={quote('/h5/checkin', safe='')}"
    else:
        qr_payload = f"session_id={s.id}"
        portal_login_url = None
    return QuickTrainingOut(
        session_id=s.id,
        title=s.title,
        start_at=s.start_at,
        duration_minutes=s.duration_minutes,
        location=s.location,
        organization_id=s.organization_id,
        organization_name=org.name if org else "",
        brigade_id=s.brigade_id,
        brigade_name=brigade.name if brigade else "",
        qr_payload=qr_payload,
        portal_login_url=portal_login_url,
        attendance_count=cnt,
    )


@router.post("/trainings/quick", response_model=QuickTrainingOut)
def create_training_quick(
    body: QuickTrainingCreate,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    """手机看板一键创建培训：标题 + 单位 + 时长，自动按单位推断大队并生成签到二维码内容。"""
    org = db.get(Organization, body.organization_id)
    if not org:
        raise HTTPException(404, "单位不存在")
    if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权在该单位创建培训")
    start = body.start_at or datetime.utcnow()
    sess = TrainingSession(
        title=body.title.strip(),
        brigade_id=org.brigade_id,
        organization_id=org.id,
        start_at=start,
        end_at=start + timedelta(minutes=body.duration_minutes),
        duration_minutes=body.duration_minutes,
        location=(body.location or "").strip() or None,
        remark=None,
        is_active=True,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return _build_quick_training_out(sess, db)


@router.get("/trainings/{session_id}/qrcode-info", response_model=QuickTrainingOut)
def training_qrcode_info(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    """重新拉取某培训的二维码内容与基本信息（手机看板「再看一次」用）。"""
    deactivate_expired_sessions(db)
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权访问")
    return _build_quick_training_out(sess, db)


@router.post("/trainings/{session_id}/attendance", status_code=201)
def add_attendance(
    session_id: int,
    body: AttendanceAdd,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作")

    person: Optional[Person] = None
    if body.person_id:
        person = db.get(Person, body.person_id)
    elif body.phone:
        person = db.query(Person).filter(Person.phone == body.phone).first()
    if not person:
        raise HTTPException(400, "未找到人员，请先在小程序完成实名绑定")

    dur = body.duration_minutes if body.duration_minutes is not None else sess.duration_minutes
    existing = (
        db.query(TrainingAttendance)
        .filter(
            TrainingAttendance.session_id == session_id,
            TrainingAttendance.person_id == person.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "该人员已在本次培训名单中")
    a = TrainingAttendance(session_id=session_id, person_id=person.id, duration_minutes=dur)
    db.add(a)
    db.commit()
    return {"ok": True}


@router.get("/stats/by-district", response_model=List[StatsDistrictItem])
def stats_by_district(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    bid = brigade_filter_brigade_id(admin)

    q_sess = (
        db.query(
            Organization.district_id,
            func.count(TrainingSession.id),
        )
        .select_from(TrainingSession)
        .join(Organization, Organization.id == TrainingSession.organization_id)
    )
    if bid is not None:
        q_sess = q_sess.filter(TrainingSession.brigade_id == bid)
    if start:
        q_sess = q_sess.filter(TrainingSession.start_at >= start)
    if end:
        q_sess = q_sess.filter(TrainingSession.start_at <= end)
    sess_rows = {r[0]: int(r[1]) for r in q_sess.group_by(Organization.district_id).all()}

    q_min = (
        db.query(
            Organization.district_id,
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == TrainingSession.organization_id)
    )
    if bid is not None:
        q_min = q_min.filter(TrainingSession.brigade_id == bid)
    if start:
        q_min = q_min.filter(TrainingSession.start_at >= start)
    if end:
        q_min = q_min.filter(TrainingSession.start_at <= end)
    min_rows = {r[0]: int(r[1] or 0) for r in q_min.group_by(Organization.district_id).all()}

    districts = db.query(District).order_by(District.id).all()
    out: List[StatsDistrictItem] = []
    for d in districts:
        out.append(
            StatsDistrictItem(
                district_id=d.id,
                district_name=d.name,
                total_minutes=min_rows.get(d.id, 0),
                session_count=sess_rows.get(d.id, 0),
            )
        )
    # 保留无参训数据的区县（0 柱），便于与全市区县名单一致
    return out


@router.get("/stats/by-person", response_model=List[StatsPersonItem])
def stats_by_person(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    bid = brigade_filter_brigade_id(admin)
    query = (
        db.query(
            Person.id,
            Person.name,
            Person.phone,
            func.count(TrainingAttendance.id),
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0),
        )
        .select_from(Person)
        .join(TrainingAttendance, TrainingAttendance.person_id == Person.id)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
    )
    if bid is not None:
        query = query.filter(TrainingSession.brigade_id == bid)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Person.name.like(like), Person.phone.like(like)))
    rows = (
        query.group_by(Person.id, Person.name, Person.phone)
        .order_by(func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0).desc())
        .limit(limit)
        .all()
    )
    return [
        StatsPersonItem(
            person_id=r[0],
            name=r[1] or "",
            phone=r[2] or "",
            session_count=int(r[3]),
            total_minutes=int(r[4] or 0),
        )
        for r in rows
    ]


@router.get("/stats/orgs-by-district", response_model=List[StatsOrgInDistrictItem])
def stats_orgs_by_district(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    district_id: int = Query(..., description="区县 ID"),
):
    """某区县内全部单位及培训时长、参训人数；无参训记录的单位时长为 0，仍出现在列表中。

    使用子查询汇总参训数据再与单位左连接，避免多表 outerjoin + group_by 在 SQLite 下漏行或重复聚合。
    """
    bid = brigade_filter_brigade_id(admin)

    sub_mins = (
        db.query(
            TrainingSession.organization_id.label("oid"),
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0).label("tm"),
        )
        .select_from(TrainingSession)
        .join(TrainingAttendance, TrainingAttendance.session_id == TrainingSession.id)
        .group_by(TrainingSession.organization_id)
    ).subquery()

    sub_pc = (
        db.query(
            TrainingSession.organization_id.label("oid"),
            func.count(func.distinct(TrainingAttendance.person_id)).label("pc"),
        )
        .select_from(TrainingSession)
        .join(TrainingAttendance, TrainingAttendance.session_id == TrainingSession.id)
        .group_by(TrainingSession.organization_id)
    ).subquery()

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
        .filter(Organization.district_id == district_id)
    )
    if bid is not None:
        q = q.filter(Organization.brigade_id == bid)
    rows = q.order_by(Organization.name).all()
    return [
        StatsOrgInDistrictItem(
            organization_id=r[0],
            organization_name=r[1],
            total_minutes=int(r[2] or 0),
            person_count=int(r[3] or 0),
        )
        for r in rows
    ]


@router.get("/stats/search-suggest", response_model=List[StatsSearchItem])
def stats_search_suggest(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    q: str = Query("", description="关键词"),
    limit: int = Query(12, ge=1, le=30),
):
    """统计数据页：单位名称、人员姓名/手机联想；人员副标题含所在单位名。"""
    if not q.strip():
        return []
    kw = f"%{q.strip()}%"
    bid = brigade_filter_brigade_id(admin)
    out: List[StatsSearchItem] = []

    oq = _org_query(admin, db).filter(Organization.name.like(kw)).order_by(Organization.name).limit(limit)
    for o in oq.all():
        d = db.get(District, o.district_id)
        dname = d.name if d else ""
        ot = "企业" if o.org_type == OrgType.enterprise else "行业部门"
        out.append(
            StatsSearchItem(
                kind="organization",
                id=o.id,
                title=o.name,
                subtitle=f"{dname} · {ot}",
                organization_id=o.id,
                district_id=o.district_id,
            )
        )

    remain = max(0, limit - len(out))
    if remain > 0:
        if bid is not None:
            pq = (
                db.query(Person, Organization)
                .join(Organization, Person.organization_id == Organization.id)
                .filter(Organization.brigade_id == bid)
                .filter(or_(Person.name.like(kw), Person.phone.like(kw)))
            )
        else:
            pq = (
                db.query(Person, Organization)
                .outerjoin(Organization, Person.organization_id == Organization.id)
                .filter(or_(Person.name.like(kw), Person.phone.like(kw)))
            )
        pq = pq.order_by(Person.name).limit(remain)
        for p, o in pq.all():
            org_name = o.name if o else "未关联单位"
            phone = p.phone or ""
            out.append(
                StatsSearchItem(
                    kind="person",
                    id=p.id,
                    title=(p.name or "未登记姓名").strip() or f"人员#{p.id}",
                    subtitle=f"{org_name} · {phone}",
                    person_id=p.id,
                    organization_id=p.organization_id,
                    district_id=p.district_id,
                )
            )
    return out


@router.get("/stats/persons-by-organization", response_model=List[StatsPersonItem])
def stats_persons_by_organization(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    organization_id: int = Query(..., description="单位 ID"),
):
    """某单位下已参训人员及每人时长、次数。"""
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "单位不存在")
    if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权查看该单位")
    query = (
        db.query(
            Person.id,
            Person.name,
            Person.phone,
            func.count(TrainingAttendance.id),
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0),
        )
        .select_from(TrainingAttendance)
        .join(Person, Person.id == TrainingAttendance.person_id)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .filter(TrainingSession.organization_id == organization_id)
    )
    rows = (
        query.group_by(Person.id, Person.name, Person.phone)
        .order_by(func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0).desc())
        .all()
    )
    return [
        StatsPersonItem(
            person_id=r[0],
            name=r[1] or "",
            phone=r[2] or "",
            session_count=int(r[3]),
            total_minutes=int(r[4] or 0),
        )
        for r in rows
    ]


def _detachment_active_count(db: Session) -> int:
    return (
        db.query(AdminUser)
        .filter(AdminUser.role == AdminRole.detachment, AdminUser.is_active.is_(True))
        .count()
    )


@router.get("/accounts", response_model=List[AdminAccountOut])
def list_admin_accounts(
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AdminUser, Brigade.name)
        .outerjoin(Brigade, AdminUser.brigade_id == Brigade.id)
        .order_by(AdminUser.id)
        .all()
    )
    return [
        AdminAccountOut(
            id=u.id,
            username=u.username,
            role=u.role,
            brigade_id=u.brigade_id,
            brigade_name=bname,
            is_active=u.is_active,
        )
        for u, bname in rows
    ]


@router.post("/accounts", response_model=AdminAccountOut)
def create_admin_account(
    body: AdminAccountCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    if db.query(AdminUser).filter(AdminUser.username == body.username.strip()).first():
        raise HTTPException(400, "用户名已存在")
    brigade_id: Optional[int] = body.brigade_id
    if body.role == AdminRole.brigade:
        if not brigade_id:
            raise HTTPException(400, "大队账号必须选择所属大队")
        if not db.get(Brigade, brigade_id):
            raise HTTPException(400, "大队不存在")
    else:
        brigade_id = None
    u = AdminUser(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        brigade_id=brigade_id,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    bname = db.get(Brigade, u.brigade_id).name if u.brigade_id else None
    return AdminAccountOut(
        id=u.id,
        username=u.username,
        role=u.role,
        brigade_id=u.brigade_id,
        brigade_name=bname,
        is_active=u.is_active,
    )


@router.patch("/accounts/{user_id}", response_model=AdminAccountOut)
def update_admin_account(
    user_id: int,
    body: AdminAccountUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    u = db.get(AdminUser, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    data = body.model_dump(exclude_unset=True)
    new_role = data.get("role", u.role)
    new_active = data.get("is_active", u.is_active)
    new_brigade_id = data.get("brigade_id", u.brigade_id)

    if new_role == AdminRole.brigade:
        if not new_brigade_id:
            raise HTTPException(400, "大队账号必须选择所属大队")
        if not db.get(Brigade, new_brigade_id):
            raise HTTPException(400, "大队不存在")
    else:
        new_brigade_id = None

    if u.role == AdminRole.detachment and u.is_active:
        removing_detachment = new_role != AdminRole.detachment or new_active is False
        if removing_detachment and _detachment_active_count(db) <= 1:
            raise HTTPException(400, "至少需要保留一名在职的支队管理员账号")

    u.role = new_role
    u.brigade_id = new_brigade_id
    u.is_active = new_active
    db.commit()
    db.refresh(u)
    bname = db.get(Brigade, u.brigade_id).name if u.brigade_id else None
    return AdminAccountOut(
        id=u.id,
        username=u.username,
        role=u.role,
        brigade_id=u.brigade_id,
        brigade_name=bname,
        is_active=u.is_active,
    )


@router.post("/accounts/{user_id}/password", status_code=204)
def reset_admin_password(
    user_id: int,
    body: AdminPasswordReset,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    u = db.get(AdminUser, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    u.password_hash = hash_password(body.new_password)
    db.commit()
