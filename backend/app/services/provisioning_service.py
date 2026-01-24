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
        
        logger.info(f"Provisioning service initialized (mock={self.use_mock})")
    
    async def provision_infrastructure(
        self,
        app_name: str,
        recommendations: RecommendationOutput
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
        
        return await self._create_stack(app_name, recommendations)
    
    async def _create_stack(
        self,
        app_name: str,
        recommendations: RecommendationOutput
    ) -> dict:
        """Create CloudFormation stack."""
        try:
            stack_name = f"autocloud-{app_name.lower().replace(' ', '-')}"
            
            # Generate CloudFormation template
            template = self._generate_template(app_name, recommendations)
            
            # Create stack
            response = self.cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=json.dumps(template),
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Application', 'Value': app_name},
                    {'Key': 'ManagedBy', 'Value': 'AutoCloud-Architect'}
                ]
            )
            
            stack_id = response['StackId']
            logger.info(f"Created CloudFormation stack: {stack_id}")
            
            # Wait for stack creation
            resources = await self._wait_for_stack(stack_name)
            
            return {
                "stack_id": stack_id,
                "stack_name": stack_name,
                "resources": resources
            }
            
        except Exception as e:
            logger.error(f"Stack creation failed: {str(e)}")
            raise ProvisioningException(f"Failed to provision infrastructure: {str(e)}")
    
    async def _wait_for_stack(self, stack_name: str) -> list[AWSResource]:
        """Wait for stack creation and return resources."""
        waiter = self.cf_client.get_waiter('stack_create_complete')
        
        try:
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={'Delay': 10, 'MaxAttempts': 60}
            )
        except Exception as e:
            raise ProvisioningException(f"Stack creation timed out: {str(e)}")
        
        # Get stack resources
        response = self.cf_client.describe_stack_resources(StackName=stack_name)
        
        resources = []
        for resource in response.get('StackResources', []):
            resources.append(AWSResource(
                resource_type=resource['ResourceType'],
                resource_id=resource['PhysicalResourceId'],
                status=resource['ResourceStatus'],
                details={
                    'logical_id': resource['LogicalResourceId']
                }
            ))
        
        return resources
    
    def _generate_template(
        self,
        app_name: str,
        recommendations: RecommendationOutput
    ) -> dict:
        """Generate CloudFormation template from recommendations."""
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
                }
            },
            "Resources": {},
            "Outputs": {}
        }
        
        # Add VPC resources
        self._add_vpc_resources(template)
        
        # Add compute resources
        self._add_compute_resources(template, recommendations)
        
        # Add storage resources
        self._add_storage_resources(template, recommendations)
        
        # Add database if required
        if recommendations.database:
            self._add_database_resources(template, recommendations)
        
        # Add load balancer if required
        if recommendations.networking.use_alb:
            self._add_alb_resources(template)
        
        return template
    
    def _add_vpc_resources(self, template: dict):
        """Add VPC and networking resources to template."""
        template["Resources"]["VPC"] = {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16",
                "EnableDnsHostnames": True,
                "EnableDnsSupport": True,
                "Tags": [{"Key": "Name", "Value": {"Ref": "AppName"}}]
            }
        }
        
        template["Resources"]["InternetGateway"] = {
            "Type": "AWS::EC2::InternetGateway"
        }
        
        template["Resources"]["AttachGateway"] = {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "InternetGatewayId": {"Ref": "InternetGateway"}
            }
        }
        
        template["Resources"]["PublicSubnet"] = {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.1.0/24",
                "MapPublicIpOnLaunch": True,
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]}
            }
        }
    
    def _add_compute_resources(self, template: dict, recommendations: RecommendationOutput):
        """Add EC2 compute resources to template."""
        template["Resources"]["SecurityGroup"] = {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "AutoCloud security group",
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"},
                    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "CidrIp": "0.0.0.0/0"}
                ]
            }
        }
        
        template["Resources"]["EC2Instance"] = {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "InstanceType": {"Ref": "InstanceType"},
                "ImageId": "ami-0c55b159cbfafe1f0",  # Amazon Linux 2
                "SubnetId": {"Ref": "PublicSubnet"},
                "SecurityGroupIds": [{"Ref": "SecurityGroup"}],
                "Tags": [{"Key": "Name", "Value": {"Ref": "AppName"}}]
            }
        }
        
        template["Outputs"]["InstanceId"] = {
            "Value": {"Ref": "EC2Instance"},
            "Description": "EC2 Instance ID"
        }
        
        template["Outputs"]["PublicIP"] = {
            "Value": {"Fn::GetAtt": ["EC2Instance", "PublicIp"]},
            "Description": "Public IP Address"
        }
    
    def _add_storage_resources(self, template: dict, recommendations: RecommendationOutput):
        """Add S3 storage resources to template."""
        if recommendations.storage.s3_bucket:
            template["Resources"]["S3Bucket"] = {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {"Fn::Sub": "${AppName}-storage-${AWS::AccountId}"},
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True
                    }
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
                    "BillingMode": "PAY_PER_REQUEST"
                }
            }
        else:
            # RDS
            template["Resources"]["DBSubnetGroup"] = {
                "Type": "AWS::RDS::DBSubnetGroup",
                "Properties": {
                    "DBSubnetGroupDescription": "Subnet group for RDS",
                    "SubnetIds": [{"Ref": "PublicSubnet"}]
                }
            }
            
            template["Resources"]["RDSInstance"] = {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "DBInstanceClass": recommendations.database.instance_class or "db.t3.micro",
                    "Engine": "mysql",
                    "MasterUsername": "admin",
                    "MasterUserPassword": "ChangeMe123!",
                    "AllocatedStorage": "20",
                    "VPCSecurityGroups": [{"Ref": "SecurityGroup"}],
                    "DBSubnetGroupName": {"Ref": "DBSubnetGroup"}
                }
            }
    
    def _add_alb_resources(self, template: dict):
        """Add Application Load Balancer resources."""
        template["Resources"]["ALB"] = {
            "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "Properties": {
                "Name": {"Fn::Sub": "${AppName}-alb"},
                "Subnets": [{"Ref": "PublicSubnet"}],
                "SecurityGroups": [{"Ref": "SecurityGroup"}],
                "Scheme": "internet-facing",
                "Type": "application"
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
            "resources": resources
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
