from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, List

from starlette import status

from ... import crud, schemas
from ...db import models
from ..deps import get_current_active_user, get_current_admin_user
from ...db.base import get_db

router = APIRouter()


@router.get("/me", response_model=schemas.User, tags=["Users"])
def read_users_me(
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    获取当前用户信息。这是一个受保护的端点。
    """
    return current_user


# --- 新增：更新当前用户信息 ---
@router.put("/me", response_model=schemas.User, tags=["Users"])
def update_users_me(
        user_in: schemas.UserUpdate,  # 使用 UserUpdate Schema
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户的个人信息 (包括密码、邮箱、通知偏好)。
    用户不能修改自己的角色。
    """
    # 确保用户不能通过这个接口修改自己的角色
    if user_in.role is not None and user_in.role != current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to change your own role."
        )

    # 检查更新的用户名是否已存在且不是当前用户
    if user_in.username and user_in.username != current_user.username:
        existing_user = crud.get_user_by_username(db, username=user_in.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered."
            )

    # 检查更新的邮箱是否已存在且不是当前用户
    if user_in.email and user_in.email != current_user.email:
        existing_user_with_email = db.query(models.User).filter(models.User.email == user_in.email).first()
        if existing_user_with_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

    updated_user = crud.update_user(db, db_user=current_user, user_in=user_in)
    return updated_user


# -----------------------------

@router.get("/admin-check", response_model=schemas.User, tags=["Users"])
def check_if_admin(
        current_user: models.User = Depends(get_current_admin_user)
) -> Any:
    """
    检查当前用户是否为管理员。这是一个只有管理员能访问的端点。
    """
    return current_user

# app/api/routers/users.py
# ...
@router.post("/", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
def create_new_user_by_admin(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """(Admin) 创建新用户。"""
    # 此处省略了检查用户名是否重复的逻辑，你可以在crud中添加
    return crud.create_user(db, user=user_in)

@router.get("/", response_model=List[schemas.User], dependencies=[Depends(get_current_admin_user)])
def read_all_users(db: Session = Depends(get_db)):
    """(Admin) 获取所有用户信息。"""
    return crud.get_users(db) # 假设crud.get_users已实现


@router.delete("/{user_id}", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
def delete_existing_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_admin_user)
):
    """(Admin) 删除用户"""
    if current_user.id == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot delete themselves.")

    user_to_delete = crud.get_user(db, user_id=user_id)  # 假设crud.get_user存在
    if not user_to_delete:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    return crud.delete_user(db, user_id=user_id)