import secrets
import io
import zipfile
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import brigade_filter_brigade_id, get_current_admin, require_detachment_admin
from app.models import (
    AdminRole,
    AdminUser,
    AdminWxBindCode,
    AdminWxBinding,
    Brigade,
    District,
    JobTitleOption,
    KnowledgeArticle,
    KnowledgeCategoryOption,
    Organization,
    OrgType,
    OrgTypeOption,
    Person,
    TrainingAttendance,
    TrainingSession,
    TrainingTopicOption,
)
from app.schemas import (
    AdminAccountCreate,
    AdminAccountOut,
    AdminAccountUpdate,
    AdminLogin,
    AdminPasswordReset,
    AdminPersonManageIn,
    AdminPersonOut,
    AdminPersonRebindIn,
    AdminUserOut,
    AdminWxBindCodeOut,
    AdminWxBindingOut,
    AttendanceAdd,
    BrigadeOut,
    DistrictOut,
    DictionaryOptionOut,
    JobTitleOptionCreate,
    JobTitleOptionUpdate,
    KnowledgeArticleCreate,
    KnowledgeArticleOut,
    KnowledgeArticleUpdate,
    KnowledgeCategoryCreate,
    KnowledgeCategoryUpdate,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    OrgTypeOptionCreate,
    OrgTypeOptionUpdate,
    QuickTrainingCreate,
    QuickTrainingOut,
    StatsDistrictItem,
    StatsJobTitleSummary,
    StatsOrgCompletionItem,
    StatsOrgInDistrictItem,
    StatsPersonItem,
    StatsPersonTrainingItem,
    StatsSearchItem,
    StatsTopicSummaryItem,
    StatsTypeInDistrictItem,
    StatsTrainingSummaryItem,
    TrainingAttendancePersonItem,
    SuggestItem,
    Token,
    TrainingSessionCreate,
    TrainingSessionOut,
    TrainingSessionPatch,
    TrainingTopicOptionCreate,
    TrainingTopicOptionUpdate,
)
from app.config import settings
from app.security import create_access_token, hash_password, verify_password
from app.training_activity import deactivate_expired_sessions, end_of_local_day_utc

router = APIRouter(prefix="/api/admin", tags=["admin"])

ORG_TYPE_LABELS = {
    OrgType.emergency: "应急",
    OrgType.education: "教育",
    OrgType.civil_affairs: "民政",
    OrgType.culture_tourism: "文旅",
    OrgType.health: "卫建",
    OrgType.commerce: "商务",
    OrgType.industry_agriculture: "农业农村",
    OrgType.development_reform: "发改",
    OrgType.other_department: "其他部门",
    OrgType.department: "其他部门",
    OrgType.enterprise: "其他部门",
}

DETACHMENT_BRIGADE_CODE = "HLDZD"


def _org_type_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value or "")


def _org_type_labels(db: Session) -> dict[str, str]:
    labels = {_org_type_value(k): v for k, v in ORG_TYPE_LABELS.items()}
    for item in db.query(OrgTypeOption).filter(OrgTypeOption.is_active.is_(True)).all():
        labels[item.code] = item.name
    return labels


def _org_type_name(value, db: Session) -> str:
    code = _org_type_value(value)
    return _org_type_labels(db).get(code, code or "其他部门")


def _slug_code(name: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "_" for ch in name.strip())
    raw = "_".join(part for part in raw.split("_") if part)
    return raw[:48] or f"custom_{secrets.randbelow(1_000_000):06d}"


def _is_detachment_brigade(db: Session, brigade_id: Optional[int]) -> bool:
    if not brigade_id:
        return False
    b = db.get(Brigade, brigade_id)
    return bool(b and b.code == DETACHMENT_BRIGADE_CODE)


def _apply_time_range(query, start: Optional[datetime], end: Optional[datetime]):
    if start:
        query = query.filter(TrainingSession.start_at >= start)
    if end:
        query = query.filter(TrainingSession.start_at < end)
    return query


def _attendance_org_id():
    return func.coalesce(TrainingAttendance.organization_id, TrainingSession.organization_id)


def _ensure_training_access(sess: TrainingSession, admin: AdminUser) -> None:
    if admin.role == AdminRole.brigade and sess.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权操作该培训")


def _attendance_rows_for_session(db: Session, session_id: int) -> list[TrainingAttendancePersonItem]:
    att_org_id = _attendance_org_id()
    rows = (
        db.query(TrainingAttendance, Person, Organization)
        .select_from(TrainingAttendance)
        .join(Person, Person.id == TrainingAttendance.person_id)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .outerjoin(Organization, Organization.id == att_org_id)
        .filter(TrainingAttendance.session_id == session_id)
        .order_by(Organization.name, Person.name, Person.id)
        .all()
    )
    return [
        TrainingAttendancePersonItem(
            index=i,
            person_id=p.id,
            organization_name=o.name if o else "",
            name=p.name or "",
            job_title=p.job_title,
            phone=p.phone or "",
            duration_minutes=int(a.duration_minutes or 0),
            checked_in_at=a.checked_in_at,
        )
        for i, (a, p, o) in enumerate(rows, start=1)
    ]


def _xml_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _xlsx_response(filename: str, headers: list[str], rows: list[list]) -> Response:
    sheet_rows = [headers] + rows
    xml_rows = []
    for r_idx, row in enumerate(sheet_rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{_col_name(c_idx)}{r_idx}"
            text = (
                _xml_text(value)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    quoted = filename.encode("utf-8").decode("latin1", errors="ignore")
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{quoted}"'},
    )


def _read_xlsx_rows(data: bytes) -> list[list[str]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("x:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//x:t", ns)))
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    rows: list[list[str]] = []
    for row in root.findall(".//x:row", ns):
        values: list[str] = []
        for cell in row.findall("x:c", ns):
            ctype = cell.attrib.get("t")
            if ctype == "inlineStr":
                values.append("".join(t.text or "" for t in cell.findall(".//x:t", ns)).strip())
            else:
                v = cell.find("x:v", ns)
                raw = (v.text or "") if v is not None else ""
                if ctype == "s" and raw.isdigit() and int(raw) < len(shared):
                    raw = shared[int(raw)]
                values.append(raw.strip())
        rows.append(values)
    return rows


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
    rows = q.order_by(Brigade.id).all()
    return sorted(rows, key=lambda b: 0 if b.code == DETACHMENT_BRIGADE_CODE else 1)


@router.get("/districts", response_model=List[DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.query(District).order_by(District.id).all()


@router.get("/org-types", response_model=List[DictionaryOptionOut])
def list_org_type_options(
    _: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    q = db.query(OrgTypeOption)
    if not include_inactive:
        q = q.filter(OrgTypeOption.is_active.is_(True))
    rows = q.order_by(OrgTypeOption.sort_order, OrgTypeOption.id).all()
    return [
        DictionaryOptionOut(id=o.id, code=o.code, name=o.name, sort_order=o.sort_order, is_active=o.is_active)
        for o in rows
    ]


@router.post("/org-types", response_model=DictionaryOptionOut)
def create_org_type_option(
    body: OrgTypeOptionCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    code = (body.code or _slug_code(name)).strip()
    if db.query(OrgTypeOption).filter(or_(OrgTypeOption.name == name, OrgTypeOption.code == code)).first():
        raise HTTPException(400, "单位类型名称或编码已存在")
    row = OrgTypeOption(code=code, name=name, sort_order=body.sort_order, is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, code=row.code, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.patch("/org-types/{item_id}", response_model=DictionaryOptionOut)
def update_org_type_option(
    item_id: int,
    body: OrgTypeOptionUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(OrgTypeOption, item_id)
    if not row:
        raise HTTPException(404, "单位类型不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        name = data["name"].strip()
        dup = db.query(OrgTypeOption).filter(OrgTypeOption.name == name, OrgTypeOption.id != row.id).first()
        if dup:
            raise HTTPException(400, "单位类型名称已存在")
        row.name = name
    if "sort_order" in data:
        row.sort_order = data["sort_order"]
    if "is_active" in data:
        row.is_active = data["is_active"]
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, code=row.code, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.delete("/org-types/{item_id}", status_code=204)
def delete_org_type_option(
    item_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(OrgTypeOption, item_id)
    if not row:
        raise HTTPException(404, "单位类型不存在")
    if db.query(Organization).filter(Organization.org_type == row.code).first():
        row.is_active = False
    else:
        db.delete(row)
    db.commit()


@router.get("/job-titles", response_model=List[DictionaryOptionOut])
def list_job_title_options(
    _: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    q = db.query(JobTitleOption)
    if not include_inactive:
        q = q.filter(JobTitleOption.is_active.is_(True))
    rows = q.order_by(JobTitleOption.sort_order, JobTitleOption.id).all()
    return [
        DictionaryOptionOut(id=o.id, name=o.name, sort_order=o.sort_order, is_active=o.is_active)
        for o in rows
    ]


@router.post("/job-titles", response_model=DictionaryOptionOut)
def create_job_title_option(
    body: JobTitleOptionCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    if db.query(JobTitleOption).filter(JobTitleOption.name == name).first():
        raise HTTPException(400, "职务名称已存在")
    row = JobTitleOption(name=name, sort_order=body.sort_order, is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.patch("/job-titles/{item_id}", response_model=DictionaryOptionOut)
def update_job_title_option(
    item_id: int,
    body: JobTitleOptionUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(JobTitleOption, item_id)
    if not row:
        raise HTTPException(404, "职务不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        name = data["name"].strip()
        dup = db.query(JobTitleOption).filter(JobTitleOption.name == name, JobTitleOption.id != row.id).first()
        if dup:
            raise HTTPException(400, "职务名称已存在")
        row.name = name
    if "sort_order" in data:
        row.sort_order = data["sort_order"]
    if "is_active" in data:
        row.is_active = data["is_active"]
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.delete("/job-titles/{item_id}", status_code=204)
def delete_job_title_option(
    item_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(JobTitleOption, item_id)
    if not row:
        raise HTTPException(404, "职务不存在")
    if db.query(Person).filter(Person.job_title == row.name).first():
        row.is_active = False
    else:
        db.delete(row)
    db.commit()


@router.get("/training-topics", response_model=List[DictionaryOptionOut])
def list_training_topics(
    _: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    q = db.query(TrainingTopicOption)
    if not include_inactive:
        q = q.filter(TrainingTopicOption.is_active.is_(True))
    rows = q.order_by(TrainingTopicOption.sort_order, TrainingTopicOption.id).all()
    return [DictionaryOptionOut(id=o.id, name=o.name, sort_order=o.sort_order, is_active=o.is_active) for o in rows]


@router.post("/training-topics", response_model=DictionaryOptionOut)
def create_training_topic(
    body: TrainingTopicOptionCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    if db.query(TrainingTopicOption).filter(TrainingTopicOption.name == name).first():
        raise HTTPException(400, "培训主题已存在")
    row = TrainingTopicOption(name=name, sort_order=body.sort_order, is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.patch("/training-topics/{item_id}", response_model=DictionaryOptionOut)
def update_training_topic(
    item_id: int,
    body: TrainingTopicOptionUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(TrainingTopicOption, item_id)
    if not row:
        raise HTTPException(404, "培训主题不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        name = data["name"].strip()
        dup = db.query(TrainingTopicOption).filter(TrainingTopicOption.name == name, TrainingTopicOption.id != row.id).first()
        if dup:
            raise HTTPException(400, "培训主题已存在")
        row.name = name
    if "sort_order" in data:
        row.sort_order = data["sort_order"]
    if "is_active" in data:
        row.is_active = data["is_active"]
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.delete("/training-topics/{item_id}", status_code=204)
def delete_training_topic(
    item_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(TrainingTopicOption, item_id)
    if not row:
        raise HTTPException(404, "培训主题不存在")
    if db.query(TrainingSession).filter(TrainingSession.topic_id == row.id).first():
        row.is_active = False
    else:
        db.delete(row)
    db.commit()


@router.get("/knowledge-categories", response_model=List[DictionaryOptionOut])
def list_knowledge_categories(
    _: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    q = db.query(KnowledgeCategoryOption)
    if not include_inactive:
        q = q.filter(KnowledgeCategoryOption.is_active.is_(True))
    rows = q.order_by(KnowledgeCategoryOption.sort_order, KnowledgeCategoryOption.id).all()
    return [
        DictionaryOptionOut(id=o.id, code=o.code, name=o.name, sort_order=o.sort_order, is_active=o.is_active)
        for o in rows
    ]


@router.post("/knowledge-categories", response_model=DictionaryOptionOut)
def create_knowledge_category(
    body: KnowledgeCategoryCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    code = (body.code or _slug_code(name)).strip()
    if db.query(KnowledgeCategoryOption).filter(or_(KnowledgeCategoryOption.name == name, KnowledgeCategoryOption.code == code)).first():
        raise HTTPException(400, "栏目名称或编码已存在")
    row = KnowledgeCategoryOption(code=code, name=name, sort_order=body.sort_order, is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, code=row.code, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.patch("/knowledge-categories/{item_id}", response_model=DictionaryOptionOut)
def update_knowledge_category(
    item_id: int,
    body: KnowledgeCategoryUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(KnowledgeCategoryOption, item_id)
    if not row:
        raise HTTPException(404, "栏目不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        name = data["name"].strip()
        dup = db.query(KnowledgeCategoryOption).filter(KnowledgeCategoryOption.name == name, KnowledgeCategoryOption.id != row.id).first()
        if dup:
            raise HTTPException(400, "栏目名称已存在")
        row.name = name
    if "sort_order" in data:
        row.sort_order = data["sort_order"]
    if "is_active" in data:
        row.is_active = data["is_active"]
    db.commit()
    db.refresh(row)
    return DictionaryOptionOut(id=row.id, code=row.code, name=row.name, sort_order=row.sort_order, is_active=row.is_active)


@router.delete("/knowledge-categories/{item_id}", status_code=204)
def delete_knowledge_category(
    item_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(KnowledgeCategoryOption, item_id)
    if not row:
        raise HTTPException(404, "栏目不存在")
    if db.query(KnowledgeArticle).filter(KnowledgeArticle.category == row.code).first():
        row.is_active = False
    else:
        db.delete(row)
    db.commit()


@router.get("/knowledge-articles", response_model=List[KnowledgeArticleOut])
def list_knowledge_articles(
    _: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    include_inactive: bool = False,
    category: Optional[str] = None,
):
    q = db.query(KnowledgeArticle)
    if not include_inactive:
        q = q.filter(KnowledgeArticle.is_active.is_(True))
    if category:
        q = q.filter(KnowledgeArticle.category == category)
    return q.order_by(KnowledgeArticle.category, KnowledgeArticle.sort_order, KnowledgeArticle.id).all()


@router.post("/knowledge-articles", response_model=KnowledgeArticleOut)
def create_knowledge_article(
    body: KnowledgeArticleCreate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = KnowledgeArticle(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/knowledge-articles/{article_id}", response_model=KnowledgeArticleOut)
def update_knowledge_article(
    article_id: int,
    body: KnowledgeArticleUpdate,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(KnowledgeArticle, article_id)
    if not row:
        raise HTTPException(404, "内容不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.delete("/knowledge-articles/{article_id}", status_code=204)
def delete_knowledge_article(
    article_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    row = db.get(KnowledgeArticle, article_id)
    if not row:
        raise HTTPException(404, "内容不存在")
    db.delete(row)
    db.commit()


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
    if not db.query(OrgTypeOption).filter(OrgTypeOption.code == body.org_type, OrgTypeOption.is_active.is_(True)).first():
        raise HTTPException(400, "单位类型不存在或已停用")
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
    if "org_type" in data and not db.query(OrgTypeOption).filter(OrgTypeOption.code == data["org_type"], OrgTypeOption.is_active.is_(True)).first():
        raise HTTPException(400, "单位类型不存在或已停用")
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
    if admin.role == AdminRole.brigade:
        raise HTTPException(403, "大队账号不可删除数据")
    db.delete(o)
    db.commit()


@router.get("/trainings", response_model=List[TrainingSessionOut])
def list_trainings(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    brigade_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    q: Optional[str] = None,
):
    deactivate_expired_sessions(db)
    query = db.query(TrainingSession)
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        query = query.filter(TrainingSession.brigade_id == bid)
    elif brigade_id is not None:
        query = query.filter(TrainingSession.brigade_id == brigade_id)
    if organization_id is not None:
        query = query.filter(TrainingSession.organization_id == organization_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(TrainingSession.title.like(like))
    return query.order_by(TrainingSession.start_at.desc()).limit(500).all()


def _default_training_organization(db: Session, brigade_id: int) -> Optional[Organization]:
    brigade = db.get(Brigade, brigade_id)
    if not brigade:
        return None
    if brigade.code == DETACHMENT_BRIGADE_CODE:
        org = db.query(Organization).filter(Organization.name == "葫芦岛市消防救援支队").first()
        if org:
            return org
    org = (
        db.query(Organization)
        .filter(Organization.brigade_id == brigade_id, Organization.remark == "SYSTEM_FIRE_BRIGADE")
        .order_by(Organization.id)
        .first()
    )
    if org:
        return org
    return db.query(Organization).filter(Organization.brigade_id == brigade_id).order_by(Organization.id).first()


@router.post("/trainings", response_model=TrainingSessionOut)
def create_training(
    body: TrainingSessionCreate,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    if admin.role == AdminRole.brigade and body.brigade_id != admin.brigade_id:
        raise HTTPException(403, "只能在本大队下创建培训")
    org = db.get(Organization, body.organization_id) if body.organization_id else _default_training_organization(db, body.brigade_id)
    if not org:
        raise HTTPException(400, "未找到主办单位对应的系统单位")
    if not org or (org.brigade_id != body.brigade_id and not _is_detachment_brigade(db, body.brigade_id)):
        raise HTTPException(400, "单位与大队不匹配")
    if body.topic_id and not db.query(TrainingTopicOption).filter(
        TrainingTopicOption.id == body.topic_id,
        TrainingTopicOption.is_active.is_(True),
    ).first():
        raise HTTPException(400, "培训主题不存在或已停用")
    data = body.model_dump()
    data["organization_id"] = org.id
    if data.get("end_at") is None and data.get("start_at") is not None:
        data["end_at"] = end_of_local_day_utc(data["start_at"])
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
    if "topic_id" in data and data["topic_id"] and not db.query(TrainingTopicOption).filter(
        TrainingTopicOption.id == data["topic_id"],
        TrainingTopicOption.is_active.is_(True),
    ).first():
        raise HTTPException(400, "培训主题不存在或已停用")
    if "is_active" in data:
        sess.is_active = bool(data["is_active"])
        if not sess.is_active:
            sess.end_at = datetime.utcnow()
    for key in ("title", "topic_id", "start_at", "end_at", "duration_minutes", "location", "remark"):
        if key in data:
            setattr(sess, key, data[key])
    if "start_at" in data and "end_at" not in data:
        sess.end_at = end_of_local_day_utc(sess.start_at)
    db.commit()
    db.refresh(sess)
    return sess


@router.post("/trainings/{session_id}/end", response_model=TrainingSessionOut)
def end_training(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    _ensure_training_access(sess, admin)
    sess.is_active = False
    sess.end_at = datetime.utcnow()
    db.commit()
    db.refresh(sess)
    return sess


@router.delete("/trainings/{session_id}", status_code=204)
def delete_training(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    _ensure_training_access(sess, admin)
    db.delete(sess)
    db.commit()


@router.get("/trainings/{session_id}/attendances", response_model=List[TrainingAttendancePersonItem])
def list_training_attendances(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    _ensure_training_access(sess, admin)
    return _attendance_rows_for_session(db, session_id)


def _build_quick_training_out(s: TrainingSession, db: Session) -> QuickTrainingOut:
    org = db.get(Organization, s.organization_id)
    brigade = db.get(Brigade, s.brigade_id)
    topic = db.get(TrainingTopicOption, s.topic_id) if s.topic_id else None
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
        topic_id=s.topic_id,
        topic_name=topic.name if topic else None,
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
    if body.topic_id and not db.query(TrainingTopicOption).filter(
        TrainingTopicOption.id == body.topic_id,
        TrainingTopicOption.is_active.is_(True),
    ).first():
        raise HTTPException(400, "培训主题不存在或已停用")
    start = body.start_at or datetime.utcnow()
    sess = TrainingSession(
        title=body.title.strip(),
        topic_id=body.topic_id,
        brigade_id=org.brigade_id,
        organization_id=org.id,
        start_at=start,
        end_at=end_of_local_day_utc(start),
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
        if admin.role != AdminRole.detachment:
            raise HTTPException(400, "未找到人员，请先在小程序完成实名绑定")
        if not body.phone or not body.name:
            raise HTTPException(400, "支队管理员直接添加人员时需填写姓名和手机号")
        clean_phone = body.phone.strip()
        if not (clean_phone.startswith("1") and len(clean_phone) == 11 and clean_phone.isdigit()):
            raise HTTPException(400, "手机号格式错误")
        org = db.get(Organization, body.organization_id or sess.organization_id)
        if not org:
            raise HTTPException(400, "单位不存在")
        person = Person(
            openid=f"manual_{clean_phone}",
            name=body.name.strip(),
            phone=clean_phone,
            district_id=org.district_id,
            organization_id=org.id,
            job_title=body.job_title.strip() if body.job_title else None,
            person_category=body.person_category.strip() if body.person_category else None,
        )
        db.add(person)
        db.flush()
    elif admin.role == AdminRole.detachment:
        changed = False
        if body.name and not person.name:
            person.name = body.name.strip()
            changed = True
        if body.job_title:
            person.job_title = body.job_title.strip()
            changed = True
        if body.person_category:
            person.person_category = body.person_category.strip()
            changed = True
        if changed:
            db.flush()

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
    attendance_org_id = body.organization_id or person.organization_id or sess.organization_id
    a = TrainingAttendance(
        session_id=session_id,
        person_id=person.id,
        organization_id=attendance_org_id,
        duration_minutes=dur,
    )
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
    att_org_id = _attendance_org_id()

    q_sess = (
        db.query(
            Organization.district_id,
            func.count(func.distinct(TrainingSession.id)),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == att_org_id)
    )
    if bid is not None:
        q_sess = q_sess.filter(TrainingSession.brigade_id == bid)
    if start:
        q_sess = q_sess.filter(TrainingSession.start_at >= start)
    if end:
        q_sess = q_sess.filter(TrainingSession.start_at < end)
    sess_rows = {r[0]: int(r[1]) for r in q_sess.group_by(Organization.district_id).all()}

    q_min = (
        db.query(
            Organization.district_id,
            func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == att_org_id)
    )
    if bid is not None:
        q_min = q_min.filter(TrainingSession.brigade_id == bid)
    if start:
        q_min = q_min.filter(TrainingSession.start_at >= start)
    if end:
        q_min = q_min.filter(TrainingSession.start_at < end)
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
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    """某区县内全部单位及培训时长、参训人数；无参训记录的单位时长为 0，仍出现在列表中。

    使用子查询汇总参训数据再与单位左连接，避免多表 outerjoin + group_by 在 SQLite 下漏行或重复聚合。
    """
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


@router.get("/stats/types-by-district", response_model=List[StatsTypeInDistrictItem])
def stats_types_by_district(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    district_id: int = Query(..., description="区县 ID"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    """某区县内按单位类型汇总培训时长、人数和单位数量。"""
    bid = brigade_filter_brigade_id(admin)
    q_orgs = db.query(Organization).filter(Organization.district_id == district_id)
    if bid is not None:
        q_orgs = q_orgs.filter(Organization.brigade_id == bid)
    orgs = q_orgs.all()
    org_type_by_id = {o.id: o.org_type for o in orgs}
    att_org_id = _attendance_org_id()
    counts: dict[str, int] = {}
    for o in orgs:
        label = _org_type_name(o.org_type, db)
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
    rows = q.all()
    totals: dict[str, dict[str, int]] = {
        label: {"total_minutes": 0, "person_count": 0, "organization_count": count}
        for label, count in counts.items()
    }
    for oid, minutes, persons in rows:
        label = _org_type_name(org_type_by_id.get(oid), db)
        if label not in totals:
            totals[label] = {"total_minutes": 0, "person_count": 0, "organization_count": 0}
        totals[label]["total_minutes"] += int(minutes or 0)
        totals[label]["person_count"] += int(persons or 0)

    return [
        StatsTypeInDistrictItem(
            org_type=k,
            org_type_name=k,
            total_minutes=v["total_minutes"],
            person_count=v["person_count"],
            organization_count=v["organization_count"],
        )
        for k, v in sorted(totals.items(), key=lambda item: item[0])
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
        ot = _org_type_name(o.org_type, db)
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
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    """某单位下已参训人员及每人时长、次数。"""
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "单位不存在")
    if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权查看该单位")
    att_org_id = _attendance_org_id()
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
        .filter(att_org_id == organization_id)
    )
    if start:
        query = query.filter(TrainingSession.start_at >= start)
    if end:
        query = query.filter(TrainingSession.start_at < end)
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


def _training_summary_query(admin: AdminUser, db: Session, start: Optional[datetime], end: Optional[datetime]):
    bid = brigade_filter_brigade_id(admin)
    q = (
        db.query(
            TrainingSession,
            Organization.name.label("org_name"),
            Brigade.name.label("brigade_name"),
            TrainingTopicOption.name.label("topic_name"),
            func.count(func.distinct(TrainingAttendance.person_id)).label("person_count"),
        )
        .select_from(TrainingSession)
        .join(Organization, Organization.id == TrainingSession.organization_id)
        .join(Brigade, Brigade.id == TrainingSession.brigade_id)
        .outerjoin(TrainingTopicOption, TrainingTopicOption.id == TrainingSession.topic_id)
        .outerjoin(TrainingAttendance, TrainingAttendance.session_id == TrainingSession.id)
        .group_by(TrainingSession.id, Organization.name, Brigade.name, TrainingTopicOption.name)
    )
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    return _apply_time_range(q, start, end)


def _summary_item(row) -> StatsTrainingSummaryItem:
    sess = row[0]
    return StatsTrainingSummaryItem(
        session_id=sess.id,
        title=sess.title,
        start_at=sess.start_at,
        person_count=int(row.person_count or 0),
        brigade_name=row.brigade_name or "",
        organization_name=row.org_name or "",
        topic_name=row.topic_name,
        duration_minutes=int(sess.duration_minutes or 0),
        is_active=bool(sess.is_active),
    )


@router.get("/stats/training-summary", response_model=List[StatsTrainingSummaryItem])
def stats_training_summary(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    topic_id: Optional[int] = None,
    job_title: Optional[str] = None,
):
    q = _training_summary_query(admin, db, start, end)
    if topic_id is not None:
        q = q.filter(TrainingSession.topic_id == topic_id)
    if job_title:
        q = q.join(Person, Person.id == TrainingAttendance.person_id).filter(
            or_(Person.person_category == job_title, Person.job_title == job_title)
        )
    rows = q.order_by(TrainingSession.start_at.desc()).limit(1000).all()
    return [_summary_item(r) for r in rows]


@router.get("/stats/trainings-by-district", response_model=List[StatsTrainingSummaryItem])
def stats_trainings_by_district(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    district_id: int = Query(..., ge=1),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    bid = brigade_filter_brigade_id(admin)
    att_org_id = _attendance_org_id()
    q = (
        db.query(
            TrainingSession,
            Organization.name.label("org_name"),
            Brigade.name.label("brigade_name"),
            TrainingTopicOption.name.label("topic_name"),
            func.count(func.distinct(TrainingAttendance.person_id)).label("person_count"),
        )
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == att_org_id)
        .join(Brigade, Brigade.id == TrainingSession.brigade_id)
        .outerjoin(TrainingTopicOption, TrainingTopicOption.id == TrainingSession.topic_id)
        .filter(Organization.district_id == district_id)
        .group_by(TrainingSession.id, Organization.name, Brigade.name, TrainingTopicOption.name)
    )
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    q = _apply_time_range(q, start, end)
    return [_summary_item(r) for r in q.order_by(TrainingSession.start_at.desc()).limit(500).all()]


@router.get("/stats/by-job-title", response_model=StatsJobTitleSummary)
def stats_by_job_title(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    job_title: str = Query(..., min_length=1),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    bid = brigade_filter_brigade_id(admin)
    att_org_id = _attendance_org_id()
    base = (
        db.query(
            District.id,
            District.name,
            func.count(func.distinct(Person.id)),
        )
        .select_from(TrainingAttendance)
        .join(Person, Person.id == TrainingAttendance.person_id)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == att_org_id)
        .join(District, District.id == Organization.district_id)
        .filter(or_(Person.person_category == job_title, Person.job_title == job_title))
    )
    if bid is not None:
        base = base.filter(TrainingSession.brigade_id == bid)
    base = _apply_time_range(base, start, end)
    rows = base.group_by(District.id, District.name).order_by(District.id).all()
    trainings_q = _training_summary_query(admin, db, start, end).join(Person, Person.id == TrainingAttendance.person_id).filter(
        or_(Person.person_category == job_title, Person.job_title == job_title)
    )
    trainings = [_summary_item(r) for r in trainings_q.order_by(TrainingSession.start_at.desc()).limit(300).all()]
    return StatsJobTitleSummary(
        job_title=job_title,
        person_category=job_title,
        total_person_count=sum(int(r[2] or 0) for r in rows),
        district_counts=[{"district_id": r[0], "district_name": r[1], "person_count": int(r[2] or 0)} for r in rows],
        trainings=trainings,
    )


@router.get("/stats/by-topic", response_model=List[StatsTopicSummaryItem])
def stats_by_topic(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    topic_id: Optional[int] = None,
):
    bid = brigade_filter_brigade_id(admin)
    q = (
        db.query(
            TrainingSession.topic_id,
            func.coalesce(TrainingTopicOption.name, "未分类"),
            func.count(func.distinct(TrainingAttendance.person_id)),
        )
        .select_from(TrainingSession)
        .outerjoin(TrainingTopicOption, TrainingTopicOption.id == TrainingSession.topic_id)
        .outerjoin(TrainingAttendance, TrainingAttendance.session_id == TrainingSession.id)
        .group_by(TrainingSession.topic_id, TrainingTopicOption.name)
    )
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    if topic_id is not None:
        q = q.filter(TrainingSession.topic_id == topic_id)
    q = _apply_time_range(q, start, end)
    rows = q.all()
    out: list[StatsTopicSummaryItem] = []
    for tid, name, count in rows:
        tq = _training_summary_query(admin, db, start, end)
        tq = tq.filter(TrainingSession.topic_id == tid) if tid else tq.filter(TrainingSession.topic_id.is_(None))
        trainings = [_summary_item(r) for r in tq.order_by(TrainingSession.start_at.desc()).limit(300).all()]
        brigades = sorted({t.brigade_name for t in trainings if t.brigade_name})
        out.append(StatsTopicSummaryItem(
            topic_id=tid,
            topic_name=name or "未分类",
            person_count=int(count or 0),
            trainings=trainings,
            brigades=brigades,
        ))
    return out


@router.get("/stats/org-completion", response_model=List[StatsOrgCompletionItem])
def stats_org_completion(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    organization_id: int = Query(..., ge=1),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "单位不存在")
    if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
        raise HTTPException(403, "无权查看该单位")
    registered = (
        db.query(func.coalesce(Person.person_category, Person.job_title), func.count(Person.id))
        .filter(    
            Person.organization_id == organization_id,
            or_(Person.person_category.isnot(None), Person.job_title.isnot(None)),
        )
        .group_by(func.coalesce(Person.person_category, Person.job_title))
        .all()
    )
    out: list[StatsOrgCompletionItem] = []
    for title, total in registered:
        q = (
            db.query(func.count(func.distinct(TrainingAttendance.person_id)))
            .select_from(TrainingAttendance)
            .join(Person, Person.id == TrainingAttendance.person_id)
            .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
            .filter(
                _attendance_org_id() == organization_id,
                or_(Person.person_category == title, Person.job_title == title),
            )
        )
        q = _apply_time_range(q, start, end)
        trained = int(q.scalar() or 0)
        total_i = int(total or 0)
        out.append(StatsOrgCompletionItem(
            job_title=title or "未填",
            person_category=title or "未填",
            registered_count=total_i,
            trained_count=trained,
            completion_percent=round((trained / total_i * 100) if total_i else 0, 1),
        ))
    return sorted(out, key=lambda x: x.job_title)


@router.get("/exports/training-summary.xlsx")
def export_training_summary(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    topic_id: Optional[int] = None,
    job_title: Optional[str] = None,
):
    q = _training_summary_query(admin, db, start, end)
    if topic_id is not None:
        q = q.filter(TrainingSession.topic_id == topic_id)
    if job_title:
        q = q.join(Person, Person.id == TrainingAttendance.person_id).filter(
            or_(Person.person_category == job_title, Person.job_title == job_title)
        )
    rows = q.order_by(TrainingSession.start_at.desc()).limit(5000).all()
    return _xlsx_response(
        "training-summary.xlsx",
        ["培训名称", "培训开展日期", "培训人数", "培训主题", "开展大队", "单位名称"],
        [[r[0].title, r[0].start_at, int(r.person_count or 0), r.topic_name or "", r.brigade_name or "", r.org_name or ""] for r in rows],
    )


@router.get("/exports/training-attendance/{session_id}.xlsx")
def export_training_attendance(
    session_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    sess = db.get(TrainingSession, session_id)
    if not sess:
        raise HTTPException(404, "培训不存在")
    _ensure_training_access(sess, admin)
    rows = _attendance_rows_for_session(db, session_id)
    filename = f"training-attendance-{session_id}.xlsx"
    return _xlsx_response(
        filename,
        ["序号", "单位", "姓名", "职务", "电话"],
        [[r.index, r.organization_name, r.name, r.job_title or "", r.phone] for r in rows],
    )


@router.get("/imports/person-template.xlsx")
def download_person_import_template(_: Annotated[AdminUser, Depends(get_current_admin)]):
    return _xlsx_response(
        "person-import-template.xlsx",
        ["姓名", "手机号", "区县", "单位名称", "职务", "人员类别", "是否管理员"],
        [["张三", "13800000000", "龙港区", "葫芦岛市消防救援支队", "值班员", "消控室人员", "否"]],
    )


@router.post("/imports/persons")
async def import_persons(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        rows = _read_xlsx_rows(data)
    except Exception as exc:
        raise HTTPException(400, f"无法读取 Excel：{exc}")
    if not rows:
        raise HTTPException(400, "Excel 为空")
    header = [x.strip() for x in rows[0]]
    required = ["姓名", "手机号", "区县", "单位名称", "人员类别"]
    missing = [x for x in required if x not in header]
    if missing:
        raise HTTPException(400, f"缺少列：{', '.join(missing)}")
    idx = {name: header.index(name) for name in header}
    imported = 0
    updated = 0
    errors: list[str] = []
    for line_no, row in enumerate(rows[1:], start=2):
        def val(col: str) -> str:
            pos = idx.get(col, -1)
            return row[pos].strip() if 0 <= pos < len(row) else ""
        name = val("姓名")
        phone = val("手机号")
        district_name = val("区县")
        org_name = val("单位名称")
        job_title = val("职务") or val("职务/人员类别")
        person_category = val("人员类别") or job_title
        is_admin_text = val("是否管理员")
        if not any([name, phone, district_name, org_name, person_category]):
            continue
        if not name or not phone or not district_name or not org_name or not person_category:
            errors.append(f"第{line_no}行：必填项不完整")
            continue
        if not phone.startswith("1") or len(phone) != 11 or not phone.isdigit():
            errors.append(f"第{line_no}行：手机号格式错误")
            continue
        district = db.query(District).filter(District.name == district_name).first()
        if not district:
            errors.append(f"第{line_no}行：区县不存在")
            continue
        org = db.query(Organization).filter(Organization.district_id == district.id, Organization.name == org_name).first()
        if not org:
            errors.append(f"第{line_no}行：单位不存在")
            continue
        if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
            errors.append(f"第{line_no}行：无权导入该单位人员")
            continue
        person = db.query(Person).filter(Person.phone == phone).first()
        if person:
            person.name = name
            person.district_id = district.id
            person.organization_id = org.id
            person.job_title = job_title
            person.person_category = person_category
            updated += 1
        else:
            person = Person(
                openid=f"imported_{phone}",
                name=name,
                phone=phone,
                district_id=district.id,
                organization_id=org.id,
                job_title=job_title,
                person_category=person_category,
            )
            db.add(person)
            imported += 1
        db.flush()
        if admin.role == AdminRole.detachment and is_admin_text in ("是", "管理员", "1", "true", "TRUE"):
            _sync_person_admin(person, org, True, db)
    if errors:
        db.rollback()
        return {"ok": False, "imported": 0, "updated": 0, "errors": errors[:50]}
    db.commit()
    return {"ok": True, "imported": imported, "updated": updated, "errors": []}


@router.get("/imports/organization-template.xlsx")
def download_organization_import_template(_: Annotated[AdminUser, Depends(get_current_admin)]):
    return _xlsx_response(
        "organization-import-template.xlsx",
        ["单位名称", "单位类型", "区县", "所属大队", "联系人", "联系电话", "备注"],
        [["某某单位", "商务", "龙港区", "龙港大队", "李四", "13800000000", ""]],
    )


@router.post("/imports/organizations")
async def import_organizations(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        rows = _read_xlsx_rows(data)
    except Exception as exc:
        raise HTTPException(400, f"无法读取 Excel：{exc}")
    if not rows:
        raise HTTPException(400, "Excel 为空")
    header = [x.strip() for x in rows[0]]
    required = ["单位名称", "单位类型", "区县"]
    missing = [x for x in required if x not in header]
    if missing:
        raise HTTPException(400, f"缺少列：{', '.join(missing)}")
    idx = {name: header.index(name) for name in header}
    type_by_name = {x.name: x.code for x in db.query(OrgTypeOption).filter(OrgTypeOption.is_active.is_(True)).all()}
    brigade_by_name = {x.name: x for x in db.query(Brigade).all()}
    district_by_name = {x.name: x for x in db.query(District).all()}
    imported = 0
    updated = 0
    errors: list[str] = []
    for line_no, row in enumerate(rows[1:], start=2):
        def val(col: str) -> str:
            pos = idx.get(col, -1)
            return row[pos].strip() if 0 <= pos < len(row) else ""
        name = val("单位名称")
        type_name = val("单位类型")
        district_name = val("区县")
        brigade_name = val("所属大队")
        if not any([name, type_name, district_name, brigade_name]):
            continue
        if not name or not type_name or not district_name:
            errors.append(f"第{line_no}行：单位名称、单位类型、区县必填")
            continue
        district = district_by_name.get(district_name)
        if not district:
            errors.append(f"第{line_no}行：区县不存在")
            continue
        org_type = type_by_name.get(type_name) or type_name
        if org_type not in type_by_name.values():
            errors.append(f"第{line_no}行：单位类型不存在或已停用")
            continue
        if admin.role == AdminRole.brigade:
            brigade = db.get(Brigade, admin.brigade_id)
        else:
            brigade = brigade_by_name.get(brigade_name) if brigade_name else db.query(Brigade).filter(Brigade.code == DETACHMENT_BRIGADE_CODE).first()
        if not brigade:
            errors.append(f"第{line_no}行：所属大队不存在")
            continue
        if admin.role == AdminRole.brigade and brigade.id != admin.brigade_id:
            errors.append(f"第{line_no}行：无权导入该大队单位")
            continue
        org = db.query(Organization).filter(Organization.district_id == district.id, Organization.name == name).first()
        if org:
            if admin.role == AdminRole.brigade and org.brigade_id != admin.brigade_id:
                errors.append(f"第{line_no}行：无权修改该单位")
                continue
            org.org_type = org_type
            org.brigade_id = brigade.id
            org.contact_name = val("联系人") or None
            org.contact_phone = val("联系电话") or None
            org.remark = val("备注") or org.remark
            updated += 1
        else:
            db.add(Organization(
                name=name,
                org_type=org_type,
                brigade_id=brigade.id,
                district_id=district.id,
                contact_name=val("联系人") or None,
                contact_phone=val("联系电话") or None,
                remark=val("备注") or None,
            ))
            imported += 1
    if errors:
        db.rollback()
        return {"ok": False, "imported": 0, "updated": 0, "errors": errors[:50]}
    db.commit()
    return {"ok": True, "imported": imported, "updated": updated, "errors": []}


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
    binding_counts = dict(
        db.query(AdminWxBinding.admin_user_id, func.count(AdminWxBinding.id))
        .filter(AdminWxBinding.is_active.is_(True))
        .group_by(AdminWxBinding.admin_user_id)
        .all()
    )
    first_bindings = {
        row[0]: row[1]
        for row in (
            db.query(AdminWxBinding.admin_user_id, func.min(AdminWxBinding.bound_at))
            .filter(AdminWxBinding.is_active.is_(True))
            .group_by(AdminWxBinding.admin_user_id)
            .all()
        )
    }
    return [
        AdminAccountOut(
            id=u.id,
            username=u.username,
            role=u.role,
            brigade_id=u.brigade_id,
            brigade_name=bname,
            is_active=u.is_active,
            wx_bound=bool(binding_counts.get(u.id)),
            wx_bound_at=first_bindings.get(u.id),
            wx_binding_count=int(binding_counts.get(u.id, 0)),
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
        wx_bound=False,
        wx_bound_at=None,
        wx_binding_count=0,
    )


@router.post("/accounts/{user_id}/wx-bind-code", response_model=AdminWxBindCodeOut)
def create_admin_wx_bind_code(
    user_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    """为指定管理员生成 8 位小程序绑定码（15 分钟内有效，一次性）。"""
    u = db.get(AdminUser, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if not u.is_active:
        raise HTTPException(400, "账号已停用，无法绑定")

    ttl = 15
    expires_at = datetime.utcnow() + timedelta(minutes=ttl)
    db.query(AdminWxBindCode).filter(
        AdminWxBindCode.admin_user_id == u.id,
        AdminWxBindCode.used_at.is_(None),
    ).update({AdminWxBindCode.used_at: datetime.utcnow()}, synchronize_session=False)
    for _ in range(20):
        code = f"{secrets.randbelow(100_000_000):08d}"
        if db.query(AdminWxBindCode).filter(AdminWxBindCode.code == code).first():
            continue
        row = AdminWxBindCode(code=code, admin_user_id=u.id, expires_at=expires_at)
        db.add(row)
        db.commit()
        return AdminWxBindCodeOut(code=code, expires_at=expires_at, expires_in_minutes=ttl)
    raise HTTPException(500, "绑定码生成失败，请重试")


def _person_out(person: Person, db: Session) -> AdminPersonOut:
    district = db.get(District, person.district_id) if person.district_id else None
    org = db.get(Organization, person.organization_id) if person.organization_id else None
    admin = (
        db.query(AdminUser)
        .join(AdminWxBinding, AdminWxBinding.admin_user_id == AdminUser.id)
        .filter(AdminWxBinding.wx_openid == person.openid, AdminWxBinding.is_active.is_(True))
        .first()
    )
    admin_brigade = db.get(Brigade, admin.brigade_id) if admin and admin.brigade_id else None
    return AdminPersonOut(
        person_id=person.id,
        name=person.name or "",
        phone=person.phone or "",
        district_id=person.district_id,
        district_name=district.name if district else None,
        organization_id=person.organization_id,
        organization_name=org.name if org else None,
        job_title=person.job_title,
        person_category=person.person_category,
        wechat_bound=bool(person.openid),
        is_admin=bool(admin and admin.is_active),
        admin_role=admin.role.value if admin else None,
        admin_brigade_id=admin.brigade_id if admin else None,
        admin_brigade_name=admin_brigade.name if admin_brigade else None,
        created_at=person.created_at,
    )


@router.get("/persons", response_model=List[AdminPersonOut])
def list_persons(
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="姓名、手机号、单位关键词"),
    district_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
):
    query = db.query(Person).outerjoin(Organization, Person.organization_id == Organization.id)
    query = query.filter(Person.name.isnot(None), Person.phone.isnot(None), Person.organization_id.isnot(None))
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        query = query.filter(Organization.brigade_id == bid)
    if district_id is not None:
        query = query.filter(Person.district_id == district_id)
    if organization_id is not None:
        query = query.filter(Person.organization_id == organization_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Person.name.like(like), Person.phone.like(like), Organization.name.like(like)))
    rows = query.order_by(Person.updated_at.desc(), Person.id.desc()).limit(500).all()
    return [_person_out(p, db) for p in rows]


def _sync_person_admin(person: Person, org: Organization, is_admin: bool, db: Session) -> None:
    binding = db.query(AdminWxBinding).filter(AdminWxBinding.wx_openid == person.openid).first()
    existing = db.get(AdminUser, binding.admin_user_id) if binding else None
    if not is_admin:
        if binding:
            binding.is_active = False
        return
    if existing:
        existing.role = AdminRole.brigade
        existing.brigade_id = org.brigade_id
        existing.is_active = True
        if binding:
            binding.person_id = person.id
            binding.is_active = True
        return
    username_base = f"mp_{person.id}"
    username = username_base
    suffix = 1
    while db.query(AdminUser).filter(AdminUser.username == username).first():
        suffix += 1
        username = f"{username_base}_{suffix}"
    admin = AdminUser(
        username=username,
        password_hash=hash_password(secrets.token_urlsafe(16)),
        role=AdminRole.brigade,
        brigade_id=org.brigade_id,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    db.add(AdminWxBinding(admin_user_id=admin.id, wx_openid=person.openid, person_id=person.id, bound_at=datetime.utcnow()))


@router.patch("/persons/{person_id}", response_model=AdminPersonOut)
def manage_person_profile(
    person_id: int,
    body: AdminPersonManageIn,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "人员不存在")
    if not db.get(District, body.district_id):
        raise HTTPException(400, "区县不存在")
    org = db.get(Organization, body.organization_id)
    if not org or org.district_id != body.district_id:
        raise HTTPException(400, "所选单位与区县不一致，或单位不存在")
    if admin.role == AdminRole.brigade:
        current_org = db.get(Organization, person.organization_id) if person.organization_id else None
        if (current_org and current_org.brigade_id != admin.brigade_id) or org.brigade_id != admin.brigade_id:
            raise HTTPException(403, "只能修改本大队人员")
        if body.is_admin:
            raise HTTPException(403, "大队账号不可设置管理员身份")
    dup = db.query(Person).filter(Person.phone == body.phone, Person.id != person.id).first()
    if dup:
        raise HTTPException(400, "该手机号已被其他人员绑定")

    person.name = body.name.strip()
    person.phone = body.phone.strip()
    person.district_id = body.district_id
    person.organization_id = body.organization_id
    person.job_title = body.job_title.strip() if body.job_title else None
    if "person_category" in body.model_fields_set:
        person.person_category = body.person_category.strip() if body.person_category else None
    if admin.role == AdminRole.detachment:
        _sync_person_admin(person, org, body.is_admin, db)
    db.commit()
    db.refresh(person)
    return _person_out(person, db)


@router.get("/persons/{person_id}/trainings", response_model=List[StatsPersonTrainingItem])
def admin_person_trainings(
    person_id: int,
    admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "人员不存在")
    att_org_id = _attendance_org_id()
    q = (
        db.query(TrainingAttendance, TrainingSession, Organization, District)
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == att_org_id)
        .join(District, District.id == Organization.district_id)
        .filter(TrainingAttendance.person_id == person_id)
    )
    bid = brigade_filter_brigade_id(admin)
    if bid is not None:
        q = q.filter(TrainingSession.brigade_id == bid)
    rows = q.order_by(TrainingSession.start_at.desc()).limit(300).all()
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


@router.patch("/persons/{person_id}/rebind", response_model=AdminPersonOut)
def rebind_person_profile(
    person_id: int,
    body: AdminPersonRebindIn,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    """支队管理员重新绑定人员姓名、手机号、单位与身份/岗位。"""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "人员不存在")
    if not db.get(District, body.district_id):
        raise HTTPException(400, "区县不存在")
    org = db.get(Organization, body.organization_id)
    if not org or org.district_id != body.district_id:
        raise HTTPException(400, "所选单位与区县不一致，或单位不存在")
    dup = db.query(Person).filter(Person.phone == body.phone, Person.id != person.id).first()
    if dup:
        raise HTTPException(400, "该手机号已被其他人员绑定")

    person.name = body.name.strip()
    person.phone = body.phone.strip()
    person.district_id = body.district_id
    person.organization_id = body.organization_id
    person.job_title = body.job_title.strip() if body.job_title else None
    if "person_category" in body.model_fields_set:
        person.person_category = body.person_category.strip() if body.person_category else None
    db.commit()
    db.refresh(person)
    return _person_out(person, db)


@router.get("/accounts/{user_id}/wx-bindings", response_model=List[AdminWxBindingOut])
def list_admin_wx_bindings(
    user_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    u = db.get(AdminUser, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    rows = (
        db.query(AdminWxBinding, Person)
        .outerjoin(Person, Person.id == AdminWxBinding.person_id)
        .filter(AdminWxBinding.admin_user_id == user_id, AdminWxBinding.is_active.is_(True))
        .order_by(AdminWxBinding.bound_at.desc())
        .all()
    )
    return [
        AdminWxBindingOut(
            id=b.id,
            admin_user_id=b.admin_user_id,
            wx_openid=b.wx_openid,
            bound_at=b.bound_at,
            is_active=b.is_active,
            person_id=p.id if p else None,
            person_name=p.name if p else None,
            person_phone=p.phone if p else None,
        )
        for b, p in rows
    ]


@router.delete("/accounts/{user_id}/wx-bindings/{binding_id}", status_code=204)
def clear_admin_wx_binding(
    user_id: int,
    binding_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    binding = db.get(AdminWxBinding, binding_id)
    if not binding or binding.admin_user_id != user_id:
        raise HTTPException(404, "绑定不存在")
    binding.is_active = False
    db.commit()


@router.delete("/accounts/{user_id}/wx-bind", status_code=204)
def clear_admin_wx_bind(
    user_id: int,
    _: Annotated[AdminUser, Depends(require_detachment_admin)],
    db: Session = Depends(get_db),
):
    u = db.get(AdminUser, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    db.query(AdminWxBinding).filter(
        AdminWxBinding.admin_user_id == user_id,
        AdminWxBinding.is_active.is_(True),
    ).update({AdminWxBinding.is_active: False}, synchronize_session=False)
    u.wx_openid = None
    u.wx_bound_at = None
    db.commit()


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
    binding_count = (
        db.query(AdminWxBinding)
        .filter(AdminWxBinding.admin_user_id == u.id, AdminWxBinding.is_active.is_(True))
        .count()
    )
    first_binding = (
        db.query(func.min(AdminWxBinding.bound_at))
        .filter(AdminWxBinding.admin_user_id == u.id, AdminWxBinding.is_active.is_(True))
        .scalar()
    )
    return AdminAccountOut(
        id=u.id,
        username=u.username,
        role=u.role,
        brigade_id=u.brigade_id,
        brigade_name=bname,
        is_active=u.is_active,
        wx_bound=bool(binding_count),
        wx_bound_at=first_binding,
        wx_binding_count=int(binding_count),
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
