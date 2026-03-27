from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import engine, Base

# Import all models first to ensure proper mapper configuration
from app.models.tenant import Tenant
from app.models.user import User, Role, Permission, RolePermission, UserRole
from app.models.workflow import WorkflowState, WorkflowTransition
from app.models.issue import Issue
from app.models.audit import AuditLog
from app.models.ai_summary import AISummary
from app.models.attachment import Attachment

from app.api.routes import auth, issues, workflow, dashboard, ai
from app.services.websocket_manager import ws_manager
from app.services.event_bus import event_bus

limiter = Limiter(key_func=get_remote_address)


async def on_issue_updated(payload):
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        await ws_manager.broadcast_to_tenant(tenant_id, {
            "type": "issue_updated",
            "data": payload,
        })


async def on_issue_created(payload):
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        await ws_manager.broadcast_to_tenant(tenant_id, {
            "type": "issue_created",
            "data": payload,
        })


async def on_sla_breached(payload):
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        await ws_manager.broadcast_to_tenant(tenant_id, {
            "type": "sla_breached",
            "data": payload,
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    event_bus.register("IssueCreated", on_issue_created)
    event_bus.register("IssueUpdated", on_issue_updated)
    event_bus.register("SLABreached", on_sla_breached)

    yield

    event_bus.clear()


app = FastAPI(
    title="Compliance & Workflow Management System",
    version="1.0.0",
    description="AI-Powered multi-tenant compliance and issue management platform",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(issues.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    from app.core.security import decode_token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    token_tenant = payload.get("tenant_id")
    if token_tenant != tenant_id:
        await websocket.close(code=4003, reason="Tenant mismatch")
        return

    await ws_manager.connect(tenant_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(tenant_id, websocket)


@app.get("/health")
async def health():
    return {"status": "healthy"}
