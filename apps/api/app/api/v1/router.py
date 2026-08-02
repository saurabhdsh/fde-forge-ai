"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    analytics,
    assessments,
    audit,
    auth,
    coding_assessments,
    courses,
    curriculum,
    health,
    learners,
    learning_plans,
    organizations,
    skills,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(learners.router, prefix="/learners", tags=["learners"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
api_router.include_router(
    coding_assessments.router, prefix="/coding-assessments", tags=["coding-assessments"]
)
api_router.include_router(
    learning_plans.router, prefix="/learning-plans", tags=["learning-plans"]
)
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
