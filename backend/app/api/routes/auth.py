from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.auth import authenticate_user, create_access_token, get_current_user, revoke_current_token, user_read
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.schemas.auth import LoginRequest, LoginResponse, UserRead

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, request.username.strip(), request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(db, user)
    return LoginResponse(access_token=token.token, user=user_read(user))


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return user_read(user)


@router.post("/auth/logout", status_code=204)
def logout(_: User = Depends(get_current_user), revoke: None = Depends(revoke_current_token)) -> None:
    return None
