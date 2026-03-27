import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.issue import Issue
from app.models.user import User
from app.schemas.dashboard import DashboardMetrics, StatusCount, CategoryCount

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

CACHE_TTL_SECONDS = 60


async def _get_redis():
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    cache_key = f"dashboard:metrics:{tenant_id}"

    r = await _get_redis()
    try:
        cached = await r.get(cache_key)
        if cached:
            return DashboardMetrics.model_validate_json(cached)
    except Exception:
        pass

    total_result = await db.execute(
        select(func.count(Issue.id)).where(Issue.tenant_id == tenant_id)
    )
    total_issues = total_result.scalar() or 0

    status_result = await db.execute(
        select(Issue.status, func.count(Issue.id))
        .where(Issue.tenant_id == tenant_id)
        .group_by(Issue.status)
    )
    issues_by_status = [StatusCount(status=row[0], count=row[1]) for row in status_result.all()]

    category_result = await db.execute(
        select(Issue.category, func.count(Issue.id))
        .where(Issue.tenant_id == tenant_id)
        .group_by(Issue.category)
    )
    issues_by_category = [CategoryCount(category=row[0], count=row[1]) for row in category_result.all()]

    overdue_result = await db.execute(
        select(func.count(Issue.id))
        .where(Issue.tenant_id == tenant_id, Issue.is_overdue == True)
    )
    overdue_count = overdue_result.scalar() or 0

    sla_breach_percentage = (overdue_count / total_issues * 100) if total_issues > 0 else 0.0

    resolved_result = await db.execute(
        select(func.count(Issue.id))
        .where(Issue.tenant_id == tenant_id, Issue.resolved_at != None)
    )
    resolved_count = resolved_result.scalar() or 0

    avg_result = await db.execute(
        select(
            func.avg(
                extract("epoch", Issue.resolved_at - Issue.created_at) / 3600
            )
        ).where(
            Issue.tenant_id == tenant_id,
            Issue.resolved_at != None,
        )
    )
    average_resolution_hours = round(avg_result.scalar() or 0.0, 2)

    metrics = DashboardMetrics(
        total_issues=total_issues,
        issues_by_status=issues_by_status,
        issues_by_category=issues_by_category,
        sla_breach_percentage=round(sla_breach_percentage, 2),
        average_resolution_hours=average_resolution_hours,
        overdue_count=overdue_count,
        resolved_count=resolved_count,
    )

    try:
        await r.set(cache_key, metrics.model_dump_json(), ex=CACHE_TTL_SECONDS)
    except Exception:
        pass

    return metrics
