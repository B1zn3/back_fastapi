from fastapi import Depends, HTTPException, status
from src.deps.auth_deps import get_current_user
from src.models.model import User

def require_role(required_role: str):
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role or current_user.role.name != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется роль: {required_role}"
            )
        return current_user
    return role_dependency