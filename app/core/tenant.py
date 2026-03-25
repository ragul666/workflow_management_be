import uuid
from contextvars import ContextVar

tenant_context: ContextVar[uuid.UUID] = ContextVar("tenant_context")


def set_tenant(tenant_id: uuid.UUID):
    tenant_context.set(tenant_id)


def get_tenant() -> uuid.UUID:
    return tenant_context.get()
