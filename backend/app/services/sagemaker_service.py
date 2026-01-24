"""
AutoCloud Architect - SageMaker Service

Handles communication with Amazon SageMaker for infrastructure recommendations.
"""
import boto3
import json
import logging
from typing import Optional

from app.config import get_settings
from app.schemas.requirements import RequirementsInput, AppType, PerformancePriority, BudgetTier
from app.schemas.deployment import (
    RecommendationOutput,
    ComputeRecommendation,
    StorageRecommendation,
    DatabaseRecommendation,
    NetworkingRecommendation
)
from app.core.exceptions import SageMakerException

logger = logging.getLogger(__name__)
settings = get_settings()


class SageMakerService:
    """
    Service for interacting with Amazon SageMaker.
    
    In production, this calls a real SageMaker endpoint.
    For development, it uses a rule-based recommendation engine.
    """
    
    def __init__(self):
        """Initialize SageMaker client."""
        self.use_mock = not settings.aws_access_key_id
        
        if not self.use_mock:
            self.client = boto3.client(
                'sagemaker-runtime',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        
        logger.info(f"SageMaker service initialized (mock={self.use_mock})")
    
    async def get_recommendations(
        self, 
        requirements: RequirementsInput
    ) -> RecommendationOutput:
        """
        Get infrastructure recommendations based on requirements.
        
        Args:
            requirements: User's application requirements
            
        Returns:
            RecommendationOutput with suggested AWS architecture
        """
        if self.use_mock:
            return self._get_mock_recommendations(requirements)
        
        return await self._invoke_endpoint(requirements)
    
    async def _invoke_endpoint(
        self, 
        requirements: RequirementsInput
    ) -> RecommendationOutput:
        """
        Invoke the real SageMaker endpoint.
        
        Args:
            requirements: User's application requirements
            
        Returns:
            RecommendationOutput from the ML model
        """
        try:
            # Prepare input for the model
            input_data = self._prepare_input(requirements)
            
            # Invoke SageMaker endpoint
            response = self.client.invoke_endpoint(
                EndpointName=settings.sagemaker_endpoint_name,
                ContentType='application/json',
                Body=json.dumps(input_data)
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            
            return self._parse_response(result, requirements)
            
        except Exception as e:
            logger.error(f"SageMaker invocation failed: {str(e)}")
            raise SageMakerException(f"Failed to get recommendations: {str(e)}")
    
    def _prepare_input(self, requirements: RequirementsInput) -> dict:
        """Prepare input data for the ML model."""
        return {
            "app_type": requirements.app_type.value,
            "expected_users": requirements.expected_users,
            "data_size_gb": requirements.data_size_gb,
            "performance_priority": requirements.performance_priority.value,
            "budget_tier": requirements.budget_tier.value,
            "requires_database": int(requirements.requires_database),
            "requires_load_balancer": int(requirements.requires_load_balancer),
            "requires_auto_scaling": int(requirements.requires_auto_scaling)
        }
    
    def _parse_response(
        self, 
        response: dict, 
        requirements: RequirementsInput
    ) -> RecommendationOutput:
        """Parse SageMaker response into RecommendationOutput."""
        return RecommendationOutput(
            compute=ComputeRecommendation(
                instance_type=response.get("instance_type", "t3.micro"),
                instance_count=response.get("instance_count", 1),
                use_spot=response.get("use_spot", False)
            ),
            storage=StorageRecommendation(
                s3_bucket=True,
                storage_class=response.get("storage_class", "STANDARD")
            ),
            database=DatabaseRecommendation(
                db_type=response.get("db_type", "dynamodb"),
                instance_class=response.get("db_instance_class"),
                multi_az=response.get("multi_az", False)
            ) if requirements.requires_database else None,
            networking=NetworkingRecommendation(
                use_alb=response.get("use_alb", False),
                use_nat=True,
                public_subnets=2,
                private_subnets=2
            ),
            use_auto_scaling=response.get("use_auto_scaling", False),
            min_instances=response.get("min_instances", 1),
            max_instances=response.get("max_instances", 4),
            estimated_monthly_cost_usd=response.get("estimated_cost", 50.0),
            confidence_score=response.get("confidence", 0.85)
        )
    
    def _get_mock_recommendations(
        self, 
        requirements: RequirementsInput
    ) -> RecommendationOutput:
        """
        Generate recommendations using rule-based logic.
        
        This is used for development when SageMaker is not available.
        """
        logger.info("Using mock recommendations (SageMaker not configured)")
        
        # Determine instance type based on users and performance
        instance_type = self._select_instance_type(
            requirements.expected_users,
            requirements.performance_priority,
            requirements.budget_tier
        )
        
        # Determine instance count
        instance_count = self._calculate_instance_count(
            requirements.expected_users,
            requirements.requires_auto_scaling
        )
        
        # Determine database type
        db_type, db_instance_class = self._select_database(
            requirements.app_type,
            requirements.data_size_gb,
            requirements.budget_tier
        )
        
        # Determine if ALB is needed
        use_alb = (
            requirements.requires_load_balancer or 
            requirements.expected_users > 500 or
            instance_count > 1
        )
        
        # Calculate cost estimate
        cost = self._estimate_cost(
            instance_type,
            instance_count,
            db_type,
            db_instance_class,
            use_alb,
            requirements.data_size_gb
        )
        
        return RecommendationOutput(
            compute=ComputeRecommendation(
                instance_type=instance_type,
                instance_count=instance_count,
                use_spot=requirements.budget_tier == BudgetTier.LOW
            ),
            storage=StorageRecommendation(
                s3_bucket=True,
                storage_class="STANDARD" if requirements.budget_tier != BudgetTier.LOW else "STANDARD_IA"
            ),
            database=DatabaseRecommendation(
                db_type=db_type,
                instance_class=db_instance_class,
                multi_az=requirements.budget_tier == BudgetTier.HIGH
            ) if requirements.requires_database else None,
            networking=NetworkingRecommendation(
                use_alb=use_alb,
                use_nat=True,
                public_subnets=2,
                private_subnets=2
            ),
            use_auto_scaling=requirements.requires_auto_scaling or requirements.expected_users > 1000,
            min_instances=1,
            max_instances=max(4, instance_count * 2),
            estimated_monthly_cost_usd=cost,
            confidence_score=0.88
        )
    
    def _select_instance_type(
        self, 
        users: int, 
        performance: PerformancePriority,
        budget: BudgetTier
    ) -> str:
        """Select appropriate EC2 instance type."""
        if budget == BudgetTier.LOW:
            if users < 100:
                return "t3.micro"
            elif users < 1000:
                return "t3.small"
            else:
                return "t3.medium"
        elif budget == BudgetTier.MEDIUM:
            if users < 100:
                return "t3.small"
            elif users < 1000:
                return "t3.medium"
            elif users < 10000:
                return "t3.large"
            else:
                return "m5.large"
        else:  # HIGH
            if performance == PerformancePriority.HIGH:
                if users < 1000:
                    return "m5.large"
                elif users < 10000:
                    return "m5.xlarge"
                else:
                    return "m5.2xlarge"
            else:
                if users < 1000:
                    return "t3.large"
                else:
                    return "m5.large"
    
    def _calculate_instance_count(self, users: int, auto_scaling: bool) -> int:
        """Calculate recommended instance count."""
        if users < 100:
            return 1
        elif users < 1000:
            return 2 if auto_scaling else 1
        elif users < 10000:
            return 2
        else:
            return 3
    
    def _select_database(
        self, 
        app_type: AppType, 
        data_size: int,
        budget: BudgetTier
    ) -> tuple[str, Optional[str]]:
        """Select database type and instance class."""
        # DynamoDB for simple apps or low budget
        if budget == BudgetTier.LOW or app_type == AppType.API:
            return "dynamodb", None
        
        # RDS for web/ML apps with moderate+ data
        if data_size > 20 or budget == BudgetTier.HIGH:
            if budget == BudgetTier.HIGH:
                return "rds-mysql", "db.t3.medium"
            else:
                return "rds-mysql", "db.t3.micro"
        
        return "dynamodb", None
    
    def _estimate_cost(
        self,
        instance_type: str,
        instance_count: int,
        db_type: str,
        db_instance_class: Optional[str],
        use_alb: bool,
        data_size_gb: int
    ) -> float:
        """Estimate monthly cost in USD."""
        # Simplified cost estimation
        instance_costs = {
            "t3.micro": 8.50,
            "t3.small": 17.00,
            "t3.medium": 34.00,
            "t3.large": 68.00,
            "m5.large": 77.00,
            "m5.xlarge": 154.00,
            "m5.2xlarge": 307.00
        }
        
        db_costs = {
            "dynamodb": 25.00,  # Base cost
            "db.t3.micro": 15.00,
            "db.t3.medium": 50.00
        }
        
        cost = instance_costs.get(instance_type, 50.0) * instance_count
        
        if db_type == "dynamodb":
            cost += db_costs["dynamodb"]
        elif db_instance_class:
            cost += db_costs.get(db_instance_class, 30.0)
        
        if use_alb:
            cost += 25.00  # ALB base cost
        
        cost += data_size_gb * 0.023  # S3 storage
        cost += 10.0  # NAT Gateway base
        
        return round(cost, 2)
