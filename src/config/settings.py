"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class OllamaSettings(BaseSettings):
    host: str = "http://localhost:11434"
    keep_alive: str = "5m"
    reasoning_model: str = "qwen3:14b"
    vision_model: str = "qwen2.5vl:7b"
    scope_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"

    model_config = {"env_prefix": "OLLAMA_"}


class QdrantSettings(BaseSettings):
    url: str = "http://localhost:6333"
    collection: str = "construction_knowledge"

    model_config = {"env_prefix": "QDRANT_"}


class PostgresSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    db: str = "ai_worker"
    user: str = "ai_worker"
    password: str = "changeme"

    model_config = {"env_prefix": "POSTGRES_"}

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": "REDIS_"}


class MinioSettings(BaseSettings):
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "ai-worker"

    model_config = {"env_prefix": "MINIO_"}


class JobTreadSettings(BaseSettings):
    api_key: str = ""
    api_url: str = "https://api.jobtread.com/graphql"

    model_config = {"env_prefix": "JOBTREAD_"}


class MorawareSettings(BaseSettings):
    api_key: str = ""
    api_url: str = ""

    model_config = {"env_prefix": "MORAWARE_"}


class QuickBooksSettings(BaseSettings):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8080/callback"
    environment: str = "sandbox"

    model_config = {"env_prefix": "QB_"}


class Settings(BaseSettings):
    """Root application settings aggregating all sub-configs."""

    anthropic_api_key: str = ""
    log_level: str = "INFO"
    environment: str = "development"
    default_region: str = "bend_or"
    labor_premium_factor: float = 1.10

    ollama: OllamaSettings = OllamaSettings()
    qdrant: QdrantSettings = QdrantSettings()
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    minio: MinioSettings = MinioSettings()
    jobtread: JobTreadSettings = JobTreadSettings()
    moraware: MorawareSettings = MorawareSettings()
    quickbooks: QuickBooksSettings = QuickBooksSettings()

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}
