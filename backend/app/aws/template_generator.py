"""
AutoCloud Architect - Template Generator
"""
from typing import Dict, Any
from app.schemas.deployment import RecommendationOutput


class TemplateGenerator:
    """Generate CloudFormation templates from recommendations."""
    
    @staticmethod
    def generate_master_template(
        app_name: str,
        recommendations: RecommendationOutput
    ) -> Dict[str, Any]:
        """Generate complete CloudFormation template."""
        return {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": f"AutoCloud - {app_name}",
            "Parameters": {
                "AppName": {"Type": "String", "Default": app_name},
                "InstanceType": {"Type": "String", "Default": recommendations.compute.instance_type}
            },
            "Resources": {},
            "Outputs": {}
        }
