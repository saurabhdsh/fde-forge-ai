"""Bedrock helper unit tests (no live AWS required)."""

from app.ai.providers.bedrock_provider import resolve_bedrock_model_id


def test_resolve_prefixes_anthropic_in_us_region() -> None:
    assert (
        resolve_bedrock_model_id("anthropic.claude-sonnet-4-5-20250929-v1:0", "us-east-1")
        == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )


def test_resolve_keeps_us_prefixed() -> None:
    mid = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    assert resolve_bedrock_model_id(mid, "us-east-1") == mid
