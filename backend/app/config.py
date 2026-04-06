"""
AutoCloud Architect - Backend Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from typing import Optional
import os


# Find .env file — check current dir, then parent dir (project root)
def _find_env_file() -> str:
    """Locate the .env file in the project."""
    # Check if .env is in current working directory
    if Path(".env").exists():
        return ".env"
    
    # Check parent directory (project root when running from backend/)
    parent_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if parent_env.exists():
        return str(parent_env)
    
    # Check two levels up from CWD
    cwd_parent = Path.cwd().parent / ".env"
    if cwd_parent.exists():
        return str(cwd_parent)
    
    return ".env"  # Default fallback


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Settings
    app_name: str = "AutoCloud Architect"
    debug: bool = True
    api_version: str = "v1"
    
    # AWS Settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    
    # SageMaker Configuration
    sagemaker_endpoint_name: str = "autocloud-recommender"
    sagemaker_role_arn: str = ""
    
    # S3 Configuration
    s3_deployment_bucket: str = "autocloud-deployments"
    
    # EC2 SSH Settings
    ec2_key_pair_name: str = ""
    ec2_ssh_public_key: str = ""
    
    # Backend Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    
    # CORS Origins
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = _find_env_file()
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    
    # Log which mode we're in
    if settings.aws_access_key_id:
        print(f"[Config] AWS credentials loaded (region={settings.aws_default_region}) — REAL MODE")
    else:
        print(f"[Config] No AWS credentials found — MOCK MODE")
        print(f"[Config] Searched for .env at: {Settings.Config.env_file}")
    
    return settings
