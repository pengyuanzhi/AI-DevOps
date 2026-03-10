"""
认证相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...db.session import get_db_session
from ...db.models import User
from ...schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
):
    """
    用户登录
    """
    # TODO: 实现真实的认证逻辑
    # 1. 验证用户名和密码
    # 2. 生成JWT token
    # 3. 返回token和用户信息

    # 临时实现：总是返回成功
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        # 如果用户不存在，创建一个临时用户用于开发
        user = User(
            username=form_data.username,
            email=f"{form_data.username}@example.com",
            gitlab_user_id=1,
            role="admin",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 生成token（临时实现）
    from datetime import timedelta
    import secrets

    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout():
    """
    用户登出
    """
    # TODO: 实现token黑名单机制
    return {"message": "已成功登出"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session),
):
    """
    获取当前用户信息
    """
    # TODO: 从token中解析用户ID
    # 临时实现：返回第一个用户
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(refresh_token: str):
    """
    刷新Token
    """
    # TODO: 实现token刷新逻辑
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="功能尚未实现",
    )
