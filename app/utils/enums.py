import enum


class RoleType(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    USER = "user"


class IssueCategory(str, enum.Enum):
    COMPLIANCE = "compliance"
    QUALITY = "quality"
    SAFETY = "safety"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"


class IssuePriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
