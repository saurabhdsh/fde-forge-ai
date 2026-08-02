"""Application configuration with fail-fast validation."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "FDE Forge AI"
    app_tagline: str = "Transform AI Engineers into Customer-Ready Forward Deployed Engineers."
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    secret_key: str = Field(..., min_length=32)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    csrf_secret: str = Field(..., min_length=32)
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    database_url: str = Field(...)
    database_url_sync: str = Field(...)

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "fde-forge"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    ai_default_provider: str = Field(
        default="openai",
        validation_alias=AliasChoices("AI_DEFAULT_PROVIDER", "DEFAULT_LLM_PROVIDER"),
    )
    ai_default_model: str = "gpt-4o-mini"
    ai_max_retries: int = 3
    ai_request_timeout_seconds: int = 180
    ai_daily_org_budget: float = 50.0
    ai_fallback_model: str = ""
    enabled_llm_providers: str = Field(
        default="openai,bedrock",
        validation_alias=AliasChoices("ENABLED_LLM_PROVIDERS", "enabled_llm_providers"),
    )

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = ""
    anthropic_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("BEDROCK_ENABLED", "bedrock_enabled"),
    )
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        validation_alias=AliasChoices("BEDROCK_MODEL_ID", "bedrock_model_id"),
    )
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    google_api_key: str = ""
    gemini_model: str = ""

    tavus_api_key: str = ""
    tavus_pal_id: str = "pcb7a34da5fe"
    tavus_face_id: str = "r90bbd427f71"
    tavus_callback_base_url: str = ""
    tavus_webhook_secret: str = ""
    tavus_max_call_duration_seconds: int = 900
    tavus_test_mode: bool = False

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@fdeforge.example.com"
    smtp_use_tls: bool = False

    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "fde-forge-api"
    sentry_dsn: str = ""
    log_level: str = "INFO"

    max_upload_size_mb: int = 10
    allowed_file_types: str = "pdf,docx,txt,md"
    code_execution_timeout_seconds: int = 30
    code_execution_memory_limit_mb: int = 512
    code_execution_enabled: bool = False

    rate_limit_per_minute: int = 120
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    seed_admin_email: str = "saurabh@fdeforge.example.com"
    seed_admin_password: str = "admin123"
    seed_learner_password: str = "ChangeMeLearner123!"

    @field_validator("secret_key", "csrf_secret")
    @classmethod
    def validate_secrets(cls, value: str) -> str:
        if value.startswith("change-me") and len(value) < 40:
            pass
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if self.secret_key.startswith("change-me"):
                raise ValueError("SECRET_KEY must be set for production")
            if self.csrf_secret.startswith("change-me"):
                raise ValueError("CSRF_SECRET must be set for production")
            if self.cookie_secure is False:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_file_type_list(self) -> list[str]:
        return [t.strip().lower() for t in self.allowed_file_types.split(",") if t.strip()]

    @property
    def enabled_llm_provider_list(self) -> list[str]:
        return [
            p.strip().lower()
            for p in (self.enabled_llm_providers or "").split(",")
            if p.strip()
        ]

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())

    @property
    def bedrock_configured(self) -> bool:
        if not self.bedrock_enabled:
            return False
        if not (self.bedrock_model_id or "").strip():
            return False
        if self.aws_access_key_id and self.aws_secret_access_key:
            return True
        try:
            from app.ai.providers.bedrock_provider import has_aws_credentials

            return has_aws_credentials()
        except Exception:  # noqa: BLE001
            return False

    @property
    def ai_configured(self) -> bool:
        default = (self.ai_default_provider or "openai").lower()
        if default == "bedrock" and self.bedrock_configured:
            return True
        if default == "openai" and self.openai_configured:
            return True
        if "bedrock" in self.enabled_llm_provider_list and self.bedrock_configured:
            return True
        if "openai" in self.enabled_llm_provider_list and self.openai_configured:
            return True
        return False

    @property
    def tavus_configured(self) -> bool:
        return bool(self.tavus_api_key and self.tavus_api_key.strip())

    @property
    def is_development(self) -> bool:
        return self.app_env in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
