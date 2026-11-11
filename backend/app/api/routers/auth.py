from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Any

from ... import crud, schemas
from ...db.base import get_db
from ...core import security

router = APIRouter()


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Auth"])
@router.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Auth"], include_in_schema=False)
def create_new_user(user: schemas.UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    公开注册普通用户。管理员账号只能由后台管理员维护。
    """
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册",
        )
    if user.email and crud.get_user_by_email(db, email=str(user.email)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )
    try:
        return crud.create_user(db=db, user=user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已被注册",
        )


@router.post("/token", response_model=schemas.Token, tags=["Auth"])
def login_for_access_token(
        db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    用户登录以获取 Access Token。
    使用表单数据 (form data): username 和 password。
    """
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(
        data={"sub": user.username}
    )

    return {"access_token": access_token, "token_type": "bearer"}
