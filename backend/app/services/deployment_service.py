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
    
    Handles code cloning from GitHub, packaging, and deployment to EC2 instances
    via SSM Run Command.
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
            self.ec2_client = boto3.client(
                'ec2',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        
        logger.info(f"Deployment service initialized (mock={self.use_mock})")
    
    async def deploy_application(
        self,
        job_id: str,
        code_url: Optional[str],
        resources: List[AWSResource],
        stack_outputs: Optional[dict] = None
    ) -> dict:
        """
        Deploy application to provisioned resources.
        
        Args:
            job_id: Deployment job ID
            code_url: GitHub repo URL, S3 URL, or None for sample app
            resources: List of provisioned AWS resources
            stack_outputs: CloudFormation stack outputs with PublicIP, InstanceId, etc.
            
        Returns:
            Deployment result with endpoint URL and dashboard info
        """
        if self.use_mock:
            return await self._mock_deploy(job_id, resources)
        
        return await self._deploy_to_ec2(job_id, code_url, resources, stack_outputs)
    
    async def _deploy_to_ec2(
        self,
        job_id: str,
        code_url: Optional[str],
        resources: List[AWSResource],
        stack_outputs: Optional[dict] = None
    ) -> dict:
        """Deploy application to EC2 instance via SSM."""
        try:
            # Get instance ID from stack outputs or resources
            instance_id = None
            public_ip = None
            
            if stack_outputs:
                instance_id = stack_outputs.get("InstanceId")
                public_ip = stack_outputs.get("PublicIP")
                # If ALB is configured, use its DNS name
                alb_dns = stack_outputs.get("ALBDNSName")
            
            if not instance_id:
                # Fallback: find from resources list
                ec2_resource = next(
                    (r for r in resources if r.resource_type == "AWS::EC2::Instance"),
                    None
                )
                if not ec2_resource:
                    raise DeploymentException("No EC2 instance found in provisioned resources")
                instance_id = ec2_resource.resource_id
            
            logger.info(f"Deploying to instance {instance_id} (IP: {public_ip})")
            
            # Wait for SSM agent to be ready on the instance
            await self._wait_for_ssm_agent(instance_id)
            
            # Wait a bit more for UserData script to finish
            logger.info("Waiting for instance bootstrap to complete...")
            await asyncio.sleep(30)
            
            # Generate and execute deployment script
            deploy_script = self._generate_deploy_script(code_url)
            
            response = self.ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    'commands': deploy_script,
                    'executionTimeout': ['600']
                },
                TimeoutSeconds=600
            )
            
            command_id = response['Command']['CommandId']
            logger.info(f"Started deployment command: {command_id}")
            
            # Wait for command completion
            await self._wait_for_command(instance_id, command_id)
            
            # If we don't have the public IP yet, fetch it
            if not public_ip:
                public_ip = await self._get_instance_public_ip(instance_id)
            
            # Determine the endpoint URL
            endpoint = f"http://{alb_dns}" if alb_dns else f"http://{public_ip}"
            
            return {
                "endpoint": endpoint,
                "public_ip": public_ip,
                "dashboard_url": f"https://{settings.aws_default_region}.console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}",
                "instance_id": instance_id,
                "status": "deployed"
            }
            
        except DeploymentException:
            raise
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise DeploymentException(f"Failed to deploy application: {str(e)}")
    
    async def _wait_for_ssm_agent(self, instance_id: str, max_wait: int = 300):
        """Wait for SSM agent to come online on the instance."""
        logger.info(f"Waiting for SSM agent on {instance_id}...")
        
        elapsed = 0
        interval = 10
        
        while elapsed < max_wait:
            try:
                response = self.ssm_client.describe_instance_information(
                    Filters=[
                        {'Key': 'InstanceIds', 'Values': [instance_id]}
                    ]
                )
                
                instances = response.get('InstanceInformationList', [])
                if instances and instances[0].get('PingStatus') == 'Online':
                    logger.info(f"SSM agent is online on {instance_id}")
                    return
                    
            except Exception as e:
                logger.debug(f"SSM check error (will retry): {str(e)}")
            
            await asyncio.sleep(interval)
            elapsed += interval
        
        raise DeploymentException(
            f"SSM agent did not come online on {instance_id} within {max_wait}s. "
            "The instance may still be booting. Check the instance status in AWS Console."
        )
    
    async def _get_instance_public_ip(self, instance_id: str) -> str:
        """Fetch the public IP of an EC2 instance."""
        try:
            response = self.ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            
            reservations = response.get('Reservations', [])
            if reservations:
                instances = reservations[0].get('Instances', [])
                if instances:
                    public_ip = instances[0].get('PublicIpAddress')
                    if public_ip:
                        return public_ip
            
            return "unknown"
            
        except Exception as e:
            logger.error(f"Failed to get public IP: {str(e)}")
            return "unknown"
    
    def _generate_deploy_script(self, code_url: Optional[str]) -> list[str]:
        """
        Generate deployment shell script.
        
        Supports:
        - GitHub/GitLab repo URLs (git clone)
        - S3 URLs (aws s3 cp)
        - No URL (deploy sample page)
        
        Auto-detects project type and installs dependencies accordingly.
        """
        script = [
            "#!/bin/bash",
            "set -e",
            "exec > /var/log/deploy.log 2>&1",
            "",
            "echo '=== AutoCloud Architect: Starting Deployment ==='",
            "cd /var/www/app",
            "",
        ]
        
        if code_url and self._is_git_url(code_url):
            # GitHub/GitLab repository
            script.extend(self._generate_git_deploy_script(code_url))
        elif code_url and code_url.startswith("s3://"):
            # S3 download
            script.extend(self._generate_s3_deploy_script(code_url))
        else:
            # Deploy sample application
            script.extend(self._generate_sample_deploy_script())
        
        # Auto-detect project type and build
        script.extend(self._generate_auto_detect_script())
        
        script.extend([
            "",
            "# Restart nginx to pick up any config changes",
            "systemctl restart nginx",
            "",
            "echo '=== AutoCloud Architect: Deployment Complete ==='",
        ])
        
        return script
    
    def _is_git_url(self, url: str) -> bool:
        """Check if URL is a Git repository URL."""
        git_hosts = ['github.com', 'gitlab.com', 'bitbucket.org']
        return any(host in url for host in git_hosts) or url.endswith('.git')
    
    def _generate_git_deploy_script(self, repo_url: str) -> list[str]:
        """Generate script to clone and deploy from a Git repository."""
        # Clean up the URL (handle various formats)
        clean_url = repo_url.strip()
        if not clean_url.endswith('.git'):
            clean_url = clean_url.rstrip('/') + '.git'
        
        return [
            f"echo 'Cloning repository: {repo_url}'",
            "",
            "# Clean existing files",
            "rm -rf /var/www/app/*",
            "rm -rf /var/www/app/.* 2>/dev/null || true",
            "",
            "# Clone the repository",
            f"git clone {clean_url} /var/www/app",
            "",
            "echo 'Repository cloned successfully'",
            "ls -la /var/www/app/",
            "",
        ]
    
    def _generate_s3_deploy_script(self, s3_url: str) -> list[str]:
        """Generate script to download and deploy from S3."""
        return [
            f"echo 'Downloading from S3: {s3_url}'",
            "",
            "# Clean existing files",
            "rm -rf /var/www/app/*",
            "",
            "# Download from S3",
            f"aws s3 cp {s3_url} /tmp/app-code.zip",
            "",
            "# Extract",
            "cd /var/www/app",
            "unzip -o /tmp/app-code.zip",
            "rm /tmp/app-code.zip",
            "",
            "# If there's a single directory inside, move its contents up",
            "DIRS=($(find . -maxdepth 1 -mindepth 1 -type d))",
            "if [ ${#DIRS[@]} -eq 1 ] && [ ! -f index.html ] && [ ! -f package.json ]; then",
            "    mv ${DIRS[0]}/* . 2>/dev/null || true",
            "    mv ${DIRS[0]}/.* . 2>/dev/null || true",
            "    rmdir ${DIRS[0]} 2>/dev/null || true",
            "fi",
            "",
        ]
    
    def _generate_sample_deploy_script(self) -> list[str]:
        """Generate script to deploy a sample HTML application."""
        return [
            "echo 'Deploying sample application'",
            "",
            "cat > /var/www/app/index.html << 'HTMLEOF'",
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "    <title>AutoCloud Architect - Deployed</title>",
            "    <style>",
            "        * { margin: 0; padding: 0; box-sizing: border-box; }",
            "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }",
            "        .container { text-align: center; padding: 2rem; }",
            "        h1 { font-size: 3rem; background: linear-gradient(135deg, #3b82f6, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem; }",
            "        .badge { display: inline-block; background: rgba(16,185,129,0.2); color: #10b981; padding: 0.5rem 1rem; border-radius: 999px; font-size: 0.875rem; margin-bottom: 2rem; }",
            "        p { color: #94a3b8; font-size: 1.125rem; max-width: 500px; margin: 0 auto 1.5rem; }",
            "        .info { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 1.5rem; margin-top: 2rem; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto; }",
            "        .info-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); }",
            "        .info-row:last-child { border: none; }",
            "        .info-label { color: #94a3b8; }",
            "        .info-value { color: #3b82f6; font-weight: 600; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='container'>",
            "        <div class='badge'>✅ Deployed Successfully</div>",
            "        <h1>AutoCloud Architect</h1>",
            "        <p>Your infrastructure has been provisioned and this application is live on AWS.</p>",
            "        <div class='info'>",
            "            <div class='info-row'><span class='info-label'>Status</span><span class='info-value'>Running</span></div>",
            "            <div class='info-row'><span class='info-label'>Platform</span><span class='info-value'>AWS EC2</span></div>",
            "            <div class='info-row'><span class='info-label'>Server</span><span class='info-value'>Nginx</span></div>",
            "        </div>",
            "    </div>",
            "</body>",
            "</html>",
            "HTMLEOF",
            "",
        ]
    
    def _generate_auto_detect_script(self) -> list[str]:
        """
        Generate script that auto-detects the project type and builds accordingly.
        
        Supports: Node.js (package.json), Python (requirements.txt), static HTML (index.html).
        """
        return [
            "cd /var/www/app",
            "",
            "# Auto-detect project type and build",
            "if [ -f 'package.json' ]; then",
            "    echo 'Detected Node.js project'",
            "    ",
            "    # Install dependencies",
            "    npm install --production 2>/dev/null || npm install",
            "    ",
            "    # Check if there's a build script (React, Vue, etc.)",
            "    if grep -q '\"build\"' package.json; then",
            "        echo 'Running build...'",
            "        npm run build 2>/dev/null || true",
            "        ",
            "        # Find the build output directory",
            "        if [ -d 'build' ]; then",
            "            echo 'Serving from build/ directory'",
            "            # Update nginx to serve from build dir",
            "            sed -i 's|root /var/www/app;|root /var/www/app/build;|' /etc/nginx/conf.d/app.conf",
            "        elif [ -d 'dist' ]; then",
            "            echo 'Serving from dist/ directory'",
            "            sed -i 's|root /var/www/app;|root /var/www/app/dist;|' /etc/nginx/conf.d/app.conf",
            "        elif [ -d 'out' ]; then",
            "            echo 'Serving from out/ directory'",
            "            sed -i 's|root /var/www/app;|root /var/www/app/out;|' /etc/nginx/conf.d/app.conf",
            "        fi",
            "    else",
            "        # No build script — it's likely a server app (Express, Fastify)",
            "        echo 'Starting Node.js server with PM2'",
            "        ",
            "        # Determine the entry point",
            "        ENTRY=$(node -e \"const p=require('./package.json'); console.log(p.main || 'index.js')\" 2>/dev/null || echo 'index.js')",
            "        START_SCRIPT=$(node -e \"const p=require('./package.json'); console.log(p.scripts && p.scripts.start ? 'start' : '')\" 2>/dev/null || echo '')",
            "        ",
            "        if [ -n \"$START_SCRIPT\" ]; then",
            "            pm2 start npm --name app -- start",
            "        elif [ -f \"$ENTRY\" ]; then",
            "            PORT=3000 pm2 start $ENTRY --name app",
            "        fi",
            "        pm2 save 2>/dev/null || true",
            "        ",
            "        # Update nginx to proxy to the Node app",
            "        cat > /etc/nginx/conf.d/app.conf << 'NGINXEOF'",
            "server {",
            "    listen 80 default_server;",
            "    location / {",
            "        proxy_pass http://localhost:3000;",
            "        proxy_http_version 1.1;",
            "        proxy_set_header Upgrade $http_upgrade;",
            "        proxy_set_header Connection 'upgrade';",
            "        proxy_set_header Host $host;",
            "        proxy_cache_bypass $http_upgrade;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "    }",
            "}",
            "NGINXEOF",
            "    fi",
            "",
            "elif [ -f 'requirements.txt' ]; then",
            "    echo 'Detected Python project'",
            "    ",
            "    # Create virtual environment and install deps",
            "    python3.11 -m venv venv",
            "    source venv/bin/activate",
            "    pip install -r requirements.txt",
            "    pip install gunicorn 2>/dev/null || true",
            "    ",
            "    # Find the entry point",
            "    if [ -f 'app.py' ]; then",
            "        ENTRY='app:app'",
            "    elif [ -f 'main.py' ]; then",
            "        ENTRY='main:app'",
            "    elif [ -f 'wsgi.py' ]; then",
            "        ENTRY='wsgi:app'",
            "    elif [ -f 'manage.py' ]; then",
            "        # Django",
            "        python manage.py collectstatic --noinput 2>/dev/null || true",
            "        ENTRY=$(find . -name 'wsgi.py' | head -1 | sed 's|./||;s|/|.|g;s|.py$||'):application",
            "    else",
            "        ENTRY='app:app'",
            "    fi",
            "    ",
            "    # Start with gunicorn",
            "    nohup /var/www/app/venv/bin/gunicorn $ENTRY -b 0.0.0.0:8000 --daemon 2>/dev/null || true",
            "    ",
            "    # Update nginx to proxy to Python app",
            "    cat > /etc/nginx/conf.d/app.conf << 'NGINXEOF'",
            "server {",
            "    listen 80 default_server;",
            "    location / {",
            "        proxy_pass http://localhost:8000;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "    }",
            "    location /static/ {",
            "        root /var/www/app;",
            "    }",
            "}",
            "NGINXEOF",
            "",
            "elif [ -f 'index.html' ]; then",
            "    echo 'Detected static HTML project — serving directly with nginx'",
            "    # nginx is already configured to serve from /var/www/app",
            "",
            "else",
            "    echo 'Could not detect project type. Serving directory contents with nginx.'",
            "fi",
            "",
            "# Fix permissions",
            "chown -R ec2-user:ec2-user /var/www/app",
            "",
        ]
    
    async def _wait_for_command(self, instance_id: str, command_id: str):
        """Wait for SSM command to complete."""
        max_attempts = 120  # 10 minutes
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = self.ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                status = response['Status']
                
                if status == 'Success':
                    logger.info(f"Command {command_id} completed successfully")
                    output = response.get('StandardOutputContent', '')
                    if output:
                        logger.info(f"Command output (last 500 chars): {output[-500:]}")
                    return
                elif status in ['Failed', 'Cancelled', 'TimedOut']:
                    error_output = response.get('StandardErrorContent', '')
                    stdout = response.get('StandardOutputContent', '')
                    detail = error_output or stdout or status
                    raise DeploymentException(
                        f"Deployment command failed ({status}): {detail[-500:]}"
                    )
                elif status in ['InProgress', 'Pending', 'Delayed']:
                    pass  # Still running
                    
            except DeploymentException:
                raise
            except Exception as e:
                # Command might not be available yet
                if 'InvocationDoesNotExist' in str(e):
                    pass
                else:
                    logger.warning(f"Error checking command: {str(e)}")
            
            await asyncio.sleep(5)
            attempt += 1
        
        raise DeploymentException("Deployment command timed out after 10 minutes")
    
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
            "public_ip": public_ip,
            "dashboard_url": f"https://{settings.aws_default_region}.console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}",
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
        
        # Try health check with retries (app may need time to start)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                import httpx
                
                async with httpx.AsyncClient(verify=False) as client:
                    response = await client.get(endpoint, timeout=15.0, follow_redirects=True)
                    
                    if response.status_code < 500:
                        return {
                            "healthy": response.status_code < 400,
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "message": "Health check passed" if response.status_code < 400 else f"HTTP {response.status_code}"
                        }
                        
            except Exception as e:
                logger.warning(f"Health check attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(10)
        
        return {
            "healthy": False,
            "endpoint": endpoint,
            "message": "Health check failed after retries — app may still be starting"
        }

    async def upload_to_s3(self, file_content, filename: str) -> str:
        """
        Upload a file to S3 and return its URL.
        
        Args:
            file_content: File-like object to upload
            filename: Name for the file in S3
            
        Returns:
            S3 URL of the uploaded file
        """
        if self.use_mock:
            return f"s3://{settings.s3_deployment_bucket}/uploads/{filename}"
        
        try:
            bucket = settings.s3_deployment_bucket
            key = f"uploads/{filename}"
            
            self.s3_client.upload_fileobj(
                file_content,
                bucket,
                key
            )
            
            s3_url = f"s3://{bucket}/{key}"
            logger.info(f"Uploaded to S3: {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise DeploymentException(f"Failed to upload file: {str(e)}")
