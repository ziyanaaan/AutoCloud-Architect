"""
AutoCloud Architect - Deployment Schemas
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class DeploymentState(str, Enum):
    """Deployment job state enumeration."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class ComputeRecommendation(BaseModel):
    """Recommended compute configuration."""
    instance_type: str = Field(..., description="EC2 instance type")
    instance_count: int = Field(default=1, description="Number of instances")
    use_spot: bool = Field(default=False, description="Use spot instances")


class StorageRecommendation(BaseModel):
    """Recommended storage configuration."""
    s3_bucket: bool = Field(default=True, description="Create S3 bucket")
    storage_class: str = Field(default="STANDARD", description="S3 storage class")


class DatabaseRecommendation(BaseModel):
    """Recommended database configuration."""
    db_type: str = Field(..., description="Database type (rds-mysql, rds-postgres, dynamodb)")
    instance_class: Optional[str] = Field(None, description="RDS instance class")
    multi_az: bool = Field(default=False, description="Multi-AZ deployment")


class NetworkingRecommendation(BaseModel):
    """Recommended networking configuration."""
    use_alb: bool = Field(default=False, description="Use Application Load Balancer")
    use_nat: bool = Field(default=True, description="Use NAT Gateway")
    public_subnets: int = Field(default=2, description="Number of public subnets")
    private_subnets: int = Field(default=2, description="Number of private subnets")


class RecommendationOutput(BaseModel):
    """
    SageMaker recommendation output schema.
    
    Contains the complete infrastructure recommendation
    based on user requirements analysis.
    """
    
    # Recommendations
    compute: ComputeRecommendation
    storage: StorageRecommendation
    database: Optional[DatabaseRecommendation] = None
    networking: NetworkingRecommendation
    
    # Additional recommendations
    use_auto_scaling: bool = Field(default=False)
    min_instances: int = Field(default=1)
    max_instances: int = Field(default=4)
    
    # Cost estimate
    estimated_monthly_cost_usd: float = Field(..., description="Estimated monthly cost in USD")
    
    # Confidence
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Model confidence score"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "compute": {
                    "instance_type": "t3.medium",
                    "instance_count": 2,
                    "use_spot": False
                },
                "storage": {
                    "s3_bucket": True,
                    "storage_class": "STANDARD"
                },
                "database": {
                    "db_type": "rds-mysql",
                    "instance_class": "db.t3.micro",
                    "multi_az": False
                },
                "networking": {
                    "use_alb": True,
                    "use_nat": True,
                    "public_subnets": 2,
                    "private_subnets": 2
                },
                "use_auto_scaling": True,
                "min_instances": 1,
                "max_instances": 4,
                "estimated_monthly_cost_usd": 150.00,
                "confidence_score": 0.92
            }
        }


class DeploymentRequest(BaseModel):
    """Request to start a deployment."""
    job_id: str = Field(..., description="Unique deployment job ID")
    requirements: dict = Field(..., description="Original requirements")
    recommendations: RecommendationOutput = Field(..., description="Approved recommendations")
    code_url: Optional[str] = Field(None, description="URL or path to application code (S3 URL or repo URL)")
    repo_url: Optional[str] = Field(None, description="GitHub/GitLab repository URL")


class AWSResource(BaseModel):
    """Provisioned AWS resource details."""
    resource_type: str = Field(..., description="AWS resource type")
    resource_id: str = Field(..., description="AWS resource ID")
    resource_arn: Optional[str] = Field(None, description="AWS resource ARN")
    status: str = Field(..., description="Resource status")
    details: dict = Field(default_factory=dict, description="Additional details")


class DeploymentStatus(BaseModel):
    """Current deployment status."""
    state: DeploymentState
    progress_percent: int = Field(ge=0, le=100)
    current_step: str
    message: str
    resources: List[AWSResource] = Field(default_factory=list)
    error: Optional[str] = None


class DeploymentJob(BaseModel):
    """Complete deployment job information."""
    job_id: str
    app_name: str
    status: DeploymentStatus
    recommendations: RecommendationOutput
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    endpoint_url: Optional[str] = None
    cloudwatch_dashboard_url: Optional[str] = None
    stack_id: Optional[str] = None
