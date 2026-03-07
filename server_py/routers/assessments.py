import json
import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_auth
from schemas import ErrorResponse
import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.get("/available")
async def get_available(
    user_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return modules with quiz data from enrolled courses the user hasn't taken yet."""
    items = await storage.get_available_assessments(db, user_id)
    result = []
    for item in items:
        quiz_data = {}
        try:
            quiz_data = json.loads(item["quiz"]) if item["quiz"] else {}
        except Exception:
            pass
        questions = quiz_data.get("questions", [])
        result.append({
            "moduleId": item["module_id"],
            "moduleTitle": item["module_title"],
            "courseId": item["course_id"],
            "courseTitle": item["course_title"],
            "enrollmentId": item["enrollment_id"],
            "questionCount": len(questions),
            "questions": questions,
        })
    return result


@router.get("/history")
async def get_history(
    user_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return past assessment results for the current user."""
    assessments = await storage.get_assessment_history(db, user_id)
    result = []
    for a in assessments:
        # Get module title
        module_title = "Unknown"
        try:
            from sqlalchemy import select
            from models import CourseModule, Course
            mod_q = await db.execute(select(CourseModule).where(CourseModule.id == a.module_id))
            mod = mod_q.scalar_one_or_none()
            if mod:
                module_title = mod.title
                course_q = await db.execute(select(Course).where(Course.id == mod.course_id))
                course = course_q.scalar_one_or_none()
                course_title = course.title if course else "Unknown"
            else:
                course_title = "Unknown"
        except Exception:
            course_title = "Unknown"
        result.append({
            "id": a.id,
            "moduleId": a.module_id,
            "moduleTitle": module_title,
            "courseId": a.course_id,
            "courseTitle": course_title,
            "score": a.score,
            "answers": a.answers,
            "submittedAt": a.submitted_at.isoformat() if a.submitted_at else None,
        })
    return result


@router.post("/submit")
async def submit_assessment(
    body: dict,
    user_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Score answers against the module's quiz JSON and persist result."""
    module_id: int = body.get("moduleId")
    answers: list = body.get("answers", [])  # list of chosen option indices

    if not module_id:
        return Response(
            content=ErrorResponse(message="moduleId required").model_dump_json(),
            status_code=400, media_type="application/json",
        )

    # Load the module and its quiz
    from sqlalchemy import select
    from models import CourseModule
    mod_q = await db.execute(select(CourseModule).where(CourseModule.id == module_id))
    module = mod_q.scalar_one_or_none()
    if not module or not module.quiz:
        return Response(
            content=ErrorResponse(message="Quiz not found for this module").model_dump_json(),
            status_code=404, media_type="application/json",
        )

    try:
        quiz = json.loads(module.quiz)
    except Exception:
        return Response(
            content=ErrorResponse(message="Invalid quiz data").model_dump_json(),
            status_code=500, media_type="application/json",
        )

    questions = quiz.get("questions", [])
    if not questions:
        return Response(
            content=ErrorResponse(message="No questions in quiz").model_dump_json(),
            status_code=400, media_type="application/json",
        )

    # Score: count correct answers
    correct = 0
    for i, q in enumerate(questions):
        if i < len(answers) and answers[i] == q.get("correct"):
            correct += 1
    score = round(correct / len(questions) * 100, 1)

    # Persist assessment
    assessment = await storage.create_assessment(
        db, user_id=user_id, course_id=module.course_id,
        module_id=module_id, score=score, answers=answers,
    )

    # Fetch module title for notification
    course_q = await db.execute(
        select(__import__("models", fromlist=["Course"]).Course)
        .where(__import__("models", fromlist=["Course"]).Course.id == module.course_id)
    )
    course = course_q.scalar_one_or_none()
    course_title = course.title if course else "your course"

    # Fire notification
    await storage.create_notification(
        db, user_id=user_id,
        title="Assessment Submitted",
        message=f"You scored {score}% on '{module.title}' in {course_title}.",
    )

    return {
        "id": assessment.id,
        "score": score,
        "correct": correct,
        "total": len(questions),
        "moduleId": module_id,
        "moduleTitle": module.title,
    }
