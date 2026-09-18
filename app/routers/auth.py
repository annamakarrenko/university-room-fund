from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    COOKIE_SECURE,
    SESSION_COOKIE,
    SESSION_TTL_HOURS,
    create_session,
    get_current_user,
    hash_password,
    token_digest,
    verify_password,
)
from app.database import get_db
from app.models import AuthSession, User
from app.schemas import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_HOURS * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    username = data.username.strip().lower()
    user = User(
        username=username,
        display_name=data.display_name.strip(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from None
    db.refresh(user)

    token, _ = create_session(db, user)
    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    username = data.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token, _ = create_session(db, user)
    set_session_cookie(response, token)
    return user


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = (
            db.query(AuthSession)
            .filter(AuthSession.token_hash == token_digest(token))
            .first()
        )
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
