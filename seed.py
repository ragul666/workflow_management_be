import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, Role, Permission, RolePermission, UserRole
from app.models.workflow import WorkflowState, WorkflowTransition
from app.models.issue import Issue
from app.models.audit import AuditLog
from app.models.ai_summary import AISummary
from app.models.attachment import Attachment

PERMISSIONS = [
    ("issue:create", "Create issues"),
    ("issue:read", "Read issues"),
    ("issue:update", "Update issues"),
    ("issue:delete", "Delete issues"),
    ("issue:transition", "Transition issue status"),
    ("issue:assign", "Assign issues"),
    ("workflow:read", "Read workflow configuration"),
    ("workflow:manage", "Manage workflow states and transitions"),
    ("dashboard:read", "View dashboard metrics"),
    ("ai:generate", "Generate AI summaries"),
    ("audit:read", "Read audit logs"),
    ("user:manage", "Manage users"),
]

ROLE_PERMISSIONS = {
    "admin": [p[0] for p in PERMISSIONS],
    "manager": [
        "issue:create", "issue:read", "issue:update", "issue:transition",
        "issue:assign", "workflow:read", "dashboard:read", "ai:generate", "audit:read",
    ],
    "reviewer": [
        "issue:read", "issue:update", "issue:transition",
        "workflow:read", "dashboard:read", "ai:generate", "audit:read",
    ],
    "user": [
        "issue:create", "issue:read", "issue:update",
        "workflow:read", "dashboard:read",
    ],
}

WORKFLOW_STATES = [
    ("Draft", "draft", 0, True, False),
    ("Submitted", "submitted", 1, False, False),
    ("Under Review", "under_review", 2, False, False),
    ("Approved", "approved", 3, False, True),
    ("Closed", "closed", 4, False, True),
    ("Rejected", "rejected", 5, False, True),
]

WORKFLOW_TRANSITIONS = [
    ("draft", "submitted", ["admin", "manager", "reviewer", "user"]),
    ("submitted", "under_review", ["admin", "manager"]),
    ("under_review", "approved", ["admin", "manager", "reviewer"]),
    ("under_review", "rejected", ["admin", "manager", "reviewer"]),
    ("approved", "closed", ["admin", "manager"]),
    ("rejected", "draft", ["admin", "manager", "user"]),
    ("submitted", "draft", ["admin", "manager"]),
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        tenant = Tenant(name="MedTech Corp", slug="medtech")
        db.add(tenant)
        await db.flush()

        tenant2 = Tenant(name="PharmaCo", slug="pharmaco")
        db.add(tenant2)
        await db.flush()

        perm_map = {}
        for codename, desc in PERMISSIONS:
            perm = Permission(codename=codename, description=desc)
            db.add(perm)
            await db.flush()
            perm_map[codename] = perm

        role_map = {}
        for role_name, perm_codes in ROLE_PERMISSIONS.items():
            role = Role(name=role_name, description=f"{role_name.title()} role")
            db.add(role)
            await db.flush()
            role_map[role_name] = role

            for code in perm_codes:
                rp = RolePermission(role_id=role.id, permission_id=perm_map[code].id)
                db.add(rp)

        await db.flush()

        users_data = [
            ("admin@medtech.com", "admin123", "Ragul K V", tenant.id, "admin"),
            ("manager@medtech.com", "manager123", "Santhosh M", tenant.id, "manager"),
            ("reviewer@medtech.com", "reviewer123", "Vignesh R", tenant.id, "reviewer"),
            ("user@medtech.com", "user123", "Suresh K", tenant.id, "user"),
            ("admin@pharmaco.com", "admin123", "Rajesh K", tenant2.id, "admin"),
        ]

        user_objects = []
        for email, password, name, tid, role_name in users_data:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=name,
                tenant_id=tid,
            )
            db.add(user)
            await db.flush()
            user_objects.append(user)

            ur = UserRole(user_id=user.id, role_id=role_map[role_name].id)
            db.add(ur)

        await db.flush()

        for name, slug, order, is_initial, is_terminal in WORKFLOW_STATES:
            for t in [tenant, tenant2]:
                state = WorkflowState(
                    name=name,
                    slug=slug,
                    display_order=order,
                    is_initial=is_initial,
                    is_terminal=is_terminal,
                    tenant_id=t.id,
                )
                db.add(state)

        await db.flush()

        for from_s, to_s, roles in WORKFLOW_TRANSITIONS:
            for t in [tenant, tenant2]:
                trans = WorkflowTransition(
                    from_state=from_s,
                    to_state=to_s,
                    allowed_roles=roles,
                    tenant_id=t.id,
                )
                db.add(trans)

        await db.flush()

        admin_user = user_objects[0]
        manager_user = user_objects[1]
        now = datetime.now(timezone.utc)

        sample_issues = [
            ("Equipment Calibration Deviation", "Automated packaging line PL-3 showed calibration drift exceeding acceptable tolerance limits during routine QC check. Temperature readings off by 2.3 degrees Celsius.", "quality", "high", "submitted", now + timedelta(days=3), False),
            ("Raw Material Contamination Report", "Batch RM-2024-156 of active pharmaceutical ingredient showed trace contamination levels above ICH Q3D limits for elemental impurities.", "compliance", "critical", "under_review", now + timedelta(days=1), False),
            ("SOP Update Required - Clean Room Protocol", "Current SOP-CR-012 does not reflect updated ISO 14644-1:2015 classification requirements for Grade A clean rooms.", "regulatory", "medium", "draft", now + timedelta(days=14), False),
            ("Supplier Audit Finding - Cold Chain", "During annual supplier audit of LogiTemp Inc., temperature excursions were found in 3 of 50 sampled shipment records.", "operational", "high", "approved", now - timedelta(days=2), False),
            ("Overdue CAPA Implementation", "Corrective action for non-conformance NC-2024-089 has exceeded its 30-day implementation deadline.", "compliance", "critical", "submitted", now - timedelta(days=5), True),
            ("Water System Qualification", "Annual requalification of purified water system WS-02 is due. Previous qualification showed bioburden levels approaching alert limits.", "quality", "medium", "draft", now + timedelta(days=7), False),
        ]

        for title, desc, cat, prio, stat, due, overdue in sample_issues:
            issue = Issue(
                title=title,
                description=desc,
                category=cat,
                priority=prio,
                status=stat,
                due_date=due,
                is_overdue=overdue,
                tenant_id=tenant.id,
                created_by=admin_user.id,
                assigned_to=manager_user.id,
            )
            db.add(issue)
            await db.flush()

            audit = AuditLog(
                entity_type="issue",
                entity_id=issue.id,
                issue_id=issue.id,
                action="created",
                field_name="status",
                new_value=stat,
                user_id=admin_user.id,
                tenant_id=tenant.id,
            )
            db.add(audit)

        await db.commit()

    await engine.dispose()
    print("Seed data created successfully")


if __name__ == "__main__":
    asyncio.run(seed())
