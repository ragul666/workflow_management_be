from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue
from app.services.event_bus import event_bus


class SLAService:
    @staticmethod
    async def check_overdue_issues(db: AsyncSession):
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Issue).where(
                and_(
                    Issue.due_date != None,
                    Issue.due_date < now,
                    Issue.is_overdue == False,
                    Issue.resolved_at == None,
                )
            )
        )
        issues = result.scalars().all()
        count = 0

        for issue in issues:
            issue.is_overdue = True
            count += 1
            await event_bus.emit("SLABreached", {
                "issue_id": str(issue.id),
                "tenant_id": str(issue.tenant_id),
                "title": issue.title,
            })

        if count > 0:
            await db.commit()
        return count

    @staticmethod
    def get_sla_remaining(due_date: datetime) -> dict:
        if not due_date:
            return {"remaining_seconds": None, "is_overdue": False}

        now = datetime.now(timezone.utc)
        diff = due_date - now
        total_seconds = int(diff.total_seconds())
        return {
            "remaining_seconds": max(total_seconds, 0),
            "is_overdue": total_seconds < 0,
        }


sla_service = SLAService()
