# AutoCloud Architect - Architecture

## System Overview

AutoCloud Architect is an intelligent AWS infrastructure recommendation and deployment system.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                 │
│                         (React Dashboard)                                   │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND API                                       │
│                         (FastAPI Server)                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Routes     │  │  Schemas     │  │  Services    │  │    AWS       │   │
│  │   /analyze   │  │  Validation  │  │  SageMaker   │  │  Integration │   │
│  │   /deploy    │  │  Pydantic    │  │  Provisioning│  │  boto3       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  SageMaker   │ │ CloudForm    │ │  CloudWatch  │
            │  Endpoint    │ │ ation        │ │  Monitoring  │
            └──────────────┘ └──────────────┘ └──────────────┘
```

## Components

### 1. Frontend (React + Vite)
- **RequirementsForm**: Collects application requirements
- **RecommendationsView**: Displays AI recommendations
- **DeploymentProgress**: Shows real-time deployment status
- **ResultsDashboard**: Final deployment summary

### 2. Backend (FastAPI)
- **SageMaker Service**: Invokes ML model for recommendations
- **Provisioning Service**: Creates CloudFormation stacks
- **Deployment Service**: Deploys applications to EC2
- **Monitoring Service**: Sets up CloudWatch dashboards

### 3. SageMaker Model
- Multi-output classifier (RandomForest)
- Input: App type, users, data size, performance, budget
- Output: Instance type, database, ALB, ASG recommendations

### 4. Infrastructure (CloudFormation)
- VPC with public/private subnets
- EC2 instances with Auto Scaling
- S3 buckets and DynamoDB tables
- Application Load Balancer
- IAM roles with least privilege

## Data Flow

1. User enters requirements in web form
2. Frontend sends POST to `/api/v1/analyze`
3. Backend invokes SageMaker endpoint
4. SageMaker returns recommendations
5. User approves and clicks Deploy
6. Backend creates CloudFormation stack
7. Resources are provisioned
8. Application is deployed to EC2
9. Health check verifies deployment
10. User receives endpoint URL

## Security

- All S3 buckets have public access blocked
- EC2 instances use IAM roles (no hardcoded credentials)
- Security groups limit inbound traffic
- SSM used for instance management (no SSH keys required)
