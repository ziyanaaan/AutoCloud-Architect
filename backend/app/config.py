"""
AutoCloud Architect - Backend Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Settings
    app_name: str = "AutoCloud Architect"
    debug: bool = True
    api_version: str = "v1"
    
    # AWS Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    
    # SageMaker Configuration
    sagemaker_endpoint_name: str = "autocloud-recommender"
    sagemaker_role_arn: str = ""
    
    # S3 Configuration
    s3_deployment_bucket: str = "autocloud-deployments"
    
    # Backend Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    
    # CORS Origins
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
