# app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from ..db.models import UserRole

# 共用的基础属性
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    email: Optional[EmailStr] = None # 邮箱字段，使用 EmailStr 类型验证格式
    receive_notifications: bool = True # 是否接收通知，默认为 True

# 创建用户时需要的属性 (从API接收)
class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=72)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[EmailStr]) -> Optional[EmailStr]:
        return value.lower() if value else value

# 用于更新用户信息的Pydantic模型
# 所有字段都是可选的，这样可以实现部分更新
class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None # 允许修改密码
    email: Optional[EmailStr] = None
    receive_notifications: Optional[bool] = None
    role: Optional[UserRole] = None # 只有管理员才能修改角色

# 从数据库读取并返回给API的属性
class User(UserBase): # 继承 UserBase 以包含 email 和 receive_notifications
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True # 允许Pydantic从ORM对象(如SQLAlchemy模型)转换数据
