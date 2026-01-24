"""
AutoCloud Architect - SageMaker Training Script

This script trains a multi-output classifier to predict AWS infrastructure
recommendations based on application requirements.

Usage:
    python train.py --train-data ../dataset/training_data.csv --output-dir ./model

For SageMaker:
    The script follows SageMaker's training container contract.
"""

import argparse
import os
import json
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


def load_data(data_path):
    """Load and preprocess training data."""
    df = pd.read_csv(data_path)
    
    # Encode categorical features
    encoders = {}
    
    # Encode app_type
    encoders['app_type'] = LabelEncoder()
    df['app_type_encoded'] = encoders['app_type'].fit_transform(df['app_type'])
    
    # Encode performance
    encoders['performance'] = LabelEncoder()
    df['performance_encoded'] = encoders['performance'].fit_transform(df['performance'])
    
    # Encode budget
    encoders['budget'] = LabelEncoder()
    df['budget_encoded'] = encoders['budget'].fit_transform(df['budget'])
    
    return df, encoders


def prepare_features(df):
    """Prepare feature matrix and target variables."""
    # Input features
    X = df[[
        'app_type_encoded',
        'expected_users',
        'data_size_gb',
        'performance_encoded',
        'budget_encoded'
    ]].values
    
    # Normalize numerical features
    X[:, 1] = np.log1p(X[:, 1])  # log transform users
    X[:, 2] = np.log1p(X[:, 2])  # log transform data size
    
    # Target variables
    y_compute = df['compute_type'].values
    y_db = df['db_type'].fillna('none').values
    y_alb = df['use_alb'].values
    y_asg = df['use_asg'].values
    
    return X, y_compute, y_db, y_alb, y_asg


def train_models(X, y_compute, y_db, y_alb, y_asg):
    """Train separate classifiers for each output."""
    
    # Split data
    X_train, X_test, y_compute_train, y_compute_test = train_test_split(
        X, y_compute, test_size=0.2, random_state=42
    )
    
    _, _, y_db_train, y_db_test = train_test_split(
        X, y_db, test_size=0.2, random_state=42
    )
    
    _, _, y_alb_train, y_alb_test = train_test_split(
        X, y_alb, test_size=0.2, random_state=42
    )
    
    _, _, y_asg_train, y_asg_test = train_test_split(
        X, y_asg, test_size=0.2, random_state=42
    )
    
    # Train models
    models = {}
    
    # Compute type classifier
    models['compute'] = RandomForestClassifier(n_estimators=50, random_state=42)
    models['compute'].fit(X_train, y_compute_train)
    acc_compute = accuracy_score(y_compute_test, models['compute'].predict(X_test))
    print(f"Compute classifier accuracy: {acc_compute:.2f}")
    
    # Database type classifier
    models['database'] = RandomForestClassifier(n_estimators=50, random_state=42)
    models['database'].fit(X_train, y_db_train)
    acc_db = accuracy_score(y_db_test, models['database'].predict(X_test))
    print(f"Database classifier accuracy: {acc_db:.2f}")
    
    # ALB classifier
    models['alb'] = RandomForestClassifier(n_estimators=50, random_state=42)
    models['alb'].fit(X_train, y_alb_train)
    acc_alb = accuracy_score(y_alb_test, models['alb'].predict(X_test))
    print(f"ALB classifier accuracy: {acc_alb:.2f}")
    
    # ASG classifier
    models['asg'] = RandomForestClassifier(n_estimators=50, random_state=42)
    models['asg'].fit(X_train, y_asg_train)
    acc_asg = accuracy_score(y_asg_test, models['asg'].predict(X_test))
    print(f"ASG classifier accuracy: {acc_asg:.2f}")
    
    return models, {
        'compute': acc_compute,
        'database': acc_db,
        'alb': acc_alb,
        'asg': acc_asg
    }


def save_model(models, encoders, output_dir):
    """Save trained models and encoders."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save models
    with open(os.path.join(output_dir, 'models.pkl'), 'wb') as f:
        pickle.dump(models, f)
    
    # Save encoders
    with open(os.path.join(output_dir, 'encoders.pkl'), 'wb') as f:
        pickle.dump(encoders, f)
    
    print(f"Model saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    
    # SageMaker specific arguments
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR', './model'))
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN', '../dataset'))
    
    # Custom arguments
    parser.add_argument('--train-data', type=str, default=None)
    parser.add_argument('--output-dir', type=str, default=None)
    
    args = parser.parse_args()
    
    # Determine data path
    if args.train_data:
        data_path = args.train_data
    else:
        data_path = os.path.join(args.train, 'training_data.csv')
    
    # Determine output directory
    output_dir = args.output_dir or args.model_dir
    
    print(f"Loading data from: {data_path}")
    df, encoders = load_data(data_path)
    
    print(f"Training data shape: {df.shape}")
    X, y_compute, y_db, y_alb, y_asg = prepare_features(df)
    
    print("Training models...")
    models, metrics = train_models(X, y_compute, y_db, y_alb, y_asg)
    
    save_model(models, encoders, output_dir)
    
    # Save metrics
    with open(os.path.join(output_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("Training complete!")


if __name__ == '__main__':
    main()
