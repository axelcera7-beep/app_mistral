"""Auth routes — extracted from main.py without modification."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/auth/register", response_model=AuthResponse)
def api_register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check uniqueness
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris.")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé.")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    logger.info("User registered: %s", user.username)
    return AuthResponse(token=token, username=user.username)


@router.post("/api/auth/login", response_model=AuthResponse)
def api_login(body: LoginRequest, db: Session = Depends(get_db)):
    """Login an existing user."""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    token = create_access_token(user.id, user.username)
    logger.info("User logged in: %s", user.username)
    return AuthResponse(token=token, username=user.username)


@router.get("/api/auth/me", response_model=UserResponse)
def api_me(user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(id=user.id, username=user.username, email=user.email)
