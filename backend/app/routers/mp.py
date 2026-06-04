from typing import Annotated, List

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_person_token, resolve_mp_admin
from app.models import Brigade, District, JobTitleOption, Organization, OrgTypeOption, Person, TrainingAttendance, TrainingSession
from app.schemas import (
    DistrictOut,
    MpActiveTrainingItem,
    MpCheckinIn,
    MpCheckinOut,
    MpLoginIn,
    MpLoginOut,
    MpOrganizationCreateIn,
    MpOrgListItem,
    MpPersonOut,
    MpProfileIn,
    MpTrainingItem,
    DictionaryOptionOut,
)
from app.security import create_access_token
from app.training_activity import deactivate_expired_sessions, effective_end_utc, session_allows_checkin, today_bounds_utc
from app.wechat import code_to_session

router = APIRouter(prefix="/api/mp", tags=["miniprogram"])


def _admin_fields(person: Person, db: Session) -> dict:
    admin = resolve_mp_admin(db, person)
    if not admin:
        return {
            "is_admin": False,
            "admin_role": None,
            "admin_brigade_id": None,
            "admin_username": None,
            "admin_brigade_name": None,
        }
    bname = None
    if admin.brigade_id:
        b = db.get(Brigade, admin.brigade_id)
        bname = b.name if b else None
    return {
        "is_admin": True,
        "admin_role": admin.role.value,
        "admin_brigade_id": admin.brigade_id,
        "admin_username": admin.username,
        "admin_brigade_name": bname,
    }


def _build_person_out(person: Person, db: Session) -> MpPersonOut:
    dname = oname = None
    if person.district_id:
        dd = db.get(District, person.district_id)
        dname = dd.name if dd else None
    if person.organization_id:
        oo = db.get(Organization, person.organization_id)
        oname = oo.name if oo else None
    return MpPersonOut(
        name=person.name,
        phone=person.phone,
        district_id=person.district_id,
        district_name=dname,
        organization_id=person.organization_id,
        organization_name=oname,
        job_title=person.job_title,
        wechat_bound=True,
        **_admin_fields(person, db),
    )


def _profile_complete(p: Person) -> bool:
    return bool(
        p.name
        and p.phone
        and p.district_id
        and p.organization_id
    )


def _require_complete_profile(person: Person) -> None:
    if not _profile_complete(person):
        raise HTTPException(409, "请先完成单位和姓名登记")


@router.post("/login", response_model=MpLoginOut)
async def mp_login(body: MpLoginIn, db: Session = Depends(get_db)):
    try:
        wx = await code_to_session(body.code)
        openid = wx["openid"]
    except Exception as e:
        raise HTTPException(400, f"登录失败: {e!s}")

    person = db.query(Person).filter(Person.openid == openid).first()
    if not person:
        person = Person(openid=openid)
        db.add(person)
        db.commit()
        db.refresh(person)

    need_profile = not _profile_complete(person)
    token = create_access_token(person.id, {"typ": "mp"})
    return MpLoginOut(token=token, need_profile=need_profile, **_admin_fields(person, db))


@router.get("/me", response_model=MpPersonOut)
def mp_me(
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    return _build_person_out(person, db)


@router.get("/districts", response_model=List[DistrictOut])
def mp_districts(
    _: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    return db.query(District).order_by(District.id).all()


@router.get("/org-types", response_model=List[DictionaryOptionOut])
def mp_org_types(
    _: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    rows = db.query(OrgTypeOption).filter(OrgTypeOption.is_active.is_(True)).order_by(OrgTypeOption.sort_order, OrgTypeOption.id).all()
    return [DictionaryOptionOut(id=o.id, code=o.code, name=o.name, sort_order=o.sort_order, is_active=o.is_active) for o in rows]


@router.get("/job-titles", response_model=List[DictionaryOptionOut])
def mp_job_titles(
    _: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    rows = db.query(JobTitleOption).filter(JobTitleOption.is_active.is_(True)).order_by(JobTitleOption.sort_order, JobTitleOption.id).all()
    return [DictionaryOptionOut(id=o.id, name=o.name, sort_order=o.sort_order, is_active=o.is_active) for o in rows]


@router.get("/organizations", response_model=List[MpOrgListItem])
def mp_organizations(
    _: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
    district_id: int = Query(..., description="区县 ID"),
    q: str = Query("", description="单位名称关键词"),
):
    query = db.query(Organization).filter(Organization.district_id == district_id)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(Organization.name.like(like))
    district = db.get(District, district_id)
    priority_names = []
    if district and district.name == "龙港区":
        priority_names = ["葫芦岛市消防救援支队", "龙港区消防救援大队"]
    elif district:
        priority_names = [f"{district.name}消防救援大队"]
    priority_order = case(
        {name: idx for idx, name in enumerate(priority_names)},
        value=Organization.name,
        else_=len(priority_names),
    )
    rows = query.order_by(priority_order, Organization.name).limit(100).all()
    return [MpOrgListItem(id=o.id, name=o.name, org_type=str(o.org_type)) for o in rows]


# 小程序自助创建单位时，按所在区县选择默认承接大队
_DISTRICT_DEFAULT_BRIGADE_CODE: dict[str, str] = {
    "连山区": "LS",
    "龙港区": "LG",
    "南票区": "NP",
    "绥中县": "SZ",
    "建昌县": "JC",
    "兴城市": "XC",
    "杨家杖子经济开发区": "YJJKQ",
    "经济开发区": "JJKFQ",
    "高新技术开发区": "GXJSQ",
}


@router.post("/organizations", response_model=MpOrgListItem)
def mp_create_organization(
    body: MpOrganizationCreateIn,
    _: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    """小程序绑定页选「其他单位」时使用：自动按区县挂到默认大队下。"""
    district = db.get(District, body.district_id)
    if not district:
        raise HTTPException(400, "区县不存在")
    name = body.name.strip()
    dup = (
        db.query(Organization)
        .filter(Organization.district_id == district.id, Organization.name == name)
        .first()
    )
    if dup:
        return MpOrgListItem(id=dup.id, name=dup.name, org_type=str(dup.org_type))
    if not db.query(OrgTypeOption).filter(OrgTypeOption.code == body.org_type, OrgTypeOption.is_active.is_(True)).first():
        raise HTTPException(400, "单位类型不存在或已停用")

    code = _DISTRICT_DEFAULT_BRIGADE_CODE.get(district.name)
    brigade = (
        db.query(Brigade).filter(Brigade.code == code).first() if code else None
    ) or db.query(Brigade).order_by(Brigade.id).first()
    if not brigade:
        raise HTTPException(500, "系统未配置消防大队")

    org = Organization(
        name=name,
        org_type=body.org_type,
        brigade_id=brigade.id,
        district_id=district.id,
        remark="MP_SELF_REGISTER",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return MpOrgListItem(id=org.id, name=org.name, org_type=str(org.org_type))


@router.post("/profile", response_model=MpPersonOut)
def mp_profile(
    body: MpProfileIn,
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    dup = db.query(Person).filter(Person.phone == body.phone, Person.id != person.id).first()
    if dup:
        raise HTTPException(400, "该手机号已被其他账号绑定")

    if not db.get(District, body.district_id):
        raise HTTPException(400, "区县不存在")
    org = db.get(Organization, body.organization_id)
    if not org or org.district_id != body.district_id:
        raise HTTPException(400, "所选单位与区县不一致，或单位不存在")

    person.name = body.name.strip()
    person.phone = body.phone.strip()
    person.district_id = body.district_id
    person.organization_id = body.organization_id
    person.job_title = body.job_title.strip() if body.job_title else None
    db.commit()
    db.refresh(person)
    return _build_person_out(person, db)


@router.get("/active-trainings", response_model=List[MpActiveTrainingItem])
def mp_active_trainings(
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    """今天全市未结束且未手动结束的活动场次，供人员选择加入。"""
    _require_complete_profile(person)
    deactivate_expired_sessions(db)
    now = datetime.utcnow()
    day_start, day_end = today_bounds_utc(now)
    rows = (
        db.query(TrainingSession, Organization, District)
        .join(Organization, Organization.id == TrainingSession.organization_id)
        .join(District, District.id == Organization.district_id)
        .filter(TrainingSession.is_active.is_(True))
        .filter(TrainingSession.start_at >= day_start)
        .filter(TrainingSession.start_at < day_end)
        .order_by(TrainingSession.start_at.desc())
        .limit(300)
        .all()
    )
    out: list[MpActiveTrainingItem] = []
    for sess, org, dist in rows:
        if effective_end_utc(sess) <= now:
            continue
        same = bool(person.district_id and org.district_id == person.district_id)
        out.append(
            MpActiveTrainingItem(
                session_id=sess.id,
                title=sess.title,
                start_at=sess.start_at,
                duration_minutes=int(sess.duration_minutes or 0),
                location=sess.location,
                organization_name=org.name,
                district_name=dist.name,
                district_id=dist.id,
                same_district=same,
            )
        )
    out.sort(key=lambda x: (0 if x.same_district else 1, -x.start_at.timestamp()))
    return out


@router.post("/checkin", response_model=MpCheckinOut)
def mp_checkin(
    body: MpCheckinIn,
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    _require_complete_profile(person)
    sess = db.get(TrainingSession, body.session_id)
    if not sess:
        raise HTTPException(404, "培训不存在或已被删除")

    existing = (
        db.query(TrainingAttendance)
        .filter(
            TrainingAttendance.session_id == sess.id,
            TrainingAttendance.person_id == person.id,
        )
        .first()
    )
    already_checked = existing is not None
    if not existing:
        ok, msg = session_allows_checkin(sess, db)
        if not ok:
            raise HTTPException(400, msg)
        existing = TrainingAttendance(
            session_id=sess.id,
            person_id=person.id,
            duration_minutes=int(sess.duration_minutes or 0),
        )
        db.add(existing)
        db.commit()

    org = db.get(Organization, sess.organization_id)
    return MpCheckinOut(
        ok=True,
        already_checked=already_checked,
        session_id=sess.id,
        title=sess.title,
        start_at=sess.start_at,
        location=sess.location,
        duration_minutes=existing.duration_minutes,
        organization_name=org.name if org else "",
    )


@router.get("/trainings", response_model=List[MpTrainingItem])
def mp_trainings(
    person: Annotated[Person, Depends(get_current_person_token)],
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            TrainingSession.id,
            TrainingSession.title,
            TrainingSession.start_at,
            TrainingAttendance.duration_minutes,
            Organization.name,
            District.name,
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == TrainingSession.organization_id)
        .join(District, District.id == Organization.district_id)
        .filter(TrainingAttendance.person_id == person.id)
        .order_by(TrainingSession.start_at.desc())
        .limit(200)
        .all()
    )
    return [
        MpTrainingItem(
            session_id=r[0],
            title=r[1],
            start_at=r[2],
            duration_minutes=r[3],
            organization_name=r[4],
            district_name=r[5],
        )
        for r in rows
    ]
