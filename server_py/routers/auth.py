from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user_id
from schemas import LoginInput, RegisterInput, UserOut, ErrorResponse, MessageResponse
from session import create_session, delete_session, COOKIE_NAME, MAX_AGE_DAYS
import storage

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginInput, response: Response, db: AsyncSession = Depends(get_db)):
    user = await storage.get_user_by_email(db, body.email)
    if not user or user.password != body.password:
        return Response(
            content=ErrorResponse(message="Invalid email or password").model_dump_json(by_alias=True),
            status_code=401,
            media_type="application/json",
        )

    sid = await create_session(db, user.id)
    response.set_cookie(
        COOKIE_NAME, sid,
        httponly=True, max_age=MAX_AGE_DAYS * 24 * 60 * 60, samesite="lax",
    )
    return UserOut.model_validate(user).model_dump(by_alias=True)


@router.post("/register", status_code=201)
async def register(body: RegisterInput, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await storage.get_user_by_email(db, body.email)
    if existing:
        return Response(
            content=ErrorResponse(message="User already exists", field="email").model_dump_json(by_alias=True),
            status_code=400,
            media_type="application/json",
        )

    user = await storage.create_user(
        db, email=body.email, password=body.password,
        full_name=body.full_name, role=body.role,
    )
    sid = await create_session(db, user.id)
    response.set_cookie(
        COOKIE_NAME, sid,
        httponly=True, max_age=MAX_AGE_DAYS * 24 * 60 * 60, samesite="lax",
    )
    return UserOut.model_validate(user).model_dump(by_alias=True)


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), user_id: int | None = Depends(get_current_user_id)):
    if user_id is None:
        return Response(
            content=ErrorResponse(message="Not authenticated").model_dump_json(by_alias=True),
            status_code=401,
            media_type="application/json",
        )

    user = await storage.get_user(db, user_id)
    if not user:
        return Response(
            content=ErrorResponse(message="Not authenticated").model_dump_json(by_alias=True),
            status_code=401,
            media_type="application/json",
        )

    return UserOut.model_validate(user).model_dump(by_alias=True)


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    sid = request.cookies.get(COOKIE_NAME)
    if sid:
        await delete_session(db, sid)
    response.delete_cookie(COOKIE_NAME)
    return MessageResponse(message="Logged out").model_dump(by_alias=True)
