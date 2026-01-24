"""
AutoCloud Architect - SageMaker Endpoint Deployment

This script deploys the trained model to a SageMaker real-time endpoint.

Usage:
    python deploy_endpoint.py --model-path ./model --endpoint-name autocloud-recommender

Prerequisites:
    - AWS credentials configured
    - Trained model artifacts in model-path
    - SageMaker execution role ARN
"""

import argparse
import boto3
import sagemaker
from sagemaker.sklearn import SKLearnModel
import os
import tarfile
import shutil


def create_model_archive(model_dir, output_path='model.tar.gz'):
    """Create a tar.gz archive of the model directory."""
    with tarfile.open(output_path, 'w:gz') as tar:
        for item in os.listdir(model_dir):
            item_path = os.path.join(model_dir, item)
            tar.add(item_path, arcname=item)
    
    print(f"Created model archive: {output_path}")
    return output_path


def upload_model_to_s3(model_path, bucket, prefix='autocloud/models'):
    """Upload model archive to S3."""
    s3 = boto3.client('s3')
    
    key = f"{prefix}/model.tar.gz"
    s3.upload_file(model_path, bucket, key)
    
    model_uri = f"s3://{bucket}/{key}"
    print(f"Uploaded model to: {model_uri}")
    return model_uri


def deploy_endpoint(model_uri, role_arn, endpoint_name, instance_type='ml.t2.medium'):
    """Deploy model to SageMaker endpoint."""
    
    sklearn_model = SKLearnModel(
        model_data=model_uri,
        role=role_arn,
        entry_point='inference.py',
        source_dir='./inference',
        framework_version='1.2-1',
        py_version='py3'
    )
    
    print(f"Deploying endpoint: {endpoint_name}")
    predictor = sklearn_model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        endpoint_name=endpoint_name
    )
    
    print(f"Endpoint deployed: {endpoint_name}")
    return predictor


def test_endpoint(endpoint_name):
    """Test the deployed endpoint with sample data."""
    runtime = boto3.client('sagemaker-runtime')
    
    test_input = {
        "app_type": "web",
        "expected_users": 1000,
        "data_size_gb": 50,
        "performance_priority": "balanced",
        "budget_tier": "medium"
    }
    
    import json
    response = runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Body=json.dumps(test_input)
    )
    
    result = json.loads(response['Body'].read().decode())
    print("Test prediction:")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-path', type=str, default='./training/model')
    parser.add_argument('--endpoint-name', type=str, default='autocloud-recommender')
    parser.add_argument('--role-arn', type=str, required=False)
    parser.add_argument('--bucket', type=str, default='autocloud-models')
    parser.add_argument('--instance-type', type=str, default='ml.t2.medium')
    parser.add_argument('--test-only', action='store_true')
    
    args = parser.parse_args()
    
    if args.test_only:
        test_endpoint(args.endpoint_name)
        return
    
    # Get role ARN from environment if not provided
    role_arn = args.role_arn or os.environ.get('SAGEMAKER_ROLE_ARN')
    if not role_arn:
        print("Error: SageMaker role ARN required. Set via --role-arn or SAGEMAKER_ROLE_ARN env var")
        return
    
    # Create model archive
    archive_path = create_model_archive(args.model_path)
    
    # Upload to S3
    model_uri = upload_model_to_s3(archive_path, args.bucket)
    
    # Deploy endpoint
    deploy_endpoint(
        model_uri=model_uri,
        role_arn=role_arn,
        endpoint_name=args.endpoint_name,
        instance_type=args.instance_type
    )
    
    # Test endpoint
    test_endpoint(args.endpoint_name)
    
    # Cleanup
    os.remove(archive_path)
    print("Deployment complete!")


if __name__ == '__main__':
    main()
