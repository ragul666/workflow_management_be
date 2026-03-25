from functools import wraps
from typing import List

from fastapi import HTTPException, status


def require_permissions(*permissions: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

            user_permissions = set()
            for ur in current_user.user_roles:
                for rp in ur.role.role_permissions:
                    user_permissions.add(rp.permission.codename)

            for perm in permissions:
                if perm not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {perm}"
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_user_roles(user) -> List[str]:
    return [ur.role.name for ur in user.user_roles]


def get_user_permissions(user) -> set:
    permissions = set()
    for ur in user.user_roles:
        for rp in ur.role.role_permissions:
            permissions.add(rp.permission.codename)
    return permissions


def has_role(user, role_name: str) -> bool:
    return role_name in get_user_roles(user)


def has_permission(user, permission_codename: str) -> bool:
    return permission_codename in get_user_permissions(user)
