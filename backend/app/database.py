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
        if "person_category" not in cols:
            conn.execute(text("ALTER TABLE persons ADD COLUMN person_category VARCHAR(64)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_persons_person_category ON persons(person_category)"))

        rows = conn.execute(text("PRAGMA table_info(training_attendances)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "checked_in_at" not in cols:
                conn.execute(text("ALTER TABLE training_attendances ADD COLUMN checked_in_at DATETIME"))
            if "organization_id" not in cols:
                conn.execute(text("ALTER TABLE training_attendances ADD COLUMN organization_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_training_attendances_organization_id ON training_attendances(organization_id)"))
            conn.execute(text("""
                UPDATE training_attendances
                SET organization_id = (
                    SELECT persons.organization_id
                    FROM persons
                    WHERE persons.id = training_attendances.person_id
                )
                WHERE organization_id IS NULL
            """))
            conn.execute(text("""
                UPDATE training_attendances
                SET organization_id = (
                    SELECT training_sessions.organization_id
                    FROM training_sessions
                    WHERE training_sessions.id = training_attendances.session_id
                )
                WHERE organization_id IS NULL
            """))

        rows = conn.execute(text("PRAGMA table_info(training_sessions)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "is_active" not in cols:
                conn.execute(text("ALTER TABLE training_sessions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
            if "topic_id" not in cols:
                conn.execute(text("ALTER TABLE training_sessions ADD COLUMN topic_id INTEGER"))

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

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS org_type_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(64) NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_type_options_code ON org_type_options(code)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_org_type_options_is_active ON org_type_options(is_active)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS job_title_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(64) NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_job_title_options_is_active ON job_title_options(is_active)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS training_topic_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_training_topic_options_is_active ON training_topic_options(is_active)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category VARCHAR(64) NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                image_url VARCHAR(512),
                video_url VARCHAR(512),
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        rows = conn.execute(text("PRAGMA table_info(knowledge_articles)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "image_url" not in cols:
                conn.execute(text("ALTER TABLE knowledge_articles ADD COLUMN image_url VARCHAR(512)"))
            if "video_url" not in cols:
                conn.execute(text("ALTER TABLE knowledge_articles ADD COLUMN video_url VARCHAR(512)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_articles_category ON knowledge_articles(category)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_articles_is_active ON knowledge_articles(is_active)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(64) NOT NULL UNIQUE,
                value TEXT NOT NULL DEFAULT '',
                updated_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_settings_key ON app_settings(key)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_category_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(64) NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_category_options_code ON knowledge_category_options(code)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_category_options_is_active ON knowledge_category_options(is_active)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
