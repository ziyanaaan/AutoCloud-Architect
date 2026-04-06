"""
AutoCloud Architect - Provisioning Service

Handles AWS infrastructure provisioning using CloudFormation.
"""
import boto3
import json
import logging
import asyncio
from typing import Optional

from app.config import get_settings
from app.schemas.deployment import RecommendationOutput, AWSResource
from app.core.exceptions import ProvisioningException

logger = logging.getLogger(__name__)
settings = get_settings()


class ProvisioningService:
    """
    Service for provisioning AWS infrastructure.
    
    Uses CloudFormation to create and manage AWS resources
    based on the recommendations from SageMaker.
    """
    
    def __init__(self):
        """Initialize CloudFormation client."""
        self.use_mock = not settings.aws_access_key_id
        
        if not self.use_mock:
            self.cf_client = boto3.client(
                'cloudformation',
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
        
        # Cache for AMI ID lookup
        self._ami_id_cache = None
        
        logger.info(f"Provisioning service initialized (mock={self.use_mock})")
    
    def _get_latest_ami_id(self) -> str:
        """Get latest Amazon Linux 2023 AMI ID using EC2 API.
        
        Falls back to a known AMI ID if the API call fails.
        """
        if self._ami_id_cache:
            return self._ami_id_cache
        
        # Known fallback AMI IDs per region (Amazon Linux 2023, x86_64)
        fallback_amis = {
            "us-east-1": "ami-0c02fb55956c7d316",
            "us-east-2": "ami-05bfbece1ed5beb54",
            "us-west-1": "ami-0ed05376b59b90e46",
            "us-west-2": "ami-0735c191cf914754d",
            "eu-west-1": "ami-0905a3c97561e0b69",
            "eu-central-1": "ami-0faab6bdbac9486fb",
            "ap-south-1": "ami-0a4408457f9a03be3",
            "ap-southeast-1": "ami-0c802847a7dd848c0",
        }
        
        if self.use_mock:
            return fallback_amis.get(settings.aws_default_region, "ami-0c02fb55956c7d316")
        
        try:
            response = self.ec2_client.describe_images(
                Filters=[
                    {'Name': 'name', 'Values': ['al2023-ami-2023*-x86_64']},
                    {'Name': 'state', 'Values': ['available']},
                    {'Name': 'owner-alias', 'Values': ['amazon']},
                    {'Name': 'architecture', 'Values': ['x86_64']},
                ],
                Owners=['amazon']
            )
            
            images = response.get('Images', [])
            if images:
                # Sort by creation date (newest first)
                images.sort(key=lambda x: x.get('CreationDate', ''), reverse=True)
                self._ami_id_cache = images[0]['ImageId']
                logger.info(f"Found latest AMI: {self._ami_id_cache} ({images[0].get('Name', '')})")
                return self._ami_id_cache
        except Exception as e:
            logger.warning(f"EC2 AMI lookup failed: {str(e)[:100]}")
        
        # Fallback
        ami = fallback_amis.get(settings.aws_default_region, "ami-0c02fb55956c7d316")
        logger.info(f"Using fallback AMI: {ami}")
        self._ami_id_cache = ami
        return ami
    
    async def provision_infrastructure(
        self,
        app_name: str,
        recommendations: RecommendationOutput,
        code_url: str = None
    ) -> dict:
        """
        Provision AWS infrastructure based on recommendations.
        
        Args:
            app_name: Name of the application
            recommendations: Infrastructure recommendations
            
        Returns:
            Dictionary with stack_id and provisioned resources
        """
        if self.use_mock:
            return await self._mock_provision(app_name, recommendations)
        
        return await self._create_stack(app_name, recommendations, code_url)
    
    async def _create_stack(
        self,
        app_name: str,
        recommendations: RecommendationOutput,
        code_url: str = None
    ) -> dict:
        """Create CloudFormation stack."""
        try:
            stack_name = f"autocloud-{app_name.lower().replace(' ', '-').replace('_', '-')}"
            
            # Generate CloudFormation template
            template = self._generate_template(app_name, recommendations, code_url)
            
            # Validate template (optional — CreateStack validates anyway)
            try:
                self.cf_client.validate_template(
                    TemplateBody=json.dumps(template)
                )
                logger.info("CloudFormation template validated successfully")
            except Exception as e:
                logger.warning(f"Template validation skipped ({str(e)[:100]}). Proceeding with CreateStack.")
            
            # Create stack
            create_params = {
                'StackName': stack_name,
                'TemplateBody': json.dumps(template),
                'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                'Tags': [
                    {'Key': 'Application', 'Value': app_name},
                    {'Key': 'ManagedBy', 'Value': 'AutoCloud-Architect'}
                ]
            }
            
            response = self.cf_client.create_stack(**create_params)
            
            stack_id = response['StackId']
            logger.info(f"Created CloudFormation stack: {stack_id}")
            
            # Wait for stack creation
            resources = await self._wait_for_stack(stack_name)
            
            # Get stack outputs (public IP, instance ID, etc.)
            outputs = await self._get_stack_outputs(stack_name)
            
            return {
                "stack_id": stack_id,
                "stack_name": stack_name,
                "resources": resources,
                "outputs": outputs
            }
            
        except ProvisioningException:
            raise
        except Exception as e:
            logger.error(f"Stack creation failed: {str(e)}")
            raise ProvisioningException(f"Failed to provision infrastructure: {str(e)}")
    
    async def _wait_for_stack(self, stack_name: str) -> list[AWSResource]:
        """Wait for stack creation and return resources."""
        logger.info(f"Waiting for stack {stack_name} to complete...")
        
        max_attempts = 120  # 20 minutes max
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = self.cf_client.describe_stacks(StackName=stack_name)
                stack = response['Stacks'][0]
                stack_status = stack['StackStatus']
                
                if stack_status == 'CREATE_COMPLETE':
                    logger.info(f"Stack {stack_name} created successfully")
                    break
                elif stack_status in ['CREATE_FAILED', 'ROLLBACK_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_FAILED']:
                    # Get failure reason
                    events = self.cf_client.describe_stack_events(StackName=stack_name)
                    failure_reasons = [
                        e.get('ResourceStatusReason', '')
                        for e in events.get('StackEvents', [])
                        if 'FAILED' in e.get('ResourceStatus', '')
                    ]
                    reason = '; '.join(filter(None, failure_reasons[:3])) or 'Unknown failure'
                    raise ProvisioningException(f"Stack creation failed: {reason}")
                
                logger.info(f"Stack status: {stack_status} (attempt {attempt + 1})")
                
            except ProvisioningException:
                raise
            except Exception as e:
                logger.warning(f"Error checking stack status: {str(e)}")
            
            await asyncio.sleep(10)
            attempt += 1
        
        if attempt >= max_attempts:
            raise ProvisioningException("Stack creation timed out after 20 minutes")
        
        # Get stack resources
        response = self.cf_client.describe_stack_resources(StackName=stack_name)
        
        resources = []
        for resource in response.get('StackResources', []):
            resources.append(AWSResource(
                resource_type=resource['ResourceType'],
                resource_id=resource.get('PhysicalResourceId', 'pending'),
                status=resource['ResourceStatus'],
                details={
                    'logical_id': resource['LogicalResourceId']
                }
            ))
        
        return resources
    
    async def _get_stack_outputs(self, stack_name: str) -> dict:
        """Get outputs from a completed CloudFormation stack."""
        try:
            response = self.cf_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            outputs = {}
            for output in stack.get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            
            logger.info(f"Stack outputs: {outputs}")
            return outputs
            
        except Exception as e:
            logger.error(f"Failed to get stack outputs: {str(e)}")
            return {}
    
    def _generate_template(
        self,
        app_name: str,
        recommendations: RecommendationOutput,
        code_url: str = None
    ) -> dict:
        """Generate a complete, working CloudFormation template."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": f"AutoCloud Architect - {app_name}",
            "Parameters": {
                "AppName": {
                    "Type": "String",
                    "Default": app_name
                },
                "InstanceType": {
                    "Type": "String",
                    "Default": recommendations.compute.instance_type
                },
                "AmiId": {
                    "Type": "String",
                    "Default": self._get_latest_ami_id()
                }
            },
            "Resources": {},
            "Outputs": {}
        }
        
        # Add key pair parameter if configured
        if settings.ec2_key_pair_name:
            template["Parameters"]["KeyName"] = {
                "Type": "String",
                "Default": settings.ec2_key_pair_name
            }
        
        # Build template in correct dependency order
        self._add_vpc_resources(template)
        self._add_compute_resources(template, recommendations, code_url)
        self._add_storage_resources(template, recommendations)
        
        if recommendations.database:
            self._add_database_resources(template, recommendations)
        
        if recommendations.networking.use_alb:
            self._add_alb_resources(template)
        
        return template
    
    def _add_vpc_resources(self, template: dict):
        """Add VPC, subnets, internet gateway, route table — everything needed for internet access."""
        resources = template["Resources"]
        
        # VPC
        resources["VPC"] = {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16",
                "EnableDnsHostnames": True,
                "EnableDnsSupport": True,
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-vpc"}}]
            }
        }
        
        # Internet Gateway
        resources["InternetGateway"] = {
            "Type": "AWS::EC2::InternetGateway",
            "Properties": {
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-igw"}}]
            }
        }
        
        resources["AttachGateway"] = {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "InternetGatewayId": {"Ref": "InternetGateway"}
            }
        }
        
        # Route Table with route to Internet Gateway
        resources["PublicRouteTable"] = {
            "Type": "AWS::EC2::RouteTable",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-public-rt"}}]
            }
        }
        
        resources["PublicRoute"] = {
            "Type": "AWS::EC2::Route",
            "DependsOn": "AttachGateway",
            "Properties": {
                "RouteTableId": {"Ref": "PublicRouteTable"},
                "DestinationCidrBlock": "0.0.0.0/0",
                "GatewayId": {"Ref": "InternetGateway"}
            }
        }
        
        # Public Subnet 1 (AZ-a)
        resources["PublicSubnet1"] = {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.1.0/24",
                "MapPublicIpOnLaunch": True,
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-public-1"}}]
            }
        }
        
        resources["Subnet1RouteTableAssoc"] = {
            "Type": "AWS::EC2::SubnetRouteTableAssociation",
            "Properties": {
                "SubnetId": {"Ref": "PublicSubnet1"},
                "RouteTableId": {"Ref": "PublicRouteTable"}
            }
        }
        
        # Public Subnet 2 (AZ-b) — required for ALB and high availability
        resources["PublicSubnet2"] = {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.2.0/24",
                "MapPublicIpOnLaunch": True,
                "AvailabilityZone": {"Fn::Select": [1, {"Fn::GetAZs": ""}]},
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-public-2"}}]
            }
        }
        
        resources["Subnet2RouteTableAssoc"] = {
            "Type": "AWS::EC2::SubnetRouteTableAssociation",
            "Properties": {
                "SubnetId": {"Ref": "PublicSubnet2"},
                "RouteTableId": {"Ref": "PublicRouteTable"}
            }
        }
        
        # Outputs
        template["Outputs"]["VpcId"] = {
            "Value": {"Ref": "VPC"},
            "Description": "VPC ID"
        }
    
    def _add_compute_resources(self, template: dict, recommendations: RecommendationOutput, code_url: str = None):
        """Add EC2 instance with security group and full deployment UserData."""
        resources = template["Resources"]
        
        # Security Group
        resources["SecurityGroup"] = {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": {"Fn::Sub": "${AppName} security group"},
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 3000, "ToPort": 3000, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "CidrIp": "0.0.0.0/0"}
                ],
                "Tags": [{"Key": "Name", "Value": {"Fn::Sub": "${AppName}-sg"}}]
            }
        }
        
        # Build the full UserData script with deployment logic baked in
        userdata_script = self._build_userdata_script(code_url)
        
        # EC2 Instance
        ec2_properties = {
            "InstanceType": {"Ref": "InstanceType"},
            "ImageId": {"Ref": "AmiId"},
            "SubnetId": {"Ref": "PublicSubnet1"},
            "SecurityGroupIds": [{"Ref": "SecurityGroup"}],
            "UserData": {"Fn::Base64": userdata_script},
            "Tags": [
                {"Key": "Name", "Value": {"Ref": "AppName"}},
                {"Key": "ManagedBy", "Value": "AutoCloud-Architect"}
            ]
        }
        
        # Add key pair if configured
        if settings.ec2_key_pair_name:
            ec2_properties["KeyName"] = {"Ref": "KeyName"}
        
        resources["EC2Instance"] = {
            "Type": "AWS::EC2::Instance",
            "DependsOn": "PublicRoute",
            "Properties": ec2_properties
        }
        
        # Outputs
        template["Outputs"]["InstanceId"] = {
            "Value": {"Ref": "EC2Instance"},
            "Description": "EC2 Instance ID"
        }
        
        template["Outputs"]["PublicIP"] = {
            "Value": {"Fn::GetAtt": ["EC2Instance", "PublicIp"]},
            "Description": "Public IP Address"
        }
    
    def _build_userdata_script(self, code_url: str = None) -> str:
        """Build a complete UserData script that bootstraps the instance AND deploys the app.
        
        This approach avoids needing IAM roles or SSM - everything runs
        during instance boot via UserData.
        """
        # Determine what to deploy
        if code_url and any(host in code_url for host in ['github.com', 'gitlab.com', 'bitbucket.org']):
            # Git repository
            clean_url = code_url.strip().rstrip('/')
            if not clean_url.endswith('.git'):
                clean_url += '.git'
            deploy_section = f"""
# Clone the repository
echo "Cloning repository: {code_url}"
if ! git clone {clean_url} /var/www/app; then
    echo "Failed to clone repository. Dropping error page."
    mkdir -p /var/www/app
    echo "<html><head><title>Deployment Error</title><style>body{{font-family:sans-serif;text-align:center;padding:50px}}</style></head><body><h1>Deployment Failed</h1><p>AutoCloud Architect could not clone the repository at <b>{code_url}</b>.</p><p>Please ensure the repository is public and the URL is correct.</p></body></html>" > /var/www/app/index.html
fi
cd /var/www/app || true
echo "Repository step completed"
"""
        elif code_url and code_url.startswith('s3://'):
            deploy_section = f"""
# Download from S3
echo "Downloading from S3: {code_url}"
aws s3 cp {code_url} /tmp/app-code.zip
cd /var/www/app
unzip -o /tmp/app-code.zip
rm /tmp/app-code.zip
"""
        else:
            deploy_section = """
# Deploy sample application
cat > /var/www/app/index.html << 'SAMPLEEOF'
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>AutoCloud Architect - Live</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#0f172a,#1e293b);color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center}.c{text-align:center;padding:2rem}h1{font-size:3rem;background:linear-gradient(135deg,#3b82f6,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:1rem}.b{display:inline-block;background:rgba(16,185,129,.2);color:#10b981;padding:.5rem 1rem;border-radius:999px;font-size:.875rem;margin-bottom:2rem}p{color:#94a3b8;font-size:1.125rem;max-width:500px;margin:0 auto 1.5rem}.i{background:rgba(255,255,255,.05);border-radius:12px;padding:1.5rem;margin-top:2rem;text-align:left;max-width:400px;margin-left:auto;margin-right:auto}.r{display:flex;justify-content:space-between;padding:.5rem 0;border-bottom:1px solid rgba(255,255,255,.1)}.r:last-child{border:none}.l{color:#94a3b8}.v{color:#3b82f6;font-weight:600}</style></head>
<body><div class="c"><div class="b">Deployed Successfully</div><h1>AutoCloud Architect</h1><p>Your infrastructure has been provisioned and this application is live on AWS.</p><div class="i"><div class="r"><span class="l">Status</span><span class="v">Running</span></div><div class="r"><span class="l">Platform</span><span class="v">AWS EC2</span></div><div class="r"><span class="l">Server</span><span class="v">Nginx</span></div></div></div></body></html>
SAMPLEEOF
"""

        ssh_section = ""
        if settings.ec2_ssh_public_key:
            ssh_section = f"""
# Inject SSH Public Key
echo "Injecting SSH public key"
mkdir -p /home/ec2-user/.ssh
echo "{settings.ec2_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
chmod 700 /home/ec2-user/.ssh
chmod 600 /home/ec2-user/.ssh/authorized_keys
chown -R ec2-user:ec2-user /home/ec2-user/.ssh
"""

        return f"""#!/bin/bash
exec > /var/log/userdata.log 2>&1

echo "=== AutoCloud Architect: Bootstrapping ==="
{ssh_section}
# Update and install packages
dnf update -y
dnf install -y git nginx unzip

# Try to install Node.js and Python (may vary by AMI)
dnf install -y nodejs npm python3.11 python3.11-pip 2>/dev/null || dnf install -y nodejs python3-pip 2>/dev/null || true

# Install PM2 globally if npm is available
npm install -g pm2 2>/dev/null || true

# Create app directory
mkdir -p /var/www/app
chown -R ec2-user:ec2-user /var/www/app

# ===== DEPLOY APPLICATION =====
{deploy_section}

# ===== AUTO-DETECT AND BUILD =====
cd /var/www/app

APP_ROOT="/var/www/app"

if [ -f "package.json" ]; then
    echo "Detected Node.js project"
    npm install --production 2>/dev/null || npm install 2>/dev/null || true
    
    if grep -q '"build"' package.json 2>/dev/null; then
        echo "Running build..."
        npm run build 2>/dev/null || true
        
        if [ -d "build" ]; then
            APP_ROOT="/var/www/app/build"
        elif [ -d "dist" ]; then
            APP_ROOT="/var/www/app/dist"
        elif [ -d "out" ]; then
            APP_ROOT="/var/www/app/out"
        fi
    elif grep -q '"start"' package.json 2>/dev/null; then
        echo "Starting Node.js server with PM2"
        cd /var/www/app && PORT=3000 pm2 start npm --name app -- start 2>/dev/null || true
        pm2 save 2>/dev/null || true
    fi

elif [ -f "requirements.txt" ]; then
    echo "Detected Python project"
    python3.11 -m venv /var/www/app/venv 2>/dev/null || python3 -m venv /var/www/app/venv 2>/dev/null || true
    if [ -f "/var/www/app/venv/bin/activate" ]; then
        source /var/www/app/venv/bin/activate
        pip install -r requirements.txt 2>/dev/null || true
        pip install gunicorn 2>/dev/null || true
        
        if [ -f "app.py" ]; then
            nohup /var/www/app/venv/bin/gunicorn app:app -b 0.0.0.0:8000 --daemon 2>/dev/null || true
        elif [ -f "main.py" ]; then
            nohup /var/www/app/venv/bin/gunicorn main:app -b 0.0.0.0:8000 --daemon 2>/dev/null || true
        fi
    fi

else
    echo "Static site or unknown project type"
fi

# ===== CONFIGURE NGINX =====
cat > /etc/nginx/conf.d/app.conf << 'NGINXEOF'
server {{
    listen 80 default_server;
    root {{APP_ROOT_PLACEHOLDER}};
    index index.html index.htm;
    
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    
    location /api {{
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
NGINXEOF

# Set the correct app root in nginx config
sed -i "s|{{APP_ROOT_PLACEHOLDER}}|$APP_ROOT|g" /etc/nginx/conf.d/app.conf

# Overwrite main nginx.conf to remove default server blocks cleanly
cat > /etc/nginx/nginx.conf << 'NGINXEOF_MAIN'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;
include /usr/share/nginx/modules/*.conf;
events {{
    worker_connections 1024;
}}
http {{
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';
    access_log  /var/log/nginx/access.log  main;
    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 4096;
    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;
    # Load modular configuration files from the /etc/nginx/conf.d directory
    include /etc/nginx/conf.d/*.conf;
}}
NGINXEOF_MAIN

# Disable default nginx server block (for Debian/Ubuntu based AMIs just in case)
rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Fix permissions
chown -R ec2-user:ec2-user /var/www/app

# Start nginx
systemctl enable nginx
systemctl restart nginx

echo "=== AutoCloud Architect: Deployment Complete ==="
echo "App root: $APP_ROOT"
"""
    
    def _add_storage_resources(self, template: dict, recommendations: RecommendationOutput):
        """Add S3 storage resources to template."""
        if recommendations.storage.s3_bucket:
            template["Resources"]["S3Bucket"] = {
                "Type": "AWS::S3::Bucket",
                "DeletionPolicy": "Retain",
                "Properties": {
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True
                    },
                    "Tags": [{"Key": "ManagedBy", "Value": "AutoCloud-Architect"}]
                }
            }
            
            template["Outputs"]["S3BucketName"] = {
                "Value": {"Ref": "S3Bucket"},
                "Description": "S3 Bucket Name"
            }
    
    def _add_database_resources(self, template: dict, recommendations: RecommendationOutput):
        """Add database resources to template."""
        if recommendations.database.db_type == "dynamodb":
            template["Resources"]["DynamoDBTable"] = {
                "Type": "AWS::DynamoDB::Table",
                "Properties": {
                    "TableName": {"Fn::Sub": "${AppName}-table"},
                    "AttributeDefinitions": [
                        {"AttributeName": "id", "AttributeType": "S"}
                    ],
                    "KeySchema": [
                        {"AttributeName": "id", "KeyType": "HASH"}
                    ],
                    "BillingMode": "PAY_PER_REQUEST",
                    "Tags": [{"Key": "ManagedBy", "Value": "AutoCloud-Architect"}]
                }
            }
        else:
            # RDS — needs a subnet group with 2 subnets in different AZs
            template["Resources"]["DBSubnetGroup"] = {
                "Type": "AWS::RDS::DBSubnetGroup",
                "Properties": {
                    "DBSubnetGroupDescription": {"Fn::Sub": "${AppName} DB subnet group"},
                    "SubnetIds": [
                        {"Ref": "PublicSubnet1"},
                        {"Ref": "PublicSubnet2"}
                    ]
                }
            }
            
            template["Resources"]["DBSecurityGroup"] = {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": {"Fn::Sub": "${AppName} database security group"},
                    "VpcId": {"Ref": "VPC"},
                    "SecurityGroupIngress": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 3306,
                            "ToPort": 3306,
                            "SourceSecurityGroupId": {"Ref": "SecurityGroup"}
                        }
                    ]
                }
            }
            
            template["Resources"]["RDSInstance"] = {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "DBInstanceClass": recommendations.database.instance_class or "db.t3.micro",
                    "Engine": "mysql",
                    "MasterUsername": "admin",
                    "MasterUserPassword": "AutoCloud123!",
                    "AllocatedStorage": "20",
                    "VPCSecurityGroups": [{"Ref": "DBSecurityGroup"}],
                    "DBSubnetGroupName": {"Ref": "DBSubnetGroup"},
                    "MultiAZ": recommendations.database.multi_az,
                    "Tags": [{"Key": "ManagedBy", "Value": "AutoCloud-Architect"}]
                }
            }
            
            template["Outputs"]["RDSEndpoint"] = {
                "Value": {"Fn::GetAtt": ["RDSInstance", "Endpoint.Address"]},
                "Description": "RDS Endpoint"
            }
    
    def _add_alb_resources(self, template: dict):
        """Add Application Load Balancer with target group and listener."""
        resources = template["Resources"]
        
        resources["ALBSecurityGroup"] = {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": {"Fn::Sub": "${AppName} ALB security group"},
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"}
                ]
            }
        }
        
        resources["ALB"] = {
            "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "Properties": {
                "Name": {"Fn::Sub": "${AppName}-alb"},
                "Subnets": [
                    {"Ref": "PublicSubnet1"},
                    {"Ref": "PublicSubnet2"}
                ],
                "SecurityGroups": [{"Ref": "ALBSecurityGroup"}],
                "Scheme": "internet-facing",
                "Type": "application"
            }
        }
        
        resources["ALBTargetGroup"] = {
            "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
            "Properties": {
                "Name": {"Fn::Sub": "${AppName}-tg"},
                "Port": 80,
                "Protocol": "HTTP",
                "VpcId": {"Ref": "VPC"},
                "TargetType": "instance",
                "Targets": [
                    {"Id": {"Ref": "EC2Instance"}, "Port": 80}
                ],
                "HealthCheckPath": "/",
                "HealthCheckIntervalSeconds": 30,
                "HealthyThresholdCount": 2,
                "UnhealthyThresholdCount": 5
            }
        }
        
        resources["ALBListener"] = {
            "Type": "AWS::ElasticLoadBalancingV2::Listener",
            "Properties": {
                "LoadBalancerArn": {"Ref": "ALB"},
                "Port": 80,
                "Protocol": "HTTP",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": {"Ref": "ALBTargetGroup"}
                    }
                ]
            }
        }
        
        template["Outputs"]["ALBDNSName"] = {
            "Value": {"Fn::GetAtt": ["ALB", "DNSName"]},
            "Description": "ALB DNS Name"
        }
    
    async def _mock_provision(
        self,
        app_name: str,
        recommendations: RecommendationOutput
    ) -> dict:
        """Mock provisioning for development."""
        logger.info("Using mock provisioning (AWS not configured)")
        
        # Simulate provisioning delay
        await asyncio.sleep(2)
        
        resources = [
            AWSResource(
                resource_type="AWS::EC2::VPC",
                resource_id="vpc-mock12345",
                status="CREATE_COMPLETE",
                details={"cidr": "10.0.0.0/16"}
            ),
            AWSResource(
                resource_type="AWS::EC2::Instance",
                resource_id="i-mock12345",
                status="CREATE_COMPLETE",
                details={
                    "instance_type": recommendations.compute.instance_type,
                    "public_ip": "54.123.45.67"
                }
            ),
            AWSResource(
                resource_type="AWS::S3::Bucket",
                resource_id=f"{app_name.lower()}-storage-mock",
                status="CREATE_COMPLETE",
                details={}
            )
        ]
        
        if recommendations.database:
            if recommendations.database.db_type == "dynamodb":
                resources.append(AWSResource(
                    resource_type="AWS::DynamoDB::Table",
                    resource_id=f"{app_name.lower()}-table",
                    status="CREATE_COMPLETE",
                    details={}
                ))
            else:
                resources.append(AWSResource(
                    resource_type="AWS::RDS::DBInstance",
                    resource_id="autocloud-db-mock",
                    status="CREATE_COMPLETE",
                    details={"endpoint": "autocloud-db.mock.rds.amazonaws.com"}
                ))
        
        if recommendations.networking.use_alb:
            resources.append(AWSResource(
                resource_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
                resource_id="arn:aws:elasticloadbalancing:us-east-1:mock:loadbalancer/app/autocloud-alb/mock",
                status="CREATE_COMPLETE",
                details={"dns_name": "autocloud-alb-mock.us-east-1.elb.amazonaws.com"}
            ))
        
        return {
            "stack_id": "arn:aws:cloudformation:us-east-1:mock:stack/autocloud-mock/12345",
            "stack_name": f"autocloud-{app_name.lower()}",
            "resources": resources,
            "outputs": {
                "PublicIP": "54.123.45.67",
                "InstanceId": "i-mock12345",
                "VpcId": "vpc-mock12345"
            }
        }
    
    async def delete_stack(self, stack_name: str) -> bool:
        """Delete a CloudFormation stack."""
        if self.use_mock:
            logger.info(f"Mock: Deleted stack {stack_name}")
            return True
        
        try:
            self.cf_client.delete_stack(StackName=stack_name)
            logger.info(f"Initiated deletion of stack: {stack_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete stack: {str(e)}")
            return False
