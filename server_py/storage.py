from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Course, CourseModule, Enrollment, Notification, SpeakingPractice


# --- Users ---


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, *, email: str, password: str, full_name: str, role: str = "employee") -> User:
    user = User(email=email, password=password, full_name=full_name, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return list(result.scalars().all())


# --- Courses ---


async def get_courses(db: AsyncSession) -> List[dict]:
    result = await db.execute(select(Course))
    courses = list(result.scalars().all())
    out = []
    for c in courses:
        creator = await get_user(db, c.created_by) if c.created_by else None
        out.append({"course": c, "creator": creator})
    return out


async def get_course(db: AsyncSession, course_id: int) -> dict | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        return None
    modules = await get_course_modules(db, course.id)
    creator = await get_user(db, course.created_by) if course.created_by else None
    return {"course": course, "modules": modules, "creator": creator}


async def create_course(db: AsyncSession, *, title: str, description: str, status: str = "draft",
                        created_by: int | None = None, objectives: list[str] | None = None,
                        audience: str | None = None, depth: str | None = None) -> Course:
    course = Course(title=title, description=description, status=status,
                    created_by=created_by, objectives=objectives, audience=audience, depth=depth)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


# --- Modules ---


async def get_course_modules(db: AsyncSession, course_id: int) -> List[CourseModule]:
    result = await db.execute(select(CourseModule).where(CourseModule.course_id == course_id))
    return list(result.scalars().all())


async def create_course_module(db: AsyncSession, *, course_id: int, title: str, content: str,
                               sort_order: int = 0, quiz: str | None = None) -> CourseModule:
    module = CourseModule(course_id=course_id, title=title, content=content, sort_order=sort_order, quiz=quiz)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


# --- Enrollments ---


async def get_enrollments(db: AsyncSession, user_id: int | None = None) -> List[dict]:
    stmt = select(Enrollment)
    if user_id is not None:
        stmt = stmt.where(Enrollment.user_id == user_id)
    result = await db.execute(stmt)
    enrollments = list(result.scalars().all())
    out = []
    for e in enrollments:
        course_data = await get_course(db, e.course_id) if e.course_id else None
        user = await get_user(db, e.user_id) if e.user_id else None
        out.append({"enrollment": e, "course": course_data, "user": user})
    return out


async def get_enrollment(db: AsyncSession, enrollment_id: int) -> dict | None:
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        return None
    course_data = await get_course(db, enrollment.course_id) if enrollment.course_id else None
    user = await get_user(db, enrollment.user_id) if enrollment.user_id else None
    return {"enrollment": enrollment, "course": course_data, "user": user}


async def create_enrollment(db: AsyncSession, *, user_id: int, course_id: int,
                            status: str = "assigned", progress_pct: int = 0) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id, status=status,
                            progress_pct=progress_pct, started_at=datetime.utcnow())
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def update_enrollment_progress(db: AsyncSession, enrollment_id: int,
                                     progress_pct: int, status: str | None = None) -> Enrollment | None:
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        return None

    enrollment.progress_pct = progress_pct
    if status:
        enrollment.status = status
    if progress_pct == 100:
        enrollment.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(enrollment)
    return enrollment


# --- Notifications ---


async def get_notifications(db: AsyncSession, user_id: int) -> List[Notification]:
    result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    return list(result.scalars().all())


async def create_notification(db: AsyncSession, *, user_id: int, title: str,
                              message: str, is_read: bool = False) -> Notification:
    notification = Notification(user_id=user_id, title=title, message=message, is_read=is_read)
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_notification_read(db: AsyncSession, notification_id: int) -> Notification | None:
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if notification is None:
        return None
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


# --- Speaking Practice ---


async def get_speaking_practices(db: AsyncSession, user_id: int) -> List[SpeakingPractice]:
    result = await db.execute(
        select(SpeakingPractice)
        .where(SpeakingPractice.user_id == user_id)
        .order_by(desc(SpeakingPractice.created_at))
    )
    return list(result.scalars().all())


async def create_speaking_practice(db: AsyncSession, *, user_id: int, prompt: str,
                                   transcript: str | None = None, audio_url: str | None = None,
                                   pronunciation_score: float | None = None,
                                   fluency_score: float | None = None,
                                   feedback: str | None = None,
                                   corrections: str | None = None) -> SpeakingPractice:
    practice = SpeakingPractice(
        user_id=user_id, prompt=prompt, transcript=transcript, audio_url=audio_url,
        pronunciation_score=pronunciation_score, fluency_score=fluency_score,
        feedback=feedback, corrections=corrections,
    )
    db.add(practice)
    await db.commit()
    await db.refresh(practice)
    return practice
