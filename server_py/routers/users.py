from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserOut
import storage

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await storage.get_users(db)
    return [UserOut.model_validate(u).model_dump(by_alias=True) for u in users]
