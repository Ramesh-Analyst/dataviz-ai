import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DATABASE_URL: str = Field(default="sqlite:///./dataviz.db")
    SECRET_KEY: str = Field(default="949f57d605175cf14e7a83d7350c37cf3a9f7e8b91c89f53e6b772bd2304910e")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    CORS_ORIGINS: str = Field(default="")

    @property
    def cors_origins_list(self) -> list[str]:
        default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        if not self.CORS_ORIGINS:
            return default_origins
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return origins if origins else default_origins

    model_config = SettingsConfigDict(
        # Load env file from backend root (3 levels up from core/config.py)
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL or self.DATABASE_URL == "sqlite:///./dataviz.db":
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(backend_dir, "dataviz.db").replace("\\", "/")
            self.DATABASE_URL = f"sqlite:///{db_path}"

settings = Settings()

# Ensure the upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
