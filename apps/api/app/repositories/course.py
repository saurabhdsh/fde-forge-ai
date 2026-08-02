"""Course repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseModule, CourseProgress, CourseSlide


class CourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID, organization_id: UUID) -> list[Course]:
        result = await self.session.execute(
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(CourseModule.slides),
                selectinload(Course.progress),
            )
            .where(
                Course.user_id == user_id,
                Course.organization_id == organization_id,
            )
            .order_by(Course.domain)
        )
        return list(result.scalars().all())

    async def get_by_id(self, course_id: UUID, organization_id: UUID) -> Course | None:
        result = await self.session.execute(
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(CourseModule.slides),
                selectinload(Course.progress),
            )
            .where(Course.id == course_id, Course.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def get_by_domain(
        self, user_id: UUID, organization_id: UUID, domain: str
    ) -> Course | None:
        result = await self.session.execute(
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(CourseModule.slides),
                selectinload(Course.progress),
            )
            .where(
                Course.user_id == user_id,
                Course.organization_id == organization_id,
                Course.domain == domain,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, course: Course) -> Course:
        self.session.add(course)
        await self.session.flush()
        return course

    async def get_slide(self, slide_id: UUID) -> CourseSlide | None:
        result = await self.session.execute(
            select(CourseSlide)
            .options(selectinload(CourseSlide.module).selectinload(CourseModule.course))
            .where(CourseSlide.id == slide_id)
        )
        return result.scalar_one_or_none()
