import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, async_session_factory
from schemas import (
    CourseListOut, CourseDetailOut, CourseOut, CourseModuleOut,
    CreateCourse, CreateModule, GenerateCourseInput, ErrorResponse,
)
import storage
from services.mistral_ai import generate_course_outline, generate_chapter_content
from services.image_service import fetch_images_for_chapter
from services.edge_tts_service import generate_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["courses"])


# ───────────────────────── Background pipeline ─────────────────────────

async def _generate_course_pipeline(course_id: int, title: str, audience: str, depth: str):
    """Full AI generation pipeline: outline → content → audio."""
    async with async_session_factory() as db:
        try:
            # Step 1: Generate outline via Mistral
            await storage.update_course_generation_status(
                db, course_id, "generating_outline",
                json.dumps({"step": "Generating course outline...", "pct": 5}),
            )

            outline = await generate_course_outline(title, audience, depth)

            # Update course with refined title/description/objectives
            await storage.update_course_details(
                db, course_id,
                title=outline.get("title", title),
                description=outline.get("description", "AI-generated course"),
                objectives=outline.get("objectives", []),
            )

            chapters = outline.get("chapters", [])
            total_chapters = len(chapters)

            if total_chapters == 0:
                await storage.update_course_generation_status(db, course_id, "failed",
                    json.dumps({"step": "No chapters generated", "pct": 0}))
                return

            # Step 2: Generate content for each chapter
            module_ids: list[int] = []
            tts_scripts: list[str] = []

            for i, chapter in enumerate(chapters, 1):
                pct = int(10 + (i / total_chapters) * 55)
                await storage.update_course_generation_status(
                    db, course_id, "generating_content",
                    json.dumps({"step": f"Generating chapter {i}/{total_chapters}: {chapter['title']}", "pct": pct}),
                )

                # Generate content
                chapter_data = await generate_chapter_content(
                    outline.get("title", title),
                    chapter["title"],
                    chapter.get("summary", ""),
                    audience,
                    depth,
                )

                # Fetch images
                search_terms = chapter.get("search_terms", [chapter["title"]])
                images = await fetch_images_for_chapter(search_terms, max_images=3)

                # Insert images into markdown content if we got any
                content = chapter_data.get("content", "")
                if images:
                    img_section = "\n\n---\n\n### 📷 Visual References\n\n"
                    for img_url in images:
                        img_section += f"![Illustration]({img_url})\n\n"
                    content += img_section

                # Save module
                quiz_json = json.dumps(chapter_data.get("quiz", {})) if chapter_data.get("quiz") else None
                module = await storage.create_course_module(
                    db,
                    course_id=course_id,
                    title=chapter["title"],
                    content=content,
                    sort_order=i,
                    quiz=quiz_json,
                    images=images,
                )
                module_ids.append(module.id)
                tts_scripts.append(chapter_data.get("tts_script", ""))

            # Step 3: Generate audio for each chapter
            for i, (mod_id, script) in enumerate(zip(module_ids, tts_scripts), 1):
                if not script or not script.strip():
                    continue

                pct = int(65 + (i / len(module_ids)) * 30)
                await storage.update_course_generation_status(
                    db, course_id, "generating_audio",
                    json.dumps({"step": f"Generating audio {i}/{len(module_ids)}", "pct": pct}),
                )

                try:
                    filename = f"course_{course_id}_module_{mod_id}.mp3"
                    audio_url = await generate_audio(script, filename)
                    await storage.update_module_audio(db, mod_id, audio_url)
                except Exception as e:
                    logger.warning(f"Audio generation failed for module {mod_id}: {e}")
                    # Continue - audio is optional

            # Step 4: Mark completed
            await storage.update_course_generation_status(
                db, course_id, "completed",
                json.dumps({"step": "Course generation complete!", "pct": 100}),
            )

        except Exception:
            logger.exception("Course generation failed for course_id=%s", course_id)
            async with async_session_factory() as err_db:
                await storage.update_course_generation_status(
                    err_db, course_id, "failed",
                    json.dumps({"step": "Generation failed. Please try again.", "pct": 0}),
                )


# ───────────────────────── Endpoints ─────────────────────────

@router.get("")
async def list_courses(db: AsyncSession = Depends(get_db)):
    courses = await storage.get_courses(db)
    result = []
    for item in courses:
        c = item["course"]
        data = CourseListOut.model_validate(c).model_dump(by_alias=True)
        if item["creator"]:
            from schemas import UserOut
            data["creator"] = UserOut.model_validate(item["creator"]).model_dump(by_alias=True)
        else:
            data["creator"] = None
        result.append(data)
    return result


@router.post("", status_code=201)
async def create_course(body: CreateCourse, db: AsyncSession = Depends(get_db)):
    course = await storage.create_course(
        db, title=body.title, description=body.description, status=body.status,
        created_by=body.created_by, objectives=body.objectives,
        audience=body.audience, depth=body.depth,
    )
    return CourseOut.model_validate(course).model_dump(by_alias=True)


@router.post("/generate", status_code=201)
async def generate_course(
    body: GenerateCourseInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a course and kick off AI generation in the background."""
    course = await storage.create_course(
        db,
        title=body.title,
        description="Generating...",
        status="draft",
        audience=body.audience,
        depth=body.depth,
    )
    await storage.update_course_generation_status(
        db, course.id, "generating_outline",
        json.dumps({"step": "Starting course generation...", "pct": 0}),
    )

    background_tasks.add_task(
        _generate_course_pipeline, course.id, body.title, body.audience, body.depth,
    )

    return CourseOut.model_validate(course).model_dump(by_alias=True)


@router.get("/{course_id}")
async def get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    data = await storage.get_course(db, course_id)
    if data is None:
        return Response(
            content=ErrorResponse(message="Course not found").model_dump_json(by_alias=True),
            status_code=404,
            media_type="application/json",
        )

    c = data["course"]
    result = CourseDetailOut.model_validate(c).model_dump(by_alias=True)
    result["modules"] = [CourseModuleOut.model_validate(m).model_dump(by_alias=True) for m in data["modules"]]
    if data["creator"]:
        from schemas import UserOut
        result["creator"] = UserOut.model_validate(data["creator"]).model_dump(by_alias=True)
    else:
        result["creator"] = None
    return result


@router.get("/{course_id}/modules")
async def list_modules(course_id: int, db: AsyncSession = Depends(get_db)):
    modules = await storage.get_course_modules(db, course_id)
    return [CourseModuleOut.model_validate(m).model_dump(by_alias=True) for m in modules]


@router.patch("/{course_id}/publish")
async def publish_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle course status between draft and published."""
    data = await storage.get_course(db, course_id)
    if data is None:
        return Response(
            content=ErrorResponse(message="Course not found").model_dump_json(by_alias=True),
            status_code=404,
            media_type="application/json",
        )
    course = data["course"]
    new_status = "published" if course.status != "published" else "draft"

    from sqlalchemy import update as sa_update
    from models import Course
    stmt = sa_update(Course).where(Course.id == course_id).values(status=new_status)
    await db.execute(stmt)
    await db.commit()

    # Re-fetch
    refreshed = await storage.get_course(db, course_id)
    c = refreshed["course"]
    result = CourseDetailOut.model_validate(c).model_dump(by_alias=True)
    result["modules"] = [CourseModuleOut.model_validate(m).model_dump(by_alias=True) for m in refreshed["modules"]]
    return result


@router.post("/{course_id}/modules", status_code=201)
async def create_module(course_id: int, body: CreateModule, db: AsyncSession = Depends(get_db)):
    module = await storage.create_course_module(
        db, course_id=course_id, title=body.title,
        content=body.content, sort_order=body.sort_order, quiz=body.quiz,
    )
    return CourseModuleOut.model_validate(module).model_dump(by_alias=True)
