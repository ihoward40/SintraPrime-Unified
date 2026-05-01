"""Admin service for dashboard operations."""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timezone, timedelta
from portal.models import User, AuditLog

class AdminService:
    """Admin dashboard service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_stats(self):
        """Get user statistics."""
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        active_today = self.db.query(func.count(User.id)).filter(
            User.last_login >= datetime.now(timezone.utc) - timedelta(days=1)
        ).scalar() or 0
        return {"total": total_users, "active_today": active_today}
    
    def get_audit_logs(self, limit: int = 100):
        """Retrieve recent audit logs."""
        logs = self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource": log.resource,
                "timestamp": log.created_at.isoformat(),
                "status": log.status,
            }
            for log in logs
        ]
    
    def get_system_health(self):
        """Get system health metrics."""
        return {
            "database": "healthy",
            "cache": "healthy",
            "auth_service": "healthy",
            "uptime_seconds": 3600,
        }
