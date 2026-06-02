import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrgType(str, enum.Enum):
    emergency = "emergency"  # 应急
    education = "education"  # 教育
    civil_affairs = "civil_affairs"  # 民政
    culture_tourism = "culture_tourism"  # 文旅
    health = "health"  # 卫建
    commerce = "commerce"  # 商务
    industry_agriculture = "industry_agriculture"  # 工农业农村
    development_reform = "development_reform"  # 发改
    other_department = "other_department"  # 其他部门
    department = "department"  # 旧数据兼容：行业部门
    enterprise = "enterprise"  # 旧数据兼容：企业


class AdminRole(str, enum.Enum):
    detachment = "detachment"  # 支队：看全部
    brigade = "brigade"  # 大队：只看本大队


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), default=AdminRole.brigade)
    brigade_id: Mapped[int | None] = mapped_column(ForeignKey("brigades.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    wx_openid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    wx_bound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    brigade = relationship("Brigade", back_populates="admins")
    wx_bind_codes = relationship("AdminWxBindCode", back_populates="admin_user")


class AdminWxBindCode(Base):
    """支队在网站生成的 8 位绑定码，供管理员在小程序输入以绑定微信 openid。"""

    __tablename__ = "admin_wx_bind_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    admin_user = relationship("AdminUser", back_populates="wx_bind_codes")


class Brigade(Base):
    __tablename__ = "brigades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)

    admins = relationship("AdminUser", back_populates="brigade")
    organizations = relationship("Organization", back_populates="brigade")


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)

    organizations = relationship("Organization", back_populates="district")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    org_type: Mapped[OrgType] = mapped_column(Enum(OrgType))
    brigade_id: Mapped[int] = mapped_column(ForeignKey("brigades.id"), index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brigade = relationship("Brigade", back_populates="organizations")
    district = relationship("District", back_populates="organizations")
    trainings = relationship("TrainingSession", back_populates="organization")


class Person(Base):
    """小程序用户：微信 openid 绑定；实名信息；所属区县与单位"""

    __tablename__ = "persons"
    __table_args__ = (UniqueConstraint("openid", name="uq_person_openid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), nullable=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    job_title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    district = relationship("District", foreign_keys=[district_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    attendances = relationship("TrainingAttendance", back_populates="person")


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    brigade_id: Mapped[int] = mapped_column(ForeignKey("brigades.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="trainings")
    attendances = relationship("TrainingAttendance", back_populates="session", cascade="all, delete-orphan")


class TrainingAttendance(Base):
    __tablename__ = "training_attendances"
    __table_args__ = (UniqueConstraint("session_id", "person_id", name="uq_session_person"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session = relationship("TrainingSession", back_populates="attendances")
    person = relationship("Person", back_populates="attendances")
