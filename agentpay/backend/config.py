from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-opus-4-6-v1"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "sqlite:///./agentpay.db"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
