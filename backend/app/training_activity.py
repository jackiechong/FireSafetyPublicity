"""培训场次活动状态：有效结束时间、到期自动关闭扫码签到。"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import TrainingSession

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _local_day_bounds_utc(moment: datetime) -> tuple[datetime, datetime]:
    """给定 UTC/naive UTC 时间，返回其北京时间当天 [00:00, 次日 00:00) 对应的 naive UTC 边界。"""
    aware = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)
    local_dt = aware.astimezone(LOCAL_TZ)
    local_start = datetime.combine(local_dt.date(), time.min, tzinfo=LOCAL_TZ)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def today_bounds_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    return _local_day_bounds_utc(now or datetime.utcnow())


def end_of_local_day_utc(moment: datetime) -> datetime:
    return _local_day_bounds_utc(moment)[1]


def effective_end_utc(sess: TrainingSession) -> datetime:
    """培训结束时刻：显式 end_at 优先，否则按开始时间所在北京时间当天 24:00。"""
    if sess.end_at is not None:
        return sess.end_at
    return end_of_local_day_utc(sess.start_at)


def deactivate_expired_sessions(db: Session) -> int:
    """将已超过结束时间且仍为活动状态的场次标记为非活动。返回变更条数。"""
    now = datetime.utcnow()
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
    now = datetime.utcnow()
    if effective_end_utc(sess) <= now:
        return False, "本场培训已超过签到时限"
    return True, ""
