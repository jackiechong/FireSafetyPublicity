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
    org_type: OrgType
    brigade_id: int
    district_id: int
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    org_type: Optional[OrgType] = None
    brigade_id: Optional[int] = None
    district_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    org_type: OrgType
    brigade_id: int
    district_id: int
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingSessionCreate(BaseModel):
    title: str
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


class TrainingSessionOut(BaseModel):
    id: int
    title: str
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
    duration_minutes: Optional[int] = None


class QuickTrainingCreate(BaseModel):
    """手机端「一键创建培训」请求体。"""
    title: str = Field(..., min_length=1, max_length=200)
    organization_id: int = Field(..., ge=1)
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    location: Optional[str] = Field(default=None, max_length=200)
    start_at: Optional[datetime] = None


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


class MpProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=11, max_length=11)
    district_id: int = Field(..., description="所属区县")
    organization_id: int = Field(..., description="所属单位（行业部门/企业）")
    job_title: Optional[str] = Field(default=None, max_length=64, description="职务/岗位")


class MpOrganizationCreateIn(BaseModel):
    """小程序绑定页选「其他单位」时自助新增单位。"""
    district_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=256)
    org_type: OrgType = OrgType.enterprise


class MpPersonOut(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    job_title: Optional[str] = None
    wechat_bound: bool = True

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
    start_at: datetime
    duration_minutes: int
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


class StatsOrgInDistrictItem(BaseModel):
    organization_id: int
    organization_name: str
    total_minutes: int
    person_count: int


class StatsSearchItem(BaseModel):
    kind: str  # organization | person
    id: int
    title: str
    subtitle: str
    organization_id: Optional[int] = None
    district_id: Optional[int] = None
    person_id: Optional[int] = None


class SuggestItem(BaseModel):
    id: int
    name: str
    org_type: OrgType
    district_name: str
