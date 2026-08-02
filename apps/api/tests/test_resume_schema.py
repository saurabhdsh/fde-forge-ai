"""AI schema validation tests."""

import pytest
from pydantic import ValidationError

from app.schemas.learner import ResumeExtractionPayload


def test_resume_extraction_schema_valid() -> None:
    payload = ResumeExtractionPayload.model_validate(
        {
            "summary": "AI engineer",
            "skills": [
                {
                    "name": "Python Programming",
                    "proficiency_level": "proficient",
                    "confidence": 0.9,
                }
            ],
            "technical_experience": [],
            "project_experience": [],
            "domain_experience": ["healthcare"],
            "certifications": [],
            "suggested_target_roles": ["Payer FDE"],
            "suggested_domains": ["healthcare"],
        }
    )
    assert payload.skills[0].name == "Python Programming"


def test_resume_extraction_rejects_bad_confidence() -> None:
    with pytest.raises(ValidationError):
        ResumeExtractionPayload.model_validate(
            {
                "skills": [
                    {
                        "name": "Python",
                        "proficiency_level": "working",
                        "confidence": 2.5,
                    }
                ]
            }
        )
