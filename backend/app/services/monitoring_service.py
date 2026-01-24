"""
AutoCloud Architect - Monitoring Service

Handles CloudWatch monitoring and metrics collection.
"""
import boto3
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from app.config import get_settings
from app.core.exceptions import AutoCloudException

logger = logging.getLogger(__name__)
settings = get_settings()


class MonitoringService:
    """
    Service for monitoring deployed AWS resources.
    
    Uses CloudWatch to collect metrics and set up alarms.
    """
    
    def __init__(self):
        """Initialize CloudWatch client."""
        self.use_mock = not settings.aws_access_key_id
        
        if not self.use_mock:
            self.cw_client = boto3.client(
                'cloudwatch',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self.logs_client = boto3.client(
                'logs',
                region_name=settings.aws_default_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        
        logger.info(f"Monitoring service initialized (mock={self.use_mock})")
    
    async def get_instance_metrics(
        self,
        instance_id: str,
        period_minutes: int = 60
    ) -> dict:
        """
        Get CloudWatch metrics for an EC2 instance.
        
        Args:
            instance_id: EC2 instance ID
            period_minutes: Time period in minutes
            
        Returns:
            Dictionary with CPU, memory, and network metrics
        """
        if self.use_mock:
            return self._get_mock_metrics(instance_id)
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=period_minutes)
            
            # Get CPU utilization
            cpu_response = self.cw_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average', 'Maximum']
            )
            
            # Get network metrics
            network_in = self.cw_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            network_out = self.cw_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            return {
                "instance_id": instance_id,
                "period_minutes": period_minutes,
                "cpu": {
                    "average": self._get_stat(cpu_response, 'Average'),
                    "maximum": self._get_stat(cpu_response, 'Maximum')
                },
                "network": {
                    "bytes_in": self._get_stat(network_in, 'Sum'),
                    "bytes_out": self._get_stat(network_out, 'Sum')
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}")
            raise AutoCloudException(f"Failed to get metrics: {str(e)}")
    
    def _get_stat(self, response: dict, stat_name: str) -> Optional[float]:
        """Extract statistic from CloudWatch response."""
        datapoints = response.get('Datapoints', [])
        if datapoints:
            return datapoints[-1].get(stat_name)
        return None
    
    def _get_mock_metrics(self, instance_id: str) -> dict:
        """Generate mock metrics for development."""
        import random
        
        return {
            "instance_id": instance_id,
            "period_minutes": 60,
            "cpu": {
                "average": round(random.uniform(5, 30), 2),
                "maximum": round(random.uniform(30, 70), 2)
            },
            "network": {
                "bytes_in": random.randint(1000000, 10000000),
                "bytes_out": random.randint(500000, 5000000)
            },
            "status": "healthy",
            "uptime_hours": round(random.uniform(1, 100), 1)
        }
    
    async def create_dashboard(
        self,
        app_name: str,
        instance_id: str
    ) -> str:
        """
        Create a CloudWatch dashboard for the deployment.
        
        Args:
            app_name: Application name
            instance_id: EC2 instance ID
            
        Returns:
            Dashboard URL
        """
        if self.use_mock:
            return f"https://console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}#dashboards:name=mock-dashboard"
        
        dashboard_name = f"AutoCloud-{app_name}"
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "CPU Utilization",
                        "metrics": [
                            ["AWS/EC2", "CPUUtilization", "InstanceId", instance_id]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": settings.aws_default_region
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "Network Traffic",
                        "metrics": [
                            ["AWS/EC2", "NetworkIn", "InstanceId", instance_id],
                            ["AWS/EC2", "NetworkOut", "InstanceId", instance_id]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": settings.aws_default_region
                    }
                }
            ]
        }
        
        try:
            import json
            self.cw_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            return f"https://console.aws.amazon.com/cloudwatch/home?region={settings.aws_default_region}#dashboards:name={dashboard_name}"
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {str(e)}")
            return ""
    
    async def create_alarms(
        self,
        app_name: str,
        instance_id: str
    ) -> List[str]:
        """
        Create CloudWatch alarms for the deployment.
        
        Args:
            app_name: Application name
            instance_id: EC2 instance ID
            
        Returns:
            List of created alarm names
        """
        if self.use_mock:
            return [f"{app_name}-cpu-high", f"{app_name}-status-check"]
        
        alarms = []
        
        try:
            # CPU alarm
            cpu_alarm = f"{app_name}-cpu-high"
            self.cw_client.put_metric_alarm(
                AlarmName=cpu_alarm,
                AlarmDescription=f"High CPU utilization for {app_name}",
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Statistic='Average',
                Period=300,
                EvaluationPeriods=2,
                Threshold=80.0,
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ]
            )
            alarms.append(cpu_alarm)
            
            # Status check alarm
            status_alarm = f"{app_name}-status-check"
            self.cw_client.put_metric_alarm(
                AlarmName=status_alarm,
                AlarmDescription=f"Status check failed for {app_name}",
                MetricName='StatusCheckFailed',
                Namespace='AWS/EC2',
                Statistic='Maximum',
                Period=60,
                EvaluationPeriods=2,
                Threshold=1.0,
                ComparisonOperator='GreaterThanOrEqualToThreshold',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ]
            )
            alarms.append(status_alarm)
            
            logger.info(f"Created {len(alarms)} CloudWatch alarms")
            return alarms
            
        except Exception as e:
            logger.error(f"Failed to create alarms: {str(e)}")
            return []
