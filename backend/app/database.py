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

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_wx_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER NOT NULL,
                wx_openid VARCHAR(64) NOT NULL UNIQUE,
                person_id INTEGER,
                bound_at DATETIME,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                remark VARCHAR(256),
                FOREIGN KEY(admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY(person_id) REFERENCES persons(id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_wx_bindings_admin_user_id ON admin_wx_bindings(admin_user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_wx_bindings_wx_openid ON admin_wx_bindings(wx_openid)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_wx_bindings_person_id ON admin_wx_bindings(person_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_wx_bindings_is_active ON admin_wx_bindings(is_active)"))
        conn.execute(text("""
            INSERT OR IGNORE INTO admin_wx_bindings (admin_user_id, wx_openid, person_id, bound_at, is_active, remark)
            SELECT admin_users.id, admin_users.wx_openid, persons.id, COALESCE(admin_users.wx_bound_at, CURRENT_TIMESTAMP), 1, 'MIGRATED_LEGACY'
            FROM admin_users
            LEFT JOIN persons ON persons.openid = admin_users.wx_openid
            WHERE admin_users.wx_openid IS NOT NULL AND admin_users.wx_openid != ''
        """))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
