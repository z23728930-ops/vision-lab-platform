from sqlalchemy.orm import Session
from typing import Optional, List
from ..db import models
from ..schemas import user as user_schema
from ..core.security import get_password_hash


def get_user(db: Session, user_id: int) -> Optional[models.User]: # <-- 修改返回类型提示
    """通过ID查询用户"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]: # <-- 修改返回类型提示
    """通过用户名查询用户"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """通过邮箱查询用户。"""
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]: # <-- 保持不变，或根据Python版本使用typing.List
    """获取用户列表"""
    return db.query(models.User).offset(skip).limit(limit).all()

def delete_user(db: Session, user_id: int) -> Optional[models.User]: # <-- 修改返回类型提示
    """通过ID删除用户"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def create_user(db: Session, user: user_schema.UserCreate) -> models.User:
    """创建新用户"""
    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        email=user.email,
        receive_notifications=user.receive_notifications,
        # 公开注册只能创建普通用户，管理员由现有管理员在后台维护。
        role=models.UserRole.user,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: models.User, user_in: user_schema.UserUpdate) -> Optional[models.User]:
    """
    更新用户信息。
    db_user: 要更新的数据库用户对象。
    user_in: 包含更新数据的Pydantic模型。
    """
    update_data = user_in.model_dump(exclude_unset=True) # 只包含已设置的字段

    # 如果有新密码，则哈希
    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    else:
        # 确保如果密码没有提供，不要覆盖现有的password_hash
        update_data.pop("password", None)

    # 遍历更新数据并应用到db_user对象
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
