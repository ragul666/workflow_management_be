from typing import List, Dict

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class DashboardMetrics(BaseModel):
    total_issues: int
    issues_by_status: List[StatusCount]
    issues_by_category: List[CategoryCount]
    sla_breach_percentage: float
    average_resolution_hours: float
    overdue_count: int
    resolved_count: int
