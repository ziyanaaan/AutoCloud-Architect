"""
AutoCloud Architect - API Routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from typing import Optional
import uuid
import logging

from app.schemas.requirements import RequirementsInput
from app.schemas.deployment import (
    RecommendationOutput,
    DeploymentRequest,
    DeploymentJob,
    DeploymentStatus,
    DeploymentState
)
from app.services.sagemaker_service import SageMakerService
from app.services.provisioning_service import ProvisioningService
from app.services.deployment_service import DeploymentService
from app.core.exceptions import bad_request_exception, not_found_exception

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job storage (use Redis/DB in production)
deployment_jobs: dict[str, DeploymentJob] = {}

# Service instances
sagemaker_service = SageMakerService()
provisioning_service = ProvisioningService()
deployment_service = DeploymentService()


@router.post("/analyze", response_model=dict)
async def analyze_requirements(requirements: RequirementsInput):
    """
    Analyze application requirements and get infrastructure recommendations.
    
    This endpoint sends requirements to the SageMaker model and returns
    recommended AWS architecture.
    """
    logger.info(f"Analyzing requirements for: {requirements.app_name}")
    
    try:
        # Get recommendations from SageMaker
        recommendations = await sagemaker_service.get_recommendations(requirements)
        
        # Generate a job ID for potential deployment
        job_id = str(uuid.uuid4())
        
        return {
            "job_id": job_id,
            "app_name": requirements.app_name,
            "recommendations": recommendations.model_dump(),
            "message": "Analysis complete. Review recommendations and proceed to deploy."
        }
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/deploy", response_model=DeploymentJob)
async def start_deployment(
    request: DeploymentRequest,
    background_tasks: BackgroundTasks
):
    """
    Start infrastructure provisioning and application deployment.
    
    This initiates the full deployment pipeline:
    1. Create CloudFormation stack
    2. Provision AWS resources
    3. Deploy application
    4. Verify health
    """
    logger.info(f"Starting deployment for job: {request.job_id}")
    
    # Check if job already exists
    if request.job_id in deployment_jobs:
        raise bad_request_exception(f"Deployment job {request.job_id} already exists")
    
    # Create job record
    from datetime import datetime
    job = DeploymentJob(
        job_id=request.job_id,
        app_name=request.requirements.get("app_name", "unknown"),
        status=DeploymentStatus(
            state=DeploymentState.PENDING,
            progress_percent=0,
            current_step="Initializing",
            message="Deployment job created"
        ),
        recommendations=request.recommendations,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    deployment_jobs[request.job_id] = job
    
    # Start deployment in background
    background_tasks.add_task(
        execute_deployment,
        request.job_id,
        request.requirements,
        request.recommendations,
        request.code_url
    )
    
    return job


async def execute_deployment(
    job_id: str,
    requirements: dict,
    recommendations: RecommendationOutput,
    code_url: Optional[str]
):
    """Execute the full deployment pipeline."""
    from datetime import datetime
    
    job = deployment_jobs.get(job_id)
    if not job:
        return
    
    try:
        # Step 1: Analyzing
        job.status.state = DeploymentState.ANALYZING
        job.status.progress_percent = 10
        job.status.current_step = "Validating configuration"
        job.status.message = "Validating infrastructure configuration..."
        job.updated_at = datetime.utcnow()
        
        # Step 2: Provisioning
        job.status.state = DeploymentState.PROVISIONING
        job.status.progress_percent = 30
        job.status.current_step = "Creating CloudFormation stack"
        job.status.message = "Provisioning AWS resources..."
        job.updated_at = datetime.utcnow()
        
        # Create infrastructure
        stack_result = await provisioning_service.provision_infrastructure(
            app_name=requirements.get("app_name", "autocloud-app"),
            recommendations=recommendations
        )
        
        job.stack_id = stack_result.get("stack_id")
        job.status.resources = stack_result.get("resources", [])
        job.status.progress_percent = 60
        
        # Step 3: Deploying
        job.status.state = DeploymentState.DEPLOYING
        job.status.current_step = "Deploying application"
        job.status.message = "Installing and configuring application..."
        job.updated_at = datetime.utcnow()
        
        # Deploy application
        deployment_result = await deployment_service.deploy_application(
            job_id=job_id,
            code_url=code_url,
            resources=stack_result.get("resources", [])
        )
        
        job.status.progress_percent = 85
        
        # Step 4: Verifying
        job.status.state = DeploymentState.VERIFYING
        job.status.current_step = "Running health checks"
        job.status.message = "Verifying deployment health..."
        job.updated_at = datetime.utcnow()
        
        # Health check
        health_result = await deployment_service.verify_health(
            endpoint=deployment_result.get("endpoint")
        )
        
        # Step 5: Complete
        job.status.state = DeploymentState.COMPLETED
        job.status.progress_percent = 100
        job.status.current_step = "Deployment complete"
        job.status.message = "Application deployed successfully!"
        job.endpoint_url = deployment_result.get("endpoint")
        job.cloudwatch_dashboard_url = deployment_result.get("dashboard_url")
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        logger.info(f"Deployment {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Deployment {job_id} failed: {str(e)}")
        job.status.state = DeploymentState.FAILED
        job.status.error = str(e)
        job.status.message = f"Deployment failed: {str(e)}"
        job.updated_at = datetime.utcnow()


@router.get("/deploy/{job_id}", response_model=DeploymentJob)
async def get_deployment_status(job_id: str):
    """Get the current status of a deployment job."""
    job = deployment_jobs.get(job_id)
    if not job:
        raise not_found_exception("Deployment job", job_id)
    return job


@router.get("/deploy/{job_id}/logs")
async def get_deployment_logs(job_id: str, limit: int = 100):
    """Get deployment logs for a job."""
    job = deployment_jobs.get(job_id)
    if not job:
        raise not_found_exception("Deployment job", job_id)
    
    # In production, fetch from CloudWatch Logs
    return {
        "job_id": job_id,
        "logs": [
            {"timestamp": str(job.created_at), "message": "Deployment job created"},
            {"timestamp": str(job.updated_at), "message": job.status.message}
        ]
    }


@router.get("/deployments")
async def list_deployments():
    """List all deployment jobs."""
    return {
        "count": len(deployment_jobs),
        "deployments": [job.model_dump() for job in deployment_jobs.values()]
    }


@router.post("/upload")
async def upload_application_code(file: UploadFile = File(...)):
    """Upload application code for deployment."""
    logger.info(f"Uploading file: {file.filename}")
    
    # In production, upload to S3
    # For now, return a mock URL
    upload_id = str(uuid.uuid4())
    
    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size": file.size,
        "url": f"s3://autocloud-deployments/uploads/{upload_id}/{file.filename}",
        "message": "File uploaded successfully"
    }
