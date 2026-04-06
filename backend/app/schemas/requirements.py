"""
AutoCloud Architect - Requirements Schemas
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class AppType(str, Enum):
    """Application type enumeration."""
    WEB = "web"
    API = "api"
    STATIC = "static"
    ML = "ml"


class PerformancePriority(str, Enum):
    """Performance priority levels."""
    LOW = "low"
    BALANCED = "balanced"
    HIGH = "high"


class BudgetTier(str, Enum):
    """Budget tier levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RequirementsInput(BaseModel):
    """
    User application requirements input schema.
    
    This captures all the information needed to analyze
    and recommend an appropriate AWS architecture.
    """
    
    # Application Details
    app_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Name of the application"
    )
    
    app_type: AppType = Field(
        ..., 
        description="Type of application (web, api, static, ml)"
    )
    
    description: Optional[str] = Field(
        None, 
        max_length=500,
        description="Brief description of the application"
    )
    
    # Capacity Requirements
    expected_users: int = Field(
        ..., 
        ge=1, 
        le=10000000,
        description="Expected number of concurrent users"
    )
    
    data_size_gb: int = Field(
        ..., 
        ge=0, 
        le=10000,
        description="Expected data storage size in GB"
    )
    
    # Priorities
    performance_priority: PerformancePriority = Field(
        default=PerformancePriority.BALANCED,
        description="Performance priority level"
    )
    
    budget_tier: BudgetTier = Field(
        default=BudgetTier.MEDIUM,
        description="Budget tier for AWS resources"
    )
    
    # Optional Features
    requires_database: bool = Field(
        default=True,
        description="Whether the application requires a database"
    )
    
    requires_load_balancer: bool = Field(
        default=False,
        description="Whether to use an Application Load Balancer"
    )
    
    requires_auto_scaling: bool = Field(
        default=False,
        description="Whether to enable Auto Scaling"
    )
    
    requires_cdn: bool = Field(
        default=False,
        description="Whether to use CloudFront CDN"
    )
    
    # Code Source
    repo_url: Optional[str] = Field(
        None,
        description="GitHub/GitLab repository URL for the application code"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "app_name": "my-web-app",
                "app_type": "web",
                "description": "A modern web application",
                "expected_users": 1000,
                "data_size_gb": 50,
                "performance_priority": "balanced",
                "budget_tier": "medium",
                "requires_database": True,
                "requires_load_balancer": True,
                "requires_auto_scaling": False,
                "requires_cdn": False,
                "repo_url": "https://github.com/username/repo"
            }
        }
