"""培训场次活动状态：有效结束时间、到期自动关闭扫码签到。"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import TrainingSession

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def now_local() -> datetime:
    """当前北京时间（naive datetime，与数据库及前端展示口径一致）。"""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def _local_day_bounds_utc(moment: datetime) -> tuple[datetime, datetime]:
    """给定北京时间（naive 或 aware），返回其北京时间当天 [00:00, 次日 00:00) 的 naive 边界。"""
    local_dt = moment.astimezone(LOCAL_TZ).replace(tzinfo=None) if moment.tzinfo is not None else moment
    local_start = datetime.combine(local_dt.date(), time.min)
    local_end = local_start + timedelta(days=1)
    return local_start, local_end


def today_bounds_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    return _local_day_bounds_utc(now or now_local())


def end_of_local_day_utc(moment: datetime) -> datetime:
    return _local_day_bounds_utc(moment)[1]


def effective_end_utc(sess: TrainingSession) -> datetime:
    """培训结束时刻：显式 end_at 优先（兼容旧库 UTC 16:00 自动跨日边界），否则按开始时间所在北京时间当天 24:00。"""
    day_end = end_of_local_day_utc(sess.start_at)
    if sess.end_at is not None:
        if sess.is_active and sess.end_at.time() == time(16, 0) and sess.end_at < day_end:
            return day_end
        return sess.end_at
    return day_end


def deactivate_expired_sessions(db: Session) -> int:
    """将已超过结束时间且仍为活动状态的场次标记为非活动。返回变更条数。"""
    now = now_local()
    changed = 0
    for s in db.query(TrainingSession).filter(TrainingSession.is_active.is_(True)).all():
        try:
            if effective_end_utc(s) <= now:
                s.is_active = False
                changed += 1
        except Exception:
            continue
    if changed:
        db.commit()
    return changed


def session_allows_checkin(sess: TrainingSession, db: Session) -> tuple[bool, str]:
    """是否允许学员扫码签到。"""
    deactivate_expired_sessions(db)
    db.refresh(sess)
    if not sess.is_active:
        return False, "本场培训已结束或未开放扫码签到"
    now = now_local()
    if effective_end_utc(sess) <= now:
        return False, "本场培训已超过签到时限"
    return True, ""
