from typing import Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # Core Settings
    PROJECT_NAME: str = "Operational Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    SECRET_KEY: str
    OPENAI_API_KEY: str | None = None

    # GitHub OAuth Settings
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/github/callback"
    WEBHOOK_BASE_URL: str | None = None

    # Slacl OAuth Settings
    SLACK_CLIENT_ID: str | None = None
    SLACK_CLIENT_SECRET: str | None = None
    SLACK_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/slack/callback"

    # Google/Gmail OAuth Settings
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/gmail/callback"

    # Jira OAuth 2.0 (3LO) Settings
    JIRA_CLIENT_ID: str | None = None
    JIRA_CLIENT_SECRET: str | None = None
    JIRA_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/jira/callback"


    # Token Lifespans
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "securepassword"
    POSTGRES_DB: str = "oip_db"

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "oip_mongo"
    MONGODB_TEST_DB: str = "oip_mongo_test"

    # RabbitMQ Message Queue Settings
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_MAX_RETRIES: int = 5
    QUEUE_INITIAL_BACKOFF_MS: int = 2000
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0


    @computed_field
    @property
    def sync_database_url(self) -> str:
        """Constructs a synchronous database URL for Alembic migrations."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """Constructs an asynchronous database URL for FastAPI async sessions."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
