from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def sqlite_migrate_legacy_person_columns() -> None:
    """旧版 SQLite 库表缺少区县/单位等字段时自动 ALTER，避免已有 data/app.db 启动失败。"""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(persons)")).fetchall()
        if not rows:
            return
        cols = {r[1] for r in rows}
        if "district_id" not in cols:
            conn.execute(text("ALTER TABLE persons ADD COLUMN district_id INTEGER"))
        if "organization_id" not in cols:
            conn.execute(text("ALTER TABLE persons ADD COLUMN organization_id INTEGER"))
        if "job_title" not in cols:
            conn.execute(text("ALTER TABLE persons ADD COLUMN job_title VARCHAR(64)"))

        rows = conn.execute(text("PRAGMA table_info(training_attendances)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "checked_in_at" not in cols:
                conn.execute(text("ALTER TABLE training_attendances ADD COLUMN checked_in_at DATETIME"))

        rows = conn.execute(text("PRAGMA table_info(training_sessions)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "is_active" not in cols:
                conn.execute(text("ALTER TABLE training_sessions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))

        rows = conn.execute(text("PRAGMA table_info(admin_users)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "wx_openid" not in cols:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN wx_openid VARCHAR(64)"))
            if "wx_bound_at" not in cols:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN wx_bound_at DATETIME"))

        rows = conn.execute(text("PRAGMA table_info(admin_wx_bind_codes)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "failed_attempts" not in cols:
                conn.execute(text("ALTER TABLE admin_wx_bind_codes ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
