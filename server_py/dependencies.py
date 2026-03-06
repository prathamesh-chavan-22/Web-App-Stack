from typing import Optional

from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from session import get_session_user_id, COOKIE_NAME


async def get_current_user_id(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[int]:
    sid = request.cookies.get(COOKIE_NAME)
    if not sid:
        return None
    return await get_session_user_id(db, sid)


async def require_auth(user_id: Optional[int] = Depends(get_current_user_id)) -> int:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
