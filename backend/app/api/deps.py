from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from .. import crud, schemas
from ..core import security
from ..core.config import settings
from ..db.base import get_db
from ..db import models

# 这会创建一个OAuth2兼容的安全方案
# tokenUrl 指向我们获取token的登录接口
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"/api/v1/auth/token"
)


def get_current_user(
        db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    """
    依赖项：获取当前用户。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
        current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    依赖项：获取当前活跃用户。
    (未来可以扩展，比如检查用户是否被禁用)
    """
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(
        current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    依赖项：获取当前管理员用户。
    如果用户不是管理员，则会抛出HTTPException。
    """
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user