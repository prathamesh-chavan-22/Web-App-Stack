from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_auth
from schemas import SpeakingPracticeOut, CreateSpeakingPractice, ErrorResponse
import storage

router = APIRouter(prefix="/api/speaking", tags=["speaking"])


@router.get("")
async def list_practices(user_id: int = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    practices = await storage.get_speaking_practices(db, user_id)
    return [SpeakingPracticeOut.model_validate(p).model_dump(by_alias=True) for p in practices]


@router.post("", status_code=201)
async def create_practice(
    body: CreateSpeakingPractice,
    user_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    practice = await storage.create_speaking_practice(
        db, user_id=user_id, prompt=body.prompt,
        transcript=body.transcript, audio_url=body.audio_url,
        pronunciation_score=body.pronunciation_score,
        fluency_score=body.fluency_score,
        feedback=body.feedback, corrections=body.corrections,
    )
    return SpeakingPracticeOut.model_validate(practice).model_dump(by_alias=True)
