"""
AutoCloud Architect - CloudFormation Helper
"""
import boto3
import json
import logging
from typing import Optional, Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CloudFormationHelper:
    """Helper class for CloudFormation operations."""
    
    def __init__(self):
        self.use_mock = not settings.aws_access_key_id
        if not self.use_mock:
            self.client = boto3.client(
                'cloudformation',
                region_name=settings.aws_default_region
            )
    
    def validate_template(self, template: Dict[str, Any]) -> bool:
        if self.use_mock:
            return True
        try:
            self.client.validate_template(TemplateBody=json.dumps(template))
            return True
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def get_stack_status(self, stack_name: str) -> Optional[str]:
        if self.use_mock:
            return "CREATE_COMPLETE"
        try:
            response = self.client.describe_stacks(StackName=stack_name)
            return response['Stacks'][0]['StackStatus'] if response['Stacks'] else None
        except:
            return None
