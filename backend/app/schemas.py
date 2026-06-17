from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import AdminRole, OrgType


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: AdminRole
    brigade_id: Optional[int] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class AdminAccountOut(BaseModel):
    id: int
    username: str
    role: AdminRole
    brigade_id: Optional[int] = None
    brigade_name: Optional[str] = None
    is_active: bool
    wx_bound: bool = False
    wx_bound_at: Optional[datetime] = None
    wx_binding_count: int = 0


class AdminWxBindingOut(BaseModel):
    id: int
    admin_user_id: int
    wx_openid: str
    bound_at: datetime
    is_active: bool = True
    person_id: Optional[int] = None
    person_name: Optional[str] = None
    person_phone: Optional[str] = None


class AdminWxBindCodeOut(BaseModel):
    code: str
    expires_at: datetime
    expires_in_minutes: int = 15


class AdminAccountCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: AdminRole
    brigade_id: Optional[int] = None


class AdminAccountUpdate(BaseModel):
    role: Optional[AdminRole] = None
    brigade_id: Optional[int] = None
    is_active: Optional[bool] = None


class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class DictionaryOptionOut(BaseModel):
    id: int
    name: str
    sort_order: int = 100
    is_active: bool = True
    code: Optional[str] = None


class OrgTypeOptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    code: Optional[str] = Field(default=None, max_length=64)
    sort_order: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class OrgTypeOptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class JobTitleOptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    sort_order: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class JobTitleOptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class TrainingTopicOptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    sort_order: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class TrainingTopicOptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class KnowledgeArticleCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=20000)
    sort_order: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class KnowledgeArticleUpdate(BaseModel):
    category: Optional[str] = Field(default=None, min_length=1, max_length=64)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, max_length=20000)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class KnowledgeArticleOut(BaseModel):
    id: int
    category: str
    title: str
    content: str
    sort_order: int = 100
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KnowledgeCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    code: Optional[str] = Field(default=None, max_length=64)
    sort_order: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class KnowledgeCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class BrigadeOut(BaseModel):
    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class DistrictOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    org_type: str = Field(..., min_length=1, max_length=64)
    brigade_id: int
    district_id: int
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    org_type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    brigade_id: Optional[int] = None
    district_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    org_type: str
    brigade_id: int
    district_id: int
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingSessionCreate(BaseModel):
    title: str
    topic_id: Optional[int] = None
    brigade_id: int
    organization_id: int
    start_at: datetime
    end_at: Optional[datetime] = None
    duration_minutes: int = Field(ge=0)
    location: Optional[str] = None
    remark: Optional[str] = None
    is_active: bool = Field(default=True, description="是否开放扫码签到；超过结束时间后由系统自动关闭")


class TrainingSessionPatch(BaseModel):
    is_active: Optional[bool] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    topic_id: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    location: Optional[str] = None
    remark: Optional[str] = None


class TrainingSessionOut(BaseModel):
    id: int
    title: str
    topic_id: Optional[int] = None
    brigade_id: int
    organization_id: int
    start_at: datetime
    end_at: Optional[datetime] = None
    duration_minutes: int
    is_active: bool = True
    location: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceAdd(BaseModel):
    person_id: Optional[int] = None
    phone: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=64)
    organization_id: Optional[int] = None
    job_title: Optional[str] = Field(default=None, max_length=64)
    person_category: Optional[str] = Field(default=None, max_length=64)
    duration_minutes: Optional[int] = None


class QuickTrainingCreate(BaseModel):
    """手机端「一键创建培训」请求体。"""
    title: str = Field(..., min_length=1, max_length=200)
    organization_id: int = Field(..., ge=1)
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    location: Optional[str] = Field(default=None, max_length=200)
    start_at: Optional[datetime] = None
    topic_id: Optional[int] = None


class QuickTrainingOut(BaseModel):
    session_id: int
    title: str
    start_at: datetime
    duration_minutes: int
    location: Optional[str] = None
    organization_id: int
    organization_name: str
    brigade_id: int
    brigade_name: str
    qr_payload: str  # 二维码内容（本场培训，公众号 OAuth）
    portal_login_url: Optional[str] = None  # 通用入口：扫码后登录再自选活动场次（需配置公众号回调域名）
    attendance_count: int = 0


class MpLoginIn(BaseModel):
    code: str


class MpLoginOut(BaseModel):
    token: str
    need_profile: bool
    is_admin: bool = False
    admin_role: Optional[str] = None
    admin_brigade_id: Optional[int] = None
    admin_username: Optional[str] = None
    admin_brigade_name: Optional[str] = None


class MpWxBindIn(BaseModel):
    code: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")


class MpWxBindOut(BaseModel):
    ok: bool = True
    admin_username: str
    admin_role: str
    admin_brigade_name: Optional[str] = None


class MpAdminMeOut(BaseModel):
    admin_username: str
    admin_role: str
    admin_brigade_id: Optional[int] = None
    admin_brigade_name: Optional[str] = None


class MpProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=11, max_length=11)
    district_id: int = Field(..., description="所属区县")
    organization_id: int = Field(..., description="所属单位")
    job_title: str = Field(..., min_length=1, max_length=64, description="职务/岗位")


class MpOrganizationCreateIn(BaseModel):
    """小程序绑定页选「其他单位」时自助新增单位。"""
    district_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=256)
    org_type: str = Field(default=OrgType.other_department.value, min_length=1, max_length=64)


class MpPersonOut(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    job_title: Optional[str] = None
    wechat_bound: bool = True
    is_admin: bool = False
    admin_role: Optional[str] = None
    admin_brigade_id: Optional[int] = None
    admin_username: Optional[str] = None
    admin_brigade_name: Optional[str] = None

    model_config = {"from_attributes": True}


class MpOrgListItem(BaseModel):
    id: int
    name: str
    org_type: str


class MpTrainingItem(BaseModel):
    session_id: int
    title: str
    start_at: datetime
    duration_minutes: int
    organization_name: str
    district_name: str


class MpCheckinIn(BaseModel):
    session_id: int = Field(..., ge=1)


class MpActiveTrainingItem(BaseModel):
    session_id: int
    title: str
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None
    start_at: datetime
    duration_minutes: int
    location: Optional[str] = None
    organization_name: str
    district_name: str
    district_id: int
    same_district: bool = False


class MpCheckinOut(BaseModel):
    ok: bool = True
    already_checked: bool = False
    session_id: int
    title: str
    start_at: datetime
    location: Optional[str] = None
    duration_minutes: int
    organization_name: str


class StatsDistrictItem(BaseModel):
    district_id: int
    district_name: str
    total_minutes: int
    session_count: int


class StatsPersonItem(BaseModel):
    person_id: int
    name: str
    phone: str
    session_count: int
    total_minutes: int


class StatsPersonTrainingItem(BaseModel):
    session_id: int
    title: str
    start_at: datetime
    duration_minutes: int
    organization_name: str
    district_name: str
    location: Optional[str] = None


class AdminPersonRebindIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^1\d{10}$")
    district_id: int = Field(..., ge=1)
    organization_id: int = Field(..., ge=1)
    job_title: Optional[str] = Field(default=None, max_length=64)
    person_category: Optional[str] = Field(default=None, max_length=64)


class AdminPersonManageIn(AdminPersonRebindIn):
    is_admin: bool = False


class AdminPersonOut(BaseModel):
    person_id: int
    name: str
    phone: str
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    job_title: Optional[str] = None
    person_category: Optional[str] = None
    wechat_bound: bool = True
    is_admin: bool = False
    admin_role: Optional[str] = None
    admin_brigade_id: Optional[int] = None
    admin_brigade_name: Optional[str] = None
    created_at: Optional[datetime] = None


class StatsOrgInDistrictItem(BaseModel):
    organization_id: int
    organization_name: str
    total_minutes: int
    person_count: int


class StatsTypeInDistrictItem(BaseModel):
    org_type: str
    org_type_name: str
    total_minutes: int
    person_count: int
    organization_count: int


class StatsSearchItem(BaseModel):
    kind: str  # organization | person
    id: int
    title: str
    subtitle: str
    organization_id: Optional[int] = None
    district_id: Optional[int] = None
    person_id: Optional[int] = None


class StatsTrainingSummaryItem(BaseModel):
    session_id: int
    title: str
    start_at: datetime
    person_count: int
    brigade_name: str
    organization_name: str
    topic_name: Optional[str] = None


class StatsJobTitleSummary(BaseModel):
    job_title: str
    person_category: Optional[str] = None
    total_person_count: int
    district_counts: list[dict]
    trainings: list[StatsTrainingSummaryItem]


class StatsTopicSummaryItem(BaseModel):
    topic_id: Optional[int] = None
    topic_name: str
    person_count: int
    trainings: list[StatsTrainingSummaryItem]
    brigades: list[str]


class StatsOrgCompletionItem(BaseModel):
    job_title: str
    person_category: Optional[str] = None
    registered_count: int
    trained_count: int
    completion_percent: float


class SuggestItem(BaseModel):
    id: int
    name: str
    org_type: str
    district_name: str
