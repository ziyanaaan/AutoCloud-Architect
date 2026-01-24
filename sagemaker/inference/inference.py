"""
AutoCloud Architect - SageMaker Inference Script

This script handles inference requests for the AutoCloud recommendation model.
It follows the SageMaker inference container contract.

Functions:
    model_fn: Load the model
    input_fn: Parse input data
    predict_fn: Make predictions
    output_fn: Format output
"""

import os
import json
import pickle
import numpy as np


def model_fn(model_dir):
    """Load model artifacts from the model directory."""
    models_path = os.path.join(model_dir, 'models.pkl')
    encoders_path = os.path.join(model_dir, 'encoders.pkl')
    
    with open(models_path, 'rb') as f:
        models = pickle.load(f)
    
    with open(encoders_path, 'rb') as f:
        encoders = pickle.load(f)
    
    return {'models': models, 'encoders': encoders}


def input_fn(request_body, request_content_type):
    """Parse the input data from the request."""
    if request_content_type == 'application/json':
        data = json.loads(request_body)
        return data
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")


def predict_fn(input_data, model):
    """Make predictions using the loaded model."""
    models = model['models']
    encoders = model['encoders']
    
    # Encode input features
    app_type_encoded = encoders['app_type'].transform([input_data['app_type']])[0]
    performance_encoded = encoders['performance'].transform([input_data['performance_priority']])[0]
    budget_encoded = encoders['budget'].transform([input_data['budget_tier']])[0]
    
    # Prepare feature vector
    X = np.array([[
        app_type_encoded,
        np.log1p(input_data['expected_users']),
        np.log1p(input_data['data_size_gb']),
        performance_encoded,
        budget_encoded
    ]])
    
    # Make predictions
    compute_type = models['compute'].predict(X)[0]
    db_type = models['database'].predict(X)[0]
    use_alb = int(models['alb'].predict(X)[0])
    use_asg = int(models['asg'].predict(X)[0])
    
    # Get prediction probabilities for confidence
    compute_proba = models['compute'].predict_proba(X).max()
    
    # Build response
    result = {
        'instance_type': compute_type,
        'instance_count': 2 if use_asg else 1,
        'use_spot': input_data.get('budget_tier') == 'low',
        'db_type': db_type if db_type != 'none' else None,
        'db_instance_class': get_db_instance(db_type, input_data['budget_tier']),
        'multi_az': input_data.get('budget_tier') == 'high',
        'use_alb': bool(use_alb),
        'use_auto_scaling': bool(use_asg),
        'min_instances': 1,
        'max_instances': 4 if use_asg else 1,
        'storage_class': 'STANDARD_IA' if input_data.get('budget_tier') == 'low' else 'STANDARD',
        'estimated_cost': estimate_cost(compute_type, db_type, use_alb, use_asg),
        'confidence': float(compute_proba)
    }
    
    return result


def output_fn(prediction, response_content_type):
    """Format the prediction output."""
    if response_content_type == 'application/json':
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {response_content_type}")


def get_db_instance(db_type, budget_tier):
    """Determine RDS instance class based on database type and budget."""
    if db_type in ['none', 'dynamodb', None]:
        return None
    
    if budget_tier == 'low':
        return 'db.t3.micro'
    elif budget_tier == 'medium':
        return 'db.t3.medium'
    else:
        return 'db.m5.large'


def estimate_cost(compute_type, db_type, use_alb, use_asg):
    """Estimate monthly cost in USD."""
    # Base compute costs
    compute_costs = {
        't3.micro': 8.50,
        't3.small': 17.00,
        't3.medium': 34.00,
        't3.large': 68.00,
        'm5.large': 77.00,
        'm5.xlarge': 154.00,
        'm5.2xlarge': 307.00
    }
    
    cost = compute_costs.get(compute_type, 50.0)
    
    if use_asg:
        cost *= 2  # Assume 2 instances average
    
    # Database costs
    if db_type == 'dynamodb':
        cost += 25
    elif db_type and 'rds' in db_type:
        cost += 50
    
    # ALB cost
    if use_alb:
        cost += 25
    
    # Base infrastructure (VPC, NAT, etc.)
    cost += 35
    
    return round(cost, 2)
