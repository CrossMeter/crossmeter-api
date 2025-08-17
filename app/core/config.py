import os

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # API Configuration
    api_v1_prefix: str = "/v1"
    project_name: str = "PIaaS - Payment Infrastructure as a Service"
    version: str = "1.0.0"
    description: str = "Crypto payment infrastructure with multi-chain bridging abstraction"
    
    # Supabase Configuration
    supabase_url: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "https://your-project.supabase.co"),
        description="Supabase project URL"
    )
    supabase_key: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_KEY", "your-supabase-anon-key"),
        description="Supabase anonymous key"
    )
    supabase_service_key: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", "your-supabase-service-key"),
        description="Supabase service role key (for admin operations)"
    )
    
    # Redis Cloud Configuration (for webhook queue)
    redis_url: str = Field(
        # Use the environment variable for Redis Cloud URL as default (see environment.template)
        default_factory=lambda: os.getenv("REDIS_URL", "redis://default:your-password@your-endpoint.c1.cloud.redislabs.com:12345/0"),
        description="Redis URL for task queue (use rediss:// for SSL)"
    )
    redis_host: Optional[str] = Field(
        default=None,
        description="Redis host (alternative to URL)"
    )
    redis_port: Optional[int] = Field(
        default=None,
        description="Redis port"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password"
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number"
    )
    redis_ssl: bool = Field(
        default=False,
        description="Use SSL for Redis connection"
    )
    
    # Celery Configuration
    celery_broker_url: Optional[str] = Field(
        default=None,
        description="Celery broker URL (defaults to redis_url if not set)"
    )
    celery_result_backend: Optional[str] = Field(
        default=None,
        description="Celery result backend URL (defaults to redis_url if not set)"
    )
    
    # Webhook Configuration
    webhook_retry_attempts: int = Field(default=3, description="Number of webhook retry attempts")
    webhook_retry_delay_seconds: int = Field(default=2, description="Initial webhook retry delay")
    webhook_timeout_seconds: int = Field(default=30, description="Webhook request timeout")
    
    # Router Contract Configuration
    default_router_address: str = Field(
        default="0x1234567890123456789012345678901234567890",
        description="Default router contract address"
    )
    default_router_function: str = Field(
        default="createPayment",
        description="Default router function name"
    )
    
    # Security
    secret_key: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production"),
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Environment
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Database Pool Settings (for future use)
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # Dynamic.xyz Configuration
    dynamic_environment_id: Optional[str] = Field(
        default=None,
        description="Dynamic.xyz environment ID"
    )
    dynamic_api_base_url: Optional[str] = Field(
        default="https://app.dynamic.xyz",
        description="Dynamic.xyz API base URL"
    )
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def get_redis_url(self) -> str:
        """Get the Redis URL for connections."""
        return self.redis_url
    
    @property
    def get_celery_broker_url(self) -> str:
        """Get the Celery broker URL."""
        return self.celery_broker_url or self.redis_url
    
    @property
    def get_celery_result_backend(self) -> str:
        """Get the Celery result backend URL."""
        return self.celery_result_backend or self.redis_url


# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings."""
    return settings
