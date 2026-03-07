import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_auth
from schemas import SpeakingPracticeOut, ErrorResponse
import storage
from services.mistral_ai import analyze_speaking_transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speaking", tags=["speaking"])


@router.get("")
async def list_practices(user_id: int = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    practices = await storage.get_speaking_practices(db, user_id)
    return [SpeakingPracticeOut.model_validate(p).model_dump(by_alias=True) for p in practices]


@router.post("", status_code=201)
async def create_practice(
    body: dict,
    user_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive prompt + transcript, run AI analysis, store and return results."""
    prompt = body.get("prompt", "")
    transcript = body.get("transcript", "")

    # AI-powered analysis
    analysis = {"pronunciation_score": 75.0, "fluency_score": 75.0,
                "feedback": "Keep practicing!", "corrections": ""}
    try:
        analysis = await analyze_speaking_transcript(prompt, transcript)
    except Exception as e:
        logger.warning(f"Speaking AI analysis failed: {e}")

    practice = await storage.create_speaking_practice(
        db, user_id=user_id, prompt=prompt,
        transcript=transcript,
        pronunciation_score=analysis.get("pronunciation_score"),
        fluency_score=analysis.get("fluency_score"),
        feedback=analysis.get("feedback"),
        corrections=analysis.get("corrections"),
    )

    # Fire notification
    try:
        await storage.create_notification(
            db, user_id=user_id,
            title="Speaking Practice Analyzed",
            message=f"Your practice has been analyzed. Pronunciation: {round(analysis.get('pronunciation_score', 0))}%, Fluency: {round(analysis.get('fluency_score', 0))}%.",
        )
    except Exception:
        pass

    return SpeakingPracticeOut.model_validate(practice).model_dump(by_alias=True)
