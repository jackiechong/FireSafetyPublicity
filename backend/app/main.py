import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.database import Base, SessionLocal, engine, sqlite_migrate_legacy_person_columns
from app.models import Organization, Person, TrainingAttendance, TrainingSession
from app.routers import admin, mp, wxoa
from app.seed import seed

os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)

startup_state = {"seed_ok": False, "seed_error": None}


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    sqlite_migrate_legacy_person_columns()
    seed()
    startup_state["seed_ok"] = True
    startup_state["seed_error"] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        initialize_database()
    except Exception as exc:
        startup_state["seed_ok"] = False
        startup_state["seed_error"] = repr(exc)
        raise
    yield


app = FastAPI(title="葫芦岛消防培训实名制 API", version="0.1.0", lifespan=lifespan)

# 与 allow_credentials=True 不能同时使用 allow_origins=["*"]，否则浏览器对带 Authorization 的请求 CORS 行为异常。
# 开发环境前端常用 127.0.0.1:5173；直连 API（VITE_API_BASE）时需显式放行来源。
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(mp.router)
app.include_router(wxoa.router)


@app.get("/")
def root():
    """根路径无业务接口，引导到 Swagger 文档。"""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    db = SessionLocal()
    try:
        return {
            "status": "ok",
            "seed_ok": startup_state["seed_ok"],
            "seed_error": startup_state["seed_error"],
            "counts": {
                "organizations": db.query(Organization).count(),
                "persons": db.query(Person).count(),
                "trainings": db.query(TrainingSession).count(),
                "attendances": db.query(TrainingAttendance).count(),
            },
        }
    finally:
        db.close()
