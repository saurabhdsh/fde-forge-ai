"""Communication interview repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication_interview import CommunicationInterview


class CommunicationInterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, interview: CommunicationInterview) -> CommunicationInterview:
        self.session.add(interview)
        await self.session.flush()
        return interview

    async def get_by_id(
        self, interview_id: UUID, organization_id: UUID
    ) -> CommunicationInterview | None:
        result = await self.session.execute(
            select(CommunicationInterview).where(
                CommunicationInterview.id == interview_id,
                CommunicationInterview.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(
        self, conversation_id: str
    ) -> CommunicationInterview | None:
        result = await self.session.execute(
            select(CommunicationInterview).where(
                CommunicationInterview.tavus_conversation_id == conversation_id
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_user(
        self, user_id: UUID, organization_id: UUID
    ) -> CommunicationInterview | None:
        result = await self.session.execute(
            select(CommunicationInterview)
            .where(
                CommunicationInterview.user_id == user_id,
                CommunicationInterview.organization_id == organization_id,
            )
            .order_by(CommunicationInterview.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
