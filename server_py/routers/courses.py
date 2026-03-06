from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import (
    CourseListOut, CourseDetailOut, CourseOut, CourseModuleOut,
    CreateCourse, CreateModule, ErrorResponse,
)
import storage

router = APIRouter(prefix="/api/courses", tags=["courses"])


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


@router.post("/{course_id}/modules", status_code=201)
async def create_module(course_id: int, body: CreateModule, db: AsyncSession = Depends(get_db)):
    module = await storage.create_course_module(
        db, course_id=course_id, title=body.title,
        content=body.content, sort_order=body.sort_order, quiz=body.quiz,
    )
    return CourseModuleOut.model_validate(module).model_dump(by_alias=True)
