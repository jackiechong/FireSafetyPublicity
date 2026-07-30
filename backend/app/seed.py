"""初始化葫芦岛支队示例数据：区县、大队、默认管理员、测试用假数据"""

import random
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal, sqlite_migrate_legacy_person_columns
from app.models import (
    AdminRole,
    AdminUser,
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
from app.security import hash_password


DISTRICTS = [
    "连山区",
    "龙港区",
    "南票区",
    "绥中县",
    "建昌县",
    "兴城市",
    "杨家杖子经济开发区",
    "经济开发区",
    "高新技术开发区",
]

BRIGADES = [
    ("葫芦岛支队", "HLDZD"),
    ("连山大队", "LS"),
    ("龙港大队", "LG"),
    ("南票大队", "NP"),
    ("绥中大队", "SZ"),
    ("建昌大队", "JC"),
    ("兴城大队", "XC"),
    ("高新大队", "GX"),
    ("杨家杖子大队", "YJZ"),
    ("杨家杖子经济开发区大队", "YJJKQ"),
    ("经济开发区大队", "JJKFQ"),
    ("高新技术开发区大队", "GXJSQ"),
]

DEMO_MARK = "DEMO_SEED"
# 建昌县批量模拟：30 单位 × 每单位 20–30 人，每人约 60 分钟学时（幂等，仅缺省时写入）
FAKE_JIANCHANG_BULK = "FAKE_JIANCHANG_BULK"

# 各区县默认挂靠大队（用于补演示单位 / 补零数据）
DISTRICT_DEFAULT_BRIGADE: dict[str, str] = {
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

DEFAULT_ORG_TYPES: list[tuple[str, str]] = [
    ("emergency", "应急"),
    ("education", "教育"),
    ("civil_affairs", "民政"),
    ("culture_tourism", "文旅"),
    ("health", "卫建"),
    ("commerce", "商务"),
    ("industry_agriculture", "农业农村"),
    ("development_reform", "发改"),
    ("other_department", "其他部门"),
]

DEFAULT_JOB_TITLES = ["消防安全责任人", "消防安全管理人", "安全员", "值班长", "员工", "主管", "电工"]

DEFAULT_TRAINING_TOPICS = ["消防负责人培训", "消控室人员培训", "员工消防培训", "灭火器材使用培训", "法律法规培训"]

DEFAULT_KNOWLEDGE_CATEGORIES: list[tuple[str, str]] = [
    ("knowledge", "消防知识"),
    ("video", "宣传视频"),
    ("system", "制度"),
    ("equipment", "器材使用"),
]

DEMO_ORG_SPECS: list[tuple[str, OrgType, str, str]] = [
    ("【测试】连山商业综合体", OrgType.commerce, "LS", "连山区"),
    ("【测试】连山区某中学", OrgType.education, "LS", "连山区"),
    ("【测试】龙港石化储运", OrgType.emergency, "LG", "龙港区"),
    ("【测试】龙港区卫健局", OrgType.health, "LG", "龙港区"),
    ("【测试】绥中某酒店", OrgType.culture_tourism, "SZ", "绥中县"),
    ("【测试】兴城古城景区", OrgType.culture_tourism, "XC", "兴城市"),
    ("【测试】建昌县工业园区", OrgType.industry_agriculture, "JC", "建昌县"),
    ("【测试】南票区演示单位", OrgType.other_department, "NP", "南票区"),
    ("【测试】杨家杖子经区演示单位", OrgType.development_reform, "YJJKQ", "杨家杖子经济开发区"),
    ("【测试】经济开发区演示单位", OrgType.commerce, "JJKFQ", "经济开发区"),
    ("【测试】高新技术开发区演示单位", OrgType.emergency, "GXJSQ", "高新技术开发区"),
]


def _ensure_districts(db: Session) -> None:
    existing = {d.name for d in db.query(District).all()}
    changed = False
    for n in DISTRICTS:
        if n not in existing:
            db.add(District(name=n))
            existing.add(n)
            changed = True
    if changed:
        db.commit()


def _ensure_brigades(db: Session) -> None:
    by_code = {b.code: b for b in db.query(Brigade).all()}
    changed = False
    for name, code in BRIGADES:
        if code not in by_code:
            db.add(Brigade(name=name, code=code))
            changed = True
    if changed:
        db.commit()


# 已从大队列表移除：启动时若库中仍存在，将关联数据迁到承接大队后删除记录
_RETIRED_BRIGADE_HANDOFF = {
    "BH": "LG",  # 滨海大队 -> 龙港大队
    "JCXQ": "JC",  # 建昌新区大队 -> 建昌大队
}


def _retire_removed_brigades(db: Session) -> None:
    for old_code, new_code in _RETIRED_BRIGADE_HANDOFF.items():
        old_b = db.query(Brigade).filter(Brigade.code == old_code).first()
        new_b = db.query(Brigade).filter(Brigade.code == new_code).first()
        if not old_b or not new_b:
            continue
        oid, nid = old_b.id, new_b.id
        db.query(Organization).filter(Organization.brigade_id == oid).update(
            {"brigade_id": nid},
            synchronize_session=False,
        )
        db.query(TrainingSession).filter(TrainingSession.brigade_id == oid).update(
            {"brigade_id": nid},
            synchronize_session=False,
        )
        db.query(AdminUser).filter(AdminUser.brigade_id == oid).update(
            {"brigade_id": nid},
            synchronize_session=False,
        )
        db.delete(old_b)
    db.commit()


def seed():
    Base.metadata.create_all(bind=engine)
    sqlite_migrate_legacy_person_columns()
    db: Session = SessionLocal()
    try:
        _ensure_districts(db)
        _ensure_brigades(db)
        _ensure_dictionary_options(db)
        _retire_removed_brigades(db)
        _ensure_fire_brigade_organizations(db)
        _ensure_other_organizations(db)
        _reclassify_demo_org_types(db)

        if db.query(AdminUser).count() == 0:
            det = AdminUser(
                username="zhidui",
                password_hash=hash_password("zhidui123"),
                role=AdminRole.detachment,
                brigade_id=None,
            )
            db.add(det)
            b1 = db.query(Brigade).filter(Brigade.code == "LS").first()
            if b1:
                db.add(
                    AdminUser(
                        username="lianshan",
                        password_hash=hash_password("dadui123"),
                        role=AdminRole.brigade,
                        brigade_id=b1.id,
                    )
                )
            db.commit()

        _ensure_root_admin(db)

        _seed_demo_dataset(db)
        _ensure_demo_persons(db)
        _ensure_demo_trainings(db, total=200)
        _ensure_demo_attendances(db)
        _seed_jianchang_fake_bulk(db)
        _ensure_fake_padding_for_zero_districts(db)
    finally:
        db.close()


def _ensure_other_organizations(db: Session) -> None:
    districts = db.query(District).order_by(District.id).all()
    brigades_by_code = {b.code: b for b in db.query(Brigade).all()}
    first_brigade = db.query(Brigade).order_by(Brigade.id).first()
    changed = False
    for district in districts:
        exists = (
            db.query(Organization)
            .filter(Organization.district_id == district.id, Organization.name == "其他")
            .first()
        )
        if exists:
            continue
        brigade = brigades_by_code.get(DISTRICT_DEFAULT_BRIGADE.get(district.name, "")) or first_brigade
        if not brigade:
            continue
        db.add(
            Organization(
                name="其他",
                org_type=OrgType.other_department,
                brigade_id=brigade.id,
                district_id=district.id,
                remark="SYSTEM_OTHER",
            )
        )
        changed = True
    if changed:
        db.commit()


def _ensure_root_admin(db: Session) -> None:
    """确保最高权限管理员账号存在：admin / admin。"""
    user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    if not user:
        db.add(
            AdminUser(
                username="admin",
                password_hash=hash_password("admin"),
                role=AdminRole.detachment,
                brigade_id=None,
                is_active=True,
            )
        )
        db.commit()
        return
    user.password_hash = hash_password("admin")
    user.role = AdminRole.detachment
    user.brigade_id = None
    user.is_active = True
    db.commit()


def _ensure_dictionary_options(db: Session) -> None:
    changed = False
    existing_types = {x.code: x for x in db.query(OrgTypeOption).all()}
    for idx, (code, name) in enumerate(DEFAULT_ORG_TYPES, start=1):
        item = existing_types.get(code)
        if not item:
            db.add(OrgTypeOption(code=code, name=name, sort_order=idx, is_active=True))
            changed = True
        elif item.name != name:
            item.name = name
            changed = True

    existing_titles = {x.name for x in db.query(JobTitleOption).all()}
    for idx, name in enumerate(DEFAULT_JOB_TITLES, start=1):
        if name not in existing_titles:
            db.add(JobTitleOption(name=name, sort_order=idx, is_active=True))
            changed = True
    existing_topics = {x.name for x in db.query(TrainingTopicOption).all()}
    for idx, name in enumerate(DEFAULT_TRAINING_TOPICS, start=1):
        if name not in existing_topics:
            db.add(TrainingTopicOption(name=name, sort_order=idx, is_active=True))
            changed = True
    existing_categories = {x.code: x for x in db.query(KnowledgeCategoryOption).all()}
    for idx, (code, label) in enumerate(DEFAULT_KNOWLEDGE_CATEGORIES, start=1):
        cat = existing_categories.get(code)
        if not cat:
            db.add(KnowledgeCategoryOption(code=code, name=label, sort_order=idx, is_active=True))
            changed = True
        elif cat.name != label and not db.query(KnowledgeCategoryOption).filter(KnowledgeCategoryOption.name == label, KnowledgeCategoryOption.code != code).first():
            cat.name = label
            changed = True
        title = f"{label}栏目"
        if not db.query(KnowledgeArticle).filter(
            KnowledgeArticle.category == code, KnowledgeArticle.title == title
        ).first():
            db.add(KnowledgeArticle(category=code, title=title, content="请在后台编辑本栏目内容。", sort_order=idx, is_active=True))
            changed = True
    legacy_law = db.query(KnowledgeCategoryOption).filter(KnowledgeCategoryOption.code == "law").first()
    if legacy_law:
        db.query(KnowledgeArticle).filter(KnowledgeArticle.category == "law").update(
            {"category": "video"},
            synchronize_session=False,
        )
        db.delete(legacy_law)
        changed = True
    if changed:
        db.commit()


def _ensure_fire_brigade_organizations(db: Session) -> None:
    """补齐小程序绑定页优先展示的消防支队/大队单位。"""
    districts = {d.name: d for d in db.query(District).all()}
    brigades_by_code = {b.code: b for b in db.query(Brigade).all()}
    specs: list[tuple[str, str, str]] = []
    for district_name, brigade_code in DISTRICT_DEFAULT_BRIGADE.items():
        if district_name == "龙港区":
            specs.append(("葫芦岛市消防救援支队", district_name, brigade_code))
            specs.append(("龙港区消防救援大队", district_name, brigade_code))
        else:
            specs.append((f"{district_name}消防救援大队", district_name, brigade_code))

    changed = False
    for org_name, district_name, brigade_code in specs:
        district = districts.get(district_name)
        brigade = brigades_by_code.get(brigade_code)
        if not district or not brigade:
            continue
        existing = (
            db.query(Organization)
            .filter(Organization.district_id == district.id, Organization.name == org_name)
            .first()
        )
        if existing:
            if existing.brigade_id != brigade.id:
                existing.brigade_id = brigade.id
                changed = True
            if existing.org_type != OrgType.emergency:
                existing.org_type = OrgType.emergency
                changed = True
            continue
        db.add(
            Organization(
                name=org_name,
                org_type=OrgType.emergency,
                brigade_id=brigade.id,
                district_id=district.id,
                remark="SYSTEM_FIRE_BRIGADE",
            )
        )
        changed = True
    if changed:
        db.commit()


def _reclassify_demo_org_types(db: Session) -> None:
    """将已有演示/fake 单位迁移到新的部门类型体系。"""
    changed = False
    by_name = {name: org_type for name, org_type, _, _ in DEMO_ORG_SPECS}
    for org in db.query(Organization).all():
        target = by_name.get(org.name)
        if not target:
            if org.remark == "SYSTEM_OTHER":
                target = OrgType.other_department
            elif org.remark == FAKE_JIANCHANG_BULK:
                # 建昌批量 fake 数据按序轮换，便于类型占比图有分布。
                types = [
                    OrgType.emergency,
                    OrgType.education,
                    OrgType.civil_affairs,
                    OrgType.culture_tourism,
                    OrgType.health,
                    OrgType.commerce,
                    OrgType.industry_agriculture,
                    OrgType.development_reform,
                    OrgType.other_department,
                ]
                target = types[org.id % len(types)]
            elif org.org_type in (OrgType.enterprise, OrgType.department):
                target = OrgType.other_department
        if target and org.org_type != target:
            org.org_type = target
            changed = True
    if changed:
        db.commit()


def _seed_demo_dataset(db: Session) -> None:
    """按名称幂等插入【测试】演示单位，不因已有其它演示数据而跳过新区县。"""
    districts = {d.name: d.id for d in db.query(District).all()}
    brigades = {b.code: b.id for b in db.query(Brigade).all()}
    if len(districts) < 3 or len(brigades) < 3:
        return

    existing_names = {o.name for o in db.query(Organization).all()}
    changed = False
    for name, org_type, brigade_code, district_name in DEMO_ORG_SPECS:
        if name in existing_names:
            continue
        if district_name not in districts or brigade_code not in brigades:
            continue
        db.add(
            Organization(
                name=name,
                org_type=org_type,
                brigade_id=brigades[brigade_code],
                district_id=districts[district_name],
                contact_name="测试联系人",
                contact_phone="13900000000",
                remark=DEMO_MARK,
            )
        )
        existing_names.add(name)
        changed = True
    if changed:
        db.commit()


def _district_total_training_minutes(db: Session, district_id: int) -> int:
    q = (
        db.query(func.coalesce(func.sum(TrainingAttendance.duration_minutes), 0))
        .select_from(TrainingAttendance)
        .join(TrainingSession, TrainingSession.id == TrainingAttendance.session_id)
        .join(Organization, Organization.id == TrainingSession.organization_id)
        .filter(Organization.district_id == district_id)
    )
    return int(q.scalar() or 0)


def _ensure_fake_padding_for_zero_districts(db: Session) -> None:
    """统计时长仍为 0 的区县：补一条演示培训 + 参训记录（仅 DEMO，便于柱状图有柱）。"""
    districts = db.query(District).order_by(District.id).all()
    base = datetime(2025, 3, 1, 9, 0, 0)
    random.seed(101)
    changed = False
    for d in districts:
        if _district_total_training_minutes(db, d.id) > 0:
            continue
        code = DISTRICT_DEFAULT_BRIGADE.get(d.name)
        if not code:
            continue
        b = db.query(Brigade).filter(Brigade.code == code).first()
        if not b:
            continue
        org = (
            db.query(Organization)
            .filter(Organization.district_id == d.id, Organization.remark == DEMO_MARK)
            .first()
        )
        if not org:
            org = Organization(
                name=f"【测试】{d.name}演示单位",
                org_type=OrgType.other_department,
                brigade_id=b.id,
                district_id=d.id,
                contact_name="演示",
                contact_phone="13900000000",
                remark=DEMO_MARK,
            )
            db.add(org)
            db.flush()

        oid = f"fake_pad_d{d.id}"
        person = db.query(Person).filter(Person.openid == oid).first()
        if not person:
            phone = f"138{(100000000 + d.id):09d}"[-11:]
            person = Person(
                openid=oid,
                name="演示员",
                phone=phone,
                district_id=d.id,
                organization_id=org.id,
                job_title="员工",
            )
            db.add(person)
            db.flush()

        dur = 90 + (d.id % 5) * 30
        sess = TrainingSession(
            title=f"【测试】{d.name}补录演示",
            brigade_id=org.brigade_id,
            organization_id=org.id,
            start_at=base + timedelta(days=(d.id % 60)),
            duration_minutes=dur,
            location="演示场地",
            remark=DEMO_MARK,
        )
        db.add(sess)
        db.flush()
        db.add(TrainingAttendance(session_id=sess.id, person_id=person.id, organization_id=person.organization_id, duration_minutes=dur))
        changed = True
    if changed:
        db.commit()


def _ensure_demo_persons(db: Session) -> None:
    """单位已存在时也会补全 5 名测试人员（openid fake_openid_test_*）。"""
    if db.query(Person).filter(Person.openid.like("fake_openid_test_%")).count() >= 5:
        return
    orgs = db.query(Organization).filter(Organization.remark == DEMO_MARK).all()
    if len(orgs) < 3:
        return
    org_by_name = {o.name: o for o in orgs}
    districts = {d.name: d.id for d in db.query(District).all()}
    persons_spec = [
        ("fake_openid_test_001", "张三", "13800138001", "连山区", "【测试】连山商业综合体", "消防安全管理人"),
        ("fake_openid_test_002", "李四", "13800138002", "连山区", "【测试】连山区某中学", "副校长"),
        ("fake_openid_test_003", "王五", "13800138003", "龙港区", "【测试】龙港石化储运", "安全主管"),
        ("fake_openid_test_004", "赵六", "13800138004", "龙港区", "【测试】龙港区卫健局", "科长"),
        ("fake_openid_test_005", "钱七", "13800138005", "绥中县", "【测试】绥中某酒店", "店长"),
    ]
    for oid, name, phone, dname, oname, job in persons_spec:
        if db.query(Person).filter(Person.openid == oid).first():
            continue
        org = org_by_name.get(oname)
        if not org or dname not in districts:
            continue
        db.add(
            Person(
                openid=oid,
                name=name,
                phone=phone,
                district_id=districts[dname],
                organization_id=org.id,
                job_title=job,
            )
        )
    db.commit()


def _ensure_demo_trainings(db: Session, total: int = 200) -> None:
    """生成/补全带 DEMO_MARK 的培训记录至 total 条（用于列表与统计测试）。"""
    orgs = db.query(Organization).filter(Organization.remark == DEMO_MARK).all()
    if not orgs:
        return
    existing = db.query(TrainingSession).filter(TrainingSession.remark == DEMO_MARK).count()
    if existing >= total:
        return
    need = total - existing
    random.seed(42)
    titles = [
        "消防安全培训",
        "灭火器实操",
        "疏散演练",
        "消防安全管理人培训",
        "电气火灾防范",
        "微型消防站培训",
        "消防控制室值班培训",
        "动火作业安全",
        "九小场所专项",
        "高层建筑消防",
    ]
    base = datetime(2025, 1, 8, 8, 0, 0)
    for i in range(need):
        idx = existing + i
        org = orgs[idx % len(orgs)]
        day_offset = (idx * 2) % 500
        hour = 8 + (idx % 9)
        minute = (idx % 4) * 15
        start = base + timedelta(days=day_offset, hours=hour, minutes=minute)
        dur = 30 + (idx % 11) * 15
        if dur > 180:
            dur = 180
        db.add(
            TrainingSession(
                title=f"【测试】{random.choice(titles)}（自动 #{idx + 1}）",
                brigade_id=org.brigade_id,
                organization_id=org.id,
                start_at=start,
                duration_minutes=dur,
                location=f"测试场地-{(idx % 40) + 1}",
                remark=DEMO_MARK,
            )
        )
    db.commit()


def _seed_jianchang_fake_bulk(db: Session) -> None:
    """在建昌县生成 30 个模拟单位；每单位 20–30 名人员，每人约 60 分钟培训记录。启动幂等。"""
    district = db.query(District).filter(District.name == "建昌县").first()
    brigade = db.query(Brigade).filter(Brigade.code == "JC").first()
    if not district or not brigade:
        return

    existing_orgs = (
        db.query(Organization)
        .filter(Organization.district_id == district.id, Organization.remark == FAKE_JIANCHANG_BULK)
        .count()
    )
    if existing_orgs >= 30:
        return

    random.seed(5142026)
    org_labels = [
        "商贸城",
        "宾馆酒店",
        "学校",
        "医院",
        "养老院",
        "物流仓储",
        "加油站",
        "住宅小区物业",
        "工业园区企业",
        "农贸市场",
        "文化场馆",
        "餐饮连锁",
        "银行网点",
        "通信机房",
        "在建工地",
        "家具卖场",
        "纺织企业",
        "食品加工",
        "冷库运营",
        "汽车维修",
        "网吧",
        "KTV",
        "洗浴中心",
        "宗教场所",
        "敬老院",
        "幼儿园",
        "乡镇政府",
        "林业管护站",
        "水库管理",
        "景区运营",
    ]
    surnames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    given = "伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀英华慧兰云飞鹏波辉刚平玉梅琳雪晨阳"

    base_day = datetime(2025, 4, 10, 9, 0, 0)
    for i in range(30):
        label = org_labels[i % len(org_labels)]
        org = Organization(
            name=f"【建昌模拟】{label}{i + 1:02d}号",
            org_type=random.choice([
                OrgType.emergency,
                OrgType.education,
                OrgType.civil_affairs,
                OrgType.culture_tourism,
                OrgType.health,
                OrgType.commerce,
                OrgType.industry_agriculture,
                OrgType.development_reform,
                OrgType.other_department,
            ]),
            brigade_id=brigade.id,
            district_id=district.id,
            contact_name=f"联系人{i + 1}",
            contact_phone=f"139{8000000 + i:08d}",
            remark=FAKE_JIANCHANG_BULK,
        )
        db.add(org)
        db.flush()

        n_staff = random.randint(20, 30)
        people: list[Person] = []
        for j in range(n_staff):
            oid = f"fake_jc_o{i:02d}_p{j:03d}"
            if db.query(Person).filter(Person.openid == oid).first():
                continue
            name = f"{random.choice(surnames)}{random.choice(given)}"
            num = (26000000 + i * 10000 + j) % 100000000
            phone = f"138{num:08d}"
            p = Person(
                openid=oid,
                name=name,
                phone=phone,
                district_id=district.id,
                organization_id=org.id,
                job_title=random.choice(["安全员", "值班长", "员工", "主管", "电工"]),
            )
            db.add(p)
            people.append(p)
        db.flush()

        dur = random.choice([55, 58, 60, 60, 62, 65])
        sess = TrainingSession(
            title=f"{org.name}消防安全培训",
            brigade_id=brigade.id,
            organization_id=org.id,
            start_at=base_day + timedelta(days=(i * 4) % 150, hours=i % 6),
            duration_minutes=dur,
            location="建昌县模拟培训场地",
            remark=FAKE_JIANCHANG_BULK,
        )
        db.add(sess)
        db.flush()

        for p in people:
            if not p.id:
                continue
            exists = (
                db.query(TrainingAttendance)
                .filter(
                    TrainingAttendance.session_id == sess.id,
                    TrainingAttendance.person_id == p.id,
                )
                .first()
            )
            if exists:
                continue
            db.add(TrainingAttendance(session_id=sess.id, person_id=p.id, organization_id=p.organization_id, duration_minutes=dur))

    db.commit()


def _ensure_demo_attendances(db: Session) -> None:
    """为 DEMO 培训场次写入参训记录，便于统计、管理端列表与小程序「我的培训」。"""
    sessions = (
        db.query(TrainingSession)
        .filter(TrainingSession.remark == DEMO_MARK)
        .order_by(TrainingSession.id)
        .all()
    )
    persons = db.query(Person).filter(Person.openid.like("fake_openid_test_%")).all()
    if not sessions or not persons:
        return

    pid_by_org: dict[int, list[Person]] = {}
    for p in persons:
        pid_by_org.setdefault(p.organization_id, []).append(p)

    random.seed(43)
    for s in sessions:
        if db.query(TrainingAttendance).filter(TrainingAttendance.session_id == s.id).count() > 0:
            continue

        org = db.get(Organization, s.organization_id)
        candidates = list(pid_by_org.get(s.organization_id, []))
        if not candidates and org:
            candidates = [p for p in persons if p.district_id == org.district_id]
        if not candidates:
            candidates = list(persons)

        n = len(candidates)
        k = random.randint(1, min(3, max(1, n)))
        chosen = random.sample(candidates, k) if n >= k else list(candidates)
        dur = int(s.duration_minutes or 60)
        for p in chosen:
            db.add(TrainingAttendance(session_id=s.id, person_id=p.id, organization_id=p.organization_id, duration_minutes=dur))
    db.commit()


if __name__ == "__main__":
    seed()
