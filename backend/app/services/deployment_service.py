"""
AutoCloud Architect - Deployment Service

Handles application deployment to provisioned AWS resources.
"""
import boto3
import logging
import asyncio
from typing import Optional, List

from app.config import get_settings
from app.schemas.deployment import AWSResource
from app.core.exceptions import DeploymentException

logger = logging.getLogger(__name__)
settings = get_settings()


class DeploymentService:
    """
    Service for deploying applications to AWS infrastructure.
    
    Handles code packaging, uploading, and deployment to EC2 instances.
    """
    
    def __init__(self):
        """Initialize deployment clients."""
        self.use_mock = not settings.aws_access_key_id
        
        if not self.use_mock:
            self.s3_client = boto3.client(
                's3',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self.ssm_client = boto3.client(
                'ssm',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        
        logger.info(f"Deployment service initialized (mock={self.use_mock})")
    
    async def deploy_application(
        self,
        job_id: str,
        code_url: Optional[str],
        resources: List[AWSResource]
    ) -> dict:
        """
        Deploy application to provisioned resources.
        
        Args:
            job_id: Deployment job ID
            code_url: URL or path to application code
            resources: List of provisioned AWS resources
            
        Returns:
            Deployment result with endpoint URL
        """
        if self.use_mock:
            return await self._mock_deploy(job_id, resources)
        
        return await self._deploy_to_ec2(job_id, code_url, resources)
    
    async def _deploy_to_ec2(
        self,
        job_id: str,
        code_url: Optional[str],
        resources: List[AWSResource]
    ) -> dict:
        """Deploy application to EC2 instance."""
        try:
            # Find EC2 instance
            ec2_resource = next(
                (r for r in resources if r.resource_type == "AWS::EC2::Instance"),
                None
            )
            
            if not ec2_resource:
                raise DeploymentException("No EC2 instance found in resources")
            
            instance_id = ec2_resource.resource_id
            
            # Prepare deployment script
            deploy_script = self._generate_deploy_script(code_url)
            
            # Execute deployment via SSM
            response = self.ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    'commands': deploy_script
                }
            )
            
            command_id = response['Command']['CommandId']
            logger.info(f"Started deployment command: {command_id}")
            
            # Wait for command completion
            await self._wait_for_command(instance_id, command_id)
            
            # Get public IP
            public_ip = ec2_resource.details.get('public_ip', 'unknown')
            
            return {
                "endpoint": f"http://{public_ip}",
                "dashboard_url": f"https://console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}",
                "instance_id": instance_id
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise DeploymentException(f"Failed to deploy application: {str(e)}")
    
    def _generate_deploy_script(self, code_url: Optional[str]) -> list[str]:
        """Generate deployment shell script."""
        script = [
            "#!/bin/bash",
            "set -e",
            "",
            "# Update system",
            "yum update -y",
            "",
            "# Install Docker",
            "amazon-linux-extras install docker -y",
            "service docker start",
            "usermod -a -G docker ec2-user",
            "",
            "# Install nginx as reverse proxy",
            "amazon-linux-extras install nginx1 -y",
            "systemctl start nginx",
            "systemctl enable nginx",
        ]
        
        if code_url:
            script.extend([
                "",
                f"# Download application from {code_url}",
                f"aws s3 cp {code_url} /tmp/app.zip",
                "unzip /tmp/app.zip -d /var/www/app",
            ])
        else:
            script.extend([
                "",
                "# Create sample application",
                "mkdir -p /var/www/app",
                'echo "<html><body><h1>AutoCloud Architect - Deployed Successfully!</h1></body></html>" > /var/www/app/index.html',
            ])
        
        script.extend([
            "",
            "# Configure nginx",
            "cat > /etc/nginx/conf.d/app.conf << 'EOF'",
            "server {",
            "    listen 80;",
            "    root /var/www/app;",
            "    index index.html;",
            "}",
            "EOF",
            "",
            "# Restart nginx",
            "systemctl restart nginx",
            "",
            "echo 'Deployment complete!'",
        ])
        
        return script
    
    async def _wait_for_command(self, instance_id: str, command_id: str):
        """Wait for SSM command to complete."""
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            response = self.ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            
            status = response['Status']
            
            if status in ['Success']:
                logger.info(f"Command {command_id} completed successfully")
                return
            elif status in ['Failed', 'Cancelled', 'TimedOut']:
                raise DeploymentException(f"Deployment command failed: {status}")
            
            await asyncio.sleep(5)
            attempt += 1
        
        raise DeploymentException("Deployment command timed out")
    
    async def _mock_deploy(
        self,
        job_id: str,
        resources: List[AWSResource]
    ) -> dict:
        """Mock deployment for development."""
        logger.info("Using mock deployment (AWS not configured)")
        
        # Simulate deployment delay
        await asyncio.sleep(3)
        
        # Find mock EC2 resource
        ec2_resource = next(
            (r for r in resources if r.resource_type == "AWS::EC2::Instance"),
            None
        )
        
        public_ip = "54.123.45.67"
        if ec2_resource:
            public_ip = ec2_resource.details.get('public_ip', public_ip)
        
        return {
            "endpoint": f"http://{public_ip}",
            "dashboard_url": f"https://console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}",
            "instance_id": "i-mock12345",
            "status": "deployed"
        }
    
    async def verify_health(self, endpoint: Optional[str]) -> dict:
        """
        Verify deployment health by checking the endpoint.
        
        Args:
            endpoint: Application endpoint URL
            
        Returns:
            Health check result
        """
        if not endpoint:
            return {"healthy": True, "message": "No endpoint to check"}
        
        if self.use_mock:
            await asyncio.sleep(1)
            return {
                "healthy": True,
                "endpoint": endpoint,
                "status_code": 200,
                "message": "Mock health check passed"
            }
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, timeout=10.0)
                
                return {
                    "healthy": response.status_code == 200,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "message": "Health check passed" if response.status_code == 200 else "Health check failed"
                }
                
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return {
                "healthy": False,
                "endpoint": endpoint,
                "error": str(e),
                "message": f"Health check failed: {str(e)}"
            }
