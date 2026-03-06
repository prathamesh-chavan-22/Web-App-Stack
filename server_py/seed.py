from sqlalchemy.ext.asyncio import AsyncSession

import storage


async def seed_database(db: AsyncSession):
    """Seed the database with initial data if empty."""
    users = await storage.get_users(db)
    if len(users) > 0:
        return

    print("Seeding database...")

    l_and_d = await storage.create_user(
        db, email="admin@lms.local", password="password",
        full_name="Admin User", role="l_and_d",
    )
    manager = await storage.create_user(
        db, email="manager@lms.local", password="password",
        full_name="Manager User", role="manager",
    )
    employee = await storage.create_user(
        db, email="employee@lms.local", password="password",
        full_name="John Employee", role="employee",
    )

    course1 = await storage.create_course(
        db, title="Onboarding 101", description="Welcome to the company!",
        status="published", created_by=l_and_d.id,
    )
    await storage.create_course_module(
        db, course_id=course1.id, title="Company History",
        content="We started in 2024...", sort_order=1,
    )
    await storage.create_course_module(
        db, course_id=course1.id, title="Code of Conduct",
        content="Be nice.", sort_order=2,
    )

    course2 = await storage.create_course(
        db, title="Advanced Security", description="How to keep things secure.",
        status="published", created_by=l_and_d.id,
    )
    await storage.create_course_module(
        db, course_id=course2.id, title="Phishing",
        content="Don't click weird links.", sort_order=1,
    )

    await storage.create_enrollment(
        db, user_id=employee.id, course_id=course1.id,
        status="in_progress", progress_pct=50,
    )

    await storage.create_notification(
        db, user_id=employee.id, title="Welcome",
        message="Welcome to the LMS!", is_read=False,
    )

    print("Database seeded successfully.")
