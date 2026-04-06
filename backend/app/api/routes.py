"""
AutoCloud Architect - API Routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from typing import Optional
import uuid
import logging

from app.config import get_settings

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
from app.services.monitoring_service import MonitoringService
from app.api.websocket import notify_deployment_update
from app.core.exceptions import bad_request_exception, not_found_exception

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# In-memory job storage (use Redis/DB in production)
deployment_jobs: dict[str, DeploymentJob] = {}

# Service instances
sagemaker_service = SageMakerService()
provisioning_service = ProvisioningService()
deployment_service = DeploymentService()
monitoring_service = MonitoringService()


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
    3. Deploy application code (from GitHub repo, S3, or sample app)
    4. Create CloudWatch dashboard and alarms
    5. Verify health
    """
    logger.info(f"Starting deployment for job: {request.job_id}")
    
    # Check if job already exists
    if request.job_id in deployment_jobs:
        raise bad_request_exception(f"Deployment job {request.job_id} already exists")
    
    # Determine the code URL — prefer repo_url, fallback to code_url
    code_url = request.repo_url or request.code_url
    
    # Also check if requirements dict contains repo_url
    if not code_url:
        code_url = request.requirements.get("repo_url")
    
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
        code_url
    )
    
    return job


async def _update_job_status(
    job: DeploymentJob,
    state: DeploymentState,
    progress: int,
    step: str,
    message: str
):
    """Update job status and send WebSocket notification."""
    from datetime import datetime
    
    job.status.state = state
    job.status.progress_percent = progress
    job.status.current_step = step
    job.status.message = message
    job.updated_at = datetime.utcnow()
    
    # Notify WebSocket clients
    try:
        await notify_deployment_update(job.job_id, {
            "state": state.value,
            "progress_percent": progress,
            "current_step": step,
            "message": message,
            "resources": [r.model_dump() for r in job.status.resources]
        })
    except Exception as e:
        logger.debug(f"WebSocket notification failed (non-critical): {str(e)}")


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
    
    app_name = requirements.get("app_name", "autocloud-app")
    
    try:
        # Step 1: Analyzing
        await _update_job_status(
            job, DeploymentState.ANALYZING, 10,
            "Validating configuration",
            "Validating infrastructure configuration..."
        )
        
        # Brief pause so frontend can see this step
        import asyncio
        await asyncio.sleep(2)
        
        # Step 2: Provisioning (this also deploys the app via UserData)
        await _update_job_status(
            job, DeploymentState.PROVISIONING, 20,
            "Creating CloudFormation stack",
            "Provisioning AWS resources (VPC, EC2, security groups) and deploying application... This may take 3-5 minutes."
        )
        
        # Create infrastructure — code_url is embedded in UserData
        stack_result = await provisioning_service.provision_infrastructure(
            app_name=app_name,
            recommendations=recommendations,
            code_url=code_url
        )
        
        job.stack_id = stack_result.get("stack_id")
        job.status.resources = stack_result.get("resources", [])
        stack_outputs = stack_result.get("outputs", {})
        
        public_ip = stack_outputs.get("PublicIP", "")
        instance_id = stack_outputs.get("InstanceId", "")
        alb_dns = stack_outputs.get("ALBDNSName", "")
        
        endpoint = f"http://{alb_dns}" if alb_dns else f"http://{public_ip}"
        
        await _update_job_status(
            job, DeploymentState.PROVISIONING, 60,
            "Infrastructure provisioned",
            f"AWS resources created. Instance: {instance_id}, IP: {public_ip}"
        )
        
        # Step 3: Waiting for deployment to complete (UserData runs on boot)
        await _update_job_status(
            job, DeploymentState.DEPLOYING, 70,
            "Application deploying",
            "Application is being deployed on the instance (installing dependencies, building)..."
        )
        
        # Give the UserData script time to run
        import asyncio
        await asyncio.sleep(30)
        
        deployment_result = {
            "endpoint": endpoint,
            "public_ip": public_ip,
            "instance_id": instance_id,
            "dashboard_url": f"https://{settings.aws_default_region}.console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}",
        }
        
        await _update_job_status(
            job, DeploymentState.DEPLOYING, 75,
            "Application deployed",
            "Application code deployed. Setting up monitoring..."
        )
        
        # Step 4: Set up monitoring (CloudWatch dashboard + alarms)
        instance_id = deployment_result.get("instance_id", "")
        dashboard_url = deployment_result.get("dashboard_url", "")
        
        if instance_id and instance_id != "i-mock12345":
            try:
                # Create CloudWatch dashboard
                dashboard_url = await monitoring_service.create_dashboard(
                    app_name=app_name,
                    instance_id=instance_id
                )
                logger.info(f"CloudWatch dashboard created: {dashboard_url}")
                
                # Create alarms
                alarms = await monitoring_service.create_alarms(
                    app_name=app_name,
                    instance_id=instance_id
                )
                logger.info(f"CloudWatch alarms created: {alarms}")
                
            except Exception as e:
                logger.warning(f"Monitoring setup failed (non-critical): {str(e)}")
        
        await _update_job_status(
            job, DeploymentState.VERIFYING, 85,
            "Running health checks",
            "Verifying deployment health..."
        )
        
        # Step 5: Health check
        health_result = await deployment_service.verify_health(
            endpoint=deployment_result.get("endpoint")
        )
        
        # Step 6: Complete
        job.status.state = DeploymentState.COMPLETED
        job.status.progress_percent = 100
        job.status.current_step = "Deployment complete"
        job.status.message = "Application deployed successfully!"
        job.endpoint_url = deployment_result.get("endpoint")
        job.cloudwatch_dashboard_url = dashboard_url
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        # Final WebSocket notification
        await notify_deployment_update(job.job_id, {
            "state": "completed",
            "progress_percent": 100,
            "current_step": "Deployment complete",
            "message": "Application deployed successfully!",
            "resources": [r.model_dump() for r in job.status.resources],
            "endpoint_url": job.endpoint_url,
            "cloudwatch_dashboard_url": job.cloudwatch_dashboard_url
        })
        
        logger.info(f"Deployment {job_id} completed: {job.endpoint_url}")
        
    except Exception as e:
        logger.error(f"Deployment {job_id} failed: {str(e)}")
        job.status.state = DeploymentState.FAILED
        job.status.error = str(e)
        job.status.message = f"Deployment failed: {str(e)}"
        job.updated_at = datetime.utcnow()
        
        # Notify about failure
        try:
            await notify_deployment_update(job.job_id, {
                "state": "failed",
                "progress_percent": job.status.progress_percent,
                "current_step": "Failed",
                "message": f"Deployment failed: {str(e)}",
                "error": str(e)
            })
        except Exception:
            pass


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
    
    logs = [
        {"timestamp": str(job.created_at), "message": "Deployment job created"},
        {"timestamp": str(job.updated_at), "message": job.status.message}
    ]
    
    if job.endpoint_url:
        logs.append({"timestamp": str(job.completed_at or job.updated_at), "message": f"Endpoint: {job.endpoint_url}"})
    if job.cloudwatch_dashboard_url:
        logs.append({"timestamp": str(job.completed_at or job.updated_at), "message": f"Dashboard: {job.cloudwatch_dashboard_url}"})
    
    return {
        "job_id": job_id,
        "logs": logs
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
    """Upload application code (ZIP file) for deployment."""
    logger.info(f"Uploading file: {file.filename}")
    
    upload_id = str(uuid.uuid4())
    filename = f"{upload_id}/{file.filename}"
    
    try:
        # Upload to S3
        s3_url = await deployment_service.upload_to_s3(file.file, filename)
        
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "size": file.size,
            "url": s3_url,
            "message": "File uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
