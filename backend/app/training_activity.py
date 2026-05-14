"""培训场次活动状态：有效结束时间、到期自动关闭扫码签到。"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import TrainingSession


def effective_end_utc(sess: TrainingSession) -> datetime:
    """培训结束时刻：显式 end_at 优先，否则按开始时间 + 计划时长。"""
    if sess.end_at is not None:
        return sess.end_at
    return sess.start_at + timedelta(minutes=int(sess.duration_minutes or 0))


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
